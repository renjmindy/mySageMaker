# Visualization Spec - Handler test positions report, 2026-09-01 to 2026-10-21

- **Question answered**: How many test positions can test, where are the closed ones **now**, and which should be looked at first?
- **Audience**: fab / equipment engineers and operations managers; read on a desktop or a phone.
- **Form and encoding**
  - Tiles: share of positions able to test (time-weighted) with a plausible range (95% day bootstrap) and a lower bound; positions closed now (>= 50% of the last 7 days).
  - Grids (front 1-256, rear 257-512): 16 columns x 16 rows in the handler's layout, highest row on top; fill = share of time closed, six single-hue buckets; toggle between "Last 7 days" (default) and "Whole period".
  - Ranked table: up to 10 positions per side by last-7-day share, with whole-period share and a plain-words status (closed long-term, closed recently, closed now, partly closed, reopened).
  - Line: daily share able to test, front blue / rear orange, band = plausible range of the period average.
- **Data**: `lib/contactor_io.py` defaults (252-256 counts and count-list gaps > 50 dropped); recency window 7 days to the last reading; numbers from `chronic_sites.py`, `site_availability.py`, `daily_trend.py`. Rules and statuses: assumptions A8, A15, A18, A19 (A19 is applied but unconfirmed).
- **Caveats shown on the page**: date range; readings weighted by duration; unreadable readings left out; plausible range and lower bound. Not shown: that neighbouring positions failing together is a hypothesis (A13) - the page does not state a cause.
- **Accessibility**: radio toggle, arrow-key cell reading with an aria-live region, tap/hover tooltips, ranked table, table view, dark mode with its own steps, 24 px touch cells on narrow/touch screens, no horizontal page scroll at 375 px.
- **Verification**: `scripts/viz_check.py` (22 checks incl. browser) and `scripts/test_viz_check.py`; light and dark renders were also looked at by eye.
- **Known limits**: the status words depend on the 7-day window (A19); the page is regenerated, not versioned (`out/` is git-ignored); a screen reader was not tested.
