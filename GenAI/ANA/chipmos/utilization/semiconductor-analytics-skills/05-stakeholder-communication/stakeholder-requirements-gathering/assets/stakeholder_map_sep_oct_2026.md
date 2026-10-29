# Stakeholder Map - handler contactor capacity analysis

Names are not yet known: every name is `[OPEN]` until the process owner fills them. Roles below are the ones the questions, requirements and sign-offs refer to.

## Roles and decision rights
| Role | Name | Decides | Needs from the analysis | Decision rights |
|---|---|---|---|---|
| process owner | [OPEN] | what the data means and how it is cleaned; confirms assumptions | definitions, rules, effects and open questions | confirms data semantics and cleaning rules (A1-A20); accepts the analysis brief and requirements; signs off definitions |
| equipment / maintenance lead | [OPEN] | when to inspect or replace contactors and HIFIX boards | closed-now groups, event times, alert volume | accepts actions and alert rules; owns the dashboard's alerts |
| production planner | [OPEN] | scheduling around downtime; planned production time | capacity trend, planned versus actual | owns the planned-time calendar (A11) |
| data / capture owner | [OPEN] | capture pipeline, validity flags, retention | data-quality findings, schema | owns the CSV semantics and any capture change |
| process engineer | [OPEN] | whether a physical cause is real | event timeline, block alignment | confirms or refutes the physical-cause hypothesis (A13) |
| finance / business owner | [OPEN] | whether a repair or investment pays back | the business case (deferred) | approves margin and cost parameters before the deferral is lifted |
| reviewer | [OPEN] | whether a release may go out | QA results, waivers, sign-off | independent sign-off (not the author) |
| analyst | Claude (draft) | method and presentation | all inputs | builds and documents; cannot confirm assumptions or sign off |

"Process owner" in the assumptions log (`source: process owner (chat)`) means the person who answered the data and rule questions during the project; that person and role must be named here.

## Who is accountable for what
| Deliverable | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| analysis document and metric definitions | analyst | process owner | process engineer | managers |
| daily validation decisions | analyst | process owner | data / capture owner | equipment / maintenance lead |
| dashboard and alerts | analyst | equipment / maintenance lead | data / capture owner | production planner |
| business case (deferred) | analyst | finance / business owner | equipment / maintenance lead | process owner |
| QA sign-off | analyst | reviewer | process owner | everyone above |
