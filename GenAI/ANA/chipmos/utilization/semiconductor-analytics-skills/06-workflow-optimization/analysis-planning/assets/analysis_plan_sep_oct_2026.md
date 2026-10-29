# Analysis Plan - handler contactor capacity, Sep-Oct 2026

**Status**: DRAFT - not confirmed by a decision-maker. **Prepared by**: Claude (draft), 2026-10-29.
Sources: the brief and requirements in `05-stakeholder-communication/stakeholder-requirements-gathering/assets/` (analysis_brief_sep_oct_2026.md, requirements_sep_oct_2026.md), the stakeholder map there for every role named here, and the generated open-question guide for every dependency. Phase status is **derived** from the requirements' statuses (worst of: blocked, deferred, partial, met), not typed; `scripts/plan_check.py` rejects a status that disagrees.

## Phases
| phase | deliverable | requirements | entry criteria | exit check | owner role | target date | status |
|---|---|---|---|---|---|---|---|
| P0 | Data-quality gate and definitions: loader rules, validation report, assumptions log, metric definitions, data catalog | R3 | contactor CSVs delivered | `05-stakeholder-communication/analysis-qa-checklist/scripts/data_gate.py` "no missing days" | process owner | no deadline set | met |
| P1 | Site capacity per side and day, with range and lower bound | R1 | P0 exit | `05-stakeholder-communication/analysis-qa-checklist/scripts/qa_runner.py` "headline reconciled across all deliverables" | process owner | no deadline set | met |
| P2 | Closed-now view and ranked list, closure events | R2 | P1 exit | `04-data-storytelling-visualization/visualization-builder/scripts/viz_check.py` "numbers match the analysis scripts" | equipment / maintenance lead | no deadline set | met |
| P3 | Alerts and dashboard | R4, R5 | P2 exit; a database and a dashboard tool | `04-data-storytelling-visualization/dashboard-specification/scripts/dashboard_spec_check.py` "every query runs and returns what the tag declares" | equipment / maintenance lead | no deadline set | partial |
| P4 | Time-based utilization (OEE): time availability, performance, quality, OEE | R6 | run / idle history, output, good units, cycle time, planned-time basis | `03-data-analysis-investigation/oee-calculator/scripts/test_oee_calculator.py` "test_doc_example" | process owner | no deadline set | blocked |
| P5 | Business case in units and money for repairs | R7 | real business parameters; deferral lifted | `05-stakeholder-communication/impact-quantification/scripts/test_cost_impact.py` "test_value_arithmetic_by_hand" | finance / business owner | no deadline set | deferred |
| P6 | Findings for managers, engineers and customers; method explanation | R8, R9 | P1 and P2 exit | `05-stakeholder-communication/technical-to-business-translator/scripts/translation_check.py` "numbers kept, none invented" | equipment / maintenance lead | no deadline set | partial |
| P7 | Independent QA sign-off of each release | R10 | the phase's exit check passes | `05-stakeholder-communication/analysis-qa-checklist/scripts/qa_runner.py` "analysis document reproduces (doc_numbers_check)" | reviewer | no deadline set | partial |

## Dependencies
Each row names what is missing, who provides it, and the open question that asks for it (a theme or an assumption id in the question registry).
| dependency | needed by | provider role | ask | status | if missing |
|---|---|---|---|---|---|
| run / idle / jam / down history, output counts, good units and bins, ideal cycle time | P4 | data / capture owner | run-state, output, good-unit and cycle-time feeds | missing | OEE stays blocked; only capacity is reported |
| planned production time (calendar, shifts, maintenance windows) | P4 | production planner | A11 | missing | time availability has no basis |
| a PostgreSQL / Timescale instance and a dashboard tool; the grid visual | P3 | equipment / maintenance lead | dashboard and alert owners | missing | the dashboard stays a specification |
| maintenance and contactor-change records, screenshots of the closed positions | P2 | equipment / maintenance lead | maintenance and contactor-change records, screenshots | missing | events and the chronic list cannot be checked against reality |
| business parameters (units per hour, margin, repair cost, downtime, probability a repair holds, capacity-constrained) | P5 | finance / business owner | business parameters for the deferred cost estimate | missing | the business case stays deferred |
| an independent reviewer | P7 | reviewer | sign-off | missing | no release can be signed off |
| named people for every role, including the process owner | P0 to P7 | process owner | stakeholder names | missing | no brief, assumption or sign-off can be confirmed |

## Estimates and calibration
Size scale (by uncertainty, not code volume): **S** = no open decision and no outside input; **M** = needs a decision from a role or a rule that may change; **L** = needs two or more outside inputs or confirmations that block it. The original estimates are from the first version of the plan.
| phase | original estimate | basis | what happened | next-time size |
|---|---|---|---|---|
| P0 | - | cleaning rules and definitions need owner decisions (A3-A20) | the most-revised area: rules, weighting and their wording were corrected more than once | L |
| P1 | S ("scripts exist") | the numbers depend on P0's rules | the loader and availability area changed more than any other; the size driver was rules, not code | M |
| P2 | M | validating events needs records that do not exist | built, but still unchecked against reality | M |
| P3 | M | needs a database and a dashboard tool | specified, not built; the missing tooling dominated | L |
| P4 | M | needs run-state, output, cycle-time and planned-time inputs | blocked; the feeds were never available | L |
| P5 | - | needs real business parameters | deferred by decision | L |
| P6 | - | wording is cheap, checking meaning is not | needed checkers and corrections (a wrong position claim, a wrong weighting description) | M |
| P7 | - | independent review needs a reviewer | gate built; reviewer missing | M |

## Risk register
| id | risk | likelihood | impact | trigger | mitigation | owner role | status | evidence |
|---|---|---|---|---|---|---|---|---|
| K1 | screen-read quality: failed readings, garbled position numbers, unflagged near-full bands | high | medium | new data delivered | loader rules, data gate, validation report decisions | data / capture owner | materialised | `01-data-quality-validation/contactor-log-validation/assets/validation_report_sep_oct_2026.md` |
| K2 | applied but unconfirmed rules (A9, A12, A17-A20) change numbers or statuses | medium | medium | the process owner answers differently | list them in the guide; sensitivity tables; the QA gate watches the loader constants | process owner | open | `02-documentation-knowledge/analysis-assumptions-log/assumptions.json` |
| K3 | no ground truth: no screenshots or maintenance records to check closed groups and events | high | high | someone acts on an unchecked group | ask for records and screenshots; call events state changes, not equipment events | equipment / maintenance lead | open | `05-stakeholder-communication/stakeholder-requirements-gathering/assets/question_registry.json` |
| K4 | short history (32 days): low power, a shift under about 2 points is invisible | high | low | a period-to-period difference is over-read | report ranges and intervals; re-test with three months | analyst | open | `02-documentation-knowledge/analysis-documentation/assets/handler_utilization_analysis_sep_oct_2026.md` |
| K5 | documentation drifts from the code (wrong weighting description, stale guide, wrong position word) | high | medium | a rule or constant changes | checkers tie documents to the code; the QA gate runs them | analyst | materialised | `05-stakeholder-communication/analysis-qa-checklist/scripts/qa_runner.py` |
| K6 | the OEE feeds never arrive, so the stated goal cannot be met | medium | high | no answer to the feed question | keep OEE blocked, report capacity honestly, escalate the question | data / capture owner | open | `03-data-analysis-investigation/oee-calculator/scripts/oee_calculator.py` |
| K7 | private data enters the repository | low | high | a broad git add | git-ignored data folders, explicit staging, checks before every commit | analyst | mitigated | `.gitignore` |
| K8 | nobody confirms anything: no named decision-maker or reviewer | high | high | the brief stays a draft | stakeholder map, waivers that expire, the generated guide | process owner | open | `05-stakeholder-communication/stakeholder-requirements-gathering/assets/stakeholder_map_sep_oct_2026.md` |
| K9 | business figures are quoted before real parameters exist | medium | high | a summary quotes money | the deferral status file and guard fail any deliverable that does | analyst | mitigated | `lib/deferral.py` |

## Scope rule
In scope when the input feed exists. An unnamed owner is a tracked open item (stakeholder map and guide), not a blocker for analysis; but numbers do not leave the analytics team as released until the process owner has named an owner for each metric and a reviewer has signed off (P7). Never in scope: trial lots and engineering runs.

## Next actions
Ordered by what each unblocks.
| order | action | role | ask | unblocks |
|---|---|---|---|---|
| 1 | Name the people for every role and confirm or correct the brief | process owner | stakeholder names | every confirmation and sign-off |
| 2 | Answer the planned-production-time question | production planner | A11 | the basis for time-based OEE |
| 3 | Say where run-state, output, good-unit and cycle-time data can be obtained | data / capture owner | run-state, output, good-unit and cycle-time feeds | P4 |
| 4 | Provide maintenance records or screenshots for the closed groups | equipment / maintenance lead | maintenance and contactor-change records, screenshots | checking P2 against reality |
| 5 | Name an independent reviewer | reviewer | sign-off | P7 and every release |
| 6 | Decide where the dashboard runs and name the alert owners | equipment / maintenance lead | dashboard and alert owners | P3 |
