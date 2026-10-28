# Contactor Log Semantics

Source: Advantest handler (e.g. M6242) *Setup > Contactor Select* screen, captured periodically
and converted to CSV (`Timestamp,err_01,err_02`).

## Screen geometry
- 16 columns x 32 rows = 512 contactor sites. Site `s` -> row `(s-1)//16 + 1`, column `(s-1)%16 + 1`.
- Front screen shows rows 1-16 (sites 1-256); rear screen shows rows 17-32 (sites 257-512).
- Blue cell = active/open; grey cell = closed (not functional). Only grey cells are logged.
- Each cell shows `site (DUT-site)`; the parenthesised number equals the site in the observed screens.

## Column meaning
| Column | Meaning | Reliability |
|---|---|---|
| `Timestamp` | capture time, minute resolution, ~every 3-4 min | high |
| `err_01` | reported number of closed sites on that side | medium (can disagree with list) |
| `err_02` | `;`-separated closed site IDs, or `N/A` | medium (OCR noise in IDs) |

## Confirmed interpretation rules
| Observation | Interpretation | Action |
|---|---|---|
| `err_01 == 256` | read failure (not "everything closed") | drop sample |
| `err_01` in 252-255 | read failure (confirmed) | drop sample (default `NEAR_FULL_MIN = 252`) |
| `err_02 == N/A` and `err_01 == 0` | truly zero closed sites | keep, n_closed = 0 |
| `err_02 == N/A` and `err_01 > 0` | list unreadable | drop sample |
| `err_01 != len(list)` | count is noisier | trust list length |
| ID outside side range (e.g. 1917, 7777) | OCR merge/split artefact | remove ID |
| duplicate ID in a row | OCR artefact | de-duplicate |
| 2026-07-30 file | trial run (lot TRIAL) | exclude |

## Open findings (from Sep-Oct data)
- `err_01` is **never lower** than the cleaned list length: in 100% of mismatching rows the count is higher
  (median +8 front / +10 rear). The list therefore under-reports closures; list length is a lower bound and
  `err_01` an upper bound. Availability can be reported as a range.
- Values of 252-255 (e.g. front 252 x102, 254 x57; rear 252 x106) are read failures **(confirmed by the process owner)**.
  They drove the front 09/09 spike (day median 28 closed, day mean 75; 24.3 once excluded) and are now dropped by default.
  Headline effect: front 90.02% -> 91.33%, rear 96.04% -> 96.08%.
