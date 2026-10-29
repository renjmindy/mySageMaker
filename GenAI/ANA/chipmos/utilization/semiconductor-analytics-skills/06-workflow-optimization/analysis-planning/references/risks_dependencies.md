# Risks and Dependencies

## Risk register (in the plan)
Columns: id, risk, likelihood and impact (low / medium / high), trigger, mitigation, owner role (from the stakeholder map), status (open / materialised / mitigated), evidence.
- A **materialised** risk cites the evidence that it happened; a **mitigated** one cites the artifact that enforces the mitigation (a script, a guard, an ignore file). `scripts/plan_check.py` verifies the paths exist.
- The register must contain risks that actually materialised in this project (screen-read quality, documentation drifting from the code); a register with only hypothetical risks has not been reviewed.

## Dependencies (in the plan)
Columns: dependency, needed by (phase), provider role, ask, status, impact if missing.
- The provider is a role in the stakeholder map; the **ask** is a theme or assumption id in `question_registry.json`, so every dependency is also a question the interview guide generates. No dependency is described only in prose.
- A blocked or deferred phase has at least one dependency.
