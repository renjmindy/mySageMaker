# Validation Rules and Severity Thresholds

Per day and per side (starting values - tune once a baseline exists):

| Check | MEDIUM | HIGH | CRITICAL |
|---|---|---|---|
| read-failure rate (`READ_FAIL_256` + `READ_FAIL_NEAR_FULL` + `READ_FAIL_GAP` + `NA_NONZERO`) | >= 2% | >= 5% | >= 15% |
| rows with out-of-range IDs | >= 3% | >= 10% | >= 25% |
| rows where count != list length | >= 10% | >= 25% | >= 50% |
| coverage (samples / expected ~360 per day) | < 90% | < 75% | < 50% |
| max gap between samples | > 15 min | > 30 min | > 60 min |

A day is **usable** if no CRITICAL finding; **usable with caveat** if HIGH; otherwise OK.

## Suspicious-day triage
1. Does the same set of sites explain the elevated closed count (real event) or do IDs vary row to row (noise)?
2. Does the other side show anything on the same day?
3. Is the elevated stretch contiguous in time (outage / maintenance) or scattered?
4. Compare with the screenshot nearest to the stretch if available.
