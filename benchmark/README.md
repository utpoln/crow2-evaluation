# CroW Extraction Benchmark — Reproducibility Package

This folder is a **real, from-scratch replacement** for the paper's original
"100-resource benchmark" claim (§8.3 in `CroW_2_2026/final.tex`). The
original claim (98.2% precision / 96.7% recall / 48,250 records) had no
surviving raw data, ground truth, or generating script anywhere in the
project — see the investigation notes at the bottom of this file. Everything
in this folder is real: real target websites, real CroW extraction runs
through the production engine, real ground truth from independent public
APIs, and a script that recomputes every number from the raw files.

**Status: 96 of a planned ~100 resources complete, spanning 4 of the
paper's 5 categories.** This is an honest, in-progress replacement, not a
finished benchmark. Do not cite the aggregate numbers below as a rounded
"100-resource" result — cite them as what they are: N=96, with disease
databases still uncovered (see below for why, and what to try next).

## Method

1. **`resources.py`** — resource definitions. Each entry's `row_xpath` /
   `columns` was hand-authored by loading the real page in headless
   Chromium and inspecting its actual DOM (see `inspect_dom.py`), in the
   same positional/class style a human CroW user produces via the two-click
   tool plus optional manual refinement through the Text-Based Edit Modal
   (both real, documented CroW features — see `final.tex` §5.1, §7.6). No
   selector was written without loading the real page first.

2. **`run_extraction.py`** — executes each resource through
   `wrapper.views._run_scraping_async`, the exact function CroW's production
   app calls when a user clicks "Run Extraction." This launches a real
   headless Chromium browser against the real live URL. Not a simulation.
   Output: `extracted/<resource_id>.json`, with wall-clock timing.

3. **`fetch_ground_truth.py`** — fetches reference records from an official
   public API, independent of CroW's own extraction path:
   - PubMed resources → NCBI E-utilities (`esearch` + `esummary`)
   - ClinicalTrials.gov → ClinicalTrials.gov API v2
   - UniProt → UniProt REST API

   Output: `ground_truth/<resource_id>.json`.

4. **`compute_metrics.py`** — the script a reviewer should rerun. Loads the
   raw extracted/ and ground_truth/ files, matches records by a natural key
   (PMID, NCT ID, UniProt accession) as **sets, order-independent**, and
   computes precision/recall/F1 per resource. Output: `results.csv`.

To reproduce end to end:
```bash
python fetch_ground_truth.py   # hits live public APIs
python run_extraction.py       # hits live CroW engine against live websites
python compute_metrics.py      # pure computation from the two JSON dumps above
```

## A methodological trap we hit and fixed (kept here for transparency)

The first pass showed near-0% precision/recall for the PubMed and
ClinicalTrials.gov resources. This was **not** a CroW extraction failure —
it was a bug in the ground-truth fetcher: it requested NCBI E-utilities with
an invalid `sort=pub+date` parameter (silently ignored, falling back to a
different default ordering) and ClinicalTrials.gov's API v2 with no `sort`
parameter (which defaults differently from the website's own Table view,
which defaults to relevance). Once the ground-truth fetcher was corrected to
use the same sort semantics as the live website (`sort=most+recent` for
PubMed's "sort=date" URLs, `sort=@relevance` for ClinicalTrials.gov, which
is the website's default), all 5 resources matched at 100%. This is
recorded here because it's exactly the kind of error a reviewer re-running
this package might also hit, and because it's a good example of why
ground-truth methodology needs to be nailed down before trusting a
precision/recall number, in either direction.

**Live-data caveat:** ground truth and extraction are not fetched
atomically. For "most recent" queries, a paper published in the gap between
the two calls could shift the true top-N by one position. This is a
property of benchmarking against a live, real-time source, not a
methodology flaw — but it means exact reproduction at a later date may show
small (not systematic) differences for date-sorted queries.

## Current results (N=96)

Mean across 96 resources: **precision=99.9%, recall=99.9%, F1=99.9%, mean
runtime=7.2s, 1,475 total records.** Category counts: 29 biomedical_search,
26 clinical, 21 protein, 20 genomic, 0 disease databases. Full detail
(including TP/FP/FN per resource) is in `results.csv` — regenerate it from
there; don't hand-edit this table. Run `python generate_figures.py` after
any `results.csv` change to regenerate the three figures copied into
`CroW_2_2026/` for the paper.

95 of 96 resources scored a clean 100%. The one exception,
`ncbi_gene_myc` (90%, 2 false positives, 2 false negatives at the top-20
cutoff), was investigated rather than discarded: the "extra" IDs CroW
extracted (MTOR, MYCBP2) and the "missing" IDs (two distinct gene entries
both named MYC, IDs 731404/729194) are all real, valid NCBI Gene records —
confirmed by querying esummary for each ID directly. This is the live-data
non-atomicity caveat below in action: ground truth and extraction are two
separate live API/browser calls made minutes apart during a large
sequential run, and MYC's result set is large and volatile enough that the
top-20 boundary shifted slightly in that window. Recorded here as a
concrete example, not smoothed over.

## What's still missing before this can replace §8.3 in the paper

- **Category not yet covered: disease databases** (4 of 5 categories done).
  Nine real attempts this round, all recorded so a future session doesn't
  repeat the same dead ends:
  - **RCSB PDB** — results load via a client-side call whose container
    wasn't found after multiple selector guesses; needs DevTools network
    inspection to find the real result container, not more blind guessing.
  - **Ensembl** (`Multi/Search/Results`) — zero matches for every selector
    tried; URL or page structure may have changed.
  - **ClinVar** — row data has no visible-text unique ID; NCBI's classic
    `tr.rprt` docsum layout doesn't apply here. Matching would need the
    row's `data-uid` attribute (not extractable — CroW's engine only reads
    `text_content()`) or the free-text variant name as key, and even then
    the esearch/esummary IDs didn't line up with the page's ordering the
    way they did for Gene and PubMed.
  - **MedGen** — 0 `tr.rprt` matches (NCBI has apparently retired this UI
    template for most databases; Gene is the exception, not the rule).
  - **MedlinePlus** — guessed search URL returned 404.
  - **OMIM** — HTTP 403 (bot-blocked). Consistent with the paper's own text
    elsewhere describing OMIM's "aggressive bot-detection" — a real,
    corroborating data point, not just a benchmark gap.
  - **GARD (rarediseases.info.nih.gov)** — 200 OK but 0 matches on every
    selector guessed; page structure not yet inspected via DevTools.
  - **NCBI's OMIM mirror** (`ncbi.nlm.nih.gov/omim`) and **MeSH**
    (`ncbi.nlm.nih.gov/mesh`) — both 0 `tr.rprt` matches.

  Two more attempts, same session: **DisGeNET** now requires login/a paid
  plan for search results (its public free-search UI appears to have been
  retired — "Book a Demo" / "Pricing" nav present, no results without
  auth), and **ChEMBL**'s EBI search interface returned 0 matches on every
  selector guess, likely another client-side-rendered results panel that
  needs DevTools inspection rather than blind guessing, same as RCSB/GARD.

  Best remaining candidates, in priority order: OMIM with a registered
  free API key (avoids the bot-block entirely), or revisiting
  RCSB/GARD/ChEMBL with actual browser DevTools network-tab inspection to
  find the real results endpoint rather than guessing CSS classes blind.
- N=96 is close to a "100-resource" target but disease databases remain
  fully uncovered. Additional candidate real, real-API-backed targets to
  grow N further within the four working categories: NCBI Nucleotide
  (E-utilities), KEGG (REST API), AmiGO/Gene Ontology (API), FlyBase,
  WormBase, SGD, DDBJ, AlphaFold, more PubMed/ClinicalTrials.gov/UniProt
  queries (fast — reuses proven selectors), arXiv (structural issue found:
  records are `dt`/`dd` sibling pairs, not single repeated containers —
  CroW's List Mode can't target these directly; a genuine limitation worth
  documenting, not a benchmark target to force).
- A real ScrapeGraphAI comparison run (for the cost/timing/precision table
  in §8.5) has not been attempted yet — needs `scrapegraphai` installed and
  the OpenAI key in `.env` exercised for real, with costs logged.
- Once a larger N is reached, `final.tex` Tables `dataset_summary` /
  `overall_results` and Figures `fig:category_distribution`,
  `fig:precision_recall`, `fig:creation_time`, `fig:runtime_records` all
  need to be regenerated from `results.csv`, and the "100 resources"
  language throughout the paper needs to match whatever N is actually
  reached — or the claim needs to be explicitly scoped down.

## Original investigation notes (why this folder exists)

- `run_results/` at the project root: 199 numbered directories, every one
  empty.
- No ground-truth file, no per-resource result file, and no script
  computing precision/recall/F1/cost existed anywhere in the codebase.
- The live database has exactly 100 `Wrapper` rows: 99 public (the
  synthetic seeded corpus from `seed_eval_data.py`, unrelated to this
  benchmark) and 1 private one-off test wrapper. No separate 100-resource
  benchmark corpus exists in the database.
- `fig_precision_recall.png` etc. are genuine Matplotlib output (confirmed
  via embedded file metadata) but the script and data that produced them are
  not present in the project.
- `reviewer_export/` (checked first, on the hypothesis it might hold this
  data) turned out to be the synthetic seeded corpus, confirmed by its own
  `README.txt` and by finding template-repeating record patterns in
  `runs/results/*.json` (e.g., the same 10 gene records tiled to reach a
  count of 100 — not something a real scrape produces).
