---
name: analysis-retrospective
description: Run a short retrospective after each phase of the utilization project and capture reusable learnings (data pitfalls, rule changes, process gaps). Activate at phase gates, after a surprising finding (e.g. the near-full read artefact), or at project end.
---

# When to use
- After delivering a phase (availability, dashboard, OEE)
- After an error or surprise changed the numbers
- Before applying the workflow to another handler or fab

# Process
1. **Gather facts** — timeline, what shipped, what changed (rules, numbers).
2. **Ask** (`references/retro_frameworks.md`): what worked, what did not, what surprised us.
3. **Capture learnings** — concrete rules (e.g. "always check counts just below the read-failure value"); use `references/learning_capture.md`.
4. **Update artefacts** — assumptions log, validation rules, QA checks, loader.
5. **Assign actions** with owners/dates (e.g. request direct handler logs instead of OCR).
6. **Record** in `assets/retrospective_template.md` and `assets/learnings_log_template.md`.

# Inputs the skill needs
- Required: phase outputs, assumptions log history, QA results
- Optional: stakeholder feedback

# Output
- `assets/retrospective_template.md` (filled) and `assets/learnings_log_template.md` (appended)
