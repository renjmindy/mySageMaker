---
name: handler-data-catalog
description: Catalog entry and site-geometry map for test-handler contactor logs (Advantest handler Contactor Select screen -> front/rear CSV). Activate when onboarding a handler data source, when someone asks "what does err_01/err_02 mean", or when you need to translate a site ID into row/column/block on the HIFIX.
---

# When to use
- Documenting the contactor-log source for a data catalog or wiki
- Explaining to a new analyst or fab engineer how a site ID maps to a position on the 16x32 contactor grid
- Adding a new handler (M6242 is the reference) with a different HIFIX size (e.g. 16x16)

# Process
1. **Identify the source** — handler ID, software screen (*Setup > Contactor Select*), capture method (screenshot + OCR -> CSV), cadence (~3-4 min), file naming (`contactor_YYYYMMDD.csv`, `contactor_rear_YYYYMMDD.csv`).
2. **Describe the schema** — fill `assets/catalog_entry_template.md` using `references/handler_screen_reference.md` (column semantics, blue/grey meaning, front vs rear).
3. **Build the site map** — run `scripts/site_map.py` to print row / column / 2x2-block for any site or to render a closed-site set as an ASCII grid. Use it to sanity-check that IDs make physical sense.
4. **Record known quirks** — read failures (256), `N/A` semantics, OCR garbage IDs, count > list length (see `01-data-quality-validation/contactor-log-validation/references/log_semantics.md`).
5. **Name the owner and refresh path** — who owns the handler, who owns the capture pipeline, what happens when a screen layout changes.
6. **Review with the process owner** — open items go to `analysis-assumptions-log`.

# Inputs the skill needs
- Required: handler ID and screenshot(s) of the Contactor Select screen (front and rear)
- Required: file naming and delivery location of the CSVs
- Optional: HIFIX type and DUT/site mapping (the screens show `site (DUT-site)`; observed equal)
- Optional: physical meaning of the 2x2 blocks (see open question in assumptions log)

# Output
- `assets/catalog_entry_template.md` (template) and `assets/contactor_logs_catalog_entry.md` (filled for the contactor logs; unknowns marked [OPEN])
- Console output of `site_map.py` — position lookup / ASCII grid for discussion with fab engineers
