"""
Closure episodes and closure events for contactor sites.

Pipeline
  1. keep consistent readings only (count == list length, <= --max-closed closed sites)
  2. debounce each site with a centred rolling median (--window readings, default 5 ~ 20 min);
     closures shorter than about half the window are ignored by design
  3. closure EPISODES per site: start, end, duration (ongoing / left-censored flagged)
  4. closure EVENTS: episodes that start within --group-min minutes AND are spatially connected
     (4-neighbour adjacency) form one event, so concurrent but unrelated closures are not merged
  5. rank events by block alignment (share of sites whose whole aligned 2x2 block closed with them),
     then size, then duration; filter with --min-sites / --min-duration

block_aligned ~1.0 -> board/module-style event; ~0 with many blocks -> scattered blips (a random set
of 8 sites scores ~0.0). The output also prints a false-event baseline: episodes on "quiet" sites
(closed < 0.5% of the time), which should be rare on healthy sites.

Usage:
    python closure_events.py --side rear
    python closure_events.py --side front --min-sites 2 --min-duration 60 --sort start
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import contactor_io as cio  # noqa: E402


def block_members(site: int) -> set[int]:
    row, col = cio.site_row_col(site)
    r0, c0 = (row - 1) // 2 * 2 + 1, (col - 1) // 2 * 2 + 1
    return {(r - 1) * cio.COLS + c for r in (r0, r0 + 1) for c in (c0, c0 + 1)}


def aligned_share(sites: list[int]) -> float:
    """Share of sites whose whole aligned 2x2 block is in the set (1.0 = pure block events)."""
    s = set(sites)
    return sum(block_members(x) <= s for x in sites) / len(sites)


def closure_episodes(mat: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Per-site closure episodes from the debounced state: site, start, end, duration_min, ongoing, left_censored."""
    state = mat.drop(columns="weight_min").astype(float)
    smooth = state.rolling(window, center=True, min_periods=1).median().astype(bool)
    ts = smooth.index
    rows = []
    for site in smooth.columns:
        a = smooth[site].to_numpy()
        if not a.any():
            continue
        d = np.diff(np.concatenate([[False], a, [False]]).astype(int))
        for s, e in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
            ongoing = e >= len(a)
            end = ts[-1] if ongoing else ts[e]
            rows.append({"site": int(site), "start": ts[s], "end": end,
                         "duration_min": (end - ts[s]).total_seconds() / 60,
                         "ongoing": bool(ongoing), "left_censored": bool(s == 0)})
    return pd.DataFrame(rows, columns=["site", "start", "end", "duration_min", "ongoing", "left_censored"])


def _components(sites: set[int]) -> list[list[int]]:
    remaining, out = set(sites), []
    while remaining:
        stack, comp = [remaining.pop()], []
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
    return out


def group_events(ep: pd.DataFrame, group_min: float = 30) -> pd.DataFrame:
    """Episodes starting within group_min minutes of each other, split into spatially connected components."""
    if ep.empty:
        return pd.DataFrame(columns=["start", "end", "duration_min", "n_sites", "sites", "n_blocks_2x2",
                                     "block_aligned", "ongoing", "left_censored"])
    ep = ep.sort_values("start").reset_index(drop=True)
    gid = (ep["start"].diff().dt.total_seconds().div(60).fillna(1e9) > group_min).cumsum()
    rows = []
    for _, g in ep.groupby(gid):
        for comp in _components(set(g["site"])):
            e = g[g["site"].isin(comp)]
            blocks = {f"R{(cio.site_row_col(s)[0] + 1) // 2}C{(cio.site_row_col(s)[1] + 1) // 2}" for s in comp}
            rows.append({"start": e["start"].min(), "end": e["end"].max(), "duration_min": float(e["duration_min"].median()),
                         "n_sites": len(comp), "sites": comp, "n_blocks_2x2": len(blocks),
                         "block_aligned": round(aligned_share(comp), 2),
                         "ongoing": bool(e["ongoing"].any()), "left_censored": bool(e["left_censored"].any())})
    return pd.DataFrame(rows)


def rank_events(ev: pd.DataFrame) -> pd.DataFrame:
    return ev.sort_values(["block_aligned", "n_sites", "duration_min"], ascending=False).reset_index(drop=True)


def quiet_baseline(mat: pd.DataFrame, ep: pd.DataFrame) -> dict:
    state = mat.drop(columns="weight_min").astype(float)
    share = state.mul(mat["weight_min"], axis=0).sum() / mat["weight_min"].sum()
    quiet = [int(s) for s in share[share < 0.005].index]
    q = ep[ep["site"].isin(quiet)]
    return {"quiet_sites": len(quiet), "episodes": len(q), "per_site": round(len(q) / max(1, len(quiet)), 2),
            "median_duration_min": round(float(q["duration_min"].median()), 0) if len(q) else None}


def compact(sites: list[int], n: int = 10) -> str:
    return ",".join(map(str, sites[:n])) + (f" +{len(sites) - n} more" if len(sites) > n else "")


def main():
    ap = argparse.ArgumentParser(description="Closure episodes and events")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--side", choices=["front", "rear"], default="rear")
    ap.add_argument("--start", default=cio.DEFAULT_START)
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN)
    ap.add_argument("--window", type=int, default=5, help="rolling-median window (readings)")
    ap.add_argument("--group-min", type=float, default=30, help="episodes starting within this many minutes can form one event")
    ap.add_argument("--min-sites", type=int, default=4)
    ap.add_argument("--min-duration", type=float, default=30, help="minimum median episode duration in minutes")
    ap.add_argument("--sort", choices=["rank", "start"], default="rank")
    ap.add_argument("--max-closed", type=int, default=100, help="ignore readings with more closed sites than this (implausible)")
    ap.add_argument("--allow-mismatch", action="store_true", help="keep readings where err_01 != list length")
    ap.add_argument("--max-rows", type=int, default=25)
    args = ap.parse_args()

    df = cio.load_side(args.side, args.data_dir, args.start, near_full_min=args.near_full_min)
    # events must come from consistent reads: a list that disagrees with err_01 is missing IDs and would
    # fake "opened" episodes; implausibly large sets are burst noise
    keep = df["valid"] & (df["n_closed"] <= args.max_closed)
    if not args.allow_mismatch:
        keep &= ~df["count_mismatch"]
    print(f"using {int(keep.sum())} of {int(df['valid'].sum())} valid readings (consistent, <= {args.max_closed} closed)")
    mat = cio.closed_matrix(df.assign(valid=keep), args.side)

    ep = closure_episodes(mat, args.window)
    ev = group_events(ep, args.group_min)
    sel = ev[(ev["n_sites"] >= args.min_sites) & (ev["duration_min"] >= args.min_duration)]
    sel = rank_events(sel) if args.sort == "rank" else sel.sort_values("start").reset_index(drop=True)

    base = quiet_baseline(mat, ep)
    print(f"\n=== {args.side.upper()} closure events (window={args.window}) ===")
    print(f"funnel: {len(ep)} episodes -> {len(ev)} spatially separate events -> {len(sel)} with >= {args.min_sites} sites and median duration >= {args.min_duration:.0f} min")
    print(f"false-event baseline: {base['quiet_sites']} quiet sites (closed < 0.5%) have {base['episodes']} episodes "
          f"({base['per_site']} per site, median {base['median_duration_min']} min) - expect few on healthy sites")
    out = sel.head(args.max_rows).copy()
    out["sites"] = out["sites"].map(compact)
    out["duration_min"] = out["duration_min"].round(0).astype(int)
    out["flags"] = out.apply(lambda r: ("ongoing " if r.ongoing else "") + ("at-period-start" if r.left_censored else ""), axis=1)
    pd.set_option("display.width", 220, "display.max_colwidth", 60)
    if len(sel):
        if len(out):
            print(out[["start", "end", "duration_min", "n_sites", "block_aligned", "n_blocks_2x2", "sites", "flags"]].to_string(index=False))
        print(f"\nshowing {len(out)} of {len(sel)}; aligned (>= 0.9): {int((sel['block_aligned'] >= 0.9).sum())}, "
              f"scattered (< 0.3): {int((sel['block_aligned'] < 0.3).sum())}; ranked by alignment, size, duration")
    else:
        print("no events pass the filters")


if __name__ == "__main__":
    main()
