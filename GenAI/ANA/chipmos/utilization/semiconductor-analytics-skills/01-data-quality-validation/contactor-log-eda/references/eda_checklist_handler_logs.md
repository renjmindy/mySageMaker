# EDA Checklist - Handler Contactor Logs

- [ ] Date range, number of files per side, and any missing days
- [ ] Median sampling gap (~3-4 min expected) and largest gap
- [ ] Share of read failures (256) and unreadable lists (`N/A` with count > 0)
- [ ] Share of `N/A` + 0 rows (genuine zero-closed) - are they clustered on specific days (e.g. rear 09/17, 09/19, 09/23, 10/02)?
- [ ] Closed-count distribution per side (p50 / p90 / max)
- [ ] Sites closed in >90% of samples (candidate chronic sites)
- [ ] Days whose mean closed count is > 2x the period median (candidate events)
- [ ] Do closed sets change abruptly at day boundaries (maintenance / reconfiguration)?
- [ ] Is closure spatially clustered (adjacent sites / 2x2 blocks)?
- [ ] Open questions for the process owner
