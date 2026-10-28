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
3. **Detect transitions** — `scripts/closure_events.py` finds open->closed and closed->open transitions per site.
4. **Group into events** — transitions within 30 min become one event; list sites, block membership and time.
5. **Form hypotheses** — use `references/rca_framework.md` (contactor wear, module/board, handler fault, capture artefact).
6. **Test** — compare with maintenance log, other side, neighbouring days; check whether the aligned 2x2 block closed/opened together.
7. **Document** in `assets/rca_report_template.md`.

# Inputs the skill needs
- Required: cleaned logs
- Optional: maintenance / contactor-change log with timestamps (strongly recommended)
- Optional: screenshots around the event time

# Output
- Console: event timeline (time, type, sites, blocks)
- `assets/rca_report_template.md` (filled)
