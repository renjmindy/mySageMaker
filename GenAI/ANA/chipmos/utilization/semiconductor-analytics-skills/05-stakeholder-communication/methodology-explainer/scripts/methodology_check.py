"""
Checks the methodology slide and write-up against the code and the documents they describe.

  * rule coverage: every assumption id in the metric contract appears in the write-up's rules table, each row
    carries its loader constant (256, 252, 50, 15) and the effect it states matches the measured effect
  * rules ranked by measured effect (A8 near-full, A15 count-list gap, A18 time weighting): the slide must
    name the top two with their numbers - the cleaning rules are not "four", they are what moves the number
  * worked example recomputed from the real loader: minutes counted and closed positions per row, the result,
    and the cases people get wrong (failed read, 252-255, count above list, out-of-range ID, capture gap over the cap)
  * numbers on the slide and in the write-up are traceable to the analysis document; the slide's numbers appear
    in the write-up (subset); no unfilled placeholders; no money figures while impact is deferred
  * plain language on the slide (no glossary jargon, at most ~130 words), limits stated (lower bound, plausible
    range, hypothesis, not OEE), reproduction commands point at scripts that exist
  * the teach-back table equals the write-up's raw columns and does not leak the answer; the audience guide is
    a pointer, not a second copy

Usage:
    python methodology_check.py            # run the checks on the real files
    python methodology_check.py --answer   # answer key for the teach-back exercise
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
for sub in ("lib", "04-data-storytelling-visualization/executive-summary-generator/scripts",
            "05-stakeholder-communication/technical-to-business-translator/scripts"):
    sys.path.insert(0, str(ROOT / sub))
import contactor_io as cio  # noqa: E402
import deferral  # noqa: E402
import exec_summary_check as esc  # noqa: E402
import jargon_detector  # noqa: E402

BASE = HERE.parents[1]
SLIDE = BASE / "assets" / "methodology_slide_sep_oct_2026.md"
WRITEUP = BASE / "assets" / "methodology_writeup_sep_oct_2026.md"
BLANK = BASE / "assets" / "teachback_blank.md"
GUIDE = BASE / "references" / "audience_depth_guide.md"
CANONICAL = ROOT / "02-documentation-knowledge/analysis-documentation/references/audience_depth_guide.md"
CONTRACT = ROOT / "02-documentation-knowledge/semiconductor-metric-definitions/assets/metric_definition.yaml"
SLIDE_MAX_WORDS = 130
RULE_CONSTANT = {"A3": str(cio.READ_FAIL_COUNT), "A8": str(cio.NEAR_FULL_MIN), "A15": str(cio.MAX_COUNT_GAP), "A18": str(int(cio.DEFAULT_MAX_GAP_MIN))}


def table(section_text: str) -> list[list[str]]:
    rows = [l.strip() for l in section_text.splitlines() if l.strip().startswith("|")]
    rows = [r for r in rows if not re.match(r"^\|[\s:|-]+\|$", r)]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows]


def section(text: str, title: str) -> str:
    m = re.search(rf"^## {re.escape(title)}\s*$(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
    return m.group(1) if m else ""


def contract_ids(yaml_text: str) -> list[str]:
    block = yaml_text.split("\ncontract:", 1)[1].split("\nsemantic_model:", 1)[0] if "\ncontract:" in yaml_text else ""
    m = re.search(r"assumptions:\s*\[([^\]]*)\]", block)
    return [x.strip() for x in m.group(1).split(",") if x.strip()] if m else []


def rule_effects(data_dir=None) -> dict[str, float]:
    """Effect (pts) on the front headline, defined as in the analysis document's sensitivity table:
    A8 = adding the 252-255 rule to the 256-only rule; A15 = then adding the count-list gap rule; A18 = weighted vs plain mean."""
    only256 = cio.weighted_availability(cio.load_side("front", data_dir, near_full_min=0, max_count_gap=0)) * 100
    with_a8 = cio.weighted_availability(cio.load_side("front", data_dir, max_count_gap=0)) * 100
    df = cio.load_side("front", data_dir)
    final = cio.weighted_availability(df) * 100
    v = df[df["valid"]]
    return {"A8": abs(with_a8 - only256), "A15": abs(final - with_a8), "A18": abs(final - (1 - v["n_closed"].mean() / 256) * 100)}


def expand(lst: str) -> str:
    out = []
    for tok in lst.split(";"):
        tok = tok.strip()
        m = re.fullmatch(r"(\d+)-(\d+)", tok)
        out += [str(i) for i in range(int(m.group(1)), int(m.group(2)) + 1)] if m else [tok]
    return ";".join(out)


def load_example(rows: list[list[str]]):
    """Run the real loader on the worked-example readings; returns the cleaned frame."""
    d = Path(tempfile.mkdtemp(prefix="method_"))
    lines = ["Timestamp,err_01,err_02"] + [f"2026/09/01 {r[0]},{r[1]},{expand(r[2])}" for r in rows]
    (d / "contactor_20260901.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        return cio.load_side("front", d)
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def answer(rows: list[list[str]]) -> dict:
    df = load_example(rows)
    v = df[df["valid"]]
    return {"availability": cio.weighted_availability(df) * 100, "minutes": float(v["weight_min"].sum()),
            "closed_minutes": float((v["n_closed"] * v["weight_min"]).sum()), "df": df}


def check(slide: str, writeup: str, blank: str, analysis: str, contract_yaml: str, effects: dict[str, float],
          guide: str | None = None, canonical: str | None = None) -> list[tuple[str, str, str]]:
    res = []
    add = lambda name, status, detail="": res.append((name, status, detail))
    s_body, w_body = esc.strip_comments(slide), esc.strip_comments(writeup)

    add("no unfilled placeholders", "FAIL" if "[REQUIRED" in s_body + w_body else "PASS")
    money = deferral.check(s_body + w_body)
    add("no money or throughput figures while impact-quantification is deferred", "PASS" if not money else "FAIL", ", ".join(money[:3]))

    # --- rules table: coverage, constants, effects
    rules = table(section(w_body, "Rules that decide which readings count"))[1:]
    by_id = {r[0]: r for r in rules if r and re.fullmatch(r"A\d+", r[0])}
    need = contract_ids(contract_yaml)
    missing = [i for i in need if i not in by_id]
    add("every contract rule is in the write-up's rules table", "PASS" if not missing else "FAIL", ", ".join(missing))
    bad = [f"{i}: Number column lacks {c} (has {by_id[i][2] or 'nothing'})" for i, c in RULE_CONSTANT.items() if i in by_id and c not in by_id[i][2]]
    add("rules carry the loader's constants", "PASS" if not bad else "FAIL", "; ".join(bad) if bad else "256, 252, 50, 15")
    eff_bad = []
    for i in ("A8", "A15", "A18"):
        if i in by_id and i in effects:
            m = re.search(r"(\d+(?:\.\d+)?)\s*pt", by_id[i][-1])
            if m:
                dec = len(m.group(1).split(".")[1]) if "." in m.group(1) else 0
                if abs(effects[i] - float(m.group(1))) > 0.5 * 10 ** (-dec) + 0.01:  # "about": half a unit plus input rounding
                    eff_bad.append(f"{i}: states {m.group(1)} pts, measured {effects[i]:.2f}")
    add("stated effects equal the measured effects", "PASS" if not eff_bad else "FAIL", "; ".join(eff_bad))

    top2 = sorted(effects, key=effects.get, reverse=True)[:2]
    lacking = [f"{i} ({RULE_CONSTANT[i]})" for i in top2 if i not in s_body or RULE_CONSTANT[i] not in s_body]
    add("the slide names the two rules that move the number most", "PASS" if not lacking else "FAIL",
        f"top two by measured effect: {', '.join(f'{i} {effects[i]:.2f} pts' for i in top2)}" if not lacking else f"slide lacks {', '.join(lacking)}")

    # --- worked example recomputed from the loader
    rows = [r for r in table(section(w_body, "Worked example"))[1:] if len(r) >= 6 and re.fullmatch(r"\d\d:\d\d", r[0])]
    if not rows:
        add("worked example recomputed from the loader", "FAIL", "no readable worked-example table")
    else:
        ans = answer(rows)
        df = ans["df"]
        diffs = []
        for r, (_, d) in zip(rows, df.iterrows()):
            exp_min = float(d["weight_min"]) if d["valid"] else 0.0
            exp_closed = str(int(d["n_closed"])) if d["valid"] else "-"
            if abs(float(r[3]) - exp_min) > 1e-6 or r[4] != exp_closed:
                diffs.append(f"{r[0]}: table {r[3]} min / {r[4]}, loader {exp_min:g} min / {exp_closed}")
        m = re.search(r"Result:\s*\*\*([\d.]+)%\*\*", section(w_body, "Worked example"))
        if not m:
            diffs.append("no 'Result: **x%**' line")
        elif esc._round(ans["availability"], 1) != esc._round(float(m.group(1)), 1):
            diffs.append(f"result {m.group(1)}% but the loader gives {ans['availability']:.2f}%")
        add("worked example recomputed from the loader", "PASS" if not diffs else "FAIL",
            f"{len(rows)} readings, result {ans['availability']:.1f}%" if not diffs else "; ".join(diffs))
        gaps = df["timestamp"].diff().shift(-1).dt.total_seconds().div(60)
        cases = {"a failed read (256)": (df["status"] == "READ_FAIL_256").any(), "a count of 252-255": (df["status"] == "READ_FAIL_NEAR_FULL").any(),
                 "a count above the list": df["count_mismatch"].any(), "an out-of-range position number": (df["n_oob"] > 0).any(),
                 "a capture gap over the 15-minute cap": (gaps > cio.DEFAULT_MAX_GAP_MIN).any()}
        miss = [k for k, ok in cases.items() if not ok]
        add("worked example covers the cases people get wrong", "PASS" if not miss else "FAIL", "missing: " + ", ".join(miss) if miss else "")

    # --- numbers
    wo = re.sub(r"^## Worked example.*?(?=^## )", "", w_body, flags=re.DOTALL | re.MULTILINE)
    bad_nums = esc.untraceable(s_body + "\n" + wo, analysis, esc.derived(slide + writeup))
    add("numbers traceable to the analysis document", "PASS" if not bad_nums else "FAIL", ", ".join(bad_nums[:6]))
    w_nums = [(v, d) for _, v, d in esc.numbers(w_body)]
    not_in_w = [tok for tok, v, d in esc.numbers(s_body) if not any(esc._round(x, d) == esc._round(v, d) for x, _ in w_nums)]
    add("slide numbers also appear in the write-up", "PASS" if not not_in_w else "FAIL", ", ".join(not_in_w))
    s_ids = set(re.findall(r"\bA\d+\b", s_body))
    add("slide rule ids appear in the write-up", "PASS" if s_ids <= set(re.findall(r"\bA\d+\b", w_body)) else "FAIL", ", ".join(sorted(s_ids - set(re.findall(r"\bA\d+\b", w_body)))))

    # --- slide plain language and length
    words = len(re.findall(r"[A-Za-z0-9%.'/-]+", s_body))
    add("slide is short", "PASS" if words <= SLIDE_MAX_WORDS else "FAIL", f"{words} words (max {SLIDE_MAX_WORDS})")
    hits = [f"{t} x{n}" for t, n, _ in jargon_detector.detect(s_body) if t != "oee"]
    add("slide in plain language", "PASS" if not hits else "FAIL", ", ".join(hits))

    # --- limits and reproduction
    low = w_body.lower()
    limits = {"lower bound": "lower bound" in low, "plausible range": "plausible range" in low, "hypothesis": "hypothes" in low,
              "OEE not covered": "oee" in low and bool(re.search(r"cannot|not yet|until", low))}
    miss = [k for k, ok in limits.items() if not ok]
    add("limits stated (lower bound, range, hypothesis, not OEE)", "PASS" if not miss else "FAIL", ", ".join(miss))
    add("slide says it is not OEE and gives a range", "PASS" if "oee" in s_body.lower() and "range" in s_body.lower() else "FAIL")
    cmds = re.findall(r"^python (\S+\.py)", section(w_body, "Reproduce"), re.MULTILINE)
    gone = [c for c in cmds if not (ROOT / c).exists()]
    add("reproduction commands point at existing scripts", "PASS" if cmds and not gone else "FAIL", ", ".join(gone) if gone else f"{len(cmds)} commands")

    # --- teach-back and the audience guide
    raw = [r[:3] for r in table(w_body_example(w_body))[1:] if len(r) >= 3 and re.fullmatch(r"\d\d:\d\d", r[0])]
    blank_rows = [r for r in table(blank)[1:] if re.fullmatch(r"\d\d:\d\d", r[0])]
    leak = bool(re.search(r"90\.\d|Result|minutes counted", blank))
    add("teach-back table equals the write-up's raw columns and hides the answer", "PASS" if raw == blank_rows and raw and not leak else "FAIL",
        "" if raw == blank_rows and not leak else "raw columns differ or the answer leaks")
    if guide is not None and canonical is not None:
        ok = guide.strip() != canonical.strip() and "audience_depth_guide.md" in guide and len(guide) < 1200
        add("audience guide is a pointer, not a second copy", "PASS" if ok else "FAIL")
    return res


def w_body_example(text: str) -> str:
    return section(text, "Worked example")


def main():
    ap = argparse.ArgumentParser(description="Methodology explainer checker")
    ap.add_argument("--answer", action="store_true", help="answer key for the teach-back exercise")
    args = ap.parse_args()
    writeup = WRITEUP.read_text(encoding="utf-8")
    if args.answer:
        rows = [r for r in table(w_body_example(esc.strip_comments(writeup)))[1:] if len(r) >= 6 and re.fullmatch(r"\d\d:\d\d", r[0])]
        a = answer(rows)
        print(f"Answer key: capacity {a['availability']:.1f}% (counted minutes {a['minutes']:g}, closed-position minutes {a['closed_minutes']:g})")
        return
    res = check(SLIDE.read_text(encoding="utf-8"), writeup, BLANK.read_text(encoding="utf-8"), esc.DEFAULT_ANALYSIS.read_text(encoding="utf-8"),
                CONTRACT.read_text(encoding="utf-8"), rule_effects(), GUIDE.read_text(encoding="utf-8"), CANONICAL.read_text(encoding="utf-8"))
    for name, status, detail in res:
        print(f"[{status:4s}] {name:66s} {detail}")
    fails = sum(1 for _, s, _ in res if s == "FAIL")
    print(f"\n{len(res)} checks: {fails} FAIL")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
