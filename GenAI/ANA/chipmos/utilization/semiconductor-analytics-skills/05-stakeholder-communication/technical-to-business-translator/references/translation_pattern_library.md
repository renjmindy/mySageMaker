# Translation Patterns

Every row is machine-checked by `scripts/translation_check.py` (numbers kept and none invented, caveats kept, position words match the handler grid, language for the manager persona, readability). Add a row only when it passes.

| Technical | Plain |
|---|---|
| "Front availability 91.3% (time-weighted, broken readings excluded)" | "On average 9 of every 100 front test positions could not test; readings that were clearly broken were left out." |
| "Cluster 229/230/245/246 closed 92% of the period" | "Four neighbouring positions (229, 230, 245, 246) at the top of the front grid are almost always out of service." |
| "The reported count is never below the list length (list under-reports closures)" | "A position counts as closed only if we can see it in the list. The true number may be slightly higher." |
| "OEE blocked: no run-state feed" | "We can say how many positions work, but not yet how much of the planned time the handler produced." |

## How to add one
1. Write the technical statement exactly as it appears in the analysis (numbers must trace to the analysis document).
2. Write the plain version for the manager persona; keep the headline number (or its complement as "N of every 100") and every caveat.
3. If it names positions, give the direction in words only if the checker agrees: the handler grid has row 16 (front) / row 32 (rear) on top and column 1 on the left. Earlier versions of this table said "near the bottom" for positions 229/230/245/246, which are in rows 15-16 - the top; the checker now rejects that.
4. Run `python scripts/translation_check.py`.
