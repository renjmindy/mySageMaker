# QA Sign-off - handler contactor capacity, 2026-09-01 to 2026-10-02

**Status**: READY FOR REVIEW - **not signed off** (no independent reviewer yet; two manual items open).
**Repo state**: `f7dc8d79` or later (the QA gate changes that accompany this sign-off are in the following commit).

## Automated (`qa_runner.py --with-doc-check`)
41 checks: **0 FAIL, 0 WARN (unwaived), 4 WAIVED**. The data gate and the repo-health checks both ran; the analysis document's 12 commands re-ran with all 56 numbers found.

## Waivers in effect (`qa_waivers.json`)
| Check | Reason | Owner | Expires |
|---|---|---|---|
| rear: site IDs belong to this side | rear 2026-09-16: one stray token (131, in 26 readings; 1431 once) inside otherwise consistent lists, removed by the range filter (A17); headline effect negligible; cause unknown - ask the capture owner | analyst | 2026-12-31 |
| metric definitions vs loader | metric owners not yet named by the process owner | process owner | 2026-12-31 |
| executive summary vs analysis document | ask-table owners and dates are [OPEN] | process owner | 2026-12-31 |
| dashboard spec vs schema, data and backtest | dashboard, data and alert owners and channels are [OPEN] | process owner | 2026-12-31 |

The first waiver is a real finding of the new data gate: rear 09/16 had 17.1% of readings with an out-of-range ID against 1.8% overall. It stays visible until it expires or is explained.

## Fault-injection evidence
Ten faults were injected one at a time into a temporary copy of the real data; the previous gate detected none, the current one detects all ten. The 16 unit tests in `scripts/test_data_gate.py` repeat these on synthetic data so they run anywhere.

| Fault | Caught by |
|---|---|
| a day's file missing | no missing days; data not going backwards |
| every reading on one day failed | flagged day without a recorded decision |
| a day's rows duplicated | no duplicate timestamps |
| front and rear files swapped for a day | site IDs belong to the side |
| about 150 unflagged near-full readings | unflagged near-full band (A14 type) |
| one day's timestamps shifted by 8 hours | reading days match their file days |
| a column header renamed | data format (the loader raises) |
| the last two days never arrived | data has not gone backwards |
| +40 closed positions for 3 days (a real fault) | headline vs the last release (WARN) |
| trial run included (start 2026-07-30) | analysis start equals the documented scope (A6) |

## Headline reconciliation
| Deliverable | Front | Rear | Ties to the data? |
|---|---|---|---|
| data (loader) | 91.32% | 96.07% | - |
| analysis document | 91.32% | 96.07% | yes |
| insight brief | 91.32% | 96.07% | yes |
| executive summary | 91% | 96% | yes (rounded as written) |
| dashboard spec (P1/P2 query) | 91.32% | 96.07% | yes |
| HTML report tiles | 91.3% | 96.1% | yes (rounded as written) |

## Headline change versus the last release
None: the release baseline (`release_baseline.json`) was recorded from this same data on 2026-10-29. The first real comparison happens with the next data delivery.

## Manual checklist (`references/qa_checklist_master.md`)
| Item | Done? | Notes |
|---|---|---|
| Period and exclusions stated | yes | analysis document, Data section; scope check automated |
| Front and rear labelled, ranges correct | yes | automated site-range check; labels read in each deliverable |
| Cleaning rules cited, open assumptions disclosed | yes | A11, A13, A14 and the applied-but-unconfirmed rules are disclosed |
| Availability never presented as OEE; OEE stated as blocked | yes | enforced by the summary, brief and spec checkers |
| Range shown | yes | tiles, summary and line bands |
| Same number everywhere | yes | automated reconciliation |
| Charts: one axis, legend, tooltip, table view | yes | `viz_check.py`; light, dark and phone renders looked at by eye; no screen reader test |
| Chronic-site list reviewed against the handler screenshot or maintenance log | **no** | no screenshot of the Sep/Oct state and no maintenance log exist |
| Reviewer other than the author signed off | **no** | reviewer not yet named |

## Open items blocking sign-off
- Independent reviewer: [OPEN]
- Screenshot or maintenance-log check of the front groups still closed and the new rear group: [OPEN]
- Owners named for the metrics, summary actions, dashboard and alerts (the four waivers above): [OPEN]

Analyst: Claude (draft)   Reviewer (not the author): [OPEN]   Date: 2026-10-29
