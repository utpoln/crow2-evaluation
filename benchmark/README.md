# CroW Extraction Benchmark — Reproducibility Package

This folder is a **real, from-scratch replacement** for the paper's original
"100-resource benchmark" claim (§8.3 in `CroW_2_2026/final.tex`). The
original claim (98.2% precision / 96.7% recall / 48,250 records) had no
surviving raw data, ground truth, or generating script anywhere in the
project — see the investigation notes at the bottom of this file. Everything
in this folder is real: real target websites, real CroW extraction runs
through the production engine, real ground truth from independent public
APIs, and a script that recomputes every number from the raw files.

**Status: 141 resources complete, spanning all 5 of the paper's target
categories, in both List Mode and Single Page Mode.** Cite the aggregate
numbers below as what they are: N=141 (118 List Mode + 23 Single Page
Mode), not a rounded "100-resource" or "150-resource" result.

## Method

1. **`resources.py`** — resource definitions. Each entry's `row_xpath` /
   `columns` (List Mode) or per-field XPaths (Single Page Mode) was
   hand-authored by loading the real page in headless Chromium and
   inspecting its actual DOM (see `inspect_dom.py`), in the same
   positional/class style a human CroW user produces via the two-click tool
   (List Mode) or the field-by-field selector picker (Single Page Mode),
   plus optional manual refinement through the Text-Based Edit Modal (all
   real, documented CroW features — see `final.tex` §5.1, §7.6). No
   selector was written without loading the real page first. 118 resources
   use List Mode (`mode: "A"`, a `row_xpath` plus column XPaths, one row per
   record); 23 use Single Page Mode (`mode: "B"`, `row_xpath: None`,
   independent absolute-XPath field selectors on a single entity/detail
   page, one record per page — 13 UniProt entry pages, 10 ClinicalTrials.gov
   study pages).

2. **`run_extraction.py`** — executes each resource through
   `wrapper.views._run_scraping_async`, the exact function CroW's production
   app calls when a user clicks "Run Extraction." This launches a real
   headless Chromium browser against the real live URL. Not a simulation.
   Output: `extracted/<resource_id>.json`, with wall-clock timing.

3. **`fetch_ground_truth.py`** — fetches reference records from an official
   public API, independent of CroW's own extraction path:
   - PubMed resources → NCBI E-utilities (`esearch` + `esummary`)
   - ClinicalTrials.gov (list) → ClinicalTrials.gov API v2 search endpoint
   - ClinicalTrials.gov (single study) → ClinicalTrials.gov API v2 study endpoint
   - UniProt (list) → UniProt REST API search endpoint
   - UniProt (single entry) → UniProt REST API entry endpoint
   - NCBI Gene → NCBI E-utilities (`esearch` + `esummary`, db=gene)
   - MedlinePlus (disease topics) → MedlinePlus `wsearch` web service (`db=healthTopics`)

   Output: `ground_truth/<resource_id>.json`.

4. **`compute_metrics.py`** — the script a reviewer should rerun. Loads the
   raw extracted/ and ground_truth/ files and branches on mode: List Mode
   resources are matched by a natural key (PMID, NCT ID, UniProt accession,
   URL) as **sets, order-independent**; Single Page Mode resources are
   matched **field by field** (no key — one record per page) with
   whitespace/zero-width-space normalization. Computes precision/recall/F1
   per resource either way. Output: `results.csv`.

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

## Current results (N=141)

Mean across 141 resources: **precision=99.3%, recall=99.3%, F1=99.3%, mean
runtime=7.2s, 1,764 total records.** Category counts: 29 biomedical_search,
36 clinical, 34 protein, 20 genomic, 22 disease databases. By mode: List
Mode (118 resources) precision=99.3%/recall=99.2%/F1=99.3%; Single Page
Mode (23 resources) precision=100.0%/recall=100.0%/F1=100.0%. Full detail
(including TP/FP/FN per resource) is in `results.csv` — regenerate it from
there; don't hand-edit this table. Run `python generate_figures.py` after
any `results.csv` change to regenerate the three figures copied into
`CroW_2_2026-2/` for the paper.

131 of 141 resources scored a clean 100%. The 10 exceptions are all List
Mode and share one root cause: a fixed top-N cutoff against a live,
relevance-ranked index that can shift slightly between the extraction call
and the (separately timed) ground-truth call. `ncbi_gene_myc` (90%, 2 false
positives, 2 false negatives at the top-20 cutoff) was investigated rather
than discarded: the "extra" IDs CroW extracted (MTOR, MYCBP2) and the
"missing" IDs (two distinct gene entries both named MYC, IDs
731404/729194) are all real, valid NCBI Gene records — confirmed by
querying esummary for each ID directly. The nine MedlinePlus disease-topic
exceptions (diabetes, hypertension, asthma, osteoporosis, malaria,
pneumonia, rheumatoid arthritis, obesity, stroke — each off by 1-3 records
out of 10) show the same pattern: MedlinePlus's federated relevance search
re-ranks between successive queries, so a fixed `retmax=10` cutoff can
include or exclude different records depending on exact query timing. This
is the live-data non-atomicity caveat below in action, not an extraction
defect. Recorded here as a concrete example, not smoothed over.

## Disease-database category: dead ends recorded for posterity

The disease-databases category (now covered by 22 MedlinePlus health-topic
resources — see `resources.py`'s `medlineplus()` template) went through
several failed attempts on other portals before landing on MedlinePlus.
Recorded here so a future session doesn't repeat the same dead ends:

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
- **OMIM** — HTTP 403 (bot-blocked). Consistent with the paper's own text
  elsewhere describing OMIM's "aggressive bot-detection" — a real,
  corroborating data point, not just a benchmark gap.
- **GARD (rarediseases.info.nih.gov)** — 200 OK but 0 matches on every
  selector guessed; page structure not yet inspected via DevTools.
- **NCBI's OMIM mirror** (`ncbi.nlm.nih.gov/omim`) and **MeSH**
  (`ncbi.nlm.nih.gov/mesh`) — both 0 `tr.rprt` matches.
- **DisGeNET** now requires login/a paid plan for search results (its
  public free-search UI appears to have been retired), and **ChEMBL**'s EBI
  search interface returned 0 matches on every selector guess, likely
  another client-side-rendered results panel that needs DevTools
  inspection rather than blind guessing, same as RCSB/GARD.

**What worked:** MedlinePlus's `vsearch.nlm.nih.gov` Vivisimo-based search
UI paired with the independent `wsearch.nlm.nih.gov/ws/query` API — but
only after discovering the website's default search is a *federated*
meta-search across multiple NLM sources while the API's `db=healthTopics`
only searches one; see `binning-state=group==Health Topics` in
`resources.py`'s `medlineplus()` for the fix (restricts the website to the
same single source as the API).

## What's still missing

- **A real ScrapeGraphAI comparison run** (for the cost/timing/precision
  table in §8.5 of the paper) has not been attempted yet — needs
  `scrapegraphai` installed and a real API key exercised, with costs
  logged.

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
