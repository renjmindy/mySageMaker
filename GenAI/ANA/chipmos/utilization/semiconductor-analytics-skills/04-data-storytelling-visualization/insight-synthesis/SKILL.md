---
name: insight-synthesis
description: Turn contactor-availability results into a ranked list of insights with evidence, confidence and recommended action. Activate after the analysis scripts have run and before writing any summary for managers or fab engineers.
---

# When to use
- You have numbers, charts and event timelines but not yet a story
- Deciding which of many findings deserve stakeholder attention

# Process
1. **Collect findings** from `site-availability`, `chronic-site-detection`, `downtime-time-series`, `closure-event-root-cause`.
2. **Write each as observation + evidence + confidence + action** (see `references/insight_framework.md`) - e.g. "Three groups of front positions are closed now and account for most of the current front loss (7.05 pts in the last 7 days)". Prefer what is closed *now* (recency view) to the period average; say "closed" and "cost", not "cause" or "recover", unless confirmed.
3. **Check against assumptions** — cite every assumption with its logged status. A finding that depends on an OPEN assumption cannot be High; one that depends on an APPLIED (unconfirmed) assumption is High only if you show it is insensitive to it (e.g. the same result with a 3-, 7- or 14-day window).
4. **Prioritise** by impact x confidence x actionability with the scales in `references/prioritization_guide.md`; record each score and rationale in the brief's Scoring table, and list insights in score order.
5. **Separate what is known from what needs data** — OEE is blocked until run and idle time, output, good-unit and cycle-time data exist; list open assumptions and missing records under Known unknowns.
6. **Draft the brief** in `assets/insight_brief_template.md`; max five insights. Run `scripts/insight_brief_check.py`: it verifies structure, that every number is traceable to the analysis document, assumption ids and statuses against the log, High-confidence rules, causal wording, the score arithmetic and ranking (with a re-weighting sensitivity), topic coverage, and that the executive summary only uses numbers found in the brief.

# Inputs the skill needs
- Required: outputs of the analysis scripts and the assumptions log
- Optional: stakeholder priorities and maintenance constraints

# Output
- `assets/insight_brief_template.md` (template) and `assets/insight_brief_sep_oct_2026.md` (filled) — ranked insights with evidence, confidence, assumptions, actions and a scoring table
- `scripts/insight_brief_check.py` (PASS/WARN/FAIL per check) and `scripts/test_insight_brief_check.py` (14 unit tests that break the real brief one way at a time)
