"""
Checks the dashboard spec against the schema, the metric definitions, the data and the backtest.

  * no inline schema: tables and columns come from timescaledb_schema.sql (single source of truth);
    every `table.column` source exists; statuses in the SQL equal the loader's and the recency statuses
  * every panel: known group, known metric, existing sources, a query (unless blocked), thresholds that
    name a defined alert; OEE panels are in the blocked group; data-health panels read only capture data
  * every tagged query runs against a SQLite copy loaded with the real data, returns the declared
    columns and at least the declared rows; P1/P2 equal the headline, P4 equals the rows of P7
  * every alert: rate per week equals the backtest, "page" severity only under about one a week, an owner
    (OPEN = warning), an action; the rejected-rule numbers equal the backtest
  * no stale terms (superseded table, period-based "chronic cluster" alert), no placeholders

Usage:
    python dashboard_spec_check.py
    python dashboard_spec_check.py path/to/spec.md
"""

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "03-data-analysis-investigation/chronic-site-detection/scripts"))
import alert_backtest as ab  # noqa: E402
import build_dashboard_db as bdb  # noqa: E402
import chronic_sites as cs  # noqa: E402
import contactor_io as cio  # noqa: E402

DEFAULT_SPEC = HERE.parents[1] / "assets" / "dashboard_spec_sep_oct_2026.md"
METRIC_YAML = ROOT / "02-documentation-knowledge/semiconductor-metric-definitions/assets/metric_definition.yaml"
GROUPS = {"answer", "diagnosis", "detail", "data-health", "blocked"}
CAPTURE_TABLES = {"contactor_samples", "equipment_daily_metrics"}
STALE = ("site_state_events", "new chronic cluster", "chronic cluster alert")
PAGE_MAX_PER_WEEK = 1.0
TICKET_MAX_PER_WEEK = 3.0
ALERT_IDS_IN_BACKTEST = ("CAP_LOW", "GROUP_LONG", "DQ_FAIL_DAY", "DQ_STALE")


def table(section: str) -> list[dict]:
    rows = [l.strip() for l in section.splitlines() if l.strip().startswith("|")]
    rows = [r for r in rows if not re.match(r"^\|[\s:|-]+\|$", r)]
    if len(rows) < 2:
        return []
    cell = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
    head = [h.lower() for h in cell(rows[0])]
    return [dict(zip(head, cell(r))) for r in rows[1:]]


def section(text: str, title: str) -> str:
    m = re.search(rf"^## {re.escape(title)}\s*$(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
    return m.group(1) if m else ""


def sql_blocks(text: str) -> list[dict]:
    out = []
    for m in re.finditer(r"```sql\n-- (panel|alert): (\w+) \| columns: ([^|\n]*)(?: \| rows: (\d+))?\n(.*?)```", text, re.DOTALL):
        out.append({"kind": m.group(1), "id": m.group(2), "columns": [c.strip() for c in m.group(3).split(",")],
                    "rows": int(m.group(4)) if m.group(4) else None, "sql": m.group(5).strip()})
    return out


def metric_status(yaml_text: str) -> dict[str, str]:
    body = yaml_text.split("\nmetrics:", 1)[1] if "\nmetrics:" in yaml_text else ""
    out = {}
    for block in re.split(r"\n\s*-\s+name:\s*", body)[1:]:
        out[block.splitlines()[0].strip()] = "blocked" if re.search(r"^\s*status:\s*blocked", block, re.MULTILINE) else "active"
    return out


def loader_statuses() -> set[str]:
    src = (ROOT / "lib" / "contactor_io.py").read_text(encoding="utf-8")
    m = re.search(r"status:\s*([A-Z_0-9 |]+)\n", src)
    return {s.strip() for s in m.group(1).split("|")} if m else set()


def recency_statuses() -> set[str]:
    return {cs.recency_status(p, r, q) for p in (0, 0.2, 0.9) for r in (0, 0.05, 0.3, 0.9) for q in (0, 0.3, 0.9)}


def sql_status_sets(schema_sql: str) -> tuple[set[str], set[str]]:
    pat = r"status\s+text\s+NOT NULL CHECK \(status IN \(([^)]*)\)\)"
    found = [{x.strip().strip("'") for x in m.split(",")} for m in re.findall(pat, schema_sql)]
    return (found[0] if found else set()), (found[1] if len(found) > 1 else set())


def check(spec: str, schema_sql: str, metric_yaml: str, con, backtest: dict, headline: dict) -> list[tuple[str, str, str]]:
    res = []
    add = lambda name, status, detail="": res.append((name, status, detail))
    schema = bdb.parse_schema(schema_sql)

    add("no unfilled placeholders", "FAIL" if "[REQUIRED" in spec else "PASS")
    opens = spec.count("[OPEN")
    add("owners and open items named", "WARN" if opens else "PASS", f"{opens} [OPEN] item(s)" if opens else "")

    inline = re.search(r"CREATE TABLE|\(ts timestamptz", spec)
    add("schema not duplicated in the spec", "FAIL" if inline else "PASS" if "timescaledb_schema.sql" in spec else "FAIL",
        "inline schema found" if inline else "" if "timescaledb_schema.sql" in spec else "must point at timescaledb_schema.sql")
    missing = [t for t in schema if f"`{t}`" not in section(spec, "Data model")]
    add("every schema table is named in the data model section", "PASS" if not missing else "FAIL", ", ".join(missing))

    cs_sql, rec_sql = sql_status_sets(schema_sql)
    ok = cs_sql == loader_statuses() and rec_sql == recency_statuses()
    add("schema statuses equal the loader and recency statuses", "PASS" if ok else "FAIL",
        "" if ok else f"samples {sorted(cs_sql ^ loader_statuses())} / recency {sorted(rec_sql ^ recency_statuses())} differ")

    metrics = metric_status(metric_yaml)
    panels = table(section(spec, "Panels"))
    alerts = table(section(spec, "Alerts"))
    blocks = sql_blocks(spec)
    q = {(b["kind"], b["id"]): b for b in blocks}
    alert_ids = {a["id"] for a in alerts}

    problems = []
    for p in panels:
        pid = p["id"]
        if p["group"] not in GROUPS:
            problems.append(f"{pid}: unknown group {p['group']}")
        if p["metric"] not in ("-", *metrics):
            problems.append(f"{pid}: unknown metric {p['metric']}")
        for src in [s.strip() for s in p["source"].split(",") if s.strip() and s.strip() != "-"]:
            t, _, c = src.partition(".")
            if t not in schema or c not in [col for col, _ in schema[t]]:
                problems.append(f"{pid}: source {src} not in the schema")
        blocked_metric = metrics.get(p["metric"]) == "blocked" or "oee" in (p["metric"] + p["notes"]).lower()
        if blocked_metric and p["group"] != "blocked":
            problems.append(f"{pid}: OEE / blocked metric outside the blocked group")
        if p["group"] == "blocked":
            if "BLOCKED" not in p["notes"]:
                problems.append(f"{pid}: blocked panel must say BLOCKED")
            if ("panel", pid) in q:
                problems.append(f"{pid}: blocked panel must not have a query")
        elif ("panel", pid) not in q:
            problems.append(f"{pid}: no query")
        if p["group"] == "data-health":
            tabs = {s.strip().partition(".")[0] for s in p["source"].split(",")}
            if not tabs <= CAPTURE_TABLES:
                problems.append(f"{pid}: data-health panel reads {sorted(tabs - CAPTURE_TABLES)} (equipment data)")
        for a in re.findall(r"\b([A-Z]+_[A-Z_]+)\b", p["thresholds"]):
            if a not in alert_ids:
                problems.append(f"{pid}: threshold names undefined alert {a}")
    for kind, qid in q:
        if kind == "panel" and qid not in {p["id"] for p in panels}:
            problems.append(f"query {qid} has no panel")
    add("panels consistent with schema, metrics and alerts", "PASS" if not problems else "FAIL", "; ".join(problems))

    groups = [p["group"] for p in panels]
    gaps = [g for g in ("answer", "diagnosis", "detail") if g not in groups] + (["data-health (needs 2)"] if groups.count("data-health") < 2 else [])
    add("panel groups cover answer, diagnosis, detail and capture health", "PASS" if not gaps else "FAIL", ", ".join(gaps))

    failures, results = [], {}
    for b in blocks:
        sql = re.sub(r"\$__timeFilter\(\w+\)", "1=1", b["sql"])
        try:
            cur = con.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
        except Exception as e:  # noqa: BLE001
            failures.append(f"{b['id']}: {str(e)[:70]}")
            continue
        results[(b["kind"], b["id"])] = rows
        if cols != b["columns"]:
            failures.append(f"{b['id']}: columns {cols} != declared {b['columns']}")
        if b["rows"] is not None and len(rows) < b["rows"]:
            failures.append(f"{b['id']}: {len(rows)} rows < declared minimum {b['rows']}")
    add("every query runs and returns what the tag declares", "PASS" if not failures else "FAIL",
        f"{len(blocks)} queries dry-run" if not failures else "; ".join(failures))

    xs = []
    for side, pid in (("front", "P1"), ("rear", "P2")):
        rows = results.get(("panel", pid))
        if not rows or abs(rows[0][0] - headline[side]) > 0.01:
            xs.append(f"{pid} {rows[0][0] if rows else None} vs headline {headline[side]:.2f}")
    p4, p7 = results.get(("panel", "P4")), results.get(("panel", "P7"))
    if p4 and p7:
        for side, n in p4:
            if sum(1 for r in p7 if r[0] == side) != n:
                xs.append(f"P4 closed_now {side}={n} but P7 lists {sum(1 for r in p7 if r[0] == side)}")
    add("headline and closed-now panels match the analysis", "PASS" if not xs else "FAIL", "; ".join(xs))

    al = []
    for a in alerts:
        aid = a["id"]
        try:
            f, r = float(a["front per week"]), float(a["rear per week"])
        except ValueError:
            al.append(f"{aid}: rates not numeric")
            continue
        if aid in ALERT_IDS_IN_BACKTEST:
            for side, val in (("front", f), ("rear", r)):
                if abs(backtest[side][aid]["per_week"] - val) > 0.01:
                    al.append(f"{aid} {side}: spec {val} vs backtest {backtest[side][aid]['per_week']}")
        else:
            al.append(f"{aid}: no backtest for this rule")
        cap = PAGE_MAX_PER_WEEK if a["severity"] == "page" else TICKET_MAX_PER_WEEK
        if max(f, r) > cap:
            al.append(f"{aid}: {a['severity']} at {max(f, r)}/week exceeds {cap}")
        if not a["action"] or "[REQUIRED" in a["action"]:
            al.append(f"{aid}: no action")
    add("alerts backtested, tolerable and actionable", "PASS" if not al else "FAIL", "; ".join(al))
    owners = [a["id"] for a in alerts if "[OPEN" in a["owner"]]
    add("alert owners assigned", "WARN" if owners else "PASS", f"unassigned: {', '.join(owners)}" if owners else "")

    rej = section(spec, "Alerts").split("Rejected rules", 1)[-1]
    exp = [f"{backtest['front']['BASELINE']['per_week']:.2f}", f"{backtest['rear']['BASELINE']['per_week']:.2f}",
           f"{backtest['front']['GROUP_ANY']['per_week']:.2f}", f"{backtest['rear']['GROUP_ANY']['per_week']:.2f}"]
    miss = [e for e in exp if e not in rej]
    add("rejected-rule numbers equal the backtest", "PASS" if not miss else "FAIL", f"missing {', '.join(miss)}" if miss else "")

    stale = [t for t in STALE if t in spec.lower()]
    add("no stale terms", "PASS" if not stale else "FAIL", ", ".join(stale))
    rr = section(spec, "Refresh and retention").strip()
    add("refresh and retention stated", "PASS" if rr and "[REQUIRED" not in rr else "FAIL")
    return res


def main():
    ap = argparse.ArgumentParser(description="Dashboard spec checker")
    ap.add_argument("spec", nargs="?", default=str(DEFAULT_SPEC))
    args = ap.parse_args()
    con = bdb.build(":memory:")
    headline = {s: cio.weighted_availability(cio.load_side(s)) * 100 for s in cio.SIDES}
    res = check(Path(args.spec).read_text(encoding="utf-8"), bdb.SCHEMA_SQL.read_text(encoding="utf-8"),
                METRIC_YAML.read_text(encoding="utf-8"), con, ab.backtest(), headline)
    for name, status, detail in res:
        print(f"[{status:4s}] {name:58s} {detail}")
    fails = sum(1 for _, s, _ in res if s == "FAIL")
    print(f"\n{len(res)} checks: {fails} FAIL, {sum(1 for _, s, _ in res if s == 'WARN')} WARN")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
