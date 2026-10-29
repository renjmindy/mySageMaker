---
name: impact-quantification
description: DEFERRED until real business parameters are supplied. Convert the capacity that is closed now into units and money with explicit parameters, a low/mid/high range and a repair-holds probability. Activate only after status.json is lifted - for a maintenance request, contactor replacement or automation business case.
---

# Status: DEFERRED
`status.json` says `"deferred": true`. While it does, **no deliverable may quote money, margin, payback or units-per-hour figures**: the executive summary, insight brief and dashboard spec checkers and the QA gate fail on them (`lib/deferral.py`). `scripts/cost_impact.py` prints only a deferral notice when run bare, refuses to run without every business parameter, and its `--demo` output is labelled ILLUSTRATIVE and must never be quoted. Lifting the deferral is an explicit edit of `status.json` after the parameters below exist with a source, owner and date.

# When to use
- (After the deferral is lifted) justifying replacing contactor groups
- Estimating the value of reaching a target capacity
- Comparing options by recovered units per hour

# Process
1. **Pick the groups closed now** from `chronic-site-detection` (recency statuses PERSISTENT, NEW, CURRENT); a group that was fixed is history and has no value to recover.
2. **Count site-equivalents from the current state** — `cost_impact.py` uses the last 3, 7 and 14 days (low = fewest, mid = 7 days, high = most). The whole-period average is printed as history only: a forward decision needs what is lost now (for the front group 197-246 the period average understated the current loss by about a quarter).
3. **Require every business parameter, no defaults** — units per hour per site, hours per day, margin per unit, days, repair cost, **whether the handler is capacity-constrained**, the probability the repair holds, repair downtime days and sites offline during repair. A zero is legitimate only when stated explicitly. Each parameter needs a source, owner and date (`references/assumption_documentation.md`).
4. **Apply the constraint** — if the handler is not capacity-constrained, extra sites add no output (idle capacity absorbs the loss): only the repair cost remains.
5. **Compute value with the formula in `references/impact_quantification_framework.md`** — gross = gain x hours x days x margin x P(repair holds); minus downtime loss and repair cost. Report low / mid / high, never one figure.
6. **Reconcile and backtest** — recovered capacity must not exceed the handler's capacity and must reconcile with real output counts; test the method on a past repair (e.g. the rear reopening on 09/21-22): did output rise?
7. **Document** in `assets/business_case_template.md` with assumption ids; have finance approve the margin.

# Inputs the skill needs
- Required: the groups and the data (through `lib/contactor_io.py`, current windows)
- Required (user-supplied; nothing in the logs): all nine business parameters above, each with source, owner, date
- Optional: a past repair with output data for the backtest

# Output
- `status.json` (the machine-readable deferral) and `lib/deferral.py` (the guard the checkers call)
- Console (when run with real parameters): site-equivalents per window, low / mid / high gain, gross, downtime, repair cost and net
- `scripts/test_cost_impact.py` (14 unit tests on symbolic numbers and a synthetic dataset)
- `assets/business_case_template.md` / `assets/impact_estimate_template.md` (filled only after the deferral is lifted)
