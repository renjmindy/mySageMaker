"""
Run the full utilization workflow and write a JSON summary.

Steps: validation -> availability -> chronic sites -> events -> heatmap -> QA gate.
Each step's output is saved under out/pipeline/<timestamp>/. Exit code 1 if QA fails.

Usage:
    python daily_pipeline.py
    python daily_pipeline.py --near-full-min 0   # only to compare against the old 256-only rule
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import contactor_io as cio  # noqa: E402


def steps(nf):
    py = [sys.executable, "-I"]
    extra = ["--near-full-min", str(nf)] if nf is not None else []
    a, b = ROOT / "03-data-analysis-investigation", ROOT / "01-data-quality-validation"
    return [
        ("validation", py + [str(b / "contactor-log-validation/scripts/read_failure_detector.py")] + extra),
        ("availability", py + [str(a / "site-availability/scripts/site_availability.py"), "--quiet-days"] + extra),
        ("chronic_front", py + [str(a / "chronic-site-detection/scripts/chronic_sites.py"), "--side", "front"] + extra),
        ("chronic_rear", py + [str(a / "chronic-site-detection/scripts/chronic_sites.py"), "--side", "rear"] + extra),
        ("events_rear", py + [str(a / "closure-event-root-cause/scripts/closure_events.py"), "--side", "rear", "--min-sites", "4"] + extra),
        ("dashboard_db", py + [str(ROOT / "04-data-storytelling-visualization/dashboard-specification/scripts/build_dashboard_db.py")]),
        ("heatmap", py + [str(ROOT / "04-data-storytelling-visualization/visualization-builder/scripts/site_heatmap.py")] + extra),
        ("qa", py + [str(ROOT / "05-stakeholder-communication/analysis-qa-checklist/scripts/qa_runner.py")] + extra),
    ]


def main():
    ap = argparse.ArgumentParser(description="Daily utilization pipeline")
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN)
    args = ap.parse_args()

    run_dir = ROOT / "out" / "pipeline" / datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    summary = {"run": run_dir.name, "near_full_min": args.near_full_min, "steps": {}}
    for name, cmd in steps(args.near_full_min):
        p = subprocess.run(cmd, capture_output=True, text=True)
        (run_dir / f"{name}.log").write_text(p.stdout + p.stderr, encoding="utf-8")
        summary["steps"][name] = "ok" if p.returncode == 0 else f"FAILED({p.returncode})"
        print(f"{name:14s} {summary['steps'][name]}")

    summary["availability_pct"] = {
        s: round(cio.weighted_availability(cio.load_side(s, near_full_min=args.near_full_min)) * 100, 2) for s in cio.SIDES}
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\navailability: {summary['availability_pct']}\nlogs: {run_dir}")
    sys.exit(1 if summary["steps"]["qa"] != "ok" else 0)


if __name__ == "__main__":
    main()
