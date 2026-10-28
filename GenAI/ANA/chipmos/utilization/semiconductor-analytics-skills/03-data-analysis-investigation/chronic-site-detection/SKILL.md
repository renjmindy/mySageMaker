---
name: chronic-site-detection
description: Rank contactor sites by closure share and find spatially clustered (adjacent / aligned 2x2 block) chronic offenders. Activate when asked "which contactors should we fix first", before a maintenance window, or to prioritise HIFIX / contactor replacement.
---

# When to use
- Planning contactor or HIFIX maintenance
- Explaining why availability is below 100% (a few sites explain most of it)
- Separating chronic closures from transient ones

# Process
1. **Load cleaned data** via the shared loader (252-255 read failures are dropped by default).
2. **Compute closure share per site** — share of valid samples where the site is closed (`scripts/chronic_sites.py`).
3. **Classify by period and by recency** — period class: chronic >= 50%, frequent 10-50%, occasional < 10%. Recency status over the last 7 days (A19): PERSISTENT, NEW, CURRENT, INTERMITTENT, RESOLVED (see `references/chronic_thresholds.md`). Period share alone mislabels sites that were fixed or that broke recently.
4. **Cluster** — group chronic/frequent sites by 4-neighbour adjacency and by aligned 2x2 block; large clusters point to a module/board cause rather than single contactors.
5. **Estimate capacity lost** — each site's share = lost availability points, for the whole period and for the last 7 days; show the top-N cumulative contribution (Pareto).
6. **Prioritise** — act on what is closed *now* (the "attention now" cluster list and `currently_closed_site_rate`); treat RESOLVED sites as history and NEW sites as emerging. Rank by lost capacity x ease of fix; hand to `closure-event-root-cause`.
7. **Fill `assets/chronic_sites_report_template.md`**.

# Inputs the skill needs
- Required: cleaned contactor logs
- Optional: maintenance history to tell "fixed" from "still broken" (closure sets change between days)
- Optional: physical layout / board mapping to validate 2x2 clusters

# Output
- Console: ranked sites, clusters, Pareto of lost capacity
- `assets/chronic_sites_report_template.md` (filled)
