---
name: semiconductor-metric-definitions
description: Governed definitions (dbt-semantic-layer style YAML) for site availability, time availability, OEE and chronic-site metrics for test handlers. Activate before computing any utilization number, when two reports disagree, or when extending the analysis from availability-only to full OEE.
---

# When to use
- Fixing the meaning of "utilization" before building dashboards
- Two people quote different availability numbers (weighted vs unweighted, with/without near-full rows)
- Adding Performance and Quality once output / cycle-time data become available

# Process
1. **Start from the business question** — "how much of the contactor capacity is usable?" (site availability) vs "how much of planned time did the handler produce?" (time-based OEE).
2. **Define the metric** — copy `assets/metric_definition.yaml` and fill name, formula, grain, filters, owner. See `references/oee_for_test_handlers.md` for formula variants.
3. **Fix the cleaning contract** — every metric must state which rows are valid (see `contactor-log-validation`).
4. **Validate the YAML** — run `scripts/metric_yaml_validator.py <file>` to check required keys.
5. **Reconcile** — recompute the headline number with `03-data-analysis-investigation/site-availability/scripts/site_availability.py` and compare to any dashboard value.
6. **Publish and version** — store the YAML next to the analysis; bump `version` on any rule change.

# Inputs the skill needs
- Required: the business question and decision it supports
- Required: cleaning contract (valid-row rules) and planned-time basis
- Optional: ideal cycle time, good-unit counts (needed for Performance and Quality)

# Output
- `assets/metric_definition.yaml` (filled) — one governed definition per metric
- Validator output — pass/fail per YAML file
