---
name: methodology-explainer
description: Explain how handler capacity was computed and cleaned at the depth the audience needs (slide, write-up, appendix), with every rule tied to the metric contract, the rules that move the number ranked by measured effect, and a worked example recomputed from the real loader. Activate when stakeholders ask "how did you get this number?", before a review, or when the method changes.
---

# When to use
- A manager questions the 91% and 96% figures
- A peer, auditor or customer wants the cleaning rules
- Preparing a methodology slide or appendix, or after any rule or weighting change (the explainer must not drift from the code)

# Process
1. **Choose depth** — slide for executives, write-up for engineers and data owners (`references/audience_depth_guide.md` points at the canonical guide).
2. **State the data** — handler screen read about every 4 minutes, front 1-256 and rear 257-512, the period, the exclusion of the trial run.
3. **State every rule that decides which readings count** in the write-up's rules table, one row per assumption id in the metric contract (A3, A4, A5, A7, A8, A9, A15, A17, A18 today), each with its loader constant and its effect on the headline. The number of rules is not fixed; do not write "four bullets".
4. **Lead the slide with the rules that move the number most** — `scripts/methodology_check.py` ranks A8 (252-255 counts), A15 (count-list gap) and A18 (time weighting) by measured effect on the front figure (today A8 +1.31 pts, A18 about 0.65, A15 about 0.01) and requires the slide to name the top two with their numbers.
5. **State the formula and the weighting exactly** — capacity = 1 - closed-position minutes / (256 x counted minutes). Each valid reading counts for the time until the next reading in the file, capped at 15 minutes; **a dropped reading's own time is not counted**; across a capture gap (missing rows) the last valid reading counts for at most 15 minutes (A18). An earlier version of this guidance said the state carries across a dropped reading - that was wrong.
6. **Show a worked example that includes the cases people get wrong** — a failed read, a count of 252-255, a count above the list, an out-of-range position number, a capture gap over the cap. Raw columns first, result last; the checker recomputes every row and the result from the loader.
7. **State the limits with the number** — lower bound (the list under-reports closures), plausible range, hypotheses (the 2x2 grouping cause), and that this is capacity, not OEE.
8. **Run `scripts/methodology_check.py`**: rule coverage, constants, stated effects, the slide's top rules, worked example, traceable numbers, plain language and length of the slide, limits, reproduction commands, teach-back table, a single audience guide.
9. **Teach-back test** — give a reader the rules and `assets/teachback_blank.md` (raw readings only). Within 0.1 pt of `methodology_check.py --answer` means the explanation works.
10. **Fill the templates** (`assets/methodology_slide_template.md`, `assets/methodology_writeup_template.md`); see the filled `*_sep_oct_2026.md` files.

# Inputs the skill needs
- Required: the metric definitions contract, the assumptions log and the analysis document (the source of truth for rules and numbers)
- Required: the loader (`lib/contactor_io.py`), used to recompute the example and the rule effects
- Optional: the audience and a reader for the teach-back test

# Output
- `assets/methodology_slide_sep_oct_2026.md` (slide) and `assets/methodology_writeup_sep_oct_2026.md` (write-up with rules table and worked example); templates for both
- `assets/teachback_blank.md` — the exercise without the answer
- `scripts/methodology_check.py` (PASS/FAIL per check, `--answer` for the key) and `scripts/test_methodology_check.py` (16 unit tests that break the real explainer one way at a time)
