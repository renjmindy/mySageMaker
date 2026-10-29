"""
Checks the analysis plan against the requirements, the stakeholder map and the open-question registry.

  * coverage: every requirement is in exactly one phase; no unknown requirement ids
  * status is DERIVED: a phase's status equals the worst status of its requirements (blocked, deferred,
    partial, met) - a hand-typed status that disagrees fails
  * every phase has an owner role from the stakeholder map, a target date or an explicit "no deadline set"
    (a warning), an entry criterion and an exit check = an existing script plus a quoted check/test name found in it
  * dependencies: provider is a real role, the `ask` is a theme or assumption id in the question registry, and
    every blocked / deferred phase has at least one dependency
  * estimates: sizes S/M/L (scale = uncertainty), a basis and what happened for every phase
  * risks: likelihood / impact / owner role valid; a materialised risk cites existing evidence, a mitigated one
    cites the existing artifact that enforces it
  * next actions: ordered, each routed to a real role and a real question, none unblocking nothing
  * stale terms (the old "owner is named" scope rule, role names that do not exist) and money figures are rejected

Usage:
    python plan_check.py             # check the plan
    python plan_check.py --status    # print the derived status of every phase
"""

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
BASE = HERE.parents[1]
REQ_DIR = ROOT / "05-stakeholder-communication/stakeholder-requirements-gathering"
sys.path.insert(0, str(ROOT / "lib"))
import deferral  # noqa: E402

PLAN = BASE / "assets" / "analysis_plan_sep_oct_2026.md"
SCOPE = BASE / "references" / "scoping_framework.md"
REQS = REQ_DIR / "assets" / "requirements_sep_oct_2026.md"
MAP = REQ_DIR / "assets" / "stakeholder_map_sep_oct_2026.md"
REGISTRY = REQ_DIR / "assets" / "question_registry.json"
RANK = {"met": 0, "partial": 1, "deferred": 2, "blocked": 3}
SIZES = {"S", "M", "L"}
LEVELS = {"low", "medium", "high"}
RISK_STATUS = {"open", "materialised", "mitigated"}
STALE = ("owner is named", "handler/mes owner", "equipment engineering")


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


def derived_status(statuses: list[str]) -> str:
    return max(statuses, key=lambda s: RANK[s]) if statuses else "met"


def resolvable(check: str, root: Path) -> str | None:
    """None if `script.py` "name" resolves: the script exists and contains every quoted name."""
    path = re.findall(r"`([^`]+\.py)`", check)
    quoted = re.findall(r'"([^"]+)"', check)
    if not path or not (root / path[0]).exists():
        return "script missing"
    if not quoted or not all(q in (root / path[0]).read_text(encoding="utf-8") for q in quoted):
        return f"quoted name not found in {Path(path[0]).name}"
    return None


def check(plan: str, scope: str, reqs: str, stakeholders: str, registry: dict, root: Path = ROOT) -> list[tuple[str, str, str]]:
    res = []
    add = lambda name, status, detail="": res.append((name, status, detail))
    mark = "[" + "OPEN"

    add("no unfilled placeholders", "FAIL" if "[" + "REQUIRED" in plan else "PASS")
    money = deferral.check(plan)
    add("no money or throughput figures while impact-quantification is deferred", "PASS" if not money else "FAIL", ", ".join(money[:3]))
    roles = {r["role"] for r in table(section(stakeholders, "Roles and decision rights"))} | {"analyst"}
    stale = [t for t in STALE if t in (plan + scope).lower()]
    add("no stale terms", "PASS" if not stale else "FAIL", ", ".join(stale))

    req_status = {r["id"]: r["status"] for r in table(reqs)}
    phases = table(section(plan, "Phases"))
    mapped: dict[str, list[str]] = {}
    for p in phases:
        for rid in [x.strip() for x in p["requirements"].split(",") if x.strip()]:
            mapped.setdefault(rid, []).append(p["phase"])
    unmapped = sorted(set(req_status) - set(mapped))
    dup = sorted(r for r, ph in mapped.items() if len(ph) > 1)
    unknown = sorted(set(mapped) - set(req_status))
    add("every requirement is in exactly one phase", "PASS" if not (unmapped or dup or unknown) else "FAIL",
        "; ".join(filter(None, [f"unmapped {unmapped}" if unmapped else "", f"in several phases {dup}" if dup else "", f"unknown {unknown}" if unknown else ""])))

    bad_status = []
    for p in phases:
        rids = [x.strip() for x in p["requirements"].split(",") if x.strip()]
        want = derived_status([req_status[r] for r in rids if r in req_status])
        if p["status"] != want:
            bad_status.append(f"{p['phase']}: plan says {p['status']}, requirements say {want}")
    add("phase status equals the status derived from its requirements", "PASS" if not bad_status else "FAIL", "; ".join(bad_status))

    problems, no_date = [], []
    for p in phases:
        i = p["phase"]
        if p["owner role"] not in roles:
            problems.append(f"{i}: owner role '{p['owner role']}' is not in the stakeholder map")
        if not p["entry criteria"]:
            problems.append(f"{i}: no entry criteria")
        err = resolvable(p["exit check"], root)
        if err:
            problems.append(f"{i}: exit check - {err}")
        if re.fullmatch(r"\d{4}-\d\d-\d\d", p["target date"]):
            continue
        if p["target date"].lower().startswith("no deadline"):
            no_date.append(i)
        else:
            problems.append(f"{i}: target date '{p['target date']}'")
    add("phases have an owner role, entry criteria and a resolvable exit check", "PASS" if not problems else "FAIL", "; ".join(problems[:5]))
    add("phases have a target date", "WARN" if no_date else "PASS", f"no deadline set for {len(no_date)} phase(s)" if no_date else "")

    asks = set(registry["assumptions"]) | {s["theme"] for s in registry["sources"]} | {s["theme"] for s in registry["static"]}
    deps = table(section(plan, "Dependencies"))
    dprob = []
    phase_ids = {p["phase"] for p in phases}
    for d in deps:
        if d["provider role"] not in roles:
            dprob.append(f"'{d['dependency'][:30]}...': provider role '{d['provider role']}' unknown")
        if d["ask"] not in asks:
            dprob.append(f"'{d['dependency'][:30]}...': ask '{d['ask']}' is not a question in the registry")
        for ph in re.findall(r"P\d+", d["needed by"]):
            if ph not in phase_ids:
                dprob.append(f"needed-by {ph} is not a phase")
    covered = {ph for d in deps for ph in re.findall(r"P\d+", d["needed by"])}
    for p in phases:
        if p["status"] in ("blocked", "deferred") and p["phase"] not in covered:
            dprob.append(f"{p['phase']} is {p['status']} with no dependency")
    add("dependencies have a real provider role and a registered question", "PASS" if deps and not dprob else "FAIL", "; ".join(dprob[:5]))

    est = table(section(plan, "Estimates and calibration"))
    eprob = [f"{e['phase']}: size/basis/outcome incomplete" for e in est
             if e["next-time size"] not in SIZES or not e["basis"] or not e["what happened"] or e["original estimate"].split()[0] not in SIZES | {"-"}]
    missing_est = sorted(phase_ids - {e["phase"] for e in est})
    add("every phase has a sized, justified and calibrated estimate", "PASS" if est and not eprob and not missing_est else "FAIL",
        "; ".join(eprob + ([f"no estimate for {missing_est}"] if missing_est else [])))

    risks = table(section(plan, "Risk register"))
    rprob = []
    for k in risks:
        if k["likelihood"] not in LEVELS or k["impact"] not in LEVELS:
            rprob.append(f"{k['id']}: likelihood/impact")
        if k["owner role"] not in roles:
            rprob.append(f"{k['id']}: owner '{k['owner role']}'")
        if k["status"] not in RISK_STATUS:
            rprob.append(f"{k['id']}: status {k['status']}")
        for f in ("trigger", "mitigation"):
            if not k[f]:
                rprob.append(f"{k['id']}: no {f}")
        ev = re.findall(r"`([^`]+)`", k["evidence"])
        if k["status"] in ("materialised", "mitigated") and (not ev or not all((root / e).exists() for e in ev)):
            rprob.append(f"{k['id']}: {k['status']} without existing evidence")
    add("risks are complete, owned and evidenced", "PASS" if risks and not rprob else "FAIL", "; ".join(rprob[:5]))
    add("the register includes risks that materialised", "PASS" if any(k["status"] == "materialised" for k in risks) else "FAIL")

    acts = table(section(plan, "Next actions"))
    aprob = []
    if [a["order"] for a in acts] != [str(i) for i in range(1, len(acts) + 1)]:
        aprob.append("order is not 1..n")
    for a in acts:
        if a["role"] not in roles:
            aprob.append(f"{a['order']}: role '{a['role']}'")
        if a["ask"] not in asks:
            aprob.append(f"{a['order']}: ask '{a['ask']}' not in the registry")
        if not a["unblocks"]:
            aprob.append(f"{a['order']}: unblocks nothing")
    add("next actions are ordered, routed and unblock something", "PASS" if acts and not aprob else "FAIL", "; ".join(aprob[:5]))
    return res


def main():
    ap = argparse.ArgumentParser(description="Analysis plan checker")
    ap.add_argument("--status", action="store_true", help="print the derived status of every phase")
    args = ap.parse_args()
    plan, reqs = PLAN.read_text(encoding="utf-8"), REQS.read_text(encoding="utf-8")
    if args.status:
        rs = {r["id"]: r["status"] for r in table(reqs)}
        for p in table(section(plan, "Phases")):
            print(p["phase"], derived_status([rs[x.strip()] for x in p["requirements"].split(",") if x.strip() in rs]))
        return
    res = check(plan, SCOPE.read_text(encoding="utf-8"), reqs, MAP.read_text(encoding="utf-8"), json.loads(REGISTRY.read_text(encoding="utf-8")))
    for name, status, detail in res:
        print(f"[{status:4s}] {name:70s} {detail}")
    fails = sum(1 for _, s, _ in res if s == "FAIL")
    print(f"\n{len(res)} checks: {fails} FAIL, {sum(1 for _, s, _ in res if s == 'WARN')} WARN")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
