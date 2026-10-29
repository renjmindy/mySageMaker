# Site Availability Method

```
availability(side, period) = 1 - sum_i(closed_i * minutes_i) / (256 * sum_i(minutes_i))
```
- `i` ranges over valid samples (`OK`, `NA_ZERO`)
- `minutes_i` = gap to the next sample, capped at 15 min. **a dropped reading's own time is not counted** (the reading before it covers only up to the dropped reading's timestamp); **across a capture gap (missing rows) the last valid reading is carried forward for at most 15 minutes**, and gap time beyond that is not counted (A18)
- Front and rear are reported separately; the combined 512-site number is the mean of the two
- Range: high = list-length closures, low = `max(err_01, list length)` closures

## Why weighting matters
Samples are ~4 min apart but gaps reach 20 min; an unweighted mean over-represents dense stretches (e.g. the burst of bad reads on front 09/09).

## Sensitivity table to always include
| Variant | Front | Rear |
|---|---|---|
| 256-only rule (superseded) | 89.95% | 95.80% |
| **Confirmed rules** (256, 252-255, count-list gap > 50 and N/A>0 dropped), list-based | **90.85%** | **95.99%** |
| Same rules, count-based lower bound (counts the gap of open question A21) | 86.19% | 91.46% |

## Sensitivity (2026-09-01 to 2026-10-21, time-weighted)
| Rule set | Front | Rear |
|---|---|---|
| 256 only (superseded) | 89.95% | 95.80% |
| + counts 252-255 dropped | 90.73% | 95.92% |
| + count-list gap > 50 dropped (current) | 90.85% | 95.99% |

The 252-255 rule moves the headline most (+0.77 pt on the front, +0.12 pt on the rear). The gap rule moves it by +0.12 pt (front) and +0.07 pt (rear), more than in September because the constant 40-site gap from 2026-10-05 pushes some October readings over the limit of 50 (validation report, section 1).

| Weighting | Front | Rear |
|---|---|---|
| unweighted mean | 91.50% | 96.52% |
| time-weighted, cap 5 min | 91.22% | 96.33% |
| time-weighted, cap 10 min | 90.87% | 96.01% |
| time-weighted, cap 15 / 30 min (current: 15) | 90.85% | 95.99% |
| time-weighted, no cap | 90.86% | 95.99% |

Excluding 2026-09-09 and 2026-10-02 changes the headline by at most 0.02 pt; also excluding 2026-10-15 changes it by -0.04 pt (front) and +0.07 pt (rear).

## Precision
`site_availability.py` prints a 95% interval from a bootstrap that resamples whole days (weighted by valid minutes): front 90.25-91.43%, rear 95.45-96.53% (about +/-0.6 pt; daily standard deviation about 2.1 pts front and 2.0 pts rear). The upper/lower range is now **4.66 pts on the front and 4.53 pts on the rear**, far wider than the interval: the unanswered question about the 40-site gap (A21) is a larger source of uncertainty than sampling. Differences under about 1.5 pts between periods are not distinguishable from daily variation; before 2026-10-05 the range was under 0.5 pt (see the split in the analysis document).

## Validation of the implementation
An independent recomputation straight from the raw CSVs (no loader, no pandas) matches to 4 decimals (front 90.8504%, rear 95.9907%; lower bounds 86.1872% and 91.4626%); it is `06-workflow-optimization/peer-review-template/scripts/independent_recompute.py`, and the peer-review checker compares it with the loader-based headline. `metric_yaml_validator.py --recompute` is a different, weaker check: it recomputes from the loader's output, so it tests the formula against this script, not the loader itself.
