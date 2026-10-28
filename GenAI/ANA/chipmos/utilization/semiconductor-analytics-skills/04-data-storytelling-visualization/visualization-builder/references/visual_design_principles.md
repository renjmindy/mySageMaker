# Visual Design Principles (applied in `site_heatmap.py`)

- **Colour follows the job**: magnitude = single-hue sequential ramp (light = near zero in light mode, dark = near zero in dark mode); identity = fixed categorical slots (front = blue, rear = orange).
- **One axis**: availability only, y from a rounded floor to 100%.
- **Direct labels** at line ends plus a legend for the 7 closure buckets; text uses ink tokens, not series colours.
- **Hover**: every cell and point has a tooltip (site, row/col, closed share; day, value). A **table view** is included for non-visual access.
- **Dark mode** is a separate selected step ramp validated against the dark surface, not an inversion.
- **Context first**: title says what is plotted; subtitle states cleaning rules and period.
