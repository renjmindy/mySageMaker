"""
Self-contained HTML report: site closure heatmap (front/rear grids), daily
availability line chart and a table view. No external dependencies.

Usage:
    python site_heatmap.py
    python site_heatmap.py --output ../../../out/site_heatmap.html
"""

import argparse
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import contactor_io as cio  # noqa: E402

BUCKETS = [(0.0, 0.01), (0.01, 0.05), (0.05, 0.10), (0.10, 0.25), (0.25, 0.50), (0.50, 0.75), (0.75, 1.01)]
LABELS = ["<1%", "1-5%", "5-10%", "10-25%", "25-50%", "50-75%", ">=75%"]
# single-hue blue ramp (light mode: light = near zero; dark mode: dark = near zero)
LIGHT = ["#e8f0fa", "#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]
DARK = ["#222a33", "#274a78", "#2f64a8", "#3987e5", "#5598e7", "#86b6ef", "#cde2fb"]


def bucket(share: float) -> int:
    return next(i for i, (lo, hi) in enumerate(BUCKETS) if lo <= share < hi)


def grid_svg(side: str, share: dict[int, float]) -> str:
    lo = cio.SIDES[side]["lo"]
    first_row = (lo - 1) // cio.COLS + 1
    cell, gap, left, top = 26, 2, 34, 6
    w = left + cio.COLS * (cell + gap)
    h = top + 16 * (cell + gap) + 18
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{side} closure share by site" class="grid">']
    for i, r in enumerate(range(first_row + 15, first_row - 1, -1)):  # highest row on top, like the screen
        y = top + i * (cell + gap)
        out.append(f'<text x="{left - 6}" y="{y + cell * 0.68}" text-anchor="end" class="axis">{r}</text>')
        for c in range(1, cio.COLS + 1):
            s = (r - 1) * cio.COLS + c
            sh = share.get(s, 0.0)
            x = left + (c - 1) * (cell + gap)
            tip = f"Site {s} (row {r}, col {c}): closed {sh * 100:.1f}% of time"
            out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" class="b{bucket(sh)}" data-tip="{html.escape(tip)}"/>')
    for c in range(1, cio.COLS + 1):
        x = left + (c - 1) * (cell + gap) + cell / 2
        out.append(f'<text x="{x}" y="{h - 4}" text-anchor="middle" class="axis">{c}</text>')
    out.append("</svg>")
    return "".join(out)


def line_svg(series: dict[str, list[tuple[str, float]]]) -> str:
    w, h, l, r, t, b = 760, 260, 44, 20, 12, 28
    days = [d for d, _ in next(iter(series.values()))]
    vals = [v for s in series.values() for _, v in s]
    lo = max(0, int(min(vals) // 5) * 5)
    hi = 100
    X = lambda i: l + i * (w - l - r) / max(1, len(days) - 1)
    Y = lambda v: t + (hi - v) * (h - t - b) / (hi - lo)
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="daily site availability, front and rear" class="line">']
    for v in range(lo, hi + 1, 5 if hi - lo <= 30 else 10):
        out.append(f'<line x1="{l}" x2="{w - r}" y1="{Y(v)}" y2="{Y(v)}" class="gridline"/><text x="{l - 6}" y="{Y(v) + 4}" text-anchor="end" class="axis">{v}%</text>')
    for i in range(0, len(days), 5):
        out.append(f'<text x="{X(i)}" y="{h - 8}" text-anchor="middle" class="axis">{days[i][5:]}</text>')
    for k, (name, pts) in enumerate(series.items()):
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(i):.1f},{Y(v):.1f}" for i, (_, v) in enumerate(pts))
        out.append(f'<path d="{d}" class="s{k}" fill="none"/>')
        for i, (day, v) in enumerate(pts):
            out.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="7" class="hit" data-tip="{name} {day}: {v:.1f}%"/>')
        x_end, y_end = X(len(pts) - 1), Y(pts[-1][1])
        out.append(f'<text x="{x_end - 4}" y="{y_end - 8}" text-anchor="end" class="lbl">{name}</text>')
    out.append("</svg>")
    return "".join(out)


CSS = """
:root{--surface:#fcfcfb;--page:#f9f9f7;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--c1:#2a78d6;--c2:#eb6834;
""" + "".join(f"--b{i}:{c};" for i, c in enumerate(LIGHT)) + """}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--surface:#1a1a19;--page:#0d0d0d;--ink:#f0efec;--ink2:#c3c2b7;--grid:#2c2c2a;--c1:#3987e5;--c2:#d95926;
""" + "".join(f"--b{i}:{c};" for i, c in enumerate(DARK)) + """}}
body{margin:0;background:var(--page);color:var(--ink);font:14px/1.5 system-ui,sans-serif}
main{max-width:960px;margin:0 auto;padding:24px 16px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:28px 0 8px}p.sub{color:var(--ink2);margin:0 0 16px}
.tiles{display:flex;gap:12px;flex-wrap:wrap}.tile{background:var(--surface);border:1px solid var(--grid);border-radius:10px;padding:12px 16px;min-width:150px}
.tile b{display:block;font-size:26px}.tile span{color:var(--ink2);font-size:12px}
.card{background:var(--surface);border:1px solid var(--grid);border-radius:10px;padding:12px 16px}
.grids{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:12px}
svg{width:100%;height:auto}.axis{fill:var(--muted);font-size:10px}.lbl{fill:var(--ink2);font-size:12px}
.gridline{stroke:var(--grid)}.s0,.s1{stroke-width:2}.s0{stroke:var(--c1)}.s1{stroke:var(--c2)}.hit{fill:transparent}.hit:hover{fill:var(--ink2);fill-opacity:.4}
""" + "".join(f".b{i}{{fill:var(--b{i})}}" for i in range(7)) + """
rect:hover{stroke:var(--ink);stroke-width:1.5}
.legend{display:flex;gap:10px;flex-wrap:wrap;font-size:12px;color:var(--ink2);margin-top:8px}.legend i{display:inline-block;width:14px;height:14px;border-radius:3px;vertical-align:-3px;margin-right:4px}
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--surface);padding:4px 8px;border-radius:6px;font-size:12px;display:none}
table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:3px 8px;border-bottom:1px solid var(--grid);text-align:right}th:first-child,td:first-child{text-align:left}
details{margin-top:16px}
"""

JS = """
const tip=document.getElementById('tip');
document.addEventListener('mousemove',e=>{const t=e.target.closest('[data-tip]');
 if(t){tip.textContent=t.dataset.tip;tip.style.display='block';tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY+12)+'px'}else tip.style.display='none'});
"""


def main():
    ap = argparse.ArgumentParser(description="Contactor closure heatmap + availability report (HTML)")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--start", default=cio.DEFAULT_START)
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN, help="err_01 >= N (<256) is a read failure; 0 disables")
    ap.add_argument("--output", default=str(cio.REPO_ROOT / "out" / "site_heatmap.html"))
    args = ap.parse_args()

    shares, daily, tiles = {}, {}, []
    for side in cio.SIDES:
        df = cio.load_side(side, args.data_dir, args.start, near_full_min=args.near_full_min)
        mat = cio.closed_matrix(df, side)
        w = mat["weight_min"]
        closed = mat.drop(columns="weight_min").astype(float)
        shares[side] = dict(zip(closed.columns, (closed.mul(w, axis=0).sum() / w.sum()).tolist()))
        v = df[df["valid"]].copy()
        v["day"] = v["timestamp"].dt.strftime("%Y-%m-%d")
        daily[side.capitalize()] = [(d, (1 - (g["n_closed"] * g["weight_min"]).sum() / (256 * g["weight_min"].sum())) * 100)
                                    for d, g in v.groupby("day")]
        tiles.append((side.capitalize(), cio.weighted_availability(df) * 100))

    subtitle = f"{args.start} onward, time-weighted, cleaned logs" + (f", near-full (>= {args.near_full_min}) excluded" if args.near_full_min else "")
    legend = "".join(f'<span><i style="background:var(--b{i})"></i>{LABELS[i]}</span>' for i in range(7))
    rows = "".join(f"<tr><td>{d}</td>" + "".join(f"<td>{dict(daily[k])[d]:.1f}%</td>" if d in dict(daily[k]) else "<td>-</td>" for k in daily) + "</tr>"
                   for d in sorted({d for s in daily.values() for d, _ in s}))
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Contactor Site Availability</title><style>{CSS}</style></head><body><main>
<h1>Contactor site availability</h1><p class="sub">{html.escape(subtitle)}</p>
<div class="tiles">{"".join(f'<div class="tile"><b>{v:.1f}%</b><span>{k} sites open (time-weighted)</span></div>' for k, v in tiles)}</div>
<h2>Where the closures are - share of time each site is closed</h2>
<div class="grids"><div class="card"><strong>Front (sites 1-256)</strong>{grid_svg("front", shares["front"])}</div>
<div class="card"><strong>Rear (sites 257-512)</strong>{grid_svg("rear", shares["rear"])}</div></div>
<div class="legend">{legend}</div>
<h2>Daily availability</h2><div class="card">{line_svg(daily)}</div>
<details><summary>Table view</summary><table><tr><th>Day</th>{"".join(f"<th>{k}</th>" for k in daily)}</tr>{rows}</table></details>
<div id="tip"></div></main><script>{JS}</script></body></html>"""
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
