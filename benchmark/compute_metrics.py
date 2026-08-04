"""
Recomputes precision/recall/F1 for every benchmark resource from the raw
files in extracted/ and ground_truth/. This is the script a reviewer would
rerun to verify the reported numbers. Matching is by key_field (e.g. PMID,
NCT_ID, Accession), set-based and order-independent: CroW's record set is
compared against the independently-fetched ground-truth record set.
"""
import json, os, sys, csv

sys.path.insert(0, os.path.dirname(__file__))
from resources import RESOURCES

BASE = os.path.dirname(__file__)
EXTRACTED = os.path.join(BASE, "extracted")
GROUND_TRUTH = os.path.join(BASE, "ground_truth")


def load(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def main():
    rows = []
    for res in RESOURCES:
        rid = res["id"]
        key = res["key_field"]
        extracted = load(os.path.join(EXTRACTED, f"{rid}.json"))
        gt = load(os.path.join(GROUND_TRUTH, f"{rid}.json"))
        if extracted is None or gt is None:
            print(f"SKIP {rid}: missing extracted or ground_truth file")
            continue

        extracted_keys = {r.get(key, "").strip() for r in extracted["records"] if r.get(key, "").strip()}
        gt_keys = {r.get(key, "").strip() for r in gt["records"] if r.get(key, "").strip()}

        tp = len(extracted_keys & gt_keys)
        fp = len(extracted_keys - gt_keys)
        fn = len(gt_keys - extracted_keys)

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

        rows.append({
            "resource_id": rid,
            "category": res["category"],
            "extracted_count": len(extracted_keys),
            "ground_truth_count": len(gt_keys),
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "elapsed_seconds": round(extracted.get("elapsed_seconds", 0), 2),
        })

    out_csv = os.path.join(BASE, "results.csv")
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    print(f"{'resource':<25} {'cat':<20} {'P':>6} {'R':>6} {'F1':>6} {'TP':>4} {'FP':>4} {'FN':>4}  time(s)")
    for r in rows:
        print(f"{r['resource_id']:<25} {r['category']:<20} {r['precision']*100:>5.1f}% {r['recall']*100:>5.1f}% "
              f"{r['f1']*100:>5.1f}% {r['true_positive']:>4} {r['false_positive']:>4} {r['false_negative']:>4}  {r['elapsed_seconds']:>6.1f}")

    if rows:
        n = len(rows)
        print(f"\nMean across {n} resources: "
              f"precision={sum(r['precision'] for r in rows)/n*100:.1f}%  "
              f"recall={sum(r['recall'] for r in rows)/n*100:.1f}%  "
              f"F1={sum(r['f1'] for r in rows)/n*100:.1f}%  "
              f"mean_runtime={sum(r['elapsed_seconds'] for r in rows)/n:.1f}s")
    print(f"\nWrote {out_csv}")


if __name__ == "__main__":
    main()
