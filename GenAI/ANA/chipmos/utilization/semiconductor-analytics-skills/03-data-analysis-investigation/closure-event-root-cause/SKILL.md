---
name: closure-event-root-cause
description: Detect when sites actually opened or closed (debounced against OCR flicker) and investigate each event. Activate when the closed set changes between days, availability steps up or down, or maintenance needs to be correlated with data.
---

# When to use
- A site cluster appeared, disappeared or moved (e.g. rear 479/463/480/464 on 09/21-22; 306/387 on 09/12-14)
- Verifying that a repair actually restored sites
- Building a timeline of contactor state changes for the process owner

# Process
1. **Build the site x time state matrix** from cleaned logs (`lib/contactor_io.closed_matrix`).
2. **Filter and debounce** — keep only samples where `err_01` equals the list length and closures are plausible (<= 100); then apply a rolling median (default window 5 samples, ~20 min) per site so single-sample OCR flicker disappears. Without the filter, bursts of garbled reads create fake events.
3. **Build closure episodes** — `scripts/closure_events.py` pairs each closure with its reopening per site: start, end, duration, and flags for ongoing (still closed at the last reading) and at-period-start episodes. Closures shorter than about half the window (under 3 readings) are ignored by design.
4. **Group into events** — episodes that start within 30 min **and** are spatially connected form one event, so concurrent but unrelated closures are not merged. Events are ranked by 2x2 block alignment, then size, then duration, and filtered by `--min-sites` (default 4) and `--min-duration` (default 30 min). The output prints the funnel (episodes -> events -> shown) and a false-event baseline (episodes on sites that are closed < 0.5% of the time).
5. **Form hypotheses** — use `references/rca_framework.md` (contactor wear, module/board, handler fault, capture artefact).
6. **Test** — compare with the maintenance log (the real test; none exists yet), the other side and neighbouring days; check whether the aligned 2x2 block closed/opened together. Treat an "event" as a state change in the cleaned data, not a confirmed equipment event. Run `scripts/test_closure_events.py` after any change.
7. **Document** in `assets/rca_report_template.md`.

# Inputs the skill needs
- Required: cleaned logs
- Optional: maintenance / contactor-change log with timestamps (strongly recommended)
- Optional: screenshots around the event time

# Output
- Console: ranked closure events (start, end, duration, sites, block alignment, flags) with the funnel and false-event baseline
- `scripts/test_closure_events.py` — unit tests on synthetic matrices
- `assets/rca_report_template.md` (filled)
