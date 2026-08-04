# CroW 2.0 — Evaluation & Chart Artifacts

This repository holds the evaluation data, ground truth, and chart-generation
code referenced by the CroW 2.0 paper. **It is a data/evaluation artifact
release, not the CroW application source code.** The platform source is not
included here.

It contains two independent things. Don't confuse them — they measure
different claims in the paper.

## 1. `benchmark/` — real, controlled extraction-quality benchmark (§8.3)

A real benchmark of scientific web resources (currently N=96, in progress
toward ~100), executed through CroW's production extraction engine against
live websites, checked against ground truth fetched independently from each
portal's own public API (NCBI E-utilities, ClinicalTrials.gov API v2,
UniProt REST API). Every number in the paper's Table 2/3 and Figures
10–12 is recomputed from the raw files here.

**What you can rerun yourself, with nothing else installed but this repo's
Python dependencies:**
```bash
cd benchmark
python fetch_ground_truth.py   # hits live public APIs, writes ground_truth/*.json
python compute_metrics.py      # pure computation from extracted/ + ground_truth/, writes results.csv
python generate_figures.py     # regenerates the 3 paper figures from results.csv
```

**What you cannot rerun from this repo alone:** `run_extraction.py` calls
`wrapper.views._run_scraping_async`, the CroW application's real extraction
engine. That application's source is not included in this repository, so
`run_extraction.py` will not execute here — it's included for transparency
(to show exactly what was called and how) and as documentation of the
method, not as a self-contained reproduction step. The `extracted/*.json`
files it already produced are included, so `compute_metrics.py` still
reproduces every reported precision/recall/F1 number without needing to
re-run extraction.

See `benchmark/README.md` for full methodology, current status, known
limitations (disease-database category not yet covered), and a record of
failed attempts at sites we couldn't yet integrate.

## 2. `generate_charts.py` + `reviewer_export/` — seeded operational corpus (§8.4)

A **synthetic** corpus (100 seeded wrapper configs, 1,352 generated run
records) used in the paper only to validate the repository, run-history, and
charting pipeline at scale — explicitly *not* evidence of real-world
extraction reliability (see §8.4 of the paper for the full disclaimer).
`reviewer_export/` is the raw seeded data; `generate_charts.py` reads it and
produces the corresponding figures.

```bash
pip install numpy pandas matplotlib seaborn
python generate_charts.py
# writes figures to ./charts/
```

This script has no dependency on the CroW application — it only reads the
CSV/JSON files under `reviewer_export/`.

## Scope

This repository intentionally does not include: the CroW Django application
source, wrapper induction/selector code, deployment configuration, or
credentials. It is the evaluation and reproducibility layer only.

## Citation

If you use this data, please cite the CroW 2.0 paper (Naha and Jamil,
preprint submitted to Elsevier).
