"""
Sampling cadence and daily coverage for contactor logs.

Usage:
    python sampling_cadence_check.py
    python sampling_cadence_check.py --side front --expected-interval 4
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import contactor_io as cio  # noqa: E402


def cadence_by_day(df, expected_interval: float = 4.0):
    d = df.copy()
    d["day"] = d["timestamp"].dt.date
    d["gap"] = d["timestamp"].diff().dt.total_seconds().div(60)
    g = d.groupby("day").agg(
        samples=("timestamp", "count"),
        median_gap=("gap", "median"),
        max_gap=("gap", "max"),
    )
    g["expected"] = int(24 * 60 / expected_interval)
    g["coverage_pct"] = (g["samples"] / g["expected"] * 100).round(1)
    return g.round(1)


def main():
    ap = argparse.ArgumentParser(description="Sampling cadence / coverage check")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--side", choices=["front", "rear", "both"], default="both")
    ap.add_argument("--start", default=cio.DEFAULT_START)
    ap.add_argument("--expected-interval", type=float, default=4.0, help="minutes")
    args = ap.parse_args()

    for side in (cio.SIDES if args.side == "both" else [args.side]):
        rep = cadence_by_day(cio.load_side(side, args.data_dir, args.start), args.expected_interval)
        print(f"\n=== {side.upper()} cadence ===")
        print(rep.to_string())
        print(f"days: {len(rep)}  mean coverage: {rep['coverage_pct'].mean():.1f}%  worst max gap: {rep['max_gap'].max()} min")


if __name__ == "__main__":
    main()
