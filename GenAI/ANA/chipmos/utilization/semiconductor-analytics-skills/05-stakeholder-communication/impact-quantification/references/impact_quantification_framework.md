# Impact Quantification Framework

```
site_equivalents(window) = sum over the groups' sites of the share of the last <window> days each was closed   (window = 3, 7, 14 days)
gain_units_per_hour      = site_equivalents x units/h per site                  (0 if the handler is not capacity-constrained)
gross_value              = gain_units_per_hour x hours/day x days x margin per unit x P(repair holds)
downtime_loss            = repair_downtime_days x hours/day x sites_offline x units/h per site x margin   (0 if not constrained)
net_value                = gross_value - downtime_loss - repair_cost
```
- **Range, not a point**: low / mid / high use the 3-, 7- (mid) and 14-day windows. The whole-period average is history and is never used for a forward estimate. The count-versus-list gap (closures the list may have missed) widens the real range further and is not modelled.
- **Capacity constraint is a precondition**: idle sites that are not needed cost nothing. State whether the handler is constrained before any value is computed.
- **Repair risk**: P(repair holds) multiplies the gain; repair downtime takes sites offline while it lasts.
- Do not double-count with Performance in OEE; OEE stays blocked until its data exist.
- No parameter has a default. A parameter without a source, owner and date is not an input.

## Evaluating a real estimate (after the deferral is lifted)
1. Every parameter has a source, owner and date; finance approved the margin.
2. Recovered capacity <= the handler's capacity and reconciles with real output counts.
3. Low / mid / high shown; the conclusion survives the low case or says it does not.
4. Backtest on a past repair: did output rise by about the predicted amount?
5. The deliverables carry the figures only after `status.json` is lifted, with their provenance.
