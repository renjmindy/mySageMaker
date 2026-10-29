# Retro Frameworks

Pick one to start the conversation; the output is always the same: rows in the learnings log and actions in the retrospective.

## Start / Stop / Continue
Ask each person for one item per column. Convert every "Stop" into a rule going forward and name what enforces it; a "Start" that has no owner becomes an action.

## 4Ls: Liked, Learned, Lacked, Longed for
"Lacked" and "Longed for" are the source of dependencies and requests (a missing feed, a missing reviewer): route them through the plan's dependencies and the question registry, not through prose.

## Timeline of surprises -> rule changes
List what changed a number or a document, in order: the surprise, the rule it produced, and where the rule lives. For this project start from the corrections: `git log --grep` for correct, wrong, stale, drift, plus files that record "Corrected" or "an earlier version" (the checker lists them).

## Questions that make the lesson concrete
- Which class is it (data-pitfall, doc-drift, over-claim, blind-check, process)? If the class already has entries, this is a repeat: what did the earlier fix not cover?
- What would have caught it earlier, and does that check exist now? Name the file and the check.
- Could the check have failed? Show the negative test.
- Is it about the data, the product or the process? Keep them separate: data lessons belong in the assumptions log and loader, product lessons in the checkers, process lessons in the plan.
- Does it change the plan's risks or estimates? Update both.

## Ground rules
- Blameless: describe the situation and the missing safeguard, never a person.
- Evidence first: a lesson cites a commit or a file. If it cannot, it is an opinion; put it under the surprises or the limits.
- Hold the session with the people who used the outputs, not only the analyst; until then say so under Limits.
