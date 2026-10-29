---
name: peer-review-template
description: Structured, checkable peer review of a handler utilization release - a reviewer who is not the author reproduces the headline without the loader, works a rigor checklist that covers every defect class this project has had, records severity-ranked findings, and the verdict, response and QA sign-off are checked for consistency. Activate before publishing numbers, after rule or code changes, or when onboarding a second analyst.
---

# When to use
- A reviewer (not the author) must sign off on the availability numbers before a release
- Rules or code in `lib/contactor_io.py` changed
- Responding to review comments

# Process
1. **Author prepares** — run the pipeline and the QA gate, then `python scripts/review_prep.py --write`. It generates the claims to reproduce (headline, lower bound, range, closed now), where each appears, the author's recomputation without the loader, the unconfirmed rules, the waivers and the deliverables under review. The context package (`context-packager`) orients a reviewer who is new to the project.
2. **The process owner names the reviewer** — a person holding the `reviewer` role in the stakeholder map, not the author. Until then the record says NOT REVIEWED, and the author cannot fill the reviewer's parts. The reviewer needs access to the private data folder.
3. **Reviewer reproduces** — runs `scripts/independent_recompute.py` (raw files only: no loader, no pandas) and the pipeline, and fills the reproduction table; anything outside 0.01 percentage points needs a blocking finding.
4. **Rigor check** — `references/analytical_rigor_checklist.md`: each item names what already enforces it and what a person adds; an item that cannot be done is recorded as unchecked with the reason.
5. **Code check** — `references/code_review_for_analysis.md`.
6. **Write findings** with a severity (`references/peer_review_framework.md`: blocking, non-blocking, note), evidence and a requested change, in `assets/peer_review_sep_oct_2026.md` (form: `assets/peer_review_template.md`).
7. **Author responds** in `assets/review_response_sep_oct_2026.md`: fixed (with a commit or file that exists), disputed (with the reason) or deferred (with an action). Only the reviewer closes a finding, by marking it verified.
8. **Verdict and sign-off** — the verdict follows from the findings (`approve`, `approve with changes`, `reject`; `pending` until done). Name the reviewer in the QA sign-off, run `python scripts/review_check.py`, and only after approval run `qa_runner.py --update-baseline`.

# Inputs the skill needs
- Required: repository state at a named commit, QA output, assumptions log, access to the data folder, a named reviewer
- Optional: a previous review

# Output
- `assets/peer_review_sep_oct_2026.md` and `assets/review_response_sep_oct_2026.md` (forms: `assets/*_template.md`)
- `scripts/independent_recompute.py` (reproduction without the loader), `scripts/review_prep.py` (the author's generated preparation), `scripts/review_check.py` (PASS / WARN / FAIL per check) and `scripts/test_review_check.py` (tests that break the kit and the record one way at a time)
