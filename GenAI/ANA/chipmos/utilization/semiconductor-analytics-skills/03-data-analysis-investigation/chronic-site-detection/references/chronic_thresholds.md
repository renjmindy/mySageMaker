# Chronic-Site Thresholds

| Class | Closed share | Meaning |
|---|---|---|
| chronic | >= 50% | persistently down over the period - maintenance candidate |
| frequent | 10-50% | closed for part of the period (e.g. until a fix / after a fault) |
| occasional | < 10% | transient; mostly OCR/noise or short events |

Caveats
- A share of 30-50% with a sharp on/off boundary on a given day means the site was fixed or failed on that date - check `closure-event-root-cause`.
- Single-ID flicker (e.g. 91 vs 97 alternating) is OCR noise, not a closure.
- Aligned 2x2 blocks closing together (rows 2k-1,2k x cols 2j-1,2j) suggest a shared cause; confirm with the process owner (assumption A13).
