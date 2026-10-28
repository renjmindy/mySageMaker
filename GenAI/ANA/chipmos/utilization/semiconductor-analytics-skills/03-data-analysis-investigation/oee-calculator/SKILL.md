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
3. **Performance (P)** — output x ideal cycle time / run minutes, where `ideal_cycle_min` is minutes per unit at the handler level with **all sites open**. Closed sites therefore lower P through lower output; `--site-availability` only decomposes P into a site-capacity part and a speed part and never changes OEE (see `references/oee_scenarios.md`).
4. **Quality (Q)** — good / total.
5. **Combine** — `scripts/oee_calculator.py` returns one of three statuses: **BLOCKED** (a factor is missing: no number, no partial product), **INVALID** (impossible input: negative values, good > output, run > planned, planned = 0, output without run time, Performance > 100%; exit code 2) or **OK**. A zero is a value, not "missing". An OK result is self-checked: OEE must equal good x ideal cycle / planned.
6. **Sanity-check** — `--demo` reproduces the guide's simulator example (400/480 min, 380 out, 370 good = 77.1%); those are illustrative numbers from a screenshot, not handler data, and the 1.0 min ideal cycle is back-solved. Run `scripts/test_oee_calculator.py` after any change.
7. **Fill `assets/oee_report_template.md`** with completeness and caveats.

# Inputs the skill needs
- Required (today): site availability per side
- Required (for full OEE): run/idle/down minutes, planned downtime, output, good output, ideal cycle time
- Optional: production calendar and lot types (exclude engineering/trial lots)

# Output
- Console: A, P, Q and either OEE, `BLOCKED (missing ...)` or `INVALID` with the errors
- `scripts/test_oee_calculator.py` — unit tests (blocked, invalid, zero, identity, decomposition cases)
- `assets/oee_report_template.md` (filled)
