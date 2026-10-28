---
name: analysis-assumptions-log
description: Track every assumption behind the handler-utilization analysis - confirmed rules, open questions, and their impact on the numbers. Activate at project start, whenever a data rule is decided in conversation with the process owner, and before sharing results.
---

# When to use
- A rule was agreed verbally (e.g. "256 means read failure") and must be written down
- A result depends on an unresolved question (e.g. is 09/09 a real event?)
- Before a review, to show stakeholders exactly what the numbers rely on

# Process
1. **Start from the tracked log** — `assumptions.json` (next to this file) is the single source of truth and is committed to git; `assets/assumptions_log_template.md` is the report layout.
2. **Capture each assumption** — id, statement, category (`references/assumption_categories.md`), source and date (who confirmed, when), status (CONFIRMED / APPLIED / OPEN / DISPUTED), impact if wrong. Every rule or constant in `lib/contactor_io.py` needs an id.
3. **Track with the script** — `scripts/assumptions_tracker.py add|list|resolve|cite|check`; `check` fails when the log drifts from the loader constants (NEAR_FULL_MIN, MAX_COUNT_GAP, 15-min weight cap) or a CONFIRMED entry has no source/date.
4. **Quantify impact** — for OPEN items run the sensitivity (e.g. availability with the default rule vs `--near-full-min 0`) and record the delta.
5. **Link to outputs** — every figure in reports cites assumption ids (`assumptions_tracker.py cite A8 A15 A18` prints the footnote).
6. **Review before release** — run `check`; OPEN or APPLIED-but-unconfirmed items with high impact must be raised in the stakeholder deliverable.

# Inputs the skill needs
- Required: the decisions/answers given by the process owner
- Optional: sensitivity results for open assumptions

# Output
- `assumptions.json` (tracked) and a rendered Markdown table
- `assets/assumptions_log_template.md` (filled) — log attached to the analysis report
