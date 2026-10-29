"""
Unit tests for insight_brief_check.py: each test breaks one thing in the real brief and expects the
matching check to fail (so a pass on the real brief means something).

Usage:
    python test_insight_brief_check.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import insight_brief_check as ibc  # noqa: E402
import assumptions_tracker as at  # noqa: E402

BRIEF = ibc.DEFAULT_BRIEF.read_text(encoding="utf-8")
ANALYSIS = ibc.DEFAULT_ANALYSIS.read_text(encoding="utf-8")
SUMMARY = ibc.DEFAULT_SUMMARY.read_text(encoding="utf-8")
LOG = at.load()


def run(brief=BRIEF, analysis=ANALYSIS, log=LOG, summary=None):
    return {n: (s, d) for n, s, d in ibc.check(brief, analysis, log, summary)}


def rep(text, old, new, count=1):
    assert old in text, old
    return text.replace(old, new, count)


class TestInsightBriefCheck(unittest.TestCase):
    def test_real_brief_has_no_failures(self):
        self.assertEqual([n for n, (s, _) in run(summary=SUMMARY).items() if s == "FAIL"], [])

    def test_money_or_throughput_figures_fail_while_impact_is_deferred(self):
        self.assertEqual(run(rep(BRIEF, "Inspect the two eight-site front groups first, then the column-13 group.", "Inspect the two eight-site front groups first; worth $5,000 a month."))["no money or throughput figures while impact-quantification is deferred"][0], "FAIL")

    def test_placeholder_fails(self):
        self.assertEqual(run(rep(BRIEF, "Inspect the two eight-site front groups first, then the column-13 group.", "[REQUIRED]"))["no unfilled placeholders"][0], "FAIL")

    def test_more_than_five_insights_fails(self):
        extra = "| 6 | x | y | **Low** - one day of data only here | A18 (APPLIED) | z |\n"
        self.assertEqual(run(rep(BRIEF, "\n## Scoring", "\n" + extra + "\n## Scoring"))["at most five insights"][0], "FAIL")

    def test_untraceable_number_fails(self):
        self.assertEqual(run(rep(BRIEF, "6.31 pts together", "9.25 pts together"))["numbers traceable"][0], "FAIL")

    def test_derived_arithmetic_is_verified(self):
        self.assertEqual(run(rep(BRIEF, "6.31 = 2.64+2.52+1.15", "6.31 = 2.64+2.52+1.5"))["numbers traceable"][0], "FAIL")

    def test_confidence_needs_a_basis(self):
        self.assertEqual(run(rep(BRIEF, "**High** - the ranking repeats across both halves of the period (top-20 overlap 17/20), and both eight-site groups are still closed now and insensitive to the window length (3, 7 or 14 days); only the size of the smaller group depends on the window.", "**High**"))["confidence stated with its test"][0], "FAIL")

    def test_high_confidence_on_open_assumption_fails(self):
        log = [dict(a, status="OPEN") if a["id"] == "A8" else a for a in LOG]
        self.assertEqual(run(log=log)["assumption ids and High-confidence rules"][0], "FAIL")

    def test_high_confidence_on_applied_assumption_needs_insensitivity(self):
        b = rep(BRIEF, "and both eight-site groups are still closed now and insensitive to the window length (3, 7 or 14 days); only the size of the smaller group depends on the window", "and both eight-site groups are still closed now and the result looks right")
        self.assertEqual(run(b)["assumption ids and High-confidence rules"][0], "FAIL")

    def test_unknown_assumption_and_wrong_status_fail(self):
        self.assertEqual(run(rep(BRIEF, "A10 (CONFIRMED)", "A99 (CONFIRMED)"))["assumption ids and High-confidence rules"][0], "FAIL")
        self.assertEqual(run(rep(BRIEF, "A19 (APPLIED)", "A19 (CONFIRMED)"))["assumption statuses match the log"][0], "FAIL")

    def test_causal_wording_needs_a_hypothesis(self):
        b = rep(BRIEF, "Inspect the rear block and the new column-13 group next.", "Replace the board, which is the root cause.")
        self.assertEqual(run(b)["no causal overreach"][0], "FAIL")

    def test_score_arithmetic_label_agreement_and_order(self):
        self.assertEqual(run(rep(BRIEF, "| 3 | 3 | 3 | 27 |", "| 3 | 3 | 3 | 20 |"))["scoring consistent and ranked"][0], "FAIL")
        self.assertEqual(run(rep(BRIEF, "| 2 | 2 | 3 | 12 |", "| 2 | 3 | 3 | 18 |"))["scoring consistent and ranked"][0], "FAIL")  # label says Medium (2)
        swapped = rep(rep(BRIEF, "| 1 | 3 | 3 | 3 | 27 |", "| 1 | 1 | 1 | 1 | 1 |"), "| 5 | 1 | 2 | 1 | 2 |", "| 5 | 3 | 3 | 3 | 27 |")
        self.assertEqual(run(swapped)["scoring consistent and ranked"][0], "FAIL")  # confidence labels / order break

    def test_ranking_sensitivity_warns_when_top_changes(self):
        # same product for #1 and #2 but opposite strengths: the winner flips under 'sum'/'conf_act'
        scores = {"a": (3, 1, 3), "b": (1, 3, 3), "c": (1, 1, 1)}
        self.assertNotEqual(ibc.top_bottom(scores, "product"), ibc.top_bottom(scores, "impact2"))

    def test_missing_oee_in_known_unknowns_fails(self):
        self.assertEqual(run(rep(BRIEF, "- OEE: run and idle time", "- Missing: run and idle time"))["known unknowns mention OEE"][0], "FAIL")

    def test_summary_numbers_must_appear_in_the_brief(self):
        s = rep(SUMMARY, "About 3% of readings", "About 45% of readings")
        self.assertEqual(run(summary=s)["executive summary numbers appear in the brief"][0], "WARN")


if __name__ == "__main__":
    unittest.main(verbosity=1)
