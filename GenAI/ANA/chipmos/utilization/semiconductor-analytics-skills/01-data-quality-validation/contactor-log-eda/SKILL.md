---
name: contactor-log-eda
description: Exploratory profile of handler contactor logs - coverage, sampling cadence, closed-count distribution, and which sites ever appear. Activate on a newly received batch of contactor CSVs or when you need to understand a date range before choosing an analysis.
---

# When to use
- First look at a new batch of front/rear contactor CSVs
- Checking whether the capture cadence (~3-4 min) and daily coverage are good enough for time-weighted metrics
- Choosing sensible thresholds (e.g. what counts as a "chronic" closed site) from the observed distribution

# Process
1. **Load via `lib/contactor_io.py`** so cleaning rules match the validation skill (run `contactor-log-validation` first if unsure).
2. **Coverage and cadence** — run `scripts/sampling_cadence_check.py` for samples per day, median/max gap, and days with holes.
3. **Closed-count distribution** — run `scripts/coverage_report.py` for per-side distribution of `n_closed` (min / p50 / p90 / max), days with all-zero, and the number of distinct sites ever closed.
4. **Compare sides** — front and rear are independent 256-site grids; note which side carries most of the closures.
5. **Record observations** against `references/eda_checklist_handler_logs.md` and write them up in `assets/eda_report_template.md`.
6. **Hand off** — list questions for the process owner (e.g. an unexplained day) before moving to `03-data-analysis-investigation`.

# Inputs the skill needs
- Required: contactor CSVs for the period
- Optional: expected capture interval (default ~4 min) and expected planned-production windows

# Output
- Console tables (cadence, coverage, distributions)
- `assets/eda_report_template.md` (filled) — one-page profile with open questions
