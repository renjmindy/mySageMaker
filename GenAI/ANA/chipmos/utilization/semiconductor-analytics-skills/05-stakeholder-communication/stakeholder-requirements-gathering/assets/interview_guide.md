# Interview Guide - Handler Utilization

## Open questions from the analysis (answer needed)
1. Is `err_01` of 252-255 a read failure like 256? (front 09/09 spike depends on it)
2. What does `N/A` with a non-zero count mean? (~70 rows)
3. Do rear zero-closed days (09/17, 09/19, 09/23, 10/02) reflect real repair / board swap, or idle/no-lot days?
4. Are aligned 2x2 blocks one physical unit (board / module / DUT group)? Which?
5. Planned production time: is 24x7 right, or is there a calendar/shift plan and maintenance windows?
6. Where can we get run / idle / jam / down state history and unit counts (handler logs, MES)?
7. Should reports be per side or combined (512 sites)?

## General
- What decision will this analysis change? What would you do with a 3-point availability gain?
- Which alert would you actually act on?
- Who must sign off on definitions?
