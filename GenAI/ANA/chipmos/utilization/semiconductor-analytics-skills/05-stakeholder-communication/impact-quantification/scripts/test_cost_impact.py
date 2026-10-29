"""
Unit tests for cost_impact.py and the deferral guard. All business numbers here are SYMBOLIC test values
chosen so the arithmetic is easy to check by hand - they are not estimates and not data. The data half uses a
small synthetic dataset (sites 100/101 closed only on days 1-2).

Usage:
    python test_cost_impact.py
"""

import atexit
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "lib"))
import cost_impact as ci  # noqa: E402
import deferral  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="impact_"))
atexit.register(shutil.rmtree, TMP, ignore_errors=True)
BASE = dict(uph_per_site=10, hours_per_day=10, margin_per_unit=2, days=2, repair_cost=100, capacity_constrained=True,
            p_hold=0.5, repair_downtime_days=1, sites_offline_during_repair=4)


def make_dataset(root: Path):
    root.mkdir(parents=True)
    for d in range(1, 7):
        ids = [5, 6, 21, 22] + ([100, 101] if d <= 2 else [])
        t0 = datetime(2026, 9, d, 0, 2)
        rows = [f"{(t0 + timedelta(minutes=4 * i)):%Y/%m/%d %H:%M},{len(ids)},{';'.join(map(str, ids))}" for i in range(360)]
        (root / f"contactor_202609{d:02d}.csv").write_text("﻿Timestamp,err_01,err_02\n" + "\n".join(rows) + "\n", encoding="utf-8")
        rear = [f"{(t0 + timedelta(minutes=4 * i)):%Y/%m/%d %H:%M},1,300" for i in range(360)]
        (root / f"contactor_rear_202609{d:02d}.csv").write_text("﻿Timestamp,err_01,err_02\n" + "\n".join(rear) + "\n", encoding="utf-8")


make_dataset(TMP / "data")


class TestCostImpact(unittest.TestCase):
    def test_value_arithmetic_by_hand(self):
        r = ci.value(3.0, BASE)
        self.assertAlmostEqual(r["gain_units_per_hour"], 30.0)
        self.assertAlmostEqual(r["gross_value"], 30 * 10 * 2 * 2 * 0.5)      # 600
        self.assertAlmostEqual(r["downtime_loss"], 1 * 10 * 4 * 10 * 2)      # 800
        self.assertAlmostEqual(r["net_value"], 600 - 800 - 100)

    def test_not_capacity_constrained_means_no_gain_and_only_the_repair_cost(self):
        r = ci.value(3.0, {**BASE, "capacity_constrained": False})
        self.assertEqual((r["gross_value"], r["downtime_loss"], r["net_value"]), (0.0, 0.0, -100))

    def test_no_business_parameter_has_a_default(self):
        for k in ci.REQUIRED:
            p = {**BASE, k: None}
            self.assertIn(f"{k} is required (no default)", ci.validate(p))
        with self.assertRaises(ValueError):
            ci.value(1.0, {**BASE, "repair_cost": None})

    def test_zero_is_an_explicit_value_not_missing(self):
        self.assertEqual(ci.validate({**BASE, "repair_cost": 0, "repair_downtime_days": 0, "sites_offline_during_repair": 0}), [])

    def test_invalid_values_are_rejected(self):
        for k, v in (("p_hold", 1.2), ("p_hold", -0.1), ("hours_per_day", 25), ("hours_per_day", 0), ("days", 0), ("uph_per_site", -1),
                     ("margin_per_unit", -1), ("sites_offline_during_repair", 300), ("capacity_constrained", "yes")):
            self.assertTrue(ci.validate({**BASE, k: v}), (k, v))

    def test_data_half_uses_what_is_closed_now_not_the_period_average(self):
        se = ci.site_equivalents("front", [5, 6, 100, 101], data_dir=TMP / "data")
        self.assertAlmostEqual(se["period"], 2 + 2 * (2 / 6), places=2)   # 2 always closed + 2 sites x 2 of 6 days
        self.assertAlmostEqual(se[3], 2.0, places=2)                      # sites 100/101 reopened before the last 3 days
        self.assertAlmostEqual(se[7], se["period"], places=2)             # a 7-day window covers the whole 6-day dataset
        self.assertLess(se[3], se["period"])

    def test_scenarios_come_from_the_windows_and_never_from_the_period_average(self):
        se = {"period": 99.0, 3: 2.0, 7: 3.0, 14: 3.0}
        r = ci.scenarios(se, BASE)
        self.assertEqual([r[k]["site_equivalents"] for k in ("low", "mid", "high")], [2.0, 3.0, 3.0])
        self.assertTrue(all(r[k]["site_equivalents"] != 99.0 for k in r))

    def test_bare_run_prints_only_the_deferral_notice(self):
        out = subprocess.run([sys.executable, "-I", str(HERE.parent / "cost_impact.py")], capture_output=True, text=True).stdout
        self.assertIn("DEFERRED", out)
        self.assertNotIn("NET", out)
        self.assertFalse(deferral.business_figures(out))

    def test_demo_is_labelled_illustrative(self):
        out = subprocess.run([sys.executable, "-I", str(HERE.parent / "cost_impact.py"), "--demo"], capture_output=True, text=True).stdout
        self.assertIn("ILLUSTRATIVE", out)
        self.assertIn("NOT real", out)


class TestDeferral(unittest.TestCase):
    def test_money_and_throughput_figures_are_found(self):
        for text in ("saves $5,000 a month", "worth NT$ 3000", "about 5000 USD", "we gain 20 units per hour", "UPH 25",
                     "a margin of 0.05 per part", "payback 3 months", "revenue of 1.2 million"):
            self.assertTrue(deferral.business_figures(text), text)

    def test_ordinary_capacity_language_is_not_flagged(self):
        for text in ("Together they cost about 7 percentage points of front capacity", "OEE needs run and idle time, output, good-unit and cycle-time data",
                     "91.32% of positions able to test", "inspect the three front groups first", "20 of 256 front sites (7.8%) closed now"):
            self.assertEqual(deferral.business_figures(text), [], text)

    def test_html_comments_and_scripts_are_ignored(self):
        self.assertEqual(deferral.business_figures("<!-- $5 --><script>var a='$5'</script>ok"), [])

    def test_deferral_can_be_lifted_only_by_the_status_file(self):
        off, on = TMP / "off.json", TMP / "on.json"
        off.write_text(json.dumps({"deferred": False})); on.write_text(json.dumps({"deferred": True}))
        self.assertEqual(deferral.check("saves $5,000", off), [])
        self.assertTrue(deferral.check("saves $5,000", on))
        self.assertTrue(deferral.is_deferred(TMP / "missing.json"))  # unreadable status = stay deferred

    def test_real_status_is_deferred_and_the_real_deliverables_are_clean(self):
        self.assertTrue(deferral.is_deferred())
        for rel in ("04-data-storytelling-visualization/executive-summary-generator/assets/executive_summary_sep_oct_2026.md",
                    "04-data-storytelling-visualization/insight-synthesis/assets/insight_brief_sep_oct_2026.md",
                    "04-data-storytelling-visualization/dashboard-specification/assets/dashboard_spec_sep_oct_2026.md",
                    "02-documentation-knowledge/analysis-documentation/assets/handler_utilization_analysis_sep_oct_2026.md",
                    "05-stakeholder-communication/analysis-qa-checklist/assets/qa_signoff_sep_oct_2026.md"):
            self.assertEqual(deferral.check((ROOT / rel).read_text(encoding="utf-8")), [], rel)


if __name__ == "__main__":
    unittest.main(verbosity=1)
