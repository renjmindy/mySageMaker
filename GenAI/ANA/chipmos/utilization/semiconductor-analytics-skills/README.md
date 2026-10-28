# Semiconductor Analytics Skills

Reusable analysis skills for **test-handler utilization** in semiconductor back-end test - built for the Advantest handler contactor-site logs (front 1-256 / rear 257-512) and structured like [data-analytics-skills](https://github.com/nimrodfisher/data-analytics-skills): six workflow stages, each skill a `SKILL.md` plus optional `scripts/`, `references/`, `assets/`.

**Problem**: the handler screen *Contactor Select* is captured every ~4 minutes. `err_01` = number of closed (grey) sites, `err_02` = list of closed site IDs. From that we derive site availability, chronic contactors, closure events and - once run-state, output and bin data exist - time-based OEE.

## Workflow and skills (25)

| Stage | Skills |
|---|---|
| **01 data-quality-validation** | contactor-log-validation, contactor-log-eda |
| **02 documentation-knowledge** | handler-data-catalog, analysis-assumptions-log, semiconductor-metric-definitions, analysis-documentation |
| **03 data-analysis-investigation** | site-availability, chronic-site-detection, downtime-time-series, closure-event-root-cause, oee-calculator |
| **04 data-storytelling-visualization** | visualization-builder, dashboard-specification, insight-synthesis, executive-summary-generator |
| **05 stakeholder-communication** | technical-to-business-translator, stakeholder-requirements-gathering, impact-quantification, analysis-qa-checklist, methodology-explainer |
| **06 workflow-optimization** | analysis-planning, pipeline-automation, context-packager, peer-review-template, analysis-retrospective |

Status: 24 skills are active; `impact-quantification` is deferred (see Status).

Typical chain: `contactor-log-validation` -> `site-availability` -> `chronic-site-detection` / `closure-event-root-cause` -> `visualization-builder` -> `insight-synthesis` -> `executive-summary-generator`, gated by `analysis-qa-checklist` and `analysis-assumptions-log`.

## Data rules (confirmed with the process owner)
- 256 closed = read failure -> drop; `N/A` + count 0 = zero closed -> keep; `N/A` + count > 0 -> drop
- list length is trusted over `err_01` (in practice `err_01` is never lower, so list length is a lower bound)
- IDs outside the side's range and duplicates = OCR noise; Sep/Oct 2026 only (07/30 was a trial run)
- `err_01` of 252-255 is also a read failure (confirmed) - applied by default (`NEAR_FULL_MIN = 252`)
- `err_01` exceeding the list length by more than 50 = unreadable list -> dropped (`MAX_COUNT_GAP = 50`)
- Open: what the aligned 2x2 blocks physically are (kept as a hypothesis); planned-time basis; side aggregation

All rules live once in `lib/contactor_io.py`; every script imports it.

## Quick start
```bash
python validate_skills.py                                    # check SKILL.md structure
python 03-data-analysis-investigation/site-availability/scripts/site_availability.py --quiet-days
python 06-workflow-optimization/pipeline-automation/scripts/daily_pipeline.py
```
Raw CSVs are read from `../dat` by default (override with `--data-dir`); they are git-ignored.

## Status
Site availability, chronic sites, events, visual report and QA run today on the available data (Sep-Oct 2026: front 91.3%, rear 96.1% time-weighted; lower bounds 90.9% / 95.6%).

- **OEE is blocked** until run-state, output, good-unit and cycle-time data exist; `oee-calculator` prints `BLOCKED` and no OEE number until all three factors are measured.
- **impact-quantification is deferred**: `cost_impact.py` is not part of the current workflow or pipeline and must not be used until real units/hour per site and margin per unit are supplied (it never defaults them; its demo is illustrative).
