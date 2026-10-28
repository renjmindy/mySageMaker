---
name: stakeholder-requirements-gathering
description: Elicit and confirm requirements for handler utilization / OEE analysis with fab, equipment and data owners - definitions, data feeds, decisions and success criteria. Activate at project kick-off and whenever a definition or data feed is unclear (e.g. what planned time means, where run-state data lives).
---

# When to use
- Starting or extending the utilization project
- A key rule is unknown (e.g. meaning of err_01 = 252-255, planned production calendar)
- Scoping the move from site availability to full OEE

# Process
1. **Identify stakeholders and decisions** — who decides on maintenance, who owns the handler, who owns capture (`references/decision_maker_framework.md`).
2. **Use the interview guide** `assets/interview_guide.md` (seeded with this project's open questions).
3. **Capture definitions** — utilization = time-based OEE; planned time basis; side handling; trial-lot exclusion.
4. **Inventory data feeds** — run/idle/down states, output counts, good/bad bins, ideal cycle time, maintenance log.
5. **Agree success criteria** — e.g. "daily availability by side, chronic-site list weekly, alert on new cluster".
6. **Write the analysis brief** `assets/analysis_brief_template.md` and have it confirmed.
7. **Log changes** in `analysis-assumptions-log`.

# Inputs the skill needs
- Required: list of stakeholders and their roles
- Required: current open questions (from the assumptions log)
- Optional: existing reports or dashboards in use

# Output
- `assets/analysis_brief_template.md` (filled) — scope, definitions, deliverables, success criteria
- `assets/requirements_doc_template.md` (filled) — detailed requirements
