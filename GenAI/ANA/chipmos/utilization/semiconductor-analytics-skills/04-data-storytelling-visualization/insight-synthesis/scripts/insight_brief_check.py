"""
Checks an insight brief against the analysis document and the assumptions log.

  * structure: at most 5 insights, every cell filled, no [REQUIRED] placeholders
  * confidence earned: the cell starts with High/Medium/Low and states the test behind it;
    High may not depend on an OPEN assumption, and may depend on an APPLIED (unconfirmed)
    assumption only if the cell says the result is insensitive to it
  * assumptions: every A-id exists in the log and the status written next to it matches the log
  * traceable numbers: every number (decimal, %, or followed by "points") matches the analysis
    document after rounding, or is a declared derived number whose arithmetic checks out
  * no causal overreach: "cause" / "recover" only in a row that also says hypothesis / not confirmed
  * scoring: score = impact x confidence x actionability, confidence agrees with the label, rows are
    ranked by score; the top and bottom insight survive three alternative weightings
  * coverage: the brief touches the current-state, rear, headline-rules, OEE and trend topics
  * known unknowns mention OEE; an optional executive summary only uses numbers found in the brief

Usage:
    python insight_brief_check.py
    python insight_brief_check.py path/to/brief.md --analysis-doc path/to/analysis.md
"""

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "04-data-storytelling-visualization/executive-summary-generator/scripts"))
sys.path.insert(0, str(ROOT / "02-documentation-knowledge/analysis-assumptions-log/scripts"))
import exec_summary_check as esc  # noqa: E402

DEFAULT_BRIEF = HERE.parents[1] / "assets" / "insight_brief_sep_oct_2026.md"
DEFAULT_ANALYSIS = esc.DEFAULT_ANALYSIS
DEFAULT_SUMMARY = esc.DEFAULT_SUMMARY
LEVEL = {"high": 3, "medium": 2, "low": 1}
CAUSAL = re.compile(r"\b(caus(?:e|es|ed|ing)|recover(?:s|ed|ing)?|root cause)\b", re.IGNORECASE)
HEDGE = re.compile(r"hypothes|not confirmed|unconfirmed|suspect", re.IGNORECASE)
TOPICS = {
    "front groups closed now": r"front.*(now|last 7 days)|(now|last 7 days).*front",
    "rear": r"rear",
    "headline depends on read rules": r"unreadable|failed reading|252-255",
    "OEE": r"oee",
    "trend": r"trend|level shift",
}


def table(section: str) -> list[dict]:
    rows = [l.strip() for l in section.splitlines() if l.strip().startswith("|")]
    rows = [r for r in rows if not re.match(r"^\|[\s:|-]+\|$", r)]
    if len(rows) < 2:
        return []
    cell = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
    head = [h.lower() for h in cell(rows[0])]
    return [dict(zip(head, cell(r))) for r in rows[1:]]


def section(text: str, title: str) -> str:
    m = re.search(rf"^## {re.escape(title)}\s*$(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
    return m.group(1) if m else ""


def rank(scores: dict[str, tuple[int, int, int]], how: str) -> list[str]:
    f = {"product": lambda i, c, a: i * c * a, "impact2": lambda i, c, a: i * i * c * a,
         "sum": lambda i, c, a: i + c + a, "conf_act": lambda i, c, a: c * a}[how]
    return sorted(scores, key=lambda k: -f(*scores[k]))


def top_bottom(scores, how) -> tuple[set, set]:
    f = {"product": lambda i, c, a: i * c * a, "impact2": lambda i, c, a: i * i * c * a,
         "sum": lambda i, c, a: i + c + a, "conf_act": lambda i, c, a: c * a}[how]
    vals = {k: f(*v) for k, v in scores.items()}
    hi, lo = max(vals.values()), min(vals.values())
    return {k for k, v in vals.items() if v == hi}, {k for k, v in vals.items() if v == lo}


def check(brief: str, analysis: str, assumptions: list[dict], summary: str | None = None) -> list[tuple[str, str, str]]:
    res = []
    add = lambda name, status, detail="": res.append((name, status, detail))
    body = esc.strip_comments(brief)
    log = {a["id"]: a for a in assumptions}

    add("no unfilled placeholders", "FAIL" if "[REQUIRED" in body else "PASS")
    ins = table(section(body, "Insights"))
    need = {"#", "insight", "evidence", "confidence", "depends on", "action"}
    if not ins or not need <= set(ins[0]):
        add("insights table", "FAIL", f"needs columns {sorted(need)}")
        return res
    add("at most five insights", "PASS" if 1 <= len(ins) <= 5 else "FAIL", f"{len(ins)} insights")
    empty = [r["#"] for r in ins if any(not r[k] for k in need)]
    add("every cell filled", "PASS" if not empty else "FAIL", f"empty cells in insight(s) {empty}" if empty else "")

    conf_val, bad_conf, bad_dep, bad_status, causal = {}, [], [], [], []
    for r in ins:
        cell = re.sub(r"\*\*", "", r["confidence"])
        lvl = cell.split()[0].strip("-:,.").lower() if cell else ""
        if lvl not in LEVEL or len(cell.split()) < 6:
            bad_conf.append(f"#{r['#']} (needs High/Medium/Low plus the test behind it)")
            continue
        conf_val[r["#"]] = LEVEL[lvl]
        ids = re.findall(r"\bA\d+\b", r["depends on"])
        for aid in ids:
            if aid not in log:
                bad_dep.append(f"#{r['#']}: {aid} not in the assumptions log")
        for aid, st in re.findall(r"\b(A\d+)\s*\((\w+)\)", r["depends on"]):
            if aid in log and log[aid]["status"] != st:
                bad_status.append(f"#{r['#']}: {aid} written as {st}, log says {log[aid]['status']}")
        if lvl == "high":
            st = [log[a]["status"] for a in ids if a in log]
            if "OPEN" in st or "DISPUTED" in st:
                bad_dep.append(f"#{r['#']}: High depends on an OPEN assumption")
            elif "APPLIED" in st and not re.search(r"insensitiv|not sensitive|sensitivity", cell, re.IGNORECASE):
                bad_dep.append(f"#{r['#']}: High depends on an APPLIED assumption without showing insensitivity")
        row_text = " ".join(r[k] for k in ("insight", "evidence", "action"))
        if CAUSAL.search(row_text) and not HEDGE.search(row_text):
            causal.append(f"#{r['#']}")
    add("confidence stated with its test", "PASS" if not bad_conf else "FAIL", "; ".join(bad_conf))
    add("assumption ids and High-confidence rules", "PASS" if not bad_dep else "FAIL", "; ".join(bad_dep))
    add("assumption statuses match the log", "PASS" if not bad_status else "FAIL", "; ".join(bad_status))
    add("no causal overreach", "PASS" if not causal else "FAIL", f"cause/recover without a hypothesis in {', '.join(causal)}" if causal else "")

    text = " ".join(" ".join(r[k] for k in ("insight", "evidence", "action")) for r in ins) + " " + section(body, "Insights").split("|")[0]
    bad = esc.untraceable(text, analysis, esc.derived(brief))
    add("numbers traceable", "PASS" if not bad else "FAIL",
        f"{len(esc.numbers(text))} numbers checked against the analysis document" if not bad else f"not found in the analysis document: {', '.join(bad)}")

    sc = table(section(body, "Scoring"))
    scores, problems = {}, []
    for r in sc:
        try:
            i, c, a, s = (int(r[k]) for k in ("impact", "confidence", "actionability", "score"))
        except (KeyError, ValueError):
            problems.append(f"row {r.get('#', '?')} is incomplete")
            continue
        scores[r["#"]] = (i, c, a)
        if s != i * c * a:
            problems.append(f"#{r['#']}: score {s} != {i}x{c}x{a}")
        if r["#"] in conf_val and conf_val[r["#"]] != c:
            problems.append(f"#{r['#']}: confidence score {c} disagrees with the label in the insights table")
    if set(scores) != {r["#"] for r in ins}:
        problems.append("scoring rows do not match the insights")
    order = [r["#"] for r in ins]
    prod = [scores[k][0] * scores[k][1] * scores[k][2] for k in order if k in scores]
    if prod != sorted(prod, reverse=True):
        problems.append("insights are not listed in score order")
    add("scoring consistent and ranked", "PASS" if not problems else "FAIL", "; ".join(problems))
    if scores and not problems:
        base_top, base_bot = top_bottom(scores, "product")
        moved = [h for h in ("impact2", "sum", "conf_act") if top_bottom(scores, h) != (base_top, base_bot)]
        add("ranking survives re-weighting", "PASS" if not moved else "WARN",
            "top and bottom insight unchanged under 3 alternative weightings" if not moved else f"top/bottom changes under {', '.join(moved)}")

    low = body.lower()
    missing = [k for k, rx in TOPICS.items() if not re.search(rx, low, re.DOTALL)]
    add("covers the current topics", "PASS" if not missing else "WARN", f"not mentioned: {', '.join(missing)}" if missing else "")
    add("known unknowns mention OEE", "PASS" if "oee" in section(body, "Known unknowns").lower() else "FAIL")

    if summary is not None:
        miss = esc.untraceable(esc.strip_comments(summary), body, esc.derived(summary))
        add("executive summary numbers appear in the brief", "PASS" if not miss else "WARN",
            "" if not miss else f"not in the brief: {', '.join(miss)}")
    return res


def main():
    ap = argparse.ArgumentParser(description="Insight brief checker")
    ap.add_argument("brief", nargs="?", default=str(DEFAULT_BRIEF))
    ap.add_argument("--analysis-doc", default=str(DEFAULT_ANALYSIS))
    ap.add_argument("--summary", default=str(DEFAULT_SUMMARY), help="executive summary to cross-check ('' to skip)")
    args = ap.parse_args()
    import assumptions_tracker as at
    summary = Path(args.summary).read_text(encoding="utf-8") if args.summary and Path(args.summary).exists() else None
    res = check(Path(args.brief).read_text(encoding="utf-8"), Path(args.analysis_doc).read_text(encoding="utf-8"), at.load(), summary)
    for name, status, detail in res:
        print(f"[{status:4s}] {name:46s} {detail}")
    fails = sum(1 for _, s, _ in res if s == "FAIL")
    print(f"\n{len(res)} checks: {fails} FAIL, {sum(1 for _, s, _ in res if s == 'WARN')} WARN")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
