# Effort Estimation

Size by **uncertainty**, not code volume:
| Size | Meaning |
|---|---|
| S | no open decision and no outside input |
| M | needs a decision from a role, or a rule that may change |
| L | needs two or more outside inputs or confirmations that block it |

Rules
- Write the basis (what makes it S, M or L) next to every size.
- After each phase record what happened and the size you would give it next time; the plan keeps both (`analysis_plan_*.md`, "Estimates and calibration").
- Lesson from this project: the first plan sized availability as "S: scripts exist". The loader and availability area turned out to be the most-revised part, because the real driver was cleaning rules, definitions and their wording, not code. When a phase's numbers depend on rules that are not confirmed, size it M or L.
- Calendar time is not estimated here: no deadline has been set (see the brief), and the repository history covers only about two days.
