# Site Availability Method

```
availability(side, period) = 1 - sum_i(closed_i * minutes_i) / (256 * sum_i(minutes_i))
```
- `i` ranges over valid samples (`OK`, `NA_ZERO`)
- `minutes_i` = gap to next sample, capped at 15 min (a failed read still consumes its interval, i.e. its time is simply not counted, not imputed)
- Front and rear are reported separately; the combined 512-site number is the mean of the two
- Range: high = list-length closures, low = `max(err_01, list length)` closures

## Why weighting matters
Samples are ~4 min apart but gaps reach 20 min; an unweighted mean over-represents dense stretches (e.g. the burst of bad reads on front 09/09).

## Sensitivity table to always include
| Variant | Front | Rear |
|---|---|---|
| 256-only rule (superseded) | 90.02% | 96.04% |
| **Confirmed rules** (256, 252-255 and N/A>0 dropped) | **91.33%** (low 90.76%) | **96.08%** (low 95.47%) |
