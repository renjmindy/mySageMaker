"""
Unit tests for closure_events.py on synthetic site-state matrices (no handler data needed).

Usage:
    python test_closure_events.py
"""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import closure_events as ce  # noqa: E402


def matrix(n: int = 400) -> pd.DataFrame:
    idx = pd.date_range("2026-09-01", periods=n, freq="4min")
    m = pd.DataFrame(False, index=idx, columns=list(range(1, 257)))
    m["weight_min"] = 4.0
    return m


def close(m: pd.DataFrame, sites, start: int, length: int) -> None:
    m.iloc[start:start + length, [m.columns.get_loc(s) for s in sites]] = True


BLOCK_A = [1, 2, 17, 18]          # aligned 2x2 block, rows 1-2, cols 1-2
BLOCK_B = [199, 200, 215, 216]    # rows 13-14, cols 7-8: an aligned 2x2 block far from BLOCK_A


class TestClosureEvents(unittest.TestCase):
    def test_closure_of_three_readings_is_found_two_are_ignored(self):
        m = matrix(); close(m, [50], 100, 3); close(m, [60], 200, 2)
        ep = ce.closure_episodes(m)
        self.assertEqual(sorted(ep["site"]), [50])  # the 2-reading blip is debounced away

    def test_episode_start_end_and_duration(self):
        m = matrix(); close(m, [50], 100, 10)
        ep = ce.closure_episodes(m).iloc[0]
        self.assertEqual(ep["start"], m.index[100])
        self.assertEqual(ep["end"], m.index[110])
        self.assertEqual(ep["duration_min"], 40.0)
        self.assertFalse(ep["ongoing"] or ep["left_censored"])

    def test_ongoing_and_left_censored_flags(self):
        m = matrix(); close(m, [50], 390, 10); close(m, [60], 0, 10)
        ep = ce.closure_episodes(m).set_index("site")
        self.assertTrue(ep.loc[50, "ongoing"])
        self.assertTrue(ep.loc[60, "left_censored"])

    def test_aligned_block_is_one_event_with_full_alignment(self):
        m = matrix(); close(m, BLOCK_A, 100, 45)
        ev = ce.group_events(ce.closure_episodes(m))
        self.assertEqual(len(ev), 1)
        self.assertEqual((ev.iloc[0]["n_sites"], ev.iloc[0]["block_aligned"]), (4, 1.0))

    def test_concurrent_unrelated_closures_are_not_merged(self):
        m = matrix(); close(m, BLOCK_A, 100, 45); close(m, BLOCK_B, 100, 45)  # same minute, far apart
        ev = ce.group_events(ce.closure_episodes(m))
        self.assertEqual(sorted(ev["n_sites"]), [4, 4])
        self.assertTrue((ev["block_aligned"] >= 0.99).all())

    def test_scattered_sites_stay_separate_and_fail_the_size_filter(self):
        m = matrix(); close(m, [5, 70, 130, 190, 250, 100], 100, 45)
        ev = ce.group_events(ce.closure_episodes(m))
        self.assertEqual(len(ev), 6)
        self.assertTrue((ev["n_sites"] == 1).all())
        self.assertEqual(ce.aligned_share([5, 70, 130, 190, 250, 100]), 0.0)

    def test_connected_but_misaligned_sites_form_one_event_with_low_alignment(self):
        m = matrix(); close(m, [2, 3, 18, 19], 100, 45)  # a 2x2 square straddling two aligned blocks
        ev = ce.group_events(ce.closure_episodes(m))
        self.assertEqual(len(ev), 1)
        self.assertEqual((ev.iloc[0]["n_sites"], ev.iloc[0]["block_aligned"]), (4, 0.0))

    def test_ranking_prefers_alignment_then_size_then_duration(self):
        m = matrix()
        close(m, [2, 3, 18, 19], 100, 60)   # misaligned, long
        close(m, BLOCK_A, 200, 20)          # aligned, short
        ranked = ce.rank_events(ce.group_events(ce.closure_episodes(m)))
        self.assertEqual(ranked.iloc[0]["block_aligned"], 1.0)

    def test_quiet_site_baseline(self):
        m = matrix(4000); close(m, [50], 100, 10)  # 0.25% of readings: a "quiet" site (< 0.5%)
        base = ce.quiet_baseline(m, ce.closure_episodes(m))
        self.assertEqual(base["episodes"], 1)
        self.assertEqual(base["quiet_sites"], 256)


if __name__ == "__main__":
    unittest.main(verbosity=1)
