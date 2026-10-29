"""
Unit tests for viz_check.py: each test breaks one thing in the real report and expects the matching
check to fail (static checks only, no browser).

Usage:
    python test_viz_check.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_heatmap as sh  # noqa: E402
import viz_check as vc  # noqa: E402

DATA = sh.collect()
PAGE = sh.render(DATA)


def status(page=PAGE):
    return {n: s for n, s, _ in vc.run_static(DATA, page)}


def rep(text, old, new):
    assert old in text, old
    return text.replace(old, new, 1)


class TestVizCheck(unittest.TestCase):
    def test_real_report_has_no_failures(self):
        self.assertEqual([n for n, s in status().items() if s == "FAIL"], [])

    def test_tampered_heatmap_cell_fails(self):
        self.assertEqual(status(rep(PAGE, "closed 98% of the last 7 days", "closed 40% of the last 7 days"))["numbers match the analysis scripts"], "FAIL")

    def test_tampered_period_cell_fails(self):
        import re
        old = re.search(r"closed ([\d.]+)% of the whole period", PAGE).group(0)
        new = "closed 12.3% of the whole period" if "12.3%" not in old else "closed 45.6% of the whole period"
        self.assertEqual(status(rep(PAGE, old, new))["numbers match the analysis scripts"], "FAIL")

    def test_tampered_tile_and_range_fail(self):
        headline = f"<b>{DATA['sides']['front']['availability_pct']:.1f}%</b>"
        self.assertEqual(status(rep(PAGE, headline, "<b>99.9%</b>"))["numbers match the analysis scripts"], "FAIL")
        lo, hi = DATA["sides"]["rear"]["ci"]
        self.assertEqual(status(rep(PAGE, f"plausible range {lo:.1f}-{hi:.1f}%", "plausible range 1.0-2.0%"))["numbers match the analysis scripts"], "FAIL")

    def test_missing_date_range_fails(self):
        rng = sh.date_range(DATA["first"], DATA["last"])
        self.assertEqual(status(rep(PAGE, rng + ".", "recently."))["subtitle states the date range"], "FAIL")

    def test_jargon_in_visible_text_fails(self):
        self.assertEqual(status(rep(PAGE, "Handler test positions: how many can test", "Contactor site availability"))["plain language in visible text"], "FAIL")

    def test_missing_toggle_ranked_table_and_live_region_fail(self):
        self.assertEqual(status(PAGE.replace('type="radio"', 'type="checkbox"'))["view toggle (radio)"], "FAIL")
        self.assertEqual(status(rep(PAGE, "Positions closed the most", "Other"))["ranked table of positions closed the most"], "FAIL")
        self.assertEqual(status(rep(PAGE, 'aria-live="polite"', ""))["aria-live region"], "FAIL")

    def test_missing_range_on_tiles_fails(self):
        self.assertEqual(status(PAGE.replace("plausible range", "typical"))["plausible range on every tile"], "FAIL")

    def test_responsive_and_touch_rules_are_required(self):
        self.assertEqual(status(rep(PAGE, "minmax(min(380px,100%),1fr)", "minmax(380px,1fr)"))["responsive grid rule (no fixed 380 px minimum)"], "FAIL")
        self.assertEqual(status(rep(PAGE, "(pointer:coarse)", "(pointer:fine)"))["touch-size rule for narrow / coarse pointers"], "FAIL")

    def test_ramp_check_catches_close_steps_and_wrong_order(self):
        ok, _ = vc.ramp_check(["#e8f0fa", "#e0ecfa", "#6da7ec", "#3987e5", "#1c5cab", "#0d366b"], increasing=False)
        self.assertFalse(ok)  # first step ~1 DeltaE
        ok, detail = vc.ramp_check(["#0d366b", "#1c5cab", "#3987e5", "#6da7ec", "#b7d3f6", "#e8f0fa"], increasing=False)
        self.assertFalse(ok)  # dark to light but declared decreasing
        self.assertIn("NOT monotonic", detail)

    def test_series_colours_too_close_are_detected(self):
        self.assertLess(vc.delta_e("#2a78d6", "#2f7fd6"), vc.MIN_SERIES_DE)
        self.assertGreater(vc.delta_e(*sh.SERIES_LIGHT), vc.MIN_SERIES_DE)

    def test_shipped_ramps_pass(self):
        self.assertTrue(vc.ramp_check(sh.LIGHT, increasing=False)[0])
        self.assertTrue(vc.ramp_check(sh.DARK, increasing=True)[0])


if __name__ == "__main__":
    unittest.main(verbosity=1)
