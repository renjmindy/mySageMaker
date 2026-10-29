# Dashboard Requirements Questions

- Who reads it, how often, on which screen (fab floor TV / desktop / mobile)?
- Which handlers and how many sites (M6242: 2 x 256)?
- What action follows an alert? Who owns it?
- Which time ranges (shift, day, week)?
- Do we have run-state, output and good-unit feeds for OEE panels yet? (not today)
- Who owns the dashboard, the data, and each alert? Who is paged, and at what hours?
- What is the tolerated alert volume per person per week? (the backtest shows what each rule would have produced)
- Is there a real PostgreSQL/Timescale instance to dry-run the queries on, and which visual will draw the 16x16 grid?
- What are the capture-to-database latency and the raw-data retention?
