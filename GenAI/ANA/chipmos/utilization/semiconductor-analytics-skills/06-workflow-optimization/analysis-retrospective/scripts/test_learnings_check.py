"""
Tests for learnings_check.py: each test breaks one thing in the real log, retrospective or their sources and
expects the matching check to fail.

Usage:
    python test_learnings_check.py
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import learnings_check as lc  # noqa: E402

LOG = lc.LOG.read_text(encoding="utf-8")
RETRO = lc.RETRO.read_text(encoding="utf-8")
PLAN = lc.pc.PLAN.read_text(encoding="utf-8")
MAP = lc.pc.MAP.read_text(encoding="utf-8")
REGISTRY = json.loads(lc.pc.REGISTRY.read_text(encoding="utf-8"))
OWN = [f.read_text(encoding="utf-8") for f in lc.OWN_FILES]
FILES = lc.scan_corrections()


def run(log=LOG, retro=RETRO, plan=PLAN, own=OWN, files=FILES, commit=lc.git_has, root=lc.ROOT):
    return {n: (s, d) for n, s, d in lc.check(log, retro, plan, MAP, REGISTRY, own, files, root=root, commit_exists=commit)}


def rep(text, old, new):
    assert old in text, old
    return text.replace(old, new, 1)


class TestHelpers(unittest.TestCase):
    def test_counts_and_table(self):
        rows = [{"class": "a", "repeat of": "-", "status": "encoded"}, {"class": "a", "repeat of": "L1", "status": "open"}, {"class": "b", "repeat of": "-", "status": "documented"}]
        c = lc.counts(rows)
        self.assertEqual(c["a"], {"learnings": 2, "repeats": 1, "encoded": 1, "documented": 0, "open": 1})
        self.assertIn("| b | 1 | 0 | 0 | 1 | 0 |", lc.table_text(c))

    def test_resolve(self):
        ok = '`lib/contactor_io.py` "NEAR_FULL_MIN"'
        self.assertEqual(lc.resolve(ok, lc.ROOT, True), [])
        self.assertTrue(lc.resolve('`lib/contactor_io.py` "NOT_THERE"', lc.ROOT, True))
        self.assertTrue(lc.resolve('`lib/nope.py` "X"', lc.ROOT, True))
        self.assertTrue(lc.resolve("`CLAUDE.md`", lc.ROOT, True), "a document is not code")
        self.assertTrue(lc.resolve("`lib/contactor_io.py`", lc.ROOT, True), "code needs a named check")
        self.assertEqual(lc.resolve("`CLAUDE.md`", lc.ROOT, False), [])
        self.assertTrue(lc.resolve("-", lc.ROOT, True))

    def test_scan_skips_this_skill_and_private_folders(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for rel in ("a/doc.md", "analysis-retrospective/x.md", "reports/y.md", "out/z.md", "a/code.py"):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text("Corrected 2026-10-29: the old text was wrong.", encoding="utf-8")
            self.assertEqual(lc.scan_corrections(root), ["a/doc.md"])


class TestLearningsCheck(unittest.TestCase):
    def test_real_log_has_no_failures_and_warns_about_deadlines(self):
        r = run()
        self.assertEqual([n for n, (s, _) in r.items() if s == "FAIL"], [])
        self.assertEqual(r["actions have a deadline"][0], "WARN")

    def test_a_real_date_clears_the_warning_for_that_action(self):
        n = len(lc.pc.table(lc.pc.section(RETRO, "Actions")))  # derived: no count is typed here
        r = run(retro=rep(RETRO, "| no deadline set | L19 |", "| 2026-12-01 | L19 |"))
        self.assertIn(f"{n - 1} action", r["actions have a deadline"][1])

    def test_placeholder_money_and_stale_terms(self):
        self.assertEqual(run(retro=RETRO + "\n[" + "REQUIRED]")["no unfilled placeholders"][0], "FAIL")
        self.assertEqual(run(log=LOG + "\nThe repair saves $5,000.")["no money or throughput figures while impact-quantification is deferred"][0], "FAIL")
        self.assertEqual(run(own=OWN + ["encoded in QA check A8"])["no stale terms in the skill and its templates"][0], "FAIL")

    def test_the_skills_own_files_hold_no_stale_example(self):
        self.assertEqual(run()["no stale terms in the skill and its templates"][0], "PASS")

    def test_learning_fields_class_phase_and_values(self):
        name = "every learning is complete, classified and concrete"
        self.assertEqual(run(log=rep(LOG, "| data-pitfall | P0 | Readings with counts", "| cosmic | P0 | Readings with counts"))[name][0], "FAIL")
        self.assertEqual(run(log=rep(LOG, "| data-pitfall | P0 | Readings with counts", "| data-pitfall | P42 | Readings with counts"))[name][0], "FAIL")
        self.assertEqual(run(log=rep(LOG, "| user | encoded | `lib/contactor_io.py` \"MAX_COUNT_GAP\"", "| a colleague | encoded | `lib/contactor_io.py` \"MAX_COUNT_GAP\""))[name][0], "FAIL")
        self.assertEqual(run(log=rep(LOG, "| user | encoded |", "| user | finished |"))[name][0], "FAIL")
        self.assertEqual(run(log=rep(LOG, "| L3 | data-pitfall", "| L2 | data-pitfall"))[name][0], "FAIL")

    def test_rules_must_be_concrete_and_blameless(self):
        name = "every learning is complete, classified and concrete"
        rule = "Treat counts from 252 up as read failures, and test every delivery for an unflagged band just below the failure value."
        self.assertEqual(run(log=rep(LOG, rule, "Be more careful with the data."))[name][0], "FAIL")
        self.assertEqual(run(log=rep(LOG, rule, "Use the right counts."))[name][0], "FAIL")
        self.assertEqual(run(log=rep(LOG, rule, "Do not be careless with read failures and counts again."))[name][0], "FAIL")

    def test_sources_must_exist(self):
        name = "sources are real commits or existing files"
        self.assertEqual(run(log=rep(LOG, "| `248234ac` | K1 | - |\n| L3", "| `deadbee0` | K1 | - |\n| L3"))[name][0], "FAIL")
        self.assertEqual(run(log=rep(LOG, "`35e39d2c` | - | - |", "`no/such/file.md` | - | - |"))[name][0], "FAIL")
        self.assertEqual(run(commit=lambda h: None)[name][0], "PASS", "when git cannot answer, commits are not judged")

    def test_encoded_lessons_must_resolve_to_code(self):
        name = "encoded lessons point at code that contains the named check"
        self.assertEqual(run(log=rep(LOG, '"NEAR_FULL_MIN"; ', '"NO_SUCH_CONSTANT"; '))[name][0], "FAIL")
        self.assertEqual(run(log=rep(LOG, "`lib/deferral.py` \"def check\";", "`lib/no_such.py` \"def check\";"))[name][0], "FAIL")
        self.assertEqual(run(log=rep(LOG, "`lib/deferral.py` \"def check\";", "`CLAUDE.md` \"A12\";"))[name][0], "FAIL")
        self.assertEqual(run(log=rep(LOG, "| encoded | `lib/contactor_io.py` \"MAX_COUNT_GAP\"", "| encoded | -"))[name][0], "FAIL")

    def test_documented_lessons_must_point_at_a_file(self):
        name = "documented lessons point at an existing file"
        self.assertEqual(run(log=rep(LOG, "| documented | `CLAUDE.md` |", "| documented | `NO_SUCH.md` |"))[name][0], "FAIL")

    def test_repeats_must_name_an_earlier_learning_of_the_same_class(self):
        name = "a repeat names an earlier learning of the same class"
        self.assertEqual(run(log=rep(LOG, "| K5 | L6 |", "| K5 | L1 |"))[name][0], "FAIL")
        self.assertEqual(run(log=rep(LOG, "| K5 | L6 |", "| K5 | L99 |"))[name][0], "FAIL")
        self.assertEqual(run(log=rep(LOG, "| K5 | L6 |", "| K5 | L7 |"))[name][0], "FAIL")

    def test_classes_must_be_used_and_recurring_ones_need_a_fix(self):
        name = "every class is used, and recurring classes have a systemic fix that exists"
        self.assertEqual(run(log=LOG + "\n| unused | a class nobody used | - |")[name][0], "FAIL")
        self.assertEqual(run(log=rep(LOG, '`lib/deferral.py` "def check" |\n| blind-check', "- |\n| blind-check"))[name][0], "FAIL")
        self.assertEqual(run(log=rep(LOG, '"analysis plan checker tests"', '"a check nobody wrote"'))[name][0], "FAIL")

    def test_a_correction_recorded_in_a_deliverable_must_be_logged(self):
        name = "every correction recorded inside a deliverable is in the log"
        self.assertEqual(run(files=FILES + ["05-stakeholder-communication/some/new_doc.md"])[name][0], "FAIL")
        self.assertEqual(run(log=LOG.replace("references/metaphor_bank.md", "references/other.md"))[name][0], "FAIL")

    def test_real_scan_finds_the_known_corrections(self):
        self.assertGreaterEqual(len(FILES), 5)
        self.assertIn("02-documentation-knowledge/analysis-assumptions-log/assumptions.json", FILES)

    def test_risks_must_exist_and_materialised_risks_need_a_learning(self):
        name = "learnings link to plan risks, and every materialised risk has a learning"
        self.assertEqual(run(log=rep(LOG, "| K10 |", "| K77 |"))[name][0], "FAIL")
        self.assertEqual(run(log=LOG.replace("| K1 |", "| - |"))[name][0], "FAIL")
        r = run(plan=rep(PLAN, "| mitigated | `lib/deferral.py` |", "| materialised | `lib/deferral.py` |"), log=LOG.replace("| K9 |", "| - |"))[name]
        self.assertEqual(r[0], "FAIL")
        self.assertIn("K9 materialised", r[1])

    def test_retrospective_claims_must_cite_the_log(self):
        name = "what worked, what did not and surprises each cite the log"
        self.assertEqual(run(retro=rep(RETRO, "- A correction was itself wrong (L7).", "- A correction was itself wrong."))[name][0], "FAIL")
        self.assertEqual(run(retro=rep(RETRO, "(L7).", "(L77)."))[name][0], "FAIL")
        self.assertEqual(run(retro=rep(RETRO, "(L22).", "(L22).\n- The weather was unkind."))[name][0], "FAIL")
        self.assertEqual(run(retro=rep(RETRO, "- Injecting faults into a copy of the real data and writing a negative test for each check found real defects in our own gate and checkers (L9, L14, L16).", "- Everything went well."))[name][0], "FAIL")

    def test_the_class_table_is_derived_from_the_log(self):
        name = "lessons-by-class table equals the log"
        self.assertEqual(run(retro=rep(RETRO, "| doc-drift | 8 | 2 |", "| doc-drift | 7 | 2 |"))[name][0], "FAIL")
        self.assertEqual(run(retro=rep(RETRO, "| process | 2 |", "| surprise | 2 |"))[name][0], "FAIL")
        self.assertEqual(run(log=rep(LOG, "| K5 | L6 |", "| K5 | - |"))[name][0], "FAIL")

    def test_actions_are_owned_routed_and_cover_documented_and_open_lessons(self):
        name = "actions are owned, routed and cover every documented or open learning"
        self.assertEqual(run(retro=rep(RETRO, "| analyst | - | no deadline set | L22 |", "| the intern | - | no deadline set | L22 |"))[name][0], "FAIL")
        self.assertEqual(run(retro=rep(RETRO, "| data source facts |", "| nothing registered |"))[name][0], "FAIL")
        self.assertEqual(run(retro=rep(RETRO, "| no deadline set | L22 |", "| no deadline set | L99 |"))[name][0], "FAIL")
        self.assertEqual(run(retro=rep(RETRO, "| no deadline set | L22 | open |", "| no deadline set | - | open |"))[name][0], "FAIL")
        self.assertEqual(run(retro=rep(RETRO, "| no deadline set | L19 |", "| soon | L19 |"))[name][0], "FAIL")
        self.assertEqual(run(retro=rep(RETRO, "| A2 |", "| A3 |"))[name][0], "FAIL")

    def test_limits_must_be_stated(self):
        name = "limits are stated"
        start = RETRO.index("## Limits")
        self.assertEqual(run(retro=RETRO[:start] + "## Limits\n- Only one limit.\n")[name][0], "FAIL")
        self.assertEqual(run(retro=RETRO[:start])[name][0], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=1)
