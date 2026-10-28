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
3. **Fix the cleaning contract** — the `contract:` block lists valid and dropped statuses and the loader constants (252, 50, 15 min) and cites assumption ids; it must equal `lib/contactor_io.py`.
4. **Validate the YAML** — run `scripts/metric_yaml_validator.py --recompute`: checks required keys, placeholder owners (FAIL for `[REQUIRED]`, WARN for `[OPEN]`), changelog for version > 1, contract vs loader, known assumption ids, and recomputes availability independently of `site_availability.py`. The QA runner runs the same check.
5. **Reconcile** — `--recompute` compares the formula with `site_availability.py`; also compare to any dashboard value. Report the range (`site_availability_low` to `site_availability`) and the combined view only next to the per-side figures.
6. **Publish and version** — bump `version` and add a `changelog` entry on any rule change (the validator enforces this); name a real owner to clear the `[OPEN]` warnings.

# Inputs the skill needs
- Required: the business question and decision it supports
- Required: cleaning contract (valid-row rules) and planned-time basis
- Optional: ideal cycle time, good-unit counts (needed for Performance and Quality)

# Output
- `assets/metric_definition.yaml` (filled) — one governed definition per metric
- Validator output — pass/fail per YAML file
