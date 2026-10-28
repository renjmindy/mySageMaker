---
name: insight-synthesis
description: Turn contactor-availability results into a ranked list of insights with evidence, confidence and recommended action. Activate after the analysis scripts have run and before writing any summary for managers or fab engineers.
---

# When to use
- You have numbers, charts and event timelines but not yet a story
- Deciding which of many findings deserve stakeholder attention

# Process
1. **Collect findings** from `site-availability`, `chronic-site-detection`, `downtime-time-series`, `closure-event-root-cause`.
2. **Write each as claim + evidence + confidence** (see `references/insight_framework.md`) - e.g. "Two 8-site clusters (143/144/159/160/175/176/191/192 and 197/198/213/214/229/230/245/246) cause ~4.8 of the ~8.7 points of front capacity loss."
3. **Check against assumptions** — mark any finding that depends on an OPEN assumption.
4. **Prioritise** by impact x confidence x actionability (`references/prioritization_guide.md`).
5. **Separate what is known from what needs data** (OEE blocked by missing run-state/output).
6. **Draft the brief** in `assets/insight_brief_template.md`; max five insights.

# Inputs the skill needs
- Required: outputs of the analysis scripts and the assumptions log
- Optional: stakeholder priorities and maintenance constraints

# Output
- `assets/insight_brief_template.md` (filled) — ranked insights with evidence and actions
