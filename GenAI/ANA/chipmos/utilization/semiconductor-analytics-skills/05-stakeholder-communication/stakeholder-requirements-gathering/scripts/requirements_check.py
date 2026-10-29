"""
Checks the requirements work: brief, requirements, stakeholder map and the generated interview guide.

  * brief complete: every field and section present, no placeholders, scope names the period and the trial-run
    exclusion, the assumption counts match the log; a DRAFT brief is a warning, a CONFIRMED one needs a name and date
  * stakeholder map: roles with decision rights; every role named in requirements, the registry and the brief
    exists; unnamed people are counted (warning); "process owner" is defined
  * requirements: unique ids, priority and status values, a known source role, a deliverable that exists, an
    acceptance check = an existing script plus a quoted check/test name that appears in that script; anything not
    "met" says what it is blocked by (deferred cites status.json, blocked cites an assumption id or missing data)
  * success criteria point at real requirements and every "must" requirement has one
  * interview guide in sync: the generated block equals what the log and the open markers produce; every open
    assumption and every file with open markers is routed to a role in the registry
  * no stale terms, no money figures while impact-quantification is deferred

Usage:
    python requirements_check.py
"""

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
BASE = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "lib"))
import deferral  # noqa: E402
import open_questions as oq  # noqa: E402

BRIEF = BASE / "assets" / "analysis_brief_sep_oct_2026.md"
REQS = BASE / "assets" / "requirements_sep_oct_2026.md"
MAP = BASE / "assets" / "stakeholder_map_sep_oct_2026.md"
GUIDE = oq.GUIDE
SKILL = BASE / "SKILL.md"
PRIORITY = {"must", "should", "could"}
STATUS = {"met", "partial", "blocked", "deferred"}
STALE = ("chronic-site list", "alert on new cluster", "recoverable points", "chronic cluster")
BRIEF_FIELDS = ("Business question", "Decision / owner", "Scope", "Definitions agreed", "Status")
BRIEF_SECTIONS = ("Data feeds", "Deliverables and dates", "Success criteria", "Risks")


def table(text: str) -> list[dict]:
    rows = [l.strip() for l in text.splitlines() if l.strip().startswith("|")]
    rows = [r for r in rows if not re.match(r"^\|[\s:|-]+\|$", r)]
    if len(rows) < 2:
        return []
    cell = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
    head = [h.lower() for h in cell(rows[0])]
    return [dict(zip(head, cell(r))) for r in rows[1:]]


def section(text: str, title: str) -> str:
    m = re.search(rf"^## {re.escape(title)}[^\n]*\n(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
    return m.group(1) if m else ""


def check(brief: str, reqs: str, stakeholders: str, guide: str, skill: str, registry: dict, assumptions: list[dict],
          markers: dict[str, int], expected_block: str, root: Path = ROOT) -> list[tuple[str, str, str]]:
    res = []
    add = lambda name, status, detail="": res.append((name, status, detail))
    mark = "[" + "OPEN"
    everything = brief + reqs + stakeholders

    add("no unfilled placeholders", "FAIL" if "[" + "REQUIRED" in everything else "PASS")
    money = deferral.check(everything)
    add("no money or throughput figures while impact-quantification is deferred", "PASS" if not money else "FAIL", ", ".join(money[:3]))
    stale = [t for t in STALE if t in (everything + skill + oq.block_of(guide) + guide.split(oq.END)[-1]).lower()]
    add("no stale terms", "PASS" if not stale else "FAIL", ", ".join(stale))

    # ---- brief
    missing = [f for f in BRIEF_FIELDS if f"**{f}**" not in brief] + [s for s in BRIEF_SECTIONS if not section(brief, s)]
    add("brief has every field and section", "PASS" if not missing else "FAIL", ", ".join(missing))
    scope = re.search(r"\*\*Scope\*\*:(.*)", brief)
    ok = bool(scope) and all(x in scope.group(1) for x in ("2026-09-01", "2026-10-02", "07/30")) and "front" in scope.group(1) and "rear" in scope.group(1)
    add("scope names sides, period and the trial-run exclusion", "PASS" if ok else "FAIL")
    by = {}
    for a in assumptions:
        by[a["status"]] = by.get(a["status"], 0) + 1
    m = re.search(r"(\d+) confirmed, (\d+) applied.*?(\d+) open", brief)
    drift = not m or (int(m.group(1)), int(m.group(2)), int(m.group(3))) != (by.get("CONFIRMED", 0), by.get("APPLIED", 0), by.get("OPEN", 0))
    add("assumption counts in the brief match the log", "FAIL" if drift else "PASS",
        f"log has {by.get('CONFIRMED', 0)} confirmed, {by.get('APPLIED', 0)} applied, {by.get('OPEN', 0)} open" if drift else "")
    st = re.search(r"\*\*Status\*\*:\s*(\w+)", brief)
    if not st:
        add("brief confirmation", "FAIL", "no status")
    elif st.group(1).upper() == "CONFIRMED":
        cb = re.search(r"\*\*Confirmed by\*\*:\s*([^.]*)", brief)
        add("brief confirmation", "FAIL" if not cb or mark in cb.group(1) else "PASS", "a CONFIRMED brief needs a name and date")
    else:
        add("brief confirmation", "WARN", "brief is a DRAFT - not confirmed by a decision-maker")

    # ---- stakeholder map
    roles = table(section(stakeholders, "Roles and decision rights"))
    names = {r["role"]: r for r in roles}
    add("stakeholder map has roles with decision rights", "PASS" if roles and all(r.get("decision rights") for r in roles) else "FAIL")
    defined = "process owner" in names and bool(re.search(r'"process owner"[^\n]*\bmeans\b', stakeholders, re.IGNORECASE))
    add("process owner is a defined role, not just a label", "PASS" if defined else "FAIL", "" if defined else 'the map must say what "process owner" means and list the role')
    unnamed = [r["role"] for r in roles if mark in r.get("name", "")]
    add("roles have named people", "WARN" if unnamed else "PASS", f"{len(unnamed)} role(s) unnamed: {', '.join(unnamed)}" if unnamed else "")
    raci = table(section(stakeholders, "Who is accountable for what"))
    bad_raci = [r["deliverable"] for r in raci if r.get("accountable") not in names]
    add("every accountable role exists", "PASS" if raci and not bad_raci else "FAIL", ", ".join(bad_raci))

    # ---- requirements
    rq = table(reqs)
    ids = [r["id"] for r in rq]
    problems = []
    if len(ids) != len(set(ids)) or not ids:
        problems.append("duplicate or no ids")
    for r in rq:
        i = r["id"]
        if r["priority"] not in PRIORITY:
            problems.append(f"{i}: priority {r['priority']}")
        if r["status"] not in STATUS:
            problems.append(f"{i}: status {r['status']}")
        if r["source role"] not in names:
            problems.append(f"{i}: unknown source role {r['source role']}")
        d = re.findall(r"`([^`]+)`", r["deliverable"])
        if not d or not all((root / x).exists() for x in d):
            problems.append(f"{i}: deliverable path missing")
        acc = r["acceptance check"]
        path = re.findall(r"`([^`]+\.py)`", acc)
        quoted = re.findall(r'"([^"]+)"', acc)
        if not path or not (root / path[0]).exists():
            problems.append(f"{i}: acceptance script missing")
        elif not quoted or not all(q in (root / path[0]).read_text(encoding="utf-8") for q in quoted):
            problems.append(f"{i}: quoted check/test name not found in {Path(path[0]).name}")
        blocked = r["blocked by"]
        if r["status"] == "met" and blocked != "-":
            problems.append(f"{i}: met but blocked by {blocked}")
        if r["status"] != "met" and blocked in ("-", ""):
            problems.append(f"{i}: {r['status']} without saying what blocks it")
        if r["status"] == "deferred" and "status.json" not in blocked:
            problems.append(f"{i}: deferred must cite status.json")
        if r["status"] == "blocked" and not (re.search(r"\bA\d+\b", blocked) or "missing" in blocked):
            problems.append(f"{i}: blocked must cite an assumption id or missing data")
        for aid in re.findall(r"\bA\d+\b", blocked):
            if aid not in {a["id"] for a in assumptions}:
                problems.append(f"{i}: {aid} not in the assumptions log")
    add("requirements are complete, owned, traceable and honest about status", "PASS" if not problems else "FAIL", "; ".join(problems[:5]) + (f" (+{len(problems) - 5} more)" if len(problems) > 5 else ""))

    sc = re.findall(r"- SC\d+ \(([^)]*)\)", brief)
    cited = {x.strip() for grp in sc for x in grp.split(",")}
    unknown = sorted(cited - set(ids))
    uncovered = sorted(r["id"] for r in rq if r["priority"] == "must" and r["id"] not in cited)
    add("success criteria point at requirements and cover every must", "PASS" if sc and not unknown and not uncovered else "FAIL",
        "; ".join(filter(None, [f"unknown {unknown}" if unknown else "", f"no success criterion for {uncovered}" if uncovered else ""])))

    # ---- guide
    cov = oq.coverage(markers, assumptions, registry)
    cov_bad = [f"{k}: {v}" for k, v in cov.items() if v]
    add("every open item is routed to a role", "PASS" if not cov_bad else "FAIL", "; ".join(cov_bad))
    roles_used = {v["ask"] for v in registry["assumptions"].values()} | {s["ask"] for s in registry["sources"]} | {s["ask"] for s in registry["static"]}
    add("registry asks only roles that exist", "PASS" if roles_used <= set(names) else "FAIL", ", ".join(sorted(roles_used - set(names))))
    add("interview guide matches the log and the open markers", "PASS" if oq.block_of(guide) == expected_block else "FAIL", "" if oq.block_of(guide) == expected_block else "run scripts/open_questions.py --write")
    return res


def main():
    argparse.ArgumentParser(description="Requirements checker").parse_args()
    assumptions = json.loads(oq.LOG.read_text(encoding="utf-8"))
    registry = json.loads(oq.REGISTRY.read_text(encoding="utf-8"))
    markers = oq.scan_markers()
    res = check(BRIEF.read_text(encoding="utf-8"), REQS.read_text(encoding="utf-8"), MAP.read_text(encoding="utf-8"),
                GUIDE.read_text(encoding="utf-8"), SKILL.read_text(encoding="utf-8"), registry, assumptions, markers,
                oq.generate(markers, assumptions, registry))
    for name, status, detail in res:
        print(f"[{status:4s}] {name:68s} {detail}")
    fails = sum(1 for _, s, _ in res if s == "FAIL")
    print(f"\n{len(res)} checks: {fails} FAIL, {sum(1 for _, s, _ in res if s == 'WARN')} WARN")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
