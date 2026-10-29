"""
Bundle the project's context into one Markdown file for a new analyst or an AI assistant session.

Everything is derived from the project's own files, nothing is typed here:
  header  - status (requirements and plan), what not to do, next steps, how to reproduce, commit hash
  rules   - loader rules, assumptions (unconfirmed ones marked, blank sources shown), metric definitions (latest version)
  state   - headline recomputed from the data (not copied from an old run), pipeline freshness, open decisions
            from the assumptions log and the open markers, QA sign-off and waivers
  history - only with --with-history: older metric versions (including superseded wording), learnings, actions

The package is written only if the pipeline summary is fresh and the budget holds (tokens are estimated at
chars/3, deliberately pessimistic for tables and YAML). `context_check.py` verifies the result.

Usage:
    python context_bundler.py
    python context_bundler.py --budget-tokens 9000 --with-history --output ../../../out/context_package.md
"""

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
BASE = HERE.parents[1]
for sub in ("lib", "02-documentation-knowledge/analysis-assumptions-log/scripts", "03-data-analysis-investigation/site-availability/scripts",
            "03-data-analysis-investigation/chronic-site-detection/scripts", "05-stakeholder-communication/stakeholder-requirements-gathering/scripts",
            "06-workflow-optimization/analysis-planning/scripts"):
    sys.path.insert(0, str(ROOT / sub))
import assumptions_tracker as at  # noqa: E402
import chronic_sites as cs  # noqa: E402
import contactor_io as cio  # noqa: E402
import deferral  # noqa: E402
import open_questions as oq  # noqa: E402
import plan_check as pc  # noqa: E402
import pandas as pd  # noqa: E402
import site_availability as sa  # noqa: E402

METRIC = ROOT / "02-documentation-knowledge/semiconductor-metric-definitions/assets/metric_definition.yaml"
SIGNOFF = ROOT / "05-stakeholder-communication/analysis-qa-checklist/assets/qa_signoff_sep_oct_2026.md"
WAIVERS = ROOT / "05-stakeholder-communication/analysis-qa-checklist/qa_waivers.json"
LEARNINGS = ROOT / "06-workflow-optimization/analysis-retrospective/assets/learnings_log_sep_oct_2026.md"
RETRO = ROOT / "06-workflow-optimization/analysis-retrospective/assets/retrospective_sep_oct_2026.md"
TEMPLATE = BASE / "assets" / "context_package_template.md"
RECENT_DAYS = 7
COMMANDS = [
    ("06-workflow-optimization/pipeline-automation/scripts/daily_pipeline.py", "full run; writes out/pipeline/<run>/summary.json"),
    ("03-data-analysis-investigation/site-availability/scripts/site_availability.py", "the headline with its range"),
    ("05-stakeholder-communication/analysis-qa-checklist/scripts/qa_runner.py --with-doc-check", "the QA gate"),
]


def estimate_tokens(text: str) -> int:
    """Pessimistic: chars/3 (plain chars/4 undercounts tables, YAML and identifiers)."""
    return -(-len(text) // 3)


def git_state(root: Path = ROOT):
    """(short commit, has uncommitted changes to tracked files); (None, None) if git cannot answer."""
    try:
        h = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=20)
        d = subprocess.run(["git", "-C", str(root), "diff", "--quiet", "HEAD", "--", str(root)], capture_output=True, timeout=20)
        return (h.stdout.strip(), d.returncode != 0) if h.returncode == 0 else (None, None)
    except (OSError, subprocess.SubprocessError):
        return None, None


def fresh_state(data_dir=None, recent_days: int = RECENT_DAYS) -> dict:
    """Headline numbers recomputed from the data through the shared loader."""
    folder = Path(data_dir or cio.DEFAULT_DATA_DIR)
    out = {"data_mtime": max((f.stat().st_mtime for f in folder.glob("contactor*.csv")), default=0.0), "sides": {}}
    for side in cio.SIDES:
        df = cio.load_side(side, data_dir)
        o = sa.overall(df)
        lo, hi = sa.bootstrap_ci(df)
        mat = cio.closed_matrix(df, side)
        recent = cs.window_share(mat, start=mat.index.max() - pd.Timedelta(days=recent_days))
        out["sides"][side] = {"availability": float(o["availability_high_pct"]), "lower_bound": float(o["availability_low_pct"]),
                              "ci_low": round(lo * 100, 2) if lo <= 1.5 else round(lo, 2), "ci_high": round(hi * 100, 2) if hi <= 1.5 else round(hi, 2),
                              "closed_now": int((recent >= 0.5).sum()), "last_reading": mat.index.max().strftime("%Y-%m-%d %H:%M")}
    return out


def pipeline_info(state: dict, root: Path = ROOT) -> dict:
    """Latest pipeline summary and why it can or cannot be trusted."""
    runs = sorted((root / "out" / "pipeline").glob("*/summary.json")) if (root / "out" / "pipeline").exists() else []
    if not runs:
        return {"run": None, "problems": ["no pipeline run: run daily_pipeline.py first"]}
    s = json.loads(runs[-1].read_text(encoding="utf-8"))
    problems = []
    try:
        started = dt.datetime.strptime(s["run"][:15], "%Y%m%d_%H%M%S").timestamp()  # a suffix (_2) marks a second run in the same second
        if started < state["data_mtime"]:
            problems.append(f"pipeline run {s['run']} is older than the newest data file")
    except (KeyError, ValueError):
        problems.append("pipeline summary has no readable run time")
    if s.get("status") not in (None, "ok"):
        problems.append(f"pipeline run status is {s['status']}")
    for side, v in (s.get("availability_pct") or {}).items():
        if side in state["sides"] and abs(v - state["sides"][side]["availability"]) > 0.006:
            problems.append(f"pipeline {side} {v} differs from the recomputed {state['sides'][side]['availability']}")
    bad = [k for k, v in (s.get("steps") or {}).items() if v != "ok"]
    if bad:
        problems.append(f"pipeline steps not ok: {', '.join(bad)}")
    return {"run": s.get("run"), "steps": s.get("steps", {}), "problems": problems}


def trim_changelog(yaml_text: str) -> tuple[str, list[str]]:
    """Keep only the latest changelog entry; return (trimmed text, removed lines)."""
    lines = yaml_text.splitlines()
    try:
        i = lines.index("changelog:")
    except ValueError:
        return yaml_text, []
    j = i + 1
    while j < len(lines) and lines[j].startswith("  "):
        j += 1
    entries = lines[i + 1:j]
    keep = entries[:1]
    return "\n".join(lines[:i + 1] + keep + ["  # older versions (including superseded wording): history layer, --with-history"] + lines[j:]), entries[1:]


def assumptions_section(items: list[dict]) -> str:
    rows = ["| ID | Category | Statement | Status | Impact | Source | Date | Note |", "|---|---|---|---|---|---|---|---|"]
    for a in items:
        rows.append(f"| {a['id']} | {a['category']} | {a['statement']} | {a['status']} | {a['impact']} | "
                    f"{a.get('source') or 'none (unconfirmed)'} | {a.get('date') or '-'} | {a.get('note', '')} |")
    pending = [f"- {a['id']} ({a['status']}): {a['statement'][:110]}" for a in items if a["status"] != "CONFIRMED"]
    return ("## 2. Assumptions log\nCONFIRMED = the process owner said so (source and date shown). APPLIED = the analyst's design choice is in use but not confirmed. "
            "OPEN = undecided. Say which when you use a rule.\n" + "\n".join(rows) + "\n\n### Not confirmed by the process owner\n" + "\n".join(pending))


def open_decisions(assumptions: list[dict]) -> str:
    registry = json.loads(oq.REGISTRY.read_text(encoding="utf-8"))
    markers = oq.scan_markers()
    lines = ["### Decisions to confirm", "| Id | Status | Question | Ask |", "|---|---|---|---|"]
    for a in sorted((x for x in assumptions if x["status"] in ("OPEN", "APPLIED")), key=lambda x: int(x["id"][1:])):
        r = registry["assumptions"].get(a["id"])
        if r:
            lines.append(f"| {a['id']} | {a['status']} | {r['question']} | {r['ask']} |")
    lines += ["", "### Open items in the deliverables (counts of open markers)"]
    for s in registry["sources"]:
        n = sum(c for p, c in markers.items() if s["path"] in p)
        if n:
            lines.append(f"- {s['theme']}: {n} open item(s) - ask the {s['ask']}")
    lines += ["", "### Other facts needed"] + [f"- {s['theme']} - ask the {s['ask']} (blocks: {s['blocks']})" for s in registry["static"]]
    lines += ["", f"Totals: {sum(1 for a in assumptions if a['status'] in ('OPEN', 'APPLIED'))} assumptions to confirm, "
              f"{sum(markers.values())} open items in {len(markers)} files, {len(registry['static'])} other facts."]
    return "\n".join(lines)


def qa_section() -> str:
    status = next((l for l in SIGNOFF.read_text(encoding="utf-8").splitlines() if l.startswith("**Status**")), "")
    w = json.loads(WAIVERS.read_text(encoding="utf-8"))
    rows = ["| Waived check | Owner | Expires |", "|---|---|---|"] + [f"| {x['check']} | {x['owner']} | {x['expires']} |" for x in w]
    return status + "\n\nWaivers in effect (a warning someone has accepted for now; a failure is never waived):\n" + "\n".join(rows)


def header(meta: dict, reqs: list[dict], plan_phases: list[dict], next_actions: list[dict]) -> str:
    st = {}
    for r in reqs:
        st[r["status"]] = st.get(r["status"], 0) + 1
    req_line = ", ".join(f"{st[k]} {k}" for k in ("met", "partial", "blocked", "deferred") if k in st)
    sides = meta["state"]["sides"]
    must = [
        "Do not present availability as OEE. Do not report an OEE number or a partial OEE: it is blocked until run and idle history, output, "
        "good-unit and cycle-time data exist (A10, A11)." if any("OEE" in p["deliverable"] and p["status"] == "blocked" for p in plan_phases) else
        "OEE is no longer blocked in the plan; check the plan before reporting it.",
        "Do not quote money, margin, payback or units-per-hour figures: the cost estimate is deferred until real business parameters exist "
        "(`05-stakeholder-communication/impact-quantification/status.json`). Do not run `cost_impact.py` with real-looking numbers." if deferral.is_deferred() else
        "The cost estimate is not deferred; every business figure must carry a source, owner and date.",
        "Do not state a physical cause for the aligned 2x2 blocks of closed positions: it is a hypothesis (A13).",
        "Do not use an APPLIED or OPEN rule as if it were confirmed; say which it is.",
        "Do not commit, paste or upload the raw logs or screenshots (`dat/`, `doc/`): they are private and git-ignored.",
        "Do not re-parse the CSV files in new code: all cleaning goes through `lib/contactor_io.py`.",
    ]
    lines = [
        "# Context package - handler contactor utilization",
        f"Generated {meta['date']} from commit `{meta['commit']}`" + (" (the working tree has uncommitted changes)" if meta["dirty"] else "") +
        f". Data through {sides['front']['last_reading']} (front) and {sides['rear']['last_reading']} (rear). Period: {cio.DEFAULT_START} to the last reading; "
        "the 2026-07-30 trial run is excluded (A6). Front = positions 1-256, rear = 257-512, each a grid of 16 columns by 16 rows.",
        "",
        "Read in this order: this header (status, what not to do, next steps, how to reproduce), then 1 data rules, 2 assumptions (check which are not "
        "confirmed), 3 metric definitions, 4 current state, 5 open decisions, 6 QA state.",
        "",
        "## Status",
        f"Requirements ({len(reqs)}): {req_line}. Phases: " + ", ".join(f"{p['phase']} {p['status']}" for p in plan_phases) + ".",
        "",
        "## Must not",
    ] + [f"- {m}" for m in must] + ["", "## Next steps (from the plan, in order)"] + \
        [f"{a['order']}. {a['action']} ({a['role']})" for a in next_actions] + \
        ["", "## Reproduce",
         "Data: the `dat/` folder next to the utilization folder (files `contactor_YYYYMMDD.csv` and `contactor_rear_YYYYMMDD.csv`); it is not in the repository."] + \
        [f"- `python {c}` - {why}" for c, why in COMMANDS]
    return "\n".join(lines)


def history_section() -> str:
    _, old = trim_changelog(METRIC.read_text(encoding="utf-8"))
    log = pc.table(pc.section(LEARNINGS.read_text(encoding="utf-8"), "Learnings"))
    acts = pc.table(pc.section(RETRO.read_text(encoding="utf-8"), "Actions"))
    return ("# HISTORY (not rules: superseded statements are kept here on purpose)\n## Older metric definition versions\n" + "\n".join(old) +
            "\n\n## Learnings (class: rule going forward)\n" + "\n".join(f"- {l['id']} ({l['class']}): {l['rule going forward']}" for l in log) +
            "\n\n## Retrospective actions\n" + "\n".join(f"- {a['id']}: {a['action']} ({a['role']}, {a['status']})" for a in acts))


def build_package(budget_tokens: int = 8000, with_history: bool = False, data_dir=None, today: str | None = None) -> dict:
    items = at.load()
    reqs = pc.table(pc.REQS.read_text(encoding="utf-8"))
    plan = pc.PLAN.read_text(encoding="utf-8")
    rs = {r["id"]: r["status"] for r in reqs}
    phases = []
    for p in pc.table(pc.section(plan, "Phases")):
        phases.append({"phase": p["phase"], "deliverable": p["deliverable"],
                       "status": pc.derived_status([rs[x.strip()] for x in p["requirements"].split(",") if x.strip() in rs])})
    state = fresh_state(data_dir)
    pipe = pipeline_info(state)
    commit, dirty = git_state()
    meta = {"date": today or dt.date.today().isoformat(), "commit": commit or "unknown", "dirty": bool(dirty), "state": state, "pipeline": pipe,
            "with_history": with_history, "budget_tokens": budget_tokens, "problems": list(pipe["problems"])}
    yaml_text, _ = trim_changelog(METRIC.read_text(encoding="utf-8"))
    rows = ["| side | site availability | lower bound | 95% range (day bootstrap) | closed now | last reading |", "|---|---|---|---|---|---|"]
    for side, v in state["sides"].items():
        rows.append(f"| {side} | {v['availability']:.2f}% | {v['lower_bound']:.2f}% | {v['ci_low']:.2f}-{v['ci_high']:.2f}% | {v['closed_now']} of 256 | {v['last_reading']} |")
    layers = {
        "header": header(meta, reqs, phases, pc.table(pc.section(plan, "Next actions"))),
        "rules": "\n\n".join(["## 1. Data rules (loader)\n" + (ROOT / "lib" / "contactor_io.py").read_text(encoding="utf-8").split('"""')[1].strip(),
                              assumptions_section(items), "## 3. Metric definitions (latest version)\n```yaml\n" + yaml_text + "\n```"]),
        "state": "\n\n".join(["## 4. Current state (recomputed from the data on " + meta["date"] + ", not copied from an old run)\n" + "\n".join(rows) +
                              f"\nClosed now = positions closed in at least 50% of the last {RECENT_DAYS} days (A19, applied). Site availability is time-weighted; it is not OEE."
                              f"\nPipeline: run {pipe['run']}" + (f" - PROBLEM: {'; '.join(pipe['problems'])}" if pipe["problems"] else " - steps ok, matches the recomputation") + ".",
                              "## 5. Open decisions\n" + open_decisions(items), "## 6. QA state\n" + qa_section()]),
    }
    if with_history:
        layers["history"] = history_section()
    text = "\n\n".join(layers.values())
    meta["layer_tokens"] = {k: estimate_tokens(v) for k, v in layers.items()}
    meta["tokens"] = sum(t for k, t in meta["layer_tokens"].items() if k != "history")
    if meta["tokens"] > budget_tokens:
        meta["problems"].append(f"over budget: {meta['tokens']} tokens (rules and state) against {budget_tokens}")
    return {"text": text, "layers": layers, "meta": meta}


def main():
    ap = argparse.ArgumentParser(description="Context bundler")
    ap.add_argument("--budget-tokens", type=int, default=8000)
    ap.add_argument("--output", default=str(ROOT / "out" / "context_package.md"))
    ap.add_argument("--with-history", action="store_true", help="add the history layer (superseded wording included)")
    ap.add_argument("--allow-stale", action="store_true", help="write the package even if the pipeline summary is stale")
    ap.add_argument("--data-dir", default=None)
    args = ap.parse_args()
    pkg = build_package(args.budget_tokens, args.with_history, args.data_dir)
    m = pkg["meta"]
    print("layers (estimated tokens, chars/3): " + ", ".join(f"{k} {v}" for k, v in m["layer_tokens"].items()))
    blocking = [p for p in m["problems"] if not (args.allow_stale and "pipeline" in p)]
    for p in m["problems"]:
        print(("PROBLEM: " if p in blocking else "ALLOWED: ") + p)
    if blocking:
        print("not written")
        sys.exit(1)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(pkg["text"], encoding="utf-8")
    print(f"wrote {out}  rules+state ~{m['tokens']} tokens of {args.budget_tokens}  commit {m['commit']}")


if __name__ == "__main__":
    main()
