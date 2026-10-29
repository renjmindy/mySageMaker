"""
Unit tests for methodology_check.py: each test breaks one thing in the real slide / write-up (or the effects)
and expects the matching check to fail. Effects are fixed so the tests need no private data. One test pins the
weighting behaviour the explainer describes (a dropped reading's own time is not counted; a capture gap counts
for at most 15 minutes).

Usage:
    python test_methodology_check.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import methodology_check as mc  # noqa: E402

SLIDE = mc.SLIDE.read_text(encoding="utf-8")
WRITEUP = mc.WRITEUP.read_text(encoding="utf-8")
BLANK = mc.BLANK.read_text(encoding="utf-8")
ANALYSIS = mc.esc.DEFAULT_ANALYSIS.read_text(encoding="utf-8")
YAML = mc.CONTRACT.read_text(encoding="utf-8")
GUIDE = mc.GUIDE.read_text(encoding="utf-8")
CANON = mc.CANONICAL.read_text(encoding="utf-8")
EFFECTS = {"A8": 1.31, "A15": 0.01, "A18": 0.66}


def run(slide=SLIDE, writeup=WRITEUP, blank=BLANK, analysis=ANALYSIS, yaml=YAML, effects=EFFECTS, guide=GUIDE, canon=CANON):
    return {n: (s, d) for n, s, d in mc.check(slide, writeup, blank, analysis, yaml, effects, guide, canon)}


def rep(text, old, new):
    assert old in text, old
    return text.replace(old, new, 1)


class TestMethodologyCheck(unittest.TestCase):
    def test_real_explainer_has_no_failures(self):
        self.assertEqual([n for n, (s, _) in run().items() if s == "FAIL"], [])

    def test_placeholder_and_money_fail(self):
        self.assertEqual(run(writeup=WRITEUP + "\n[REQUIRED]")["no unfilled placeholders"][0], "FAIL")
        self.assertEqual(run(writeup=WRITEUP + "\nThis saves $5,000.")["no money or throughput figures while impact-quantification is deferred"][0], "FAIL")

    def test_a_missing_contract_rule_fails(self):
        w = "\n".join(l for l in WRITEUP.splitlines() if not l.startswith("| A15 |"))
        self.assertEqual(run(writeup=w)["every contract rule is in the write-up's rules table"][0], "FAIL")

    def test_wrong_constant_fails(self):
        self.assertEqual(run(writeup=rep(WRITEUP, "| 252 |", "| 250 |"))["rules carry the loader's constants"][0], "FAIL")

    def test_stated_effect_must_match_the_measurement(self):
        self.assertEqual(run(writeup=rep(WRITEUP, "raises it by 1.3 pts", "raises it by 2.9 pts"))["stated effects equal the measured effects"][0], "FAIL")

    def test_the_slide_must_name_the_rules_that_move_the_number_most(self):
        self.assertEqual(run(slide=rep(SLIDE, "(rules A8, A18)", "(rules A3)"))["the slide names the two rules that move the number most"][0], "FAIL")
        # the choice is data-driven: if the gap rule became the biggest effect, the slide would have to name it
        self.assertEqual(run(effects={"A8": 0.5, "A15": 2.0, "A18": 1.0})["the slide names the two rules that move the number most"][0], "FAIL")

    def test_worked_example_result_and_minutes_are_recomputed(self):
        self.assertEqual(run(writeup=rep(WRITEUP, "Result: **90.9%**", "Result: **91.9%**"))["worked example recomputed from the loader"][0], "FAIL")
        self.assertEqual(run(writeup=rep(WRITEUP, "| 15 | 24 | the next reading", "| 4 | 24 | the next reading"))["worked example recomputed from the loader"][0], "FAIL")
        self.assertEqual(run(writeup=rep(WRITEUP, "| 4 | 22 | the count is 8 above the list", "| 4 | 30 | the count is 8 above the list"))["worked example recomputed from the loader"][0], "FAIL")

    def test_worked_example_must_cover_the_cases_people_get_wrong(self):
        w = "\n".join(l for l in WRITEUP.splitlines() if not l.startswith("| 10:16 |"))
        self.assertEqual(run(writeup=w)["worked example covers the cases people get wrong"][0], "FAIL")

    def test_weighting_behaviour_matches_the_explanation(self):
        rows = [r for r in mc.table(mc.section(WRITEUP, "Worked example"))[1:] if len(r) >= 6 and r[0][:2].isdigit()]
        df = mc.answer(rows)["df"].set_index(mc.answer(rows)["df"]["timestamp"].dt.strftime("%H:%M"))
        self.assertEqual(df.loc["10:08", "status"], "READ_FAIL_256")
        self.assertEqual(df.loc["10:08", "valid"], False)                  # the dropped reading is not counted ...
        self.assertEqual(df.loc["10:04", "weight_min"], 4.0)               # ... and the reading before it covers only up to it
        self.assertEqual(df.loc["10:24", "weight_min"], mc.cio.DEFAULT_MAX_GAP_MIN)  # a 20-minute capture gap counts for 15

    def test_untraceable_numbers_fail(self):
        self.assertEqual(run(slide=rep(SLIDE, "front 90.6-92.1%", "front 85.5-92.1%"))["numbers traceable to the analysis document"][0], "FAIL")

    def test_slide_numbers_must_appear_in_the_write_up(self):
        self.assertEqual(run(slide=SLIDE + "\n- Extra: 0.61 points.")["slide numbers also appear in the write-up"][0], "FAIL")

    def test_slide_must_be_short_and_plain(self):
        self.assertEqual(run(slide=SLIDE + "\n" + "word " * 40)["slide is short"][0], "FAIL")
        self.assertEqual(run(slide=rep(SLIDE, "at least this much", "a lower bound"))["slide in plain language"][0], "FAIL")

    def test_limits_must_be_stated(self):
        self.assertEqual(run(writeup=rep(WRITEUP, "this is a hypothesis", "this is an idea"))["limits stated (lower bound, range, hypothesis, not OEE)"][0], "FAIL")
        self.assertEqual(run(slide=rep(SLIDE, "This is not OEE, which cannot be reported yet.", ""))["slide says it is not OEE and gives a range"][0], "FAIL")

    def test_reproduction_commands_must_exist(self):
        self.assertEqual(run(writeup=rep(WRITEUP, "methodology_check.py --answer", "no_such_script.py"))["reproduction commands point at existing scripts"][0], "FAIL")

    def test_teachback_must_match_and_hide_the_answer(self):
        name = "teach-back table equals the write-up's raw columns and hides the answer"
        self.assertEqual(run(blank=BLANK + "\nResult: 90.9%")[name][0], "FAIL")
        self.assertEqual(run(blank=rep(BLANK, "| 10:20 | 30 | 1-22 |", "| 10:20 | 31 | 1-22 |"))[name][0], "FAIL")

    def test_audience_guide_must_be_a_pointer_not_a_copy(self):
        self.assertEqual(run(guide=CANON)["audience guide is a pointer, not a second copy"][0], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=1)
