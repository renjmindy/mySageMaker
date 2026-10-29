"""
Data gate: QA checks on the CSVs themselves, designed to catch faults - not to re-test the loader.

Per side
  * format          the loader raises on a missing column / bad Timestamp / non-numeric err_01
  * scope           analysis start equals the documented scope (A6), not just "whatever was passed in"
  * completeness    no missing calendar day between the first and last reading
  * duplicates      no duplicate timestamps; every reading's day matches its file's day (time zone / renames)
  * flagged days    every day with >= 5% dropped readings or < 75% coverage (last day excluded) must be
                    recorded with a decision in the validation report - a new bad day is a FAIL, not a
                    permanently-on WARN
  * side integrity  share of readings with out-of-range site IDs per day (swapped front/rear files)
  * unflagged band  kept readings with err_01 >= 240 (A14 type) as a share of valid readings
  * failure rate    overall dropped share: WARN >= 5%, FAIL >= 15% (the day-level validation thresholds)
  * baseline        data must not end earlier or have fewer rows than the previous release; a headline
                    move over 1.5 pts (the noise floor in the analysis document) needs an explanation
  * loader guards   invariants that only fail if the loader itself is broken (labelled as such)

WARNs can be waived in qa_waivers.json with a reason, an owner and an expiry date; an expired waiver
lets the WARN reappear, and a new WARN without a waiver stands out.

Usage (normally through qa_runner.py):
    python data_gate.py                       # data checks on the real data
    python data_gate.py --update-baseline     # record this run as the release baseline
"""

import argparse
import json
import re
import sys
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import contactor_io as cio  # noqa: E402

BASELINE_PATH = HERE.parents[1] / "release_baseline.json"
WAIVERS_PATH = HERE.parents[1] / "qa_waivers.json"
VALIDATION_REPORT = ROOT / "01-data-quality-validation/contactor-log-validation/assets/validation_report_sep_oct_2026.md"
EXPECTED_PER_DAY = 360          # ~4 min cadence
DAY_FAIL_REVIEW_PCT = 5.0       # validation_rules.md: HIGH
OVERALL_FAIL_PCT = 15.0         # validation_rules.md: CRITICAL
COVERAGE_REVIEW_PCT = 75.0
OOR_WARN, OOR_FAIL = 10.0, 25.0 # % of readable rows in a day with out-of-range IDs
BAND_WARN, BAND_FAIL = 0.5, 2.0 # % of valid rows with err_01 in [240, near-full)
HEADLINE_NOISE_PTS = 1.5


def flagged_days(report: str) -> set[tuple[str, str]]:
    """(day, side) pairs with a recorded decision in the validation report's flagged-days table."""
    return {(m.group(1), m.group(2)) for m in re.finditer(r"^\|\s*(\d{4}-\d\d-\d\d)\s*\|\s*(front|rear)\s*\|", report, re.MULTILINE)}


def headline(df: pd.DataFrame) -> tuple[float, float]:
    v = df[df["valid"]]
    w = v["weight_min"]
    high = (1 - (v["n_closed"] * w).sum() / (256 * w.sum())) * 100
    upper = v[["err_01", "n_closed"]].max(axis=1).clip(upper=256)
    low = (1 - (upper * w).sum() / (256 * w.sum())) * 100
    return float(high), float(low)


def make_baseline(data_dir=None, start: str = cio.DEFAULT_START, today: str | None = None) -> dict:
    out = {"created": today or str(date.today())}
    for side in cio.SIDES:
        df = cio.load_side(side, data_dir, start)
        high, low = headline(df)
        out[side] = {"data_end": str(df["timestamp"].max()), "rows": int(len(df)),
                     "availability_high": round(high, 2), "availability_low": round(low, 2)}
    return out


def data_checks(data_dir=None, start: str = cio.DEFAULT_START, near_full_min: int = cio.NEAR_FULL_MIN,
                baseline: dict | None = None, validation_report: str | None = None,
                expected_start: str = cio.DEFAULT_START) -> list[tuple[str, str, str]]:
    res: list[tuple[str, str, str]] = []
    add = lambda name, status, detail="": res.append((name, status, detail))

    add("analysis start equals the documented scope (A6)", "PASS" if start == expected_start else "FAIL",
        f"start {start}" if start == expected_start else f"start {start} but the documented scope starts {expected_start} (07/30 was a trial run)")
    try:
        used = {s: cio.load_side(s, data_dir, start, near_full_min=near_full_min) for s in cio.SIDES}
        base = {s: cio.load_side(s, data_dir, start, near_full_min=0, max_count_gap=0) for s in cio.SIDES}  # 256-only rule, for the info line
    except (cio.DataFormatError, FileNotFoundError) as e:
        add("data format", "FAIL", str(e)[:200])
        return res
    add("data format", "PASS", "columns and values readable")
    flagged = flagged_days(validation_report) if validation_report is not None else None

    for side, df in used.items():
        v = df[df["valid"]]
        d = df.assign(day=df["timestamp"].dt.strftime("%Y-%m-%d"))
        g = d.groupby("day").agg(total=("valid", "size"), valid=("valid", "sum"))
        g["fail_pct"] = (1 - g["valid"] / g["total"]) * 100
        g["coverage_pct"] = g["total"] / EXPECTED_PER_DAY * 100

        expected_days = pd.date_range(df["timestamp"].min().normalize(), df["timestamp"].max().normalize())
        missing = [x.strftime("%Y-%m-%d") for x in expected_days if x.strftime("%Y-%m-%d") not in g.index]
        add(f"{side}: no missing days", "PASS" if not missing else "FAIL", ", ".join(missing[:6]) if missing else f"{len(g)} days")

        dups, mism = df.attrs.get("duplicate_timestamps", 0), df.attrs.get("file_date_mismatch", 0)
        add(f"{side}: no duplicate timestamps", "PASS" if dups == 0 else "FAIL", f"{dups} duplicates")
        add(f"{side}: reading days match their file days", "PASS" if mism == 0 else "FAIL", f"{mism} readings in the wrong day's file (time zone? renamed file?)")

        need = set(g.index[g["fail_pct"] >= DAY_FAIL_REVIEW_PCT])
        need |= set(g.index[:-1][g["coverage_pct"].iloc[:-1] < COVERAGE_REVIEW_PCT])  # the last day may be partial
        if flagged is None:
            add(f"{side}: flagged days have a recorded decision", "WARN", "no validation report supplied")
        else:
            unreviewed = sorted(day for day in need if (day, side) not in flagged)
            add(f"{side}: flagged days have a recorded decision", "PASS" if not unreviewed else "FAIL",
                f"{len(need)} day(s) at >= {DAY_FAIL_REVIEW_PCT:.0f}% dropped or < {COVERAGE_REVIEW_PCT:.0f}% coverage, all recorded" if not unreviewed
                else f"not in the validation report: {', '.join(unreviewed)}")

        ok_rows = d[d["status"] == "OK"]
        oor = (ok_rows.assign(o=ok_rows["n_oob"] > 0).groupby("day")["o"].mean() * 100) if len(ok_rows) else pd.Series(dtype=float)
        worst = float(oor.max()) if len(oor) else 0.0
        add(f"{side}: site IDs belong to this side", "PASS" if worst < OOR_WARN else "WARN" if worst < OOR_FAIL else "FAIL",
            f"worst day {worst:.1f}% of readings with out-of-range IDs" + (f" ({oor.idxmax()})" if worst >= OOR_WARN else ""))

        band = float(((v["err_01"] >= 240) & (v["err_01"] < (near_full_min or 256))).mean() * 100) if len(v) else 0.0
        add(f"{side}: unflagged near-full band (A14 type)", "PASS" if band < BAND_WARN else "WARN" if band < BAND_FAIL else "FAIL",
            f"{band:.2f}% of valid readings with err_01 in 240-{(near_full_min or 256) - 1}")

        fail = (1 - len(v) / len(df)) * 100
        add(f"{side}: dropped-reading rate", "PASS" if fail < DAY_FAIL_REVIEW_PCT else "WARN" if fail < OVERALL_FAIL_PCT else "FAIL", f"{fail:.2f}%")

        if baseline and side in baseline:
            b = baseline[side]
            end_ok = df["timestamp"].max() >= pd.Timestamp(b["data_end"])
            rows_ok = len(df) >= b["rows"]
            add(f"{side}: data has not gone backwards since the last release", "PASS" if end_ok and rows_ok else "FAIL",
                f"ends {df['timestamp'].max()} ({len(df)} rows) vs {b['data_end']} ({b['rows']} rows)")
            high, low = headline(df)
            delta = high - b["availability_high"]
            add(f"{side}: headline vs the last release", "PASS" if abs(delta) <= HEADLINE_NOISE_PTS else "WARN",
                f"{high:.2f}% vs {b['availability_high']:.2f}% ({delta:+.2f} pts; > {HEADLINE_NOISE_PTS} needs an explanation)")
        else:
            add(f"{side}: data has not gone backwards since the last release", "WARN", "no release baseline (run data_gate.py --update-baseline)")

        # loader guards: these can only fail if the loader itself is broken
        guards_ok = (v["n_closed"].between(0, 256).all()
                     and all(cio.SIDES[side]["lo"] <= s <= cio.SIDES[side]["hi"] for ids in v["sites"] for s in ids)
                     and int((v["err_01"] - v["n_closed"] > cio.MAX_COUNT_GAP).sum()) == 0
                     and int(v["err_01"].between(cio.NEAR_FULL_MIN, 255).sum()) == 0)
        add(f"{side}: loader guards hold (regression guard, not a data check)", "PASS" if guards_ok else "FAIL", "closed 0-256, IDs in range, gap and 252-255 rows dropped")
        unw = (1 - v["n_closed"].mean() / 256) * 100
        wtd = cio.weighted_availability(df) * 100
        add(f"{side}: weighted vs unweighted", "PASS" if abs(unw - wtd) < 2 else "WARN", f"{wtd:.2f}% vs {unw:.2f}%")
        b256 = cio.weighted_availability(base[side]) * 100
        add(f"{side}: effect of 252-255 + gap rules (info)", "PASS", f"{b256:.2f}% (256-only) -> {wtd:.2f}% (confirmed rules)")
    return res


def load_waivers(path=WAIVERS_PATH) -> list[dict]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def apply_waivers(results: list[tuple[str, str, str]], waivers: list[dict], today: str | None = None) -> list[tuple[str, str, str]]:
    """WARN -> WAIVED when a matching, unexpired waiver exists; expired waivers are mentioned and the WARN stays."""
    now = date.fromisoformat(today) if today else date.today()
    out = []
    for name, status, detail in results:
        if status == "WARN":
            for w in waivers:
                if w["check"] in name:
                    if date.fromisoformat(w["expires"]) >= now:
                        name, status = name, "WAIVED"
                        detail = f"{detail} | waived: {w['reason']} ({w['owner']}, until {w['expires']})"
                    else:
                        detail = f"{detail} | waiver expired {w['expires']}"
                    break
        out.append((name, status, detail))
    return out


def _round(x: float, places: int) -> Decimal:
    return Decimal(str(x)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def reconcile(truth: dict[str, float], texts: dict[str, str]) -> list[str]:
    """Headline per deliverable vs the loader's number, compared at the precision each deliverable writes.

    texts: name -> text; recognised layouts are the analysis document table row, the insight brief
    headline line, the executive summary bottom line, and any `front <n>%` / `rear <n>%` pair.
    Returns the mismatches (empty = reconciled).
    """
    patterns = {
        "analysis document": (r"\|\s*front\s*\|\s*\*\*([\d.]+)%\*\*", r"\|\s*rear\s*\|\s*\*\*([\d.]+)%\*\*"),
        "insight brief": (r"\*\*Headline\*\*:\s*front ([\d.]+)%", r"rear ([\d.]+)%"),
        "executive summary": (r"([\d.]+)% of front", r"([\d.]+)% of rear"),
    }
    bad = []
    for name, text in texts.items():
        pf, pr = patterns.get(name, (r"front[^\d]{0,30}([\d.]+)%", r"rear[^\d]{0,30}([\d.]+)%"))
        for side, pat in (("front", pf), ("rear", pr)):
            m = re.search(pat, text)
            if not m:
                bad.append(f"{name}: no {side} headline found")
                continue
            written = m.group(1)
            dec = len(written.split(".")[1]) if "." in written else 0
            if _round(truth[side], dec) != _round(float(written), dec):
                bad.append(f"{name} {side}: writes {written}% but the data gives {truth[side]:.2f}%")
    return bad


def main():
    ap = argparse.ArgumentParser(description="Data gate")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--start", default=cio.DEFAULT_START)
    ap.add_argument("--update-baseline", action="store_true", help="record this run as the release baseline")
    args = ap.parse_args()
    if args.update_baseline:
        BASELINE_PATH.write_text(json.dumps(make_baseline(args.data_dir, args.start), indent=2) + "\n", encoding="utf-8")
        print(f"wrote {BASELINE_PATH}")
        return
    baseline = json.loads(BASELINE_PATH.read_text()) if BASELINE_PATH.exists() else None
    report = VALIDATION_REPORT.read_text(encoding="utf-8") if VALIDATION_REPORT.exists() else None
    res = apply_waivers(data_checks(args.data_dir, args.start, baseline=baseline, validation_report=report), load_waivers())
    for name, status, detail in res:
        print(f"[{status:6s}] {name:62s} {detail}")
    sys.exit(1 if any(s == "FAIL" for _, s, _ in res) else 0)


if __name__ == "__main__":
    main()
