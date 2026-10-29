"""
Self-contained HTML report: where test positions are closed (front/rear grids), how many can test
(with a plausible range), a daily line, and a ranked table. No external dependencies.

  * heatmap view toggle: "Last N days" (what is closed now, default) or "Whole period"; the period
    ranking alone can describe history (a group that was fixed still looks dark)
  * tiles: share of positions able to test with a plausible range (95% day bootstrap) and a lower
    bound, plus how many positions are closed now
  * line: daily share per side, with each side's plausible range of the period average as a band
  * accessible: radio toggle, arrow-key reading of every cell, tap/hover tooltips, an aria-live
    region, a ranked table of the positions closed most, and a table view of the daily numbers
  * responsive: no horizontal page scroll down to 375 px; dark mode with its own colour steps

Usage:
    python site_heatmap.py
    python site_heatmap.py --recent-days 14 --output ../../../out/site_heatmap.html
"""

import argparse
import html
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "03-data-analysis-investigation/chronic-site-detection/scripts"))
sys.path.insert(0, str(ROOT / "03-data-analysis-investigation/site-availability/scripts"))
sys.path.insert(0, str(ROOT / "03-data-analysis-investigation/downtime-time-series/scripts"))
import chronic_sites as cs  # noqa: E402
import contactor_io as cio  # noqa: E402
import daily_trend as dt  # noqa: E402
import site_availability as sa  # noqa: E402

# six buckets of closure share; adjacent steps >= ~10 DeltaE (OKLab x100) in both modes (checked by viz_check.py)
EDGES = [0.05, 0.10, 0.25, 0.50, 0.75]
LABELS = ["<5%", "5-10%", "10-25%", "25-50%", "50-75%", "75%+"]
LIGHT = ["#e8f0fa", "#b7d3f6", "#6da7ec", "#3987e5", "#1c5cab", "#0d366b"]  # light = near zero
DARK = ["#222a33", "#274a78", "#2f64a8", "#3987e5", "#6da7ec", "#9ec5f4"]   # dark = near zero
SERIES_LIGHT, SERIES_DARK = ("#2a78d6", "#eb6834"), ("#3987e5", "#d95926")  # front, rear (validated pair)
STATUS_WORDS = {"PERSISTENT": "closed long-term", "NEW": "closed recently", "CURRENT": "closed now",
                "INTERMITTENT": "partly closed", "RESOLVED": "reopened", "-": "mostly open"}


def bucket(share: float) -> int:
    return sum(share >= e for e in EDGES)


def collect(data_dir=None, start=cio.DEFAULT_START, near_full_min=cio.NEAR_FULL_MIN, recent_days: int = 7) -> dict:
    """All numbers the page shows, so they can be checked independently of the HTML."""
    out = {"recent_days": recent_days, "sides": {}}
    for side in cio.SIDES:
        df = cio.load_side(side, data_dir, start, near_full_min=near_full_min)
        mat = cio.closed_matrix(df, side)
        period = cs.closure_share(mat)
        cutoff = mat.index.max() - pd.Timedelta(days=recent_days)
        recent = cs.window_share(mat, start=cutoff).reindex(period.index)
        prior = cs.window_share(mat, end=cutoff).reindex(period.index)
        status = pd.Series({s: cs.recency_status(period[s], recent[s], prior[s]) for s in period.index})
        ov = sa.overall(df)
        lo, hi = sa.bootstrap_ci(df)
        daily = dt.daily_series(df)["availability_pct"]
        out["sides"][side] = {
            "period": period, "recent": recent, "status": status,
            "availability_pct": cio.weighted_availability(df) * 100, "low_pct": ov["availability_low_pct"],
            "ci": (lo, hi), "closed_now": int((recent >= 0.5).sum()),
            "daily": [(d.strftime("%Y-%m-%d"), float(v)) for d, v in daily.items()],
            "first": df["timestamp"].min(), "last": df["timestamp"].max(),
        }
    out["first"] = min(v["first"] for v in out["sides"].values())
    out["last"] = max(v["last"] for v in out["sides"].values())
    return out


def date_range(first, last) -> str:
    f = f"{first.day} {first:%B}" + (f" {first.year}" if first.year != last.year else "")
    return f"{f} to {last.day} {last:%B %Y}"


def grid_svg(side: str, shares: pd.Series, view: str, recent: pd.Series, status: pd.Series, days: int) -> str:
    lo = cio.SIDES[side]["lo"]
    first_row = (lo - 1) // cio.COLS + 1
    cell, gap, left, top = 26, 2, 34, 6
    w = left + cio.COLS * (cell + gap)
    h = top + 16 * (cell + gap) + 18
    label = (f"{side} test positions, share of the last {days} days closed" if view == "recent"
             else f"{side} test positions, share of the whole period closed")
    out = [f'<svg viewBox="0 0 {w} {h}" role="group" tabindex="0" aria-label="{label}. Use the arrow keys to read each position; a ranked table follows." class="grid view-{view}">']
    for i, r in enumerate(range(first_row + 15, first_row - 1, -1)):  # highest row on top, like the handler screen
        y = top + i * (cell + gap)
        out.append(f'<text x="{left - 6}" y="{y + cell * 0.68}" text-anchor="end" class="axis">{r}</text>')
        for c in range(1, cio.COLS + 1):
            s = (r - 1) * cio.COLS + c
            x = left + (c - 1) * (cell + gap)
            if view == "recent":
                tip = (f"Position {s} (row {r}, column {c}): closed {recent[s] * 100:.0f}% of the last {days} days, "
                       f"{shares[s] * 100:.0f}% over the whole period - {STATUS_WORDS[status[s]]}")
                b = bucket(recent[s])
            else:
                tip = f"Position {s} (row {r}, column {c}): closed {shares[s] * 100:.1f}% of the whole period"
                b = bucket(shares[s])
            out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" class="b{b}" data-tip="{html.escape(tip)}"/>')
    for c in range(1, cio.COLS + 1):
        x = left + (c - 1) * (cell + gap) + cell / 2
        out.append(f'<text x="{x}" y="{h - 4}" text-anchor="middle" class="axis">{c}</text>')
    out.append("</svg>")
    return "".join(out)


def line_svg(sides: dict) -> str:
    w, h, l, r, t, b = 760, 260, 44, 20, 12, 28
    series = {k.capitalize(): v["daily"] for k, v in sides.items()}
    days = [d for d, _ in next(iter(series.values()))]
    vals = [v for s in series.values() for _, v in s] + [x for v in sides.values() for x in v["ci"]]
    lo = max(0, int(min(vals) // 5) * 5)
    hi = 100
    X = lambda i: l + i * (w - l - r) / max(1, len(days) - 1)
    Y = lambda v: t + (hi - v) * (h - t - b) / (hi - lo)
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="daily share of test positions able to test, front and rear, with the plausible range of each month average as a band" class="line">']
    for v in range(lo, hi + 1, 5 if hi - lo <= 30 else 10):
        out.append(f'<line x1="{l}" x2="{w - r}" y1="{Y(v)}" y2="{Y(v)}" class="gridline"/><text x="{l - 6}" y="{Y(v) + 4}" text-anchor="end" class="axis">{v}%</text>')
    for i in range(0, len(days), 5):
        out.append(f'<text x="{X(i)}" y="{h - 8}" text-anchor="middle" class="axis">{days[i][5:]}</text>')
    for k, (name, pts) in enumerate(series.items()):
        ci = sides[name.lower()]["ci"]
        out.append(f'<rect x="{l}" y="{Y(ci[1]):.1f}" width="{w - l - r}" height="{Y(ci[0]) - Y(ci[1]):.1f}" class="band{k}"/>')
    for k, (name, pts) in enumerate(series.items()):
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(i):.1f},{Y(v):.1f}" for i, (_, v) in enumerate(pts))
        out.append(f'<path d="{d}" class="s{k}" fill="none"/>')
        for i, (day, v) in enumerate(pts):
            out.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="7" class="hit" data-tip="{name} {day}: {v:.1f}%"/>')
        out.append(f'<text x="{X(len(pts) - 1) - 4}" y="{Y(pts[-1][1]) - 8}" text-anchor="end" class="lbl">{name}</text>')
    out.append("</svg>")
    return "".join(out)


def ranked_rows(data: dict, per_side: int = 10) -> str:
    rows = []
    for side, v in data["sides"].items():
        d = pd.DataFrame({"recent": v["recent"], "period": v["period"], "status": v["status"]})
        d = d[(d["recent"] >= 0.10) | (d["period"] >= 0.10)].sort_values(["recent", "period"], ascending=False).head(per_side)
        for s, r in d.iterrows():
            row, col = cio.site_row_col(int(s))
            rows.append(f"<tr><td>{side.capitalize()}</td><td>{s}</td><td>row {row}, column {col}</td>"
                        f"<td>{r['recent'] * 100:.0f}%</td><td>{r['period'] * 100:.0f}%</td><td>{STATUS_WORDS[r['status']]}</td></tr>")
    return "".join(rows)


CSS = """
:root{--surface:#fcfcfb;--page:#f9f9f7;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--c1:%s;--c2:%s;
""" % SERIES_LIGHT + "".join(f"--b{i}:{c};" for i, c in enumerate(LIGHT)) + """}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--surface:#1a1a19;--page:#0d0d0d;--ink:#f0efec;--ink2:#c3c2b7;--grid:#2c2c2a;--c1:%s;--c2:%s;
""" % SERIES_DARK + "".join(f"--b{i}:{c};" for i, c in enumerate(DARK)) + """}}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:14px/1.5 system-ui,sans-serif}
main{max-width:960px;margin:0 auto;padding:24px 16px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:28px 0 8px}p.sub{color:var(--ink2);margin:0 0 16px}
.tiles{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px}
.tile{background:var(--surface);border:1px solid var(--grid);border-radius:10px;padding:12px 16px;flex:1 1 220px;min-width:0}
.tile b{display:block;font-size:26px}.tile span{color:var(--ink2);font-size:12px;display:block}
.card{background:var(--surface);border:1px solid var(--grid);border-radius:10px;padding:12px 16px;overflow-x:auto}
.wrap{position:relative}
.wrap>input{position:absolute;opacity:0;width:1px;height:1px}
.toggle{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.toggle label{padding:8px 14px;border:1px solid var(--grid);border-radius:8px;cursor:pointer;background:var(--surface);min-height:40px}
#v-recent:checked~.toggle label[for=v-recent],#v-period:checked~.toggle label[for=v-period]{border-color:var(--c1);box-shadow:inset 0 -3px 0 var(--c1);font-weight:600}
#v-recent:focus-visible~.toggle label[for=v-recent],#v-period:focus-visible~.toggle label[for=v-period]{outline:2px solid var(--ink);outline-offset:2px}
#v-period:checked~.grids .view-recent,#v-recent:checked~.grids .view-period{display:none}
.grids{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(380px,100%),1fr));gap:12px}
svg{width:100%;height:auto}.axis{fill:var(--muted);font-size:10px}.lbl{fill:var(--ink2);font-size:12px}
svg.grid:focus-visible{outline:2px solid var(--ink);outline-offset:2px}rect.sel{stroke:var(--ink);stroke-width:2.5}
@media (pointer:coarse),(max-width:520px){svg.grid{min-width:482px}}  /* touch cells >= 24px; the card scrolls, the page does not */
.gridline{stroke:var(--grid)}.s0,.s1{stroke-width:2}.s0{stroke:var(--c1)}.s1{stroke:var(--c2)}
.band0{fill:var(--c1);opacity:.14}.band1{fill:var(--c2);opacity:.14}.hit{fill:transparent}.hit:hover{fill:var(--ink2);fill-opacity:.4}
""" + "".join(f".b{i}{{fill:var(--b{i})}}" for i in range(6)) + """
rect:hover{stroke:var(--ink);stroke-width:1.5}
.legend{display:flex;gap:10px;flex-wrap:wrap;font-size:12px;color:var(--ink2);margin-top:8px}.legend i{display:inline-block;width:14px;height:14px;border-radius:3px;vertical-align:-3px;margin-right:4px}
.legend i.l0,.legend i.l1{border-radius:3px}.k0{background:var(--c1)}.k1{background:var(--c2)}.kb{background:var(--surface);border:1px dashed var(--muted)}
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--surface);padding:4px 8px;border-radius:6px;font-size:12px;display:none;max-width:min(320px,90vw)}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:4px 8px;border-bottom:1px solid var(--grid);text-align:right;white-space:nowrap}
th:first-child,td:first-child,th:nth-child(3),td:nth-child(3),th:last-child,td:last-child{text-align:left}
details{margin-top:16px}.sr{position:absolute;left:-9999px}
"""

JS = """
const tip=document.getElementById('tip'),live=document.getElementById('live');
function show(el,x,y){tip.textContent=el.dataset.tip;tip.style.display='block';
 tip.style.left=Math.max(8,Math.min(x+12,innerWidth-tip.offsetWidth-8))+'px';tip.style.top=(y+12)+'px'}
document.addEventListener('mousemove',e=>{const t=e.target.closest('[data-tip]');if(t)show(t,e.clientX,e.clientY);else tip.style.display='none'});
document.addEventListener('pointerdown',e=>{const t=e.target.closest('[data-tip]');if(t){show(t,e.clientX,e.clientY);live.textContent=t.dataset.tip}});
document.querySelectorAll('svg.grid').forEach(svg=>{let i=0;
 const go=n=>{const cs=svg.querySelectorAll('rect[data-tip]');i=Math.max(0,Math.min(cs.length-1,n));
  cs.forEach(c=>c.classList.remove('sel'));const c=cs[i];c.classList.add('sel');live.textContent=c.dataset.tip;
  const b=c.getBoundingClientRect();show(c,b.left,b.bottom)};
 svg.addEventListener('keydown',e=>{const k={ArrowRight:1,ArrowLeft:-1,ArrowDown:16,ArrowUp:-16}[e.key];
  if(k!==undefined){e.preventDefault();go(i+k)}else if(e.key==='Home'){e.preventDefault();go(0)}else if(e.key==='End'){e.preventDefault();go(255)}});
 svg.addEventListener('focus',()=>go(i));svg.addEventListener('blur',()=>{tip.style.display='none'})});
"""


def render(data: dict) -> str:
    n = data["recent_days"]
    sides = data["sides"]
    rng = date_range(data["first"], data["last"])
    tiles = "".join(
        f'<div class="tile"><b>{v["availability_pct"]:.1f}%</b><span>of {k} test positions able to test, on average</span>'
        f'<span>plausible range {v["ci"][0]:.1f}-{v["ci"][1]:.1f}%; at least {v["low_pct"]:.1f}%</span></div>' for k, v in sides.items())
    now = "".join(
        f'<div class="tile"><b>{v["closed_now"]} of 256</b><span>{k} positions closed in the last {n} days ({v["closed_now"] / 256 * 100:.1f}%)</span></div>'
        for k, v in sides.items())
    grids = "".join(
        f'<div class="card"><strong>{k.capitalize()} (positions {cio.SIDES[k]["lo"]}-{cio.SIDES[k]["hi"]})</strong>'
        + grid_svg(k, v["period"], "recent", v["recent"], v["status"], n)
        + grid_svg(k, v["period"], "period", v["recent"], v["status"], n) + "</div>" for k, v in sides.items())
    legend = "".join(f'<span><i style="background:var(--b{i})"></i>{LABELS[i]}</span>' for i in range(6))
    days = sorted({d for v in sides.values() for d, _ in v["daily"]})
    lookup = {k: dict(v["daily"]) for k, v in sides.items()}
    rows = "".join(f"<tr><td>{d}</td>" + "".join(f"<td>{lookup[k][d]:.1f}%</td>" if d in lookup[k] else "<td>-</td>" for k in sides) + "</tr>" for d in days)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Handler test positions</title><style>{CSS}</style></head><body><main>
<h1>Handler test positions: how many can test</h1>
<p class="sub">{html.escape(rng)}. Each reading counts for the time until the next one; unreadable screen readings are left out. "Last {n} days" ends on {data["last"].day} {data["last"]:%B}.</p>
<div class="tiles">{tiles}</div><div class="tiles">{now}</div>
<h2>Where the closed positions are</h2>
<div class="wrap"><input type="radio" name="view" id="v-recent" checked><input type="radio" name="view" id="v-period">
<div class="toggle" role="group" aria-label="Time window for the grids"><label for="v-recent">Last {n} days (closed now)</label><label for="v-period">Whole period</label></div>
<div class="grids">{grids}</div></div>
<div class="legend" aria-label="Share of time a position was closed">{legend}</div>
<h2>Positions closed the most</h2>
<div class="card scroll"><table><tr><th>Side</th><th>Position</th><th>Location</th><th>Last {n} days</th><th>Whole period</th><th>Status</th></tr>{ranked_rows(data)}</table></div>
<h2>Daily share of positions able to test</h2><div class="card">{line_svg(sides)}
<div class="legend"><span><i class="k0"></i>Front</span><span><i class="k1"></i>Rear</span><span><i class="kb"></i>band = plausible range of the month average</span></div></div>
<details><summary>Table view of the daily numbers</summary><div class="scroll"><table><tr><th>Day</th>{"".join(f"<th>{k.capitalize()}</th>" for k in sides)}</tr>{rows}</table></div></details>
<div id="tip" aria-hidden="true"></div><div id="live" class="sr" aria-live="polite"></div></main><script>{JS}</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description="Test-position heatmap and capacity report (HTML)")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--start", default=cio.DEFAULT_START)
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN)
    ap.add_argument("--recent-days", type=int, default=7)
    ap.add_argument("--output", default=str(cio.REPO_ROOT / "out" / "site_heatmap.html"))
    args = ap.parse_args()

    data = collect(args.data_dir, args.start, args.near_full_min, args.recent_days)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(data), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
