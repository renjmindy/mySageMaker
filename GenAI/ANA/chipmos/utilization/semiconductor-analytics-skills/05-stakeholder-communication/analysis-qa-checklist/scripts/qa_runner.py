"""
Automated QA checks for the contactor utilization analysis.

Exit code 1 if any check FAILs.

Usage:
    python qa_runner.py
    python qa_runner.py
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "02-documentation-knowledge/analysis-assumptions-log/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "02-documentation-knowledge/semiconductor-metric-definitions/scripts"))
import contactor_io as cio  # noqa: E402
import assumptions_tracker as at  # noqa: E402
import metric_yaml_validator as myv  # noqa: E402


def run(data_dir, start, near_full_min):
    results = []
    add = lambda name, status, detail: results.append((name, status, detail))
    base = {s: cio.load_side(s, data_dir, start, near_full_min=0, max_count_gap=0) for s in cio.SIDES}  # old 256-only rule, for reference
    used = {s: cio.load_side(s, data_dir, start, near_full_min=near_full_min) for s in cio.SIDES}

    for side, df in used.items():
        v = df[df["valid"]]
        add(f"{side}: scope starts {start}", "PASS" if df["timestamp"].min() >= __import__("pandas").Timestamp(start) else "FAIL",
            f"first sample {df['timestamp'].min()}")
        fail = 1 - len(v) / len(df)
        add(f"{side}: read-failure rate", "PASS" if fail < 0.03 else "WARN" if fail < 0.10 else "FAIL", f"{fail * 100:.2f}%")
        add(f"{side}: closed within 0-256", "PASS" if v["n_closed"].between(0, 256).all() else "FAIL", f"max {v['n_closed'].max()}")
        ids_ok = all(cio.SIDES[side]["lo"] <= s <= cio.SIDES[side]["hi"] for ids in v["sites"] for s in ids)
        add(f"{side}: IDs inside side range", "PASS" if ids_ok else "FAIL", "")
        gap_kept = int((v["err_01"] - v["n_closed"] > cio.MAX_COUNT_GAP).sum())
        add(f"{side}: rows with count-list gap > {cio.MAX_COUNT_GAP} kept", "PASS" if gap_kept == 0 else "FAIL", f"{gap_kept} rows (A15)")
        near = int(v["err_01"].between(cio.NEAR_FULL_MIN, 255).sum())
        add(f"{side}: err_01 252-255 rows kept as valid", "PASS" if near == 0 else "FAIL", f"{near} rows (A8 confirmed read failure)")
        lo_hi_gap = (v["err_01"].clip(upper=256).sub(v["n_closed"]).clip(lower=0) * v["weight_min"]).sum() / v["weight_min"].sum() / 256 * 100
        add(f"{side}: count-vs-list gap (availability pts)", "PASS" if lo_hi_gap < 1 else "WARN", f"{lo_hi_gap:.2f} pts between high and low bound")
        unw = (1 - v["n_closed"].mean() / 256) * 100
        wtd = cio.weighted_availability(df) * 100
        add(f"{side}: weighted vs unweighted", "PASS" if abs(unw - wtd) < 2 else "WARN", f"{wtd:.2f}% vs {unw:.2f}%")
        days = df.groupby(df["timestamp"].dt.date).size()
        low = int((days < 0.75 * 360).sum())
        add(f"{side}: days with < 75% coverage", "PASS" if low <= 1 else "WARN", f"{low} days (last day may be partial)")
        b = cio.weighted_availability(base[side]) * 100
        add(f"{side}: effect of 252-255 + gap rules (info)", "PASS", f"{b:.2f}% (256-only) -> {wtd:.2f}% (confirmed rules)")
    problems = at.check(at.load())
    add("assumptions log vs loader", "PASS" if not problems else "FAIL", "consistent" if not problems else "; ".join(problems))
    yaml_path = Path(__file__).resolve().parents[3] / "02-documentation-knowledge/semiconductor-metric-definitions/assets/metric_definition.yaml"
    errs, warns = myv.validate(yaml_path.read_text(encoding="utf-8"))
    add("metric definitions vs loader", "FAIL" if errs else "WARN" if warns else "PASS",
        "; ".join(errs) if errs else (f"{len(warns)} owner(s) not assigned" if warns else "consistent"))
    import contextlib, io, unittest
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "03-data-analysis-investigation/oee-calculator/scripts"))
    import test_oee_calculator as toee  # noqa: E402
    suite = unittest.defaultTestLoader.loadTestsFromModule(toee)
    with contextlib.redirect_stderr(io.StringIO()):
        outcome = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
    add("OEE calculator unit tests", "PASS" if outcome.wasSuccessful() else "FAIL", f"{outcome.testsRun} tests, {len(outcome.failures) + len(outcome.errors)} failing")
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "03-data-analysis-investigation/closure-event-root-cause/scripts"))
    import test_closure_events as tce  # noqa: E402
    with contextlib.redirect_stderr(io.StringIO()):
        outcome = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromModule(tce))
    add("closure event unit tests", "PASS" if outcome.wasSuccessful() else "FAIL", f"{outcome.testsRun} tests, {len(outcome.failures) + len(outcome.errors)} failing")
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-data-storytelling-visualization/executive-summary-generator/scripts"))
    import exec_summary_check as esc  # noqa: E402
    import test_exec_summary_check as tesc  # noqa: E402
    with contextlib.redirect_stderr(io.StringIO()):
        outcome = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromModule(tesc))
    add("exec summary checker unit tests", "PASS" if outcome.wasSuccessful() else "FAIL", f"{outcome.testsRun} tests, {len(outcome.failures) + len(outcome.errors)} failing")
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-data-storytelling-visualization/insight-synthesis/scripts"))
    import insight_brief_check as ibc  # noqa: E402
    import test_insight_brief_check as tibc  # noqa: E402
    with contextlib.redirect_stderr(io.StringIO()):
        outcome = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromModule(tibc))
    add("insight brief checker unit tests", "PASS" if outcome.wasSuccessful() else "FAIL", f"{outcome.testsRun} tests, {len(outcome.failures) + len(outcome.errors)} failing")
    ib = ibc.check(ibc.DEFAULT_BRIEF.read_text(encoding="utf-8"), ibc.DEFAULT_ANALYSIS.read_text(encoding="utf-8"), at.load(), ibc.DEFAULT_SUMMARY.read_text(encoding="utf-8"))
    ib_fail = [n for n, s_, _ in ib if s_ == "FAIL"]
    ib_warn = [n for n, s_, _ in ib if s_ == "WARN"]
    add("insight brief vs analysis document and log", "FAIL" if ib_fail else "WARN" if ib_warn else "PASS",
        f"failing: {', '.join(ib_fail)}" if ib_fail else (f"warnings: {', '.join(ib_warn)}" if ib_warn else "all checks pass"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-data-storytelling-visualization/visualization-builder/scripts"))
    import viz_check as vc  # noqa: E402
    import test_viz_check as tvc  # noqa: E402
    with contextlib.redirect_stderr(io.StringIO()):
        outcome = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromModule(tvc))
    add("report checker unit tests", "PASS" if outcome.wasSuccessful() else "FAIL", f"{outcome.testsRun} tests, {len(outcome.failures) + len(outcome.errors)} failing")
    vres = vc.run_static(tvc.DATA, tvc.PAGE)
    v_fail = [n for n, s_, _ in vres if s_ == "FAIL"]
    add("report vs analysis scripts (static)", "FAIL" if v_fail else "PASS", f"failing: {', '.join(v_fail)}" if v_fail else f"{len(vres)} checks pass (browser checks: viz_check.py)")
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-data-storytelling-visualization/dashboard-specification/scripts"))
    import dashboard_spec_check as dsc  # noqa: E402
    import test_dashboard_spec_check as tdsc  # noqa: E402
    with contextlib.redirect_stderr(io.StringIO()):
        outcome = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromModule(tdsc))
    add("dashboard spec checker unit tests", "PASS" if outcome.wasSuccessful() else "FAIL", f"{outcome.testsRun} tests, {len(outcome.failures) + len(outcome.errors)} failing")
    dres = dsc.check(dsc.DEFAULT_SPEC.read_text(encoding="utf-8"), tdsc.SCHEMA, tdsc.YAML, tdsc.CON, tdsc.BACKTEST, tdsc.HEADLINE)
    d_fail = [n for n, s_, _ in dres if s_ == "FAIL"]
    d_warn = [n for n, s_, _ in dres if s_ == "WARN"]
    add("dashboard spec vs schema, data and backtest", "FAIL" if d_fail else "WARN" if d_warn else "PASS",
        f"failing: {', '.join(d_fail)}" if d_fail else (f"warnings: {', '.join(d_warn)}" if d_warn else "all checks pass"))
    chk = esc.check(esc.DEFAULT_SUMMARY.read_text(encoding="utf-8"), esc.DEFAULT_ANALYSIS.read_text(encoding="utf-8"))
    fails = [n for n, s_, _ in chk if s_ == "FAIL"]
    warns = [n for n, s_, _ in chk if s_ == "WARN"]
    add("executive summary vs analysis document", "FAIL" if fails else "WARN" if warns else "PASS",
        f"failing: {', '.join(fails)}" if fails else (f"warnings: {', '.join(warns)}" if warns else "all checks pass"))
    return results


def main():
    ap = argparse.ArgumentParser(description="Automated QA for contactor analysis")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--start", default=cio.DEFAULT_START)
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN, help="err_01 >= N (<256) is a read failure; 0 disables")
    args = ap.parse_args()
    res = run(args.data_dir, args.start, args.near_full_min)
    for name, status, detail in res:
        print(f"[{status:4s}] {name:52s} {detail}")
    fails = sum(1 for _, s, _ in res if s == "FAIL")
    warns = sum(1 for _, s, _ in res if s == "WARN")
    print(f"\n{len(res)} checks: {fails} FAIL, {warns} WARN")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
