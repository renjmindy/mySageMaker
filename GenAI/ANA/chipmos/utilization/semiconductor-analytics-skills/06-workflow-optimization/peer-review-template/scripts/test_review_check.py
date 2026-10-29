"""
Tests for independent_recompute.py, review_prep.py and review_check.py. The recompute is checked against
hand-computed arithmetic on a tiny synthetic dataset; the review checks break one rule at a time in the real
(NOT REVIEWED) record and in a synthetic COMPLETE record.

Usage:
    python test_review_check.py
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import independent_recompute as ir  # noqa: E402
import review_check as rc  # noqa: E402
import review_prep as rp  # noqa: E402

R = {k: p.read_text(encoding="utf-8") for k, p in {
    "review": rc.REVIEW, "response": rc.RESPONSE, "checklist": rc.CHECKLIST, "stakeholders": rc.pc.MAP, "learnings": rc.lc.LOG,
    "runner": rc.RUNNER, "signoff": rc.SIGNOFF}.items()}
R["own_texts"] = [f.read_text(encoding="utf-8") for f in rc.OWN_FILES]
FRESH = rc.cb.fresh_state()
INDEP = ir.recompute()
CLAIMS = rp.claims(FRESH)
# These tests check the CHECK LOGIC, so they work on a record synced to today's data; whether the stored record is
# current is reported by the QA gate (a stale record is a FAIL there, not a crash here). No test types a data value.
R["review"] = rp.write(R["review"], rp.generate(FRESH, INDEP), CLAIMS)
C1 = CLAIMS[0]
V1 = C1["value"]
LABEL1 = f"{C1['id']} | {C1['claim']}: {V1}"
OK = lambda ref, root=None: "ok"


def shift(v, d):
    return f"{float(v) + d:.2f}"


def rep(text, old, new):
    assert old in text, old
    return text.replace(old, new, 1)


def run(git=OK, **over):
    a = {**R, "fresh": FRESH, "indep": INDEP, **over}
    return {n: (s, d) for n, s, d in rc.check(a["review"], a["response"], a["checklist"], a["stakeholders"], a["learnings"], a["runner"],
                                               a["signoff"], a["own_texts"], a["fresh"], a["indep"], git=git)}


def completed():
    """Texts of a finished, approving review by a named independent reviewer."""
    r = R["review"]
    r = rep(r, "**Status**: NOT REVIEWED", "**Status**: COMPLETE")
    r = rep(r, "Reviewer: not yet named", "Reviewer: Dana Reviewer (reviewer)")
    r = rep(r, "Date reviewed: -", "Date reviewed: 2026-11-05")
    r = rep(r, "Verdict: pending", "Verdict: approve")
    for c in CLAIMS:
        dif = " / ".join(["+0.00"] * len(rc.numbers(c["value"])))
        r = rep(r, f"| {c['id']} | {c['claim']}: {c['value']} |  |  |  |", f"| {c['id']} | {c['claim']}: {c['value']} | {c['value']} | {dif} | yes |")
    for item in rc.pc.table(R["checklist"]):
        r = rep(r, f"| {item['id']} | | |", f"| {item['id']} | pass | |")
    return {"review": r, "stakeholders": rep(R["stakeholders"], "| reviewer | [OPEN] |", "| reviewer | Dana Reviewer |"),
            "signoff": rep(rep(R["signoff"], "Reviewer (not the author): [OPEN]", "Reviewer (not the author): Dana Reviewer"),
                           "**Status**: READY FOR REVIEW - **not signed off**", "**Status**: SIGNED OFF -")}


C = completed()


def runc(git=OK, **over):
    return run(git=git, **{**C, **over})


class TestIndependentRecompute(unittest.TestCase):
    def test_cleaning_rules_and_arithmetic_on_a_hand_computed_dataset(self):
        front = ["Timestamp,err_01,err_02",
                 "2026/08/31 23:56,200,1",           # before the start: excluded
                 "2026/09/01 00:00,2,1;2",           # valid, closed 2, 4 min
                 "2026/09/01 00:00,9,3;4",           # duplicate timestamp: the first row wins
                 "2026/09/01 00:04,256,1",           # read failure
                 "2026/09/01 00:08,0,N/A",           # valid, nothing closed, 4 min
                 "2026/09/01 00:12,5,N/A",           # unreadable list
                 "2026/09/01 00:16,253,1;2;3",       # near-full band is a read failure
                 "2026/09/01 00:20,100,1;2",         # count - listed > 50
                 "2026/09/01 00:24,3,1;1;999;3",     # duplicate and out-of-range IDs ignored: closed 2, next row 16 min later: capped at 15
                 "2026/09/01 00:40,0,N/A"]           # last row gets the median gap (4)
        rear = ["Timestamp,err_01,err_02", "2026/09/01 00:00,2,257;258", "2026/09/01 00:04,1,3"]
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "contactor_20260901.csv").write_text("\n".join(front) + "\n", encoding="utf-8")
            (Path(d) / "contactor_rear_20260901.csv").write_text("\n".join(rear) + "\n", encoding="utf-8")
            res = ir.recompute(d)
        # front: valid weights 4, 4, 15, 4 = 27 minutes; closed x minutes = 2*4 + 0 + 2*15 + 0 = 38
        self.assertAlmostEqual(res["front"]["high"], (1 - 38 / (256 * 27)) * 100, places=9)
        # lower bound uses max(count, listed): 2*4 + 0 + 3*15 + 0 = 53
        self.assertAlmostEqual(res["front"]["low"], (1 - 53 / (256 * 27)) * 100, places=9)
        self.assertEqual(res["front"]["valid"], 4)
        # rear: the position 3 is outside 257-512 so it is ignored; 2*4 closed over 8 minutes
        self.assertAlmostEqual(res["rear"]["high"], (1 - 8 / (256 * 8)) * 100, places=9)
        self.assertAlmostEqual(res["rear"]["low"], (1 - 12 / (256 * 8)) * 100, places=9)

    def test_agrees_with_the_loader_on_the_real_data(self):
        for s, v in INDEP.items():
            self.assertAlmostEqual(round(v["high"], 2), FRESH["sides"][s]["availability"], places=2)
            self.assertAlmostEqual(round(v["low"], 2), FRESH["sides"][s]["lower_bound"], places=2)

    def test_it_does_not_import_the_loader(self):
        src = (Path(__file__).resolve().parent / "independent_recompute.py").read_text(encoding="utf-8")
        self.assertNotIn("import contactor_io", src)
        self.assertNotIn("import pandas", src)


class TestReviewPrep(unittest.TestCase):
    def test_claims_cover_headline_bound_range_and_closed_now_for_both_sides(self):
        self.assertEqual([c["id"] for c in CLAIMS], [f"C{i}" for i in range(1, 9)])
        self.assertTrue(any("range" in c["claim"] for c in CLAIMS))

    def test_deliverables_exclude_the_review_records(self):
        names = [Path(p).name for p in rp.deliverables()]
        self.assertTrue(names)
        self.assertFalse([n for n in names if n.startswith(("peer_review_", "review_response_"))])

    def test_write_refreshes_the_block_and_author_values_but_keeps_reviewer_cells(self):
        text = rep(C["review"], f"| {LABEL1} | {V1} | +0.00 | yes |", "| C1 | stale | 0.00 | -1.00 | no |")
        new = rp.write(text, rp.generate(FRESH, INDEP), CLAIMS)
        self.assertIn(f"| {LABEL1} | 0.00 | -1.00 | no |", new)
        self.assertEqual(rp.block_of(new), rp.generate(FRESH, INDEP))

    def test_the_block_rows_are_not_rewritten_by_the_table_sync(self):
        new = rp.write(R["review"], rp.generate(FRESH, INDEP), CLAIMS)
        self.assertEqual(rp.block_of(new), rp.generate(FRESH, INDEP))


class TestKit(unittest.TestCase):
    def test_real_record_has_no_failure_and_warns_that_nobody_reviewed(self):
        r = run()
        self.assertEqual([n for n, (s, _) in r.items() if s == "FAIL"], [])
        self.assertEqual(r["a reviewer who is not the author holds the reviewer role"][0], "WARN")

    def test_placeholder_money_and_stale_terms(self):
        self.assertEqual(run(review=R["review"] + "\n[" + "REQUIRED]")["no unfilled placeholders"][0], "FAIL")
        self.assertEqual(run(review=R["review"] + "\nThe repair saves $5,000.")["no money or throughput figures while impact-quantification is deferred"][0], "FAIL")
        self.assertEqual(run(own_texts=R["own_texts"] + ["Review within 2 working days."])["no stale terms in the skill and its templates"][0], "FAIL")

    def test_checklist_must_cover_every_class_and_hard_rule(self):
        name = "the checklist covers every defect class and hard rule, and its enforcement exists"
        cl = R["checklist"]
        self.assertEqual(run(checklist=cl.replace("| process |", "| other |"))[name][0], "FAIL")
        self.assertEqual(run(checklist=cl.replace("private-data", "privacy"))[name][0], "FAIL")
        self.assertEqual(run(checklist=cl.replace("over-claim, hypothesis", "over-claim"))[name][0], "FAIL")

    def test_checklist_enforcement_must_exist(self):
        name = "the checklist covers every defect class and hard rule, and its enforcement exists"
        cl = R["checklist"]
        self.assertEqual(run(checklist=rep(cl, '"test_missing_day_is_caught"', '"test_no_such_thing"'))[name][0], "FAIL")
        self.assertEqual(run(checklist=rep(cl, "scripts/independent_recompute.py` \"def recompute\"", "scripts/nope.py` \"def recompute\""))[name][0], "FAIL")
        self.assertEqual(run(checklist=rep(cl, "record as unchecked: known gap (learning L22), no unit tests for those scripts", "-"))[name][0], "FAIL")
        self.assertEqual(run(checklist=rep(cl, "| the A8 sensitivity in the analysis document: is its size what the process owner confirmed |", "| |"))[name][0], "FAIL")

    def test_each_class_needs_a_test_the_qa_gate_runs(self):
        name = "every defect class has a test that the QA gate runs"
        self.assertEqual(run()[name][0], "PASS")
        self.assertEqual(run(runner=R["runner"].replace("test_data_gate", "test_something_else"))[name][0], "FAIL")

    def test_record_header(self):
        name = "the record header is valid"
        self.assertEqual(run(review=rep(R["review"], "**Status**: NOT REVIEWED", "**Status**: DONE"))[name][0], "FAIL")
        self.assertEqual(run(review=rep(R["review"], "Date reviewed: -", "Date reviewed: 2026-11-05"))[name][0], "FAIL")
        self.assertEqual(run(review=rep(R["review"], "Verdict: pending", "Verdict: fine"))[name][0], "FAIL")
        self.assertEqual(run(review=rep(R["review"], "0.01 percentage points", "a bit"))[name][0], "FAIL")
        self.assertEqual(run(**{**C, "review": rep(C["review"], "Date reviewed: 2026-11-05", "Date reviewed: -")})[name][0], "FAIL")

    def test_commit_must_exist_and_be_in_this_history(self):
        name = "the reviewed commit exists and is part of this history"
        self.assertEqual(run(git=lambda r, root=None: "missing")[name][0], "FAIL")
        self.assertEqual(run(git=lambda r, root=None: "not-ancestor")[name][0], "FAIL")
        self.assertEqual(run(git=lambda r, root=None: None)[name][0], "PASS")
        self.assertEqual(run(review=R["review"].replace("Release under review: commit", "Release under review: ref"))[name][0], "FAIL")

    def test_preparation_must_be_current_and_the_recompute_must_agree(self):
        name = "the author's preparation is current"
        self.assertEqual(run(review=rep(R["review"], f"| front | {INDEP['front']['high']:.4f} |", "| front | 1.0000 |"))[name][0], "FAIL")
        moved = {**FRESH, "sides": {**FRESH["sides"], "front": {**FRESH["sides"]["front"], "closed_now": 99}}}
        self.assertEqual(run(fresh=moved)[name][0], "FAIL")
        off = {**INDEP, "front": {**INDEP["front"], "high": INDEP["front"]["high"] - 0.5}}
        self.assertEqual(run(indep=off)["the recompute without the loader agrees with the loader-based headline"][0], "FAIL")


class TestCompletedReview(unittest.TestCase):
    def test_a_complete_approving_review_has_no_failure_or_warning(self):
        r = runc()
        self.assertEqual([(n, d) for n, (s, d) in r.items() if s in ("FAIL", "WARN")], [])

    def test_the_reviewer_must_be_independent_and_hold_the_role(self):
        name = "a reviewer who is not the author holds the reviewer role"
        self.assertEqual(runc(review=rep(C["review"], "Reviewer: Dana Reviewer (reviewer)", "Reviewer: Claude (analyst)"))[name][0], "FAIL")
        self.assertEqual(runc(review=rep(C["review"], "Reviewer: Dana Reviewer (reviewer)", "Reviewer: Someone Else (reviewer)"))[name][0], "FAIL")
        self.assertEqual(runc(review=rep(C["review"], "Reviewer: Dana Reviewer (reviewer)", "Reviewer: not yet named"))[name][0], "FAIL")
        self.assertEqual(runc(stakeholders=R["stakeholders"])[name][0], "FAIL")

    def test_reproduction_must_be_complete_and_arithmetic_correct(self):
        name = "the reviewer's reproduction matches the claims and its arithmetic"
        row = f"| {LABEL1} | {V1} | +0.00 | yes |"
        r = C["review"]
        self.assertEqual(runc(review=rep(r, row, f"| {LABEL1} |  |  |  |"))[name][0], "FAIL")
        self.assertEqual(runc(review=rep(r, row, f"| {C1['id']} | {C1['claim']}: {shift(V1, -0.5)} | {V1} | +0.00 | yes |"))[name][0], "FAIL")
        self.assertEqual(runc(review=rep(r, row, f"| {LABEL1} | {shift(V1, 0.08)} | +0.00 | yes |"))[name][0], "FAIL")
        self.assertEqual(runc(review=rep(r, row, f"| {LABEL1} | {shift(V1, 0.18)} | +0.18 | yes |"))[name][0], "FAIL")
        self.assertEqual(runc(review=rep(r, row, f"| {LABEL1} | {V1} | +0.00 | no |"))[name][0], "FAIL")
        c5 = CLAIMS[4]
        row5 = f"| {c5['id']} | {c5['claim']}: {c5['value']} | {c5['value']} | +0.00 / +0.00 | yes |"
        self.assertEqual(runc(review=rep(r, row5, row5.replace("| C5 |", "| C55 |")))[name][0], "FAIL")

    def test_a_number_outside_the_tolerance_needs_a_blocking_finding_that_cites_it(self):
        name = "the reviewer's reproduction matches the claims and its arithmetic"
        row = f"| {LABEL1} | {V1} | +0.00 | yes |"
        off = rep(C["review"], row, f"| {LABEL1} | {shift(V1, 0.18)} | +0.18 | no |")
        self.assertEqual(runc(review=off)[name][0], "FAIL")
        review = rep(off, "|---|---|---|---|---|---|\n\nNo findings: the review has not been done.", f"|---|---|---|---|---|---|\n| F1 | C1 does not reproduce | blocking | C1: {shift(V1, 0.18)} vs {V1} | find the cause | open |\n")
        review = rep(review, "Verdict: approve", "Verdict: reject")
        r = runc(review=review)
        self.assertEqual(r[name][0], "PASS")
        self.assertEqual(r["the verdict follows from the findings"][0], "PASS")

    def test_checklist_outcomes(self):
        name = "checklist outcomes are complete and consistent with the findings"
        r = C["review"]
        self.assertEqual(runc(review=rep(r, "| RC3 | pass | |", "| RC3 | | |"))[name][0], "FAIL")
        self.assertEqual(runc(review=rep(r, "| RC3 | pass | |", "| RC3 | unchecked | |"))[name][0], "FAIL")
        self.assertEqual(runc(review=rep(r, "| RC3 | pass | |", "| RC3 | fail | numbers differ |"))[name][0], "FAIL")
        self.assertEqual(runc(review=rep(r, "| RC3 | pass | |", "| RC3 | maybe | |"))[name][0], "FAIL")
        self.assertEqual(runc(review=rep(r, "| RC3 | pass | |", "| RC99 | pass | |"))[name][0], "FAIL")
        self.assertEqual(runc(review=rep(r, "| RC12 | pass | |", "| RC12 | unchecked | known gap L22 |"))[name][0], "PASS")

    def test_findings_must_be_complete_answered_and_traced(self):
        name = "findings are complete, answered and traced to a change"
        base = "|---|---|---|---|---|---|\n\nNo findings: the review has not been done."
        def with_row(row, response=""):
            review = rep(C["review"], base, "|---|---|---|---|---|---|\n" + row + "\n")
            return {"review": rep(review, "Verdict: approve", "Verdict: approve with changes"), "response": R["response"] + response}
        good = "| F1 | Chart label is unclear | non-blocking | viz tile | rename it | fixed |"
        self.assertEqual(runc(**with_row(good))[name][0], "FAIL")  # fixed, but no response
        resp = "\n| F1 | fixed, label renamed | the tile label | `06-workflow-optimization/peer-review-template/SKILL.md` | no |"
        self.assertEqual(runc(**with_row(good, resp))[name][0], "PASS")
        self.assertEqual(runc(**with_row(good, resp.replace("SKILL.md", "NOPE.md")))[name][0], "FAIL")
        self.assertEqual(runc(**with_row(good, resp.replace("fixed, label", "label")))[name][0], "FAIL")
        self.assertEqual(runc(**with_row(good.replace("| fixed |", "| verified |"), resp))[name][0], "FAIL")
        self.assertEqual(runc(**with_row(good.replace("| fixed |", "| verified |"), resp.replace("| no |", "| yes |")))[name][0], "PASS")
        self.assertEqual(runc(**with_row(good.replace("non-blocking", "serious"), resp))[name][0], "FAIL")
        self.assertEqual(runc(**with_row(good.replace("| rename it |", "|  |"), resp))[name][0], "FAIL")
        self.assertEqual(runc(**with_row(good, resp + "\n| F9 | fixed | x | `SKILL.md` | no |"))[name][0], "FAIL")

    def test_the_verdict_follows_from_the_findings(self):
        name = "the verdict follows from the findings"
        base = "|---|---|---|---|---|---|\n\nNo findings: the review has not been done."
        def verdict(row, v):
            review = rep(C["review"], base, "|---|---|---|---|---|---|\n" + row + "\n")
            return runc(review=rep(review, "Verdict: approve", f"Verdict: {v}"))[name][0]
        block = "| F1 | Over-claim | blocking | RC6 text | remove it | open |"
        minor = "| F2 | Naming | non-blocking | tile | rename | open |"
        self.assertEqual(verdict(block, "approve"), "FAIL")
        self.assertEqual(verdict(block, "approve with changes"), "FAIL")
        self.assertEqual(verdict(block, "reject"), "PASS")
        self.assertEqual(verdict(minor, "approve"), "FAIL")
        self.assertEqual(verdict(minor, "approve with changes"), "PASS")
        self.assertEqual(verdict(minor, "reject"), "FAIL")
        self.assertEqual(runc()[name][0], "PASS")
        self.assertEqual(runc(review=rep(C["review"], "Verdict: approve", "Verdict: pending"))[name][0], "FAIL")

    def test_the_signoff_must_agree_with_the_review(self):
        name = "the QA sign-off agrees with the review record"
        self.assertEqual(run()[name][0], "PASS")
        self.assertEqual(run(signoff=rep(R["signoff"], "**not signed off**", "SIGNED OFF"))[name][0], "FAIL")
        self.assertEqual(run(signoff=rep(R["signoff"], "Reviewer (not the author): [OPEN]", "Reviewer (not the author): Dana Reviewer"))[name][0], "FAIL")
        self.assertEqual(runc(signoff=R["signoff"])[name][0], "FAIL")
        self.assertEqual(runc(signoff=rep(C["signoff"], "Dana Reviewer", "Someone Else"))[name][0], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=1)
