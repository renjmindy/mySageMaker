# CLAUDE.md

Guidance for Claude Code in this repository.

## What this repo is
25 analysis skills (Markdown + standalone-ish Python) for semiconductor test-handler utilization, organised in 6 workflow stages. Documentation/reference library plus runnable scripts on handler contactor logs.

## Validation
```bash
python validate_skills.py
```
Each `SKILL.md` needs frontmatter (`name`, `description`) and the sections `When to use`, `Process`, `Inputs the skill needs`, `Output`.

## Conventions
- Scripts: `argparse` CLIs, only `pandas`, `numpy` and stdlib; core function(s) + `main()`; run with `python -I`.
- **All data cleaning goes through `lib/contactor_io.py`** - never re-parse the CSVs in a script. Scripts add `lib/` to `sys.path` (`parents[3]` = repo root).
- Templates use `[REQUIRED]` / `[OPTIONAL]` placeholders; YAML follows dbt-semantic-layer style.
- Business parameters (UPH, margin, cost) are never defaulted - demos are labelled ILLUSTRATIVE.
- Raw data (`*.csv`, `*.zip`) and `out/` are git-ignored.

## Data rules
See `lib/contactor_io.py` docstring and `02-documentation-knowledge/analysis-assumptions-log` (A1-A20, tracked in `02-documentation-knowledge/analysis-assumptions-log/assumptions.json`; run `assumptions_tracker.py check` after changing a loader constant). Confirmed: A8 (counts 252-255 = read failure, default). Open: A11 (planned time), A13 (2x2 blocks - keep as a hypothesis, do not state a physical cause as fact), A14. Applied but not explicitly confirmed: A9, A12, A17, A18.

## Tests
`python 03-data-analysis-investigation/oee-calculator/scripts/test_oee_calculator.py` - OEE calculator unit tests (also run by `qa_runner.py`).

## Status gates
- OEE stays blocked until run-state, output, good-unit and cycle-time data exist - never report an OEE number or a "partial OEE".
- Do not run or cite `impact-quantification/scripts/cost_impact.py` (deferred) until real business parameters are supplied.
