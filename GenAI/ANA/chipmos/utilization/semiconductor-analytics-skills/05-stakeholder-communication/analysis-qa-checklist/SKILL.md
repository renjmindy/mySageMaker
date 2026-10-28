---
name: analysis-qa-checklist
description: Automated and manual QA gate for the handler utilization analysis before results are shared - data scope, cleaning rules, metric sanity, sensitivity and communication checks. Activate before every release of numbers, dashboards or summaries.
---

# When to use
- Before sending any availability/OEE number outside the analytics team
- After changing cleaning rules, the loader or the date range
- As a quality gate in the scheduled pipeline

# Process
1. **Run `scripts/qa_runner.py`** — executes the automated checks and returns exit code 1 on FAIL.
2. **Review WARNs** — each needs a written justification or a fix.
3. **Walk the manual checklist** `references/qa_checklist_master.md` (definitions, front/rear labelling, caveats shown, numbers match across deliverables).
4. **Check common errors** `references/common_analysis_errors.md` (e.g. counting read failures as closures, mixing time-based and site-based availability).
5. **Reconcile numbers** across report, dashboard and summary to the same decimal.
6. **Sign off** in `assets/qa_signoff_template.md` (analyst + reviewer).

# Inputs the skill needs
- Required: the contactor CSV folder and the numbers about to be published
- Optional: previous release's numbers to compare

# Output
- Console PASS/WARN/FAIL table and exit code
- `assets/qa_signoff_template.md` (filled)
