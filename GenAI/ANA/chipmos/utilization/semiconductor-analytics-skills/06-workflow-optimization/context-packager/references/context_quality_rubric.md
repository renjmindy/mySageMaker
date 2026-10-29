# Context Quality Rubric

Each item names the check in `scripts/context_check.py` that enforces it. The last two are for a human.

- [ ] A newcomer can tell what is done, blocked, deferred and unconfirmed -> "the status line equals the requirements and the plan", "every assumption is present with its status; unconfirmed ones are marked"
- [ ] The package says what not to do, consistent with the status files -> "must-not rules agree with the status files and no business figures leak"
- [ ] The headline can be recomputed, and the package says how -> "the headline in the package equals a recomputation from the data", "the commit is recorded and exists", "the reproduce commands point at existing scripts"
- [ ] Nothing is stale -> "the pipeline summary is fresh and agrees", "superseded wording appears only in the history layer"
- [ ] Every rule has a source and status; a rule with no source is shown as "none (unconfirmed)" -> same assumptions check
- [ ] Open questions are explicit and equal the log and the markers -> "open decisions equal the assumptions log and the markers"
- [ ] QA state is present -> "the QA state equals the sign-off and the waivers"
- [ ] No secrets, personal data, private paths or raw data rows -> "no secrets, emails, private paths or raw data rows"
- [ ] Size within the budget -> "rules and state fit the budget (chars/3)"
- [ ] Cold-start test (human): give the package alone to someone new, or to a fresh assistant session, and ask what is blocked, what is unconfirmed and what they would do first; compare with the header. Not yet done.
- [ ] Token count (human): measure the package with the tokenizer of the assistant that will read it; the chars/3 estimate is a bound, not a measurement. Not yet done.
