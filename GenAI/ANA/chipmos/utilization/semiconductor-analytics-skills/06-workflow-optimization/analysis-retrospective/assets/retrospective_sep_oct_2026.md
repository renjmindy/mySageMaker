# Retrospective - handler contactor capacity, phases P0 to P7, to 2026-10-29

**Status**: DRAFT. **Prepared by**: Claude (analyst), from the repository history, the assumptions log and the review of each skill. The learnings are in `assets/learnings_log_sep_oct_2026.md`; this page says what they add up to. The plan's phases and risks are in `06-workflow-optimization/analysis-planning/assets/analysis_plan_sep_oct_2026.md`.

## What worked
- Injecting faults into a copy of the real data and writing a negative test for each check found real defects in our own gate and checkers (L9, L14, L16).
- Recomputing a document's numbers from the loader kept the headline identical across every deliverable (`05-stakeholder-communication/analysis-qa-checklist/scripts/qa_runner.py`).
- Asking the process owner and recording each answer with its source and date made the near-full and gap rules checkable (L1, L2).
- Generating lists from their source instead of keeping them by hand (the interview guide, the derived plan statuses) stopped them going stale (L15, L17).

## What did not
- Documentation drift is the class with the most entries, and one fact (the weighting rule) was wrong twice, because the first correction was not tested (L6, L7).
- A status line copied into CLAUDE.md is still not compared with the log (L19), and a capture fact in the validation report is still checked by hand (L5).
- Checks and rules were built without measuring what they catch: the QA gate, the alert rules, the jargon detector, a requirements check that could not fail (L9, L10, L11, L14).
- Plan inputs were first set by code size and by an owner rule that nothing satisfied (L17, L18).
- The scripts that produce the published numbers have no unit tests of their own (L22).

## Surprises
- A correction was itself wrong (L7).
- This skill's own example cited a check that does not exist (L20).
- Counts of 252 to 255 carried no flag, so a read artefact looked like a real shutdown of positions until a mean of 75 closed raised the question (L1).
- The period ranking pointed at the wrong positions on the rear side (L8).

## Lessons by class
Computed from the log; `scripts/learnings_check.py --table` prints it and the checker rejects a table that disagrees. A repeat means the same class of defect came back after a lesson was logged.
| class | learnings | repeats | encoded | documented | open |
|---|---|---|---|---|---|
| blind-check | 6 | 0 | 5 | 0 | 1 |
| data-pitfall | 3 | 0 | 3 | 0 | 0 |
| doc-drift | 8 | 2 | 6 | 2 | 0 |
| over-claim | 3 | 0 | 2 | 1 | 0 |
| process | 2 | 0 | 2 | 0 | 0 |

Each class with two or more entries has a systemic fix in the log's Classes table. Doc-drift is the class that repeated, so its systemic fix (the QA runner's reproduction and requirements checks) is the one to watch: a new drift defect after it is a failed lesson, not a new class.

## Actions
Role comes from the stakeholder map; ask is a question in the registry the interview guide generates, or - if the action is internal.
| id | action | role | ask | due | addresses | status |
|---|---|---|---|---|---|---|
| A1 | Add a check that the data-rules line in CLAUDE.md matches the statuses in the assumptions log | analyst | - | no deadline set | L19 | open |
| A2 | Recompute the capture-gap facts in the validation report and the catalog with a command the document checker runs | analyst | - | no deadline set | L5 | open |
| A3 | Have one reader per persona (manager, engineer, customer) read the metaphors and translations and say what they understood | process owner | stakeholder names | no deadline set | L21 | open |
| A4 | Add unit tests for site_availability.py, chronic_sites.py and daily_trend.py that break one rule at a time, then for the other script folders without tests | analyst | - | no deadline set | L22 | open |
| A5 | Ask whether the handler can export the list of closed positions directly instead of it being read from the screen | data / capture owner | data source facts | no deadline set | L1, L2, L3 | open |
| A6 | Hold this retrospective with the process owner and the equipment lead, and add what they found | process owner | stakeholder names | no deadline set | - | open |

## Limits
- This was written by the analyst alone. No session has been held with the process owner, the equipment lead or any reader (A6), so what surprised or hurt them is not here.
- The history covers about two days of work and one data delivery: no trend in corrections per phase can be read from it, and the "found by" column is the analyst's account of that work.
- The lessons are about this project; they are not an independent audit, and the QA reviewer role is still unfilled.
