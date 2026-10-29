"""
Tests for the two October additions to the validation scripts, on small hand-computed frames:
count_list_reconciler.gap_profile (when a constant gap between the count and the list starts) and
site_id_validator.by_month (share of out-of-range IDs per month).

Usage:
    python test_validation_scripts.py
"""

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_list_reconciler as clr  # noqa: E402
import site_id_validator as siv  # noqa: E402


def frame(gaps, start="2026-10-01 00:00", n_oob=None):
    """One reading every 4 minutes; err_01 = 3 listed IDs + the given gap."""
    ts = pd.date_range(start, periods=len(gaps), freq="4min")
    return pd.DataFrame({"timestamp": ts, "err_01": [3 + g for g in gaps], "n_closed": 3,
                         "n_oob": n_oob if n_oob is not None else 0, "n_dup": 0, "valid": True})


class TestGapProfile(unittest.TestCase):
    def test_a_constant_gap_is_found_at_its_first_reading(self):
        df = frame([0] * 100 + [40] * 100)
        p = clr.gap_profile(df)
        self.assertEqual(p["start"], str(df["timestamp"].iloc[100])[:16])
        self.assertEqual((p["share_after"], p["share_before"]), (100.0, 0.0))
        self.assertEqual(p["common"][0], (40, 100))

    def test_values_around_forty_count_as_the_gap_and_zero_does_not(self):
        df = frame([0] * 80 + [39, 40, 41, 42] * 25 + [0] * 5)
        p = clr.gap_profile(df)
        self.assertEqual(p["start"], str(df["timestamp"].iloc[80])[:16])
        self.assertGreater(p["share_after"], 90.0)

    def test_no_constant_gap_means_no_start(self):
        p = clr.gap_profile(frame([0, 1, 0, 2] * 40))
        self.assertIsNone(p["start"])

    def test_the_gap_counts_every_listed_number_not_only_the_valid_ones(self):
        # 3 valid IDs + 5 stray numbers listed; a count of 48 leaves a gap of 40, not 45
        df = frame([45] * 100, n_oob=5)
        p = clr.gap_profile(df)
        self.assertEqual(p["common"][0], (40, 100))

    def test_months_report_the_mean_count_and_list(self):
        a = frame([0] * 10, start="2026-09-30 22:00")
        b = frame([10] * 10, start="2026-10-01 08:00")
        p = clr.gap_profile(pd.concat([a, b], ignore_index=True))
        self.assertEqual(p["months"]["2026-09"], {"readings": 10, "mean_count": 3.0, "mean_list": 3.0})
        self.assertEqual(p["months"]["2026-10"], {"readings": 10, "mean_count": 13.0, "mean_list": 3.0})

    def test_dropped_readings_are_ignored(self):
        df = frame([40] * 100)
        df.loc[:49, "valid"] = False
        self.assertEqual(clr.gap_profile(df)["months"]["2026-10"]["readings"], 50)


class TestByMonth(unittest.TestCase):
    def test_shares_per_month_by_hand(self):
        sept = pd.DataFrame({"timestamp": pd.date_range("2026-09-30 20:00", periods=2, freq="4min"), "n_closed": 5, "n_oob": 0, "n_dup": 0})
        octo = pd.DataFrame({"timestamp": pd.date_range("2026-10-01 08:00", periods=4, freq="4min"), "n_closed": 3, "n_oob": [1, 0, 1, 0], "n_dup": 0})
        out = siv.by_month(pd.concat([sept, octo], ignore_index=True))
        self.assertEqual(out["2026-09"], {"rows_pct": 0.0, "numbers_pct": 0.0})
        # October: 2 of 4 rows have a stray number; 2 stray numbers among 4*3 + 2 = 14 listed
        self.assertEqual(out["2026-10"], {"rows_pct": 50.0, "numbers_pct": 14.3})

    def test_a_month_with_nothing_listed_is_zero_not_an_error(self):
        df = pd.DataFrame({"timestamp": pd.date_range("2026-10-01", periods=3, freq="4min"), "n_closed": 0, "n_oob": 0, "n_dup": 0})
        self.assertEqual(siv.by_month(df)["2026-10"], {"rows_pct": 0.0, "numbers_pct": 0.0})


if __name__ == "__main__":
    unittest.main(verbosity=1)
