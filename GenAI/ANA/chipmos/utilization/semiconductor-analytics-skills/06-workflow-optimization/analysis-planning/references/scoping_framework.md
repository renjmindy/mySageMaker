# Scoping Framework

- **In scope now**: site capacity per side with a range, the closed-now view and ranked list, closure events, the data-quality gate and definitions, the dashboard specification, plain-language and method explanations, QA sign-off.
- **Out of scope until the feeds exist**: time-based utilization (OEE): run / idle history, output, good units, cycle time and the planned-time basis.
- **Deferred by decision**: the business case in units and money (until real business parameters exist; see `impact-quantification/status.json`).
- **Never in scope**: trial lots and engineering runs.

## Rule
A metric is in scope when its **input feed exists**. A missing owner is a tracked open item (the stakeholder map and the generated question guide), not a reason to stop analysing. But numbers are not released outside the analytics team until the process owner has named an owner for each metric and an independent reviewer has signed off (phase P7).

An earlier version of this rule required a named owner for every in-scope metric; applied literally no metric would have been in scope, yet the work proceeded. The rule above states what actually happens and where the gate really is.
