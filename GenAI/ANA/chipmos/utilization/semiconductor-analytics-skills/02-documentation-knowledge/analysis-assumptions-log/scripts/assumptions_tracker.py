"""
Assumptions log backed by a TRACKED JSON file (assumptions.json next to SKILL.md).

Statuses: CONFIRMED (owner confirmed), APPLIED (used in the code, not explicitly
confirmed), OPEN (undecided / not applied), DISPUTED.

Usage:
    python assumptions_tracker.py list
    python assumptions_tracker.py add --id A19 --category data --statement "..." --impact high --status OPEN
    python assumptions_tracker.py resolve --id A9 --source "process owner (chat)" --note "..."
    python assumptions_tracker.py cite A8 A15 A18     # footnote text for reports
    python assumptions_tracker.py check               # log vs loader consistency; exit 1 on problems
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve()
LOG = HERE.parents[1] / "assumptions.json"
sys.path.insert(0, str(HERE.parents[3] / "lib"))

STATUSES = ("CONFIRMED", "APPLIED", "OPEN", "DISPUTED")


def load() -> list[dict]:
    items = json.loads(LOG.read_text(encoding="utf-8"))
    return sorted(items, key=lambda a: int(a["id"][1:]))


def save(items: list[dict]) -> None:
    items = sorted(items, key=lambda a: int(a["id"][1:]))
    LOG.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def render(items: list[dict]) -> str:
    rows = ["| ID | Category | Statement | Status | Impact | Source | Date | Note |", "|---|---|---|---|---|---|---|---|"]
    for a in items:
        rows.append(f"| {a['id']} | {a['category']} | {a['statement']} | {a['status']} | {a['impact']} | "
                    f"{a.get('source', '')} | {a.get('date', '')} | {a.get('note', '')} |")
    return "\n".join(rows)


def cite(items: list[dict], ids: list[str]) -> str:
    by = {a["id"]: a for a in items}
    lines = []
    for i in ids:
        a = by[i]
        lines.append(f"{i} [{a['status']}]: {a['statement']}")
    return "Assumptions applied:\n" + "\n".join(f"- {l}" for l in lines)


# loader constant -> (assumption id, value that must appear in that entry's text)
def _rule_links():
    import contactor_io as cio
    return {
        "NEAR_FULL_MIN": ("A8", cio.NEAR_FULL_MIN),
        "MAX_COUNT_GAP": ("A15", cio.MAX_COUNT_GAP),
        "DEFAULT_MAX_GAP_MIN": ("A18", int(cio.DEFAULT_MAX_GAP_MIN)),
    }


def check(items: list[dict]) -> list[str]:
    problems = []
    by = {a["id"]: a for a in items}
    ids = [a["id"] for a in items]
    if len(ids) != len(set(ids)):
        problems.append("duplicate ids")
    for a in items:
        if a["status"] not in STATUSES:
            problems.append(f"{a['id']}: unknown status {a['status']}")
        if a["status"] == "CONFIRMED" and not (a.get("source") and a.get("date")):
            problems.append(f"{a['id']}: CONFIRMED without source/date")
    for const, (aid, value) in _rule_links().items():
        text = f"{by.get(aid, {}).get('statement', '')} {by.get(aid, {}).get('note', '')}"
        if aid not in by:
            problems.append(f"{const}: no assumption {aid}")
        elif str(value) not in text:
            problems.append(f"{aid}: loader {const}={value} not mentioned in the entry (drift?)")
    return problems


def main():
    ap = argparse.ArgumentParser(description="Assumptions log")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list")
    sub.add_parser("check")
    ct = sub.add_parser("cite")
    ct.add_argument("ids", nargs="+")
    add = sub.add_parser("add")
    for a in ("id", "category", "statement"):
        add.add_argument(f"--{a}", required=True)
    add.add_argument("--impact", default="medium")
    add.add_argument("--status", default="OPEN", choices=STATUSES)
    add.add_argument("--source", default="")
    add.add_argument("--note", default="")
    res = sub.add_parser("resolve")
    res.add_argument("--id", required=True)
    res.add_argument("--source", required=True, help="who confirmed, e.g. 'process owner (chat)'")
    res.add_argument("--note", default="")
    args = ap.parse_args()

    items = load()
    if args.cmd == "add":
        if any(a["id"] == args.id for a in items):
            sys.exit(f"{args.id} already exists")
        items.append({"id": args.id, "category": args.category, "statement": args.statement, "status": args.status,
                      "impact": args.impact, "source": args.source, "date": str(date.today()) if args.source else "", "note": args.note})
        save(items)
    elif args.cmd == "resolve":
        for a in items:
            if a["id"] == args.id:
                a.update(status="CONFIRMED", source=args.source, date=str(date.today()))
                a["note"] = args.note or a.get("note", "")
        save(items)
    elif args.cmd == "cite":
        print(cite(items, args.ids))
        return
    elif args.cmd == "check":
        problems = check(items)
        print("OK - log consistent with the loader" if not problems else "\n".join(f"PROBLEM: {p}" for p in problems))
        sys.exit(1 if problems else 0)
    print(render(items))
    open_hi = [a["id"] for a in items if a["status"] in ("OPEN", "APPLIED") and a["impact"] == "high"]
    if open_hi:
        print(f"\nOPEN/unconfirmed high-impact assumptions: {', '.join(open_hi)}")


if __name__ == "__main__":
    main()
