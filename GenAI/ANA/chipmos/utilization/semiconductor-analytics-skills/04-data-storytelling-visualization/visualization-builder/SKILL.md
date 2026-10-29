---
name: visualization-builder
description: Build the standard report for handler contactor analysis - where test positions are closed now (front/rear grids with a last-N-days / whole-period toggle), how many can test with a plausible range, a daily line with range bands and a ranked table - as one self-contained, accessible HTML file, and check it. Activate when presenting current closures, capacity trends or any contactor-grid result to fab engineers or managers.
---

# When to use
- Showing *where* on the HIFIX positions are closed **now** (not only over the month)
- Showing capacity over time for front vs rear with its uncertainty
- Producing a shareable, offline HTML page for a meeting, usable on a phone and by keyboard

# Process
1. **Pick the form from the job** — location of the problem = grid heatmap in the physical layout (row 32 on top like the handler screen); change over time = one-axis line with range bands; headline = tiles with a plausible range; "which ones first" = ranked table. See `references/chart_selection_guide.md`.
2. **Default to what is current** — the grids open on the last 7 days (recency view of `chronic-site-detection`), with the whole-period view one toggle away. A period-only map can point at groups that were already fixed (rear: 463/464/479/480 are only partly closed now; 419/420/435/436 is the new problem).
3. **Run `scripts/site_heatmap.py`** — writes `out/site_heatmap.html` (self-contained, inline SVG/CSS, no external libraries). Numbers come from the shared loader and the analysis scripts, never re-parsed.
4. **Run `scripts/viz_check.py`** — verifies every cell, plotted point, tile and range against the analysis scripts; date range and plain language in the visible text; toggle, ranked table, legend, aria-live region; sequential ramps monotonic with adjacent steps >= 8 (OKLab x100); front/rear colours separated; and, with playwright installed, no horizontal page scroll at 375/768/1280 px, touch cells >= 24 px, arrow-key reading and the toggle. `--no-browser` skips the browser part.
5. **Apply the design rules** in `references/visual_design_principles.md` (one axis, direct labels plus legend, tooltips, table view, dark mode with its own steps).
6. **Look at the output** — render light and dark (and a phone width) and look for label collisions and overflow; the checker does not judge taste.
7. **Document intent** in `assets/viz_spec_template.md`; see `assets/viz_spec_site_heatmap_sep_oct_2026.md` for the filled spec.

# Inputs the skill needs
- Required: the contactor CSV folder (read through `lib/contactor_io.py`)
- Optional: `--recent-days` (default 7), `--start`, `--output`
- Optional: playwright (`pip install playwright && playwright install chromium`) for the browser checks

# Output
- `out/site_heatmap.html` — tiles (share able to test, plausible range, lower bound, closed now), two grids with a view toggle, ranked table, daily line with range bands, table view
- `scripts/viz_check.py` (PASS/FAIL/SKIP per check) and `scripts/test_viz_check.py` (12 unit tests that break the real page one way at a time)
- `assets/viz_spec_template.md` (template) and `assets/viz_spec_site_heatmap_sep_oct_2026.md` (filled)
