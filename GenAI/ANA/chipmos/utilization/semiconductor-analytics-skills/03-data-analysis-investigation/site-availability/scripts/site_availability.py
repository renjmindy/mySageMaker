"""
Time-weighted site availability per side and day, with lower/upper range.

  availability_high : closed = cleaned list length   (optimistic; list under-reports)
  availability_low  : closed = max(err_01, list len) (pessimistic; err_01 never < list)

Usage:
    python site_availability.py
    python site_availability.py --output ../../../out/availability
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import contactor_io as cio  # noqa: E402


def _avail(closed: pd.Series, w: pd.Series) -> float:
    return float(1 - (closed * w).sum() / (cio.SITES_PER_SIDE * w.sum())) if w.sum() else float("nan")


def daily_availability(df: pd.DataFrame) -> pd.DataFrame:
    v = df[df["valid"]].copy()
    v["day"] = v["timestamp"].dt.date
    v["closed_upper"] = v[["err_01", "n_closed"]].max(axis=1).clip(upper=cio.SITES_PER_SIDE)
    rows = []
    for day, g in v.groupby("day"):
        rows.append({
            "day": day,
            "samples": len(g),
            "mean_closed": round(float(g["n_closed"].mean()), 1),
            "availability_high_pct": round(_avail(g["n_closed"], g["weight_min"]) * 100, 2),
            "availability_low_pct": round(_avail(g["closed_upper"], g["weight_min"]) * 100, 2),
        })
    return pd.DataFrame(rows).set_index("day")


def overall(df: pd.DataFrame) -> dict:
    v = df[df["valid"]]
    upper = v[["err_01", "n_closed"]].max(axis=1).clip(upper=cio.SITES_PER_SIDE)
    return {
        "valid_samples": len(v),
        "availability_high_pct": round(_avail(v["n_closed"], v["weight_min"]) * 100, 2),
        "availability_low_pct": round(_avail(upper, v["weight_min"]) * 100, 2),
        "unweighted_pct": round((1 - v["n_closed"].mean() / cio.SITES_PER_SIDE) * 100, 2),
    }


def main():
    ap = argparse.ArgumentParser(description="Site availability per side/day")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--start", default=cio.DEFAULT_START)
    ap.add_argument("--end", default=None)
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN, help="err_01 >= N (<256) is a read failure; 0 disables")
    ap.add_argument("--output", help="CSV prefix for per-day tables")
    ap.add_argument("--quiet-days", action="store_true", help="skip per-day tables")
    args = ap.parse_args()

    res = {}
    for side in cio.SIDES:
        df = cio.load_side(side, args.data_dir, args.start, args.end, near_full_min=args.near_full_min)
        res[side] = overall(df)
        if not args.quiet_days:
            print(f"\n=== {side.upper()} daily availability ===")
            print(daily_availability(df).to_string())
        if args.output:
            daily_availability(df).to_csv(f"{args.output}_{side}.csv")
    print("\n=== OVERALL (time-weighted) ===" + (f"  [near-full >= {args.near_full_min} excluded]" if args.near_full_min else ""))
    print(pd.DataFrame(res).T.to_string())
    both_hi = sum(r["availability_high_pct"] for r in res.values()) / 2
    print(f"\ncombined 512-site view (mean of sides, high): {both_hi:.2f}%")


if __name__ == "__main__":
    main()
