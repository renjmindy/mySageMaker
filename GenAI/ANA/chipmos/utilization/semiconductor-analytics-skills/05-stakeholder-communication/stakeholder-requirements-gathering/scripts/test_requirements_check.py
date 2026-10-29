"""
Tests for requirements_check.py and open_questions.py. Each check test breaks one thing in the real brief,
requirements, stakeholder map, registry or assumptions log and expects the matching check to fail; the generator
tests use small temporary trees.

Usage:
    python test_requirements_check.py
"""

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import open_questions as oq  # noqa: E402
import requirements_check as rc  # noqa: E402

BRIEF = rc.BRIEF.read_text(encoding="utf-8")
REQS = rc.REQS.read_text(encoding="utf-8")
MAP = rc.MAP.read_text(encoding="utf-8")
GUIDE = rc.GUIDE.read_text(encoding="utf-8")
SKILL = rc.SKILL.read_text(encoding="utf-8")
REGISTRY = json.loads(oq.REGISTRY.read_text(encoding="utf-8"))
LOG = json.loads(oq.LOG.read_text(encoding="utf-8"))
MARKERS = oq.scan_markers()
OPEN = "[" + "OPEN"


def run(brief=BRIEF, reqs=REQS, mp=MAP, guide=GUIDE, skill=SKILL, registry=REGISTRY, log=LOG, markers=MARKERS):
    block = oq.generate(markers, log, registry)
    return {n: (s, d) for n, s, d in rc.check(brief, reqs, mp, guide, skill, registry, log, markers, block)}


def rep(text, old, new):
    assert old in text, old
    return text.replace(old, new, 1)


class TestRequirementsCheck(unittest.TestCase):
    def test_real_requirements_work_has_no_failures(self):
        self.assertEqual([n for n, (s, _) in run().items() if s == "FAIL"], [])

    def test_a_draft_brief_and_unnamed_roles_are_warnings_not_passes(self):
        r = run()
        self.assertEqual(r["brief confirmation"][0], "WARN")
        self.assertEqual(r["roles have named people"][0], "WARN")

    def test_placeholder_money_and_stale_terms_fail(self):
        self.assertEqual(run(brief=BRIEF + "\n[" + "REQUIRED]")["no unfilled placeholders"][0], "FAIL")
        self.assertEqual(run(brief=BRIEF + "\nSaves $5,000.")["no money or throughput figures while impact-quantification is deferred"][0], "FAIL")
        self.assertEqual(run(skill=SKILL + "\nAgree: chronic-site list weekly, alert on new cluster")["no stale terms"][0], "FAIL")

    def test_brief_fields_scope_and_counts(self):
        self.assertEqual(run(brief=rep(BRIEF, "- **Business question**:", "- Question:"))["brief has every field and section"][0], "FAIL")
        self.assertEqual(run(brief=BRIEF.replace("07/30", "an earlier day"))["scope names sides, period and the trial-run exclusion"][0], "FAIL")
        self.assertEqual(run(brief=rep(BRIEF, "11 confirmed", "12 confirmed"))["assumption counts in the brief match the log"][0], "FAIL")

    def test_a_confirmed_brief_needs_a_name_and_date(self):
        self.assertEqual(run(brief=rep(BRIEF, "**Status**: DRAFT - not confirmed.", "**Status**: CONFIRMED."))["brief confirmation"][0], "FAIL")
        ok = rep(rep(BRIEF, "**Status**: DRAFT - not confirmed.", "**Status**: CONFIRMED."), "**Confirmed by**: " + OPEN + "] on " + OPEN + "].", "**Confirmed by**: A. Name on 2026-11-01.")
        self.assertEqual(run(brief=ok)["brief confirmation"][0], "PASS")

    def test_stakeholder_map_rules(self):
        blank = "\n".join((l.rsplit("|", 2)[0] + "| |") if l.startswith("| process owner |") and "(A1-A20)" in l else l for l in MAP.splitlines())
        self.assertEqual(run(mp=blank)["stakeholder map has roles with decision rights"][0], "FAIL")
        self.assertEqual(run(mp=rep(MAP, '"Process owner" in the assumptions log (`source: process owner (chat)`) means', '"Process owner" is'))["process owner is a defined role, not just a label"][0], "FAIL")
        self.assertEqual(run(mp=rep(MAP, "| analysis document and metric definitions | analyst | process owner |", "| analysis document and metric definitions | analyst | nobody |"))["every accountable role exists"][0], "FAIL")

    def test_requirement_table_rules(self):
        name = "requirements are complete, owned, traceable and honest about status"
        cases = {
            "duplicate id": rep(REQS, "| R2 |", "| R1 |"),
            "bad priority": rep(REQS, "| must | equipment / maintenance lead | `04-data-storytelling-visualization/visualization-builder/scripts/site_heatmap.py`", "| urgent | equipment / maintenance lead | `04-data-storytelling-visualization/visualization-builder/scripts/site_heatmap.py`"),
            "unknown role": rep(REQS, "| must | production planner |", "| must | the intern |"),
            "missing deliverable": rep(REQS, "`04-data-storytelling-visualization/visualization-builder/scripts/site_heatmap.py`", "`04-data-storytelling-visualization/visualization-builder/scripts/nope.py`"),
            "acceptance script missing": rep(REQS, "`04-data-storytelling-visualization/visualization-builder/scripts/viz_check.py`", "`04-data-storytelling-visualization/visualization-builder/scripts/no_check.py`"),
            "check name not in the script": rep(REQS, '"numbers match the analysis scripts"', '"a check that does not exist"'),
            "met but blocked": rep(REQS, "| met | - |\n| R2", "| met | something |\n| R2"),
            "not met without a reason": rep(REQS, "| partial | alert owners and channels are open |", "| partial | - |"),
            "deferred without status.json": rep(REQS, "| deferred | status.json: business parameters not supplied |", "| deferred | waiting |"),
            "blocked without an id or missing data": rep(REQS, "| blocked | A10, A11: run / idle history, output, good-unit and cycle-time data missing |", "| blocked | waiting for people |"),
            "unknown assumption id": rep(REQS, "A10, A11: run / idle history", "A99: run / idle history"),
        }
        for label, text in cases.items():
            self.assertEqual(run(reqs=text)[name][0], "FAIL", label)

    def test_success_criteria_must_cover_every_must(self):
        name = "success criteria point at requirements and cover every must"
        self.assertEqual(run(brief=BRIEF.replace("- SC6 (R10): every release has an independent sign-off and a passing QA run.", ""))[name][0], "FAIL")
        self.assertEqual(run(brief=rep(BRIEF, "- SC1 (R1)", "- SC1 (R99)"))[name][0], "FAIL")

    def test_guide_sync_and_routing(self):
        self.assertEqual(run(guide=GUIDE.replace("| A11 | OPEN |", "| A11 | CLOSED |"))["interview guide matches the log and the open markers"][0], "FAIL")
        reg = copy.deepcopy(REGISTRY); reg["assumptions"].pop("A19")
        self.assertEqual(run(registry=reg)["every open item is routed to a role"][0], "FAIL")
        self.assertEqual(run(markers={**MARKERS, "new/place/new_deliverable.md": 3})["every open item is routed to a role"][0], "FAIL")
        reg = copy.deepcopy(REGISTRY); reg["static"][0]["ask"] = "the intern"
        self.assertEqual(run(registry=reg)["registry asks only roles that exist"][0], "FAIL")

    def test_an_answered_question_must_leave_the_registry_and_the_guide(self):
        log = copy.deepcopy(LOG)
        for a in log:
            if a["id"] == "A9":
                a["status"] = "CONFIRMED"
        r = run(log=log)
        self.assertEqual(r["every open item is routed to a role"][0], "FAIL")  # A9 is still registered although answered
        self.assertNotIn("| A9 |", oq.generate(MARKERS, log, REGISTRY))


class TestOpenQuestions(unittest.TestCase):
    def test_scan_counts_filled_files_and_skips_templates_references_and_the_guide(self):
        d = Path(tempfile.mkdtemp())
        try:
            (d / "assets").mkdir(); (d / "references").mkdir()
            (d / "assets" / "owners_sep_oct_2026.md").write_text(f"x {OPEN}] y {OPEN}]")
            (d / "assets" / "thing_template.md").write_text(f"{OPEN}]")
            (d / "assets" / "interview_guide.md").write_text(f"{OPEN}]")
            (d / "references" / "ref.md").write_text(f"{OPEN}]")
            (d / "SKILL.md").write_text(f"{OPEN}]")
            self.assertEqual(oq.scan_markers(d), {"assets/owners_sep_oct_2026.md": 2})
        finally:
            shutil.rmtree(d)

    def test_every_real_open_item_is_routed_and_the_guide_is_current(self):
        self.assertEqual({k: v for k, v in oq.coverage(MARKERS, LOG, REGISTRY).items() if v}, {})
        self.assertEqual(oq.block_of(GUIDE), oq.generate(MARKERS, LOG, REGISTRY))

    def test_the_guide_never_carries_its_own_markers(self):
        self.assertNotIn(OPEN, oq.generate(MARKERS, LOG, REGISTRY))


if __name__ == "__main__":
    unittest.main(verbosity=1)
