# Data Catalog Entry: Handler contactor-site logs (front / rear)

Filled from `assets/catalog_entry_template.md`. Anything not known is marked **[OPEN]** - nothing below is guessed.
Last verified against the data: 2026-10-28.

| Field | Value |
|---|---|
| Owner (data) | **[OPEN]** - not identified |
| Owner (capture pipeline) | **[OPEN]** - not identified |
| Source system | Advantest test handler, software screen *Setup > Contactor Select* (front = rows 1-16, rear = rows 17-32). Handler ID **M6242 appears only in the 2026-07-30 screenshots**; the CSVs carry no handler ID, so that the Sep/Oct logs come from the same handler is **[OPEN]** (assumed) |
| Capture method | **[OPEN]** - the logs look like periodic screen captures converted to text (garbled IDs, counts of 252-256 point to a screen-read step), but the actual method has not been confirmed |
| Cadence | about every 4 minutes (median gap 4.0 min, measured, Sep-Oct). Every gap over 15 minutes falls on 2026-09-09: front has 15 gaps of 17-22 min, rear has 11 gaps of 16-90 min (several at 90). Not an owner-documented value |
| Location / naming | `dat/contactor_YYYYMMDD.csv` (front) and `dat/contactor_rear_YYYYMMDD.csv` (rear), one file per calendar day; also delivered as zips `Chipmos FDC Front.zip` and `Chipmos FDC Rare.zip` (sic) with the same 32 files each. `dat/` is private and git-ignored |
| Format | CSV, UTF-8 with BOM, LF line endings, header `Timestamp,err_01,err_02` |
| History | Front 2026-07-30 (trial) and 2026-09-01 to 2026-10-02 15:14; rear 2026-09-01 to 2026-10-02 15:12. No rear file for 07/30. Earlier history **[OPEN]** |
| Volume (Sep-Oct) | front 11,632 rows (32 files); rear 11,589 rows (32 files) |
| Known exclusions | 2026-07-30 is a trial run (lot TRIAL, 64 devices) - excluded from analysis (assumption A6) |
| Time zone | **[OPEN]** - timestamps are naive, minute resolution |
| Refresh path / SLA | **[OPEN]** - no schedule, retention or latency guarantee known |
| Sensitivity | Private chipmos data. Must not be committed or shared (see `utilization/.gitignore`) |

## Schema
| Column | Type | Description | Quality notes |
|---|---|---|---|
| `Timestamp` | datetime, `YYYY/MM/DD HH:MM`, naive | capture time of the screen reading | no duplicate timestamps; the only gaps over 15 min are on 2026-09-09 (both sides) |
| `err_01` | integer | reported number of closed (grey) sites on that side | `256` and `252-255` are read failures (A3, A8); never below the list length |
| `err_02` | text | `;`-separated IDs of closed sites, or `N/A` | `N/A` + `err_01` 0 = zero closed (A4); `N/A` + count > 0 = unreadable (A9); contains out-of-range and duplicate IDs (A17) |

Columns are named `err_01`/`err_02` but are **not** error codes: they hold the closed-site count and list. The project docs' generic `err_01`/`err_02` error-code examples refer to a different design.

## Semantics
- **Grid**: 16 columns x 32 rows = 512 sites; site `s` is at row `(s-1)//16 + 1`, column `(s-1)%16 + 1`. Front = sites 1-256, rear = 257-512.
- **Cell colour**: blue = active/open, grey = closed (A2). Only grey cells are logged.
- **Cell label**: the screen shows `site (DUT-site)`; the two numbers are equal in the 07/30 screenshots. Whether they differ for other devices or HIFIX types is **[OPEN]**.
- **HIFIX**: 16x16 per the Main screen on 2026-07-30.
- **2x2 blocks**: closed sites often form aligned 2x2 blocks (rows 2k-1,2k x cols 2j-1,2j). The `R{r}C{c}` block label is this repo's own convention. The physical meaning (board, module, DUT group) is a **hypothesis (A13)** - not established.

## Quality profile (Sep-Oct 2026, after cleaning)
| | front | rear |
|---|---|---|
| Read-failure rate (256, 252-255, gap > 50, `N/A` with count > 0) | 3.06% | 3.37% |
| Valid rows | 11,276 | 11,199 |
| Rows kept with count > list length | 10.0% | 6.8% |
| Time-weighted site availability (list-based / lower bound) | 91.32% / 90.88% | 96.07% / 95.64% |
| Rows kept with out-of-range IDs | 0.3% | 1.8% |

Cleaning is done only in `lib/contactor_io.py`. Rules, evidence and open findings: `01-data-quality-validation/contactor-log-validation/references/log_semantics.md`; per-day decisions: `.../assets/validation_report_sep_oct_2026.md`; assumption IDs A1-A18: `02-documentation-knowledge/analysis-assumptions-log/assumptions.json`.

## Known quirks
- Counts of 252-256 are screen-read failures, not "all sites closed".
- `err_01` is never below the cleaned list length, so the list is a lower bound on closures.
- 2026-09-09 has repeated capture gaps on both sides (front up to 22 min, rear up to 90 min, 54% rear coverage); 2026-10-02 is a partial day.
- 28 kept rows with counts 240-251 and a near-full list are unresolved (A14).

## Not available in this source (needed for full OEE)
Run / idle / jam / down state timeline, planned production time, tested and good unit counts, ideal cycle time. OEE is blocked until these exist (A10, A11).

## Downstream consumers
The skills in this repository (`site-availability`, `chronic-site-detection`, `downtime-time-series`, `closure-event-root-cause`, `visualization-builder`, `pipeline-automation`).

## Items to resolve with the process owner
1. Owners of the data and of the capture pipeline
2. Handler ID for the Sep/Oct logs and the capture method
3. Time zone, refresh schedule and retention
4. Meaning of the 2x2 blocks and of `site (DUT-site)` for other devices
