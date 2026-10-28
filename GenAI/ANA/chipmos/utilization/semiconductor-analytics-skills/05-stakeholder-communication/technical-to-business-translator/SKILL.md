---
name: technical-to-business-translator
description: Translate contactor/OEE analysis findings into the language of fab operations, equipment engineering and management. Activate before sending any result outside the analytics team, or when a stakeholder says "I don't understand what a closed site means".
---

# When to use
- Preparing a message for process engineers, fab managers or customers
- Replacing data jargon (read failure, OCR noise, time-weighted) with operational wording
- Checking readability of a draft

# Process
1. **Pick the persona** from `references/stakeholder_personas.md` (test floor engineer, equipment manager, quality/customer).
2. **Map terms** with `references/translation_pattern_library.md` (e.g. "closed site" -> "test position that cannot test").
3. **Run `scripts/jargon_detector.py`** on the draft; replace flagged terms.
4. **Run `scripts/readability_scorer.py`** — target short sentences (average <= 20 words).
5. **Keep numbers, change words** — never round away the caveat.
6. **Add one analogy** if useful (`references/metaphor_bank.md`).
7. **Fill `assets/translation_template.md`** with the before/after.

# Inputs the skill needs
- Required: draft text and target persona
- Optional: glossary used at the customer site

# Output
- Jargon report and readability score (console)
- `assets/translation_template.md` (filled) — technical vs plain-language versions
