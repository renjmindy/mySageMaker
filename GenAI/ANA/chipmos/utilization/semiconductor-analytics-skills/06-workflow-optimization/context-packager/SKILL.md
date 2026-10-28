---
name: context-packager
description: Bundle the essential context of the utilization analysis (definitions, assumptions, latest results, open questions) into one compact file for a new analyst or an AI assistant session. Activate on handover, before asking an assistant to continue the work, or when a conversation gets too long.
---

# When to use
- Handing the project to a colleague
- Starting a fresh AI-assistant session without losing the data rules
- Archiving the state of the analysis

# Process
1. **Choose layers** (`references/context_layering_guide.md`): rules (must have), results, history.
2. **Bundle** — `scripts/context_bundler.py` concatenates `lib/contactor_io.py` docstring rules, the assumptions log, metric definitions and the latest pipeline summary.
3. **Check the size** — estimate tokens (chars/4); trim to the budget.
4. **Check quality** with `references/context_quality_rubric.md`.
5. **Fill `assets/context_package_template.md`** with the project-specific header.
6. **Store with the repo** (`out/context_package.md`).

# Inputs the skill needs
- Required: repository with up-to-date assumptions log and metric YAML
- Optional: latest `out/pipeline/*/summary.json`, token budget

# Output
- `out/context_package.md` — compact context bundle
- `assets/context_package_template.md` (filled) — header and reading order
