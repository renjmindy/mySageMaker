---
name: analysis-planning
description: Plan the handler utilization work from site capacity to full OEE - phases tied to the requirements, statuses derived from them, dependencies routed to real roles and registered questions, estimates with a stated basis and a calibration after each phase, a risk register that includes what actually happened, and gate criteria that point at checks that exist. Activate at kick-off, when scope changes, or when a new data feed arrives.
---

# When to use
- Starting or re-planning the utilization work for a handler or a fab
- Deciding what can be delivered now and what is blocked, and by whom
- After stakeholders answer a question or a feed arrives (statuses must move by themselves)

# Process
1. **Start from the requirements** (`stakeholder-requirements-gathering`): every requirement belongs to exactly one phase; phases are not invented from the metric chain alone (data-quality gate, communication and sign-off are phases too).
2. **Derive the status, do not type it** — a phase's status is the worst status of its requirements (blocked, deferred, partial, met). `scripts/plan_check.py --status` prints them.
3. **Give every phase an owner role, entry criteria, an exit check and a date** — the owner is a role in the stakeholder map; the exit check is an existing script plus the named check or test that must pass; no deadline is written "no deadline set" and shows as a warning until someone sets it.
4. **List dependencies as questions** — provider role from the stakeholder map, `ask` = a theme or assumption id in the question registry, so the interview guide asks for it; a blocked or deferred phase needs at least one.
5. **Estimate by uncertainty** (`references/effort_estimation.md`): S / M / L with the basis, and after each phase record what happened and the size you would give it next time. Rules that are not confirmed make a phase M or L.
6. **Keep a risk register that has been through the project** (`references/risks_dependencies.md`): likelihood, impact, trigger, mitigation, owner role, status and evidence; materialised risks cite what happened, mitigated risks cite the artifact that enforces them.
7. **State the scope rule honestly** (`references/scoping_framework.md`): in scope when the feed exists; unowned metrics are tracked open items; numbers are not released until owners are named and a reviewer signs off.
8. **List next actions in order of what they unblock**, each with a role and a question.
9. **Run `scripts/plan_check.py`**, then run a kickoff with `assets/kickoff_doc_template.md`; review at each phase gate with `analysis-qa-checklist`.

# Inputs the skill needs
- Required: the requirements and brief, the stakeholder map, the question registry
- Required: an inventory of available and missing data feeds
- Optional: deadlines and maintenance windows

# Output
- `assets/analysis_plan_sep_oct_2026.md` (8 phases, 7 dependencies, 8 estimates with calibration, 9 risks, 6 next actions) and `assets/analysis_plan_template.md`
- `assets/kickoff_doc_template.md`
- `scripts/plan_check.py` (PASS / WARN / FAIL per check, `--status`) and `scripts/test_plan_check.py` (unit tests that break the real plan one way at a time)
