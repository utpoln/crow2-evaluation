"""
CroW 2.0 Evaluation Chart Generator
Reads from reviewer_export/ and writes publication-ready figures to charts/
"""

import json
import glob
import os
from urllib.parse import urlparse
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import seaborn as sns

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE    = os.path.dirname(__file__)
EXPORT  = os.path.join(BASE, "reviewer_export")
OUT     = os.path.join(BASE, "charts")
os.makedirs(OUT, exist_ok=True)

# ── Style ──────────────────────────────────────────────────────────────────────
PALETTE = {
    "green":   "#10b981",
    "red":     "#ef4444",
    "blue":    "#3b82f6",
    "orange":  "#f59e0b",
    "purple":  "#8b5cf6",
    "gray":    "#6b7280",
    "teal":    "#14b8a6",
    "pink":    "#ec4899",
    "indigo":  "#6366f1",
    "yellow":  "#eab308",
}
STATUS_COLORS = {"completed": PALETTE["green"], "failed": PALETTE["red"], "pending": PALETTE["orange"]}

plt.rcParams.update({
    "font.family":      "DejaVu Sans",
    "font.size":        10,
    "axes.titlesize":   12,
    "axes.titleweight": "bold",
    "axes.labelsize":   10,
    "axes.spines.top":  False,
    "axes.spines.right":False,
    "figure.dpi":       150,
    "savefig.dpi":      300,
    "savefig.bbox":     "tight",
    "savefig.facecolor":"white",
})

# ── Load data ──────────────────────────────────────────────────────────────────
df = pd.read_csv(os.path.join(EXPORT, "runs", "summary.csv"))
df["started_at"]  = pd.to_datetime(df["started_at"],  utc=True, errors="coerce")
df["completed_at"]= pd.to_datetime(df["completed_at"], utc=True, errors="coerce")

with open(os.path.join(EXPORT, "stats", "overview.json")) as f:
    overview = json.load(f)

wrappers = []
for fp in glob.glob(os.path.join(EXPORT, "wrappers", "*.json")):
    with open(fp) as f:
        wrappers.append(json.load(f))

# Build per-wrapper metadata
def domain(url):
    try:
        h = urlparse(url).netloc.replace("www.", "")
        return h if h else "unknown"
    except:
        return "unknown"

w_meta = {}
for w in wrappers:
    cfg  = w.get("config", {})
    cols = cfg.get("columns", [])
    pag  = cfg.get("pagination", {}).get("type", "none")
    w_meta[w["name"]] = {
        "domain":    domain(w.get("url", "")),
        "mode":      cfg.get("mode", "?"),
        "pagination":pag,
        "n_cols":    len(cols),
        "n_params":  len(cfg.get("url_params", [])),
    }

df["domain"]     = df["wrapper_name"].map(lambda n: w_meta.get(n, {}).get("domain", "unknown"))
df["mode"]       = df["wrapper_name"].map(lambda n: w_meta.get(n, {}).get("mode", "?"))
df["pagination"] = df["wrapper_name"].map(lambda n: w_meta.get(n, {}).get("pagination", "none"))

completed = df[df["status"] == "completed"]
failed    = df[df["status"] == "failed"]

per_wrapper = df.groupby("wrapper_name").agg(
    total      =("status", "count"),
    n_completed=("status", lambda x: (x == "completed").sum()),
    n_failed   =("status", lambda x: (x == "failed").sum()),
    avg_rows   =("row_count", "mean"),
    avg_dur    =("duration_seconds", "mean"),
).reset_index()
per_wrapper["success_rate"] = per_wrapper["n_completed"] / per_wrapper["total"] * 100
per_wrapper["domain"] = per_wrapper["wrapper_name"].map(lambda n: w_meta.get(n, {}).get("domain", "unknown"))
per_wrapper["mode"]   = per_wrapper["wrapper_name"].map(lambda n: w_meta.get(n, {}).get("mode", "?"))
per_wrapper["n_cols"] = per_wrapper["wrapper_name"].map(lambda n: w_meta.get(n, {}).get("n_cols", 0))

print(f"Loaded {len(df)} runs, {len(wrappers)} wrappers")


# ═══════════════════════════════════════════════════════════════════════════════
# Fig 1 — High-level summary dashboard (4 KPI tiles)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_kpi_summary():
    r   = overview["runs"]
    n_w = overview["wrappers"]["total"]
    n_d = overview["wrappers"]["unique_domains"]
    sr  = r["success_rate_pct"]
    fig, axes = plt.subplots(1, 4, figsize=(13, 3))
    kpis = [
        (f"{n_w}",            "Public Wrappers",  PALETTE["blue"]),
        (f"{r['total']:,}",   "Scrape Runs",      PALETTE["purple"]),
        (f"{sr}%",            "Success Rate",     PALETTE["green"]),
        (f"{n_d}",            "Unique Domains",   PALETTE["teal"]),
    ]
    for ax, (val, lbl, col) in zip(axes, kpis):
        ax.set_facecolor(col + "18")
        ax.text(0.5, 0.62, val, ha="center", va="center", transform=ax.transAxes,
                fontsize=26, fontweight="bold", color=col)
        ax.text(0.5, 0.25, lbl, ha="center", va="center", transform=ax.transAxes,
                fontsize=10, color="#374151")
        for sp in ax.spines.values(): sp.set_visible(False)
        ax.set_xticks([]); ax.set_yticks([])
        ax.spines["bottom"].set_visible(True)
        ax.spines["bottom"].set_color(col)
        ax.spines["bottom"].set_linewidth(3)
    fig.suptitle("CroW — Dataset Overview", fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout(w_pad=1.5)
    fig.savefig(os.path.join(OUT, "fig1_kpi_summary.pdf"))
    fig.savefig(os.path.join(OUT, "fig1_kpi_summary.png"))
    plt.close(fig)
    print("✓ fig1_kpi_summary")

fig_kpi_summary()


# ═══════════════════════════════════════════════════════════════════════════════
# Fig 2 — Run status distribution (donut) + failure breakdown (bar)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_status_and_failures():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    # ─ Donut ─
    r = overview["runs"]
    sizes  = [r["completed"], r["failed"], r["other"]]
    labels = [f"Completed\n{r['completed']:,}", f"Failed\n{r['failed']:,}", f"Pending/Other\n{r['other']}"]
    colors = [PALETTE["green"], PALETTE["red"], PALETTE["orange"]]
    wedges, texts = ax1.pie(sizes, labels=labels, colors=colors,
                            startangle=90, pctdistance=0.82,
                            wedgeprops=dict(width=0.45, edgecolor="white", linewidth=2))
    for t in texts:
        t.set_fontsize(9)
    ax1.text(0, 0, f"{r['success_rate_pct']}%\nsuccess", ha="center", va="center",
             fontsize=12, fontweight="bold", color="#111827")
    ax1.set_title("Run Status Distribution", pad=12)

    # ─ Failure categories ─
    fc  = r["failure_categories"]
    fc_sorted = dict(sorted(fc.items(), key=lambda x: x[1]))
    colors_bar = [PALETTE["red"] if v == max(fc.values()) else "#fca5a5" for v in fc_sorted.values()]
    bars = ax2.barh(list(fc_sorted.keys()), list(fc_sorted.values()),
                    color=colors_bar, edgecolor="white", height=0.6)
    for bar, val in zip(bars, fc_sorted.values()):
        ax2.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height()/2,
                 str(val), va="center", fontsize=9, color="#374151")
    ax2.set_xlabel("Number of failed runs")
    ax2.set_title("Failure Category Breakdown")
    ax2.set_xlim(0, max(fc_sorted.values()) * 1.18)

    fig.tight_layout(w_pad=3)
    fig.savefig(os.path.join(OUT, "fig2_status_failures.pdf"))
    fig.savefig(os.path.join(OUT, "fig2_status_failures.png"))
    plt.close(fig)
    print("✓ fig2_status_failures")

fig_status_and_failures()


# ═══════════════════════════════════════════════════════════════════════════════
# Fig 3 — Wrapper configuration breakdown (mode + pagination + columns)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_wrapper_config():
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(13, 4.2))

    # Mode
    n_a = sum(1 for w in wrappers if w.get("config", {}).get("mode") == "A")
    n_b = sum(1 for w in wrappers if w.get("config", {}).get("mode") == "B")
    modes  = {"List Mode (A)": n_a, "Single Page (B)": n_b}
    ax1.bar(list(modes.keys()), list(modes.values()),
            color=[PALETTE["blue"], PALETTE["indigo"]], width=0.45, edgecolor="white")
    for x, v in enumerate(modes.values()):
        ax1.text(x, v + 0.6, str(v), ha="center", fontsize=10, fontweight="bold")
    ax1.set_ylabel("Number of wrappers")
    ax1.set_title("Extraction Mode")
    ax1.set_ylim(0, max(modes.values()) * 1.2)

    # Pagination
    pag_order = ["none", "url_increment", "button", "scroll", "container"]
    pag_labels = {"none":"None","url_increment":"URL\nIncrement","button":"Button","scroll":"Scroll","container":"Container"}
    pag_counts = {k: sum(1 for w in wrappers if w.get("config",{}).get("pagination",{}).get("type","none")==k)
                  for k in pag_order}
    pag_colors = [PALETTE["gray"], PALETTE["blue"], PALETTE["teal"], PALETTE["green"], PALETTE["purple"]]
    ax2.bar([pag_labels[k] for k in pag_order], [pag_counts[k] for k in pag_order],
            color=pag_colors, width=0.55, edgecolor="white")
    for x, k in enumerate(pag_order):
        ax2.text(x, pag_counts[k] + 0.4, str(pag_counts[k]), ha="center", fontsize=9, fontweight="bold")
    ax2.set_ylabel("Number of wrappers")
    ax2.set_title("Pagination Strategy")
    ax2.set_ylim(0, max(pag_counts.values()) * 1.2)

    # Columns per wrapper histogram
    col_counts = [len(w.get("config",{}).get("columns",[])) for w in wrappers]
    bins = range(1, max(col_counts)+2)
    ax3.hist(col_counts, bins=bins, align="left", rwidth=0.7,
             color=PALETTE["purple"], edgecolor="white")
    ax3.axvline(np.mean(col_counts), color=PALETTE["orange"], linestyle="--", linewidth=1.5,
                label=f"Mean = {np.mean(col_counts):.1f}")
    ax3.set_xlabel("Columns per wrapper")
    ax3.set_ylabel("Number of wrappers")
    ax3.set_title("Column Count Distribution")
    ax3.legend(fontsize=8)
    ax3.set_xticks(range(1, max(col_counts)+1))

    fig.tight_layout(w_pad=2.5)
    fig.savefig(os.path.join(OUT, "fig3_wrapper_config.pdf"))
    fig.savefig(os.path.join(OUT, "fig3_wrapper_config.png"))
    plt.close(fig)
    print("✓ fig3_wrapper_config")

fig_wrapper_config()


# ═══════════════════════════════════════════════════════════════════════════════
# Fig 4 — Domain-level success rate (sorted horizontal bar)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_domain_success():
    dom_stats = df.groupby("domain").agg(
        total      =("status", "count"),
        n_completed=("status", lambda x: (x=="completed").sum()),
    ).reset_index()
    dom_stats["success_rate"] = dom_stats["n_completed"] / dom_stats["total"] * 100
    dom_stats = dom_stats[dom_stats["domain"] != "unknown"].sort_values("success_rate")

    fig, ax = plt.subplots(figsize=(9, 5.5))
    colors = [PALETTE["green"] if r >= 90 else PALETTE["blue"] if r >= 75 else PALETTE["orange"]
              for r in dom_stats["success_rate"]]
    bars = ax.barh(dom_stats["domain"], dom_stats["success_rate"],
                   color=colors, edgecolor="white", height=0.6)
    for bar, (_, row) in zip(bars, dom_stats.iterrows()):
        ax.text(bar.get_width() + 0.8,
                bar.get_y() + bar.get_height()/2,
                f"{row['success_rate']:.0f}%  (n={row['total']})",
                va="center", fontsize=8.5, color="#374151")
    overall_sr = overview["runs"]["success_rate_pct"]
    ax.axvline(overall_sr, color=PALETTE["red"], linestyle="--", linewidth=1.5, label=f"Overall avg ({overall_sr}%)")
    ax.set_xlabel("Success rate (%)")
    ax.set_title("Domain-Level Extraction Success Rate")
    ax.set_xlim(0, 120)
    ax.legend(fontsize=9)

    # Legend for color tiers
    patches = [
        mpatches.Patch(color=PALETTE["green"],  label="≥ 90%"),
        mpatches.Patch(color=PALETTE["blue"],   label="75–90%"),
        mpatches.Patch(color=PALETTE["orange"], label="< 75%"),
    ]
    ax.legend(handles=patches + [mpatches.Patch(color="none", label="")],
              loc="lower right", fontsize=8.5, framealpha=0.8)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig4_domain_success.pdf"))
    fig.savefig(os.path.join(OUT, "fig4_domain_success.png"))
    plt.close(fig)
    print("✓ fig4_domain_success")

fig_domain_success()


# ═══════════════════════════════════════════════════════════════════════════════
# Fig 5 — Row count distribution (log-scale histogram + box by mode)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_row_distribution():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    rows_c = completed["row_count"].dropna()
    ax1.hist(rows_c, bins=40, color=PALETTE["blue"], edgecolor="white", alpha=0.85)
    ax1.axvline(rows_c.mean(),   color=PALETTE["red"],    linestyle="--", linewidth=1.5, label=f"Mean  {rows_c.mean():.0f}")
    ax1.axvline(rows_c.median(), color=PALETTE["orange"], linestyle=":",  linewidth=1.5, label=f"Median {rows_c.median():.0f}")
    ax1.set_xlabel("Rows extracted per run")
    ax1.set_ylabel("Number of runs")
    ax1.set_title("Row Count Distribution\n(completed runs)")
    ax1.legend(fontsize=8.5)

    # Box plot by mode
    mode_rows = completed.copy()
    mode_rows = mode_rows[mode_rows["mode"].isin(["A", "B"])]
    mode_rows["Mode"] = mode_rows["mode"].map({"A": "List (A)", "B": "Single (B)"})
    bp = ax2.boxplot(
        [mode_rows[mode_rows["Mode"]=="List (A)"]["row_count"].values,
         mode_rows[mode_rows["Mode"]=="Single (B)"]["row_count"].values],
        labels=["List Mode (A)", "Single Page (B)"],
        patch_artist=True,
        medianprops=dict(color="white", linewidth=2),
        flierprops=dict(marker="o", markersize=3, alpha=0.4),
    )
    bp["boxes"][0].set_facecolor(PALETTE["blue"])
    bp["boxes"][1].set_facecolor(PALETTE["indigo"])
    n_a = (mode_rows["Mode"]=="List (A)").sum()
    n_b = (mode_rows["Mode"]=="Single (B)").sum()
    ax2.set_title("Row Count by Extraction Mode\n(completed runs)")
    ax2.set_ylabel("Rows extracted")
    ax2.text(1, ax2.get_ylim()[1]*0.95, f"n={n_a}", ha="center", fontsize=8.5, color=PALETTE["blue"])
    ax2.text(2, ax2.get_ylim()[1]*0.95, f"n={n_b}", ha="center", fontsize=8.5, color=PALETTE["indigo"])

    fig.tight_layout(w_pad=2.5)
    fig.savefig(os.path.join(OUT, "fig5_row_distribution.pdf"))
    fig.savefig(os.path.join(OUT, "fig5_row_distribution.png"))
    plt.close(fig)
    print("✓ fig5_row_distribution")

fig_row_distribution()


# ═══════════════════════════════════════════════════════════════════════════════
# Fig 6 — Duration distribution + rows vs duration scatter
# ═══════════════════════════════════════════════════════════════════════════════
def fig_duration():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    dur_c = completed["duration_seconds"].dropna()
    ax1.hist(dur_c, bins=35, color=PALETTE["teal"], edgecolor="white", alpha=0.85)
    ax1.axvline(dur_c.mean(),   color=PALETTE["red"],    linestyle="--", linewidth=1.5, label=f"Mean  {dur_c.mean():.0f}s")
    ax1.axvline(dur_c.median(), color=PALETTE["orange"], linestyle=":",  linewidth=1.5, label=f"Median {dur_c.median():.0f}s")
    ax1.set_xlabel("Duration (seconds)")
    ax1.set_ylabel("Number of runs")
    ax1.set_title("Scrape Duration Distribution\n(completed runs)")
    ax1.legend(fontsize=8.5)

    # Scatter: rows vs duration, coloured by mode
    sc_data = completed[completed["mode"].isin(["A","B"])].dropna(subset=["row_count","duration_seconds"])
    for mode, col, lbl in [("A", PALETTE["blue"], "List (A)"), ("B", PALETTE["indigo"], "Single (B)")]:
        sub = sc_data[sc_data["mode"]==mode]
        ax2.scatter(sub["duration_seconds"], sub["row_count"],
                    color=col, alpha=0.4, s=18, label=lbl, edgecolors="none")
    # Trend line over all
    x = sc_data["duration_seconds"].values
    y = sc_data["row_count"].values
    m, b = np.polyfit(x, y, 1)
    xr = np.linspace(x.min(), x.max(), 100)
    ax2.plot(xr, m*xr+b, color=PALETTE["red"], linewidth=1.5, linestyle="--", label="Linear fit")
    ax2.set_xlabel("Duration (seconds)")
    ax2.set_ylabel("Rows extracted")
    ax2.set_title("Duration vs. Rows Extracted\n(completed runs)")
    ax2.legend(fontsize=8.5)

    fig.tight_layout(w_pad=2.5)
    fig.savefig(os.path.join(OUT, "fig6_duration.pdf"))
    fig.savefig(os.path.join(OUT, "fig6_duration.png"))
    plt.close(fig)
    print("✓ fig6_duration")

fig_duration()


# ═══════════════════════════════════════════════════════════════════════════════
# Fig 7 — Success rate by pagination type
# ═══════════════════════════════════════════════════════════════════════════════
def fig_pagination_success():
    pag_stats = df.groupby("pagination").agg(
        total      =("status", "count"),
        n_completed=("status", lambda x: (x=="completed").sum()),
    ).reset_index()
    pag_stats["success_rate"] = pag_stats["n_completed"] / pag_stats["total"] * 100
    pag_stats = pag_stats.sort_values("success_rate", ascending=False)

    label_map = {"none":"None","url_increment":"URL Incr.","button":"Button","scroll":"Scroll","container":"Container"}
    pag_stats["label"] = pag_stats["pagination"].map(label_map).fillna(pag_stats["pagination"])

    fig, ax = plt.subplots(figsize=(8, 4))
    pal = [PALETTE["green"], PALETTE["blue"], PALETTE["teal"], PALETTE["orange"], PALETTE["purple"]]
    bars = ax.bar(pag_stats["label"], pag_stats["success_rate"],
                  color=pal[:len(pag_stats)], edgecolor="white", width=0.5)
    for bar, (_, row) in zip(bars, pag_stats.iterrows()):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{row['success_rate']:.0f}%\n(n={row['total']})",
                ha="center", va="bottom", fontsize=8.5)
    overall_sr = overview["runs"]["success_rate_pct"]
    ax.axhline(overall_sr, color=PALETTE["red"], linestyle="--", linewidth=1.5, label="Overall avg")
    ax.set_ylabel("Success rate (%)")
    ax.set_ylim(0, 110)
    ax.set_title("Extraction Success Rate by Pagination Strategy")
    ax.legend(fontsize=9)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig7_pagination_success.pdf"))
    fig.savefig(os.path.join(OUT, "fig7_pagination_success.png"))
    plt.close(fig)
    print("✓ fig7_pagination_success")

fig_pagination_success()


# ═══════════════════════════════════════════════════════════════════════════════
# Fig 8 — Per-wrapper success rate heatmap strip (top 40 by run count)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_wrapper_heatmap():
    top = per_wrapper.nlargest(40, "total").sort_values("success_rate", ascending=True)
    short_names = [n if len(n) <= 30 else n[:28]+"…" for n in top["wrapper_name"]]

    fig, ax = plt.subplots(figsize=(10, 11))
    cmap = plt.cm.RdYlGn
    colors = [cmap(r/100) for r in top["success_rate"]]
    bars = ax.barh(range(len(top)), top["success_rate"], color=colors, edgecolor="white", height=0.75)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(short_names, fontsize=8)
    for i, (bar, (_, row)) in enumerate(zip(bars, top.iterrows())):
        ax.text(bar.get_width() + 0.8, i,
                f"{row['success_rate']:.0f}%  ({row['n_completed']}/{row['total']})",
                va="center", fontsize=7.5, color="#374151")
    ax.axvline(75.7, color="#374151", linestyle="--", linewidth=1, label="Overall avg")
    ax.set_xlabel("Success rate (%)")
    ax.set_xlim(0, 125)
    ax.set_title("Per-Wrapper Success Rate (top 40 by run count)", pad=10)
    ax.legend(fontsize=8.5)

    # Colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 100))
    sm.set_array([])
    cb = fig.colorbar(sm, ax=ax, fraction=0.015, pad=0.01)
    cb.set_label("Success %", fontsize=8)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig8_wrapper_heatmap.pdf"))
    fig.savefig(os.path.join(OUT, "fig8_wrapper_heatmap.png"))
    plt.close(fig)
    print("✓ fig8_wrapper_heatmap")

fig_wrapper_heatmap()


# ═══════════════════════════════════════════════════════════════════════════════
# Fig 9 — Domain coverage breakdown (stacked bar: completed vs failed per domain)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_domain_coverage():
    dom_df = df[df["domain"] != "unknown"].copy()
    dom_stats = dom_df.groupby(["domain","status"]).size().unstack(fill_value=0)
    for col in ["completed","failed","pending"]:
        if col not in dom_stats.columns:
            dom_stats[col] = 0
    dom_stats = dom_stats.sort_values("completed", ascending=True)

    fig, ax = plt.subplots(figsize=(9, 6))
    bottoms = np.zeros(len(dom_stats))
    for status, color in [("completed", PALETTE["green"]), ("failed", PALETTE["red"]), ("pending", PALETTE["orange"])]:
        vals = dom_stats[status].values
        ax.barh(dom_stats.index, vals, left=bottoms, color=color, label=status.capitalize(),
                edgecolor="white", height=0.6)
        bottoms += vals

    ax.set_xlabel("Number of runs")
    ax.set_title("Run Volume and Outcome by Domain")
    ax.legend(fontsize=9, loc="lower right")

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig9_domain_coverage.pdf"))
    fig.savefig(os.path.join(OUT, "fig9_domain_coverage.png"))
    plt.close(fig)
    print("✓ fig9_domain_coverage")

fig_domain_coverage()


# ═══════════════════════════════════════════════════════════════════════════════
# Fig 10 — Row yield: top 20 wrappers by median rows extracted
# ═══════════════════════════════════════════════════════════════════════════════
def fig_row_yield():
    yield_df = completed.groupby("wrapper_name")["row_count"].agg(
        median="median", q75=lambda x: x.quantile(0.75), q25=lambda x: x.quantile(0.25), n="count"
    ).reset_index()
    yield_df = yield_df[yield_df["n"] >= 3].sort_values("median", ascending=False).head(20)
    short = [n if len(n) <= 32 else n[:30]+"…" for n in yield_df["wrapper_name"]]

    fig, ax = plt.subplots(figsize=(9, 7))
    y_pos = range(len(yield_df))
    ax.barh(y_pos, yield_df["median"], color=PALETTE["blue"], alpha=0.85,
            edgecolor="white", height=0.6, label="Median rows")
    ax.errorbar(yield_df["median"], list(y_pos),
                xerr=[yield_df["median"]-yield_df["q25"], yield_df["q75"]-yield_df["median"]],
                fmt="none", color="#374151", linewidth=1.2, capsize=3)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(short, fontsize=8.5)
    for i, (_, row) in enumerate(yield_df.iterrows()):
        ax.text(row["median"] + 3, i, f"{row['median']:.0f}", va="center", fontsize=8)
    ax.set_xlabel("Rows extracted (median ± IQR)")
    ax.set_title("Top 20 Wrappers by Median Row Yield\n(≥3 completed runs)")

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig10_row_yield.pdf"))
    fig.savefig(os.path.join(OUT, "fig10_row_yield.png"))
    plt.close(fig)
    print("✓ fig10_row_yield")

fig_row_yield()


# ═══════════════════════════════════════════════════════════════════════════════
# Fig 11 — Wrapper topic category breakdown (inferred from domain)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_category_breakdown():
    category_map = {
        # Original domains (keys use domain() output: www. stripped)
        "en.wikipedia.org":             "Encyclopedia",
        "pubmed.ncbi.nlm.nih.gov":      "Biomedical Lit.",
        "ncbi.nlm.nih.gov":             "Genomics / Clinical",
        "arxiv.org":                    "Academic Papers",
        "github.com":                   "Software / Code",
        "stackoverflow.com":            "Dev Q&A",
        "pypi.org":                     "Python Packages",
        "news.ycombinator.com":         "Tech News",
        "clinicaltrials.gov":           "Clinical Trials",
        "catalog.data.gov":             "Open Gov Data",
        "basketball-reference.com":     "Sports Stats",
        "pro-football-reference.com":   "Sports Stats",
        "imdb.com":                     "Entertainment",
        "api.fda.gov":                  "Regulatory / FDA",
        # New bioinformatics domains
        "ebi.ac.uk":                    "Bioinformatics DB",
        "alphafold.ebi.ac.uk":          "Protein Structure",
        "uniprot.org":                  "Protein DB",
        "rcsb.org":                     "Protein Structure",
        "ensembl.org":                  "Genomics / Clinical",
        "genome.ucsc.edu":              "Genomics / Clinical",
        "flybase.org":                  "Model Organism DB",
        "wormbase.org":                 "Model Organism DB",
        "yeastgenome.org":              "Model Organism DB",
        "kegg.jp":                      "Pathways / Systems",
        "reactome.org":                 "Pathways / Systems",
        "amigo.geneontology.org":       "Pathways / Systems",
        "omim.org":                     "Genomics / Clinical",
        "ddbj.nig.ac.jp":               "Sequence Archive",
    }
    cats = defaultdict(int)
    for w in wrappers:
        dom = domain(w.get("url",""))
        cat = category_map.get(dom, "Other")
        cats[cat] += 1

    cats_sorted = dict(sorted(cats.items(), key=lambda x: x[1], reverse=True))
    pal = [PALETTE["blue"], PALETTE["green"], PALETTE["purple"], PALETTE["teal"],
           PALETTE["indigo"], PALETTE["orange"], PALETTE["pink"], PALETTE["yellow"],
           PALETTE["red"], PALETTE["gray"]]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(list(cats_sorted.keys()), list(cats_sorted.values()),
                  color=pal[:len(cats_sorted)], edgecolor="white", width=0.6)
    for bar, v in zip(bars, cats_sorted.values()):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
                str(v), ha="center", fontsize=9, fontweight="bold")
    ax.set_ylabel("Number of wrappers")
    ax.set_title("Wrapper Coverage by Topic Category")
    plt.xticks(rotation=32, ha="right", fontsize=8.5)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig11_category_breakdown.pdf"))
    fig.savefig(os.path.join(OUT, "fig11_category_breakdown.png"))
    plt.close(fig)
    print("✓ fig11_category_breakdown")

fig_category_breakdown()


# ═══════════════════════════════════════════════════════════════════════════════
# Fig 12 — Composite overview panel (paper-ready 2×3 grid)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_composite():
    fig = plt.figure(figsize=(15, 10))
    gs = GridSpec(2, 3, figure=fig, hspace=0.42, wspace=0.35)

    # A: Status donut
    ax_a = fig.add_subplot(gs[0, 0])
    r = overview["runs"]
    sizes  = [r["completed"], r["failed"], r["other"]]
    colors = [PALETTE["green"], PALETTE["red"], PALETTE["orange"]]
    wedges, _ = ax_a.pie(sizes, colors=colors, startangle=90,
                          wedgeprops=dict(width=0.45, edgecolor="white", linewidth=2))
    ax_a.text(0, 0, f"{r['success_rate_pct']}%", ha="center", va="center", fontsize=14, fontweight="bold")
    ax_a.legend([f"Completed ({r['completed']:,})", f"Failed ({r['failed']:,})", f"Other ({r['other']})"],
                loc="lower center", bbox_to_anchor=(0.5, -0.15), fontsize=7.5, ncol=1)
    ax_a.set_title("(a) Run Status", fontweight="bold")

    # B: Failure categories
    ax_b = fig.add_subplot(gs[0, 1])
    fc = overview["runs"]["failure_categories"]
    fc_s = dict(sorted(fc.items(), key=lambda x: x[1]))
    colors_b = [PALETTE["red"] if v == max(fc.values()) else "#fca5a5" for v in fc_s.values()]
    ax_b.barh(list(fc_s.keys()), list(fc_s.values()), color=colors_b, edgecolor="white", height=0.6)
    ax_b.set_xlabel("Failures", fontsize=8.5)
    ax_b.set_title("(b) Failure Causes", fontweight="bold")

    # C: Duration histogram
    ax_c = fig.add_subplot(gs[0, 2])
    dur_c = completed["duration_seconds"].dropna()
    ax_c.hist(dur_c, bins=30, color=PALETTE["teal"], edgecolor="white", alpha=0.85)
    ax_c.axvline(dur_c.mean(), color=PALETTE["red"], linestyle="--", linewidth=1.5,
                 label=f"μ={dur_c.mean():.0f}s")
    ax_c.set_xlabel("Duration (s)", fontsize=8.5)
    ax_c.set_ylabel("Runs", fontsize=8.5)
    ax_c.set_title("(c) Scrape Duration", fontweight="bold")
    ax_c.legend(fontsize=8)

    # D: Domain success rate
    ax_d = fig.add_subplot(gs[1, 0])
    dom_stats = df[df["domain"]!="unknown"].groupby("domain").agg(
        total=("status","count"), n_completed=("status", lambda x: (x=="completed").sum())
    ).reset_index()
    dom_stats["sr"] = dom_stats["n_completed"]/dom_stats["total"]*100
    dom_stats = dom_stats.sort_values("sr")
    bar_colors = [PALETTE["green"] if r>=90 else PALETTE["blue"] if r>=75 else PALETTE["orange"]
                  for r in dom_stats["sr"]]
    ax_d.barh(dom_stats["domain"], dom_stats["sr"], color=bar_colors, edgecolor="white", height=0.6)
    ax_d.axvline(overview["runs"]["success_rate_pct"], color=PALETTE["red"], linestyle="--", linewidth=1)
    ax_d.set_xlabel("Success rate (%)", fontsize=8.5)
    ax_d.set_title("(d) Domain Success Rates", fontweight="bold")
    ax_d.tick_params(axis="y", labelsize=7)

    # E: Row count histogram
    ax_e = fig.add_subplot(gs[1, 1])
    rows_c = completed["row_count"].dropna()
    ax_e.hist(rows_c, bins=35, color=PALETTE["blue"], edgecolor="white", alpha=0.85)
    ax_e.axvline(rows_c.median(), color=PALETTE["orange"], linestyle=":", linewidth=1.5,
                 label=f"med={rows_c.median():.0f}")
    ax_e.set_xlabel("Rows extracted", fontsize=8.5)
    ax_e.set_ylabel("Runs", fontsize=8.5)
    ax_e.set_title("(e) Row Count Distribution", fontweight="bold")
    ax_e.legend(fontsize=8)

    # F: Pagination success rate
    ax_f = fig.add_subplot(gs[1, 2])
    pag_stats = df.groupby("pagination").agg(
        total=("status","count"), n_c=("status", lambda x: (x=="completed").sum())
    ).reset_index()
    pag_stats["sr"] = pag_stats["n_c"]/pag_stats["total"]*100
    pag_stats = pag_stats.sort_values("sr", ascending=False)
    label_map = {"none":"None","url_increment":"URL\nIncr.","button":"Button","scroll":"Scroll","container":"Cntr."}
    pag_stats["lbl"] = pag_stats["pagination"].map(label_map).fillna(pag_stats["pagination"])
    pal_f = [PALETTE["green"], PALETTE["blue"], PALETTE["teal"], PALETTE["orange"], PALETTE["purple"]]
    ax_f.bar(pag_stats["lbl"], pag_stats["sr"], color=pal_f[:len(pag_stats)], edgecolor="white", width=0.5)
    ax_f.axhline(overview["runs"]["success_rate_pct"], color=PALETTE["red"], linestyle="--", linewidth=1)
    ax_f.set_ylabel("Success rate (%)", fontsize=8.5)
    ax_f.set_ylim(0, 110)
    ax_f.set_title("(f) Pagination vs Success", fontweight="bold")

    fig.suptitle("CroW — Evaluation Summary", fontsize=14, fontweight="bold", y=1.01)
    fig.savefig(os.path.join(OUT, "fig12_composite.pdf"))
    fig.savefig(os.path.join(OUT, "fig12_composite.png"))
    plt.close(fig)
    print("✓ fig12_composite")

fig_composite()


# ═══════════════════════════════════════════════════════════════════════════════
# Summary table as CSV (for paper tables)
# ═══════════════════════════════════════════════════════════════════════════════
def export_tables():
    # Table 1: domain-level stats
    dom_stats = df[df["domain"]!="unknown"].groupby("domain").agg(
        wrappers=("wrapper_id","nunique"),
        total_runs=("status","count"),
        completed=("status", lambda x: (x=="completed").sum()),
        failed=("status", lambda x: (x=="failed").sum()),
        avg_rows=("row_count","mean"),
        avg_dur=("duration_seconds","mean"),
    ).reset_index()
    dom_stats["success_rate_pct"] = (dom_stats["completed"]/dom_stats["total_runs"]*100).round(1)
    dom_stats["avg_rows"] = dom_stats["avg_rows"].round(1)
    dom_stats["avg_dur"]  = dom_stats["avg_dur"].round(1)
    dom_stats.to_csv(os.path.join(OUT, "table_domain_stats.csv"), index=False)
    print("✓ table_domain_stats.csv")

    # Table 2: per-wrapper summary (top 20 by total runs)
    pw = per_wrapper.nlargest(20, "total")[
        ["wrapper_name","domain","mode","n_cols","total","success_rate","avg_rows","avg_dur"]
    ].copy()
    pw["success_rate"] = pw["success_rate"].round(1)
    pw["avg_rows"]     = pw["avg_rows"].round(1)
    pw["avg_dur"]      = pw["avg_dur"].round(1)
    pw.columns         = ["Wrapper","Domain","Mode","Columns","Runs","Success%","Avg Rows","Avg Dur(s)"]
    pw.to_csv(os.path.join(OUT, "table_top_wrappers.csv"), index=False)
    print("✓ table_top_wrappers.csv")

export_tables()


print(f"\nAll charts saved to:  {OUT}/")
print("Files generated:")
for f in sorted(os.listdir(OUT)):
    print(f"  {f}")
