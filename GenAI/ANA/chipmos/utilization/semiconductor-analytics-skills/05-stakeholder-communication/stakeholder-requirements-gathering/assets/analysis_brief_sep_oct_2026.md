# Analysis Brief - handler contactor capacity, Sep-Oct 2026

**Status**: DRAFT - not confirmed. **Confirmed by**: [OPEN] on [OPEN]. **Prepared by**: Claude (draft), 2026-10-29. This brief records what the project has been doing, reconstructed from the work and the decisions logged in `02-documentation-knowledge/analysis-assumptions-log/assumptions.json`; the process owner must confirm or correct it.

- **Business question**: How much of the handler's contactor capacity can test, where is it lost, and is it changing - so that the right closed groups are inspected first.
- **Decision / owner**: which closed groups to inspect or replace first, owned by the equipment / maintenance lead ([OPEN] name); data meaning and cleaning rules owned by the process owner ([OPEN] name). Roles and decision rights: `assets/stakeholder_map_sep_oct_2026.md`.
- **Scope**: one handler (ID `unspecified` in the logs; M6242 appears only in the 07/30 screenshots), front positions 1-256 and rear 257-512, 2026-09-01 to 2026-10-02; the 07/30 trial run is excluded (A6). Capacity here means the share of positions able to test; it is not OEE.
- **Definitions agreed**: `02-documentation-knowledge/semiconductor-metric-definitions/assets/metric_definition.yaml` (version 5) and the assumptions log: 11 confirmed, 6 applied but unconfirmed (A9, A12, A17, A18, A19, A20), 3 open (A11, A13, A14).

## Data feeds
| Feed | Status | Note |
|---|---|---|
| contactor-site logs, front and rear | available | `dat/`, private; read through `lib/contactor_io.py` |
| run / idle / jam / down history | missing | needed for time-based OEE |
| output counts, good units and bin results | missing | needed for performance and quality |
| ideal cycle time | missing | needed for performance |
| planned production calendar | missing | A11 open |
| maintenance and contactor-change records | not known to exist | needed to check events against reality |
| screenshots of the Sep/Oct closed positions | missing | needed for the chronic-site review |

## Deliverables and dates
No deadline has been set ([OPEN]). Current deliverables and their state:
| Deliverable | Path | State |
|---|---|---|
| analysis document | `02-documentation-knowledge/analysis-documentation/assets/handler_utilization_analysis_sep_oct_2026.md` | done, reproducible |
| validation report | `01-data-quality-validation/contactor-log-validation/assets/validation_report_sep_oct_2026.md` | done, decisions per flagged day |
| closed-now report | `04-data-storytelling-visualization/visualization-builder/scripts/site_heatmap.py` | done, generated |
| dashboard spec | `04-data-storytelling-visualization/dashboard-specification/assets/dashboard_spec_sep_oct_2026.md` | specified, not built |
| executive summary and insight brief | `04-data-storytelling-visualization/executive-summary-generator/assets/executive_summary_sep_oct_2026.md` | done, owners open |
| methodology explainer and translations | `05-stakeholder-communication/methodology-explainer/assets/methodology_writeup_sep_oct_2026.md` | done, reader test not done |
| QA sign-off | `05-stakeholder-communication/analysis-qa-checklist/assets/qa_signoff_sep_oct_2026.md` | ready for review, not signed off |

## Success criteria
Each is testable and mapped to a requirement in `assets/requirements_sep_oct_2026.md`.
- SC1 (R1): the headline is the same in every deliverable and reproducible from the code.
- SC2 (R2): the closed-now list comes from the recency view and is reproduced by a script.
- SC3 (R3): faults injected into newly delivered data are detected automatically.
- SC4 (R4, R5): alerts fire at a tolerable rate (pages under about one a week) and have owners; the dashboard is built.
- SC5 (R6): OEE is reported only when availability, performance and quality are all measured.
- SC6 (R10): every release has an independent sign-off and a passing QA run.

## Risks
- Screen-read quality: failed and garbled readings (about 3% dropped; some unflagged bands remain, A14).
- No ground truth: no screenshots or maintenance records to check closed groups and events against.
- OEE blocked: the stated goal (time-based utilization) cannot be met without the missing feeds.
- Short history: 32 days give low power; a shift under about 2 points cannot be detected.
- Applied-but-unconfirmed rules (A9, A12, A17, A18, A19, A20) could change statuses and a few tenths of a point.
