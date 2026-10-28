# Handler Screen Reference (Advantest, e.g. M6242)

Derived from the 2026-07-30 screenshots in `doc/`.

| Screen | Purpose for this analysis |
|---|---|
| Setup > **Contactor Select** | **Data source.** Grid of 16 columns x 32 rows (front = rows 1-16, rear = rows 17-32). Each cell `site (DUT-site)`. Blue = active/open, grey = closed. |
| Main > Operating State | Context: STOPPED/WAITING/RUNNING state, lot name, file name, HIFIX type (16x16), total loaded/sorted. Candidate source for *planned/run time* (not yet captured). |
| Maintenance > Pt Sensor Temp. Disp. | Context: 19 Pt sensors (test/soak/exit chambers, shutters, hot air). Not used in the availability analysis yet; useful for correlating closures with temperature. |

## Screenshot facts (trial run, 2026-07-30)
- Lot `TRIAL`, file `BGA96B-9X13-512D`, handler `M6242`, 64 devices loaded, HIFIX 16x16.
- Only sites 1-64 blue in the trial -> 192 grey sites on the front side + a few -> the ~196 closed count in the 07/30 CSV.
- Trial data is excluded from production analysis.

## Not yet available (needed for full OEE)
- Run / idle / jam / down state timeline (Main screen "Operating State")
- Planned production time per day
- Total tested and good unit counts (Main screen "Total Loaded / Sorted", bin results)
- Ideal cycle time / UPH per device
