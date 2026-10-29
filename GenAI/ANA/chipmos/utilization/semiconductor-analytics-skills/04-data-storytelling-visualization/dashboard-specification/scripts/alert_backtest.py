"""
Backtest the dashboard's alert rules on the history, so every alert has a known false-alarm rate.

Chosen rules
  CAP_LOW     daily capacity below (median - 2 SD) of the previous 28 days (needs >= 14 prior days)
  GROUP_LONG  an aligned group (>= 4 sites, block alignment >= 0.9) reaches 72 hours closed
  DQ_FAIL_DAY a day with >= 10% of readings dropped
  DQ_STALE    a day with a gap of more than 30 minutes between readings
Rejected rules (kept so the reasoning is checkable)
  BASELINE    daily capacity below the observed average (front 91%, rear 96%)
  GROUP_ANY   any aligned group (>= 4 sites, >= 30 min) starts

The backtest is IN-SAMPLE (rules were looked at on this same data) and covers about 4.6 weeks:
treat the rates as orders of magnitude, not guarantees.

Usage:
    python alert_backtest.py
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "lib"))
for sub in ("03-data-analysis-investigation/closure-event-root-cause/scripts", "03-data-analysis-investigation/downtime-time-series/scripts"):
    sys.path.insert(0, str(ROOT / sub))
import closure_events as ce  # noqa: E402
import contactor_io as cio  # noqa: E402
import daily_trend as dt  # noqa: E402

BASELINES = {"front": 91.0, "rear": 96.0}


def backtest(data_dir=None) -> dict:
    res: dict = {}
    for side in cio.SIDES:
        df = cio.load_side(side, data_dir)
        days = df["timestamp"].dt.normalize().nunique()
        weeks = days / 7
        s = dt.daily_series(df)["availability_pct"]
        out = res.setdefault(side, {})

        fired, evaluated = 0, 0
        for i in range(14, len(s)):
            base = s.iloc[max(0, i - 28):i]
            evaluated += 1
            fired += int(s.iloc[i] < base.median() - 2 * base.std())
        out["CAP_LOW"] = {"alerts": fired, "per_week": round(fired / (evaluated / 7), 2), "unit": "days"}

        keep = df["valid"] & (df["n_closed"] <= 100) & ~df["count_mismatch"]
        ev = ce.group_events(ce.closure_episodes(cio.closed_matrix(df.assign(valid=keep), side)))
        aligned = ev[(ev["n_sites"] >= 4) & (ev["block_aligned"] >= 0.9)]
        long_n = int((aligned["duration_min"] >= 72 * 60).sum())
        out["GROUP_LONG"] = {"alerts": long_n, "per_week": round(long_n / weeks, 2), "unit": "groups"}
        any_n = int((aligned["duration_min"] >= 30).sum())
        out["GROUP_ANY"] = {"alerts": any_n, "per_week": round(any_n / weeks, 2), "unit": "groups"}

        fail = (1 - df.groupby(df["timestamp"].dt.date)["valid"].mean()) * 100
        n = int((fail >= 10).sum())
        out["DQ_FAIL_DAY"] = {"alerts": n, "per_week": round(n / weeks, 2), "unit": "days"}
        gap = df["timestamp"].diff().dt.total_seconds().div(60)
        n = int(df["timestamp"][gap > 30].dt.date.nunique())
        out["DQ_STALE"] = {"alerts": n, "per_week": round(n / weeks, 2), "unit": "days"}

        n = int((s < BASELINES[side]).sum())
        out["BASELINE"] = {"alerts": n, "per_week": round(n / weeks, 2), "unit": "days"}
        out["_days"] = days
    return res


def main():
    argparse.ArgumentParser(description="Alert backtest").parse_args()
    res = backtest()
    for side, rules in res.items():
        print(f"== {side} ({rules['_days']} days)")
        for k, v in rules.items():
            if k != "_days":
                print(f"  {k:12s} {v['alerts']:>3d} {v['unit']:6s} {v['per_week']:>5.2f} per week")


if __name__ == "__main__":
    main()
