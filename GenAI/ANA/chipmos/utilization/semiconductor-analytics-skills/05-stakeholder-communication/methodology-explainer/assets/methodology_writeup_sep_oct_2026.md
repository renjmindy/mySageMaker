# Methodology - handler test-position capacity, 2026-09-01 to 2026-10-02

## Purpose
Say how the share of test positions able to test was computed, which rules change the number, and how sure we are. Source of truth for the rules: `02-documentation-knowledge/semiconductor-metric-definitions/assets/metric_definition.yaml` (contract) and the assumptions log; results: `02-documentation-knowledge/analysis-documentation/assets/handler_utilization_analysis_sep_oct_2026.md`.

## Data
The handler's contactor screen read about every 4 minutes. Front positions are 1-256 and rear positions 257-512 (A7). Each reading gives a count of closed positions and a list of their numbers. The 2026-07-30 trial run is excluded. The raw files are private and not in the repository.

## Rules that decide which readings count
| Rule | What it does | Number | Effect on the front figure |
|---|---|---|---|
| A7 | Front positions are 1-256 and rear positions 257-512; numbers outside a side's range do not belong to it | 256 per side | - |
| A3 | A count of exactly 256 is a failed screen read and is left out | 256 | - |
| A8 | Counts of 252 to 255 are also failed reads and are left out | 252 | raises it by 1.3 pts |
| A15 | A count more than 50 above the list means the list could not be read; the reading is left out | 50 | about 0.01 pt |
| A4 | "N/A" with a count of 0 means nothing was closed; the reading is kept | - | - |
| A9 | "N/A" with a count above 0 means the list is unreadable; the reading is left out (applied, not confirmed) | - | - |
| A5 | When count and list disagree, the list is used; the count is never below the list, so the list gives a lower bound on closed positions | - | lower bound 90.88% against 91.32% |
| A17 | Position numbers outside the side's range, and repeats inside one reading, are removed (applied, not confirmed) | - | small |
| A18 | Each valid reading counts for the time until the next reading, at most 15 minutes. A dropped reading's own time is not counted. Across a capture gap (missing rows) the last valid reading counts for at most 15 minutes | 15 | time weighting is worth about 0.65 pt |

## Formula
Capacity = 1 - (sum of closed positions x minutes counted) / (256 x sum of minutes counted), over the readings that count, per side. The combined view is the mean of the two sides and is always shown next to them.

## Worked example
Nine readings, front side. Raw columns are time, count and list; the rest shows what the rules do.

| time | count | list | minutes counted | closed positions | what happens |
|---|---|---|---|---|---|
| 10:00 | 22 | 1-22 | 4 | 22 | normal reading |
| 10:04 | 22 | 1-22 | 4 | 22 | normal reading |
| 10:08 | 256 | 1;1;1 | 0 | - | failed read (A3): its own 4 minutes are not counted |
| 10:12 | 24 | 1-24 | 4 | 24 | normal reading |
| 10:16 | 252 | 1-24 | 0 | - | a count of 252 to 255 is also a failed read (A8) |
| 10:20 | 30 | 1-22 | 4 | 22 | the count is 8 above the list, so the list is used (A5) |
| 10:24 | 24 | 1-24 | 15 | 24 | the next reading is 20 minutes later; counted for at most 15 (A18) |
| 10:44 | 24 | 1-24 | 4 | 24 | normal reading |
| 10:48 | 24 | 1-23;600 | 4 | 23 | position 600 is outside the front range and is removed (A17); the last reading counts for a typical gap of 4 minutes |

Counted minutes: 4 + 4 + 4 + 4 + 15 + 4 + 4 = 39. Closed-position minutes: 22x4 + 22x4 + 24x4 + 22x4 + 24x15 + 24x4 + 23x4 = 908.
Result: **90.9%** = 1 - 908 / (256 x 39).

## How sure we are
- The reported count is never below the list, so closed positions are at least what the list shows; the result is shown as a range from a lower bound to this figure (front 90.88-91.32%, rear 95.64-96.07%).
- A plausible range for the period average comes from resampling whole days: front 90.57-92.08%, rear 95.30-96.83%. Differences under about 1.5 pts between periods cannot be told apart from day-to-day variation.
- About 3% of readings are dropped (front 3.06%, rear 3.37%).
- Neighbouring positions failing together suggests a shared part, but this is a hypothesis and is not confirmed.
- This is capacity, not OEE. OEE cannot be reported until run and idle time, output, good-unit and cycle-time data exist.

## Reproduce
Run from the repository root with only `pandas` and `numpy` installed.
```bash
python 03-data-analysis-investigation/site-availability/scripts/site_availability.py --quiet-days
python 02-documentation-knowledge/semiconductor-metric-definitions/scripts/metric_yaml_validator.py --recompute
python 05-stakeholder-communication/methodology-explainer/scripts/methodology_check.py --answer
```
