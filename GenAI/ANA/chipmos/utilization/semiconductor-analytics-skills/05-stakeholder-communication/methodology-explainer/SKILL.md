---
name: methodology-explainer
description: Explain how site availability and OEE were computed and cleaned, at the depth the audience needs (one slide, one page, or full appendix). Activate when stakeholders ask "how did you get this number?" or when auditors/customers review the method.
---

# When to use
- A manager questions the 91% vs 96% numbers
- A peer or customer wants the cleaning rules
- Preparing a methodology slide or appendix

# Process
1. **Choose depth** from `references/audience_depth_guide.md`.
2. **State the data** — handler screen captured every ~4 minutes, front 1-256 and rear 257-512, Sep-Oct.
3. **State the cleaning** in 4 bullets: failed reads dropped; `N/A` + 0 = nothing closed; list length trusted; impossible IDs removed.
4. **State the formula** — share of positions open, weighted by how long each reading represents.
5. **Show one worked example** (e.g. 22 closed of 256 for 4 minutes).
6. **State limits** — count is a minimum; OEE not yet complete.
7. **Fill `assets/methodology_slide_template.md` or `assets/methodology_writeup_template.md`**.

# Inputs the skill needs
- Required: metric definitions, assumptions log, QA results
- Optional: audience and time budget

# Output
- Slide text and/or one-page methodology write-up
