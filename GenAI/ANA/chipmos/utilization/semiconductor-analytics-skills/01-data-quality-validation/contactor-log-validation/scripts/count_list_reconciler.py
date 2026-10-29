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
        "rows_gap_over_limit_kept (should be 0)": int((v["diff"] > cio.MAX_COUNT_GAP).sum()),
        "near_full_rows_kept (err_01 252-255, should be 0)": int(v["err_01"].between(cio.NEAR_FULL_MIN, 255).sum()),
    }


GAP_LOW, GAP_HIGH = 36, 44  # the constant gap seen from 2026-10-05 is 40, with a few readings at 39, 41 and 42


def gap_profile(df, window: int = 60, share: float = 0.9) -> dict:
    """Count minus ALL listed numbers (cleaned IDs plus out-of-range and duplicate tokens), per month, and where a constant gap starts.

    The start is the first reading from which at least `share` of the next `window` valid readings have a gap of
    GAP_LOW-GAP_HIGH. It describes the data; what the gap is (sites closed on purpose, or a cut-off list) is not
    established (open question A21).
    """
    v = df[df["valid"]].copy()
    v["gap"] = v["err_01"] - v["n_closed"] - v["n_oob"] - v["n_dup"]
    v["on"] = v["gap"].between(GAP_LOW, GAP_HIGH)
    months = {m: {"readings": len(g), "mean_count": round(float(g["err_01"].mean()), 2), "mean_list": round(float(g["n_closed"].mean()), 2)}
              for m, g in v.groupby(v["timestamp"].dt.strftime("%Y-%m"))}
    out = {"months": months, "start": None}
    roll = v["on"].rolling(window).mean().shift(-(window - 1))
    hit = roll[(roll >= share) & v["on"]]  # the starting reading itself must show the gap
    if len(hit):
        t0 = v.loc[hit.index[0], "timestamp"]
        after, before = v[v["timestamp"] >= t0], v[v["timestamp"] < t0]
        out.update(start=t0.strftime("%Y-%m-%d %H:%M"), share_after=round(float(after["on"].mean() * 100), 1),
                   share_before=round(float(before["on"].mean() * 100), 2) if len(before) else 0.0,
                   common=[(int(k), int(c)) for k, c in after["gap"].value_counts().head(5).items()])
    return out


def main():
    ap = argparse.ArgumentParser(description="Reconcile count vs list length")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--side", choices=["front", "rear", "both"], default="both")
    ap.add_argument("--start", default=cio.DEFAULT_START)
    ap.add_argument("--tolerance", type=int, default=0)
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN)
    ap.add_argument("--max-count-gap", type=int, default=cio.MAX_COUNT_GAP, help="0 disables the gap rule")
    args = ap.parse_args()

    for side in (cio.SIDES if args.side == "both" else [args.side]):
        res = reconcile(cio.load_side(side, args.data_dir, args.start, near_full_min=args.near_full_min, max_count_gap=args.max_count_gap), args.tolerance)
        print(f"\n=== {side.upper()} count vs list length ===")
        for k, v in res.items():
            print(f"{k:24s} {v}")
        if res["count_lt_list_pct"] == 0 and res["count_gt_list_pct"] > 0:
            print("NOTE: count is never below list length -> the list never lists more sites than the count says;")
            print("      the list length is trusted for the headline (A5) and the count gives the lower bound on availability.")
        gp = gap_profile(cio.load_side(side, args.data_dir, args.start, near_full_min=args.near_full_min, max_count_gap=args.max_count_gap))
        print("gap profile (count minus all listed numbers):")
        for m, g in gp["months"].items():
            print(f"  {m}: {g['readings']} valid readings, mean count {g['mean_count']} vs mean list {g['mean_list']}")
        if gp["start"]:
            print(f"  constant gap of {GAP_LOW}-{GAP_HIGH} starts {gp['start']}; after it {gp['share_after']}% of valid readings show it (before: {gp['share_before']}%)")
            print(f"  most common gap values after the start: " + ", ".join(f"{k} ({c})" for k, c in gp["common"]))
        else:
            print(f"  no constant gap of {GAP_LOW}-{GAP_HIGH} found")
        if res["near_full_rows_kept (err_01 252-255, should be 0)"]:
            print("NOTE: err_01 of 252-255 is a read failure - rerun without --near-full-min 0")


if __name__ == "__main__":
    main()
