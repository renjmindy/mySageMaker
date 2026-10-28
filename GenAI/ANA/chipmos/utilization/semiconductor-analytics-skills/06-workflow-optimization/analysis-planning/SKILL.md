---
name: analysis-planning
description: Plan the handler utilization analysis from site availability to full OEE - phases, dependencies on data feeds, effort and risks. Activate at kick-off, when scope changes, or when new data feeds (run-state, output, bins) become available.
---

# When to use
- Starting a utilization/OEE project for a new handler or fab
- Deciding what can be delivered now vs what is blocked by missing data
- Re-planning after stakeholder answers

# Process
1. **Define scope** — handlers, sides, period, metric (see `references/scoping_framework.md`).
2. **Split into phases** — P1 site availability (data exists), P2 chronic sites and events, P3 dashboard and alerts, P4 time availability (needs run-state), P5 Performance/Quality (needs output, cycle time, bins), P6 full OEE.
3. **List dependencies** — each blocked item names the missing feed and its owner (`references/risks_dependencies.md`).
4. **Estimate effort** per phase (`references/effort_estimation.md`).
5. **Identify risks** — OCR quality, capture outages, unclear definitions, no maintenance log.
6. **Write the plan** in `assets/analysis_plan_template.md`; run a kickoff with `assets/kickoff_doc_template.md`.
7. **Review at each phase gate** with `analysis-qa-checklist`.

# Inputs the skill needs
- Required: business question, handler list, stakeholder list
- Required: inventory of available and missing data feeds
- Optional: deadlines and maintenance windows

# Output
- `assets/analysis_plan_template.md` (filled) — phases, dependencies, owners, dates
- `assets/kickoff_doc_template.md` (filled) — kickoff agenda and decisions needed
