"""
Tests for the translator skill's tools:
  * the jargon detector, measured on a labelled corpus (precision and recall) plus the plain-English cases that a
    word filter gets wrong
  * the readability scorer (jargon-dense short sentences must not score OK)
  * the grid geometry and position words
  * the translation checker: each test breaks one thing in a translation and expects the matching check to fail;
    the real translations and pattern library must pass

Usage:
    python test_translator.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jargon_detector as jd  # noqa: E402
import readability_scorer as rs  # noqa: E402
import translation_check as tc  # noqa: E402

JARGON = [  # a manager would be lost
    "Rear sites 419/420/435/436 are NEW with 1.53 pts in the last 7 days.",
    "The chronic clusters in the front readings explain most of the closure time.",
    "We backtested the alert rules on the history; the results are in-sample.",
    "The count-list gap rule drops readings where err_01 exceeds the list.",
    "Bootstrap resampling of days gives the range for the front readings.",
    "PERSISTENT sites stay closed across both halves (split-half overlap 17/20).",
    "The MAD-based z-score flags no day.",
    "Debounce the readings with a rolling median of five samples.",
    "Assumption A18 caps each reading at 15 minutes.",
    "Block alignment of 1.0 suggests a 2x2 module.",
    "OCR noise produces out-of-range IDs in the rear readings.",
    "The data gate fails when a day's file is missing.",
    "A waiver expires on 2026-12-31 and the WARN reappears.",
    "Near-full counts of 252 to 255 are read failures.",
    "Time-weighted availability per side with a lower bound.",
    "The hypertable partitions contactor samples by time.",
    "The false-alarm rate of the capacity rule is 0.2 per week.",
    "Permutation p = 0.669 for the best level shift.",
    "Carry-forward is limited to 15 minutes across a capture gap in the readings.",
    "Sites in the RESOLVED state are history.",
    "The closure episodes are grouped into spatially connected events.",
    "The field err_01 holds the reported count of closed positions.",
    "Unweighted mean of closed positions is higher than the time-weighted one.",
    "Pareto of closure time by position.",
    "The out-of-sample test uses the second half of the front readings.",
]
PLAIN = [  # fine for a manager
    "On average 91% of front test positions were able to test.",
    "Three groups of front positions are still out of service.",
    "We recommend inspecting them first.",
    "The site visit is on Friday.",
    "Our availability is Monday to Friday.",
    "Check back at a regular interval of four minutes.",
    "A burst pipe flooded the room.",
    "The cluster of houses is on the hill.",
    "Prices are null and void after the deadline.",
    "Sensitivity to light matters for the camera.",
    "The handler's screen is read about every four minutes.",
    "Capacity did not clearly improve or worsen over the month.",
    "About 3% of readings were left out.",
    "The month's average is plausibly between 90.6% and 92.1%.",
    "Neighbouring positions failing together suggests a shared part, such as a board.",
    "This is a hypothesis, not confirmed.",
    "She likes the new design.",
    "The current plan is fine.",
    "I am not mad about it.",
    "The meeting agenda has two items.",
    "Parking in the rear lot is free.",
    "We tested the front door lock.",
    "The report is due at 4 pm.",
]
ANALYSIS = tc.esc.DEFAULT_ANALYSIS.read_text(encoding="utf-8")
TECH = "Front 91.32% (lower bound 90.88%, plausible range 90.57-92.08%) of positions able to test; OEE is blocked."
PLAIN_OK = "On average 91% of front test positions were able to test. It could be as low as 90.9%, and is plausibly between 90.6% and 92.1%. OEE cannot be reported yet."


def verdicts(technical=TECH, plain=PLAIN_OK, persona="manager", analysis=ANALYSIS):
    return {n: (s, d) for n, s, d in tc.check_pair(technical, plain, persona, analysis)}


class TestJargonDetector(unittest.TestCase):
    def test_precision_and_recall_on_the_labelled_corpus(self):
        tp = sum(bool(jd.detect(s)) for s in JARGON)
        fp = sum(bool(jd.detect(s)) for s in PLAIN)
        fn = len(JARGON) - tp
        precision, recall = tp / max(1, tp + fp), tp / max(1, tp + fn)
        self.assertGreaterEqual(precision, 0.95, f"precision {precision:.2f} ({fp} plain sentences flagged)")
        self.assertGreaterEqual(recall, 0.90, f"recall {recall:.2f} ({fn} jargon sentences missed)")

    def test_plain_english_words_are_not_flagged_outside_the_domain(self):
        for s in PLAIN[3:10]:
            self.assertEqual(jd.detect(s), [], s)

    def test_the_same_word_is_flagged_inside_the_domain(self):
        self.assertTrue(jd.detect("Front availability of the test positions is 91%."))
        self.assertTrue(jd.detect("The chronic cluster in the front readings."))

    def test_status_codes_are_case_sensitive(self):
        self.assertTrue(jd.detect("These are PERSISTENT."))
        self.assertEqual(jd.detect("A persistent smell and a new, current plan."), [])

    def test_plurals_and_ids_and_field_names(self):
        self.assertTrue(jd.detect("Three clusters of closed sites in the front positions."))
        self.assertIn("assumption id", [t for t, _, _ in jd.detect("See A8 and A18.")])
        self.assertIn("field name", [t for t, _, _ in jd.detect("The err_01 column.")])


class TestReadabilityScorer(unittest.TestCase):
    def test_jargon_dense_short_sentences_do_not_score_ok(self):
        g = "Chronic clusters persist. Recency is PERSISTENT. Bootstrap intervals overlap. MAD flags nothing. Debounce holds."
        self.assertEqual(rs.score(g)["verdict"], "jargon-dense")

    def test_long_sentences_are_flagged(self):
        self.assertEqual(rs.score(" ".join(["word"] * 60) + ".")["verdict"], "too dense - split sentences")

    def test_allowed_terms_are_not_counted(self):
        t = "OEE cannot be reported yet for the front handler."
        self.assertEqual(rs.score(t, allow={"oee"})["jargon_per_100_words"], 0.0)
        self.assertGreater(rs.score(t)["jargon_per_100_words"], 0)

    def test_plain_text_is_ok(self):
        self.assertEqual(rs.score("Three groups of front positions are out of service. We recommend inspecting them first.")["verdict"], "OK")


class TestGeometry(unittest.TestCase):
    def test_known_groups(self):
        self.assertEqual(tc.region({229, 230, 245, 246}), {"rows": (15, 16), "vertical": "top", "horizontal": "left"})
        self.assertEqual(tc.region({3, 4, 19, 20})["vertical"], "bottom")
        self.assertEqual(tc.region({143, 144, 159, 160, 175, 176, 191, 192})["horizontal"], "right")
        self.assertEqual(tc.region({419, 420, 435, 436})["rows"], (27, 28))

    def test_the_old_library_error_is_caught(self):
        self.assertIsNotNone(tc.check_positions("Cluster 229/230/245/246 closed 92%", "A group (229, 230, 245, 246) near the bottom of the front grid is out."))
        self.assertIsNone(tc.check_positions("Cluster 229/230/245/246 closed 92%", "A group (229, 230, 245, 246) near the top of the front grid is out."))

    def test_row_ranges_and_decimals(self):
        self.assertIsNotNone(tc.check_positions("Group 143/144/159/160", "Positions 143, 144, 159 and 160 (rows 1 to 4) are out."))
        # a decimal such as 3.03 must not be read as position 3
        self.assertIsNone(tc.check_positions("Groups 143/144/159/160 and 3/4/19/20", "Positions 143, 144, 159 and 160 (rows 9 to 10, right edge) cost 3.03 points."))


class TestTranslationCheck(unittest.TestCase):
    def test_a_good_translation_passes(self):
        self.assertEqual([n for n, (s, _) in verdicts().items() if s == "FAIL"], [])

    def test_invented_number_fails(self):
        self.assertEqual(verdicts(plain=PLAIN_OK + " It is 97.5% on weekends.")["numbers kept, none invented"][0], "FAIL")

    def test_keeping_no_number_fails(self):
        p = "Most front positions were able to test. It could be a little lower. OEE cannot be reported yet."
        self.assertEqual(verdicts(plain=p)["numbers kept, none invented"][0], "FAIL")

    def test_a_percentage_restated_as_n_of_every_100_is_accepted(self):
        t = "Front availability 91.3% (broken readings excluded)"
        p = "On average 9 of every 100 front test positions could not test; broken readings were left out."
        self.assertEqual(verdicts(t, p, analysis=ANALYSIS)["numbers kept, none invented"][0], "PASS")
        self.assertEqual(verdicts(t, p.replace("9 of every", "5 of every"), analysis=ANALYSIS)["numbers kept, none invented"][0], "FAIL")

    def test_lost_caveats_fail(self):
        for drop, tech in (("It could be as low as 90.9%, and ", TECH), ("OEE cannot be reported yet.", TECH)):
            self.assertEqual(verdicts(plain=PLAIN_OK.replace(drop, ""))["caveats kept"][0], "FAIL", drop)
        hyp = "Neighbouring positions failing together suggests a shared part; this is a hypothesis, not confirmed, 91.32% of positions."
        self.assertEqual(verdicts(hyp, "A shared part is the cause of the 91% figure.")["caveats kept"][0], "FAIL")

    def test_jargon_policy_per_persona(self):
        p = PLAIN_OK + " The clusters are PERSISTENT."
        self.assertEqual(verdicts(plain=p, persona="manager")["plain language for the manager persona"][0], "FAIL")
        self.assertEqual(verdicts(plain=PLAIN_OK, persona="customer")["plain language for the customer persona"][0], "FAIL")  # OEE
        self.assertEqual(verdicts(plain=PLAIN_OK, persona="manager")["plain language for the manager persona"][0], "PASS")

    def test_wrong_position_word_fails(self):
        t = "Cluster 229/230/245/246 closed 92% of the period"
        self.assertEqual(verdicts(t, "Positions 229, 230, 245 and 246 at the bottom are out 92% of the time.", analysis=None)["positions described correctly"][0], "FAIL")

    def test_dense_translation_fails_readability(self):
        self.assertEqual(verdicts(plain=PLAIN_OK + " " + " ".join(["word"] * 70) + ".")["readable"][0], "FAIL")

    def test_technical_numbers_must_trace_to_the_analysis(self):
        self.assertEqual(verdicts(TECH.replace("91.32%", "81.32%"), PLAIN_OK.replace("91%", "81%"))["technical numbers trace to the analysis document"][0], "FAIL")

    def test_money_figures_fail_while_impact_is_deferred(self):
        self.assertEqual(verdicts(plain=PLAIN_OK + " That is worth $5,000 a month.")["no money or throughput figures while impact is deferred"][0], "FAIL")

    def test_the_real_translations_and_library_pass(self):
        res = tc.check_text(tc.TRANSLATIONS.read_text(encoding="utf-8"), ANALYSIS)
        res += tc.check_text(tc.LIBRARY.read_text(encoding="utf-8"), ANALYSIS, default_persona="manager")
        self.assertEqual([(n, d) for n, s, d in res if s == "FAIL"], [])
        self.assertGreater(len(res), 60)


if __name__ == "__main__":
    unittest.main(verbosity=1)
