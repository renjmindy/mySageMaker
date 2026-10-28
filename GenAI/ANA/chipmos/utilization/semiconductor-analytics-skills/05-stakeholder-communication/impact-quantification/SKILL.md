---
name: impact-quantification
description: DEFERRED until real business parameters are supplied. Convert recoverable site availability into capacity and money with explicit assumptions and uncertainty. Activate when a maintenance request, contactor replacement or automation investment needs a business case.
---

# Status: DEFERRED
Not used at this stage. Do not run `scripts/cost_impact.py` or quote its output until real units/hour per site and margin per unit are supplied; the script never defaults them and its `--demo` numbers are illustrative only.

# When to use
- Justifying replacing contactor clusters
- Estimating the value of reaching a target availability
- Comparing options by recovered units per hour

# Process
1. **Pick the recoverable sites** from `chronic-site-detection` (clusters).
2. **Compute site-equivalents recovered** — time-weighted number of those sites closed (`scripts/cost_impact.py --recover-sites ...`).
3. **Convert to capacity** — recovered units/hour = site-equivalents x units/hour per site (supplied, not guessed).
4. **Convert to value** — x operating hours x margin per unit; subtract fix cost.
5. **Add uncertainty** — use the availability range (list vs count-based) and `--scenario low|high`.
6. **Document assumptions** (`references/assumption_documentation.md`) and link ids.
7. **Fill `assets/business_case_template.md`**.

# Inputs the skill needs
- Required: sites to recover and period (from the data)
- Required (user-supplied, not available in the logs): units/hour per site, operating hours, margin per unit, repair cost
- Optional: probability the repair holds

# Output
- Console: site-equivalents, capacity gain, value range
- `assets/business_case_template.md` / `assets/impact_estimate_template.md` (filled)
