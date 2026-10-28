---
name: dashboard-specification
description: Specify the Grafana/web dashboard and storage schema for handler utilization and OEE - panels, queries, thresholds and alerts - using the pipeline in the project docs (TimescaleDB, Airflow, Grafana). Activate when moving from one-off analysis to a live dashboard.
---

# When to use
- Turning the analysis into a continuously refreshed dashboard
- Aligning engineering and fab ops on panels, definitions and alert thresholds
- Designing the TimescaleDB tables that Grafana will read

# Process
1. **List the decisions the dashboard serves** — maintenance prioritisation, shift handover, weekly review.
2. **Define tables** — `assets/dashboard_spec_template.md` section "Data model" (raw `contactor_samples`, derived `site_state_events`, daily `equipment_daily_metrics`) following the docs' `machine_status_logs` / `equipment_daily_metrics` pattern.
3. **Define panels** — see `references/dashboard_design_principles.md`: stat panels (front/rear availability), time series (daily + 7-day), heatmap/state grid of sites, Pareto of chronic sites, event table.
4. **Set thresholds** — availability alert below an agreed level (the docs use 75% for OEE; for site availability start from the observed baseline: front ~91%, rear ~96%) and a "new chronic cluster" alert.
5. **Set data-quality panels** — read-failure rate, last-sample age; stale or failing capture must be visible.
6. **Specify refresh** — hourly aggregation, daily close (Airflow / cron; see `06-workflow-optimization/pipeline-automation`).
7. **Review with users** and record open items in the assumptions log.

# Inputs the skill needs
- Required: metric definitions (`semiconductor-metric-definitions`)
- Required: list of handlers / sites and how they map to the dashboard hierarchy
- Optional: alert channels (Slack / LINE / email) and on-call owners

# Output
- `assets/dashboard_spec_template.md` (filled) — panels, queries, thresholds, refresh, alerts
