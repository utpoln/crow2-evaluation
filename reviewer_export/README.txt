CroW Evaluation Dataset — Reviewer Export
==========================================

This folder contains the full evaluation dataset for CroW (Configurable
Robot for the Web), a no-code web data extraction platform.

Contents
--------
wrappers/           JSON config files for all 70 public wrappers.
                    Each file contains: name, URL, mode, pagination type,
                    column definitions, and URL parameters.

runs/summary.csv    A CSV file with all 1467 scrape runs, including:
                    run_id, wrapper_name, status, row_count, duration,
                    started_at, error_message.

runs/results/       JSON result files for completed runs.
                    Format: {"count": N, "data": [{"col": "val", ...}, ...]}

stats/overview.json Aggregate statistics across all wrappers and runs.

Dataset Summary
---------------
Total public wrappers : 70
Total scrape runs     : 1467
  Completed           : 1110
  Failed              : 341
  Other (running/pending): 16
Unique domains        : 14
Pagination types seen : button, container, none, scroll, url_increment
Export date           : 2026-06-22 08:42 UTC

Contact
-------
For questions about this dataset, contact: kallolnaha@gmail.com
