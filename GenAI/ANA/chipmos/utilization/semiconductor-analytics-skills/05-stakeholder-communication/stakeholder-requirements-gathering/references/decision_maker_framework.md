# Decision-Maker Framework

The filled map for this project is `assets/stakeholder_map_sep_oct_2026.md`. For any project:

| Role to identify | Decides | Needs from the analysis |
|---|---|---|
| process owner | what the data means, how it is cleaned, which assumptions hold | definitions, rules, effects, open questions |
| equipment / maintenance lead | when to inspect or replace contactors and boards | what is closed now, event times, alert volume |
| production planner | scheduling around downtime; planned production time | capacity trend, planned versus actual |
| data / capture owner | capture pipeline, validity flags, retention | data-quality findings, schema |
| process engineer | whether a physical cause is real | event timeline, block alignment |
| finance / business owner | whether a repair pays back | the business case (when its parameters exist) |
| reviewer | whether a release may go out | QA results, waivers |

Rules: every role has a name (an unnamed role is an open item, not a blank); every deliverable has one accountable role; an answer counts only from the role that holds the decision right (a data question answered by someone who does not own the data stays "applied, not confirmed").
