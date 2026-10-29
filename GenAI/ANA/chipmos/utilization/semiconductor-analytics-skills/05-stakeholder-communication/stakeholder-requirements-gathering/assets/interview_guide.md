# Interview Guide - Handler Utilization

How to use it: ask by role (the Ask column), one role at a time, and record each answer in the assumptions log (decisions) or in the deliverable that carries the open item (facts). The questions below are **generated** from the assumptions log, the open markers in the filled deliverables and `question_registry.json`; refresh with `scripts/open_questions.py --write`. Answered questions drop out by themselves.

## Open questions
<!-- generated:start -->
### Decisions to confirm (from the assumptions log: OPEN or applied-but-unconfirmed)
| Id | Status | Question | Ask | What it blocks |
|---|---|---|---|---|
| A9 | APPLIED | Does an N/A list with a count above 0 mean the list is unreadable, so the reading is dropped (about 70 rows)? | process owner | which readings count (applied, not confirmed) |
| A11 | OPEN | Is the planned production time 24x7, or is there a calendar with shifts and maintenance windows? | production planner | time-based OEE and any capacity-constraint assessment |
| A12 | APPLIED | Should front and rear be reported separately, with the 512-position view as the mean of the two? | process owner | how the headline is presented (applied, not confirmed) |
| A13 | OPEN | Are aligned 2x2 blocks one physical unit (board, module, DUT group), and which? | process engineer | any statement of a physical cause and the maintenance plan |
| A14 | OPEN | Are readings with counts of 240 to 251 whose list also agrees real events or failed screen reads? | data / capture owner | about 28 kept readings and the failed-read band |
| A18 | APPLIED | Is capping each reading's time at 15 minutes the right way to weight readings across capture gaps? | process owner | the time-weighted headline (effect up to about 0.4 pt) |
| A19 | APPLIED | Are a 7-day window and the 50% / 10% / 20% thresholds the right way to decide what is closed now? | equipment / maintenance lead | the closed-now view, the ranked list and the dashboard status words |
| A20 | APPLIED | Are the time-series thresholds (robust z 2.5, 5% bad-reads day, p < 0.05 shift, 60-position burst) acceptable? | process owner | trend and time-of-day statements |
| A21 | OPEN | Since 2026-10-05 about 12:41 the count of closed sites is about 40 higher than the sites listed, on both sides. Are about 40 sites closed on purpose (for example a different setup), or is the list cut off by the capture? | process owner | how to read capacity from 2026-10-05: the list-based headline or the count-based lower bound (both are shown until answered) |

### Facts and owners to supply (from the open markers in the filled deliverables)
| Theme | Ask | Open items | Where | Question | What it blocks |
|---|---|---|---|---|---|
| actions in the executive summary | equipment / maintenance lead | 6 | executive_summary_sep_oct_2026.md | Who does each recommended action, and by when? | acting on the summary |
| analysis document reviewer and owners | process owner | 2 | handler_utilization_analysis_sep_oct_2026.md | Who reviews the analysis document, and who owns the metrics and data? | document sign-off |
| brief confirmation | process owner | 5 | analysis_brief_sep_oct_2026.md | Who confirms the brief, and what is the deadline? | scope, success criteria and deadlines |
| dashboard and alert owners | equipment / maintenance lead | 13 | dashboard_spec_sep_oct_2026.md | Who owns the dashboard, the data and each alert; which channel; what retention and latency; which visual draws the grid? | building the dashboard and paging anyone |
| data source facts | data / capture owner | 9 | contactor_logs_catalog_entry.md | Who owns the data and the capture; what is the handler ID of the Sep/Oct logs; how are they captured; what time zone, refresh schedule and retention apply? | provenance and the refresh path |
| metric owners | process owner | 7 | metric_definition.yaml | Who owns each metric definition? | metric governance and the QA waiver for owners |
| pipeline schedule, owner and limits | data / capture owner | 4 | pipeline_runbook_sep_oct_2026.md | When should the pipeline run, who owns it and is told when it fails, which channel, and how old may the newest reading be before a run fails? | scheduling the job, delivering alerts and the staleness limit |
| requirement owners | process owner | 1 | requirements_sep_oct_2026.md | Who owns each requirement and accepts it? | acceptance |
| sign-off | reviewer | 7 | qa_signoff_sep_oct_2026.md | Who reviews independently, and who checks the front groups against a screenshot or a maintenance log? | release sign-off |
| stakeholder names | process owner | 8 | stakeholder_map_sep_oct_2026.md | Who fills each role, including the process owner and the independent reviewer? | every confirmation and sign-off |
| waiver owners | process owner | 2 | qa_waivers.json | Name the owners the waivers refer to. | waiver expiry |

### Other facts needed (no marker carries them)
| Theme | Ask | Question | What it blocks |
|---|---|---|---|
| run-state, output, good-unit and cycle-time feeds | data / capture owner | Where can run / idle / jam / down history, unit counts, bin results and ideal cycle times be obtained (handler logs, MES)? | time-based OEE (blocked) |
| maintenance and contactor-change records, screenshots | equipment / maintenance lead | Do maintenance or contactor-change records and screenshots of the closed positions exist, and can they be shared? | checking events against reality and the chronic-site review |
| rear zero-closed days | equipment / maintenance lead | Do the rear zero-closed days (09/17, 09/19, 09/23, 10/02) reflect real repairs or board swaps, or idle days? | reading the rear history |
| business parameters for the deferred cost estimate | finance / business owner | What are units per hour per site, margin per unit, repair cost, hours per day, days, repair downtime and the probability a repair holds, and is the handler capacity-constrained? | lifting the impact-quantification deferral |

Totals: 9 assumptions to confirm, 64 open items in 11 files, 4 other facts.
<!-- generated:end -->

## General questions (ask every time)
- What decision will this analysis change? What would you do with a 3-point capacity gain?
- Which alert would you actually act on, and who acts?
- Who must sign off on definitions, and who reviews independently?
- What would make you stop trusting these numbers?
