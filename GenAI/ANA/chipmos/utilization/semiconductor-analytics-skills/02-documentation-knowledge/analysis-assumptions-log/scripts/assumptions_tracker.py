"""
Small JSON-backed assumptions log.

Usage:
    python assumptions_tracker.py list
    python assumptions_tracker.py add --id A12 --category data --statement "..." --impact high --status OPEN
    python assumptions_tracker.py resolve --id A8 --note "confirmed by process owner"
"""

import argparse
import json
from pathlib import Path

LOG = Path(__file__).resolve().parents[3] / "out" / "assumptions.json"

SEED = [
    {"id": "A1", "category": "data", "statement": "err_01 is the number of closed sites; err_02 lists the closed site IDs", "status": "CONFIRMED", "impact": "high"},
    {"id": "A2", "category": "data", "statement": "Blue = active/open, grey = closed", "status": "CONFIRMED", "impact": "high"},
    {"id": "A3", "category": "data", "statement": "err_01 == 256 is a read failure; drop the sample", "status": "CONFIRMED", "impact": "high"},
    {"id": "A4", "category": "data", "statement": "err_02 == N/A with err_01 == 0 means zero closed sites; keep", "status": "CONFIRMED", "impact": "medium"},
    {"id": "A5", "category": "data", "statement": "Trust list length over err_01 when they disagree", "status": "CONFIRMED", "impact": "medium",
     "note": "Data shows err_01 is never below list length -> list is a lower bound on closures"},
    {"id": "A6", "category": "scope", "statement": "Only Sep/Oct 2026 data; 07/30 was a trial run", "status": "CONFIRMED", "impact": "low"},
    {"id": "A7", "category": "scope", "statement": "Front = sites 1-256, rear = 257-512", "status": "CONFIRMED", "impact": "high"},
    {"id": "A8", "category": "data", "statement": "err_01 of 252-255 is also a read failure (not caught by the == 256 rule)", "status": "CONFIRMED", "impact": "high",
     "note": "Confirmed by process owner; applied by default (NEAR_FULL_MIN=252). Front 90.0% -> 91.3%; removes the 09/09 spike"},
    {"id": "A9", "category": "data", "statement": "N/A with err_01 > 0 is a read failure; drop", "status": "OPEN", "impact": "low"},
    {"id": "A10", "category": "metric", "statement": "Utilization means time-based OEE; at this stage only Availability from site closure is computable", "status": "CONFIRMED", "impact": "high",
     "note": "OEE stays BLOCKED until run-state, output, good-unit and cycle-time data exist"},
    {"id": "A11", "category": "metric", "statement": "Planned time = 24x7 unless a production calendar is provided", "status": "OPEN", "impact": "high",
     "note": "Only matters once OEE is unblocked"},
    {"id": "A12", "category": "metric", "statement": "Report front and rear separately; combined 512-site view is the mean of both", "status": "OPEN", "impact": "medium"},
    {"id": "A14", "category": "data", "statement": "Rows with count 240-251 whose list is also near-full (count and list agree) may be read failures too", "status": "OPEN", "impact": "low",
     "note": "11 front / 17 rear rows kept; dropping them would move availability ~+0.2 (front) / +0.3 (rear) pts - ask the process owner"},
    {"id": "A15", "category": "data", "statement": "err_01 - list length > 50 means the list is unreadable; drop the sample", "status": "CONFIRMED", "impact": "low",
     "note": "Agreed with process owner; MAX_COUNT_GAP=50 in lib/contactor_io.py; affects ~12 rear / 9 front rows"},
    {"id": "A16", "category": "scope", "statement": "Front 2026-09-09 (CRITICAL by failure rate) is kept with a caveat, not excluded", "status": "CONFIRMED", "impact": "low",
     "note": "Decided by process owner; cleaned availability 90.38% is normal; excluding the day changes the front headline by +0.01 pt"},
    {"id": "A13", "category": "physics", "statement": "Adjacent closed sites in aligned 2x2 blocks share a physical cause (module/board)", "status": "OPEN", "impact": "medium",
     "note": "Kept as a hypothesis by decision of the process owner - do not present as fact"},
]


def load() -> list[dict]:
    if LOG.exists():
        return json.loads(LOG.read_text())
    return [dict(a) for a in SEED]


def save(items: list[dict]) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(items, indent=2, ensure_ascii=False))


def render(items: list[dict]) -> str:
    rows = ["| ID | Category | Statement | Status | Impact | Note |", "|---|---|---|---|---|---|"]
    for a in items:
        rows.append(f"| {a['id']} | {a['category']} | {a['statement']} | {a['status']} | {a['impact']} | {a.get('note', '')} |")
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser(description="Assumptions log")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list")
    add = sub.add_parser("add")
    for a in ("id", "category", "statement"):
        add.add_argument(f"--{a}", required=True)
    add.add_argument("--impact", default="medium")
    add.add_argument("--status", default="OPEN")
    add.add_argument("--note", default="")
    res = sub.add_parser("resolve")
    res.add_argument("--id", required=True)
    res.add_argument("--note", default="")
    args = ap.parse_args()

    items = load()
    if args.cmd == "add":
        items.append({"id": args.id, "category": args.category, "statement": args.statement,
                      "status": args.status, "impact": args.impact, "note": args.note})
        save(items)
    elif args.cmd == "resolve":
        for a in items:
            if a["id"] == args.id:
                a["status"] = "CONFIRMED"
                a["note"] = args.note or a.get("note", "")
        save(items)
    print(render(items))
    open_hi = [a["id"] for a in items if a["status"] == "OPEN" and a["impact"] == "high"]
    if open_hi:
        print(f"\nOPEN high-impact assumptions: {', '.join(open_hi)}")


if __name__ == "__main__":
    main()
