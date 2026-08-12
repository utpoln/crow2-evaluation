"""
Computes precision/recall/F1 for the ScrapeGraphAI comparison subset, using
the exact same ground-truth files and matching logic as compute_metrics.py
(set-based key matching for List Mode, field-by-field for Single Page Mode),
so the numbers are directly comparable to CroW's on the same resources.
"""
import json, os, sys, csv

sys.path.insert(0, os.path.dirname(__file__))
from resources import RESOURCES
from compute_metrics import score_list_mode, score_single_page_mode

BASE = os.path.dirname(__file__)
SGAI_DIR = os.path.join(BASE, "scrapegraphai_results")
GROUND_TRUTH = os.path.join(BASE, "ground_truth")


def load(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def to_extracted_shape(res, sgai_out):
    """Reshape ScrapeGraphAI's {json_data: {...}} into the same
    {"records": [...]} shape compute_metrics's scorers expect."""
    if sgai_out["status"] != "success" or not sgai_out["data"]:
        return {"records": []}
    json_data = sgai_out["data"].get("json_data") or {}
    if res["mode"] == "A":
        return {"records": json_data.get("records", [])}
    else:
        return {"records": [json_data] if json_data else []}


def main():
    by_id = {r["id"]: r for r in RESOURCES}
    rows = []
    for fname in sorted(os.listdir(SGAI_DIR)):
        if not fname.endswith(".json"):
            continue
        rid = fname[: -len(".json")]
        res = by_id[rid]
        sgai_out = load(os.path.join(SGAI_DIR, fname))
        gt = load(os.path.join(GROUND_TRUTH, f"{rid}.json"))
        if gt is None:
            print(f"SKIP {rid}: no ground truth")
            continue

        extracted = to_extracted_shape(res, sgai_out)

        if res["mode"] == "B":
            tp, fp, fn, ex_count, gt_count = score_single_page_mode(res, extracted, gt)
        else:
            tp, fp, fn, ex_count, gt_count = score_list_mode(res, extracted, gt)

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

        rows.append({
            "resource_id": rid,
            "category": res["category"],
            "mode": res["mode"],
            "sgai_status": sgai_out["status"],
            "extracted_count": ex_count,
            "ground_truth_count": gt_count,
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "elapsed_seconds": round(sgai_out.get("elapsed_seconds", 0), 2),
        })

    out_csv = os.path.join(BASE, "scrapegraphai_results.csv")
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"{'resource':<35} {'P':>6} {'R':>6} {'F1':>6}  time(s)")
    for r in rows:
        print(f"{r['resource_id']:<35} {r['precision']*100:>5.1f}% {r['recall']*100:>5.1f}% "
              f"{r['f1']*100:>5.1f}%  {r['elapsed_seconds']:>6.1f}")

    n = len(rows)
    print(f"\nMean across {n} resources: "
          f"precision={sum(r['precision'] for r in rows)/n*100:.1f}%  "
          f"recall={sum(r['recall'] for r in rows)/n*100:.1f}%  "
          f"F1={sum(r['f1'] for r in rows)/n*100:.1f}%  "
          f"mean_runtime={sum(r['elapsed_seconds'] for r in rows)/n:.1f}s")
    print(f"\nWrote {out_csv}")


if __name__ == "__main__":
    main()
