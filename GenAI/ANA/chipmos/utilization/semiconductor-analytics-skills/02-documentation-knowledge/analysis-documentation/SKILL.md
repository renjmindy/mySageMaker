---
name: analysis-documentation
description: Write up the handler-utilization analysis so fab engineers and data owners can reproduce and trust it. Activate when an analysis is complete or handed over, or when someone asks how a number was derived.
---

# When to use
- Handing the analysis to another analyst or to process engineering
- Archiving the analysis with its data rules and exclusions
- Answering "how was this availability computed?"

# Process
1. **State the question and decision** — one sentence each.
2. **Name the data and rules** — source, period, valid-row contract, exclusions (link the validation report and assumptions log).
3. **Describe the method** — formula, weighting (time-weighted by sample interval, capped at 15 min), side handling.
4. **Show results with ranges** — report list-length-based availability as a lower bound on closures where relevant.
5. **List limitations** — see `references/audience_depth_guide.md` for how much detail each audience needs.
6. **Add reproduction steps** — exact script commands and the shared loader version.
7. **Fill `assets/analysis_doc_template.md`** and store it with the code.

# Inputs the skill needs
- Required: final numbers, scripts used, validation report, assumptions log
- Optional: stakeholder feedback and decisions taken from the analysis

# Output
- `assets/analysis_doc_template.md` (filled) — reproducible analysis document
