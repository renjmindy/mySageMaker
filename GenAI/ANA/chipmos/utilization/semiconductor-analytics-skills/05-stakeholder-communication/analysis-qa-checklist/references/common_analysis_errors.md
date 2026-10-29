# Common Errors in Contactor Analyses

| Error | Effect | Caught by |
|---|---|---|
| Counting `err_01 = 256` as "all closed" | huge false downtime | loader drops it; loader guards (regression) |
| Not catching 252-255 | spikes like front 09/09 | loader default `NEAR_FULL_MIN`; loader guards; QA fails if such rows remain |
| Unflagged near-full readings just below the band (240-251) | hidden spikes | data gate: unflagged near-full band (A14 type) |
| Trusting out-of-range IDs (1917, 7777) | phantom sites | loader range filter; data gate: site IDs belong to the side (per-day share) |
| Front and rear files swapped or mixed | wrong site positions | data gate: site IDs belong to the side (FAIL above 25% of a day's readings) |
| A missing or partial day | biased headline | data gate: no missing days; data not going backwards; flagged-day decisions |
| Duplicated rows | double-counted time | data gate: no duplicate timestamps (the loader would drop them silently) |
| Renamed or missing column | silently wrong numbers | the loader raises `DataFormatError`; data gate reports "data format" |
| Time-zone shift or renamed file | readings in the wrong day | data gate: reading days match their file days |
| A bad day nobody reviewed | unnoticed artefact | data gate: every flagged day needs a decision in the validation report |
| Data that stopped arriving | stale headline looks "better" | data gate: data has not gone backwards since the last release |
| A real equipment change | headline moves | data gate: headline vs the last release (WARN > 1.5 pts - needs an explanation) |
| Analysis start moved (trial run included) | wrong scope | data gate: analysis start equals the documented scope (A6) |
| Unweighted mean | bias from uneven sampling | time-weighted metric; data gate: weighted vs unweighted |
| Treating `N/A` always as zero | hides failures | loader: only `N/A` + count 0 |
| Reporting availability as OEE | overstated performance | OEE statement required by the summary, brief and spec checkers |
| Treating list length as exact | understated closures | range reported; summary checker requires one |
| Same number differing between deliverables | confusion | headline reconciled across all deliverables |
