# Translations - handler capacity findings, Sep-Oct 2026

Source: `04-data-storytelling-visualization/insight-synthesis/assets/insight_brief_sep_oct_2026.md` and the analysis document. Each technical statement is the finding as written for analysts; each plain version is for the persona named. `scripts/translation_check.py` verifies numbers, caveats, language, readability and position words; the persona policies are in `references/stakeholder_personas.md`.

## Persona: manager (equipment or operations manager; OEE allowed)
| Technical statement | Plain-language version |
|---|---|
| Front 91.32% (lower bound 90.88%, plausible range 90.57-92.08%) and rear 96.07% (lower bound 95.64%, plausible range 95.30-96.83%) of positions able to test; OEE is blocked until run-state, output, good-unit and cycle-time data exist. | On average 91% of front test positions and 96% of rear positions were able to test. The front could be as low as 90.9%, and the month's average is plausibly between 90.6% and 92.1% (rear 95.3% to 96.8%). OEE cannot be reported yet. |
| Three front groups are closed now: 7.05 pts together in the last 7 days; 20 of 256 front sites (7.8%) are closed and the same groups were closed earlier (PERSISTENT, top-20 overlap 17/20). | Three groups of front test positions are out of service right now and cost about 7 points of front capacity last week. In all, 20 of the 256 front positions (7.8%) are out. The same groups were out earlier in the month, so this is not a short blip. |
| Rear sites 419/420/435/436 are NEW: 0.39 pts over the period, 1.53 pts in the last 7 days (0.82 pts with a 14-day window); the older groups are INTERMITTENT, closed about 30% of the last week. | One group of four rear positions broke recently. It cost about 1.5 points of rear capacity last week, or 0.8 points over two weeks. The older rear problem groups are only partly out now, about 30% of the time. |
| The 252-255 rule raises the front headline by 1.3 pts versus counting only 256 as a failed reading; 3.06% of front and 3.37% of rear readings are dropped. | Our front figure is about 1.3 points higher because we leave out screen readings that clearly failed. About 3% of readings were left out on both sides. |
| No level shift (front +1.08 pts, p = 0.669; rear +1.91 pts, p = 0.112); daily standard deviation about 2.2 pts; differences under about 1.5 pts cannot be told apart from noise. | Capacity did not clearly rise or fall over the month. Day-to-day swings of about 2 points are normal, so a change smaller than about 1.5 points should not be read as real. |

## Persona: engineer (test floor or equipment engineer; may use position, row and column)
| Technical statement | Plain-language version |
|---|---|
| Front closed now: sites 143/144/159/160/175/176/191/192 (3.03 pts), 197/198/213/214/229/230/245/246 (2.91 pts) and 3/4/19/20 (1.11 pts) over the last 7 days. | Three groups are closed now. Group one is positions 143, 144, 159, 160, 175, 176, 191 and 192 (rows 9 to 12, right edge of the front grid). It costs 3.03 points. Group two is positions 197, 198, 213, 214, 229, 230, 245 and 246 (rows 13 to 16, near the top). It costs 2.91 points. Group three is positions 3, 4, 19 and 20 (rows 1 and 2, bottom left). It costs 1.11 points. |
| Rear sites 419/420/435/436 are NEW (1.53 pts in the last 7 days, 0.39 pts over the period); 463/464/479/480 and 291/292/307/308 are INTERMITTENT, closed about 30% of the last week. | Positions 419, 420, 435 and 436 (rows 27 and 28, left side of the rear grid) broke recently. They cost 1.53 points last week but only 0.39 over the whole period. Positions 463, 464, 479 and 480 (rows 29 and 30, right edge) are closed only about 30% of the time now. So are positions 291, 292, 307 and 308 (rows 19 and 20, left side). |
| 6 of 24 front hours and 8 of 24 rear hours stand out (about 1.1 expected by chance), but 0 of 24 once readings with 60 or more closed sites are excluded (99 front, 50 rear readings). | Some hours of the day look different: 6 of 24 front hours and 8 of 24 rear hours. Chance would give about 1. The difference disappears when the unusually large readings are left out (99 front, 50 rear). So there is no steady time-of-day effect. These readings are not yet explained. |

## Persona: customer (quality or customer contact; no internal terms)
| Technical statement | Plain-language version |
|---|---|
| 3.06% of front and 3.37% of rear readings are dropped; front 09/09 had 27.7% unusable readings and is kept with a caveat; excluding it moves the front headline by 0.01 pt. | About 3% of screen readings were unusable and are left out of every figure. One day, 9 September, had many more unusable readings, so figures for that day carry a caution. Leaving that day out would change the front figure by only about 0.01 points. |
| OEE is blocked until run and idle time, output, good-unit and cycle-time data exist; only the share of test positions able to test is measured. | We can say how many test positions are working, but not yet how much of the planned time the handler produced. That needs run time, output and yield data that we do not have yet. |
<!-- derived-numbers: 7.05 = 3.03+2.91+1.11 -->
