"""
Unit tests for exec_summary_check.py (stdlib unittest, synthetic documents).

Usage:
    python test_exec_summary_check.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exec_summary_check as esc  # noqa: E402

ANALYSIS = """Front 91.32% (low 90.88%), rear 96.07%. Interval 90.57-92.08%. Daily standard deviation about 2.2 pts.
Three clusters: 3.03 pts, 2.91 pts and 1.11 pts in the last 7 days. 30% of the time. 3.06% failed readings."""

GOOD = """# Summary

**Bottom line**: 91% of front positions and 96% of rear positions could test; we recommend inspecting three front groups first.

## Why
1. Three groups cost about 7 points of front capacity in the last 7 days.
2. Swings of about 2 points are normal.

## Confidence and limits
- Range: front between 90.6% and 92.1%.
- OEE cannot be reported yet; it needs run-state data.
- The cause is a hypothesis, not confirmed.

## Ask / next steps
| Action | Owner | By |
|---|---|---|
| Inspect the groups | Equipment lead | Friday |
<!-- derived-numbers: 7.05 = 3.03+2.91+1.11 -->
"""


def statuses(text, analysis=ANALYSIS, **kw):
    return {name: status for name, status, _ in esc.check(text, analysis, **kw)}


class TestExecSummaryCheck(unittest.TestCase):
    def test_good_summary_has_no_failures(self):
        self.assertNotIn("FAIL", statuses(GOOD).values())

    def test_jargon_including_plurals_fails(self):
        s = statuses(GOOD.replace("three front groups", "three chronic clusters"))
        self.assertEqual(s["plain language"], "FAIL")

    def test_untraceable_percentage_fails(self):
        self.assertEqual(statuses(GOOD.replace("91%", "95%"))["numbers traceable"], "FAIL")

    def test_integer_points_are_checked(self):
        self.assertEqual(statuses(GOOD.replace("about 7 points", "about 9 points"))["numbers traceable"], "FAIL")

    def test_derived_number_arithmetic_is_verified(self):
        bad = GOOD.replace("3.03+2.91+1.11", "3.03+2.91+1.5")
        self.assertEqual(statuses(bad)["numbers traceable"], "FAIL")

    def test_derived_terms_must_appear_in_the_analysis(self):
        self.assertEqual(statuses(GOOD, analysis=ANALYSIS.replace("1.11", "9.99"))["numbers traceable"], "FAIL")

    def test_too_long_fails(self):
        self.assertEqual(statuses(GOOD + "\n" + "word " * 300)["length"], "FAIL")

    def test_missing_oee_caveat_fails(self):
        self.assertEqual(statuses(GOOD.replace("OEE cannot be reported yet", "All good"))["states OEE is not yet reportable"], "FAIL")

    def test_missing_range_fails(self):
        self.assertEqual(statuses(GOOD.replace("Range: front between 90.6% and 92.1%.", "Front is 91%."))["shows a range"], "FAIL")

    def test_placeholder_fails_and_open_owner_warns(self):
        self.assertEqual(statuses(GOOD.replace("Friday", "[REQUIRED]"))["no unfilled placeholders"], "FAIL")
        self.assertEqual(statuses(GOOD.replace("Equipment lead", "[OPEN]"))["owners and dates assigned"], "WARN")

    def test_answer_first_needs_number_and_action(self):
        self.assertEqual(statuses(GOOD.replace("91% of front positions and 96% of rear positions could test; we recommend inspecting three front groups first.", "Things are fine."))["answer first"], "FAIL")

    def test_money_or_throughput_figures_fail_while_impact_is_deferred(self):
        self.assertEqual(statuses(GOOD + "\nThis saves $5,000 a month.")["no money or throughput figures while impact-quantification is deferred"], "FAIL")
        self.assertEqual(statuses(GOOD + "\nWe gain 20 units per hour.")["no money or throughput figures while impact-quantification is deferred"], "FAIL")
        self.assertEqual(statuses(GOOD)["no money or throughput figures while impact-quantification is deferred"], "PASS")

    def test_real_summary_passes_against_the_real_analysis(self):
        res = esc.check(esc.DEFAULT_SUMMARY.read_text(encoding="utf-8"), esc.DEFAULT_ANALYSIS.read_text(encoding="utf-8"))
        self.assertEqual([r for r in res if r[1] == "FAIL"], [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
