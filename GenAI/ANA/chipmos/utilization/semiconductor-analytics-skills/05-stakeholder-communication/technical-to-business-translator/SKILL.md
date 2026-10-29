---
name: technical-to-business-translator
description: Translate contactor/OEE analysis findings into the language of fab operations, equipment engineering and quality/customer contacts without losing the numbers or caveats, and check the result - numbers kept and none invented, caveats preserved, position words true to the handler grid, jargon per persona, readability. Activate before sending any result outside the analytics team, or when someone says they do not understand what a closed site means.
---

# When to use
- Preparing a message for process engineers, fab managers or customers
- Replacing data jargon (read failure, OCR noise, time-weighted, PERSISTENT) with operational wording
- Checking a draft for jargon and readability, or an existing translation for meaning loss

# Process
1. **Pick the persona** from `references/stakeholder_personas.md` (engineer, manager, customer); the page also holds each persona's language policy.
2. **Start from the technical statement as written for analysts** (analysis document or insight brief) so its numbers trace to the analysis.
3. **Translate with the pattern library** `references/translation_pattern_library.md` (every row is machine-checked); add a row only when it passes.
4. **Keep the number and the caveat** — the headline number (or its complement as "N of every 100"), nothing invented, and every caveat: lower bound, plausible range, hypothesis, OEE not available, excluded readings, noise.
5. **Describe positions only as the grid shows them** — row 16 (front) / row 32 (rear) is on top, column 1 on the left; rows are written "rows 13 to 16". `translation_check.py` rejects a wrong word (an earlier library entry said "near the bottom" for positions in the top rows).
6. **Run `scripts/translation_check.py`** — per pair: technical numbers trace to the analysis document, numbers kept / none invented, caveats kept, positions correct, language fits the persona, readable, no money figures while impact-quantification is deferred.
7. **Use `scripts/jargon_detector.py` and `scripts/readability_scorer.py` for free text.** The detector knows three kinds of term (unambiguous jargon, plain words that are jargon only in this domain, and codes such as PERSISTENT, A18, err_01) so plain English is not flagged. The scorer also reports jargon density: short sentences full of jargon are not "OK".
8. **Vet any analogy** (`references/metaphor_bank.md`): it must keep the structure of what it explains; never use one for statistical uncertainty.
9. **Test with a reader** from the persona: can they restate the point and the uncertainty?
10. **Fill `assets/translation_template.md`**; see `assets/translations_sep_oct_2026.md` for the findings translated for three personas.

# Inputs the skill needs
- Required: the technical statement (with its source) and the target persona
- Optional: the customer's own glossary

# Output
- `assets/translations_sep_oct_2026.md` (the five headline findings for the manager, three for the engineer, two for the customer) and `references/translation_pattern_library.md` (verified patterns)
- Console report from `translation_check.py`; jargon list and readability scores for free text
- `scripts/test_translator.py` — 23 tests, including precision and recall of the jargon detector on a labelled corpus (25 jargon and 23 plain sentences) and a negative test for every translation check
