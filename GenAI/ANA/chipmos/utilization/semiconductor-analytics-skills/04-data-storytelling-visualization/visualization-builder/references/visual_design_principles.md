# Visual Design Principles (applied in `site_heatmap.py`, enforced by `viz_check.py`)

- **Colour follows the job**: magnitude = one-hue sequential ramp of six buckets (<5%, 5-10%, 10-25%, 25-50%, 50-75%, 75%+); identity = fixed categorical slots (front = blue, rear = orange, validated pair).
- **Ramp rule**: lightness monotonic and adjacent steps >= 8 (OKLab x100) in light and dark; light mode = light is near zero, dark mode = dark is near zero (its own steps, not an inversion). Merging the first two buckets into "<5%" removed a step that was too close to tell apart and sits at the OCR noise floor.
- **One axis**: availability only, y from a rounded floor to 100%.
- **Uncertainty is part of the chart**: tiles show a plausible range and a lower bound; the line carries each side's range as a band.
- **Direct labels + legend**: line-end labels, a legend for the two series and the band, a legend for the six buckets. Text uses ink tokens, not series colours.
- **Every reader**: radio toggle (keyboard), arrow keys read every cell into an aria-live region, tooltips on hover and tap, a ranked table (the accessible and phone route to the data), a table view of the daily numbers.
- **Every screen**: no horizontal page scroll down to 375 px; on narrow or touch screens the grid keeps >= 24 px cells and scrolls inside its card.
- **Plain language**: "test positions", "able to test", "plausible range"; no site/availability/interval/near-full jargon in visible text.
- **Context first**: title says what is shown; subtitle gives the date range and the one rule readers need (readings weighted by duration, unreadable readings left out).
