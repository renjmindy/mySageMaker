"""
Per-day read-failure report for contactor logs.

Counts samples by status (OK, NA_ZERO, READ_FAIL_256, NA_NONZERO) and flags days
whose failure rate exceeds a threshold.

Usage:
    python read_failure_detector.py
    python read_failure_detector.py --data-dir ../../../dat --side rear --fail-pct 5
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import contactor_io as cio  # noqa: E402


def failure_report(df, fail_pct: float = 5.0):
    d = df.assign(day=df["timestamp"].dt.date)
    tab = d.pivot_table(index="day", columns="status", values="err_01", aggfunc="count", fill_value=0)
    cols = ["OK", "NA_ZERO", "READ_FAIL_256", "READ_FAIL_NEAR_FULL", "NA_NONZERO"]
    for col in cols:
        if col not in tab:
            tab[col] = 0
    tab["total"] = tab[cols].sum(axis=1)
    tab["fail_pct"] = (tab[["READ_FAIL_256", "READ_FAIL_NEAR_FULL", "NA_NONZERO"]].sum(axis=1) / tab["total"] * 100).round(2)
    tab["flag"] = tab["fail_pct"].map(lambda p: "REVIEW" if p >= fail_pct else "ok")
    return tab[["total", "OK", "NA_ZERO", "READ_FAIL_256", "READ_FAIL_NEAR_FULL", "NA_NONZERO", "fail_pct", "flag"]]


def main():
    ap = argparse.ArgumentParser(description="Per-day read-failure report")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--side", choices=["front", "rear", "both"], default="both")
    ap.add_argument("--start", default=cio.DEFAULT_START)
    ap.add_argument("--fail-pct", type=float, default=5.0)
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN, help="err_01 >= N (<256) is a read failure; 0 disables")
    ap.add_argument("--output", help="optional CSV path")
    args = ap.parse_args()

    sides = list(cio.SIDES) if args.side == "both" else [args.side]
    for side in sides:
        rep = failure_report(cio.load_side(side, args.data_dir, args.start, near_full_min=args.near_full_min), args.fail_pct)
        print(f"\n=== {side.upper()} read failures (threshold {args.fail_pct}%) ===")
        print(rep.to_string())
        print(f"overall fail rate: {(rep['READ_FAIL_256'].sum() + rep['READ_FAIL_NEAR_FULL'].sum() + rep['NA_NONZERO'].sum()) / rep['total'].sum() * 100:.2f}%")
        if args.output:
            rep.to_csv(f"{args.output}.{side}.csv")


if __name__ == "__main__":
    main()
