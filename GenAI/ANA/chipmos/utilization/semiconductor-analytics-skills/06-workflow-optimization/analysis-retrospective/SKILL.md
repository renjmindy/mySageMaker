---
name: analysis-retrospective
description: Run a retrospective after each phase of the utilization project and turn what went wrong or surprised us into a log of concrete, classified, verifiable learnings - each pointing at the code or check that enforces it, each class with a systemic fix, repeats tracked, and actions owned. Activate at phase gates, after a number or document had to be corrected, or at project end.
---

# When to use
- After delivering a phase (availability, dashboard, OEE) or a release
- After an error or surprise changed a number, a rule or a document
- Before applying the workflow to another handler or fab

# Process
1. **Gather the evidence, not the memory** — corrections and surprises come from `git log --grep` (correct, wrong, stale, drift), the assumptions log, the QA waivers and the documents that record "Corrected" or "an earlier version"; `scripts/learnings_check.py` lists the last group and fails if one is not logged.
2. **Ask the questions** in `references/retro_frameworks.md` with the people who used the outputs; until they have taken part, say so under Limits.
3. **Write each learning** as a row in the log (`references/learning_capture.md`): situation and what we did, a concrete rule, the class, the plan phase, how it was found, a source (commit or file), the plan risk it belongs to, and whether it repeats an earlier learning.
4. **Encode it, then say where** — a rule is `encoded` only when a code file contains the named check, test or constant; otherwise it is `documented` or `open` and needs an action.
5. **Look for classes** — two or more learnings in a class need a systemic fix; a defect in a logged class is logged as a repeat of the earlier one, because the lesson did not hold.
6. **Update the plan** — new or materialised risks go into the plan's risk register, and estimates are compared with what happened (the plan checker verifies the register and the retrospective checker verifies the links).
7. **Assign actions** with a role from the stakeholder map, a registered question and a date or "no deadline set".
8. **Record** in `assets/retrospective_sep_oct_2026.md` (the lessons-by-class table is computed with `learnings_check.py --table`) and run `scripts/learnings_check.py`.

# Inputs the skill needs
- Required: the git history, the assumptions log, the QA results and waivers, the plan (phases and risks)
- Optional: stakeholder feedback from a held session

# Output
- `assets/learnings_log_sep_oct_2026.md` (learnings and classes) and `assets/retrospective_sep_oct_2026.md` (worked, did not, surprises, class table, actions, limits); blank forms in `assets/*_template.md`
- `scripts/learnings_check.py` (PASS / WARN / FAIL per check, `--table`) and `scripts/test_learnings_check.py` (tests that break the real log one way at a time)
