---
name: analysis-qa-checklist
description: QA gate for the handler utilization analysis before results are shared - a data gate that catches faults in the CSVs (missing or duplicate days, bad format, time zone, swapped sides, unreviewed bad days, data going backwards, headline jumps), repo-health checks, headline reconciliation across every deliverable, waivers with owners and expiry, and a recorded sign-off. Activate before every release of numbers, dashboards or summaries.
---

# When to use
- Before sending any availability/OEE number outside the analytics team
- After new data arrives, or after changing cleaning rules, the loader or the date range
- As a quality gate in the scheduled pipeline

# Process
1. **Run `scripts/qa_runner.py`** (`--data-only` for just the data, `--with-doc-check` to also re-run the analysis document's commands). Data gate checks: format (the loader raises on a missing column), documented scope (A6), no missing or duplicate days, reading days match file days (time zone), every day with >= 5% dropped readings or < 75% coverage recorded with a decision in the validation report, site IDs belong to the side, the unflagged near-full band (A14), dropped-reading rate, data not going backwards versus the last release, headline move versus the last release (> 1.5 pts needs an explanation). Repo-health checks: unit tests and checks of every other skill, assumptions log and metric definitions versus the loader, and the headline reconciled across the analysis document, insight brief, executive summary, dashboard and HTML report. Exit code 1 only on FAIL.
2. **Handle every WARN** — fix it, or waive it in `qa_waivers.json` with a reason, an owner and an expiry date. A waived WARN shows as WAIVED; an expired waiver brings the WARN back; a new WARN without a waiver stands out. A FAIL is never waived.
3. **Know what each check is** — most `loader guards` only fail if the loader itself is broken (regression guards); the data checks above are what detect problems in the data. `references/common_analysis_errors.md` maps each common error to the check that catches it.
4. **Walk the manual checklist** `references/qa_checklist_master.md`; each item says whether it is automated or needs a person.
5. **Record the release baseline** after sign-off: `qa_runner.py --update-baseline` writes `release_baseline.json` (data end, rows, headline per side) that the next run compares against.
6. **Sign off** in `assets/qa_signoff_template.md` (see `assets/qa_signoff_sep_oct_2026.md`): automated results, waivers, fault-injection evidence, manual checklist, reconciliation, open items, analyst and a *different* reviewer.

# Inputs the skill needs
- Required: the contactor CSV folder, the validation report (decisions for flagged days) and the numbers about to be published
- Required: `release_baseline.json` from the previous release (a missing baseline is a WARN)
- Optional: waivers in `qa_waivers.json`

# Output
- Console PASS / WARN / WAIVED / FAIL table and exit code
- `scripts/data_gate.py` (data checks, waivers, reconciliation) and `scripts/test_data_gate.py` (16 fault-injection tests on synthetic data: missing day, failed day, duplicates, renamed header, non-numeric count, swapped sides, unflagged band, time-zone shift, stale data, wrong start, headline jump, waivers, reconciliation)
- `assets/qa_signoff_template.md` (template) and `assets/qa_signoff_sep_oct_2026.md` (filled; reviewer still open)
