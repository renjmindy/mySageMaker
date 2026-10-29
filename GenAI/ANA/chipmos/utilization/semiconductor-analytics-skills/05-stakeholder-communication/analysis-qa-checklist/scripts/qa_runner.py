"""
Automated QA for the contactor utilization analysis.

Two parts, so a data problem is never hidden among repo-health checks:
  * data gate    (data_gate.py): faults in the CSVs - missing/duplicate days, bad format, time zone, swapped
                  sides, unreviewed bad days, data going backwards, headline jumps, ...
  * repo health  unit tests and checks of the other skills, the assumptions log and metric definitions
                  against the loader, headline reconciled across every deliverable, optionally the
                  analysis document's reproduction check

WARNs listed in qa_waivers.json (reason, owner, expiry) show as WAIVED; an expired waiver brings the WARN
back. Exit code 1 only on FAIL.

Usage:
    python qa_runner.py                    # data gate + repo health
    python qa_runner.py --data-only        # just the data gate
    python qa_runner.py --repo-only
    python qa_runner.py --with-doc-check   # also re-run the analysis document's commands (slower)
    python qa_runner.py --update-baseline  # record the current data as the release baseline
"""

import argparse
import contextlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for sub in ("lib", "02-documentation-knowledge/analysis-assumptions-log/scripts", "02-documentation-knowledge/semiconductor-metric-definitions/scripts",
            "05-stakeholder-communication/analysis-qa-checklist/scripts", "03-data-analysis-investigation/oee-calculator/scripts",
            "03-data-analysis-investigation/closure-event-root-cause/scripts", "04-data-storytelling-visualization/executive-summary-generator/scripts",
            "04-data-storytelling-visualization/insight-synthesis/scripts", "04-data-storytelling-visualization/visualization-builder/scripts",
            "04-data-storytelling-visualization/dashboard-specification/scripts", "05-stakeholder-communication/methodology-explainer/scripts", "05-stakeholder-communication/technical-to-business-translator/scripts", "05-stakeholder-communication/stakeholder-requirements-gathering/scripts", "06-workflow-optimization/analysis-planning/scripts"):
    sys.path.insert(0, str(ROOT / sub))
sys.path.insert(0, str(ROOT / "05-stakeholder-communication/impact-quantification/scripts"))
import assumptions_tracker as at  # noqa: E402
import contactor_io as cio  # noqa: E402
import data_gate as dg  # noqa: E402
import deferral  # noqa: E402
import metric_yaml_validator as myv  # noqa: E402


def _tests(add, name, module):
    with contextlib.redirect_stderr(io.StringIO()):
        outcome = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    add(name, "PASS" if outcome.wasSuccessful() else "FAIL", f"{outcome.testsRun} tests, {len(outcome.failures) + len(outcome.errors)} failing")


def _summary(add, name, results, ok="all checks pass"):
    fails = [n for n, s, _ in results if s == "FAIL"]
    warns = [n for n, s, _ in results if s == "WARN"]
    add(name, "FAIL" if fails else "WARN" if warns else "PASS",
        f"failing: {', '.join(fails)}" if fails else (f"warnings: {', '.join(warns)}" if warns else ok))


def repo_checks(with_doc_check: bool = False) -> list[tuple[str, str, str]]:
    res: list[tuple[str, str, str]] = []
    add = lambda name, status, detail="": res.append((name, status, detail))

    problems = at.check(at.load())
    add("assumptions log vs loader", "PASS" if not problems else "FAIL", "consistent" if not problems else "; ".join(problems))
    yaml_path = ROOT / "02-documentation-knowledge/semiconductor-metric-definitions/assets/metric_definition.yaml"
    errs, warns = myv.validate(yaml_path.read_text(encoding="utf-8"))
    add("metric definitions vs loader", "FAIL" if errs else "WARN" if warns else "PASS",
        "; ".join(errs) if errs else (f"{len(warns)} owner(s) not assigned" if warns else "consistent"))

    import test_closure_events as tce
    import test_cost_impact as tci
    import test_dashboard_spec_check as tdsc
    import test_data_gate as tdg
    import test_exec_summary_check as tesc
    import test_insight_brief_check as tibc
    import test_methodology_check as tmc
    import test_plan_check as tpl
    import test_requirements_check as trq
    import test_translator as ttr
    import test_oee_calculator as toee
    import test_viz_check as tvc
    for name, mod in (("data gate fault-injection tests", tdg), ("OEE calculator unit tests", toee), ("impact quantification unit tests", tci), ("closure event unit tests", tce),
                      ("exec summary checker unit tests", tesc), ("insight brief checker unit tests", tibc),
                      ("report checker unit tests", tvc), ("methodology checker unit tests", tmc), ("translator tool tests", ttr), ("requirements checker tests", trq), ("analysis plan checker tests", tpl), ("dashboard spec checker unit tests", tdsc)):
        _tests(add, name, mod)

    import dashboard_spec_check as dsc
    import exec_summary_check as esc
    import insight_brief_check as ibc
    import viz_check as vc
    ib = ibc.check(ibc.DEFAULT_BRIEF.read_text(encoding="utf-8"), ibc.DEFAULT_ANALYSIS.read_text(encoding="utf-8"), at.load(), ibc.DEFAULT_SUMMARY.read_text(encoding="utf-8"))
    _summary(add, "insight brief vs analysis document and log", ib)
    vres = vc.run_static(tvc.DATA, tvc.PAGE)
    add("report vs analysis scripts (static)", "FAIL" if any(s == "FAIL" for _, s, _ in vres) else "PASS",
        f"{len(vres)} checks pass (browser checks: viz_check.py)" if not any(s == "FAIL" for _, s, _ in vres) else "failing: " + ", ".join(n for n, s, _ in vres if s == "FAIL"))
    dres = dsc.check(dsc.DEFAULT_SPEC.read_text(encoding="utf-8"), tdsc.SCHEMA, tdsc.YAML, tdsc.CON, tdsc.BACKTEST, tdsc.HEADLINE)
    _summary(add, "dashboard spec vs schema, data and backtest", dres)
    _summary(add, "executive summary vs analysis document", esc.check(esc.DEFAULT_SUMMARY.read_text(encoding="utf-8"), esc.DEFAULT_ANALYSIS.read_text(encoding="utf-8")))

    import open_questions as oqs
    import requirements_check as rqc
    log = at.load()
    registry = json.loads(oqs.REGISTRY.read_text(encoding="utf-8"))
    markers = oqs.scan_markers()
    rres = rqc.check(rqc.BRIEF.read_text(encoding="utf-8"), rqc.REQS.read_text(encoding="utf-8"), rqc.MAP.read_text(encoding="utf-8"),
                     rqc.GUIDE.read_text(encoding="utf-8"), rqc.SKILL.read_text(encoding="utf-8"), registry, log, markers,
                     oqs.generate(markers, log, registry))
    _summary(add, "requirements work vs the log and the deliverables", rres)

    import plan_check as plc
    pres = plc.check(plc.PLAN.read_text(encoding="utf-8"), plc.SCOPE.read_text(encoding="utf-8"), plc.REQS.read_text(encoding="utf-8"),
                     plc.MAP.read_text(encoding="utf-8"), registry)
    _summary(add, "analysis plan vs requirements, roles and questions", pres)

    import translation_check as trc
    tres = trc.check_text(trc.TRANSLATIONS.read_text(encoding="utf-8"), esc.DEFAULT_ANALYSIS.read_text(encoding="utf-8")) + \
        trc.check_text(trc.LIBRARY.read_text(encoding="utf-8"), esc.DEFAULT_ANALYSIS.read_text(encoding="utf-8"), default_persona="manager")
    _summary(add, "translations and pattern library vs the analysis", [(n, s, d) for n, s, d in tres])

    import methodology_check as mc
    mres = mc.check(mc.SLIDE.read_text(encoding="utf-8"), mc.WRITEUP.read_text(encoding="utf-8"), mc.BLANK.read_text(encoding="utf-8"),
                    esc.DEFAULT_ANALYSIS.read_text(encoding="utf-8"), mc.CONTRACT.read_text(encoding="utf-8"), mc.rule_effects(),
                    mc.GUIDE.read_text(encoding="utf-8"), mc.CANONICAL.read_text(encoding="utf-8"))
    _summary(add, "methodology explainer vs code and documents", mres)

    # headline reconciled across every deliverable (the data is the truth)
    truth = {s: cio.weighted_availability(cio.load_side(s)) * 100 for s in cio.SIDES}
    texts = {"analysis document": esc.DEFAULT_ANALYSIS.read_text(encoding="utf-8"), "insight brief": ibc.DEFAULT_BRIEF.read_text(encoding="utf-8"),
             "executive summary": esc.DEFAULT_SUMMARY.read_text(encoding="utf-8")}
    bad = dg.reconcile(truth, texts)
    for side in cio.SIDES:
        dash = tdsc.CON.execute("SELECT availability FROM capacity_summary WHERE side = ?", (side,)).fetchone()[0]
        if abs(dash - truth[side]) > 0.01:
            bad.append(f"dashboard {side}: {dash:.2f}% vs {truth[side]:.2f}%")
        if f"<b>{truth[side]:.1f}%</b>" not in tvc.PAGE:
            bad.append(f"HTML report {side}: tile does not show {truth[side]:.1f}%")
    add("headline reconciled across all deliverables", "PASS" if not bad else "FAIL",
        "analysis document, insight brief, executive summary, dashboard, HTML report" if not bad else "; ".join(bad))

    leaks = {}
    extra = {"dashboard spec": dsc.DEFAULT_SPEC.read_text(encoding="utf-8"), "HTML report": tvc.PAGE,
             "QA sign-off": (ROOT / "05-stakeholder-communication/analysis-qa-checklist/assets/qa_signoff_sep_oct_2026.md").read_text(encoding="utf-8"),
             "methodology slide": mc.SLIDE.read_text(encoding="utf-8"), "methodology write-up": mc.WRITEUP.read_text(encoding="utf-8")}
    for name, text in {**texts, **extra}.items():
        found = deferral.check(text)
        if found:
            leaks[name] = found[:2]
    add("no money or throughput figures in any deliverable (impact deferred)", "PASS" if not leaks else "FAIL",
        "analysis document, brief, summary, spec, HTML report, sign-off" if not leaks else "; ".join(f"{k}: {v}" for k, v in leaks.items()))

    if with_doc_check:
        script = ROOT / "02-documentation-knowledge/analysis-documentation/scripts/doc_numbers_check.py"
        p = subprocess.run([sys.executable, "-I", str(script)], capture_output=True, text=True, timeout=600)
        last = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-120:]
        add("analysis document reproduces (doc_numbers_check)", "PASS" if p.returncode == 0 else "FAIL", last)
    return res


def run(data_dir=None, start: str = cio.DEFAULT_START, near_full_min: int = cio.NEAR_FULL_MIN, mode: str = "all",
        waivers: bool = True, with_doc_check: bool = False, today: str | None = None) -> list[tuple[str, str, str]]:
    results: list[tuple[str, str, str]] = []
    if mode in ("all", "data"):
        baseline = json.loads(dg.BASELINE_PATH.read_text()) if dg.BASELINE_PATH.exists() else None
        report = dg.VALIDATION_REPORT.read_text(encoding="utf-8") if dg.VALIDATION_REPORT.exists() else None
        results += dg.data_checks(data_dir, start, near_full_min, baseline, report)
    if mode in ("all", "repo"):
        results += repo_checks(with_doc_check)
    return dg.apply_waivers(results, dg.load_waivers(), today) if waivers else results


def main():
    ap = argparse.ArgumentParser(description="Automated QA for contactor analysis")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--start", default=cio.DEFAULT_START)
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN, help="err_01 >= N (<256) is a read failure; 0 disables")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--data-only", action="store_true")
    g.add_argument("--repo-only", action="store_true")
    ap.add_argument("--no-waivers", action="store_true")
    ap.add_argument("--with-doc-check", action="store_true")
    ap.add_argument("--update-baseline", action="store_true")
    args = ap.parse_args()
    if args.update_baseline:
        dg.BASELINE_PATH.write_text(json.dumps(dg.make_baseline(args.data_dir, args.start), indent=2) + "\n", encoding="utf-8")
        print(f"wrote {dg.BASELINE_PATH}")
        return
    mode = "data" if args.data_only else "repo" if args.repo_only else "all"
    res = run(args.data_dir, args.start, args.near_full_min, mode, not args.no_waivers, args.with_doc_check)
    for name, status, detail in res:
        print(f"[{status:6s}] {name:62s} {detail}")
    c = {k: sum(1 for _, s, _ in res if s == k) for k in ("FAIL", "WARN", "WAIVED")}
    print(f"\n{len(res)} checks: {c['FAIL']} FAIL, {c['WARN']} WARN (unwaived), {c['WAIVED']} WAIVED")
    sys.exit(1 if c["FAIL"] else 0)


if __name__ == "__main__":
    main()
