# Impact Quantification Framework

```
recovered_site_equivalents = sum over recovered sites of time-weighted closed share
recovered_units/h = recovered_site_equivalents x units/h per site
value = recovered_units/h x operating hours x margin per unit - repair cost
```
- Use ranges: list-based vs count-based closures; repair holds 100% vs 50%.
- Count capacity only if the handler is actually capacity-constrained (otherwise value is zero - idle sites that are not needed cost nothing).
- Do not double-count with Performance in OEE.
