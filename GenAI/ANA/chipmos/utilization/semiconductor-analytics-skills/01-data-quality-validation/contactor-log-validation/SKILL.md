---
name: contactor-log-validation
description: Validate handler contactor-site logs (closed-site count + closed-site ID list, front/rear) before any utilization metric is computed. Activate when new contactor_*.csv files arrive, when a daily availability number looks implausible, or when OCR/screen-read noise is suspected in site IDs.
---

# When to use
- New `contactor_YYYYMMDD.csv` / `contactor_rear_YYYYMMDD.csv` files landed from the handler screen-capture pipeline
- A day's closed-site count jumps (e.g. 20 -> 75) and you must decide: real event or bad reads?
- Before feeding site-level data into availability / OEE calculations
- After changing the screen-capture/OCR step, to confirm noise did not get worse

# Process
1. **Load through the shared loader** — always use `lib/contactor_io.py`; never re-parse CSVs ad hoc. It applies the confirmed rules in `references/log_semantics.md` (256 and 252-255 = read failure, `N/A`+0 = zero closed, count exceeding list length by > 50 = unreadable list, list length beats count, side ID ranges).
2. **Detect read failures** — run `scripts/read_failure_detector.py`. Reports per-day rate of `READ_FAIL_256`, `READ_FAIL_NEAR_FULL`, `READ_FAIL_GAP` and `NA_NONZERO` rows. A day above 5% failures is flagged for manual review of the source screenshots.
3. **Validate site IDs** — run `scripts/site_id_validator.py`. Counts out-of-range IDs (front must be 1-256, rear 257-512) and duplicate IDs per row; lists the most frequent garbage tokens from rows that are kept (rows dropped as read failures are excluded, otherwise they dominate the ranking). Treat the pattern as a lead for the capture owner, not a diagnosis - confirm against screenshots.
4. **Reconcile count vs list** — run `scripts/count_list_reconciler.py`. Quantifies rows where `err_01 != len(list)`; list length is authoritative. Large systematic offsets point to a parsing bug, not noise.
5. **Classify severity** — use `references/validation_rules.md` thresholds (CRITICAL / HIGH / MEDIUM / LOW) per day and per side.
6. **Decide on suspicious days** — for days flagged HIGH+, compare front vs rear and neighbouring days; a real handler event shows on a stable set of sites, noise does not.
7. **Produce the report** — fill `assets/validation_report_template.md`.

# Inputs the skill needs
- Required: contactor CSVs (`Timestamp,err_01,err_02`), front and/or rear
- Required: date range to analyse (default 2026-09-01 onward; the 07/30 trial run is excluded)
- Optional: failure-rate thresholds if the defaults in `references/validation_rules.md` do not fit
- Optional: source screenshots for manual spot checks of flagged days

# Output
- Console tables from each script (per-day failure / noise rates)
- `assets/validation_report_template.md` (template) and `assets/validation_report_sep_oct_2026.md` (filled for Sep-Oct 2026) — go/no-go per day and side, with the exclusion list handed to the analysis skills
