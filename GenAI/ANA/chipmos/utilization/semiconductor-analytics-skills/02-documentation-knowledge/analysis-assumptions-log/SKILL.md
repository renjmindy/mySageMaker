---
name: analysis-assumptions-log
description: Track every assumption behind the handler-utilization analysis - confirmed rules, open questions, and their impact on the numbers. Activate at project start, whenever a data rule is decided in conversation with the process owner, and before sharing results.
---

# When to use
- A rule was agreed verbally (e.g. "256 means read failure") and must be written down
- A result depends on an unresolved question (e.g. is 09/09 a real event?)
- Before a review, to show stakeholders exactly what the numbers rely on

# Process
1. **Seed the log** — start from `assets/assumptions_log_template.md`, already pre-filled with the confirmed and open items of this analysis.
2. **Capture each assumption** — id, statement, category (`references/assumption_categories.md`), source (who confirmed), status (CONFIRMED / OPEN / DISPUTED), impact if wrong.
3. **Track with the script** — `scripts/assumptions_tracker.py add|list|resolve` keeps a JSON log (`out/assumptions.json`) and renders Markdown.
4. **Quantify impact** — for OPEN items run the sensitivity (e.g. availability with the default rule vs `--near-full-min 0`) and record the delta.
5. **Link to outputs** — every figure in reports cites assumption ids.
6. **Review before release** — OPEN items with high impact must be raised in the stakeholder deliverable.

# Inputs the skill needs
- Required: the decisions/answers given by the process owner
- Optional: sensitivity results for open assumptions

# Output
- `out/assumptions.json` and a rendered Markdown table
- `assets/assumptions_log_template.md` (filled) — log attached to the analysis report
