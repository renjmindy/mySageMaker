---
name: stakeholder-requirements-gathering
description: Elicit, record and confirm requirements for the handler utilization work with fab, equipment and data owners - a confirmed analysis brief, requirements traced to deliverables and runnable acceptance checks, a stakeholder map with decision rights, and an interview guide generated from the assumptions log and the open markers so it cannot go stale. Activate at kick-off and whenever a definition, owner or data feed is unclear.
---

# When to use
- Starting or extending the utilization project
- A definition, owner or data feed is unknown (planned time, who owns capture, where run-state data lives)
- Preparing to ask a stakeholder questions, or to check whether the project's requirements are actually being met

# Process
1. **Name the stakeholders and their decision rights** in `assets/stakeholder_map_sep_oct_2026.md` (role, name, what they decide, who is accountable per deliverable). Define who the "process owner" is - the person whose confirmations the assumptions log records. Unnamed roles are a visible gap, not a blank.
2. **Generate the interview guide, do not write it** — `scripts/open_questions.py --write` builds the open questions from the assumptions log (OPEN and applied-but-unconfirmed), the open markers in the filled deliverables and `assets/question_registry.json` (who to ask, what each blocks). Answered questions drop out by themselves; a new open item that the registry does not route is reported.
3. **Interview by role** with `assets/interview_guide.md` and `references/elicitation_techniques.md`; record each answer where the item lives (assumptions log for decisions, the deliverable for facts), then regenerate the guide.
4. **Capture definitions and data feeds** in the brief: what capacity means (not OEE), side handling, trial-run exclusion, and which feeds exist (run / idle history, output, good units, cycle time, planned-time calendar, maintenance records, screenshots).
5. **Write testable requirements** in `assets/requirements_sep_oct_2026.md`: priority, source role, deliverable path, and an acceptance check = an existing script plus the named check or test that must pass. A requirement that is not met says what blocks it (an assumption id, missing data, or `status.json` when deferred).
6. **Agree success criteria** in the brief, each mapped to requirement ids; every "must" requirement needs one.
7. **Write the analysis brief** `assets/analysis_brief_sep_oct_2026.md` and have a named decision-maker confirm it (name and date). A draft stays visibly a draft.
8. **Run `scripts/requirements_check.py`** (brief complete, scope, assumption counts against the log, roles, requirement traceability and honesty, success-criteria coverage, guide in sync, no stale terms, no money figures while impact is deferred).
9. **Log changes** in `analysis-assumptions-log`.

# Inputs the skill needs
- Required: the assumptions log and the filled deliverables (the source of the open questions)
- Required: someone to interview, by role
- Optional: existing reports or dashboards in use

# Output
- `assets/analysis_brief_sep_oct_2026.md`, `assets/requirements_sep_oct_2026.md` (10 requirements with acceptance checks), `assets/stakeholder_map_sep_oct_2026.md`
- `assets/interview_guide.md` (generated block of open questions) and `assets/question_registry.json`
- `scripts/open_questions.py` (`--write`, `--check`), `scripts/requirements_check.py` and `scripts/test_requirements_check.py`
- templates: `assets/analysis_brief_template.md`, `assets/requirements_doc_template.md`
