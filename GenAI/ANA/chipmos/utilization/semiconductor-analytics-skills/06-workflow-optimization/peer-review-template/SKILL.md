---
name: peer-review-template
description: Structured peer review of a handler utilization analysis - rigor, data rules, code and communication. Activate before publishing numbers, after major rule changes, or when onboarding a second analyst.
---

# When to use
- A reviewer (not the author) must sign off on availability/OEE numbers
- Rules or code in `lib/contactor_io.py` changed
- Responding to review comments

# Process
1. **Author prepares** — assumptions log, QA output, validation report, scripts and commands.
2. **Reviewer runs the pipeline** and reproduces headline numbers.
3. **Rigor check** with `references/analytical_rigor_checklist.md` (definitions, sensitivity, ranges, exclusions).
4. **Code check** with `references/code_review_for_analysis.md` (single loader, no copy-pasted rules).
5. **Write the review** in `assets/peer_review_template.md` (blocking / non-blocking).
6. **Author responds** in `assets/review_response_template.md`.
7. **Re-run QA** and record the sign-off.

# Inputs the skill needs
- Required: repository state, QA output, assumptions log
- Optional: previous review

# Output
- `assets/peer_review_template.md` (filled) and `assets/review_response_template.md` (filled)
