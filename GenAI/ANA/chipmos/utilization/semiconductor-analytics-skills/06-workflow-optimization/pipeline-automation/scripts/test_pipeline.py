"""
Tests for daily_pipeline.py, evaluate_alerts.py and export_for_postgres.py, using fake steps in temporary folders
(the real pipeline is never started from here: the QA gate runs these tests, and the pipeline runs the QA gate).

Usage:
    python test_pipeline.py
"""

import ast
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import daily_pipeline as dp  # noqa: E402
import evaluate_alerts as ea  # noqa: E402
import export_for_postgres as ex  # noqa: E402

ROOT = dp.ROOT
BASE = HERE.parent
OPTS = {"near_full_min": 252, "data_dir": None, "start": None, "gate": "full", "max_data_age_hours": None, "keep": None}
FIXED = datetime(2026, 10, 29, 12, 0, 0)
GOOD = {"availability_pct": {"front": 91.3, "rear": 96.0}, "data": {"front": {"last_reading": "x", "age_hours": 2.0}, "rear": {"last_reading": "x", "age_hours": 3.0}}}
QA_OK = "print('12 checks: 0 FAIL, 1 WARN (unwaived), 3 WAIVED')"


def fake_steps(*specs):
    def fn(opts, run_dir):
        return [(n, [sys.executable, "-I", "-c", code.replace("RUNDIR", repr(str(run_dir)))]) for n, code in specs]
    return fn


class Clock:
    def __init__(self):
        self.t = FIXED

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


def go(root, steps, opts=None, measure=lambda o, n: GOOD, now=None, notify_cmd=None):
    return dp.run_pipeline({**OPTS, **(opts or {})}, Path(root), steps_fn=steps, measure_fn=measure, now_fn=now or Clock(), notify_cmd=notify_cmd, echo=lambda s: None)


class TestRunSemantics(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_an_ok_run_is_published_and_the_summary_is_complete(self):
        s, code = go(self.root, fake_steps(("a", "pass"), ("qa", QA_OK)))
        self.assertEqual((s["status"], code, s["published"]), ("ok", 0, True))
        self.assertEqual(s["qa"], {"checks": 12, "fail": 0, "warn": 1, "waived": 3})
        for key in ("run", "status", "started", "finished", "seconds", "commit", "gate", "steps", "step_seconds", "availability_pct", "data", "freshness"):
            self.assertIn(key, s)
        self.assertEqual(json.loads((self.root / "out/pipeline/latest.json").read_text())["run"], s["run"])
        self.assertEqual(json.loads((self.root / "out/pipeline" / s["run"] / "summary.json").read_text())["status"], "ok")

    def test_a_failed_step_fails_the_run_even_when_qa_passes(self):
        """The defect found in the old runner: a failed middle step, a passing QA step, exit code 0."""
        s, code = go(self.root, fake_steps(("validation", "pass"), ("availability", "import sys; sys.exit(3)"), ("qa", QA_OK)))
        self.assertEqual((s["status"], code), ("failed", 1))
        self.assertEqual(s["steps"]["availability"], "FAILED(3)")
        self.assertEqual(s["steps"]["qa"], "ok")
        self.assertFalse(s["published"])
        self.assertFalse((self.root / "out/pipeline/latest.json").exists())

    def test_a_failing_qa_step_fails_the_run(self):
        s, code = go(self.root, fake_steps(("a", "pass"), ("qa", "import sys; sys.exit(1)")))
        self.assertEqual((s["status"], code), ("failed", 1))

    def test_a_step_that_cannot_start_fails_the_run(self):
        s, code = go(self.root, lambda o, r: [("a", ["/no/such/program"]), ("qa", [sys.executable, "-I", "-c", QA_OK])])
        self.assertEqual((s["steps"]["a"], s["status"], code), ("FAILED(-1)", "failed", 1))
        self.assertIn("could not start", (self.root / "out/pipeline" / s["run"] / "a.log").read_text())

    def test_a_crash_still_writes_the_summary_with_the_steps_that_ran(self):
        def boom(o, n):
            raise ValueError("err_01 has 3 non-numeric value(s)")
        s, code = go(self.root, fake_steps(("a", "pass"), ("qa", QA_OK)), measure=boom)
        self.assertEqual((s["status"], code), ("crashed", 1))
        written = json.loads((self.root / "out/pipeline" / s["run"] / "summary.json").read_text())
        self.assertEqual(written["status"], "crashed")
        self.assertIn("non-numeric", written["error"])
        self.assertEqual(written["steps"], {"a": "ok", "qa": "ok"})
        self.assertFalse(written["published"])

    def test_an_exception_while_building_the_steps_is_a_crash_not_a_traceback(self):
        def bad(opts, run_dir):
            raise RuntimeError("cannot list steps")
        s, code = go(self.root, bad)
        self.assertEqual((s["status"], code), ("crashed", 1))
        self.assertTrue((self.root / "out/pipeline" / s["run"] / "summary.json").exists())

    def test_a_failed_run_never_replaces_the_last_published_run(self):
        ok, _ = go(self.root, fake_steps(("qa", QA_OK)), now=Clock())
        bad, _ = go(self.root, fake_steps(("a", "import sys; sys.exit(1)"), ("qa", QA_OK)), now=lambda: FIXED + timedelta(hours=2))
        self.assertEqual(json.loads((self.root / "out/pipeline/latest.json").read_text())["run"], ok["run"])
        self.assertNotEqual(ok["run"], bad["run"])

    def test_no_temporary_file_is_left_behind(self):
        s, _ = go(self.root, fake_steps(("qa", QA_OK)))
        self.assertEqual(list(self.root.rglob("*.tmp")), [])


class TestFreshness(unittest.TestCase):
    def test_unit(self):
        data = {"front": {"age_hours": 5.0}, "rear": {"age_hours": 2.0}}
        self.assertEqual(dp.freshness(data, None)["status"], "not enforced")
        self.assertEqual(dp.freshness(data, 6)["status"], "ok")
        late = dp.freshness(data, 4)
        self.assertEqual(late["status"], "FAILED")
        self.assertIn("front", late["message"])

    def test_an_exceeded_limit_fails_the_run_and_a_missing_limit_does_not(self):
        with tempfile.TemporaryDirectory() as d:
            old = {"availability_pct": GOOD["availability_pct"], "data": {"front": {"last_reading": "x", "age_hours": 648.0}, "rear": {"last_reading": "x", "age_hours": 648.0}}}
            s, code = go(d, fake_steps(("qa", QA_OK)), measure=lambda o, n: old)
            self.assertEqual((s["status"], code, s["freshness"]["status"]), ("ok", 0, "not enforced"))
            s, code = go(d, fake_steps(("qa", QA_OK)), opts={"max_data_age_hours": 24}, measure=lambda o, n: old, now=lambda: FIXED + timedelta(days=1))
            self.assertEqual((s["status"], code, s["steps"]["freshness"]), ("failed", 1, "FAILED(1)"))


class TestLockRunIdsAndRetention(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "out/pipeline").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_live_lock_stops_the_run_without_creating_a_run_folder(self):
        holder = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            (self.root / "out/pipeline/.lock").write_text(str(holder.pid))
            s, code = go(self.root, fake_steps(("qa", QA_OK)))
            self.assertEqual((s["status"], code), ("locked", 2))
            self.assertEqual([d for d in (self.root / "out/pipeline").iterdir() if d.is_dir()], [])
            self.assertTrue((self.root / "out/pipeline/.lock").exists(), "the other run's lock is not ours to remove")
        finally:
            holder.kill()
            holder.wait()

    def test_a_stale_lock_is_taken_over_and_the_lock_is_always_released(self):
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        (self.root / "out/pipeline/.lock").write_text(str(dead.pid))
        s, code = go(self.root, fake_steps(("qa", QA_OK)))
        self.assertEqual(code, 0)
        self.assertFalse((self.root / "out/pipeline/.lock").exists())
        def boom(o, n):
            raise ValueError("x")
        go(self.root, fake_steps(("qa", QA_OK)), measure=boom, now=lambda: FIXED + timedelta(hours=1))
        self.assertFalse((self.root / "out/pipeline/.lock").exists(), "released after a crash too")

    def test_two_runs_in_the_same_second_get_different_folders(self):
        a, _ = go(self.root, fake_steps(("qa", QA_OK)), now=lambda: FIXED)
        b, _ = go(self.root, fake_steps(("qa", QA_OK)), now=lambda: FIXED)
        self.assertNotEqual(a["run"], b["run"])
        self.assertTrue(re.fullmatch(r"\d{8}_\d{6}_2", b["run"]))
        self.assertTrue(dp.RUN_ID.match(b["run"]))

    def test_retention_keeps_the_newest_runs_and_touches_nothing_else(self):
        base = self.root / "out/pipeline"
        for i in range(1, 6):
            (base / f"2026010{i}_000000").mkdir()
        (base / "keepme").mkdir()
        s, _ = go(self.root, fake_steps(("qa", QA_OK)), opts={"keep": 3})
        runs = sorted(d.name for d in base.iterdir() if d.is_dir() and dp.RUN_ID.match(d.name))
        self.assertEqual(len(runs), 3)
        self.assertIn(s["run"], runs)
        self.assertTrue((base / "keepme").exists())
        self.assertEqual(len(s["removed_runs"]), 3)

    def test_a_failed_run_removes_nothing(self):
        base = self.root / "out/pipeline"
        for i in range(1, 4):
            (base / f"2026010{i}_000000").mkdir()
        go(self.root, fake_steps(("a", "import sys; sys.exit(1)")), opts={"keep": 1})
        self.assertEqual(len([d for d in base.iterdir() if d.is_dir() and dp.RUN_ID.match(d.name)]), 4)


class TestNotificationAndOptions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.rec = self.root / "calls.txt"
        hook = self.root / "hook.py"
        hook.write_text(f"import json, sys\nopen({str(self.rec)!r}, 'a').write(json.dumps(sys.argv[1:2]) + '\\n')\n")
        self.cmd = f"{sys.executable} -I {hook}"

    def tearDown(self):
        self.tmp.cleanup()

    def calls(self):
        return [json.loads(l) for l in self.rec.read_text().splitlines()] if self.rec.exists() else []

    def test_hook_is_called_for_a_failed_run_and_for_firing_alerts_only(self):
        go(self.root, fake_steps(("qa", QA_OK)), notify_cmd=self.cmd)
        self.assertEqual(self.calls(), [])
        s, _ = go(self.root, fake_steps(("a", "import sys; sys.exit(1)"), ("qa", QA_OK)), notify_cmd=self.cmd, now=lambda: FIXED + timedelta(hours=1))
        self.assertEqual(self.calls(), [["failed"]])
        self.assertEqual(s["notified"], [{"kind": "failed", "result": "sent"}])
        alert = "import json, pathlib; pathlib.Path(RUNDIR, 'alerts.json').write_text(json.dumps({'alerts': [{'id': 'DQ_STALE', 'scope': 'front', 'firing': True}, {'id': 'CAP_LOW', 'scope': 'front', 'firing': False}]}))"
        s, _ = go(self.root, fake_steps(("alerts", alert), ("qa", QA_OK)), notify_cmd=self.cmd, now=lambda: FIXED + timedelta(hours=2))
        self.assertEqual(s["alerts_firing"], ["DQ_STALE:front"])
        self.assertEqual(self.calls()[-1], ["alerts"])
        self.assertEqual(json.loads((self.root / "out/pipeline" / s["run"] / "summary.json").read_text())["notified"][0]["result"], "sent")

    def test_no_hook_configured_or_a_broken_hook_does_not_change_the_result(self):
        s, code = go(self.root, fake_steps(("a", "import sys; sys.exit(1)")), notify_cmd=None)
        self.assertEqual((code, s["notified"][0]["result"]), (1, "no notification command configured"))
        s, code = go(self.root, fake_steps(("a", "import sys; sys.exit(1)")), notify_cmd="/no/such/hook", now=lambda: FIXED + timedelta(hours=1))
        self.assertEqual(code, 1)
        self.assertIn("hook failed", s["notified"][0]["result"])

    def test_options_reach_only_the_scripts_that_accept_them(self):
        opts = {**OPTS, "data_dir": "/data", "start": "2026-09-15", "near_full_min": 0}
        cmds = dict(dp.steps(opts, Path("/run")))
        self.assertIn("--data-dir", cmds["availability"])
        self.assertIn("2026-09-15", cmds["dashboard_db"])
        self.assertNotIn("--near-full-min", cmds["dashboard_db"])
        for name in ("store", "alerts"):
            self.assertNotIn("--data-dir", cmds[name])
        self.assertEqual(cmds["availability"][cmds["availability"].index("--near-full-min") + 1], "0")
        self.assertIn("--with-doc-check", dp.steps(OPTS, Path("/run"))[-1][1])
        self.assertIn("--data-only", dp.steps({**OPTS, "gate": "data"}, Path("/run"))[-1][1])
        plain = dict(dp.steps(OPTS, Path("/run")))
        self.assertNotIn("--data-dir", plain["availability"])


class TestAgainstTheRepository(unittest.TestCase):
    def test_every_step_script_exists_and_accepts_exactly_the_options_the_table_says(self):
        for name, script, _, accepts in dp.SCRIPTS:
            path = HERE / script[2:] if script.startswith("./") else ROOT / script
            self.assertTrue(path.is_file(), f"{name}: {path}")
            src = path.read_text(encoding="utf-8")
            actual = tuple(o for o in dp.COMMON if f'"--{o}"' in src)
            self.assertEqual(tuple(o for o in dp.COMMON if o in accepts), actual, f"{name}: the SCRIPTS table disagrees with {path.name}")

    def test_the_runbook_names_every_step_and_exit_code(self):
        text = (BASE / "assets" / "pipeline_runbook_sep_oct_2026.md").read_text(encoding="utf-8")
        for name, *_ in dp.SCRIPTS:
            self.assertIn(name, text, f"runbook does not mention step {name}")
        for code in ("0 ok", "1 failed or crashed", "2 another run is active"):
            self.assertIn(code, text)
        self.assertIn(dp.NOTIFY_ENV, (BASE / "assets" / "airflow_dag_example.py").read_text(encoding="utf-8"))

    def test_the_dag_example_has_the_safeguards(self):
        src = (BASE / "assets" / "airflow_dag_example.py").read_text(encoding="utf-8")
        ast.parse(src)
        for needle in ("max_active_runs=1", "dagrun_timeout", "on_failure_callback", "daily_pipeline.py"):
            self.assertIn(needle, src)
        self.assertNotIn("hooks.slack.com", src)


def alert_db(front_days=20, last_front=80.0, fail_last=False):
    con = sqlite3.connect(":memory:")
    con.executescript(ex.bdb.to_sqlite(ex.bdb.SCHEMA_SQL.read_text(encoding="utf-8")))
    for side in ("front", "rear"):
        for i in range(front_days):
            v = last_front if (i == front_days - 1 and side == "front") else 95.0 + (0.4 if i % 2 else 0.0)
            fail = 12.0 if (side == "front" and (i == front_days - 1 if fail_last else i == 3)) else 1.0
            con.execute("INSERT INTO equipment_daily_metrics VALUES (?,?,?,?,?,?,?,?,?)", (f"2026-09-{i + 1:02d}", "h", side, v, v - 0.5, 300, 360, fail, 100.0))
        con.execute("INSERT INTO contactor_samples VALUES (?,?,?,?,?,?,?,?)", ("2026-10-02 15:14:00", "h", side, 0, "[]", "NA_ZERO", 1, 4.0))
    return con


class TestAlertEvaluation(unittest.TestCase):
    SPEC = ea.dsc.DEFAULT_SPEC.read_text(encoding="utf-8")
    NOW = datetime(2026, 10, 2, 15, 30)

    def ev(self, con, now=None):
        return {(a["id"], a["scope"]): a for a in ea.evaluate(con, self.SPEC, now or self.NOW)}

    def test_cap_low_fires_when_the_last_day_drops_below_median_minus_two_sd(self):
        self.assertTrue(self.ev(alert_db(last_front=80.0))[("CAP_LOW", "front")]["firing"])
        self.assertFalse(self.ev(alert_db(last_front=95.2))[("CAP_LOW", "front")]["firing"])
        self.assertFalse(self.ev(alert_db(last_front=80.0))[("CAP_LOW", "rear")]["firing"], "the rear side is unaffected")

    def test_cap_low_needs_enough_history(self):
        a = self.ev(alert_db(front_days=10))[("CAP_LOW", "front")]
        self.assertFalse(a["firing"])
        self.assertIn("at least 15", a["detail"]["note"])

    def test_a_daily_alert_fires_only_when_the_newest_day_is_bad(self):
        old = self.ev(alert_db(fail_last=False))[("DQ_FAIL_DAY", "all")]
        self.assertFalse(old["firing"])
        self.assertEqual(old["earlier_days"], 1)
        new = self.ev(alert_db(fail_last=True))[("DQ_FAIL_DAY", "all")]
        self.assertTrue(new["firing"])
        self.assertEqual(new["detail"][0]["day"], "2026-09-20")

    def test_stale_data_fires_after_thirty_minutes_not_before(self):
        self.assertFalse(self.ev(alert_db(), datetime(2026, 10, 2, 15, 43))[("DQ_STALE", "front")]["firing"])
        self.assertTrue(self.ev(alert_db(), datetime(2026, 10, 2, 15, 45))[("DQ_STALE", "front")]["firing"])
        self.assertTrue(self.ev(alert_db(), datetime(2026, 10, 29))[("DQ_STALE", "rear")]["firing"])

    def test_a_long_aligned_group_fires_the_spec_query(self):
        con = alert_db()
        self.assertFalse(self.ev(con)[("GROUP_LONG", "all")]["firing"])
        con.execute("INSERT INTO closure_events VALUES (1,'h','front','2026-09-28 00:00:00','2026-10-02 15:00:00',5000,4,'[1,2,17,18]',1.0,1,1,0)")
        self.assertTrue(self.ev(con)[("GROUP_LONG", "all")]["firing"])
        con.execute("UPDATE closure_events SET ongoing = 0")
        self.assertFalse(self.ev(con)[("GROUP_LONG", "all")]["firing"], "a group that is no longer closed is not an alert")


class TestPostgresExport(unittest.TestCase):
    def test_arrays_nulls_and_headers(self):
        self.assertEqual(ex.pg_array("[1, 2, 30]"), "{1,2,30}")
        self.assertEqual(ex.pg_array("[]"), "{}")
        self.assertIsNone(ex.pg_array(None))

    def test_export_round_trips_every_table_and_writes_one_copy_per_table(self):
        con = alert_db()
        con.execute("INSERT INTO contactor_samples VALUES (?,?,?,?,?,?,?,?)", ("2026-10-02 15:18:00", "h", "front", 3, "[3, 4, 19]", "OK", 1, 4.0))
        con.execute("INSERT INTO equipment_daily_metrics VALUES ('2026-10-03','h','front',NULL,NULL,1,1,0,1)")
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "x.sqlite"
            con.commit()  # backup() retries forever while a write transaction is open
            disk = sqlite3.connect(db)
            con.backup(disk)
            disk.close()
            counts = ex.export(db, Path(d) / "pg")
            tables = ex.bdb.parse_schema(ex.bdb.SCHEMA_SQL.read_text(encoding="utf-8"))
            self.assertEqual(set(counts), set(tables))
            load = (Path(d) / "pg/load.sql").read_text()
            for t in tables:
                self.assertEqual(load.count(f"\\copy {t} ("), 1)
                lines = (Path(d) / f"pg/{t}.csv").read_text().splitlines()
                self.assertEqual(len(lines) - 1, counts[t], t)
            sample = (Path(d) / "pg/contactor_samples.csv").read_text()
            self.assertIn('"{3,4,19}"', sample)
            metrics = (Path(d) / "pg/equipment_daily_metrics.csv").read_text()
            self.assertRegex(metrics, r"2026-10-03,h,front,,,1,1,0(\.0)?,1(\.0)?")
            self.assertTrue(load.startswith("-- Initial load into an EMPTY schema"))
            self.assertIn("BEGIN;", load)


if __name__ == "__main__":
    unittest.main(verbosity=1)
