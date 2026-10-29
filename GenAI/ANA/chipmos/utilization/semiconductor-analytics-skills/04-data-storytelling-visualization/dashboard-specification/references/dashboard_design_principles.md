# Dashboard Design Principles

1. Top row = answer: share able to test per side with a plausible range and a lower bound (never a single exact figure), and how many positions are closed *now*.
2. Middle = diagnosis: the handler's grid for the last 7 days, the ranked "closed now" table, the daily trend with its range band. A period-wide Pareto is a **history** view and must be labelled so; the action list is the recency view.
3. Bottom = detail: aligned closure groups with duration, not every blip.
4. Capture health is its own row: dropped-reading rate, coverage and the age of the last reading. A capture problem must never look like a closed-position problem (data-health panels read only capture data).
5. Alerts evaluate debounced episodes, never a single reading, and every alert is backtested: state its rate per week on the history, its owner and the action. "Below the average" rules are noise; keep "page" for rules under about one a week.
6. OEE is a blocked panel with no number until the run and idle time, output, good-unit and cycle-time data exist.
7. Every number links to its metric definition and shows the cleaning rules.
8. One schema: panels read the tables in the single schema file; nothing is redefined in the spec.
