"""
Tests for context_bundler.py and context_check.py: each test breaks one thing in the real package (or a
synthetic pipeline folder) and expects the matching check to fail.

Usage:
    python test_context_check.py
"""

import copy
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import context_bundler as cb  # noqa: E402
import context_check as cc  # noqa: E402

PKG = cb.build_package()
HIST = cb.build_package(with_history=True)
FRESH = PKG["meta"]["state"]


def run(pkg=PKG, **kw):
    kw.setdefault("fresh", FRESH)
    return {n: (s, d) for n, s, d in cc.check(pkg, **kw)}


def mut(pkg, old, new, layer=None, every=False):
    """Copy of the package with `old` replaced (once, or everywhere with every=True) in the first layer that has it."""
    p = copy.deepcopy(pkg)
    for k, v in p["layers"].items():
        if (layer is None or k == layer) and old in v:
            p["layers"][k] = v.replace(old, new) if every else v.replace(old, new, 1)
            break
    else:
        raise AssertionError(old)
    p["text"] = "\n\n".join(p["layers"].values())
    return p


def meta(pkg, **kw):
    p = copy.deepcopy(pkg)
    p["meta"].update(kw)
    return p


class TestHelpers(unittest.TestCase):
    def test_token_estimate_is_pessimistic(self):
        self.assertEqual(cb.estimate_tokens("a" * 300), 100)
        self.assertEqual(cb.estimate_tokens("a" * 301), 101)

    def test_trim_changelog_keeps_only_the_latest(self):
        y = "version: 2\nchangelog:\n  - {version: 2}\n  - {version: 1}\ncontract:\n  x: 1"
        text, old = cb.trim_changelog(y)
        self.assertIn("{version: 2}", text)
        self.assertNotIn("{version: 1}", text)
        self.assertEqual(old, ["  - {version: 1}"])
        self.assertIn("contract:", text)
        self.assertEqual(cb.trim_changelog("a: 1"), ("a: 1", []))

    def test_pipeline_info_rejects_missing_old_wrong_and_failed_runs(self):
        state = {"data_mtime": dt.datetime(2026, 10, 2).timestamp(), "sides": {"front": {"availability": 91.32}}}

        def with_run(summary):
            d = tempfile.TemporaryDirectory()
            run_dir = Path(d.name) / "out" / "pipeline" / "x"
            run_dir.mkdir(parents=True)
            (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            return d, cb.pipeline_info(state, Path(d.name))

        with tempfile.TemporaryDirectory() as d:
            self.assertIn("no pipeline run", cb.pipeline_info(state, Path(d))["problems"][0])
        good = {"run": "20261029_120000", "steps": {"qa": "ok"}, "availability_pct": {"front": 91.32}}
        d, info = with_run(good)
        self.assertEqual(info["problems"], [])
        d.cleanup()
        d, info = with_run({**good, "run": "20260930_120000"})
        self.assertTrue(any("older than the newest data" in p for p in info["problems"]))
        d.cleanup()
        d, info = with_run({**good, "availability_pct": {"front": 90.0}})
        self.assertTrue(any("differs from the recomputed" in p for p in info["problems"]))
        d.cleanup()
        d, info = with_run({**good, "steps": {"qa": "FAILED(1)"}})
        self.assertTrue(any("not ok" in p for p in info["problems"]))
        d.cleanup()
        d, info = with_run({**good, "run": "20261029_120000_2"})
        self.assertEqual(info["problems"], [], "a second run in the same second has a suffix")
        d.cleanup()
        d, info = with_run({**good, "status": "failed"})
        self.assertTrue(any("status is failed" in p for p in info["problems"]))
        d.cleanup()
        d, info = with_run({"steps": {}})
        self.assertTrue(any("no readable run time" in p for p in info["problems"]))
        d.cleanup()


class TestContextCheck(unittest.TestCase):
    def test_real_package_has_no_failures_with_a_real_recomputation(self):
        r = {n: (s, d) for n, s, d in cc.check(PKG)}
        self.assertEqual([n for n, (s, _) in r.items() if s == "FAIL"], [])

    def test_the_package_is_orienting_and_in_budget(self):
        self.assertLessEqual(PKG["meta"]["tokens"], 8000)
        for h in ("## Status", "## Must not", "## Next steps", "## Reproduce"):
            self.assertIn(h, PKG["layers"]["header"])
        self.assertNotIn("history", PKG["layers"])

    def test_placeholder_fails(self):
        self.assertEqual(run(mut(PKG, "## Status", "[" + "REQUIRED]\n## Status"))["no unfilled placeholders"][0], "FAIL")

    def test_header_must_have_every_section_of_the_template(self):
        name = "the header has every section the template names"
        self.assertEqual(run(mut(PKG, "## Reproduce", "## How"))[name][0], "FAIL")
        self.assertEqual(run(mut(PKG, "Read in this order", "Start here"))[name][0], "FAIL")
        self.assertEqual(run(template=cb.TEMPLATE.read_text(encoding="utf-8") + "\n## Glossary\n")[name][0], "FAIL")

    def test_status_must_equal_the_requirements_and_the_plan(self):
        name = "the status line equals the requirements and the plan"
        self.assertEqual(run(mut(PKG, "): 3 met", "): 9 met"))[name][0], "FAIL")
        self.assertEqual(run(mut(PKG, "P4 blocked", "P4 met"))[name][0], "FAIL")

    def test_every_assumption_must_be_present_with_its_status_and_marked(self):
        name = "every assumption is present with its status; unconfirmed ones are marked"
        row = next(l for l in PKG["layers"]["rules"].splitlines() if l.startswith("| A13 |"))
        self.assertEqual(run(mut(PKG, row + "\n", ""))[name][0], "FAIL")
        self.assertEqual(run(mut(PKG, row, row.replace("| OPEN |", "| CONFIRMED |")))[name][0], "FAIL")
        self.assertEqual(run(mut(PKG, "- A13 (OPEN)", "- A13x (OPEN)"))[name][0], "FAIL")
        self.assertEqual(run(mut(PKG, "none (unconfirmed)", "-"))[name][0], "FAIL")
        confirmed = next(l for l in PKG["layers"]["rules"].splitlines() if l.startswith("| A1 |"))
        self.assertEqual(run(mut(PKG, confirmed, confirmed.replace("process owner (chat)", "none (unconfirmed)")))[name][0], "FAIL")

    def test_must_not_rules_follow_the_status_files(self):
        name = "must-not rules agree with the status files and no business figures leak"
        self.assertEqual(run(mut(PKG, "the cost estimate is deferred", "the cost estimate is fine"))[name][0], "FAIL")
        self.assertEqual(run(mut(PKG, "partial OEE", "partial figure"))[name][0], "FAIL")
        self.assertEqual(run(mut(PKG, "hypothesis (A13)", "fact (A13)"))[name][0], "FAIL")
        self.assertEqual(run(mut(PKG, "## Reproduce", "The repair saves $5,000.\n## Reproduce"))[name][0], "FAIL")

    def test_headline_must_equal_a_recomputation(self):
        name = "the headline in the package equals a recomputation from the data"
        self.assertEqual(run(mut(PKG, "| front | 91.32%", "| front | 90.10%"))[name][0], "FAIL")
        self.assertEqual(run(mut(PKG, "| rear | 96.07% | 95.64%", "| rear | 96.07% | 94.00%"))[name][0], "FAIL")
        self.assertEqual(run(mut(PKG, "20 of 256", "2 of 256"))[name][0], "FAIL")
        self.assertEqual(run(mut(PKG, "| rear |", "| aft |"))[name][0], "FAIL")

    def test_a_stale_pipeline_fails_unless_the_caller_skips_it(self):
        name = "the pipeline summary is fresh and agrees"
        stale = meta(PKG, pipeline={"run": "x", "problems": ["pipeline run x is older than the newest data file"]})
        self.assertEqual(run(stale)[name][0], "FAIL")
        self.assertEqual(run(stale, check_pipeline=False)[name][0], "PASS")

    def test_commit_must_exist_and_appear_in_the_header(self):
        name = "the commit is recorded and exists"
        self.assertEqual(run(meta(PKG, commit="unknown"))[name][0], "FAIL")
        bogus = mut(meta(PKG, commit="deadbee0"), "`" + PKG["meta"]["commit"] + "`", "`deadbee0`")
        self.assertEqual(run(bogus)[name][0], "FAIL")

    def test_reproduce_commands_must_exist(self):
        name = "the reproduce commands point at existing scripts"
        self.assertEqual(run(mut(PKG, "daily_pipeline.py", "no_such_pipeline.py"))[name][0], "FAIL")
        self.assertEqual(run(mut(PKG, "`python ", "`run ", every=True))[name][0], "FAIL")

    def test_open_decisions_must_equal_the_log_and_the_markers(self):
        name = "open decisions equal the assumptions log and the markers"
        row = next(l for l in PKG["layers"]["state"].splitlines() if l.startswith("| A13 |"))
        self.assertEqual(run(mut(PKG, row + "\n", ""))[name][0], "FAIL")
        self.assertEqual(run(mut(PKG, "Totals: 9 assumptions", "Totals: 4 assumptions"))[name][0], "FAIL")

    def test_qa_state_must_equal_the_signoff_and_the_waivers(self):
        name = "the QA state equals the sign-off and the waivers"
        self.assertEqual(run(mut(PKG, "READY FOR REVIEW - **not signed off**", "SIGNED OFF"))[name][0], "FAIL")
        first = json.loads(cb.WAIVERS.read_text(encoding="utf-8"))[0]["check"]
        self.assertEqual(run(mut(PKG, f"| {first} |", "| something else |"))[name][0], "FAIL")

    def test_superseded_wording_only_in_the_history_layer(self):
        name = "superseded wording appears only in the history layer"
        self.assertEqual(run(mut(PKG, "## Reproduce", "Weighting is not imputed.\n## Reproduce"))[name][0], "FAIL")
        r = run(HIST, fresh=HIST["meta"]["state"])
        self.assertEqual(r[name][0], "PASS")
        self.assertIn("across dropped readings and gaps", HIST["layers"]["history"], "the history keeps the old wording on purpose")

    def test_history_exists_only_when_requested_and_comes_last(self):
        name = "layers are ordered and history exists only when requested"
        self.assertEqual(run(HIST, fresh=HIST["meta"]["state"])[name][0], "PASS")
        self.assertEqual(run(meta(HIST, with_history=False), fresh=HIST["meta"]["state"])[name][0], "FAIL")
        p = copy.deepcopy(PKG)
        p["layers"]["history"] = "# HISTORY\nold"
        p["text"] = "\n\n".join(p["layers"].values())
        self.assertEqual(run(p)[name][0], "FAIL")
        swapped = copy.deepcopy(PKG)
        swapped["layers"] = {"rules": PKG["layers"]["rules"], "header": PKG["layers"]["header"], "state": PKG["layers"]["state"]}
        swapped["text"] = "\n\n".join(swapped["layers"].values())
        self.assertEqual(run(swapped)[name][0], "FAIL")

    def test_the_budget_is_enforced_and_pessimistic(self):
        name = "rules and state fit the budget (chars/3)"
        self.assertEqual(run(meta(PKG, budget_tokens=1000))[name][0], "FAIL")
        self.assertEqual(cb.build_package(budget_tokens=500)["meta"]["problems"][-1][:11], "over budget")

    def test_no_secrets_emails_private_paths_or_raw_rows(self):
        name = "no secrets, emails, private paths or raw data rows"
        for bad in ("api_key = abc123", "write to someone@example.com", "see /home/someone/dat", "2026-09-01 00:04:00,12,[3, 4]",
                    "token AKIAABCDEFGHIJKLMNOP", "key sk-abcdefghijklmnopqrstuvwxyz"):
            self.assertEqual(run(mut(PKG, "## Reproduce", bad + "\n## Reproduce"))[name][0], "FAIL", bad)


if __name__ == "__main__":
    unittest.main(verbosity=1)
