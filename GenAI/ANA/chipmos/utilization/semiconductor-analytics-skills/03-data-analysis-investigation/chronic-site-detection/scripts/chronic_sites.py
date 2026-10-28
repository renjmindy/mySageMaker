"""
Rank sites by closure share, cluster adjacent closed sites, show a Pareto.

Usage:
    python chronic_sites.py --side front
    python chronic_sites.py --side rear --top 15
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
    args = ap.parse_args()

    df = cio.load_side(args.side, args.data_dir, args.start, near_full_min=args.near_full_min)
    share = closure_share(cio.closed_matrix(df, args.side)).sort_values(ascending=False)

    top = share.head(args.top).to_frame()
    top["class"] = top["closed_share"].map(classify)
    top["row"], top["col"] = zip(*[cio.site_row_col(s) for s in top.index])
    top["closed_share"] = (top["closed_share"] * 100).round(1)
    print(f"\n=== {args.side.upper()} top {args.top} sites by closure share (%) ===")
    print(top.to_string())

    counts = share.map(classify).value_counts()
    print("\nclass counts:", counts.to_dict())
    n_chronic = int(counts.get("chronic", 0))
    print(f"chronic_site_rate: {n_chronic}/256 = {n_chronic / 256 * 100:.1f}%")

    sel = list(share[share >= args.min_share].index)
    print(f"\n=== clusters among {len(sel)} sites with share >= {args.min_share:.0%} ===")
    for comp in clusters(sel):
        lost = share[comp].sum() / cio.SITES_PER_SIDE * 100
        print(f"size {len(comp):2d}  lost availability {lost:5.2f} pts  sites {comp}")

    cum = share.cumsum() / share.sum() * 100
    for n in (5, 10, 20):
        print(f"top {n:2d} sites explain {cum.iloc[n - 1]:.1f}% of all closure time")


if __name__ == "__main__":
    main()
