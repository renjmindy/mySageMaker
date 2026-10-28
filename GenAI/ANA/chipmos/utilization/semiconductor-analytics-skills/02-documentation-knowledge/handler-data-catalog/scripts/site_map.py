"""
Map contactor site IDs to screen position and render closed sets as a grid.

Geometry (Advantest Contactor Select screen): 16 columns x 32 rows = 512 sites;
front = rows 1-16 (sites 1-256), rear = rows 17-32 (sites 257-512). Sites that
close together are often an aligned 2x2 block (rows 2k-1,2k x cols 2j-1,2j).

Usage:
    python site_map.py --site 229 230 245 246
    python site_map.py --render 229 230 245 246 143 144 159 160
    python site_map.py --render-from-log --side front --min-share 0.5
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import contactor_io as cio  # noqa: E402


def describe(site: int) -> dict:
    row, col = cio.site_row_col(site)
    return {
        "site": site,
        "side": "front" if site <= cio.SITES_PER_SIDE else "rear",
        "row": row,
        "col": col,
        "block_2x2": f"R{(row + 1) // 2}C{(col + 1) // 2}",
    }


def render(closed: set[int], side: str) -> str:
    lo, hi = cio.SIDES[side]["lo"], cio.SIDES[side]["hi"]
    first_row = (lo - 1) // cio.COLS + 1
    lines = ["      " + " ".join(f"{c:2d}" for c in range(1, cio.COLS + 1))]
    for r in range(first_row + 15, first_row - 1, -1):  # screen shows the highest row on top
        cells = []
        for c in range(1, cio.COLS + 1):
            s = (r - 1) * cio.COLS + c
            cells.append(" X" if s in closed else " .")
        lines.append(f"row {r:2d} " + " ".join(cells))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Contactor site geometry helper")
    ap.add_argument("--site", type=int, nargs="*", help="site IDs to describe")
    ap.add_argument("--render", type=int, nargs="*", help="site IDs to draw as closed (X)")
    ap.add_argument("--render-from-log", action="store_true", help="draw sites closed in >= --min-share of samples")
    ap.add_argument("--side", choices=["front", "rear"], default="front")
    ap.add_argument("--min-share", type=float, default=0.5)
    ap.add_argument("--data-dir", default=None)
    args = ap.parse_args()

    if args.site:
        for s in args.site:
            print(describe(s))
    if args.render:
        side = "front" if max(args.render) <= cio.SITES_PER_SIDE else "rear"
        print(render(set(args.render), side))
    if args.render_from_log:
        df = cio.load_side(args.side, args.data_dir)
        v = df[df["valid"]]
        freq: dict[int, int] = {}
        for sites in v["sites"]:
            for s in sites:
                freq[s] = freq.get(s, 0) + 1
        closed = {s for s, n in freq.items() if n / len(v) >= args.min_share}
        print(f"{args.side}: {len(closed)} sites closed in >= {args.min_share:.0%} of {len(v)} samples")
        print(render(closed, args.side))
    if not (args.site or args.render or args.render_from_log):
        print(describe(229), describe(480), sep="\n")


if __name__ == "__main__":
    main()
