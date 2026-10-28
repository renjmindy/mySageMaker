# OEE Scenarios for This Project

| Stage | Inputs available | Result |
|---|---|---|
| Today | contactor logs only | site availability (front/rear) - capacity factor, **not OEE**; OEE BLOCKED |
| Next | + run/idle/down timeline from Main screen / handler log | time availability A |
| Then | + output counts and ideal cycle time | Performance P (use effective parallelism) |
| Full | + good/total (bin results) | Quality Q -> OEE |

Effective parallelism: with 256 sites per side and `a` = site availability, parallel throughput scales with `a`.
Count it once - either inside P (preferred) or as a separate "site factor", never both.
