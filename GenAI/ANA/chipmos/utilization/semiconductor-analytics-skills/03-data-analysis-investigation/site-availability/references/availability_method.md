# Site Availability Method

```
availability(side, period) = 1 - sum_i(closed_i * minutes_i) / (256 * sum_i(minutes_i))
```
- `i` ranges over valid samples (`OK`, `NA_ZERO`)
- `minutes_i` = gap to the next sample, capped at 15 min. **A valid reading's state is carried forward across the next reading even when that one was dropped, and across capture gaps, up to the 15-minute cap** (a limited carry-forward, not zero imputation); dropped readings have no weight of their own (A18)
- Front and rear are reported separately; the combined 512-site number is the mean of the two
- Range: high = list-length closures, low = `max(err_01, list length)` closures

## Why weighting matters
Samples are ~4 min apart but gaps reach 20 min; an unweighted mean over-represents dense stretches (e.g. the burst of bad reads on front 09/09).

## Sensitivity table to always include
| Variant | Front | Rear |
|---|---|---|
| 256-only rule (superseded) | 90.02% | 96.04% |
| **Confirmed rules** (256, 252-255, count-list gap > 50 and N/A>0 dropped) | **91.32%** (low 90.88%) | **96.07%** (low 95.64%) |

## Sensitivity (Sep-Oct 2026, time-weighted)
| Rule set | Front | Rear |
|---|---|---|
| 256 only (superseded) | 90.02% | 96.04% |
| + counts 252-255 dropped | 91.33% | 96.08% |
| + count-list gap > 50 dropped (current) | 91.32% | 96.07% |

The 252-255 rule is the one that matters (+1.3 pts on the front); the gap rule changes the headline by about 0.01 pt.

| Weighting | Front | Rear |
|---|---|---|
| unweighted mean | 91.97% | 96.63% |
| time-weighted, cap 5 min | 91.73% | 96.41% |
| time-weighted, cap 10 min | 91.34% | 96.09% |
| time-weighted, cap 15 / 30 min / unlimited (current: 15) | 91.32% | 96.07% |

Excluding 2026-09-09 and 2026-10-02 changes the headline by at most 0.02 pt.

## Precision
`site_availability.py` prints a 95% interval from a bootstrap that resamples whole days (weighted by valid minutes): front 90.57-92.08%, rear 95.30-96.83% (about +/-0.75 pt; daily standard deviation about 2.2 pts). The upper/lower range (about 0.44 pt) is smaller than this sampling uncertainty, so differences below about 1.5 pts between periods are not distinguishable from day-to-day variation.

## Validation of the implementation
An independent recomputation straight from the raw CSVs (no loader) matched to 4 decimals (front 91.3179%, rear 96.0734%). `metric_yaml_validator.py --recompute` repeats a cross-check of the formula against this script.
