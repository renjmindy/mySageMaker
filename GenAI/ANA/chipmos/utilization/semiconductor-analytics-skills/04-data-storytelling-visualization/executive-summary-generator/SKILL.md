---
name: executive-summary-generator
description: Write a one-page summary of handler utilization findings for fab and equipment managers using the answer-first pyramid structure. Activate when the analysis must be communicated to decision makers with limited time.
---

# When to use
- Weekly/monthly utilization update to equipment or operations management
- Requesting a maintenance window or budget based on the analysis

# Process
1. **Lead with the answer** — one sentence: availability level, trend, and the decision needed.
2. **Give three supporting points** — each with one number and one picture (`references/pyramid_principle_guide.md`).
3. **Quantify the ask** — recoverable availability points and what that means in capacity (see `05-stakeholder-communication/impact-quantification`).
4. **State confidence and caveats** in plain language (read failures excluded, OEE incomplete).
5. **Close with next steps** with owners and dates.
6. **Check jargon** — run `05-stakeholder-communication/technical-to-business-translator/scripts/jargon_detector.py`.
7. **Fill `assets/executive_summary_template.md`**.

# Inputs the skill needs
- Required: insight brief, headline numbers with range
- Required: the decision or request
- Optional: audience name and preferred length

# Output
- `assets/executive_summary_template.md` (filled) — one page, answer first
