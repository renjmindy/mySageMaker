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
3. **Quantify the ask in availability points** — what the open problems cost now (use the recency view of `chronic-site-detection`). Do not state money or units per hour: `impact-quantification` is deferred until real business parameters exist.
4. **State confidence and caveats** in plain language: a plausible range (not only one figure), unreadable readings excluded, OEE not yet reportable and why, causes that are only hypotheses.
5. **Close with next steps** with owners and dates.
6. **Run the checker** — `scripts/exec_summary_check.py` verifies: no placeholders, answer first, length (300 words), readability, no jargon, every number traceable to the analysis document (a derived number such as a sum must be declared in a `derived-numbers` comment, and its arithmetic is verified), OEE limit stated, a range shown. Then have a manager read it for two minutes and ask what the number, the decision and the uncertainty are.
7. **Fill `assets/executive_summary_template.md`** (see `assets/executive_summary_sep_oct_2026.md` for a worked summary).

# Inputs the skill needs
- Required: insight brief, headline numbers with range
- Required: the decision or request
- Optional: audience name and preferred length

# Output
- `assets/executive_summary_template.md` (template) and `assets/executive_summary_sep_oct_2026.md` (filled) — one page, answer first
- `scripts/exec_summary_check.py` (PASS/WARN/FAIL per check) and `scripts/test_exec_summary_check.py` (unit tests)
