"""
Detect debounced open/close events per site and group them into events.

Usage:
    python closure_events.py --side rear
    python closure_events.py --side front --window 7 --min-sites 2
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import contactor_io as cio  # noqa: E402


def detect_events(mat: pd.DataFrame, window: int = 5, group_min: int = 30) -> pd.DataFrame:
    state = mat.drop(columns="weight_min").astype(float)
    smooth = state.rolling(window, center=True, min_periods=1).median().astype(bool)
    diff = smooth.astype(int).diff().fillna(0)
    rows = []
    for site in diff.columns:
        for ts, d in diff[site][diff[site] != 0].items():
            rows.append({"timestamp": ts, "site": int(site), "type": "CLOSED" if d > 0 else "OPENED"})
    ev = pd.DataFrame(rows)
    if ev.empty:
        return ev
    ev = ev.sort_values("timestamp").reset_index(drop=True)
    ev["event_id"] = (ev["timestamp"].diff().dt.total_seconds().div(60).fillna(1e9) > group_min).cumsum()
    return ev


def block_members(site: int) -> set[int]:
    row, col = cio.site_row_col(site)
    r0, c0 = (row - 1) // 2 * 2 + 1, (col - 1) // 2 * 2 + 1
    return {(r - 1) * cio.COLS + c for r in (r0, r0 + 1) for c in (c0, c0 + 1)}


def aligned_share(sites: list[int]) -> float:
    """Share of sites whose whole aligned 2x2 block is in the event (1.0 = pure block events)."""
    s = set(sites)
    return sum(block_members(x) <= s for x in sites) / len(sites)


def summarise(ev: pd.DataFrame) -> pd.DataFrame:
    out = []
    for eid, g in ev.groupby("event_id"):
        for typ, gg in g.groupby("type"):
            sites = sorted(gg["site"])
            blocks = sorted({f"R{(cio.site_row_col(s)[0] + 1) // 2}C{(cio.site_row_col(s)[1] + 1) // 2}" for s in sites})
            shown = ",".join(map(str, sites[:10])) + (f" +{len(sites) - 10} more" if len(sites) > 10 else "")
            out.append({"start": gg["timestamp"].min(), "type": typ, "n_sites": len(sites),
                        "sites": shown, "n_blocks_2x2": len(blocks),
                        "block_aligned": round(aligned_share(sites), 2)})
    return pd.DataFrame(out).sort_values("start")


def main():
    ap = argparse.ArgumentParser(description="Closure event detector")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--side", choices=["front", "rear"], default="rear")
    ap.add_argument("--start", default=cio.DEFAULT_START)
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN, help="err_01 >= N (<256) is a read failure; 0 disables")
    ap.add_argument("--window", type=int, default=5, help="rolling-median window (samples)")
    ap.add_argument("--min-sites", type=int, default=1)
    ap.add_argument("--max-closed", type=int, default=100, help="ignore samples with more closed sites than this (implausible)")
    ap.add_argument("--allow-mismatch", action="store_true", help="keep samples where err_01 != list length")
    ap.add_argument("--max-rows", type=int, default=40)
    args = ap.parse_args()

    df = cio.load_side(args.side, args.data_dir, args.start, near_full_min=args.near_full_min)
    # events must come from consistent reads: a list that disagrees with err_01 is missing IDs and would
    # fake "opened" events; implausibly large sets are burst noise
    keep = df["valid"] & (df["n_closed"] <= args.max_closed)
    if not args.allow_mismatch:
        keep &= ~df["count_mismatch"]
    print(f"using {int(keep.sum())} of {int(df['valid'].sum())} valid samples (consistent, <= {args.max_closed} closed)")
    df = df.assign(valid=keep)
    ev = detect_events(cio.closed_matrix(df, args.side), args.window)
    if ev.empty:
        print("no events")
        return
    s = summarise(ev)
    s = s[s["n_sites"] >= args.min_sites]
    pd.set_option("display.width", 200, "display.max_colwidth", 60)
    print(f"\n=== {args.side.upper()} events (window={args.window}, {len(s)} rows, showing {args.max_rows}) ===")
    print(s.head(args.max_rows).to_string(index=False))
    print("\nevents by type:", s["type"].value_counts().to_dict(),
          "| median sites per event:", float(s["n_sites"].median()))


if __name__ == "__main__":
    main()
