# Stakeholder Personas

| Persona | Cares about | Wants to see | Avoid |
|---|---|---|---|
| Test floor / equipment engineer | which contactors, where, since when | site grid, event times, block alignment | statistics terms |
| Equipment / operations manager | capacity, maintenance planning, trend | availability %, top clusters, recoverable points | OCR detail |
| Quality / customer contact | yield and delivery risk | confirmation that data is validated, OEE completeness | internal cleaning rules |
| Data/IT owner | pipeline, schema, reproducibility | catalog, rules, scripts | business framing |

## Language policy per persona (enforced by `scripts/translation_check.py`)
| Persona | Allowed internal terms | Not allowed |
|---|---|---|
| engineer | position/site, row and column, cluster, block alignment, closed site, availability, lower bound, near-full, read failure, assumption ids, OEE | field names (err_01), status codes (PERSISTENT), p-values, bootstrap, backtest, MAD |
| manager | OEE | everything else in the jargon list (site, availability, cluster, interval, assumption ids, status codes ...) |
| customer | none | all of the jargon list, including OEE |

For every persona: keep the headline number (or its complement as "N of every 100"), invent none, and keep every caveat (lower bound, range, hypothesis, not OEE, excluded readings, noise).
