"""
Export the dashboard tables as CSV files plus a load script for PostgreSQL / TimescaleDB.

The pipeline builds the six tables in a SQLite copy of `assets/timescaledb_schema.sql`. This turns them into files
a database owner can load: one CSV per table (array columns written in PostgreSQL's {a,b} form, NULL as an empty
field) and `load.sql` with one \copy per table. It is an INITIAL LOAD into an empty schema: rerunning it into tables
that already hold rows would duplicate the tables without a primary key, and the key policy for incremental loads
(replace a day, replace a handler, upsert) is the data owner's decision. Nothing here connects to a database, and
the load script has not been run against one.

Usage:
    python export_for_postgres.py --db ../../../out/dashboard.sqlite --output out/pipeline/<run>/postgres
"""

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "04-data-storytelling-visualization/dashboard-specification/scripts"))
import build_dashboard_db as bdb  # noqa: E402


def pg_array(value):
    """'[1, 2]' (JSON text, as stored in SQLite) -> '{1,2}'; None stays None."""
    if value is None:
        return None
    return "{" + ",".join(str(int(x)) for x in json.loads(value)) + "}"


def export(db: Path, out_dir: Path, schema_sql: str | None = None) -> dict[str, int]:
    schema = bdb.parse_schema(schema_sql or bdb.SCHEMA_SQL.read_text(encoding="utf-8"))
    con = sqlite3.connect(db)
    out_dir.mkdir(parents=True, exist_ok=True)
    counts, lines = {}, ["-- Initial load into an EMPTY schema (see export_for_postgres.py). Create the tables first:",
                         "--   psql -f assets/timescaledb_schema.sql", "BEGIN;"]
    for table, cols in schema.items():
        names = [c for c, _ in cols]
        arrays = {c for c, t in cols if "[]" in t}
        rows = con.execute(f"SELECT {', '.join(names)} FROM {table}").fetchall()
        with open(out_dir / f"{table}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(names)
            for r in rows:
                w.writerow([pg_array(v) if n in arrays else v for n, v in zip(names, r)])
        counts[table] = len(rows)
        lines.append(f"\\copy {table} ({', '.join(names)}) FROM '{table}.csv' WITH (FORMAT csv, HEADER true)")
    lines.append("COMMIT;")
    (out_dir / "load.sql").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return counts


def main():
    ap = argparse.ArgumentParser(description="Export the dashboard tables for PostgreSQL")
    ap.add_argument("--db", default=str(ROOT / "out" / "dashboard.sqlite"))
    ap.add_argument("--output", default=str(ROOT / "out" / "postgres"))
    args = ap.parse_args()
    if not Path(args.db).exists():
        sys.exit(f"no dashboard database at {args.db}; run build_dashboard_db.py first")
    for t, n in export(Path(args.db), Path(args.output)).items():
        print(f"{t:26s} {n:>7d} rows")
    print(f"wrote {args.output}/load.sql (initial load; not run against a database)")


if __name__ == "__main__":
    main()
