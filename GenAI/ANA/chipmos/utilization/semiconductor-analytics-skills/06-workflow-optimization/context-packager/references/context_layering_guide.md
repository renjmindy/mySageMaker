# Context Layering

The bundler builds four layers, in this order, and `scripts/context_check.py` verifies the order.

| Layer | Contents | In the budget? |
|---|---|---|
| header | status (requirements and plan phases), what not to do, next steps, how to reproduce, commit hash | yes |
| rules | loader rules, assumptions (unconfirmed ones marked), metric definitions (latest version only) | yes |
| state | headline recomputed from the data, pipeline freshness, open decisions, QA sign-off and waivers | yes |
| history | older metric versions, learnings, retrospective actions - **only with `--with-history`** | no |

- Budget: 8,000 tokens for header + rules + state, estimated at characters / 3. That is deliberately pessimistic: tables, YAML and identifiers use more tokens than ordinary prose, and no tokenizer is installed to measure them. The bundler refuses to write a package over budget; shorten the source documents, do not raise the number to fit.
- History is kept out because it contains superseded wording (for example the old weighting statements) that a reader could mistake for a rule. It is labelled as history and is the only place that wording may appear.
- Layers are generated from the project's files. Edit the source (the assumptions log, the plan, the requirements), never the package.
