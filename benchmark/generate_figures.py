"""Generates the paper's benchmark figures directly from results.csv --
no intermediate hand-editing. Rerun any time results.csv changes."""
import csv, os
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(__file__)
rows = list(csv.DictReader(open(os.path.join(BASE, "results.csv"))))
for r in rows:
    for k in ("precision", "recall", "f1", "elapsed_seconds"):
        r[k] = float(r[k])
    for k in ("extracted_count", "ground_truth_count"):
        r[k] = int(r[k])

CAT_LABELS = {
    "biomedical_search": "Biomedical\nsearch",
    "clinical": "Clinical\nregistries",
    "protein": "Protein\nknowledgebases",
    "genomic": "Genomic\nrepositories",
    "disease": "Disease\ndatabases",
}
CAT_ORDER = ["biomedical_search", "clinical", "protein", "genomic", "disease"]

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

# --- Figure 1: category distribution ---
counts = defaultdict(int)
for r in rows:
    counts[r["category"]] += 1
fig, ax = plt.subplots(figsize=(7.5, 4.2))
cats = [c for c in CAT_ORDER if counts.get(c, 0) > 0 or c == "disease"]
vals = [counts.get(c, 0) for c in cats]
colors = ["#3b82f6" if v > 0 else "#e5e7eb" for v in vals]
bars = ax.bar([CAT_LABELS[c] for c in cats], vals, color=colors, width=0.6)
for b, v in zip(bars, vals):
    label = str(v) if v > 0 else "0 (pending)"
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.5, label, ha="center", fontsize=10)
ax.tick_params(axis="x", labelsize=9)
ax.set_ylabel("Number of resources")
ax.set_ylim(0, max(vals) * 1.15)
ax.set_title(f"Benchmark corpus by category (N={len(rows)})")
plt.tight_layout()
plt.savefig(os.path.join(BASE, "fig_category_distribution.png"), dpi=200)
plt.close()

# --- Figure 2: precision/recall/F1 by category ---
by_cat = defaultdict(list)
for r in rows:
    by_cat[r["category"]].append(r)
cats2 = [c for c in CAT_ORDER if c in by_cat]
prec = [sum(x["precision"] for x in by_cat[c])/len(by_cat[c])*100 for c in cats2]
rec = [sum(x["recall"] for x in by_cat[c])/len(by_cat[c])*100 for c in cats2]
f1 = [sum(x["f1"] for x in by_cat[c])/len(by_cat[c])*100 for c in cats2]

import numpy as np
x = np.arange(len(cats2))
w = 0.25
fig, ax = plt.subplots(figsize=(6.5, 4))
ax.bar(x - w, prec, w, label="Precision", color="#10b981")
ax.bar(x, rec, w, label="Recall", color="#3b82f6")
ax.bar(x + w, f1, w, label="F1", color="#8b5cf6")
overall_prec = sum(r["precision"] for r in rows)/len(rows)*100
overall_rec = sum(r["recall"] for r in rows)/len(rows)*100
ax.axhline(overall_prec, color="#10b981", linestyle="--", linewidth=1, alpha=0.6)
ax.axhline(overall_rec, color="#3b82f6", linestyle="--", linewidth=1, alpha=0.6)
ax.set_xticks(x)
ax.set_xticklabels([CAT_LABELS[c] for c in cats2])
ax.set_ylabel("%")
ax.set_ylim(0, 110)
ax.set_title(f"Precision / Recall / F1 by category (N={len(rows)})")
ax.legend(loc="lower right", fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(BASE, "fig_precision_recall.png"), dpi=200)
plt.close()

# --- Figure 3: runtime vs records ---
fig, ax = plt.subplots(figsize=(5.5, 4))
xs = [r["extracted_count"] for r in rows]
ys = [r["elapsed_seconds"] for r in rows]
cat_colors = {"biomedical_search": "#3b82f6", "clinical": "#10b981", "protein": "#8b5cf6", "genomic": "#f59e0b"}
for c in cats2:
    xr = [r["extracted_count"] for r in by_cat[c]]
    yr = [r["elapsed_seconds"] for r in by_cat[c]]
    ax.scatter(xr, yr, label=CAT_LABELS[c].replace("\n", " "), color=cat_colors.get(c, "#666"), s=40, alpha=0.8)
ax.set_xlabel("Records extracted")
ax.set_ylabel("Runtime (s)")
ax.set_title(f"Runtime vs. records extracted (N={len(rows)})")
ax.legend(fontsize=7)
plt.tight_layout()
plt.savefig(os.path.join(BASE, "fig_runtime_vs_records.png"), dpi=200)
plt.close()

print(f"Generated 3 figures from {len(rows)} resources.")
