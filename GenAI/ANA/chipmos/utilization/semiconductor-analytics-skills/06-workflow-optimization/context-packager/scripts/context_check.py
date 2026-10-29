"""
Checks a built context package against the repository and the data.

  * orientation: the header has every section the template names, and its status line equals the requirements
    and the plan's derived phase statuses
  * rules: every assumption is present with its status, unconfirmed ones are listed and have their blank source
    marked, confirmed ones have a source
  * must-not rules agree with the status files (deferral, blocked OEE, the 2x2 hypothesis) and no business figures leak
  * the headline in the package equals a recomputation from the data; the pipeline summary is fresh and agrees
  * the commit exists; the reproduce commands point at existing scripts
  * open decisions equal the assumptions log and the generated totals; QA state equals the sign-off and the waivers
  * superseded wording (the old weighting statements) only in the history layer, which exists only when asked for
  * rules and state fit the budget (chars/3); no secrets, emails, home paths or raw data rows

Usage:
    python context_check.py                    # build in memory and check
    python context_check.py --with-history
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
import context_bundler as cb  # noqa: E402

ROOT = cb.ROOT
SUPERSEDED = ("across dropped readings and gaps", "not imputed")
SECRETS = (r"(?i)\b(api[_-]?key|secret|passwd|password|bearer)\b\s*[:=]", r"AKIA[0-9A-Z]{16}", r"\bsk-[A-Za-z0-9]{20,}")
EMAIL = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}"
RAW_ROW = r"(?m)^\d{4}-\d\d-\d\d[ T]\d\d:\d\d:\d\d,\s*\d+,"


def commit_exists(h: str, root: Path = ROOT):
    try:
        r = subprocess.run(["git", "-C", str(root), "cat-file", "-e", f"{h}^{{commit}}"], capture_output=True, timeout=20)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return None


def sect(text: str, title: str) -> str:
    m = re.search(rf"^## {re.escape(title)}[^\n]*\n(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
    return m.group(1) if m else ""


def check(pkg: dict, template: str | None = None, fresh: dict | None = None, check_pipeline: bool = True, root: Path = ROOT) -> list[tuple[str, str, str]]:
    res = []
    add = lambda n, s, d="": res.append((n, s, d))
    meta, layers = pkg["meta"], pkg["layers"]
    core = "\n\n".join(v for k, v in layers.items() if k != "history")
    header = layers["header"]
    template = cb.TEMPLATE.read_text(encoding="utf-8") if template is None else template

    add("no unfilled placeholders", "FAIL" if "[" + "REQUIRED" in pkg["text"] else "PASS")

    # ---- orientation
    wanted = [h[3:].strip() for h in template.splitlines() if h.startswith("## ")]
    missing = [h for h in wanted if not re.search(rf"^## {re.escape(h)}", header, re.MULTILINE)]
    if "Read in this order" not in header:
        missing.append("Read in this order")
    add("the header has every section the template names", "PASS" if not missing else "FAIL", ", ".join(missing))

    reqs = cb.pc.table(cb.pc.REQS.read_text(encoding="utf-8"))
    rs = {r["id"]: r["status"] for r in reqs}
    want_counts = {k: sum(1 for v in rs.values() if v == k) for k in ("met", "partial", "blocked", "deferred")}
    req_sentence = re.search(r"Requirements \(\d+\): ([^.]*)\.", sect(header, "Status"))
    got_counts = {k: int(n) for n, k in re.findall(r"(\d+) (met|partial|blocked|deferred)", req_sentence.group(1) if req_sentence else "")}
    want_phases = {p["phase"]: cb.pc.derived_status([rs[x.strip()] for x in p["requirements"].split(",") if x.strip() in rs])
                   for p in cb.pc.table(cb.pc.section(cb.pc.PLAN.read_text(encoding="utf-8"), "Phases"))}
    got_phases = dict(re.findall(r"\b(P\d) (met|partial|blocked|deferred)\b", sect(header, "Status")))
    bad = []
    if {k: v for k, v in want_counts.items() if v} != got_counts:
        bad.append(f"requirement counts {got_counts} vs {want_counts}")
    if want_phases != got_phases:
        bad.append("phase statuses differ from the plan")
    add("the status line equals the requirements and the plan", "PASS" if not bad else "FAIL", "; ".join(bad))

    # ---- rules
    items = cb.at.load()
    rows = {m.group(1): [c.strip() for c in m.group(0).strip().strip("|").split("|")] for m in re.finditer(r"(?m)^\| (A\d+) \|.*$", layers["rules"])}
    unconf_block = layers["rules"].split("### Not confirmed by the process owner")[-1] if "### Not confirmed by the process owner" in layers["rules"] else ""
    prob = []
    for a in items:
        r = rows.get(a["id"])
        if r is None:
            prob.append(f"{a['id']} missing")
            continue
        if r[3] != a["status"]:
            prob.append(f"{a['id']} status {r[3]} vs {a['status']}")
        if a["status"] != "CONFIRMED" and f"- {a['id']} (" not in unconf_block:
            prob.append(f"{a['id']} not listed as unconfirmed")
        if a["status"] == "CONFIRMED" and (not a.get("source") or r[5].startswith("none")):
            prob.append(f"{a['id']} confirmed without a source")
        if not a.get("source") and not r[5].startswith("none"):
            prob.append(f"{a['id']} blank source not marked")
    add("every assumption is present with its status; unconfirmed ones are marked", "PASS" if not prob else "FAIL", "; ".join(prob[:5]))

    # ---- must-not
    mn = sect(header, "Must not")
    prob = []
    deferred = cb.deferral.is_deferred()
    if deferred != ("cost estimate is deferred" in mn):
        prob.append("deferral statement disagrees with status.json")
    oee_blocked = any("OEE" in p["deliverable"] and want_phases.get(p["phase"]) == "blocked"
                      for p in cb.pc.table(cb.pc.section(cb.pc.PLAN.read_text(encoding="utf-8"), "Phases")))
    if oee_blocked and "partial OEE" not in mn:
        prob.append("OEE is blocked but the package does not say so")
    if "hypothesis (A13)" not in mn:
        prob.append("no A13 hypothesis statement")
    money = cb.deferral.check(core) if deferred else []
    if money:
        prob.append("business figures: " + ", ".join(money[:3]))
    add("must-not rules agree with the status files and no business figures leak", "PASS" if not prob else "FAIL", "; ".join(prob))

    # ---- headline and freshness
    fresh = fresh or cb.fresh_state()
    prob = []
    for side, v in fresh["sides"].items():
        m = re.search(rf"(?m)^\| {side} \| ([\d.]+)% \| ([\d.]+)% \| ([\d.]+)-([\d.]+)% \| (\d+) of 256 \|", layers["state"])
        if not m:
            prob.append(f"{side} row missing")
            continue
        got = [float(x) for x in m.groups()]
        exp = [v["availability"], v["lower_bound"], v["ci_low"], v["ci_high"], v["closed_now"]]
        if any(abs(g - e) > 0.006 for g, e in zip(got, exp)):
            prob.append(f"{side}: package {got} vs recomputed {exp}")
    add("the headline in the package equals a recomputation from the data", "PASS" if not prob else "FAIL", "; ".join(prob))
    pp = meta["pipeline"]["problems"]
    if not check_pipeline:
        add("the pipeline summary is fresh and agrees", "PASS", "skipped: the pipeline calls the QA gate before it writes its summary")
    else:
        add("the pipeline summary is fresh and agrees", "PASS" if not pp else "FAIL", "; ".join(pp))

    # ---- commit and commands
    c = meta["commit"]
    ok = re.fullmatch(r"[0-9a-f]{7,40}", c or "") and f"`{c}`" in header and commit_exists(c, root) is not False
    add("the commit is recorded and exists", "PASS" if ok else "FAIL", "" if ok else f"commit '{c}'")
    cmds = re.findall(r"`python ([^`]+)`", sect(header, "Reproduce"))
    miss = [x.split()[0] for x in cmds if not (root / x.split()[0]).is_file()]
    add("the reproduce commands point at existing scripts", "PASS" if cmds and not miss else "FAIL", ", ".join(miss) or ("" if cmds else "no commands"))

    # ---- open decisions and QA
    block = layers["state"].split("### Decisions to confirm")[1].split("###")[0] if "### Decisions to confirm" in layers["state"] else ""
    dec = set(re.findall(r"(?m)^\| (A\d+) \|", block))
    want = {a["id"] for a in items if a["status"] in ("OPEN", "APPLIED")}
    prob = []
    if dec != want:
        prob.append(f"decisions {sorted(dec ^ want)} differ from the log")
    markers = cb.oq.scan_markers()
    reg = json.loads(cb.oq.REGISTRY.read_text(encoding="utf-8"))
    tot = f"Totals: {len(want)} assumptions to confirm, {sum(markers.values())} open items in {len(markers)} files, {len(reg['static'])} other facts."
    if tot not in layers["state"]:
        prob.append("totals line differs from the markers and the registry")
    add("open decisions equal the assumptions log and the markers", "PASS" if not prob else "FAIL", "; ".join(prob))

    status_line = next((l for l in cb.SIGNOFF.read_text(encoding="utf-8").splitlines() if l.startswith("**Status**")), "")
    waivers = json.loads(cb.WAIVERS.read_text(encoding="utf-8"))
    miss = [w["check"] for w in waivers if f"| {w['check']} |" not in layers["state"]]
    add("the QA state equals the sign-off and the waivers", "PASS" if status_line and status_line in layers["state"] and not miss else "FAIL",
        ", ".join(miss) or ("" if status_line in layers["state"] else "sign-off status line missing"))

    # ---- superseded wording and layers
    leaks = [p for p in SUPERSEDED if p in core]
    add("superseded wording appears only in the history layer", "PASS" if not leaks else "FAIL", ", ".join(leaks))
    order = [layers.get(k) for k in ("header", "rules", "state", "history") if k in layers]
    in_order = [pkg["text"].find(o) for o in order] == sorted(pkg["text"].find(o) for o in order)
    hist_ok = ("history" in layers) == bool(meta["with_history"]) and ("history" not in layers or layers["history"].startswith("# HISTORY"))
    add("layers are ordered and history exists only when requested", "PASS" if in_order and hist_ok else "FAIL")

    # ---- budget and safety
    tokens = cb.estimate_tokens(core)
    add("rules and state fit the budget (chars/3)", "PASS" if tokens <= meta["budget_tokens"] else "FAIL", f"{tokens} of {meta['budget_tokens']} tokens")
    prob = [f"secret-like text ({p})" for p in SECRETS if re.search(p, pkg["text"])]
    if re.search(EMAIL, pkg["text"]):
        prob.append("an email address")
    if "/home/" in pkg["text"] or str(cb.cio.DEFAULT_DATA_DIR) in pkg["text"]:
        prob.append("an absolute private path")
    if re.search(RAW_ROW, pkg["text"]):
        prob.append("a raw data row")
    add("no secrets, emails, private paths or raw data rows", "PASS" if not prob else "FAIL", "; ".join(prob))
    return res


def main():
    ap = argparse.ArgumentParser(description="Context package checker")
    ap.add_argument("--with-history", action="store_true")
    ap.add_argument("--budget-tokens", type=int, default=8000)
    args = ap.parse_args()
    pkg = cb.build_package(args.budget_tokens, args.with_history)
    res = check(pkg)
    for n, s, d in res:
        print(f"[{s:4s}] {n:76s} {d}")
    fails = sum(1 for _, s, _ in res if s == "FAIL")
    print(f"\n{len(res)} checks: {fails} FAIL")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
