"""
Checks the peer-review kit and the review record of a release.

The kit
  * the rigor checklist covers every defect class in the learnings log and every hard rule, each enforced-by
    resolves to a file that contains the named check (or says what to record when it cannot be done), and each
    class has a test that the QA gate runs
The record
  * independence: a reviewer who is not the author and holds the reviewer role in the stakeholder map
    (NOT REVIEWED is a warning, not a pass)
  * the reviewed commit exists and is part of this history; the author's preparation is current; an independent
    recompute without the loader agrees with the loader-based headline
  * reproduction: the reviewer's table matches the author's claims, differences are arithmetic, anything outside
    the tolerance has a blocking finding
  * checklist outcomes are complete and consistent with the findings
  * findings are complete; each answered finding has a response, a change that exists, and a re-check when verified
  * the verdict follows from the findings; the QA sign-off agrees with the review

Usage:
    python review_check.py
"""

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
BASE = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))
for sub in ("06-workflow-optimization/analysis-planning/scripts", "06-workflow-optimization/analysis-retrospective/scripts",
            "06-workflow-optimization/context-packager/scripts"):
    sys.path.insert(0, str(ROOT / sub))
import context_bundler as cb  # noqa: E402
import independent_recompute as ir  # noqa: E402
import learnings_check as lc  # noqa: E402
import plan_check as pc  # noqa: E402
import review_prep as rp  # noqa: E402

REVIEW = rp.REVIEW
RESPONSE = BASE / "assets" / "review_response_sep_oct_2026.md"
CHECKLIST = BASE / "references" / "analytical_rigor_checklist.md"
OWN_FILES = [BASE / "SKILL.md", BASE / "assets" / "peer_review_template.md", BASE / "assets" / "review_response_template.md",
             BASE / "references" / "code_review_for_analysis.md", BASE / "references" / "peer_review_framework.md"]
RUNNER = ROOT / "05-stakeholder-communication/analysis-qa-checklist/scripts/qa_runner.py"
SIGNOFF = cb.SIGNOFF
STATUSES = ("NOT REVIEWED", "IN REVIEW", "COMPLETE")
VERDICTS = ("pending", "approve", "approve with changes", "reject")
SEVERITY = ("blocking", "non-blocking", "note")
FINDING_STATUS = ("open", "fixed", "disputed", "verified")
RESULTS = ("pass", "fail", "unchecked")
HARD_RULES = ("oee-blocked", "deferral", "hypothesis", "unconfirmed", "private-data", "reproduction")
TOLERANCE = 0.01
STALE = ("2 working days", "one round of changes")


def git_status(ref: str, root: Path = ROOT):
    """'ok', 'missing' or 'not-ancestor'; None if git cannot answer."""
    try:
        if subprocess.run(["git", "-C", str(root), "rev-parse", "--git-dir"], capture_output=True, timeout=20).returncode != 0:
            return None
        if subprocess.run(["git", "-C", str(root), "cat-file", "-e", f"{ref}^{{commit}}"], capture_output=True, timeout=20).returncode != 0:
            return "missing"
        anc = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", ref, "HEAD"], capture_output=True, timeout=20)
        return "ok" if anc.returncode == 0 else "not-ancestor"
    except (OSError, subprocess.SubprocessError):
        return None


def field(text: str, label: str) -> str:
    m = re.search(rf"(?m)^{re.escape(label)}: *(.+?) *$", text)
    return m.group(1) if m else ""


def numbers(s: str) -> list[float]:
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)]


def signed(s: str) -> list[float]:
    return [float(x) for x in re.findall(r"[+-]?\d+(?:\.\d+)?", s)]


def check(review, response, checklist, stakeholders, learnings, runner, signoff, own_texts, fresh, indep,
          root: Path = ROOT, git=git_status, today: str | None = None) -> list[tuple[str, str, str]]:
    res = []
    add = lambda n, s, d="": res.append((n, s, d))
    both = review + "\n" + response

    add("no unfilled placeholders", "FAIL" if "[" + "REQUIRED" in both + checklist else "PASS")
    money = cb.deferral.check(both)
    add("no money or throughput figures while impact-quantification is deferred", "PASS" if not money else "FAIL", ", ".join(money[:3]))
    stale = [t for t in STALE if any(t in x.lower() for x in own_texts)]
    add("no stale terms in the skill and its templates", "PASS" if not stale else "FAIL", ", ".join(stale))

    # ---- the kit: checklist
    rows = pc.table(checklist)
    classes = [c["class"] for c in pc.table(pc.section(learnings, "Classes"))]
    need = set(classes) | set(HARD_RULES)
    prob, covered = [], set()
    ids = [r.get("id", "") for r in rows]
    if len(set(ids)) != len(ids) or not rows:
        prob.append("ids are missing or duplicated")
    for r in rows:
        covered |= {t.strip() for t in r["covers"].split(",") if t.strip()}
        if not r["reviewer looks at"]:
            prob.append(f"{r['id']}: nothing for the reviewer to look at")
        if r["enforced by"] == "-":
            if r["when not possible"] in ("-", ""):
                prob.append(f"{r['id']}: no enforcement and no instruction for when it cannot be done")
        else:
            prob += [f"{r['id']}: {p}" for p in lc.resolve(r["enforced by"], root, False)]
    if need - covered:
        prob.append(f"not covered: {sorted(need - covered)}")
    add("the checklist covers every defect class and hard rule, and its enforcement exists", "PASS" if not prob else "FAIL", "; ".join(prob[:5]))

    prob = []
    for c in classes:
        ok = False
        for r in rows:
            if c in [t.strip() for t in r["covers"].split(",")]:
                for p in re.findall(r"`([^`]+)`", r["enforced by"]):
                    name = Path(p).name
                    if name.startswith("test_") and name[:-3] in runner:
                        ok = True
        if not ok:
            prob.append(c)
    add("every defect class has a test that the QA gate runs", "PASS" if not prob else "FAIL", ", ".join(prob))

    # ---- the record: header
    status, author, reviewer = field(review, "**Status**"), field(review, "Author"), field(review, "Reviewer")
    verdict, date, commit = field(review, "Verdict"), field(review, "Date reviewed"), (re.search(r"Release under review: commit `([0-9a-f]{7,40})`", review) or [None, ""])[1]
    complete = status == "COMPLETE"
    prob = []
    if status not in STATUSES:
        prob.append(f"status '{status}'")
    if not author:
        prob.append("no author")
    if verdict not in VERDICTS:
        prob.append(f"verdict '{verdict}'")
    if "0.01 percentage points" not in review:
        prob.append("no tolerance statement")
    if status == "NOT REVIEWED" and date != "-":
        prob.append("a review that has not happened has a date")
    if status != "NOT REVIEWED" and not re.fullmatch(r"\d{4}-\d\d-\d\d", date):
        prob.append("no review date")
    add("the record header is valid", "PASS" if not prob else "FAIL", "; ".join(prob))

    # ---- independence
    if status == "NOT REVIEWED":
        add("a reviewer who is not the author holds the reviewer role", "WARN", "no reviewer named: nobody independent has reviewed this release")
    else:
        names = {r["role"]: r["name"] for r in pc.table(pc.section(stakeholders, "Roles and decision rights"))}
        bad = []
        if not reviewer or "not yet named" in reviewer:
            bad.append("no reviewer named")
        elif author and (author.split(" (")[0].lower() in reviewer.lower() or reviewer.split(" (")[0].lower() in author.lower()):
            bad.append("the reviewer is the author")
        elif reviewer.split(" (")[0] not in names.get("reviewer", ""):
            bad.append("the stakeholder map does not name this person as the reviewer")
        add("a reviewer who is not the author holds the reviewer role", "PASS" if not bad else "FAIL", "; ".join(bad))

    st = git(commit, root) if commit else "missing"
    add("the reviewed commit exists and is part of this history", "PASS" if st in ("ok", None) else "FAIL", "" if st in ("ok", None) else f"commit '{commit}': {st}")

    # ---- the author's preparation and the independent recompute
    want = rp.generate(fresh, indep, root)
    add("the author's preparation is current", "PASS" if rp.block_of(review) == want else "FAIL", "" if rp.block_of(review) == want else "run review_prep.py --write")
    prob = [f"{s}: independent {round(v['high'], 2)} / {round(v['low'], 2)} vs loader {fresh['sides'][s]['availability']} / {fresh['sides'][s]['lower_bound']}"
            for s, v in indep.items()
            if abs(round(v["high"], 2) - fresh["sides"][s]["availability"]) > TOLERANCE or abs(round(v["low"], 2) - fresh["sides"][s]["lower_bound"]) > TOLERANCE]
    add("the recompute without the loader agrees with the loader-based headline", "PASS" if not prob else "FAIL", "; ".join(prob))

    # ---- findings and responses (parsed first: the reproduction and checklist checks cite them)
    findings = pc.table(pc.section(review, "Findings"))
    responses = pc.table(response)
    fprob = []
    fids = [f.get("id", "") for f in findings]
    if len(set(fids)) != len(fids):
        fprob.append("duplicate finding ids")
    resp = {r["finding"]: r for r in responses}
    for f in findings:
        i = f["id"]
        if f["severity"] not in SEVERITY:
            fprob.append(f"{i}: severity '{f['severity']}'")
        if f["status"] not in FINDING_STATUS:
            fprob.append(f"{i}: status '{f['status']}'")
        if not f["finding"] or not f["evidence"] or not f["requested change"]:
            fprob.append(f"{i}: finding, evidence and requested change are all required")
        r = resp.get(i)
        if f["status"] != "open" and r is None:
            fprob.append(f"{i}: {f['status']} but no response")
        if r:
            kind = r["response"].split()[0].lower().strip(",:;") if r["response"] else ""
            if kind not in ("fixed", "disputed", "deferred"):
                fprob.append(f"{i}: response must start with fixed, disputed or deferred")
            if kind == "fixed":
                refs = re.findall(r"`([^`]+)`", r["commit or file"])
                ok = bool(refs) and all((re.fullmatch(r"[0-9a-f]{7,40}", x) and git(x, root) in ("ok", None)) or (root / x).exists() for x in refs)
                if not ok:
                    fprob.append(f"{i}: fixed but the change it cites does not exist")
            if f["status"] == "verified" and r["re-checked by the reviewer"].lower() != "yes":
                fprob.append(f"{i}: verified without the reviewer's re-check")
    fprob += [f"response to unknown finding {k}" for k in resp if k not in fids]
    add("findings are complete, answered and traced to a change", "PASS" if not fprob else "FAIL", "; ".join(fprob[:5]))

    # ---- reproduction
    claims = rp.claims(fresh)
    table = {r["id"]: r for r in pc.table(pc.section(review, "Reviewer's reproduction"))}
    blocking_text = " ".join(f["finding"] + " " + f["evidence"] for f in findings if f["severity"] == "blocking")
    prob = []
    if set(table) != {c["id"] for c in claims}:
        prob.append(f"claims differ: {sorted(set(table) ^ {c['id'] for c in claims})}")
    for c in claims:
        r = table.get(c["id"])
        if not r:
            continue
        if r["claim and author value"] != f"{c['claim']}: {c['value']}":
            prob.append(f"{c['id']}: author value is stale")
        rep, dif, within = r["reproduced"], r["difference"], r["within tolerance"].lower()
        if complete and not (rep and dif and within):
            prob.append(f"{c['id']}: not reproduced")
        if rep:
            a, b = numbers(c["value"]), numbers(rep)
            if len(a) != len(b):
                prob.append(f"{c['id']}: reproduced value has the wrong shape")
                continue
            d = [round(y - x, 2) for x, y in zip(a, b)]
            if len(signed(dif)) != len(d) or any(abs(x - y) > 0.006 for x, y in zip(signed(dif), d)):
                prob.append(f"{c['id']}: difference is not reproduced minus author")
            out = any(abs(x) > TOLERANCE + 1e-9 for x in d)
            if (within == "yes") == out:
                prob.append(f"{c['id']}: 'within tolerance' disagrees with the difference")
            if out and c["id"] not in blocking_text:
                prob.append(f"{c['id']}: outside the tolerance but no blocking finding cites it")
    add("the reviewer's reproduction matches the claims and its arithmetic", "PASS" if not prob else "FAIL", "; ".join(prob[:5]))

    # ---- checklist outcomes
    items = {r["id"]: r for r in rows}
    outcome = {o["item"]: o for o in pc.table(pc.section(review, "Checklist outcome"))}
    prob = []
    if set(outcome) != set(items):
        prob.append(f"items differ from the checklist: {sorted(set(outcome) ^ set(items))}")
    for i, o in outcome.items():
        if o["result"] and o["result"] not in RESULTS:
            prob.append(f"{i}: result '{o['result']}'")
        if complete and not o["result"]:
            prob.append(f"{i}: no result")
        if o["result"] == "unchecked" and not o["note"]:
            prob.append(f"{i}: unchecked without a note")
        if o["result"] == "fail" and not any(i in f["finding"] + " " + f["evidence"] for f in findings):
            prob.append(f"{i}: failed with no finding that cites it")
    add("checklist outcomes are complete and consistent with the findings", "PASS" if not prob else "FAIL", "; ".join(prob[:5]))

    # ---- verdict
    open_block = [f for f in findings if f["severity"] == "blocking" and f["status"] != "verified"]
    open_other = [f for f in findings if f["severity"] == "non-blocking" and f["status"] != "verified"]
    want_v = "pending" if not complete else "reject" if open_block else "approve with changes" if open_other else "approve"
    add("the verdict follows from the findings", "PASS" if verdict == want_v else "FAIL", "" if verdict == want_v else f"verdict '{verdict}' but the findings give '{want_v}'")

    # ---- sign-off
    m = re.search(r"Reviewer \(not the author\): (.+?)\s{2,}", signoff)
    so_reviewer = m.group(1).strip() if m else ""
    so_status = next((l for l in signoff.splitlines() if l.startswith("**Status**")), "")
    prob = []
    approved = complete and verdict in ("approve", "approve with changes")
    if "not signed off" not in so_status and not approved:
        prob.append("the sign-off says signed off but there is no approving review")
    named = so_reviewer and "OPEN" not in so_reviewer
    if named and (not complete or reviewer.split(" (")[0] not in so_reviewer):
        prob.append("the sign-off names a reviewer who has not completed a review record")
    if approved and reviewer.split(" (")[0] not in so_reviewer:
        prob.append("an approving review is not reflected in the sign-off")
    add("the QA sign-off agrees with the review record", "PASS" if not prob else "FAIL", "; ".join(prob))
    return res


def main():
    fresh = cb.fresh_state()
    indep = ir.recompute()
    res = check(REVIEW.read_text(encoding="utf-8"), RESPONSE.read_text(encoding="utf-8"), CHECKLIST.read_text(encoding="utf-8"),
                pc.MAP.read_text(encoding="utf-8"), lc.LOG.read_text(encoding="utf-8"), RUNNER.read_text(encoding="utf-8"),
                SIGNOFF.read_text(encoding="utf-8"), [f.read_text(encoding="utf-8") for f in OWN_FILES], fresh, indep)
    for n, s, d in res:
        print(f"[{s:4s}] {n:78s} {d}")
    fails = sum(1 for _, s, _ in res if s == "FAIL")
    print(f"\n{len(res)} checks: {fails} FAIL, {sum(1 for _, s, _ in res if s == 'WARN')} WARN")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
