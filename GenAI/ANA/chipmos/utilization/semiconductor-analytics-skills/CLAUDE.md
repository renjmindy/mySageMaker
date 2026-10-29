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
See `lib/contactor_io.py` docstring and `02-documentation-knowledge/analysis-assumptions-log` (A1-A20, tracked in `02-documentation-knowledge/analysis-assumptions-log/assumptions.json`; run `assumptions_tracker.py check` after changing a loader constant). Confirmed: A8 (counts 252-255 = read failure, default). Open: A11 (planned time), A13 (2x2 blocks - keep as a hypothesis, do not state a physical cause as fact), A14. Applied but not explicitly confirmed: A9, A12, A17, A18, A19, A20.

## Tests
`python 05-stakeholder-communication/analysis-qa-checklist/scripts/test_data_gate.py` (fault injection on synthetic data), `python 05-stakeholder-communication/impact-quantification/scripts/test_cost_impact.py`, `python 05-stakeholder-communication/methodology-explainer/scripts/test_methodology_check.py`, `python 05-stakeholder-communication/technical-to-business-translator/scripts/test_translator.py`, `python 05-stakeholder-communication/stakeholder-requirements-gathering/scripts/test_requirements_check.py`, `python 06-workflow-optimization/analysis-planning/scripts/test_plan_check.py`, `python 06-workflow-optimization/analysis-retrospective/scripts/test_learnings_check.py`, `python 06-workflow-optimization/context-packager/scripts/test_context_check.py`, `python 06-workflow-optimization/peer-review-template/scripts/test_review_check.py`, `python 03-data-analysis-investigation/oee-calculator/scripts/test_oee_calculator.py`, `python 03-data-analysis-investigation/closure-event-root-cause/scripts/test_closure_events.py`, `python 04-data-storytelling-visualization/executive-summary-generator/scripts/test_exec_summary_check.py`, `python 04-data-storytelling-visualization/insight-synthesis/scripts/test_insight_brief_check.py` and `python 04-data-storytelling-visualization/visualization-builder/scripts/test_viz_check.py` and `python 04-data-storytelling-visualization/dashboard-specification/scripts/test_dashboard_spec_check.py` - unit tests (also run by `qa_runner.py`).

## QA gate
`python 05-stakeholder-communication/analysis-qa-checklist/scripts/qa_runner.py` (`--data-only`, `--with-doc-check`). A WARN is fixed or waived in `qa_waivers.json` with a reason, owner and expiry; a FAIL is never waived. After sign-off run `qa_runner.py --update-baseline`. The loader raises `DataFormatError` on a missing column instead of continuing.

## Status gates
- OEE stays blocked until run-state, output, good-unit and cycle-time data exist - never report an OEE number or a "partial OEE".
- impact-quantification is deferred (`impact-quantification/status.json`, enforced by `lib/deferral.py` in the summary, brief and spec checkers and the QA gate): no deliverable may quote money, margin, payback or units-per-hour figures. Do not run `cost_impact.py` with real-looking numbers; its `--demo` is illustrative only. Lift the deferral only by editing `status.json` once every business parameter has a source, owner and date.
