# OEE for Test Handlers

Formulas from the project docs (`doc/auto_architecture_*.png`):

- Time availability = actual run time / (planned load time) x 100%, load time = total time - planned downtime
- Performance = actual output x ideal cycle time / actual run time
- Quality = good units / total units
- OEE = A x P x Q (docs' demo: 400/480 min, 380 out, 370 good -> 83.3% x 95.0% x 97.4% = 77.1%)

## Two availabilities - do not mix them
| Name | Question | Source today |
|---|---|---|
| **Site availability** (capacity) | How many of the 256 contactor sites per side can test? | contactor CSVs - available |
| **Time availability** (OEE A) | What share of planned time was the handler running? | run-state log - **not available yet** |

A handler can have 100% time availability yet 90% site availability (it runs, with fewer parallel sites).
Site availability is the throughput-capacity factor; it can be folded into Performance once cycle-time and output
data exist (effective parallelism = open sites / 256).

## Semiconductor test cautions
- Parallel sites -> UPH scales with open sites; closures reduce Performance, not just Availability.
- Retest / first-pass vs final yield change Quality; define which one.
- Trial/engineering lots (e.g. lot TRIAL) are excluded from OEE.
