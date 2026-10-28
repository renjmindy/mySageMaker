---
name: oee-calculator
description: Compute handler OEE (Availability x Performance x Quality) once run-state, output, good-unit and cycle-time data exist; until then it reports BLOCKED and which inputs are missing. Activate when stakeholders ask for "utilization" as time-based OEE.
---

# Status: BLOCKED
OEE is **not reported** until run-state, output, good-unit and cycle-time data exist. No partial OEE number is produced; site availability from the contactor logs is a capacity factor, not OEE.

# When to use
- Producing an OEE figure or a placeholder with an honest completeness label
- Demonstrating the OEE formula with the doc example (77.1%)
- Integrating site availability once run-state, output and good-unit data arrive

# Process
1. **Check inputs** — run-state minutes (for time availability), total/good output, ideal cycle time. List which are missing.
2. **Time availability (A)** — run minutes / (total minutes - planned downtime). If missing, state "blocked".
3. **Performance (P)** — output x ideal cycle time / run minutes; fold in site capacity via effective parallelism = site availability (see `references/oee_scenarios.md`).
4. **Quality (Q)** — good / total.
5. **Combine** — `scripts/oee_calculator.py`; the script reports OEE only when A, P and Q are all supplied; otherwise it prints `OEE: BLOCKED` with the missing inputs.
6. **Sanity-check** — reproduce the doc demo (400/480 min, 380 out, 370 good = 77.1%).
7. **Fill `assets/oee_report_template.md`** with completeness and caveats.

# Inputs the skill needs
- Required (today): site availability per side
- Required (for full OEE): run/idle/down minutes, planned downtime, output, good output, ideal cycle time
- Optional: production calendar and lot types (exclude engineering/trial lots)

# Output
- Console: A, P, Q and either OEE or `BLOCKED (missing ...)`
- `assets/oee_report_template.md` (filled)
