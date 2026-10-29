# Code Review for Analysis Code

- Cleaning logic lives only in `lib/contactor_io.py`; no script re-parses the CSV files or re-implements a rule. (The one deliberate exception is `scripts/independent_recompute.py` in this skill, whose job is to re-implement the rules independently; it must never be imported by other code.)
- Every script that applies the cleaning rules and reports a number accepts `--data-dir`, `--start` and `--near-full-min`. Scripts that must see unclean data (the EDA and validation scripts, `data_gate.py`) may omit `--near-full-min`; the reviewer lists any other script that lacks a flag as a finding.
- No hard-coded private paths and no business parameters (cost, units per hour, margin) with defaults; demos are labelled illustrative.
- Output is deterministic (a fixed seed for the bootstrap) and `python -I` runs clean.
- A check that guards a number has a negative test that breaks the real artifact (the lesson behind the learnings log, class blind-check).
