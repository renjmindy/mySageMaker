# Dashboard Design Principles

1. Top row = answer: front and rear availability stat tiles with trend arrow and data-quality badge.
2. Middle = diagnosis: site grid (physical layout), chronic-site Pareto, daily trend.
3. Bottom = detail: event table (time, sites, aligned-block share), read-failure rate.
4. Every number shows its validity rules on hover (links to metric definitions).
5. Never alert on a single sample: debounce over >= 5 samples (~20 min).
6. Separate **data health** (capture OK?) from **equipment health** (sites closed).
