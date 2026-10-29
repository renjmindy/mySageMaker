"""
Checks the learnings log and the retrospective against the repository, the plan and the stakeholder map.

  * every learning has all its fields, a class defined in the Classes table, a plan phase (or "all"), a valid
    found-by and status, and a concrete rule (no "be more careful", no blame words)
  * the source is a real commit or an existing file
  * status "encoded": every `path` "name" in the encoded-in cell is a code file that contains the quoted name;
    "documented": the file exists and an action addresses it; "open": an action addresses it
  * a repeat names an earlier learning of the same class
  * a class with two or more learnings has a systemic fix that resolves the same way
  * every correction recorded inside a deliverable ("Corrected 2026-..", "an earlier version ... wrong") is
    cited by a learning
  * learnings link to risks in the plan, and every materialised plan risk has at least one learning
  * the retrospective's claims cite learnings, its lessons-by-class table equals the log, its actions have a
    real role and a registered question, and its limits are stated

Usage:
    python learnings_check.py            # check
    python learnings_check.py --table    # print the lessons-by-class table computed from the log
"""

import argparse
import functools
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
BASE = HERE.parents[1]
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "06-workflow-optimization/analysis-planning/scripts"))
import deferral  # noqa: E402
import plan_check as pc  # noqa: E402

LOG = BASE / "assets" / "learnings_log_sep_oct_2026.md"
RETRO = BASE / "assets" / "retrospective_sep_oct_2026.md"
OWN_FILES = [BASE / "SKILL.md", BASE / "assets" / "retrospective_template.md", BASE / "assets" / "learnings_log_template.md",
             BASE / "references" / "retro_frameworks.md", BASE / "references" / "learning_capture.md"]
FOUND_BY = {"automated", "evaluation", "analyst", "user"}
STATUSES = {"encoded", "documented", "open"}
ACTION_STATUS = {"open", "done"}
STALE = ("qa check a8",)
VAGUE = ("be more careful", "be careful", "pay more attention", "pay attention", "try harder", "double-check everything",
         "remember to", "more diligent")
BLAME = ("careless", "sloppy", "negligen", "forgot", "lazy")
CORRECTION = re.compile(r"Corrected 20\d\d-\d\d-\d\d|\b[Ee]arlier (?:version|versions|wording|draft)\b|\b[Aa]n earlier (?:version|entry|wording)\b|\bthat was wrong\b|\bwas wrong\b")
SKIP_DIRS = {"out", ".git", "__pycache__", "reports", "analysis-retrospective"}
FIELDS = ["id", "class", "phase", "situation and what we did", "rule going forward", "found by", "status", "encoded in", "source", "risk", "repeat of"]


@functools.lru_cache(maxsize=None)
def git_has(ref: str):
    """True / False if the commit exists; None if git cannot answer (not installed, not a repository)."""
    try:
        if subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-dir"], capture_output=True, timeout=20).returncode != 0:
            return None
        return subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{ref}^{{commit}}"], capture_output=True, timeout=20).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return None


def scan_corrections(root: Path = ROOT) -> list[str]:
    """Relative paths of deliverable files that record a correction of an earlier version of themselves."""
    found = []
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.suffix not in (".md", ".json", ".yaml", ".yml"):
            continue
        rel = f.relative_to(root)
        if SKIP_DIRS & set(rel.parts):
            continue
        if CORRECTION.search(f.read_text(encoding="utf-8", errors="replace")):
            found.append(rel.as_posix())
    return found


def resolve(cell: str, root: Path, code_only: bool) -> list[str]:
    """Problems with a cell of the form: `path` "name"; `path` "name" ... (empty list = resolves)."""
    parts = [p.strip() for p in cell.split(";") if p.strip()]
    if not parts or cell.strip() in ("-", ""):
        return ["nothing cited"]
    out = []
    for part in parts:
        paths = re.findall(r"`([^`]+)`", part)
        names = re.findall(r'"([^"]+)"', part)
        if len(paths) != 1:
            out.append(f"expected one `path`: {part[:40]}")
            continue
        f = root / paths[0]
        if not f.is_file():
            out.append(f"{paths[0]} does not exist")
        elif code_only and (f.suffix != ".py" or not names):
            out.append(f"{paths[0]} is not code with a named check" if f.suffix != ".py" else f"{f.name}: no check or test named")
        elif any(n not in f.read_text(encoding="utf-8") for n in names):
            out.append(f"{f.name} does not contain {[n for n in names if n not in f.read_text(encoding='utf-8')][0]!r}")
    return out


def counts(learnings: list[dict]) -> dict[str, dict[str, int]]:
    c: dict[str, dict[str, int]] = {}
    for l in learnings:
        d = c.setdefault(l["class"], {"learnings": 0, "repeats": 0, "encoded": 0, "documented": 0, "open": 0})
        d["learnings"] += 1
        d["repeats"] += l["repeat of"] not in ("-", "")
        if l["status"] in d:
            d[l["status"]] += 1
    return c


def table_text(c: dict[str, dict[str, int]]) -> str:
    rows = ["| class | learnings | repeats | encoded | documented | open |", "|---|---|---|---|---|---|"]
    rows += [f"| {k} | {v['learnings']} | {v['repeats']} | {v['encoded']} | {v['documented']} | {v['open']} |" for k, v in sorted(c.items())]
    return "\n".join(rows)


def bullets(text: str) -> list[str]:
    return [l[2:].strip() for l in text.splitlines() if l.startswith("- ")]


def check(log: str, retro: str, plan: str, stakeholders: str, registry: dict, own_texts: list[str],
          correction_files: list[str], root: Path = ROOT, commit_exists=git_has) -> list[tuple[str, str, str]]:
    res = []
    add = lambda name, status, detail="": res.append((name, status, detail))
    both = log + "\n" + retro

    add("no unfilled placeholders", "FAIL" if "[" + "REQUIRED" in both else "PASS")
    money = deferral.check(both)
    add("no money or throughput figures while impact-quantification is deferred", "PASS" if not money else "FAIL", ", ".join(money[:3]))
    stale = [t for t in STALE if any(t in x.lower() for x in own_texts)]
    add("no stale terms in the skill and its templates", "PASS" if not stale else "FAIL", ", ".join(stale))

    roles = {r["role"] for r in pc.table(pc.section(stakeholders, "Roles and decision rights"))} | {"analyst"}
    asks = set(registry["assumptions"]) | {s["theme"] for s in registry["sources"]} | {s["theme"] for s in registry["static"]}
    phases = {p["phase"] for p in pc.table(pc.section(plan, "Phases"))} | {"all"}
    risks = {k["id"]: k for k in pc.table(pc.section(plan, "Risk register"))}
    learnings = pc.table(pc.section(log, "Learnings"))
    classes = {c["class"]: c for c in pc.table(pc.section(log, "Classes"))}
    ids = [l.get("id", "") for l in learnings]

    # ---- completeness and wording
    prob = []
    for l in learnings:
        i = l.get("id", "?")
        miss = [f for f in FIELDS if not l.get(f, "").strip()]
        if miss:
            prob.append(f"{i}: empty {miss[0]}")
            continue
        if l["class"] not in classes:
            prob.append(f"{i}: class '{l['class']}' is not defined")
        if l["phase"] not in phases:
            prob.append(f"{i}: phase '{l['phase']}' is not in the plan")
        if l["found by"] not in FOUND_BY:
            prob.append(f"{i}: found by '{l['found by']}'")
        if l["status"] not in STATUSES:
            prob.append(f"{i}: status '{l['status']}'")
        rule = l["rule going forward"].lower()
        bad = [t for t in VAGUE + BLAME if t in rule]
        if bad or len(rule.split()) < 6:
            prob.append(f"{i}: rule is vague or blames ({bad[0] if bad else 'too short'})")
    if len(set(ids)) != len(ids) or not learnings:
        prob.append("ids are missing or duplicated")
    add("every learning is complete, classified and concrete", "PASS" if not prob else "FAIL", "; ".join(prob[:5]))

    # ---- sources
    sprob = []
    for l in learnings:
        toks = re.findall(r"`([^`]+)`", l.get("source", ""))
        if not toks:
            sprob.append(f"{l.get('id')}: no source")
        for t in toks:
            if re.fullmatch(r"[0-9a-f]{7,40}", t):
                if commit_exists(t) is False:
                    sprob.append(f"{l['id']}: commit {t} not found")
            elif not (root / t).exists():
                sprob.append(f"{l['id']}: {t} does not exist")
    add("sources are real commits or existing files", "PASS" if not sprob else "FAIL", "; ".join(sprob[:5]))

    # ---- encodings
    eprob, dprob = [], []
    for l in learnings:
        if l.get("status") == "encoded":
            eprob += [f"{l['id']}: {p}" for p in resolve(l["encoded in"], root, True)]
        elif l.get("status") == "documented":
            dprob += [f"{l['id']}: {p}" for p in resolve(l["encoded in"], root, False)]
    add("encoded lessons point at code that contains the named check", "PASS" if not eprob else "FAIL", "; ".join(eprob[:5]))
    add("documented lessons point at an existing file", "PASS" if not dprob else "FAIL", "; ".join(dprob[:5]))

    # ---- repeats
    by_id = {l.get("id"): l for l in learnings}
    rprob, n_rep = [], 0
    for l in learnings:
        r = l.get("repeat of", "-")
        if r in ("-", ""):
            continue
        n_rep += 1
        ref = by_id.get(r)
        if ref is None or ids.index(r) >= ids.index(l["id"]) or ref["class"] != l["class"]:
            rprob.append(f"{l['id']}: repeat of '{r}' is not an earlier learning of the same class")
    add("a repeat names an earlier learning of the same class", "PASS" if not rprob else "FAIL", "; ".join(rprob) or f"{n_rep} repeat(s) logged")

    # ---- classes
    used: dict[str, int] = {}
    for l in learnings:
        used[l.get("class", "")] = used.get(l.get("class", ""), 0) + 1
    cprob = [f"class '{c}' is defined but no learning uses it" for c in classes if c not in used]
    for c, n in used.items():
        if c in classes and n >= 2:
            cprob += [f"{c}: {p}" for p in resolve(classes[c].get("systemic fix", ""), root, True)]
    add("every class is used, and recurring classes have a systemic fix that exists", "PASS" if classes and not cprob else "FAIL", "; ".join(cprob[:5]))

    # ---- corrections recorded in deliverables
    cited = " ".join(l.get("source", "") + " " + l.get("encoded in", "") for l in learnings)
    uncited = [f for f in correction_files if f not in cited]
    add("every correction recorded inside a deliverable is in the log", "PASS" if not uncited else "FAIL",
        ", ".join(uncited) or f"{len(correction_files)} files with a recorded correction, all cited")

    # ---- risks
    kprob = []
    linked = set()
    for l in learnings:
        for k in [x.strip() for x in l.get("risk", "-").split(",") if x.strip() not in ("-", "")]:
            if k not in risks:
                kprob.append(f"{l['id']}: risk {k} is not in the plan")
            linked.add(k)
    kprob += [f"{k} materialised with no learning" for k, v in risks.items() if v["status"] == "materialised" and k not in linked]
    add("learnings link to plan risks, and every materialised risk has a learning", "PASS" if not kprob else "FAIL", "; ".join(kprob[:5]))

    # ---- retrospective claims
    def sect_ok(title, need_id):
        items = bullets(pc.section(retro, title))
        problems = []
        if not items:
            problems.append(f"'{title}' has no bullets")
        for b in items:
            cites = re.findall(r"\bL\d+\b", b)
            unknown = [c for c in cites if c not in by_id]
            paths = re.findall(r"`([^`]+)`", b)
            if unknown:
                problems.append(f"{title}: unknown learning {unknown[0]}")
            elif need_id and not cites:
                problems.append(f"{title}: '{b[:40]}...' cites no learning")
            elif not need_id and not cites and not (paths and all((root / p).exists() for p in paths)):
                problems.append(f"{title}: '{b[:40]}...' cites no learning or file")
        return problems
    rp = sect_ok("What worked", False) + sect_ok("What did not", True) + sect_ok("Surprises", True)
    add("what worked, what did not and surprises each cite the log", "PASS" if not rp else "FAIL", "; ".join(rp[:5]))

    # ---- derived counts
    want = counts(learnings)
    got = {r["class"]: r for r in pc.table(pc.section(retro, "Lessons by class"))}
    cp = []
    for c, v in want.items():
        g = got.get(c)
        if not g or any(g.get(k) != str(n) for k, n in v.items()):
            cp.append(f"{c}: table says {None if not g else {k: g.get(k) for k in v}}, log says {v}")
    cp += [f"{c}: in the table but not in the log" for c in got if c not in want]
    add("lessons-by-class table equals the log", "PASS" if not cp else "FAIL", "; ".join(cp[:3]))

    # ---- actions
    actions = pc.table(pc.section(retro, "Actions"))
    aprob, addressed, no_date = [], set(), []
    if [a.get("id") for a in actions] != [f"A{i}" for i in range(1, len(actions) + 1)]:
        aprob.append("ids are not A1..An")
    for a in actions:
        i = a.get("id", "?")
        if a["role"] not in roles:
            aprob.append(f"{i}: role '{a['role']}'")
        if a["ask"] != "-" and a["ask"] not in asks:
            aprob.append(f"{i}: ask '{a['ask']}' is not in the registry")
        if a["status"] not in ACTION_STATUS:
            aprob.append(f"{i}: status '{a['status']}'")
        if not a["action"]:
            aprob.append(f"{i}: no action")
        for x in [c.strip() for c in a["addresses"].split(",") if c.strip() != "-"]:
            if x not in by_id:
                aprob.append(f"{i}: addresses unknown {x}")
            addressed.add(x)
        if not re.fullmatch(r"\d{4}-\d\d-\d\d", a["due"]):
            if a["due"].lower().startswith("no deadline"):
                no_date.append(i)
            else:
                aprob.append(f"{i}: due '{a['due']}'")
    for l in learnings:
        if l.get("status") in ("documented", "open") and l["id"] not in addressed:
            aprob.append(f"{l['id']} is {l['status']} and no action addresses it")
    add("actions are owned, routed and cover every documented or open learning", "PASS" if actions and not aprob else "FAIL", "; ".join(aprob[:5]))
    add("actions have a deadline", "WARN" if no_date else "PASS", f"no deadline set for {len(no_date)} action(s)" if no_date else "")

    limits = bullets(pc.section(retro, "Limits"))
    add("limits are stated", "PASS" if len(limits) >= 2 else "FAIL", "" if len(limits) >= 2 else "state who took part and what cannot be concluded")
    return res


def main():
    ap = argparse.ArgumentParser(description="Learnings log and retrospective checker")
    ap.add_argument("--table", action="store_true", help="print the lessons-by-class table computed from the log")
    args = ap.parse_args()
    log = LOG.read_text(encoding="utf-8")
    if args.table:
        print(table_text(counts(pc.table(pc.section(log, "Learnings")))))
        return
    retro = RETRO.read_text(encoding="utf-8")
    res = check(log, retro, pc.PLAN.read_text(encoding="utf-8"), pc.MAP.read_text(encoding="utf-8"),
                json.loads(pc.REGISTRY.read_text(encoding="utf-8")), [f.read_text(encoding="utf-8") for f in OWN_FILES],
                scan_corrections())
    for name, status, detail in res:
        print(f"[{status:4s}] {name:76s} {detail}")
    fails = sum(1 for _, s, _ in res if s == "FAIL")
    print(f"\n{len(res)} checks: {fails} FAIL, {sum(1 for _, s, _ in res if s == 'WARN')} WARN")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
