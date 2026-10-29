"""
Derive the open questions from the project's own state, so the interview guide cannot go stale.

Sources
  * the assumptions log: every OPEN or APPLIED (applied but unconfirmed) assumption becomes a decision to confirm
  * `[OPEN` markers in the filled deliverables (templates, references and SKILL files are skipped), grouped by
    the file they sit in and routed through `assets/question_registry.json` to a role and a "what it blocks"
  * static questions in the registry that no marker or assumption carries (data feeds, records, business parameters)

An open item that the registry does not route is reported, not hidden.

Usage:
    python open_questions.py             # print the generated block
    python open_questions.py --write     # refresh the generated block in assets/interview_guide.md
    python open_questions.py --check     # exit 1 if the guide is out of date or an item is unrouted
"""

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
BASE = HERE.parents[1]
REGISTRY = BASE / "assets" / "question_registry.json"
GUIDE = BASE / "assets" / "interview_guide.md"
LOG = ROOT / "02-documentation-knowledge/analysis-assumptions-log/assumptions.json"
START, END = "<!-- generated:start -->", "<!-- generated:end -->"
SKIP_DIRS = {"out", ".git", "__pycache__", "references"}
MARKER = "[" + "OPEN"  # built so this file never counts itself


def scan_markers(root: Path = ROOT) -> dict[str, int]:
    """Relative path -> number of open markers, for filled deliverables only."""
    found = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix not in (".md", ".yaml", ".json"):
            continue
        rel = p.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts) or "template" in p.name or p.name in ("SKILL.md", "interview_guide.md", "question_registry.json"):
            continue
        n = p.read_text(encoding="utf-8", errors="ignore").count(MARKER)
        if n:
            found[str(rel)] = n
    return found


def coverage(markers: dict[str, int], assumptions: list[dict], registry: dict) -> dict[str, list[str]]:
    """Open items the registry does not route."""
    open_ids = [a["id"] for a in assumptions if a["status"] in ("OPEN", "APPLIED")]
    miss_a = [i for i in open_ids if i not in registry["assumptions"]]
    stale_a = [i for i in registry["assumptions"] if i not in open_ids]  # registered but no longer open
    miss_s = [p for p in markers if not any(s["path"] in p for s in registry["sources"])]
    return {"unrouted_assumptions": miss_a, "answered_but_registered": stale_a, "unrouted_files": miss_s}


def generate(markers: dict[str, int], assumptions: list[dict], registry: dict) -> str:
    lines = ["### Decisions to confirm (from the assumptions log: OPEN or applied-but-unconfirmed)",
             "| Id | Status | Question | Ask | What it blocks |", "|---|---|---|---|---|"]
    for a in sorted((x for x in assumptions if x["status"] in ("OPEN", "APPLIED")), key=lambda x: int(x["id"][1:])):
        r = registry["assumptions"].get(a["id"])
        if r:
            lines.append(f"| {a['id']} | {a['status']} | {r['question']} | {r['ask']} | {r['blocks']} |")
    lines += ["", "### Facts and owners to supply (from the open markers in the filled deliverables)",
              "| Theme | Ask | Open items | Where | Question | What it blocks |", "|---|---|---|---|---|---|"]
    rows = []
    for s in registry["sources"]:
        files = {p: n for p, n in markers.items() if s["path"] in p}
        if files:
            rows.append((s["theme"], s["ask"], sum(files.values()), ", ".join(sorted(Path(p).name for p in files)), s["question"], s["blocks"]))
    for theme, ask, n, where, q, b in sorted(rows):
        lines.append(f"| {theme} | {ask} | {n} | {where} | {q} | {b} |")
    lines += ["", "### Other facts needed (no marker carries them)", "| Theme | Ask | Question | What it blocks |", "|---|---|---|---|"]
    for s in registry["static"]:
        lines.append(f"| {s['theme']} | {s['ask']} | {s['question']} | {s['blocks']} |")
    total = sum(markers.values())
    lines += ["", f"Totals: {sum(1 for a in assumptions if a['status'] in ('OPEN', 'APPLIED'))} assumptions to confirm, "
              f"{total} open items in {len(markers)} files, {len(registry['static'])} other facts."]
    return "\n".join(lines)


def current() -> str:
    return generate(scan_markers(), json.loads(LOG.read_text(encoding="utf-8")), json.loads(REGISTRY.read_text(encoding="utf-8")))


def block_of(guide: str) -> str:
    m = re.search(re.escape(START) + r"\n(.*?)\n" + re.escape(END), guide, re.DOTALL)
    return m.group(1) if m else ""


def main():
    ap = argparse.ArgumentParser(description="Open questions generated from the project state")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    text = current()
    cov = coverage(scan_markers(), json.loads(LOG.read_text(encoding="utf-8")), json.loads(REGISTRY.read_text(encoding="utf-8")))
    if args.write:
        guide = GUIDE.read_text(encoding="utf-8")
        new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _m: f"{START}\n{text}\n{END}", guide, flags=re.DOTALL)
        GUIDE.write_text(new, encoding="utf-8")
        print(f"refreshed {GUIDE.name}")
    elif args.check:
        problems = [f"{k}: {v}" for k, v in cov.items() if v]
        if block_of(GUIDE.read_text(encoding="utf-8")) != text:
            problems.append("the generated block in interview_guide.md is out of date (run --write)")
        print("OK - guide in sync with the log and the open markers" if not problems else "\n".join(problems))
        sys.exit(1 if problems else 0)
    else:
        print(text)
        for k, v in cov.items():
            if v:
                print(f"\nNOT ROUTED - {k}: {v}")


if __name__ == "__main__":
    main()
