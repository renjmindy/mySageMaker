"""
Rank sites by closure share, add a recency status, cluster adjacent closed sites, show a Pareto.

Period share alone can mislead: a site fixed mid-period still looks "chronic". The recency status
compares the last N days (default 7, ending at the last valid reading) with the days before:

    PERSISTENT   closed >= 50% of the last N days and of the days before
    NEW          closed >= 50% of the last N days, < 20% before (recently broke)
    CURRENT      closed >= 50% of the last N days, otherwise
    INTERMITTENT closed 10-50% of the last N days
    RESOLVED     closed >= 10% over the period but < 10% in the last N days (fixed / gone)

Usage:
    python chronic_sites.py --side front
    python chronic_sites.py --side rear --top 15 --recent-days 7
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import contactor_io as cio  # noqa: E402


def closure_share(mat: pd.DataFrame) -> pd.Series:
    w = mat["weight_min"].to_numpy()
    closed = mat.drop(columns="weight_min").to_numpy().astype(float)
    return pd.Series((closed * w[:, None]).sum(axis=0) / w.sum(),
                     index=mat.drop(columns="weight_min").columns, name="closed_share")


def window_share(mat: pd.DataFrame, start=None, end=None) -> pd.Series:
    """Closure share over [start, end) of the matrix index (empty window -> zeros)."""
    sub = mat
    if start is not None:
        sub = sub[sub.index >= start]
    if end is not None:
        sub = sub[sub.index < end]
    if sub.empty:
        return pd.Series(0.0, index=mat.drop(columns="weight_min").columns)
    return closure_share(sub)


def recency_status(period: float, recent: float, prior: float) -> str:
    """Status of one site from its period, recent-window and prior-window closure shares."""
    if recent >= 0.5:
        if prior >= 0.5:
            return "PERSISTENT"
        return "NEW" if prior < 0.2 else "CURRENT"
    if recent >= 0.1:
        return "INTERMITTENT"
    return "RESOLVED" if period >= 0.1 else "-"


def classify(share: float, chronic: float = 0.5, frequent: float = 0.1) -> str:
    return "chronic" if share >= chronic else "frequent" if share >= frequent else "occasional"


def clusters(sites: list[int]) -> list[list[int]]:
    """Connected components under 4-neighbour adjacency on the 16-column grid."""
    remaining = set(sites)
    out = []
    while remaining:
        stack = [remaining.pop()]
        comp = []
        while stack:
            s = stack.pop()
            comp.append(s)
            row, col = cio.site_row_col(s)
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                r, c = row + dr, col + dc
                if 1 <= r <= 32 and 1 <= c <= cio.COLS:
                    n = (r - 1) * cio.COLS + c
                    if n in remaining:
                        remaining.remove(n)
                        stack.append(n)
        out.append(sorted(comp))
    return sorted(out, key=len, reverse=True)


def main():
    ap = argparse.ArgumentParser(description="Chronic closed-site detection")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--side", choices=["front", "rear"], default="front")
    ap.add_argument("--start", default=cio.DEFAULT_START)
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN, help="err_01 >= N (<256) is a read failure; 0 disables")
    ap.add_argument("--min-share", type=float, default=0.10, help="min share for cluster analysis")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--recent-days", type=int, default=7, help="window for the recency status (days before the last reading)")
    args = ap.parse_args()

    df = cio.load_side(args.side, args.data_dir, args.start, near_full_min=args.near_full_min)
    mat = cio.closed_matrix(df, args.side)
    share = closure_share(mat).sort_values(ascending=False)
    cutoff = mat.index.max() - pd.Timedelta(days=args.recent_days)
    recent = window_share(mat, start=cutoff).reindex(share.index)
    prior = window_share(mat, end=cutoff).reindex(share.index)
    status = pd.Series({s_: recency_status(share[s_], recent[s_], prior[s_]) for s_ in share.index})

    top = share.head(args.top).to_frame()
    top["class"] = top["closed_share"].map(classify)
    top["row"], top["col"] = zip(*[cio.site_row_col(s) for s in top.index])
    top["recent_share"] = (recent[top.index] * 100).round(1)
    top["status"] = status[top.index]
    top["closed_share"] = (top["closed_share"] * 100).round(1)
    print(f"\n=== {args.side.upper()} top {args.top} sites by closure share (%) | recent = last {args.recent_days} days to {mat.index.max():%Y-%m-%d} ===")
    print(top.to_string())

    counts = share.map(classify).value_counts()
    print("\nclass counts:", counts.to_dict())
    n_chronic = int(counts.get("chronic", 0))
    print(f"chronic_site_rate: {n_chronic}/256 = {n_chronic / 256 * 100:.1f}%")
    sc = status.value_counts().to_dict()
    n_now = int((recent >= 0.5).sum())
    print(f"recency status (last {args.recent_days} days): { {k: v for k, v in sc.items() if k != '-'} }")
    print(f"currently_closed_site_rate: {n_now}/256 = {n_now / 256 * 100:.1f}%  (sites closed >= 50% of the last {args.recent_days} days)")
    chron_resolved = [int(x) for x in share[(share >= 0.5)].index if status[x] == "RESOLVED"]
    if chron_resolved:
        print(f"period-chronic sites that are now RESOLVED: {chron_resolved}")
    new_sites = [int(x) for x in status[status == "NEW"].index]
    if new_sites:
        print(f"NEW sites (broke recently, low period share): {sorted(new_sites)}")

    sel = list(share[share >= args.min_share].index)
    print(f"\n=== clusters among {len(sel)} sites with share >= {args.min_share:.0%} ===")
    for comp in clusters(sel):
        lost = share[comp].sum() / cio.SITES_PER_SIDE * 100
        now = int((recent[comp] >= 0.5).sum())
        lost_now = recent[comp].sum() / cio.SITES_PER_SIDE * 100
        print(f"size {len(comp):2d}  lost availability {lost:5.2f} pts  (last {args.recent_days}d {lost_now:4.2f} pts, {now}/{len(comp)} closed now)  sites {comp}")

    sel_now = list(recent[recent >= args.min_share].index)
    print(f"\n=== clusters among {len(sel_now)} sites closed >= {args.min_share:.0%} of the last {args.recent_days} days (what needs attention now) ===")
    for comp in [c for c in clusters(sel_now) if len(c) > 1]:
        lost_now = recent[comp].sum() / cio.SITES_PER_SIDE * 100
        print(f"size {len(comp):2d}  last {args.recent_days}d {lost_now:5.2f} pts  statuses {sorted(set(status[comp]))}  sites {comp}")

    cum = share.cumsum() / share.sum() * 100
    for n in (5, 10, 20):
        print(f"top {n:2d} sites explain {cum.iloc[n - 1]:.1f}% of all closure time")


if __name__ == "__main__":
    main()
