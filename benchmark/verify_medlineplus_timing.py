"""
Tests whether the 9 MedlinePlus discrepancies (final.tex, subsec:large_scale_eval)
are caused by live relevance-ranking drift between the extraction run and the
ground-truth fetch, as claimed, rather than something portal-specific (the
alternative hypothesis a referee would reach for, given that ScrapeGraphAI's
MedlinePlus redirect-wrapper-URL confusion is reported nearby in the same
paper). Method: for each of the 9 resources, fetch ground truth and run
extraction back-to-back (seconds apart, not the original multi-minute
batch-run gap) and recompute the diff. If the discrepancies vanish under tight
timing, that supports drift; if they persist, something else is going on and
must be reported honestly instead.
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
from fetch_ground_truth import ground_truth_medlineplus

EXTRACTED_DIR = os.path.join(os.path.dirname(__file__), "extracted")
GT_DIR = os.path.join(os.path.dirname(__file__), "ground_truth")
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "extracted_ground_truth_pre_timing_check_backup")
os.makedirs(BACKUP_DIR, exist_ok=True)

DISCREPANT = [
    "medlineplus_diabetes", "medlineplus_hypertension", "medlineplus_asthma",
    "medlineplus_osteoporosis", "medlineplus_malaria", "medlineplus_pneumonia",
    "medlineplus_rheumatoid_arthritis", "medlineplus_obesity", "medlineplus_stroke",
]


async def run_extraction(res):
    config = {
        "mode": res["mode"],
        "row_xpath": res["row_xpath"],
        "columns": res["columns"],
        "pagination": res["pagination"],
    }
    t0 = time.monotonic()
    records = await _run_scraping_async(
        config=config, target_urls=[res["url"]],
        max_items=res["ground_truth"]["retmax"], col_mapping=None,
    )
    return records, time.monotonic() - t0


def backup(rid):
    for d, out in [(EXTRACTED_DIR, "extracted"), (GT_DIR, "ground_truth")]:
        src = os.path.join(d, f"{rid}.json")
        if os.path.exists(src):
            dst = os.path.join(BACKUP_DIR, f"{out}__{rid}.json")
            if not os.path.exists(dst):
                with open(src) as f_in, open(dst, "w") as f_out:
                    f_out.write(f_in.read())


async def main():
    by_id = {r["id"]: r for r in RESOURCES}
    report = []
    for rid in DISCREPANT:
        res = by_id[rid]
        backup(rid)
        print(f"\n=== {rid} ===")

        t_gt_start = time.time()
        gt_records = ground_truth_medlineplus(res["ground_truth"]["term"], res["ground_truth"]["retmax"])
        t_gt_end = time.time()
        with open(os.path.join(GT_DIR, f"{rid}.json"), "w") as f:
            json.dump({"resource_id": rid, "method": "medlineplus_api", "records": gt_records}, f, indent=2)
        print(f"  ground truth fetched at {t_gt_end:.2f} ({len(gt_records)} records)")

        ex_records, elapsed = await run_extraction(res)
        t_ex_end = time.time()
        with open(os.path.join(EXTRACTED_DIR, f"{rid}.json"), "w") as f:
            json.dump({"resource_id": rid, "url": res["url"], "elapsed_seconds": elapsed,
                       "record_count": len(ex_records), "records": ex_records}, f, indent=2)
        print(f"  extraction finished at {t_ex_end:.2f} ({len(ex_records)} records), "
              f"gap from GT fetch = {t_ex_end - t_gt_end:.1f}s")

        ex_urls = {r.get("URL", "").strip() for r in ex_records if r.get("URL", "").strip()}
        gt_urls = {r["URL"] for r in gt_records}
        tp = len(ex_urls & gt_urls)
        fp = len(ex_urls - gt_urls)
        fn = len(gt_urls - ex_urls)
        print(f"  TP={tp} FP={fp} FN={fn}")
        report.append({"resource_id": rid, "gap_seconds": round(t_ex_end - t_gt_end, 1),
                        "tp": tp, "fp": fp, "fn": fn})

    print("\n\n=== SUMMARY ===")
    all_clean = True
    for r in report:
        clean = r["fp"] == 0 and r["fn"] == 0
        all_clean = all_clean and clean
        print(f"{r['resource_id']:<35} gap={r['gap_seconds']:>5.1f}s  "
              f"TP={r['tp']} FP={r['fp']} FN={r['fn']}  {'CLEAN' if clean else 'STILL MISMATCHED'}")
    print(f"\nAll 9 clean under tight timing: {all_clean}")


if __name__ == "__main__":
    asyncio.run(main())
