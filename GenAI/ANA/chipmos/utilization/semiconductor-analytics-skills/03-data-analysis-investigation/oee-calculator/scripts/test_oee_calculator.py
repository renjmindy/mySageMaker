"""
Unit tests for oee_calculator.py (stdlib unittest). The numbers 400/480 min, 380 output and 370 good are
the illustrative values from the guide's simulator screenshot; they are NOT handler data.

Usage:
    python test_oee_calculator.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oee_calculator as o  # noqa: E402

IDEAL = 400 * 0.95 / 380  # = 1.0 min/unit, back-solved so that P = 95.0% (the screenshot shows no cycle time)
FULL = dict(run_min=400, planned_min=480, output=380, good=370, ideal_cycle_min=IDEAL)


class TestOEE(unittest.TestCase):
    def test_doc_example(self):
        r = o.oee(**FULL)
        self.assertEqual(r["status"], "OK")
        self.assertAlmostEqual(r["availability"], 400 / 480)
        self.assertAlmostEqual(r["performance"], 0.95)
        self.assertAlmostEqual(r["quality"], 370 / 380)
        self.assertAlmostEqual(r["oee"], 0.771, places=3)

    def test_blocked_states_report_no_number(self):
        for kw, missing in (({}, 3), ({"site_availability": 0.9}, 3),
                            ({"run_min": 400, "planned_min": 480}, 2),
                            ({"run_min": 400, "planned_min": 480, "output": 380, "ideal_cycle_min": 1.0}, 1)):
            r = o.oee(**kw)
            self.assertEqual(r["status"], "BLOCKED", kw)
            self.assertIsNone(r["oee"], kw)
            self.assertEqual(len(r["missing"]), missing, kw)

    def test_invalid_inputs_are_rejected(self):
        cases = {
            "planned_min = 0": {**FULL, "planned_min": 0},
            "output with run_min = 0": {**FULL, "run_min": 0},
            "good > output": {**FULL, "output": 300},
            "run > planned": {**FULL, "run_min": 500},
            "performance > 100%": {**FULL, "ideal_cycle_min": 1.5},
            "negative run_min": {**FULL, "run_min": -5},
            "negative good": {**FULL, "good": -1},
            "site_availability > 1": {**FULL, "site_availability": 1.2},
            "ideal cycle = 0": {**FULL, "ideal_cycle_min": 0},
        }
        for name, kw in cases.items():
            r = o.oee(**kw)
            self.assertEqual(r["status"], "INVALID", name)
            self.assertIsNone(r["oee"], name)
            self.assertTrue(r["errors"], name)

    def test_invalid_partial_inputs_are_caught_too(self):
        self.assertEqual(o.oee(run_min=500, planned_min=480)["status"], "INVALID")
        self.assertEqual(o.oee(output=300, good=370)["status"], "INVALID")

    def test_zero_is_a_value_not_missing(self):
        r = o.oee(run_min=400, planned_min=480, output=0, good=0, ideal_cycle_min=1.0)  # ran but produced nothing
        self.assertEqual((r["status"], r["oee"], r["performance"]), ("OK", 0.0, 0.0))
        r = o.oee(run_min=0, planned_min=480, output=0, good=0, ideal_cycle_min=1.0)  # did not run
        self.assertEqual((r["status"], r["oee"], r["availability"]), ("OK", 0.0, 0.0))

    def test_identity_oee_equals_good_times_ideal_over_planned(self):
        for run, planned, out, good, ideal in ((400, 480, 380, 370, IDEAL), (300, 600, 150, 140, 1.5), (10, 10, 5, 5, 2.0)):
            r = o.oee(run, planned, out, good, ideal)
            self.assertAlmostEqual(r["oee"], good * ideal / planned, places=9)

    def test_site_availability_decomposes_but_never_changes_oee(self):
        base = o.oee(**FULL)
        r = o.oee(**FULL, site_availability=0.95)
        self.assertAlmostEqual(r["oee"], base["oee"])
        c = r["capacity_split"]
        self.assertAlmostEqual(c["site_capacity"] * c["speed_and_other"], r["performance"])

    def test_show_exit_codes(self):
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(o.show(o.oee(**FULL)), 0)
            self.assertEqual(o.show(o.oee()), 0)  # BLOCKED is the expected current state
            self.assertEqual(o.show(o.oee(**{**FULL, "good": 999})), 2)


if __name__ == "__main__":
    unittest.main(verbosity=1)
