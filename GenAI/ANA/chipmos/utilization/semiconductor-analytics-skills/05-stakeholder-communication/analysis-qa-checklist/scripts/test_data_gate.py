"""
Fault-injection tests for the data gate, on small SYNTHETIC datasets (6 days, both sides, ~4-minute cadence,
~3% failed readings) so they run anywhere - the real CSVs are private. Each test injects one fault into a copy
of a clean dataset and asserts that the matching check reacts.

Usage:
    python test_data_gate.py
"""

import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import contactor_io as cio  # noqa: E402
import data_gate as dg  # noqa: E402

DAYS = [date(2026, 9, d) for d in range(1, 7)]
FRONT_IDS = [5, 6, 21, 22, 37, 38]
REAR_IDS = [300, 301, 316, 317]
TMP = Path(tempfile.mkdtemp(prefix="qa_gate_"))
CLEAN = TMP / "clean"


def day_rows(day, ids, fail_every=33, shift_h=0):
    t0 = datetime(day.year, day.month, day.day, 0, 2) + timedelta(hours=shift_h)
    rows = []
    for i in range(360):
        ts = (t0 + timedelta(minutes=4 * i)).strftime("%Y/%m/%d %H:%M")
        rows.append(f"{ts},256,1;1;1" if i % fail_every == 0 else f"{ts},{len(ids)},{';'.join(map(str, ids))}")
    return rows


def write(path, rows, header="Timestamp,err_01,err_02"):
    path.write_text("﻿" + header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def make_dataset(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    for d in DAYS:
        write(root / f"contactor_{d:%Y%m%d}.csv", day_rows(d, FRONT_IDS))
        write(root / f"contactor_rear_{d:%Y%m%d}.csv", day_rows(d, REAR_IDS))


make_dataset(CLEAN)
BASELINE = dg.make_baseline(CLEAN, today="2026-10-29")


def copy() -> Path:
    dst = TMP / f"case_{len(list(TMP.iterdir()))}"
    shutil.copytree(CLEAN, dst)
    return dst


def gate(path, report="", baseline=BASELINE, **kw):
    return {n: (s, d) for n, s, d in dg.data_checks(path, baseline=baseline, validation_report=report, **kw)}


def status(res, name):
    return res[name][0]


class TestDataGate(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TMP, ignore_errors=True)

    def test_clean_dataset_has_no_warn_or_fail(self):
        res = gate(CLEAN)
        self.assertEqual([(n, s) for n, (s, _) in res.items() if s in ("WARN", "FAIL")], [])

    def test_missing_day_is_caught(self):
        p = copy(); (p / "contactor_20260903.csv").unlink()
        res = gate(p)
        self.assertEqual(status(res, "front: no missing days"), "FAIL")
        self.assertEqual(status(res, "front: data has not gone backwards since the last release"), "FAIL")  # fewer rows

    def test_a_whole_day_of_failed_reads_must_have_a_recorded_decision(self):
        p = copy(); write(p / "contactor_20260904.csv", [r.rsplit(",", 2)[0] + ",256,1;1;1" for r in day_rows(date(2026, 9, 4), FRONT_IDS)])
        self.assertEqual(status(gate(p), "front: flagged days have a recorded decision"), "FAIL")
        recorded = "| 2026-09-04 | front | whole day failed | CRITICAL | n/a | keep with caveat |"
        self.assertEqual(status(gate(p, report=recorded), "front: flagged days have a recorded decision"), "PASS")
        # one failed day of six lifts the overall dropped rate to ~17% (>= 15% = FAIL); on 32 days it adds only ~3 pts
        self.assertEqual(status(gate(p, report=recorded), "front: dropped-reading rate"), "FAIL")

    def test_low_coverage_day_must_be_recorded_but_the_last_day_may_be_partial(self):
        p = copy(); write(p / "contactor_20260902.csv", day_rows(date(2026, 9, 2), FRONT_IDS)[:200])
        self.assertEqual(status(gate(p), "front: flagged days have a recorded decision"), "FAIL")
        q = copy(); write(q / "contactor_20260906.csv", day_rows(date(2026, 9, 6), FRONT_IDS)[:100])  # last day, partial
        self.assertEqual(status(gate(q, baseline=None), "front: flagged days have a recorded decision"), "PASS")

    def test_duplicate_rows_are_caught(self):
        p = copy(); f = p / "contactor_20260905.csv"
        rows = f.read_text(encoding="utf-8-sig").splitlines()
        write(f, rows[1:] + rows[1:100])
        self.assertEqual(status(gate(p), "front: no duplicate timestamps"), "FAIL")

    def test_renamed_header_fails_loudly(self):
        p = copy(); write(p / "contactor_20260903.csv", day_rows(date(2026, 9, 3), FRONT_IDS), header="Timestamp,errors_1,err_02")
        res = gate(p)
        self.assertEqual(status(res, "data format"), "FAIL")
        self.assertIn("missing column", res["data format"][1])
        with self.assertRaises(cio.DataFormatError):
            cio.load_side("front", p)

    def test_non_numeric_count_fails_loudly(self):
        p = copy(); rows = day_rows(date(2026, 9, 3), FRONT_IDS); rows[5] = rows[5].replace(",6,", ",six,", 1)
        write(p / "contactor_20260903.csv", rows)
        self.assertEqual(status(gate(p), "data format"), "FAIL")

    def test_swapped_front_and_rear_files_are_caught(self):
        p = copy(); shutil.copy(p / "contactor_rear_20260902.csv", p / "contactor_20260902.csv")
        self.assertEqual(status(gate(p), "front: site IDs belong to this side"), "FAIL")

    def test_stray_numbers_in_many_readings_are_a_warning_not_a_swapped_file(self):
        """October-type noise: 2 of 5 readings carry one stray number among 7 listed (about 6% of the listed numbers)."""
        p = copy(); ids = ";".join(map(str, FRONT_IDS))
        rows = [f"{r.split(',')[0]},7,{ids};999" if i % 5 in (1, 2) and not r.split(",")[1] == "256" else r
                for i, r in enumerate(day_rows(date(2026, 9, 4), FRONT_IDS))]
        write(p / "contactor_20260904.csv", rows)
        res = gate(p)
        self.assertEqual(status(res, "front: site IDs belong to this side"), "WARN")
        self.assertIn("of readings carry an out-of-range ID", res["front: site IDs belong to this side"][1])

    def test_a_day_where_a_third_of_the_listed_numbers_are_out_of_range_fails(self):
        p = copy(); ids = ";".join(map(str, FRONT_IDS))
        rows = [r if r.split(",")[1] == "256" else f"{r.split(',')[0]},9,{ids};991;992;993" for r in day_rows(date(2026, 9, 4), FRONT_IDS)]
        write(p / "contactor_20260904.csv", rows)
        self.assertEqual(status(gate(p), "front: site IDs belong to this side"), "FAIL")

    def test_a_constant_gap_between_the_count_and_the_list_is_flagged(self):
        """The October pattern: the count is 40 above the listed IDs on every reading of a day (kept: below the gap-rule limit of 50)."""
        p = copy(); ids = ";".join(map(str, FRONT_IDS))
        rows = [r if r.split(",")[1] == "256" else f"{r.split(',')[0]},{len(FRONT_IDS) + 40},{ids}" for r in day_rows(date(2026, 9, 4), FRONT_IDS)]
        write(p / "contactor_20260904.csv", rows)
        res = gate(p)
        self.assertEqual(status(res, "front: count and list agree"), "WARN")
        self.assertIn("A21", res["front: count and list agree"][1])
        self.assertEqual(status(res, "rear: count and list agree"), "PASS", "the other side is unaffected")

    def test_the_lower_bound_can_move_while_the_headline_does_not(self):
        """A count 40 above the list on one day of six moves the lower bound by about 2.6 pts and the list-based headline not at all."""
        p = copy(); ids = ";".join(map(str, FRONT_IDS))
        rows = [r if r.split(",")[1] == "256" else f"{r.split(',')[0]},{len(FRONT_IDS) + 40},{ids}" for r in day_rows(date(2026, 9, 4), FRONT_IDS)]
        write(p / "contactor_20260904.csv", rows)
        res = gate(p)
        self.assertEqual(status(res, "front: headline vs the last release"), "PASS")
        self.assertEqual(status(res, "front: lower bound vs the last release"), "WARN")
        self.assertEqual(status(gate(CLEAN), "front: lower bound vs the last release"), "PASS")

    def test_a_small_gap_is_not_flagged(self):
        p = copy(); ids = ";".join(map(str, FRONT_IDS))
        rows = [r if r.split(",")[1] == "256" else f"{r.split(',')[0]},{len(FRONT_IDS) + 5},{ids}" for r in day_rows(date(2026, 9, 4), FRONT_IDS)]
        write(p / "contactor_20260904.csv", rows)
        self.assertEqual(status(gate(p), "front: count and list agree"), "PASS")

    def test_unflagged_near_full_readings_are_caught(self):
        p = copy(); ids = ";".join(str(i) for i in range(1, 246))
        rows = day_rows(date(2026, 9, 5), FRONT_IDS)
        rows = [f"{r.split(',')[0]},245,{ids}" if i % 3 == 1 else r for i, r in enumerate(rows)]
        write(p / "contactor_20260905.csv", rows)
        self.assertIn(status(gate(p), "front: unflagged near-full band (A14 type)"), ("WARN", "FAIL"))

    def test_shifted_timestamps_are_caught(self):
        p = copy(); write(p / "contactor_20260904.csv", day_rows(date(2026, 9, 4), FRONT_IDS, shift_h=8))
        self.assertEqual(status(gate(p), "front: reading days match their file days"), "FAIL")

    def test_stale_data_is_caught(self):
        p = copy()
        for f in (p / "contactor_20260906.csv", p / "contactor_rear_20260906.csv"):
            f.unlink()
        res = gate(p)
        self.assertEqual(status(res, "front: data has not gone backwards since the last release"), "FAIL")
        self.assertEqual(status(res, "rear: data has not gone backwards since the last release"), "FAIL")

    def test_wrong_analysis_start_is_caught(self):
        self.assertEqual(status(gate(CLEAN, start="2026-08-01"), "analysis start equals the documented scope (A6)"), "FAIL")

    def test_headline_jump_needs_an_explanation(self):
        p = copy(); more = FRONT_IDS + list(range(41, 81))
        for d in (date(2026, 9, 4), date(2026, 9, 5), date(2026, 9, 6)):
            write(p / f"contactor_{d:%Y%m%d}.csv", day_rows(d, more))
        self.assertEqual(status(gate(p), "front: headline vs the last release"), "WARN")

    def test_missing_baseline_warns(self):
        self.assertEqual(status(gate(CLEAN, baseline=None), "front: data has not gone backwards since the last release"), "WARN")

    def test_waivers_waive_unexpired_warnings_only(self):
        res = [("rear: site IDs belong to this side", "WARN", "worst day 17%"), ("other", "WARN", "x"), ("front: no missing days", "FAIL", "y")]
        w = [{"check": "site IDs belong", "reason": "stray token", "owner": "analyst", "expires": "2026-12-31"}]
        out = {n: (s, d) for n, s, d in dg.apply_waivers(res, w, today="2026-10-29")}
        self.assertEqual(out["rear: site IDs belong to this side"][0], "WAIVED")
        self.assertIn("stray token", out["rear: site IDs belong to this side"][1])
        self.assertEqual(out["other"][0], "WARN")           # no waiver -> stands out
        self.assertEqual(out["front: no missing days"][0], "FAIL")  # a FAIL is never waived
        expired = {n: (s, d) for n, s, d in dg.apply_waivers(res, w, today="2027-01-02")}
        self.assertEqual(expired["rear: site IDs belong to this side"][0], "WARN")
        self.assertIn("expired", expired["rear: site IDs belong to this side"][1])

    def test_headline_reconciliation(self):
        truth = {"front": 91.32, "rear": 96.07}
        good = {"analysis document": "| front | **91.32%** | 90.88% |\n| rear | **96.07%** |", "executive summary": "91% of front test positions and 96% of rear positions"}
        self.assertEqual(dg.reconcile(truth, good), [])
        bad = {"executive summary": "93% of front test positions and 96% of rear positions", "insight brief": "no numbers here"}
        out = dg.reconcile(truth, bad)
        self.assertTrue(any("front: writes 93%" in x for x in out) and any("insight brief: no front headline" in x for x in out))


if __name__ == "__main__":
    unittest.main(verbosity=1)
