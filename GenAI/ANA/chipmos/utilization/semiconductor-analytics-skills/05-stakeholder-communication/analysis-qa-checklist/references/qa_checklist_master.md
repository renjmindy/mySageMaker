# QA Checklist

"Auto" = enforced by `qa_runner.py`; "Person" = needs a human and is recorded in the sign-off.

| Item | How |
|---|---|
| Period and exclusions stated (Sep/Oct only; 07/30 trial excluded) | Auto: analysis start equals the documented scope (A6). Person: the text says it |
| Front and rear labelled; ranges 1-256 / 257-512 | Auto: site IDs belong to the side; loader guards. Person: labels in the deliverables |
| Cleaning rules cited (A1-A20) and OPEN assumptions disclosed | Auto: assumptions log vs loader; brief and spec check ids and statuses. Person: disclosure reads honestly |
| "Availability" never presented as OEE; OEE completeness stated | Auto: summary, brief and spec checkers require the OEE statement; OEE panel blocked |
| Range shown where list under-reports closures | Auto: summary checker requires a range; report tiles checked |
| Same number in report, dashboard and summary | Auto: headline reconciled across all deliverables |
| Charts: one axis, legend, tooltip, table view | Auto: `viz_check.py` (static part in the gate). Person: look at it |
| New data complete and clean | Auto: missing/duplicate days, format, time zone, flagged-day decisions, side integrity, backwards data |
| Headline change versus the last release explained | Auto: WARN above 1.5 pts. Person: write the explanation in the sign-off |
| Chronic-site list reviewed against the handler screenshot or maintenance log | Person - not automatable (no ground truth in the data) |
| Reviewer other than the author signed off | Person |
