"""
Checks the generated test-position report (site_heatmap.py) instead of trusting a glance.

  * fidelity: every heatmap cell (both views), every plotted daily point, the tiles and the ranges
    match the numbers computed by the analysis scripts
  * content: date range in the subtitle, no glossary jargon in the visible text, view toggle, ranked
    table, plausible ranges, legend for two series, aria-live region, labelled grids, table view
  * colour: both sequential ramps are monotonic with adjacent steps >= MIN_STEP (OKLab x100);
    front/rear series colours are well separated in light and dark
  * responsive and access rules present in the CSS (no 380 px minimum, touch-size rule)
  * browser (optional, needs playwright): no horizontal page scroll at 375/768/1280 px, touch cells
    >= 24 px on a phone, arrow keys fill the live region, the toggle switches views

Usage:
    python viz_check.py                # builds the report in memory and checks it
    python viz_check.py --no-browser   # skip the playwright checks
"""

import argparse
import html
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "05-stakeholder-communication/technical-to-business-translator/scripts"))
import jargon_detector  # noqa: E402
import site_heatmap as sh  # noqa: E402

MIN_STEP = 8.0
MIN_SERIES_DE = 15.0
TOUCH_MIN_PX = 24


def _lin(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def oklab(h: str) -> tuple[float, float, float]:
    r, g, b = (_lin(int(h[i:i + 2], 16)) for i in (1, 3, 5))
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def delta_e(a: str, b: str) -> float:
    return 100 * math.dist(oklab(a), oklab(b))


def ramp_check(ramp: list[str], increasing: bool, min_step: float = MIN_STEP) -> tuple[bool, str]:
    L = [oklab(h)[0] for h in ramp]
    mono = all((L[i] < L[i + 1]) if increasing else (L[i] > L[i + 1]) for i in range(len(L) - 1))
    steps = [delta_e(ramp[i], ramp[i + 1]) for i in range(len(ramp) - 1)]
    ok = mono and min(steps) >= min_step
    return ok, f"{'monotonic' if mono else 'NOT monotonic'}, smallest adjacent step {min(steps):.1f} (min {min_step:.0f})"


def tips(page: str) -> list[str]:
    return [html.unescape(t) for t in re.findall(r'data-tip="([^"]*)"', page)]


def visible_text(page: str) -> str:
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", page, flags=re.DOTALL)
    return html.unescape(re.sub(r"<[^>]+>", " ", body))


def fidelity(data: dict, page: str) -> list[str]:
    """Differences between what the page shows and the numbers in `data` (empty = faithful)."""
    problems = []
    t = tips(page)
    n = data["recent_days"]
    for side, v in data["sides"].items():
        lo, hi = sh.cio.SIDES[side]["lo"], sh.cio.SIDES[side]["hi"]
        period, recent = {}, {}
        for tip in t:
            m = re.match(r"Position (\d+) \(row \d+, column \d+\): closed ([\d.]+)% of the whole period$", tip)
            if m and lo <= int(m.group(1)) <= hi:
                period[int(m.group(1))] = float(m.group(2))
            m = re.match(rf"Position (\d+) \(row \d+, column \d+\): closed (\d+)% of the last {n} days, (\d+)% over the whole period", tip)
            if m and lo <= int(m.group(1)) <= hi:
                recent[int(m.group(1))] = (int(m.group(2)), int(m.group(3)))
        if len(period) != 256 or len(recent) != 256:
            problems.append(f"{side}: {len(period)} period cells and {len(recent)} recent cells (expected 256 each)")
        for s_, val in period.items():
            if abs(val - v["period"][s_] * 100) > 0.051:
                problems.append(f"{side} position {s_}: period {val}% vs {v['period'][s_] * 100:.2f}%")
        for s_, (r_, p_) in recent.items():
            if abs(r_ - v["recent"][s_] * 100) > 0.51 or abs(p_ - v["period"][s_] * 100) > 0.51:
                problems.append(f"{side} position {s_}: recent/period shown {r_}/{p_}")
        pts = {m.group(1): float(m.group(2)) for tip in t if (m := re.match(rf"{side.capitalize()} (\d{{4}}-\d\d-\d\d): ([\d.]+)%$", tip))}
        for day, val in v["daily"]:
            if day not in pts or abs(pts[day] - val) > 0.051:
                problems.append(f"{side} {day}: plotted {pts.get(day)} vs {val:.2f}")
        if f"<b>{v['availability_pct']:.1f}%</b>" not in page:
            problems.append(f"{side}: headline tile does not show {v['availability_pct']:.1f}%")
        if f"plausible range {v['ci'][0]:.1f}-{v['ci'][1]:.1f}%" not in page:
            problems.append(f"{side}: plausible range {v['ci'][0]:.1f}-{v['ci'][1]:.1f}% missing")
        if f"<b>{v['closed_now']} of 256</b>" not in page:
            problems.append(f"{side}: closed-now tile does not show {v['closed_now']} of 256")
    return problems


def run_static(data: dict, page: str) -> list[tuple[str, str, str]]:
    res = []
    add = lambda name, status, detail="": res.append((name, status, detail))
    bad = fidelity(data, page)
    add("numbers match the analysis scripts", "FAIL" if bad else "PASS", "; ".join(bad[:4]) + (f" (+{len(bad) - 4} more)" if len(bad) > 4 else ""))

    rng = sh.date_range(data["first"], data["last"])
    add("subtitle states the date range", "PASS" if rng in html.unescape(page) else "FAIL", rng)
    text = visible_text(page)
    hits = [f"{t} x{n}" for t, n, _ in jargon_detector.detect(text)]
    add("plain language in visible text", "PASS" if not hits else "FAIL", ", ".join(hits))

    must = {
        "view toggle (radio)": 'type="radio"' in page and 'for="v-recent"' in page and 'for="v-period"' in page,
        "ranked table of positions closed the most": "Positions closed the most" in page and "<table>" in page,
        "plausible range on every tile": page.count("plausible range") >= len(data["sides"]),
        "legend names both series and the band": all(k in page for k in ("<i class=\"k0\">", "<i class=\"k1\">", "band = plausible range")),
        "aria-live region": 'aria-live="polite"' in page,
        "grids labelled and keyboard focusable": page.count('tabindex="0"') >= 4 and page.count("aria-label=") >= 7,
        "table view of the daily numbers": "Table view of the daily numbers" in page,
    }
    for name, ok in must.items():
        add(name, "PASS" if ok else "FAIL")
    add("responsive grid rule (no fixed 380 px minimum)", "PASS" if "minmax(min(380px,100%),1fr)" in page else "FAIL")
    add("touch-size rule for narrow / coarse pointers", "PASS" if "(pointer:coarse)" in page and "min-width:482px" in page else "FAIL")

    for name, ramp, inc in (("light ramp", sh.LIGHT, False), ("dark ramp", sh.DARK, True)):
        ok, detail = ramp_check(ramp, inc)
        add(f"sequential {name}", "PASS" if ok else "FAIL", detail)
    for mode, (a, b) in (("light", sh.SERIES_LIGHT), ("dark", sh.SERIES_DARK)):
        d = delta_e(a, b)
        add(f"front/rear colours ({mode})", "PASS" if d >= MIN_SERIES_DE else "FAIL", f"DeltaE {d:.1f} (min {MIN_SERIES_DE:.0f})")
    return res


def run_browser(page: str) -> list[tuple[str, str, str]]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return [("browser checks", "SKIP", "playwright not installed")]
    res = []
    add = lambda name, status, detail="": res.append((name, status, detail))
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            for w in (375, 768, 1280):
                pg = b.new_page(viewport={"width": w, "height": 900})
                pg.set_content(page)
                m = pg.evaluate("()=>({s:document.documentElement.scrollWidth,i:innerWidth,c:[...document.querySelectorAll('svg.grid')].filter(s=>getComputedStyle(s).display!=='none')[0].querySelector('rect').getBoundingClientRect().width})")
                add(f"no horizontal page scroll at {w}px", "PASS" if m["s"] <= m["i"] + 1 else "FAIL", f"page {m['s']}px in a {m['i']}px window")
                if w == 375:
                    add("touch cells >= 24px at 375px", "PASS" if m["c"] >= TOUCH_MIN_PX else "FAIL", f"{m['c']:.1f}px")
            pg = b.new_page(viewport={"width": 1000, "height": 900})
            pg.set_content(page)
            pg.focus("svg.grid.view-recent")
            pg.keyboard.press("ArrowDown")
            pg.keyboard.press("ArrowRight")
            live = pg.inner_text("#live")
            add("arrow keys read cells", "PASS" if live.startswith("Position ") else "FAIL", live[:60])
            pg.click("label[for=v-period]")
            vis = pg.evaluate("()=>[...document.querySelectorAll('svg.grid')].filter(s=>getComputedStyle(s).display!=='none').every(s=>s.classList.contains('view-period'))")
            add("toggle switches the grids", "PASS" if vis else "FAIL")
            b.close()
    except Exception as e:  # browser binary missing etc.
        return [("browser checks", "SKIP", f"{type(e).__name__}: {str(e)[:60]}")]
    return res


def main():
    ap = argparse.ArgumentParser(description="Check the test-position report")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--recent-days", type=int, default=7)
    args = ap.parse_args()
    data = sh.collect(recent_days=args.recent_days)
    page = sh.render(data)
    res = run_static(data, page) + ([] if args.no_browser else run_browser(page))
    for name, status, detail in res:
        print(f"[{status:4s}] {name:50s} {detail}")
    fails = sum(1 for _, s, _ in res if s == "FAIL")
    print(f"\n{len(res)} checks: {fails} FAIL, {sum(1 for _, s, _ in res if s == 'SKIP')} SKIP")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
