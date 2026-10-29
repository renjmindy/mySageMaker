# Methodology Explanation Patterns

**Layers** (each is a subset of the next): (1) one sentence, (2) the slide: data, measure, the rules that move the number, how sure, (3) the write-up: every rule with its assumption id, the formula, a worked example, limits, reproduction commands.

**Pick rules by effect, not by count.** The number of cleaning rules is not fixed (there are nine today). The slide shows the rules that move the headline most - ranked by their measured effect on the front figure (currently A8, +1.3 pts, and the time weighting A18, about 0.65 pt; the count-versus-list rule A15 moves it about 0.01 pt) - and points to the write-up for the rest. `scripts/methodology_check.py` recomputes the ranking from the data.

**A worked example must include the cases people get wrong**: a failed reading (its own time is not counted), a count of 252 to 255, a count that disagrees with the list, a position number outside the side's range, and a capture gap longer than the 15-minute cap. Put the raw columns first and the result last, and let the checker recompute the result from the loader so the example cannot drift from the code.

**Teach-back**: give a reader the rules and the raw columns only (`assets/teachback_blank.md`); within 0.1 pt of the answer key means the explanation works.

**Plain wording**: "test position" for site, "able to test" for available, "plausible range" for interval, "failed screen read" for read failure. State limits in the same breath as the number: lower bound, range, hypothesis, not OEE.
