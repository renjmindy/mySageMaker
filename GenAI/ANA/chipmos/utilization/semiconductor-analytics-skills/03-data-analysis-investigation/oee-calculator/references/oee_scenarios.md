# OEE Scenarios for This Project

| Stage | Inputs available | Result |
|---|---|---|
| Today | contactor logs only | site availability (front/rear) - capacity factor, **not OEE**; OEE BLOCKED |
| Next | + run/idle/down timeline from Main screen / handler log | time availability A |
| Then | + output counts and ideal cycle time | Performance P (use effective parallelism) |
| Full | + good/total (bin results) | Quality Q -> OEE |

Parallelism and site availability: `ideal_cycle_min` is minutes per unit at the handler level with all sites open (not per site). Closed sites reduce output against that full-capacity ideal, so they lower **Performance** - the loss is counted once, inside P. With `a` = site availability, the calculator can split P = a x (P / a): a site-capacity part and a speed/other part (a "speed/other" factor above 100% means `a` is understated or the ideal cycle is too large). This is a decomposition for explanation; it never multiplies into OEE.

Inputs are validated: negative values, good > output, run > planned, planned = 0, output without run time and Performance > 100% are rejected as INVALID instead of producing a number. Zero is a value (no run time or no output gives OEE = 0), not a missing input.
