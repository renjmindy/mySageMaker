# Common Errors in Contactor Analyses

| Error | Effect | Guard |
|---|---|---|
| Counting `err_01 = 256` as "all closed" | huge false downtime | loader drops it |
| Not catching 252-255 | spikes like front 09/09 | loader default `NEAR_FULL_MIN = 252`; QA FAILs if such rows remain |
| Trusting out-of-range IDs (1917, 7777) | phantom sites | loader range filter |
| Unweighted mean | bias from uneven sampling | time-weighted |
| Treating `N/A` always as zero | hides failures | only `N/A` + count 0 |
| Mixing front and rear ID ranges | wrong site positions | side ranges |
| Reporting availability as OEE | overstated performance | completeness label |
| Treating list length as exact | understated closures | report range |
