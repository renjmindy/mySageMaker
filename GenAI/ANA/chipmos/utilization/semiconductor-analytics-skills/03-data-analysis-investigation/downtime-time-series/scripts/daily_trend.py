"""
Daily availability trend, robust anomaly flags and hour-of-day profile.

Usage:
    python daily_trend.py --side front
    python daily_trend.py --side front --z 3.5
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import contactor_io as cio  # noqa: E402


def daily_series(df: pd.DataFrame) -> pd.DataFrame:
    v = df[df["valid"]].copy()
    v["day"] = pd.to_datetime(v["timestamp"].dt.date)
    g = v.groupby("day").apply(
        lambda x: pd.Series({
            "availability_pct": (1 - (x["n_closed"] * x["weight_min"]).sum() / (256 * x["weight_min"].sum())) * 100,
            "median_closed": x["n_closed"].median(),
        }),
        include_groups=False,
    )
    g["rolling7_pct"] = g["availability_pct"].rolling(7, min_periods=3).mean()
    return g.round(2)


def robust_flags(s: pd.Series, z: float = 3.5) -> pd.Series:
    med = s.median()
    mad = (s - med).abs().median() or 1e-9
    return (0.6745 * (s - med) / mad).abs() > z


def main():
    ap = argparse.ArgumentParser(description="Daily availability trend")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--side", choices=["front", "rear"], default="front")
    ap.add_argument("--start", default=cio.DEFAULT_START)
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN, help="err_01 >= N (<256) is a read failure; 0 disables")
    ap.add_argument("--z", type=float, default=3.5)
    args = ap.parse_args()

    df = cio.load_side(args.side, args.data_dir, args.start, near_full_min=args.near_full_min)
    ts = daily_series(df)
    ts["anomaly"] = robust_flags(ts["availability_pct"], args.z).map({True: "<-- check", False: ""})
    print(f"\n=== {args.side.upper()} daily availability ===")
    print(ts.to_string())

    v = df[df["valid"]]
    print("\n=== mean closed by hour of day ===")
    print(v.groupby(v["timestamp"].dt.hour)["n_closed"].mean().round(1).to_string())


if __name__ == "__main__":
    main()
