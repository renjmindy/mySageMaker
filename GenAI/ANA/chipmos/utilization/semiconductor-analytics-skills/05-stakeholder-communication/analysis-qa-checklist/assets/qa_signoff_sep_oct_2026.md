# QA Sign-off - handler contactor capacity, 2026-09-01 to 2026-10-21

**Status**: READY FOR REVIEW - **not signed off** (no independent reviewer yet; manual items open).
**Repo state**: `5eca233a` or later (the extension of the period to 2026-10-21 is in the commit that follows it).

## Automated (`qa_runner.py --with-doc-check`)
Run the command for the current result: it is not copied here, because a copied count goes stale. When this sign-off was written it reported **0 FAIL and no unwaived WARN**; the data gate and the repository-health checks both ran, and the analysis document's commands re-ran with every number found. Every accepted warning is in the waiver table below.

## Waivers in effect (`qa_waivers.json`)
| Check | Reason | Owner | Expires |
|---|---|---|---|
| rear: site IDs belong to this side | stray numbers rise from 2026-10-05 (front 4.7% and rear 20.9% of readable rows in October, 0.2% and 3.0% of all listed numbers); the process owner decided on 2026-10-29 to ignore inaccurate site IDs on both sides (A17 confirmed); cause not established - ask the capture owner | process owner | 2026-12-31 |
| front: site IDs belong to this side | stray numbers rise from 2026-10-05 (front 4.7% and rear 20.9% of readable rows in October, 0.2% and 3.0% of all listed numbers); the process owner decided on 2026-10-29 to ignore inaccurate site IDs on both sides (A17 confirmed); cause not established - ask the capture owner | process owner | 2026-12-31 |
| metric definitions vs loader | metric owners not yet named by the process owner | process owner | 2026-12-31 |
| executive summary vs analysis document | ask-table owners and dates are [OPEN] until the process owner names them | process owner | 2026-12-31 |
| dashboard spec vs schema, data and backtest | dashboard, data and alert owners and channels are [OPEN] | process owner | 2026-12-31 |
| requirements work vs the log and the deliverables | the analysis brief is a draft and the stakeholder roles are unnamed until the process owner confirms the brief and names the people | process owner | 2026-12-31 |
| analysis plan vs requirements, roles and questions | no deadline has been set by the process owner (see the brief), so phases carry 'no deadline set' until one is | process owner | 2026-12-31 |
| learnings log and retrospective vs the repository and the plan | retrospective actions have no deadline yet, and no session with the process owner has been held (see its Limits) | process owner | 2026-12-31 |
| peer review kit and record vs the repository and the data | no independent reviewer has been named by the process owner, so the release is NOT REVIEWED and requirement R10 stays partial | process owner | 2026-12-31 |
| front: count and list agree | from 2026-10-05 about 12:41 the count is a constant 40 above the listed numbers on about two thirds of readings (open question A21); the process owner decided on 2026-10-29 to keep trusting the list length (A5) and to show both figures until it is answered | process owner | 2026-12-31 |
| rear: count and list agree | from 2026-10-05 about 12:41 the count is a constant 40 above the listed numbers on about two thirds of readings (open question A21); the process owner decided on 2026-10-29 to keep trusting the list length (A5) and to show both figures until it is answered | process owner | 2026-12-31 |
| front: lower bound vs the last release | the count-based lower bound moved by about 4.7 pts (front) and 4.2 pts (rear) against the first release (data to 2026-10-02) because since 2026-10-05 the count is a constant ~40 above the list (open question A21); the process owner decided on 2026-10-29 to keep trusting the list length and to show both figures | process owner | 2026-12-31 |
| rear: lower bound vs the last release | the count-based lower bound moved by about 4.7 pts (front) and 4.2 pts (rear) against the first release (data to 2026-10-02) because since 2026-10-05 the count is a constant ~40 above the list (open question A21); the process owner decided on 2026-10-29 to keep trusting the list length and to show both figures | process owner | 2026-12-31 |

The out-of-range-ID and count-versus-list waivers are real findings of the extended period (validation report, section 2): the data gate raised them, and they stay visible until they expire or the open question A21 is answered.

## What the extended period changed in the gate
- The out-of-range check now separates **noise** (many readings with a stray number: WARN, removed by A17) from a **swapped-sides file** (a large share of the listed numbers out of range: FAIL). The old rule counted readings, so October's rear noise (up to 60% of readings, about 11% of listed numbers on the worst day) looked like a swapped file.
- New checks: **count and list agree** (flags days where the count is more than 10 above the listed numbers on at least 20% of readings) and **lower bound vs the last release** (the count-based lower bound moved by about 4.7 pts while the list-based headline moved by 0.5). Nothing in the gate covered a constant gap between the count and the list before.
- Tests that hard-coded the earlier period's numbers crashed the gate on the new data; they now derive their values from the data or from the stored documents.

## Fault-injection evidence
Faults are injected one at a time into a copy of the data; the previous gate detected none of the first ten, the current one detects all of them. The unit tests in `scripts/test_data_gate.py` repeat these on synthetic data so they run anywhere.

| Fault | Caught by |
|---|---|
| a day's file missing | no missing days; data not going backwards |
| every reading on one day failed | flagged day without a recorded decision |
| a day's rows duplicated | no duplicate timestamps |
| front and rear files swapped for a day | site IDs belong to the side (FAIL) |
| about 150 unflagged near-full readings | unflagged near-full band (A14 type) |
| one day's timestamps shifted by 8 hours | reading days match their file days |
| a column header renamed | data format (the loader raises) |
| the last two days never arrived | data has not gone backwards |
| +40 closed positions for 3 days (a real fault) | headline vs the last release (WARN) |
| trial run included (start 2026-07-30) | analysis start equals the documented scope (A6) |
| stray numbers in 2 of 5 readings of a day | site IDs belong to the side (WARN, not FAIL) |
| a third of a day's listed numbers out of range | site IDs belong to the side (FAIL) |
| the count 40 above the list for a whole day | count and list agree (WARN) |
| the same fault | lower bound vs the last release (WARN) while the headline stays inside the tolerance |

## Headline reconciliation
The gate checks that the list-based headline is the same in every deliverable; the count-based lower bound was read in each by eye (manual checklist below).

| Deliverable | Front (list-based / lower bound) | Rear (list-based / lower bound) | Ties to the data? |
|---|---|---|---|
| data (loader) | 90.85% / 86.19% | 95.99% / 91.46% | - |
| analysis document | 90.85% / 86.19% | 95.99% / 91.46% | yes (automated) |
| insight brief | 90.85% / 86.19% | 95.99% / 91.46% | yes (automated) |
| executive summary | 91% / 86.2% | 96% / 91.5% | yes (rounded as written) |
| dashboard spec (P1/P2 and P3 queries) | 90.85% / 86.19% | 95.99% / 91.46% | yes (automated) |
| HTML report tiles | rounded as written | rounded as written | yes (automated) |

## Headline change versus the last release
The release baseline (`release_baseline.json`) is still the first release (data to 2026-10-02): front 91.32% / 90.88%, rear 96.07% / 95.64%. Against it:

| Side | List-based headline | Count-based lower bound |
|---|---|---|
| front | 90.85% (-0.47 pts, inside the 1.5 pt tolerance) | 86.19% (-4.69 pts, waived: A21) |
| rear | 95.99% (-0.08 pts, inside the tolerance) | 91.46% (-4.18 pts, waived: A21) |

Explanation: the list-based headline barely moved because the cleaned lists in October look like September's; the lower bound fell because from 2026-10-05 about 12:41 the reported count is a constant 40 above the listed numbers on about two thirds of readings (open question A21). The baseline is **not** updated: it is updated only after sign-off (`qa_runner.py --update-baseline`).

## Manual checklist (`references/qa_checklist_master.md`)
| Item | Done? | Notes |
|---|---|---|
| Period and exclusions stated | yes | analysis document, Data section; the requirements check takes the expected period from the analysis document |
| Front and rear labelled, ranges correct | yes | automated site-range check; labels read in each deliverable |
| Cleaning rules cited, open assumptions disclosed | yes | A11, A13, A14, A21 and the applied-but-unconfirmed rules (A9, A12, A18, A19, A20) are disclosed |
| Availability never presented as OEE; OEE stated as blocked | yes | enforced by the summary, brief and spec checkers |
| Range shown, and both figures (list-based and count-based lower bound) beside each other | yes | read in the analysis document, brief, summary, translations and methodology slide; dashboard P3 |
| Same number everywhere | yes | automated reconciliation |
| Charts: one axis, legend, tooltip, table view | partly | `viz_check.py` is automated; the report regenerated for the extended period has not been looked at by eye or on a phone, and no screen reader test was done |
| Chronic-site list reviewed against the handler screenshot or maintenance log | **no** | no screenshot of the Sep/Oct state and no maintenance log exist |
| Reviewer other than the author signed off | **no** | reviewer not yet named (`peer_review_sep_oct_2026.md` is NOT REVIEWED) |

## Open items blocking sign-off
- Independent reviewer: [OPEN]
- Screenshot or maintenance-log check of the closed groups still closed and the new groups: [OPEN]
- Owners named for the metrics, summary actions, dashboard and alerts (the waivers above): [OPEN]
- Not blocking, but it decides what the headline means: the answer to A21 (about 40 sites closed on purpose, or a cut-off list?): [OPEN]

Analyst: Claude (draft)   Reviewer (not the author): [OPEN]   Date: 2026-10-29
