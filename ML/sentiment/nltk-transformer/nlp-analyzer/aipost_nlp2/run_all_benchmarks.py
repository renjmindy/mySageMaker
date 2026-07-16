"""
Auto-discovers every pipeline script in this directory (a script counts as a
"pipeline" if it defines a locally-declared class exposing an `analyze(df)`
method), runs each one against test_data.csv, merges their per-row Dict/JSON
outputs into a single aligned table, and renders a structured Markdown
performance report.

Usage: python run_all_benchmarks.py
"""

from __future__ import annotations

import gc
import importlib.util
import inspect
import json
import os
import resource
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Type

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "test_data.csv")
JSON_OUT_PATH = os.path.join(HERE, "benchmark_merged_results.json")
REPORT_OUT_PATH = os.path.join(HERE, "mle_nlp_report.md")

SELF_NAME = os.path.basename(__file__)


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #


def discover_pipelines(directory: str) -> List[Dict[str, Any]]:
    """
    Scan `directory` for *.py files (excluding this script) that define at
    least one class, declared in that module, with an `analyze` method. That
    class is treated as the pipeline's entry point.
    """
    pipelines: List[Dict[str, Any]] = []
    for fname in sorted(os.listdir(directory)):
        if not fname.endswith(".py") or fname == SELF_NAME:
            continue
        path = os.path.join(directory, fname)
        modname = f"_pipeline_{fname[:-3]}"
        spec = importlib.util.spec_from_file_location(modname, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        found_cls = None
        for _, obj in vars(module).items():
            if (
                inspect.isclass(obj)
                and obj.__module__ == modname
                and hasattr(obj, "analyze")
            ):
                found_cls = obj
                break

        if found_cls is not None:
            pipelines.append({"file": fname, "cls": found_cls})

    return pipelines


# --------------------------------------------------------------------------- #
# Benchmark execution
# --------------------------------------------------------------------------- #


def peak_rss_mb() -> float:
    # ru_maxrss is KB on Linux, bytes on macOS; this project only targets Linux.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def run_one_pipeline(entry: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
    fname = entry["file"]
    cls: Type = entry["cls"]
    print(f"\n=== Running {fname} ({cls.__name__}) ===", flush=True)

    record: Dict[str, Any] = {
        "file": fname,
        "class": cls.__name__,
        "status": "ERROR",
    }
    try:
        t0 = time.time()
        instance = cls()
        t1 = time.time()

        result_df = instance.analyze(df)
        t2 = time.time()

        new_cols = [c for c in result_df.columns if c not in df.columns]

        record.update(
            {
                "status": "OK",
                "device": getattr(instance, "device", "unknown"),
                "init_s": round(t1 - t0, 3),
                "inference_s": round(t2 - t1, 3),
                "total_s": round(t2 - t0, 3),
                "peak_rss_mb": round(peak_rss_mb(), 1),
                "new_columns": new_cols,
                "result_df": result_df,
            }
        )
        print(
            f"  OK  init={record['init_s']}s  inference={record['inference_s']}s  "
            f"total={record['total_s']}s  device={record['device']}  "
            f"new_columns={new_cols}",
            flush=True,
        )
    except Exception as exc:  # noqa: BLE001 - deliberately broad: one pipeline's
        # failure must not abort the batch; the exception is captured and
        # surfaced in the report instead.
        record["error"] = f"{type(exc).__name__}: {exc}"
        print(f"  ERROR  {record['error']}", flush=True)
    finally:
        gc.collect()

    return record


def merge_results(df: pd.DataFrame, records: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Left-join every pipeline's new column(s) back onto a copy of the original
    dataframe, positionally (all pipelines were run against the identical,
    unmutated `df`, so row count/order is guaranteed aligned).
    """
    merged = df.copy()
    for rec in records:
        if rec["status"] != "OK":
            continue
        result_df = rec["result_df"]
        for col in rec["new_columns"]:
            merged[f"{rec['file']}::{col}"] = result_df[col].values
    return merged


# --------------------------------------------------------------------------- #
# Report rendering
# --------------------------------------------------------------------------- #


def _preview(text: Any, limit: int = 90) -> str:
    if pd.isna(text):
        return "*(missing/None)*"
    s = str(text)
    if s.strip() == "":
        return "*(empty/whitespace string)*"
    if len(s) <= limit:
        return s
    return f"{s[:limit]}... _(truncated, {len(s)} chars total)_"


def render_report(df: pd.DataFrame, records: List[Dict[str, Any]], merged: pd.DataFrame) -> str:
    now = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines: List[str] = []
    lines.append("# MLE NLP Pipeline Benchmark Report")
    lines.append("")
    lines.append(f"- **Generated:** {now}")
    lines.append(f"- **Test dataset:** `test_data.csv` ({len(df)} rows)")
    lines.append(f"- **Pipelines discovered:** {len(records)}")
    lines.append("")

    lines.append("## 1. Test Dataset Overview")
    lines.append("")
    lines.append(
        "Deliberately adversarial/boundary rows: missing values (NaN/None), "
        "heavy double-negation / counterfactual-relief syntax, and an "
        "extremely long review (to exercise 512/1024-token truncation)."
    )
    lines.append("")
    lines.append("| Row | Preview | Chars |")
    lines.append("|---|---|---|")
    for i, text in enumerate(df["review_text"]):
        chars = 0 if pd.isna(text) else len(str(text))
        lines.append(f"| {i} | {_preview(text)} | {chars} |")
    lines.append("")

    lines.append("## 2. Performance Summary")
    lines.append("")
    lines.append("| Script | Class | Status | Device | Init (s) | Inference (s) | Total (s) | Peak RSS (MB) | New Columns |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for rec in records:
        if rec["status"] == "OK":
            lines.append(
                f"| `{rec['file']}` | `{rec['class']}` | OK | {rec['device']} | "
                f"{rec['init_s']} | {rec['inference_s']} | {rec['total_s']} | "
                f"{rec['peak_rss_mb']} | {', '.join(rec['new_columns'])} |"
            )
        else:
            lines.append(
                f"| `{rec['file']}` | `{rec['class']}` | **ERROR** | - | - | - | - | - | "
                f"{rec.get('error', 'unknown error')} |"
            )
    lines.append("")

    lines.append("## 3. Per-Row Merged Results")
    lines.append("")
    merged_cols = [c for c in merged.columns if c != "review_text"]
    header = ["Row", "Review (preview)"] + merged_cols
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    for i, row in merged.iterrows():
        cells = [str(i), _preview(row["review_text"])]
        for col in merged_cols:
            val = row[col]
            cells.append(f"`{json.dumps(val, ensure_ascii=False)}`")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    lines.append("## 4. Artifacts")
    lines.append("")
    lines.append("- Full merged per-row results (JSON): `benchmark_merged_results.json`")
    lines.append("- This report: `mle_nlp_report.md`")
    lines.append("")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main() -> None:
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} rows from test_data.csv", flush=True)

    pipelines = discover_pipelines(HERE)
    print(
        f"Discovered {len(pipelines)} pipeline(s): {[p['file'] for p in pipelines]}",
        flush=True,
    )

    records = [run_one_pipeline(p, df) for p in pipelines]
    merged = merge_results(df, records)

    # JSON output: NaN must become null, not "NaN" (invalid JSON).
    json_records = merged.where(pd.notnull(merged), None).to_dict(orient="records")
    with open(JSON_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(json_records, f, ensure_ascii=False, indent=2)
    print(f"\nWrote merged results JSON: {JSON_OUT_PATH}", flush=True)

    report = render_report(df, records, merged)
    with open(REPORT_OUT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Wrote report: {REPORT_OUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
