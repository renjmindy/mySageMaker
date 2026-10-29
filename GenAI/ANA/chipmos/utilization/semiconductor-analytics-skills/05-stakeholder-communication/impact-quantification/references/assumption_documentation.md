# Assumptions to Document for a Business Case
- units/hour per site (source, device, test time)
- operating hours (24x7 vs calendar)
- margin per unit (finance-approved)
- repair cost and downtime to repair
- probability repair holds; time to failure recurrence
- whether the handler is capacity-constrained

## Provenance table (one row per parameter, required before the deferral is lifted)
| Parameter | Value | Source | Owner | Date | Approved by |
|---|---|---|---|---|---|
| units per hour per site | [REQUIRED] | | | | |
| hours per day (planned-time basis, A11) | [REQUIRED] | | | | |
| margin per unit | [REQUIRED] | | | | finance |
| days in the horizon | [REQUIRED] | | | | |
| repair cost | [REQUIRED] | | | | |
| capacity-constrained (yes / no) | [REQUIRED] | | | | |
| probability the repair holds | [REQUIRED] | | | | |
| repair downtime days | [REQUIRED] | | | | |
| sites offline during repair | [REQUIRED] | | | | |
