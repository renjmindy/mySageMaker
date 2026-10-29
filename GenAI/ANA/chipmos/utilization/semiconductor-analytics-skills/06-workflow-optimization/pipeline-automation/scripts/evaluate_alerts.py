"""
Evaluate the dashboard spec's alert rules against the dashboard database and say which are firing now.

  * GROUP_LONG, DQ_FAIL_DAY - the spec's tagged `alert:` queries; a row returned means the alert fires.
    A query that returns days (DQ_FAIL_DAY) lists every bad day in history, so it fires only when the NEWEST day is
    among them; the earlier ones are counted in `earlier_days`
  * CAP_LOW - the last day's availability is below (median - 2 SD) of the previous 28 days, per side
    (the rule alert_backtest.py backtests; needs at least 14 earlier days)
  * DQ_STALE - the last reading of a side is more than 30 minutes older than `now`, per side

This only evaluates. Delivery (who is told, on which channel) is not decided: the alert owners and channels are
open items in the spec. The pipeline passes the firing alerts to the notification hook, if one is configured.

Usage:
    python evaluate_alerts.py --db ../../../out/dashboard.sqlite --output alerts.json
    python evaluate_alerts.py --db x.sqlite --now 2026-10-02T15:30
"""

import argparse
import datetime as dt
import json
import re
import sqlite3
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "04-data-storytelling-visualization/dashboard-specification/scripts"))
import dashboard_spec_check as dsc  # noqa: E402

CAP_MIN_DAYS, CAP_WINDOW, STALE_MINUTES = 14, 28, 30
SIDES = ("front", "rear")


def _rows(con, sql, args=()):
    cur = con.execute(sql, args)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def evaluate(con: sqlite3.Connection, spec_text: str, now: dt.datetime) -> list[dict]:
    out = []
    last_day = con.execute("SELECT MAX(day) FROM equipment_daily_metrics").fetchone()[0]
    for blk in dsc.sql_blocks(spec_text):
        if blk["kind"] != "alert":
            continue
        rows = _rows(con, re.sub(r"\$__timeFilter\(\w+\)", "1=1", blk["sql"]))
        item = {"id": blk["id"], "scope": "all"}
        if "day" in blk["columns"]:
            # a daily alert means "the newest day is bad": the query lists every bad day in history
            now_rows = [r for r in rows if r["day"] == last_day]
            item.update(firing=bool(now_rows), count=len(now_rows), detail=now_rows[:5], earlier_days=len(rows) - len(now_rows))
        else:
            item.update(firing=bool(rows), count=len(rows), detail=rows[:5])
        out.append(item)
    for side in SIDES:
        vals = [(d, v) for d, v in con.execute("SELECT day, site_availability FROM equipment_daily_metrics WHERE side = ? ORDER BY day", (side,)) if v is not None]
        if len(vals) <= CAP_MIN_DAYS:
            out.append({"id": "CAP_LOW", "scope": side, "firing": False, "count": 0, "detail": {"note": f"only {len(vals)} days of history, at least {CAP_MIN_DAYS + 1} needed"}})
            continue
        base = [v for _, v in vals[-1 - CAP_WINDOW:-1]]
        threshold = statistics.median(base) - 2 * statistics.stdev(base)
        day, value = vals[-1]
        out.append({"id": "CAP_LOW", "scope": side, "firing": value < threshold, "count": int(value < threshold),
                    "detail": {"day": day, "availability_pct": round(value, 2), "threshold_pct": round(threshold, 2)}})
        last = con.execute("SELECT MAX(ts) FROM contactor_samples WHERE side = ?", (side,)).fetchone()[0]
        age = (now - dt.datetime.fromisoformat(last)).total_seconds() / 60 if last else None
        out.append({"id": "DQ_STALE", "scope": side, "firing": age is None or age > STALE_MINUTES, "count": int(age is None or age > STALE_MINUTES),
                    "detail": {"last_reading": last, "age_minutes": None if age is None else int(age), "limit_minutes": STALE_MINUTES}})
    return out


def main():
    ap = argparse.ArgumentParser(description="Evaluate the dashboard alert rules")
    ap.add_argument("--db", default=str(ROOT / "out" / "dashboard.sqlite"))
    ap.add_argument("--spec", default=str(dsc.DEFAULT_SPEC))
    ap.add_argument("--output", default=None)
    ap.add_argument("--now", default=None, help="ISO time to treat as now (default: the clock)")
    args = ap.parse_args()
    if not Path(args.db).exists():
        sys.exit(f"no dashboard database at {args.db}; run build_dashboard_db.py first")
    now = dt.datetime.fromisoformat(args.now) if args.now else dt.datetime.now()
    res = evaluate(sqlite3.connect(args.db), Path(args.spec).read_text(encoding="utf-8"), now)
    for a in res:
        print(f"{a['id']:12s} {a['scope']:6s} {'FIRING' if a['firing'] else 'quiet ':6s} {json.dumps(a['detail'])[:110]}")
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps({"evaluated_at": now.isoformat(timespec="minutes"), "alerts": res}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
