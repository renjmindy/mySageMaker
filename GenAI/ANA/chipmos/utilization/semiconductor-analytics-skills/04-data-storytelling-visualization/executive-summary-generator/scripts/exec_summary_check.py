"""
Checks an executive summary against the analysis document.

  * no unfilled [REQUIRED] placeholders; [OPEN] owners/dates in the ask table are warnings
  * answer first: the Bottom line is one short sentence with a number and an action word
  * length: whole summary within --max-words; readable (average sentence length)
  * plain language: no glossary jargon (translator skill), except --allow terms (default: oee)
  * traceable numbers: every number with a decimal point, a % sign or followed by "points" must match, after rounding to the
    precision written, a number in the analysis document, or be declared in a
    `<!-- derived-numbers: 7 = 3.03+2.91+1.11 -->` comment whose arithmetic is verified and whose
    terms all appear in the analysis document
  * honest limits: says OEE cannot be reported yet, shows a range, flags unconfirmed causes

A passing check shows the numbers are plausible and sourced; it does not prove the wording is right
(have a manager read it).

Usage:
    python exec_summary_check.py
    python exec_summary_check.py path/to/summary.md --analysis-doc path/to/analysis.md
"""

import argparse
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "05-stakeholder-communication/technical-to-business-translator/scripts"))
import jargon_detector  # noqa: E402
import readability_scorer  # noqa: E402

DEFAULT_SUMMARY = HERE.parents[1] / "assets" / "executive_summary_sep_oct_2026.md"
DEFAULT_ANALYSIS = ROOT / "02-documentation-knowledge/analysis-documentation/assets/handler_utilization_analysis_sep_oct_2026.md"
ACTION_WORDS = ("inspect", "replace", "repair", "approve", "schedule", "fix", "investigate", "decide", "check", "service")
NUM = re.compile(r"(?<![\w.])\d+(?:\.\d+)?%?")
POINTS = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?=\s*(?:percentage points?|points?|pts)\b)")


def _round(x: float, places: int) -> Decimal:
    q = Decimal(1).scaleb(-places)
    return Decimal(str(x)).quantize(q, rounding=ROUND_HALF_UP)


def numbers(text: str) -> list[tuple[str, float, int]]:
    """(token, value, decimals) for numbers with a decimal point, a % sign, or followed by 'points'."""
    out, seen = [], set()
    pts = {m.start(1) for m in POINTS.finditer(text)}
    for m in NUM.finditer(text):
        tok = m.group(0)
        if "." in tok or tok.endswith("%") or m.start() in pts:
            body = tok.rstrip("%")
            out.append((tok, float(body), len(body.split(".")[1]) if "." in body else 0))
    return out


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def derived(text: str) -> dict[float, str]:
    m = re.search(r"<!--\s*derived-numbers:\s*(.*?)\s*-->", text, re.DOTALL)
    out = {}
    if m:
        for part in m.group(1).split("|"):
            if "=" in part:
                val, expr = part.split("=", 1)
                out[float(val)] = expr.strip()
    return out


def check(summary: str, analysis: str, max_words: int = 300, max_bottom_words: int = 40,
          max_avg_sentence: float = 20.0, allow: tuple[str, ...] = ("oee",)) -> list[tuple[str, str, str]]:
    res = []
    add = lambda name, status, detail="": res.append((name, status, detail))
    body = strip_comments(summary)

    if "[REQUIRED" in body:
        add("no unfilled placeholders", "FAIL", "[REQUIRED] left in the text")
    else:
        add("no unfilled placeholders", "PASS")
    opens = body.count("[OPEN")
    if opens:
        add("owners and dates assigned", "WARN", f"{opens} [OPEN] item(s) in the ask table")

    m = re.search(r"\*\*Bottom line\*\*:\s*(.+)", body)
    if not m:
        add("answer first", "FAIL", "no '**Bottom line**:' sentence")
    else:
        line = m.group(1).strip()
        words = len(line.split())
        has_num = bool(re.search(r"\d", line))
        has_action = any(w in line.lower() for w in ACTION_WORDS)
        ok = words <= max_bottom_words and has_num and has_action
        add("answer first", "PASS" if ok else "FAIL",
            f"{words} words (max {max_bottom_words}), number: {has_num}, action word: {has_action}")

    total = len(re.findall(r"[A-Za-z0-9%.'/-]+", body))
    add("length", "PASS" if total <= max_words else "FAIL", f"{total} words (max {max_words})")
    avg = readability_scorer.score(re.sub(r"\|.*\|", " ", body))["avg_words_per_sentence"]
    add("readability", "PASS" if avg <= max_avg_sentence else "WARN", f"average {avg} words per sentence (max {max_avg_sentence:.0f})")

    hits = [(t, n) for t, n, _ in jargon_detector.detect(body) if t not in allow]
    add("plain language", "PASS" if not hits else "FAIL", "no glossary jargon" if not hits else f"jargon: {', '.join(f'{t} x{n}' for t, n in hits)}")

    doc_nums = [(v, d) for _, v, d in numbers(strip_comments(analysis))]
    der = derived(summary)
    bad = []
    for tok, val, dec in numbers(body):
        if any(_round(v, dec) == _round(val, dec) for v, _ in doc_nums):
            continue
        match = next((dv for dv in der if _round(dv, dec) == _round(val, dec)), None)
        if match is not None:
            terms = [float(x) for x in re.split(r"\+", der[match])]
            tdec = max(len(str(t).split(".")[1]) if "." in str(t) else 0 for t in terms)
            sourced = all(any(_round(v, tdec) == _round(t, tdec) for v, _ in doc_nums) for t in terms)
            arithmetic = _round(sum(terms), dec) == _round(match, dec) == _round(val, dec)
            if sourced and arithmetic:
                continue
            bad.append(f"{tok} (derived: {'terms not in the analysis doc' if not sourced else 'arithmetic does not match'})")
        else:
            bad.append(tok)
    add("numbers traceable", "PASS" if not bad else "FAIL",
        f"{len(numbers(body))} numbers checked against the analysis document" if not bad else f"not found in the analysis document: {', '.join(bad)}")

    low = body.lower()
    add("states OEE is not yet reportable", "PASS" if "oee" in low and re.search(r"cannot|can't|not yet|not be reported|blocked|not measured", low) else "FAIL",
        "needs a sentence saying OEE cannot be reported yet and why")
    add("shows a range", "PASS" if re.search(r"range|between", low) else "FAIL", "needs a plausible range, not only a single figure")
    add("flags unconfirmed causes", "PASS" if re.search(r"hypothesis|not confirmed|unconfirmed|not yet confirmed", low) else "WARN",
        "if a cause is suggested, say it is not confirmed")
    return res


def main():
    ap = argparse.ArgumentParser(description="Executive summary checker")
    ap.add_argument("summary", nargs="?", default=str(DEFAULT_SUMMARY))
    ap.add_argument("--analysis-doc", default=str(DEFAULT_ANALYSIS))
    ap.add_argument("--max-words", type=int, default=300)
    ap.add_argument("--allow", nargs="*", default=["oee"], help="jargon terms acceptable for this audience")
    args = ap.parse_args()
    res = check(Path(args.summary).read_text(encoding="utf-8"), Path(args.analysis_doc).read_text(encoding="utf-8"),
                max_words=args.max_words, allow=tuple(args.allow))
    for name, status, detail in res:
        print(f"[{status:4s}] {name:36s} {detail}")
    fails = sum(1 for _, s, _ in res if s == "FAIL")
    print(f"\n{len(res)} checks: {fails} FAIL, {sum(1 for _, s, _ in res if s == 'WARN')} WARN")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
