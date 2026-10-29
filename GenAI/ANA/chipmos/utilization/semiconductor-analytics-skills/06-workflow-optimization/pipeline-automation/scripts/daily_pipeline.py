"""
Run the full utilization workflow, write a JSON summary, and say clearly whether the run succeeded.

Steps: validation -> availability -> chronic sites -> events -> dashboard database -> export for PostgreSQL ->
alert evaluation -> heatmap -> QA gate. Each step's output is saved under out/pipeline/<run>/.

A run is `ok` only if every step is ok (a failed step fails the run, whatever the QA step says), `failed` if a step
or the freshness limit failed, `crashed` if something raised. The summary is ALWAYS written (atomically), even
after a crash. `out/pipeline/latest.json` points at the newest run that was ok; a failed run never replaces it.
Only one run at a time (a lock file); a second one exits with code 2.

Exit code: 0 ok, 1 failed or crashed, 2 another run is active.

Usage:
    python daily_pipeline.py
    python daily_pipeline.py --gate data                 # data gate only, no repository documentation checks
    python daily_pipeline.py --max-data-age-hours 6      # fail the run if the newest reading is older
    python daily_pipeline.py --data-dir /path/to/csv --start 2026-09-15 --keep 30
    python daily_pipeline.py --near-full-min 0           # only to compare against the old 256-only rule

Notification: if the environment variable PIPELINE_NOTIFY_CMD is set (for example "python /opt/notify.py"), it is
run as `<command> failed|alerts <summary.json>` when the run failed or alerts are firing. No channel is built in.
"""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import contactor_io as cio  # noqa: E402

NOTIFY_ENV = "PIPELINE_NOTIFY_CMD"
RUN_ID = re.compile(r"^\d{8}_\d{6}(_\d+)?$")
QA_LINE = re.compile(r"(\d+) checks: (\d+) FAIL, (\d+) WARN \(unwaived\), (\d+) WAIVED")
COMMON = ("data-dir", "start", "near-full-min")
A, B = "03-data-analysis-investigation", "01-data-quality-validation"
# name, script (relative to the repository, or to this folder when it starts with "./"), fixed arguments, options the script accepts.
# test_pipeline.py checks the options column against the scripts themselves.
SCRIPTS = [
    ("validation", f"{B}/contactor-log-validation/scripts/read_failure_detector.py", [], COMMON),
    ("availability", f"{A}/site-availability/scripts/site_availability.py", ["--quiet-days"], COMMON),
    ("chronic_front", f"{A}/chronic-site-detection/scripts/chronic_sites.py", ["--side", "front"], COMMON),
    ("chronic_rear", f"{A}/chronic-site-detection/scripts/chronic_sites.py", ["--side", "rear"], COMMON),
    ("events_front", f"{A}/closure-event-root-cause/scripts/closure_events.py", ["--side", "front", "--min-sites", "4"], COMMON),
    ("events_rear", f"{A}/closure-event-root-cause/scripts/closure_events.py", ["--side", "rear", "--min-sites", "4"], COMMON),
    ("dashboard_db", "04-data-storytelling-visualization/dashboard-specification/scripts/build_dashboard_db.py", ["--output", "{db}"], ("data-dir", "start")),
    ("store", "./export_for_postgres.py", ["--db", "{db}", "--output", "{run}/postgres"], ()),
    ("alerts", "./evaluate_alerts.py", ["--db", "{db}", "--output", "{run}/alerts.json"], ()),
    ("heatmap", "04-data-storytelling-visualization/visualization-builder/scripts/site_heatmap.py", [], COMMON),
    ("qa", "05-stakeholder-communication/analysis-qa-checklist/scripts/qa_runner.py", ["{gate}"], COMMON),
]


class LockHeld(Exception):
    pass


def steps(opts: dict, run_dir: Path, root: Path = ROOT) -> list[tuple[str, list[str]]]:
    out = []
    db = root / "out" / "dashboard.sqlite"
    gate = "--with-doc-check" if opts["gate"] == "full" else "--data-only"
    for name, script, fixed, accepts in SCRIPTS:
        path = HERE / script[2:] if script.startswith("./") else root / script
        cmd = [sys.executable, "-I", str(path)] + [a.format(db=db, run=run_dir, gate=gate) for a in fixed]
        if "near-full-min" in accepts and opts["near_full_min"] is not None:
            cmd += ["--near-full-min", str(opts["near_full_min"])]
        if "data-dir" in accepts and opts["data_dir"]:
            cmd += ["--data-dir", str(opts["data_dir"])]
        if "start" in accepts and opts["start"]:
            cmd += ["--start", opts["start"]]
        out.append((name, cmd))
    return out


def run_step(cmd: list[str], log: Path) -> tuple[str, float]:
    t = time.monotonic()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
        log.write_text(p.stdout + p.stderr, encoding="utf-8")
        status = "ok" if p.returncode == 0 else f"FAILED({p.returncode})"
    except OSError as e:
        log.write_text(f"could not start: {e}\n", encoding="utf-8")
        status = "FAILED(-1)"
    return status, round(time.monotonic() - t, 1)


def measure(opts: dict, now: datetime) -> dict:
    """Headline and data age, from the shared loader."""
    out = {"availability_pct": {}, "data": {}}
    for side in cio.SIDES:
        df = cio.load_side(side, opts["data_dir"], opts["start"] or cio.DEFAULT_START, near_full_min=opts["near_full_min"])
        last = df["timestamp"].max().to_pydatetime()
        out["availability_pct"][side] = round(cio.weighted_availability(df) * 100, 2)
        out["data"][side] = {"last_reading": last.strftime("%Y-%m-%d %H:%M"), "age_hours": round((now - last).total_seconds() / 3600, 1)}
    return out


def freshness(data: dict, max_age_hours) -> dict:
    ages = {s: v["age_hours"] for s, v in data.items()}
    oldest = max(ages.values())
    if max_age_hours is None:
        return {"status": "not enforced", "max_age_hours": None, "message": f"newest readings are {ages} hours old; set --max-data-age-hours to enforce a limit"}
    late = {s: a for s, a in ages.items() if a > max_age_hours}
    return {"status": "FAILED" if late else "ok", "max_age_hours": max_age_hours,
            "message": f"older than {max_age_hours} hours: {late}" if late else f"newest reading is {oldest} hours old"}


def parse_qa(log_text: str):
    m = QA_LINE.search(log_text)
    return dict(zip(("checks", "fail", "warn", "waived"), map(int, m.groups()))) if m else None


def new_run_dir(base: Path, now: datetime) -> Path:
    name = now.strftime("%Y%m%d_%H%M%S")
    n = 1
    while True:
        cand = base / (name if n == 1 else f"{name}_{n}")
        try:
            cand.mkdir(parents=True)
            return cand
        except FileExistsError:
            n += 1


def write_json(path: Path, obj) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def acquire_lock(base: Path) -> Path:
    lock = base / ".lock"
    for _ in range(2):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return lock
        except FileExistsError:
            try:
                pid = int(lock.read_text().strip())
                os.kill(pid, 0)
                raise LockHeld(f"another run is active (pid {pid})")
            except (ValueError, ProcessLookupError, FileNotFoundError):
                lock.unlink(missing_ok=True)  # stale: the holder is gone
            except PermissionError:
                raise LockHeld("another run is active")
    raise LockHeld("could not take the lock")


def release_lock(lock: Path) -> None:
    try:
        if lock.read_text().strip() == str(os.getpid()):
            lock.unlink()
    except FileNotFoundError:
        pass


def apply_retention(base: Path, keep: int, current: Path) -> list[str]:
    runs = sorted(d for d in base.iterdir() if d.is_dir() and RUN_ID.match(d.name))
    removed = [d for d in runs[:-keep] if d != current] if keep > 0 else []
    for d in removed:
        shutil.rmtree(d)
    return [d.name for d in removed]


def notify(kind: str, summary_path: Path, cmd_text: str | None) -> dict:
    if not cmd_text:
        return {"kind": kind, "result": "no notification command configured"}
    try:
        p = subprocess.run(shlex.split(cmd_text) + [kind, str(summary_path)], capture_output=True, text=True, timeout=60)
        return {"kind": kind, "result": "sent" if p.returncode == 0 else f"hook exited {p.returncode}"}
    except (OSError, subprocess.SubprocessError) as e:
        return {"kind": kind, "result": f"hook failed: {type(e).__name__}"}


def git_state(root: Path):
    try:
        h = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=20)
        d = subprocess.run(["git", "-C", str(root), "diff", "--quiet", "HEAD", "--", str(root)], capture_output=True, timeout=20)
        return (h.stdout.strip(), d.returncode != 0) if h.returncode == 0 else (None, None)
    except (OSError, subprocess.SubprocessError):
        return None, None


def run_pipeline(opts: dict, root: Path = ROOT, steps_fn=steps, measure_fn=measure, now_fn=datetime.now, notify_cmd: str | None = None,
                 echo=print) -> tuple[dict, int]:
    base = root / "out" / "pipeline"
    base.mkdir(parents=True, exist_ok=True)
    try:
        lock = acquire_lock(base)
    except LockHeld as e:
        echo(f"not started: {e}")
        return {"status": "locked", "error": str(e)}, 2
    started = now_fn()
    run_dir = new_run_dir(base, started)
    commit, dirty = git_state(root)
    summary = {"run": run_dir.name, "status": "crashed", "started": started.isoformat(timespec="seconds"), "finished": None, "seconds": None,
               "commit": commit, "dirty": dirty, "gate": opts["gate"], "near_full_min": opts["near_full_min"], "start": opts["start"] or cio.DEFAULT_START,
               "data_dir": "custom" if opts["data_dir"] else "default", "steps": {}, "step_seconds": {}, "availability_pct": None, "data": None,
               "freshness": None, "qa": None, "alerts_firing": None, "published": False, "notified": [], "removed_runs": [], "error": None}
    t0 = time.monotonic()
    try:
        for name, cmd in steps_fn(opts, run_dir):
            summary["steps"][name], summary["step_seconds"][name] = run_step(cmd, run_dir / f"{name}.log")
            echo(f"{name:14s} {summary['steps'][name]}")
        m = measure_fn(opts, now_fn())
        summary["availability_pct"], summary["data"] = m["availability_pct"], m["data"]
        summary["freshness"] = freshness(m["data"], opts.get("max_data_age_hours"))
        if summary["freshness"]["status"] == "FAILED":
            summary["steps"]["freshness"] = "FAILED(1)"
        echo(f"{'freshness':14s} {summary['freshness']['status']}: {summary['freshness']['message']}")
        qa_log = run_dir / "qa.log"
        summary["qa"] = parse_qa(qa_log.read_text(encoding="utf-8")) if qa_log.exists() else None
        alerts = run_dir / "alerts.json"
        if alerts.exists():
            summary["alerts_firing"] = [f"{a['id']}:{a['scope']}" for a in json.loads(alerts.read_text(encoding="utf-8"))["alerts"] if a["firing"]]
        summary["status"] = "ok" if all(v == "ok" for v in summary["steps"].values()) else "failed"
    except Exception as e:  # the summary must exist whatever happened
        summary["status"] = "crashed"
        summary["error"] = f"{type(e).__name__}: {e}"
    finally:
        summary["finished"] = now_fn().isoformat(timespec="seconds")
        summary["seconds"] = round(time.monotonic() - t0, 1)
        try:
            if summary["status"] == "ok":
                write_json(base / "latest.json", {"run": run_dir.name, "finished": summary["finished"]})
                summary["published"] = True
                if opts.get("keep"):
                    summary["removed_runs"] = apply_retention(base, opts["keep"], run_dir)
            write_json(run_dir / "summary.json", summary)
            kinds = (["failed"] if summary["status"] != "ok" else []) + (["alerts"] if summary["alerts_firing"] else [])
            summary["notified"] = [notify(k, run_dir / "summary.json", notify_cmd) for k in kinds]
            if kinds:
                write_json(run_dir / "summary.json", summary)
        finally:
            release_lock(lock)
    echo(f"\nstatus: {summary['status']}" + (f" ({summary['error']})" if summary["error"] else ""))
    if summary["availability_pct"]:
        echo(f"availability: {summary['availability_pct']}")
    if summary["alerts_firing"]:
        echo(f"alerts firing: {summary['alerts_firing']}")
    echo(f"logs: {run_dir}")
    return summary, 0 if summary["status"] == "ok" else 1


def main():
    ap = argparse.ArgumentParser(description="Daily utilization pipeline")
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN)
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--start", default=None, help="first day to analyse (default: the loader's)")
    ap.add_argument("--gate", choices=["full", "data"], default="full", help="full = the whole repository gate; data = the data gate only")
    ap.add_argument("--max-data-age-hours", type=float, default=None, help="fail the run if a side's newest reading is older (no default: the data owner decides)")
    ap.add_argument("--keep", type=int, default=None, help="after an ok run keep only the newest N run folders")
    a = ap.parse_args()
    opts = {"near_full_min": a.near_full_min, "data_dir": a.data_dir, "start": a.start, "gate": a.gate,
            "max_data_age_hours": a.max_data_age_hours, "keep": a.keep}
    _, code = run_pipeline(opts, notify_cmd=os.environ.get(NOTIFY_ENV))
    sys.exit(code)


if __name__ == "__main__":
    main()
