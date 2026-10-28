"""
Reconcile err_01 (reported count) with the cleaned list length.

The list length is authoritative; this script quantifies how often and by how
much the count disagrees, and whether the offset is systematic.

Usage:
    python count_list_reconciler.py
    python count_list_reconciler.py --side front --tolerance 2
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import contactor_io as cio  # noqa: E402


def reconcile(df, tolerance: int = 0):
    v = df[df["valid"]].copy()
    v["diff"] = v["err_01"] - v["n_closed"]
    return {
        "valid_rows": len(v),
        "mismatch_rows": int((v["diff"] != 0).sum()),
        "mismatch_pct": round(float((v["diff"] != 0).mean() * 100), 2),
        "beyond_tolerance_pct": round(float((v["diff"].abs() > tolerance).mean() * 100), 2),
        "count_gt_list_pct": round(float((v["diff"] > 0).mean() * 100), 2),
        "count_lt_list_pct": round(float((v["diff"] < 0).mean() * 100), 2),
        "mean_signed_diff": round(float(v["diff"].mean()), 3),
        "max_abs_diff": int(v["diff"].abs().max()),
        "near_full_rows_kept (err_01 252-255, should be 0)": int(v["err_01"].between(cio.NEAR_FULL_MIN, 255).sum()),
    }


def main():
    ap = argparse.ArgumentParser(description="Reconcile count vs list length")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--side", choices=["front", "rear", "both"], default="both")
    ap.add_argument("--start", default=cio.DEFAULT_START)
    ap.add_argument("--tolerance", type=int, default=0)
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN)
    args = ap.parse_args()

    for side in (cio.SIDES if args.side == "both" else [args.side]):
        res = reconcile(cio.load_side(side, args.data_dir, args.start, near_full_min=args.near_full_min), args.tolerance)
        print(f"\n=== {side.upper()} count vs list length ===")
        for k, v in res.items():
            print(f"{k:24s} {v}")
        if res["count_lt_list_pct"] == 0 and res["count_gt_list_pct"] > 0:
            print("NOTE: count is never below list length -> the list under-reports closures (IDs lost in the screen read);")
            print("      list length is a LOWER BOUND. Consider reporting a range using err_01 as the upper bound.")
        if res["near_full_rows_kept (err_01 252-255, should be 0)"]:
            print("NOTE: err_01 of 252-255 is a read failure - rerun without --near-full-min 0")


if __name__ == "__main__":
    main()
