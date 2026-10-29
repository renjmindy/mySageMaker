"""
Tests for plan_check.py: each test breaks one thing in the real plan (or its sources) and expects the matching
check to fail.

Usage:
    python test_plan_check.py
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_check as pc  # noqa: E402

PLAN = pc.PLAN.read_text(encoding="utf-8")
SCOPE = pc.SCOPE.read_text(encoding="utf-8")
REQS = pc.REQS.read_text(encoding="utf-8")
MAP = pc.MAP.read_text(encoding="utf-8")
REGISTRY = json.loads(pc.REGISTRY.read_text(encoding="utf-8"))


def run(plan=PLAN, scope=SCOPE, reqs=REQS, mp=MAP, registry=REGISTRY):
    return {n: (s, d) for n, s, d in pc.check(plan, scope, reqs, mp, registry)}


def rep(text, old, new):
    assert old in text, old
    return text.replace(old, new, 1)


class TestDerivedStatus(unittest.TestCase):
    def test_worst_status_wins(self):
        self.assertEqual(pc.derived_status(["met", "met"]), "met")
        self.assertEqual(pc.derived_status(["met", "partial"]), "partial")
        self.assertEqual(pc.derived_status(["partial", "deferred"]), "deferred")
        self.assertEqual(pc.derived_status(["deferred", "blocked", "met"]), "blocked")


class TestPlanCheck(unittest.TestCase):
    def test_real_plan_has_no_failures_and_warns_about_missing_dates(self):
        r = run()
        self.assertEqual([n for n, (s, _) in r.items() if s == "FAIL"], [])
        self.assertEqual(r["phases have a target date"][0], "WARN")

    def test_a_real_date_clears_the_warning_for_that_phase(self):
        r = run(plan=rep(PLAN, "no deadline set | met |", "2026-12-01 | met |"))
        self.assertIn("7 phase", r["phases have a target date"][1])

    def test_placeholder_money_and_stale_rule_fail(self):
        self.assertEqual(run(plan=PLAN + "\n[" + "REQUIRED]")["no unfilled placeholders"][0], "FAIL")
        self.assertEqual(run(plan=PLAN + "\nThe repair saves $5,000.")["no money or throughput figures while impact-quantification is deferred"][0], "FAIL")
        self.assertEqual(run(scope=SCOPE + "\nIn scope only if an owner is named.")["no stale terms"][0], "FAIL")
        self.assertEqual(run(plan=PLAN + "\nAsk the handler/MES owner.")["no stale terms"][0], "FAIL")

    def test_every_requirement_is_in_exactly_one_phase(self):
        name = "every requirement is in exactly one phase"
        self.assertEqual(run(plan=rep(PLAN, "| R7 | real business parameters", "| - | real business parameters"))[name][0], "FAIL")
        self.assertEqual(run(plan=rep(PLAN, "| R2 | P1 exit", "| R2, R1 | P1 exit"))[name][0], "FAIL")
        self.assertEqual(run(plan=rep(PLAN, "| R1 | P0 exit", "| R99 | P0 exit"))[name][0], "FAIL")

    def test_status_is_derived_not_typed(self):
        name = "phase status equals the status derived from its requirements"
        self.assertEqual(run(plan=rep(PLAN, "| no deadline set | blocked |", "| no deadline set | met |"))[name][0], "FAIL")
        self.assertEqual(run(plan=rep(PLAN, "| no deadline set | partial |", "| no deadline set | met |"))[name][0], "FAIL")
        # and it follows the requirements: if R6 became partial the plan's 'blocked' would be wrong
        self.assertEqual(run(reqs=rep(REQS, "| blocked | A10, A11:", "| partial | A10, A11:"))[name][0], "FAIL")

    def test_phase_owner_entry_criteria_and_exit_check(self):
        name = "phases have an owner role, entry criteria and a resolvable exit check"
        self.assertEqual(run(plan=rep(PLAN, "| process owner | no deadline set | met |", "| the intern | no deadline set | met |"))[name][0], "FAIL")
        self.assertEqual(run(plan=rep(PLAN, "| contactor CSVs delivered |", "| |"))[name][0], "FAIL")
        self.assertEqual(run(plan=rep(PLAN, "scripts/data_gate.py` \"no missing days\"", "scripts/nope.py` \"no missing days\""))[name][0], "FAIL")
        self.assertEqual(run(plan=rep(PLAN, '"no missing days"', '"a check that does not exist"'))[name][0], "FAIL")
        self.assertEqual(run(plan=rep(PLAN, "| no deadline set | met |", "| soon | met |"))[name][0], "FAIL")

    def test_dependencies_need_a_real_role_and_a_registered_question(self):
        name = "dependencies have a real provider role and a registered question"
        self.assertEqual(run(plan=rep(PLAN, "| data / capture owner | run-state", "| the vendor | run-state"))[name][0], "FAIL")
        self.assertEqual(run(plan=rep(PLAN, "| A11 | missing |", "| A99 | missing |"))[name][0], "FAIL")
        no_p4 = "\n".join(l for l in PLAN.splitlines() if not (l.startswith("| ") and "| P4 |" in l and "missing" in l))
        self.assertEqual(run(plan=no_p4)[name][0], "FAIL")

    def test_estimates_need_a_basis_and_every_phase(self):
        name = "every phase has a sized, justified and calibrated estimate"
        self.assertEqual(run(plan=rep(PLAN, "| cleaning rules and definitions need owner decisions (A3-A20) |", "| |"))[name][0], "FAIL")
        self.assertEqual(run(plan="\n".join(l for l in PLAN.splitlines() if not l.startswith("| P7 | - |")))[name][0], "FAIL")
        self.assertEqual(run(plan=rep(PLAN, "| P0 | - | cleaning rules", "| P0 | XL | cleaning rules"))[name][0], "FAIL")

    def test_risks_need_valid_fields_and_evidence(self):
        name = "risks are complete, owned and evidenced"
        self.assertEqual(run(plan=rep(PLAN, "unflagged near-full bands | high |", "unflagged near-full bands | extreme |"))[name][0], "FAIL")
        self.assertEqual(run(plan=rep(PLAN, "| data / capture owner | materialised |", "| nobody | materialised |"))[name][0], "FAIL")
        self.assertEqual(run(plan=rep(PLAN, "`01-data-quality-validation/contactor-log-validation/assets/validation_report_sep_oct_2026.md`", "`no/such/evidence.md`"))[name][0], "FAIL")
        self.assertEqual(run(plan=rep(PLAN, "| analyst | mitigated | `.gitignore` |", "| analyst | mitigated | `nothing.txt` |"))[name][0], "FAIL")

    def test_the_register_must_include_materialised_risks(self):
        self.assertEqual(run(plan=PLAN.replace("| materialised |", "| open |"))["the register includes risks that materialised"][0], "FAIL")

    def test_next_actions(self):
        name = "next actions are ordered, routed and unblock something"
        self.assertEqual(run(plan=rep(PLAN, "| 2 | Answer the planned", "| 3 | Answer the planned"))[name][0], "FAIL")
        self.assertEqual(run(plan=rep(PLAN, "| production planner | A11 | the basis", "| the intern | A11 | the basis"))[name][0], "FAIL")
        self.assertEqual(run(plan=rep(PLAN, "| A11 | the basis for time-based OEE |", "| A99 | the basis for time-based OEE |"))[name][0], "FAIL")
        self.assertEqual(run(plan=rep(PLAN, "| A11 | the basis for time-based OEE |", "| A11 | |"))[name][0], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=1)
