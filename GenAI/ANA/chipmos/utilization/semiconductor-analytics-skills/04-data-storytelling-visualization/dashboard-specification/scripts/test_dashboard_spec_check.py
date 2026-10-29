"""
Unit tests for dashboard_spec_check.py: each test breaks one thing in the real spec (or schema) and expects
the matching check to fail, so a pass on the real spec means something. The SQLite copy and the backtest
are built once.

Usage:
    python test_dashboard_spec_check.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dashboard_spec_check as dsc  # noqa: E402
import build_dashboard_db as bdb  # noqa: E402
import contactor_io as cio  # noqa: E402

SPEC = dsc.DEFAULT_SPEC.read_text(encoding="utf-8")
SCHEMA = bdb.SCHEMA_SQL.read_text(encoding="utf-8")
YAML = dsc.METRIC_YAML.read_text(encoding="utf-8")
CON = bdb.build(":memory:")
BACKTEST = dsc.ab.backtest()
HEADLINE = {s: cio.weighted_availability(cio.load_side(s)) * 100 for s in cio.SIDES}

NAMES = ["schema not duplicated in the spec", "panels consistent with schema, metrics and alerts",
         "every query runs and returns what the tag declares", "headline and closed-now panels match the analysis",
         "alerts backtested, tolerable and actionable", "rejected-rule numbers equal the backtest", "no stale terms",
         "panel groups cover answer, diagnosis, detail and capture health", "schema statuses equal the loader and recency statuses",
         "no unfilled placeholders", "every schema table is named in the data model section", "refresh and retention stated"]


def run(spec=SPEC, schema=SCHEMA, yaml=YAML):
    return {n: (s, d) for n, s, d in dsc.check(spec, schema, yaml, CON, BACKTEST, HEADLINE)}


def rep(text, old, new):
    assert old in text, old
    return text.replace(old, new, 1)


class TestDashboardSpecCheck(unittest.TestCase):
    def test_real_spec_has_no_failures(self):
        self.assertEqual([n for n, (s, _) in run().items() if s == "FAIL"], [])

    def test_inline_schema_fails(self):
        self.assertEqual(run(SPEC + "\nCREATE TABLE copy (x int);")["schema not duplicated in the spec"][0], "FAIL")

    def test_missing_table_in_data_model_fails(self):
        self.assertEqual(run(rep(SPEC, "`closure_episodes`, ", ""))["every schema table is named in the data model section"][0], "FAIL")

    def test_panel_source_not_in_schema_fails(self):
        self.assertEqual(run(rep(SPEC, "capacity_summary.availability | none | front", "capacity_summary.no_such_column | none | front"))["panels consistent with schema, metrics and alerts"][0], "FAIL")

    def test_unknown_metric_fails(self):
        self.assertEqual(run(rep(SPEC, "| site_availability | capacity_summary.availability | none | rear", "| made_up_metric | capacity_summary.availability | none | rear"))["panels consistent with schema, metrics and alerts"][0], "FAIL")

    def test_oee_panel_outside_blocked_group_fails(self):
        self.assertEqual(run(rep(SPEC, "| P13 | blocked |", "| P13 | answer |"))["panels consistent with schema, metrics and alerts"][0], "FAIL")

    def test_blocked_panel_must_say_blocked(self):
        self.assertEqual(run(rep(SPEC, "OEE: BLOCKED until", "OEE is pending until"))["panels consistent with schema, metrics and alerts"][0], "FAIL")

    def test_threshold_naming_an_undefined_alert_fails(self):
        self.assertEqual(run(rep(SPEC, "| CAP_LOW alert |", "| NO_SUCH_ALERT alert |"))["panels consistent with schema, metrics and alerts"][0], "FAIL")

    def test_data_health_panel_reading_equipment_data_fails(self):
        self.assertEqual(run(rep(SPEC, "equipment_daily_metrics.fail_pct | DQ_FAIL_DAY", "closure_events.n_sites | DQ_FAIL_DAY"))["panels consistent with schema, metrics and alerts"][0], "FAIL")

    def test_missing_capture_health_panels_fails(self):
        s = SPEC.replace("| data-health |", "| diagnosis |")
        self.assertEqual(run(s)["panel groups cover answer, diagnosis, detail and capture health"][0], "FAIL")

    def test_broken_query_and_column_declaration_fail(self):
        self.assertEqual(run(rep(SPEC, "SELECT side, ci_low, ci_high, availability_low FROM", "SELECT side, ci_lo, ci_high, availability_low FROM"))["every query runs and returns what the tag declares"][0], "FAIL")
        self.assertEqual(run(rep(SPEC, "-- panel: P4 | columns: side, closed_now", "-- panel: P4 | columns: side, closed"))["every query runs and returns what the tag declares"][0], "FAIL")
        self.assertEqual(run(rep(SPEC, "-- panel: P6 | columns: grid_row, grid_col, share_recent, status | rows: 256", "-- panel: P6 | columns: grid_row, grid_col, share_recent, status | rows: 999"))["every query runs and returns what the tag declares"][0], "FAIL")

    def test_headline_panel_must_match_the_analysis(self):
        s = rep(SPEC, "SELECT availability FROM capacity_summary WHERE side = 'front';", "SELECT availability FROM capacity_summary WHERE side = 'rear';")
        self.assertEqual(run(s)["headline and closed-now panels match the analysis"][0], "FAIL")

    def test_alert_rate_must_equal_the_backtest(self):
        self.assertEqual(run(rep(SPEC, "| 1.75 | 0.88 |", "| 0.10 | 0.88 |"))["alerts backtested, tolerable and actionable"][0], "FAIL")

    def test_page_severity_needs_a_low_rate(self):
        s = rep(SPEC, "| 1.75 | 0.88 | ticket |", "| 1.75 | 0.88 | page |")
        self.assertEqual(run(s)["alerts backtested, tolerable and actionable"][0], "FAIL")

    def test_rejected_rule_numbers_are_checked(self):
        self.assertEqual(run(rep(SPEC, "17.06 per week", "5.00 per week"))["rejected-rule numbers equal the backtest"][0], "FAIL")

    def test_stale_term_fails(self):
        self.assertEqual(run(SPEC + "\nSee site_state_events.")["no stale terms"][0], "FAIL")

    def test_schema_statuses_must_equal_the_loader(self):
        bad = rep(SCHEMA, "'READ_FAIL_GAP',", "")
        self.assertEqual(run(schema=bad)["schema statuses equal the loader and recency statuses"][0], "FAIL")

    def test_placeholder_fails(self):
        self.assertEqual(run(SPEC + "\n[REQUIRED]")["no unfilled placeholders"][0], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=1)
