"""
Executes each benchmark resource through CroW's real, production extraction
engine (wrapper.views._run_scraping_async -- the exact function that runs
when a user clicks "Run Extraction" in the live app) against the live
target website. Not a simulation: this launches a real headless Chromium
browser, loads the real URL, and evaluates the real XPath selectors.
Saves one JSON file per resource under extracted/, with wall-clock timing.
"""
import asyncio, json, os, sys, time

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import django
django.setup()

from wrapper.views import _run_scraping_async
from resources import RESOURCES

OUT_DIR = os.path.join(os.path.dirname(__file__), "extracted")
os.makedirs(OUT_DIR, exist_ok=True)


async def run_one(res):
    config = {
        "mode": res["mode"],
        "row_xpath": res["row_xpath"],
        "columns": res["columns"],
        "pagination": res["pagination"],
    }
    t0 = time.monotonic()
    records = await _run_scraping_async(
        config=config,
        target_urls=[res["url"]],
        max_items=res["ground_truth"].get("retmax") or res["ground_truth"].get("pageSize") or res["ground_truth"].get("size") or 50,
        col_mapping=None,
    )
    elapsed = time.monotonic() - t0
    return records, elapsed


async def main():
    results = []
    for res in RESOURCES:
        print(f"Running {res['id']} ...", flush=True)
        try:
            records, elapsed = await run_one(res)
            out_path = os.path.join(OUT_DIR, f"{res['id']}.json")
            with open(out_path, "w") as f:
                json.dump({
                    "resource_id": res["id"],
                    "url": res["url"],
                    "elapsed_seconds": elapsed,
                    "record_count": len(records),
                    "records": records,
                }, f, indent=2)
            print(f"  OK: {len(records)} records in {elapsed:.1f}s -> {out_path}")
            results.append((res["id"], len(records), elapsed, None))
        except Exception as e:
            print(f"  FAIL: {e}")
            results.append((res["id"], 0, 0.0, str(e)))
    print("\nSummary:")
    for rid, count, elapsed, err in results:
        status = f"{count} records, {elapsed:.1f}s" if err is None else f"ERROR: {err}"
        print(f"  {rid}: {status}")


if __name__ == "__main__":
    asyncio.run(main())
