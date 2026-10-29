---
name: context-packager
description: Bundle the essential context of the utilization analysis into one compact, generated file for a new analyst or an AI assistant session - a header with status, what not to do, next steps and how to reproduce; the rules with unconfirmed ones marked; the headline recomputed from the data; the open decisions and QA state. Refuses stale or over-budget packages. Activate on handover, before asking an assistant to continue the work, or when a conversation gets too long.
---

# When to use
- Handing the project to a colleague
- Starting a fresh AI-assistant session without losing the data rules or the things it must not do
- Archiving the state of the analysis at a commit

# Process
1. **Run the pipeline first** — `daily_pipeline.py` writes `out/pipeline/<run>/summary.json`; the bundler rejects a summary that is older than the newest data file, that disagrees with a recomputation, or that has a failed step.
2. **Bundle** — `python scripts/context_bundler.py` builds the layers (`references/context_layering_guide.md`): header, rules, state (and history only with `--with-history`). Everything is derived from the assumptions log, the metric definitions, the requirements, the plan, the generated open questions, the QA sign-off and waivers; the headline is recomputed from the data, not copied.
3. **Respect the budget** — rules and state together must fit 8,000 tokens (estimated at chars/3, pessimistic); the bundler refuses to write otherwise. Fix the sources, not the number.
4. **Check it** — `python scripts/context_check.py` (also run by the QA gate with the pipeline-freshness item skipped, because the pipeline calls the gate before it writes its summary). The rubric in `references/context_quality_rubric.md` maps each item to a check.
5. **Give the reader the cold-start test** — someone new, or a fresh assistant session, reads only the package and says what is blocked, unconfirmed and next. This is the one part a script cannot do.
6. **Store** at `out/context_package.md` (git-ignored; the package carries no raw data, secrets or private paths).

# Inputs the skill needs
- Required: the repository with an up-to-date assumptions log, metric definitions, requirements, plan and QA sign-off; the data folder; a fresh pipeline run
- Optional: a different token budget, `--with-history`

# Output
- `out/context_package.md` — the compact context bundle
- `assets/context_package_template.md` — the sections the header must have (the checker compares the generated header with it)
- `scripts/context_bundler.py` (build), `scripts/context_check.py` (PASS / FAIL per check) and `scripts/test_context_check.py` (tests that break the package one way at a time)
