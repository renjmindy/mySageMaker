# Insight Framework

**Insight = observation + so-what + evidence + confidence + action.** At most five per brief.

## Confidence is earned by tests, not asserted
| Level | Requires |
|---|---|
| **High** | (1) the claim repeats across the two halves of the period (chronic-site stability: top-20 overlap, sites chronic in both halves) **or** it is measured directly rather than estimated; (2) for a claim about sites, it is true *now* (recency status PERSISTENT or CURRENT in the last 7 days); (3) it does not depend on an OPEN assumption; (4) any APPLIED (unconfirmed) assumption it uses is shown to be *insensitive* - say how (window length, threshold, rule on/off, effect in points). |
| **Medium** | depends on an applied assumption the result is sensitive to; short evidence window; low statistical power (e.g. 32 days cannot detect a shift under about 2 pts); true over the period but not confirmed now; interval overlaps the comparison |
| **Low** | does not repeat across halves; single day or few readings; contradicted by the other side; rests on a hypothesis or on an OPEN assumption |

The confidence cell starts with the level and states the test behind it ("High - repeats across both halves (top-20 overlap 17/20) ...").

## Wording
- Do not write "cause", "root cause" or "recover" unless the cause is confirmed. Write "closed", "cost", "lost" and mark explanations as hypotheses (A13).
- Every number must appear in the analysis document (after rounding); a sum or difference is declared as a derived number with its terms.
- Cite assumptions with their status as logged: "A19 (APPLIED)". `scripts/insight_brief_check.py` verifies ids and statuses against the log.

## What a brief must cover (current project)
Where the current loss is (front groups), what is new or history on the rear, whether the headline depends on read-failure rules, what OEE still needs, and whether there is a trend or time-of-day pattern - each as an insight or an explicit known unknown.

Template sentence: "[Sites/group] cost [x] pts of capacity ([window]); [evidence]; recommend [action]."
