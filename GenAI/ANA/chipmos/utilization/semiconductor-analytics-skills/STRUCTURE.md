# Repository Structure

```
semiconductor-analytics-skills/
├── README.md  QUICKSTART.md  STRUCTURE.md  CLAUDE.md
├── validate_skills.py          # SKILL.md structure validator
├── lib/contactor_io.py         # shared loader: all cleaning rules, time weights, site matrix
├── 01-data-quality-validation/   (2 skills)
├── 02-documentation-knowledge/   (4 skills)
├── 03-data-analysis-investigation/ (5 skills)
├── 04-data-storytelling-visualization/ (4 skills)
├── 05-stakeholder-communication/ (5 skills)
├── 06-workflow-optimization/     (5 skills)
└── out/                        # generated reports, logs (git-ignored)
```

Every skill: `SKILL.md` (frontmatter + When to use / Process / Inputs the skill needs / Output), optional `scripts/`, `references/`, `assets/`.

| Stage | Skill | scripts | references | assets |
|---|---|:-:|:-:|:-:|
| 01 | contactor-log-validation | 3 | 2 | 1 |
| 01 | contactor-log-eda | 2 | 1 | 1 |
| 02 | handler-data-catalog | 1 | 1 | 1 |
| 02 | analysis-assumptions-log | 1 | 1 | 1 |
| 02 | semiconductor-metric-definitions | 1 | 1 | 1 (yaml) |
| 02 | analysis-documentation | - | 1 | 1 |
| 03 | site-availability | 1 | 1 | 1 |
| 03 | chronic-site-detection | 1 | 1 | 1 |
| 03 | downtime-time-series | 1 | 1 | 1 |
| 03 | closure-event-root-cause | 1 | 1 | 1 |
| 03 | oee-calculator | 1 | 1 | 1 |
| 04 | visualization-builder | 1 | 2 | 1 |
| 04 | dashboard-specification, insight-synthesis, executive-summary-generator | - | 2 each | 1 each |
| 05 | technical-to-business-translator | 2 | 3 | 1 |
| 05 | stakeholder-requirements-gathering | - | 2 | 3 |
| 05 | impact-quantification | 1 | 2 | 2 |
| 05 | analysis-qa-checklist | 1 | 2 | 1 |
| 05 | methodology-explainer | - | 2 | 2 |
| 06 | analysis-planning | - | 3 | 2 |
| 06 | pipeline-automation | 1 | 1 | 3 (sql, dag, runbook) |
| 06 | context-packager | 1 | 2 | 1 |
| 06 | peer-review-template | - | 3 | 2 |
| 06 | analysis-retrospective | - | 2 | 2 |

Status: `impact-quantification` is deferred (no real business parameters yet); OEE is blocked (no run-state, output, good-unit, cycle-time data).

Differences from the reference repo: a shared `lib/` (scripts import it instead of being fully standalone, so cleaning rules exist once); no `skill-map.svg`.
