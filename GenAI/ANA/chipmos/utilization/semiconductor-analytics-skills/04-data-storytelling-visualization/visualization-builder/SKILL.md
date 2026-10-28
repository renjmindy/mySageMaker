---
name: visualization-builder
description: Build the standard charts for handler contactor analysis - a front/rear site closure heatmap on the physical 16-column grid and a daily availability line - as one self-contained HTML file. Activate when presenting chronic sites, availability trends or any contactor-grid result to fab engineers or managers.
---

# When to use
- Showing *where* on the HIFIX the problem is (grid heatmap) rather than a ranked list
- Showing availability over time for front vs rear
- Producing a shareable, offline HTML page for a meeting

# Process
1. **Pick the form from the job** — location of problem = grid heatmap in physical layout (row 32 on top like the handler screen); change over time = one-axis line; headline = stat tiles. See `references/chart_selection_guide.md`.
2. **Compute data via the shared loader** — closure share per site and daily availability (same cleaning rules as every other skill).
3. **Run `scripts/site_heatmap.py`** — writes `out/site_heatmap.html` (self-contained, inline SVG/CSS, no external libs).
4. **Check the design rules** in `references/visual_design_principles.md`: single-hue sequential ramp for magnitude, one axis, legend for 2+ series, tooltips, table view, dark mode.
5. **Look at the output** — open the HTML; check label collisions and the dark theme.
6. **Document intent** in `assets/viz_spec_template.md` (question, encoding, data, caveats).

# Inputs the skill needs
- Required: cleaned logs (or the CSV folder)
- Optional: title/subtitle text for the audience

# Output
- `out/site_heatmap.html` — two grids (front / rear), daily availability chart, summary tiles, data table view
- `assets/viz_spec_template.md` (filled)
