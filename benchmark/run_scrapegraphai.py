"""
Runs a real, measured comparison against ScrapeGraphAI on a representative
subset of the benchmark (professor review item 3): 3 resources from each of
the 5 List Mode categories plus 2 Single Page Mode resources = 17 total.

Uses ScrapeGraphAI's `extract()` endpoint (structured, schema-guided
extraction from a natural-language prompt), the closest real analogue to
CroW's structured output. Not a simulation: every call hits the live
ScrapeGraphAI API against the same live URLs used elsewhere in this
benchmark, and costs real credits from the account in .env.

Output: scrapegraphai_results/<resource_id>.json (raw response + timing),
scrapegraphai_results.csv (summary with precision/recall/F1 against the
same ground_truth/ files already fetched for the main benchmark).
"""
import json, os, sys, time, csv
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from resources import RESOURCES
from scrapegraph_py import ScrapeGraphAI, FetchConfig

# mode="auto" silently returned empty records for every JavaScript-rendered
# resource (PubMed, UniProt, ClinicalTrials.gov) in an initial pass -- it
# did not execute the client-side rendering these SPAs need. Forcing
# mode="js" with a wait for hydration fixed this (verified on
# pubmed_tp53_tumor_suppressor: 0 records under "auto", 10 correct records
# under "js"). Using "js" explicitly for every call so the comparison
# reflects ScrapeGraphAI's real JS-rendering capability, not an
# under-configured default.
FETCH_CONFIG = FetchConfig(mode="js", wait=3000)

BASE = os.path.dirname(__file__)
OUT_DIR = os.path.join(BASE, "scrapegraphai_results")
GROUND_TRUTH = os.path.join(BASE, "ground_truth")
os.makedirs(OUT_DIR, exist_ok=True)

SUBSET = [
    "pubmed_tp53_tumor_suppressor", "pubmed_brca1_breast_cancer", "pubmed_crispr_gene_editing",
    "clinicaltrials_crispr", "clinicaltrials_diabetes", "clinicaltrials_alzheimer_disease",
    "uniprot_insulin", "uniprot_hemoglobin", "uniprot_p53",
    "ncbi_gene_insulin", "ncbi_gene_brca1", "ncbi_gene_apoe",
    "medlineplus_diabetes", "medlineplus_hypertension", "medlineplus_asthma",
    "uniprot_entry_p01308", "clinicaltrials_study_nct03057912",
]


def build_schema(res):
    field_names = [c["name"] for c in res["columns"]]
    if res["mode"] == "A":
        return {
            "type": "object",
            "properties": {
                "records": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {f: {"type": "string"} for f in field_names},
                        "required": field_names,
                    },
                }
            },
            "required": ["records"],
        }
    else:
        return {
            "type": "object",
            "properties": {f: {"type": "string"} for f in field_names},
            "required": field_names,
        }


def build_prompt(res):
    field_names = [c["name"] for c in res["columns"]]
    if res["mode"] == "A":
        return (
            f"Extract every result row shown on this page as a list of records. "
            f"For each record, extract these fields: {', '.join(field_names)}. "
            f"Return only records actually visible in the results list on this page, "
            f"not navigation, header, or footer content."
        )
    else:
        return (
            f"Extract these fields from this single entity/detail page: "
            f"{', '.join(field_names)}. Return exactly one record with these fields."
        )


def main(only=None):
    sgai = ScrapeGraphAI(api_key=os.environ["SCRAPEGRAPH_API_KEY"])
    by_id = {r["id"]: r for r in RESOURCES}

    credits_before = sgai.credits().data.remaining
    print(f"Credits before run: {credits_before}")

    targets = [rid for rid in SUBSET if only is None or rid in only]
    rows = []
    for rid in targets:
        res = by_id[rid]
        prompt = build_prompt(res)
        schema = build_schema(res)

        for attempt in range(5):
            t0 = time.time()
            try:
                result = sgai.extract(prompt=prompt, url=res["url"], schema=schema,
                                       fetch_config=FETCH_CONFIG)
                elapsed = time.time() - t0
                status = result.status
                data = result.data.model_dump() if status == "success" and result.data else None
                error = result.error
            except Exception as e:
                elapsed = time.time() - t0
                status = "exception"
                data = None
                error = str(e)

            if status == "success" or "rate limit" not in (error or "").lower():
                break
            backoff = 15 * (attempt + 1)
            print(f"  {rid}: rate limited, retrying in {backoff}s...")
            time.sleep(backoff)

        out = {"resource_id": rid, "status": status, "elapsed_seconds": round(elapsed, 2),
               "data": data, "error": error}
        with open(os.path.join(OUT_DIR, f"{rid}.json"), "w") as f:
            json.dump(out, f, indent=2)
        print(f"{rid}: status={status} elapsed={elapsed:.1f}s")
        rows.append(out)
        time.sleep(8)

    credits_after = sgai.credits().data.remaining
    print(f"\nCredits after run: {credits_after} (used: {credits_before - credits_after})")

    with open(os.path.join(BASE, "scrapegraphai_run_summary.json"), "w") as f:
        json.dump({
            "subset_size": len(SUBSET),
            "credits_before": credits_before,
            "credits_after": credits_after,
            "credits_used": credits_before - credits_after,
        }, f, indent=2)


if __name__ == "__main__":
    only = set(sys.argv[1:]) if len(sys.argv) > 1 else None
    main(only=only)
