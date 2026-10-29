# Learning Capture

A learning is one row of the log (`assets/learnings_log_sep_oct_2026.md`) with these parts, in this order: **situation and what we did -> rule going forward -> where it is enforced**, plus a class, the plan phase, how it was found, a source and the risk it belongs to.

## The rule must be concrete
Good: "Treat counts from 252 up as read failures, and test every delivery for an unflagged band just below the failure value."
Not accepted: "be more careful", "pay attention to the data", or anything that blames a person. `scripts/learnings_check.py` rejects those and any rule shorter than six words. Say what to do differently and what makes it happen.

## "Encoded in" must resolve
Write `path` "name": a code file that exists and contains the check, test or constant you name. The example in the log:
- Situation: front 2026-09-09 showed a mean of 75 closed positions, driven by counts of 252-254.
- Rule: treat counts from 252 up as read failures; test for an unflagged band below the failure value.
- Encoded in: `lib/contactor_io.py` "NEAR_FULL_MIN"; `05-stakeholder-communication/analysis-qa-checklist/scripts/data_gate.py` "unflagged near-full band".

If nothing in code enforces it, the status is **documented** (text only) or **open**, and an action in the retrospective must address it. Do not write `encoded` for a rule that only a document states.

## Classes and repeats
- Give each learning a class. Two or more learnings in a class need a **systemic fix**: one mechanism that stops the class, not another individual fix.
- If a new defect belongs to a logged class, log it with **repeat of** the earlier learning: the lesson did not hold, and the systemic fix is what to improve.

## Corrections inside deliverables
When a document records that an earlier version was wrong ("Corrected 2026-..", "an earlier version said ... that was wrong"), cite that file in a learning's source. The checker scans for these markers and fails on a correction that is not logged.
