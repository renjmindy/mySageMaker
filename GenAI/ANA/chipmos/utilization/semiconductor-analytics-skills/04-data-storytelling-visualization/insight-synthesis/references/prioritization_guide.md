# Prioritisation

Score each insight 1-3 on three scales, record the rationale, and rank by the product (the brief's insights are listed in score order).

| Scale | 3 | 2 | 1 |
|---|---|---|---|
| **Impact** | >= 2 pts of capacity closed now | 0.5-2 pts closed now, or moves a headline number by >= 0.5 pt, or blocks a stated goal (e.g. OEE) | smaller, or informational |
| **Confidence** | High | Medium | Low (must match the confidence label in the insights table) |
| **Actionability** | a targeted physical action on an aligned group closed now (one inspection) | needs another owner (capture, data, planning) | nothing to act on, or scattered / unexplained |

Rules
- Score = impact x confidence x actionability; ties are allowed. Tie-breaker for ordering: higher actionability, then impact, then confidence.
- Impact counts capacity points **closed now** (recency view), not the period average - a group that was fixed is history.
- Do not convert points to money or units per hour while `impact-quantification` is deferred.
- **Sensitivity**: `scripts/insight_brief_check.py` recomputes the scores and re-ranks under three alternatives (impact squared; sum of the three scores; confidence x actionability only). The top-ranked and the lowest-ranked insights should not change; if they do, the ranking is not defensible and the scores need a second look.
