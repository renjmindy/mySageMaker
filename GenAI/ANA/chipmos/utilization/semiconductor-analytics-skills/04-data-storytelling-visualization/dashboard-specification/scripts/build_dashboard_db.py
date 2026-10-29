"""
Build a SQLite copy of the dashboard data model and load it with the cleaned handler data, so the
spec's panel queries can be dry-run without a Postgres/Timescale server.

The schema is NOT redefined here: it is parsed from the single source of truth
(06-workflow-optimization/pipeline-automation/assets/timescaledb_schema.sql) and translated:
timestamptz/date -> TEXT (ISO), boolean -> INTEGER, arrays -> TEXT holding JSON, hypertable calls dropped.

Dialect differences to remember when moving queries to Postgres: now() instead of a literal clock,
Grafana macros ($__timeFilter), array functions, true boolean comparisons.

Usage:
    python build_dashboard_db.py                         # writes out/dashboard.sqlite
    python build_dashboard_db.py --output /tmp/x.sqlite --handler M6242
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
SCHEMA_SQL = ROOT / "06-workflow-optimization/pipeline-automation/assets/timescaledb_schema.sql"
sys.path.insert(0, str(ROOT / "lib"))
for sub in ("03-data-analysis-investigation/chronic-site-detection/scripts",
            "03-data-analysis-investigation/closure-event-root-cause/scripts",
            "03-data-analysis-investigation/downtime-time-series/scripts",
            "03-data-analysis-investigation/site-availability/scripts"):
    sys.path.insert(0, str(ROOT / sub))
import chronic_sites as cs  # noqa: E402
import closure_events as ce  # noqa: E402
import contactor_io as cio  # noqa: E402
import daily_trend as dt  # noqa: E402
import site_availability as sa  # noqa: E402

TYPE_MAP = {"timestamptz": "TEXT", "date": "TEXT", "text": "TEXT", "integer": "INTEGER", "bigint": "INTEGER",
            "real": "REAL", "boolean": "INTEGER", "integer[]": "TEXT"}


def parse_schema(sql: str) -> dict[str, list[tuple[str, str]]]:
    """table -> [(column, postgres type)] from the CREATE TABLE statements."""
    tables = {}
    for name, body in re.findall(r"CREATE TABLE IF NOT EXISTS (\w+) \((.*?)\n\);", sql, flags=re.DOTALL):
        cols = []
        for line in body.splitlines():
            line = re.sub(r"--.*", "", line).strip().rstrip(",")
            if not line or re.match(r"(PRIMARY KEY|CHECK|UNIQUE)\b", line, re.IGNORECASE):
                continue
            col, typ = line.split()[:2]
            cols.append((col, typ.rstrip(",")))
        tables[name] = cols
    return tables


def to_sqlite(sql: str) -> str:
    out = re.sub(r"SELECT create_hypertable\(.*?\);", "", sql, flags=re.DOTALL)
    out = re.sub(r"--[^\n]*", "", out)
    out = out.replace("DEFAULT '{}'", "DEFAULT '[]'")
    for pg, lite in sorted(TYPE_MAP.items(), key=lambda kv: -len(kv[0])):
        out = re.sub(rf"(?<=\s){re.escape(pg)}(?=[\s,])", lite, out)
    return out


def _iso(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def build(output: str | Path = ":memory:", handler: str = "unspecified", recent_days: int = 7,
          data_dir=None, start: str = cio.DEFAULT_START) -> sqlite3.Connection:
    con = sqlite3.connect(str(output))
    con.executescript(to_sqlite(SCHEMA_SQL.read_text(encoding="utf-8")))
    event_id = 0
    for side in cio.SIDES:
        df = cio.load_side(side, data_dir, start)
        con.executemany(
            "INSERT INTO contactor_samples VALUES (?,?,?,?,?,?,?,?)",
            [(_iso(r.timestamp), handler, side, int(r.err_01), json.dumps([int(x) for x in r.sites]), r.status,
              int(r.valid), float(r.weight_min)) for r in df.itertuples()])

        # closure episodes / events from consistent readings, as in closure_events.py
        keep = df["valid"] & (df["n_closed"] <= 100) & ~df["count_mismatch"]
        mat = cio.closed_matrix(df.assign(valid=keep), side)
        ep = ce.closure_episodes(mat)
        con.executemany("INSERT INTO closure_episodes VALUES (?,?,?,?,?,?,?,?)",
                        [(handler, side, int(r.site), _iso(r.start), _iso(r.end), float(r.duration_min), int(r.ongoing), int(r.left_censored))
                         for r in ep.itertuples()])
        ev = ce.group_events(ep)
        rows = []
        for r in ev.itertuples():
            event_id += 1
            rows.append((event_id, handler, side, _iso(r.start), _iso(r.end), float(r.duration_min), int(r.n_sites),
                         json.dumps([int(x) for x in r.sites]), float(r.block_aligned), int(r.n_blocks_2x2), int(r.ongoing), int(r.left_censored)))
        con.executemany("INSERT INTO closure_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)

        # per-site recency (same matrix as chronic_sites.py: all valid readings)
        m_all = cio.closed_matrix(df, side)
        period = cs.closure_share(m_all)
        cutoff = m_all.index.max() - pd.Timedelta(days=recent_days)
        recent = cs.window_share(m_all, start=cutoff).reindex(period.index)
        prior = cs.window_share(m_all, end=cutoff).reindex(period.index)
        as_of = _iso(m_all.index.max())
        con.executemany("INSERT INTO site_recency VALUES (?,?,?,?,?,?,?,?)",
                        [(as_of, handler, side, int(s), recent_days, float(period[s]), float(recent[s]),
                          cs.recency_status(period[s], recent[s], prior[s])) for s in period.index])

        # daily metrics incl. data-quality columns
        ts = dt.daily_series(df)
        low = sa.daily_availability(df)
        low.index = pd.to_datetime(low.index)
        con.executemany("INSERT INTO equipment_daily_metrics VALUES (?,?,?,?,?,?,?,?,?)",
                        [(d.strftime("%Y-%m-%d"), handler, side, float(r.availability_pct), float(low.loc[d, "availability_low_pct"]),
                          int(r.valid_samples), int(round(r.valid_samples / (1 - r.fail_pct / 100))) if r.fail_pct < 100 else 0,
                          float(r.fail_pct), float(r.coverage_pct)) for d, r in ts.iterrows()])

        # period summary
        ov = sa.overall(df)
        lo, hi = sa.bootstrap_ci(df)
        con.execute("INSERT INTO capacity_summary VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (_iso(df.timestamp.min())[:10], _iso(df.timestamp.max())[:10], handler, side,
                     cio.weighted_availability(df) * 100, ov["availability_low_pct"], lo, hi, int((recent >= 0.5).sum()), recent_days))
    con.commit()
    return con


def main():
    ap = argparse.ArgumentParser(description="Build the dashboard SQLite copy")
    ap.add_argument("--output", default=str(cio.REPO_ROOT / "out" / "dashboard.sqlite"))
    ap.add_argument("--handler", default="unspecified", help="the CSVs carry no handler id (catalog entry: open)")
    ap.add_argument("--recent-days", type=int, default=7)
    args = ap.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    con = build(out, args.handler, args.recent_days)
    for t in parse_schema(SCHEMA_SQL.read_text(encoding="utf-8")):
        print(f"{t:26s} {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>7d} rows")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
