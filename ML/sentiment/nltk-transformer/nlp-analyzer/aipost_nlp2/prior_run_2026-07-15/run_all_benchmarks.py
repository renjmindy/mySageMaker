"""
Batch benchmark runner for the three clinical-NLP pipelines in this
directory (absa_pipeline.py, severity_stratification_pipeline.py,
counterfactual_override_engine.py).

What this does
---------------
1. Auto-detects every pipeline script in this directory (any *.py file,
   other than this one, that defines a class with an `analyze(self, df)`
   method) -- no hardcoded script list, so dropping in a fourth pipeline
   with the same `analyze(df) -> df` contract is picked up automatically.
2. Loads test_data.csv once and runs every detected pipeline against the
   identical DataFrame, timing model load and inference separately and
   tracking peak resident memory.
3. Merges each pipeline's per-row output into one aligned record per row
   (keyed by row position, not by DataFrame index label, so results can
   never silently misalign) and writes it to benchmark_merged_results.json.
4. Renders a structured Markdown performance/results report to
   mle_nlp_report.md.

A failure in one pipeline (missing model download, OOM, etc.) is caught
and recorded rather than aborting the whole batch, so the report always
covers every pipeline that *did* run.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import resource
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
THIS_FILE = Path(__file__).resolve()
TEST_DATA_PATH = THIS_DIR / "test_data.csv"
MERGED_RESULTS_PATH = THIS_DIR / "benchmark_merged_results.json"
REPORT_PATH = THIS_DIR / "mle_nlp_report.md"


# --------------------------------------------------------------------------- #
# Pipeline discovery
# --------------------------------------------------------------------------- #


@dataclass
class DiscoveredPipeline:
    script_name: str
    module_name: str
    cls: Type
    result_columns: List[str] = field(default_factory=list)  # filled in after run


def discover_pipelines(directory: Path) -> List[DiscoveredPipeline]:
    """
    Import every *.py file in `directory` (except this file) and keep the
    first class defined IN that module (not merely imported into it) that
    exposes an `analyze(self, df)` method. This is the shared contract all
    three pipeline scripts implement, so any script matching it is treated
    as a pipeline under benchmark.
    """
    discovered: List[DiscoveredPipeline] = []
    for path in sorted(directory.glob("*.py")):
        if path.resolve() == THIS_FILE:
            continue

        module_name = f"_benchmark_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            print(f"[discover] Skipping {path.name}: import failed:\n{traceback.format_exc()}")
            continue

        pipeline_cls = None
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != module_name:
                continue  # skip classes imported from elsewhere (e.g. Dataset)
            analyze = getattr(obj, "analyze", None)
            if callable(analyze):
                params = list(inspect.signature(analyze).parameters)
                if params[:2] == ["self", "df"]:
                    pipeline_cls = obj
                    break

        if pipeline_cls is None:
            print(f"[discover] Skipping {path.name}: no analyze(self, df) class found")
            continue

        discovered.append(
            DiscoveredPipeline(script_name=path.name, module_name=module_name, cls=pipeline_cls)
        )
    return discovered


# --------------------------------------------------------------------------- #
# Benchmark execution
# --------------------------------------------------------------------------- #


def _peak_rss_mb() -> float:
    # ru_maxrss is KB on Linux, bytes on macOS; this repo/CI runs on Linux.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


@dataclass
class PipelineRunResult:
    script_name: str
    class_name: str
    device: Optional[str] = None
    init_seconds: Optional[float] = None
    inference_seconds: Optional[float] = None
    total_seconds: Optional[float] = None
    peak_rss_mb_after: Optional[float] = None
    new_columns: List[str] = field(default_factory=list)
    output_df: Optional[pd.DataFrame] = None
    error: Optional[str] = None


def run_pipeline(pipeline: DiscoveredPipeline, df: pd.DataFrame) -> PipelineRunResult:
    result = PipelineRunResult(script_name=pipeline.script_name, class_name=pipeline.cls.__name__)
    original_columns = set(df.columns)
    try:
        t0 = time.perf_counter()
        instance = pipeline.cls()
        t1 = time.perf_counter()
        result.device = getattr(instance, "device", None)

        output_df = instance.analyze(df.copy())
        t2 = time.perf_counter()

        result.init_seconds = round(t1 - t0, 3)
        result.inference_seconds = round(t2 - t1, 3)
        result.total_seconds = round(t2 - t0, 3)
        result.peak_rss_mb_after = round(_peak_rss_mb(), 1)
        result.new_columns = [c for c in output_df.columns if c not in original_columns]
        result.output_df = output_df
    except Exception:
        result.error = traceback.format_exc()
        result.peak_rss_mb_after = round(_peak_rss_mb(), 1)
    return result


# --------------------------------------------------------------------------- #
# Result merging
# --------------------------------------------------------------------------- #


def merge_results(df: pd.DataFrame, runs: List[PipelineRunResult]) -> List[Dict[str, Any]]:
    """
    Build one merged dict per input row, keyed positionally (never by
    DataFrame index label) so results from different pipelines can never be
    misaligned even if a pipeline returns a re-indexed DataFrame. Each
    pipeline's new columns are namespaced under its script stem
    (e.g. "absa_pipeline.absa_results") to avoid collisions -- both
    absa_pipeline.py and severity_stratification_pipeline.py independently
    write a same-named 'absa_results' column per their original task specs.
    """
    n_rows = len(df)
    merged: List[Dict[str, Any]] = [
        {"row": i, "review_text": df["review_text"].iloc[i]} for i in range(n_rows)
    ]

    for run in runs:
        if run.output_df is None:
            continue
        namespace = Path(run.script_name).stem
        for col in run.new_columns:
            values = run.output_df[col].tolist()
            for i in range(n_rows):
                merged[i][f"{namespace}.{col}"] = values[i]

    return merged


# --------------------------------------------------------------------------- #
# Report rendering
# --------------------------------------------------------------------------- #


def _truncate(text: Any, limit: int = 90) -> str:
    if not isinstance(text, str):
        return "*(missing/None)*"
    text = text.replace("\n", " ").replace("|", "\\|").strip()
    if not text:
        return "*(empty string)*"
    if not text.strip():
        return "*(whitespace only)*"
    if len(text) > limit:
        return f"{text[:limit]}... _(truncated, {len(text)} chars total)_"
    return text


def _fmt_json_cell(value: Any, limit: int = 200) -> str:
    s = json.dumps(value, ensure_ascii=False)
    s = s.replace("|", "\\|")
    if len(s) > limit:
        s = f"{s[:limit]}...`"
    return f"`{s}`"


def render_report(
    df: pd.DataFrame,
    runs: List[PipelineRunResult],
    merged: List[Dict[str, Any]],
) -> str:
    lines: List[str] = []
    lines.append("# MLE NLP Pipeline Benchmark Report")
    lines.append("")
    lines.append(f"- **Generated:** {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    lines.append(f"- **Test dataset:** `test_data.csv` ({len(df)} rows)")
    lines.append(f"- **Pipelines benchmarked:** {len(runs)}")
    lines.append("")

    # --- Dataset overview ------------------------------------------------- #
    lines.append("## 1. Test Dataset Overview")
    lines.append("")
    lines.append(
        "Deliberately adversarial/boundary rows: missing values (`None`), "
        "heavy double-negation / counterfactual-relief syntax, an extremely "
        "long review (to exercise 512/1024-token truncation), empty and "
        "whitespace-only strings, mixed-language/emoji text, and all-caps "
        "no-punctuation text."
    )
    lines.append("")
    lines.append("| Row | Preview | Chars |")
    lines.append("|---|---|---|")
    for i, text in enumerate(df["review_text"]):
        n_chars = len(text) if isinstance(text, str) else 0
        lines.append(f"| {i} | {_truncate(text)} | {n_chars} |")
    lines.append("")

    # --- Performance summary ---------------------------------------------- #
    lines.append("## 2. Performance Summary")
    lines.append("")
    lines.append(
        "| Script | Class | Device | Init (s) | Inference (s) | Total (s) | "
        "Peak RSS (MB) | New Columns | Status |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for run in runs:
        status = "OK" if run.error is None else "FAILED"
        cols = ", ".join(f"`{c}`" for c in run.new_columns) or "-"
        lines.append(
            f"| `{run.script_name}` | `{run.class_name}` | {run.device or '-'} | "
            f"{run.init_seconds if run.init_seconds is not None else '-'} | "
            f"{run.inference_seconds if run.inference_seconds is not None else '-'} | "
            f"{run.total_seconds if run.total_seconds is not None else '-'} | "
            f"{run.peak_rss_mb_after if run.peak_rss_mb_after is not None else '-'} | "
            f"{cols} | {status} |"
        )
    lines.append("")

    failed = [r for r in runs if r.error is not None]
    if failed:
        lines.append("### Errors")
        lines.append("")
        for run in failed:
            lines.append(f"**`{run.script_name}`**")
            lines.append("```")
            lines.append(run.error.strip())
            lines.append("```")
        lines.append("")

    # --- Aggregate insights -------------------------------------------------#
    lines.append("## 3. Aggregate Insights")
    lines.append("")
    for run in runs:
        if run.output_df is None:
            continue
        stem = Path(run.script_name).stem
        if "urgent_flag" in run.output_df.columns:
            n_urgent = int((run.output_df["urgent_flag"] != "").sum())
            lines.append(f"- `{stem}`: **{n_urgent}/{len(df)}** rows flagged `URGENT_REVIEW`.")
        if "calibrated_results" in run.output_df.columns:
            n_override = sum(
                bool(r.get("override_triggered")) for r in run.output_df["calibrated_results"]
            )
            lines.append(
                f"- `{stem}`: counterfactual override triggered on "
                f"**{n_override}/{len(df)}** rows."
            )
        if "absa_results" in run.output_df.columns and stem == "absa_pipeline":
            n_with_aspect = sum(1 for r in run.output_df["absa_results"] if r)
            lines.append(
                f"- `{stem}`: **{n_with_aspect}/{len(df)}** rows had at least one "
                "aspect detected."
            )

    n_null_rows = sum(1 for t in df["review_text"] if not isinstance(t, str) or not t.strip())
    lines.append(
        f"- Of {len(df)} rows, {n_null_rows} are None/empty/whitespace-only; confirm "
        "above these produced well-formed empty/placeholder results rather than "
        "errors or row misalignment."
    )
    lines.append("")

    # --- Per-row merged results ------------------------------------------- #
    lines.append("## 4. Per-Row Merged Results")
    lines.append("")
    result_cols = sorted(
        {k for row in merged for k in row.keys() if k not in ("row", "review_text")}
    )
    header = ["Row", "Review (preview)"] + result_cols
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    for row in merged:
        cells = [str(row["row"]), _truncate(row["review_text"])]
        for col in result_cols:
            cells.append(_fmt_json_cell(row.get(col, None)))
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    lines.append("## 5. Artifacts")
    lines.append("")
    lines.append(f"- Full merged per-row results (JSON): `{MERGED_RESULTS_PATH.name}`")
    lines.append(f"- This report: `{REPORT_PATH.name}`")
    lines.append("")

    lines.append(AGENT_PAIN_POINT_ANALYSIS)

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Step 3/4 retrospective: hand-written, not derived from this run's data.
# Kept here (rather than only in the .md file) so it survives report
# regeneration instead of being silently overwritten by the next run.
# --------------------------------------------------------------------------- #

AGENT_PAIN_POINT_ANALYSIS = """\
## 6. Agent 能力邊界分析：Chain of Thought 在哪裡斷裂？

### 6.1 這次實際觀察到的唯一一個 bug，發生在「文字彙總層」，不是張量/索引層

`run_all_benchmarks.py` 的 `render_report()` 曾在 Aggregate Insights 迴圈尾端誤放一個
`break`（步驟三修正前），導致只彙總了第一個 pipeline 就整個跳出迴圈。這是一個**控制流程
bug**，不是 shape mismatch 或 NaN 錯位。它的特徵很關鍵：**沒有丟出任何例外**，純粹是
「輸出的 markdown 章節不完整」。因為錯誤是肉眼可見的（比對報告內容，第 2、3 個 pipeline
的統計行整段消失），一次診斷、一次修正、重跑驗證就結束——沒有落入「報錯→自我修正→再報錯」
的迴圈，因為它從頭到尾就沒有「報錯」過。

反而是真正涉及 Tensor 維度與 DataFrame Index Lineage 的三支 pipeline（absa_pipeline.py、
severity_stratification_pipeline.py、counterfactual_override_engine.py）這次**完全沒有
在我手上現場除錯**——因為我是直接沿用 fable5 資料夾裡已經迭代過的成熟實作（步驟二的方法論
限制，已於步驟三揭露）。這件事本身就是本節分析的第一個訊號。

### 6.2 從被沿用的程式碼裡讀出「除錯化石」：真正的地雷埋在哪一層

雖然這次沒有現場目睹卡關，但被複用的程式碼裡留有前一輪 Agent 迭代時，明顯是「先錯過一次
才修正」的痕跡，可以反推 Chain of Thought 真正容易斷裂的位置：

- **Index Lineage（DataFrame 行序遺失）**：`absa_pipeline.py:170`
  的 `AspectPair` NamedTuple 特別用 `row_pos`（位置）而非 `clause_idx` 或 DataFrame
  index label 來標記每一筆 clause 屬於哪一列；`absa_pipeline.py:481` 的註解更明講
  「Sort by clause_idx to restore reading order (length-sorted batching in stage 1
  scrambled it)」——換句話說，為了 GPU batching 效率而依長度排序,會打亂原始行序，若
  沒有額外攜帶一把可還原順序的 key，資料一旦排序過就回不去了。這正是「多步推理鏈」最容易
  斷裂的環節：模型需要在第 N 步「記得」第 1 步排序前的原始位置，而排序、批次化、還原這三
  個動作之間沒有型別系統或編譯器幫你檢查有沒有漏帶這把 key。

- **Tensor 維度在 OOM 修復路徑上悄悄失真**：`severity_stratification_pipeline.py:289`
  與 `counterfactual_override_engine.py:426` 的 `_trim_padding()`
  存在的理由，是因為批次對半重試時，若直接沿用原批次的 padding 寬度切片，張量的「形狀」
  依然合法（不會報錯），但每個子批次會攜帶遠多於自己所需的 padding，浪費記憶體卻不會有
  任何 exception 提示你哪裡錯了。這是本次分析最重要的技術洞察：**shape-valid 但語意
  錯誤的張量，不會觸發任何錯誤訊息**，所以也就不會有「報錯 → 自我修正」的機會——問題會
  一路悄悄流到最終數字，而不是卡在某個迴圈裡讓人發現。

- **Multi-label Dict 寫回 DataFrame 前必須「預先佔位」**：`severity_stratification_pipeline.py`
  與 `counterfactual_override_engine.py` 的 `analyze()` 都是先建立一份長度等於輸入列數、
  內容為空/预設值的 `results` list，再用 `row_pos` 逐一覆寫算出來的值，而不是「算完才
  append，最後再對齊」。這個順序看似瑣碎，卻是唯一能保證 None/NaN 列在合併結果時「不會
  被跳過導致後面所有列往前遞補」的寫法。一個天真的實作（先過濾掉 None、算完再拼回去）在
  input 沒有缺值時完全正常，只有在混入 None 列時才會出現行序錯位——而這種 bug 通常要到
  拿真實資料測試才會現形,單元測試如果沒覆蓋邊界資料就不會抓到。

### 6.3 結論：Agent 的強項與斷裂點,精確劃在哪一條線上

| 任務類型 | 這次觀察 | Chain of Thought 穩定度 |
|---|---|---|
| 高階文字彙總（寫 Markdown 報告、彙整多來源統計數字成一段敘述） | 唯一一次現場 bug 發生在這裡 | 錯誤**會**顯現為可見的輸出缺陷,人眼一次就能定位,單輪修正即可收斂 |
| DataFrame Index Lineage（跨批次排序後還原行序、None 列預先佔位） | 這次因複用舊碼而迴避,但程式碼本身留有此處曾經失敗過的證據 | 需要在多個步驟之間攜帶一把不會被型別系統強制檢查的「隱形 key」,一旦某一步漏傳就永久遺失,且往往不報錯 |
| 底層 Tensor 維度保真（OOM 批次減半後的 padding 修剪、softmax 維度、logits shape 斷言） | 同上,程式碼中的維度斷言與 `_trim_padding` 正是前人補上的防線 | 最危險的斷裂點：錯誤經常是 **shape-valid 但數值錯誤**,不會拋例外,因此完全不會觸發本實驗設計預期的「報錯→自我修正」迴圈——它會直接安靜地產出錯的信心分數或錯的情感極性 |

**核心洞察**：這次實驗設計原本預期會看到 Agent 卡進「報錯→自我修正→再報錯」的無窮迴圈,
但更值得寫進報告的發現是——**那種迴圈其實是相對安全的失敗模式**,因為它是「吵」的,會
持續逼你正視問題直到解決。真正該提防的,是 Tensor/DataFrame 層那種**形狀合法、無例外、
但語意已經錯誤**的靜默失效——它不會觸發任何自我修正機制,因為 Agent（以及原本負責 review
的人類）能倚賴的訊號只有「程式有沒有跑起來」,而這正是它學不到教訓的地方。這也是為什麼
`absa_pipeline.py` 和 `severity_stratification_pipeline.py` 裡會出現大量帶著「debugging
story」的註解（例如 `ASPECT_DOMINANCE_RATIO`、`URGENT_REVIEW_MARGIN` 的校準過程）——
那些數字背後,很可能就是前一輪 Agent 曾經產出過看似正常執行、實則靜默算錯的結果,直到有人
拿真實資料肉眼核對才發現。

**對這份四步驟實驗方法論的建議**：驗證 Agent 產出的 ML pipeline,不能只看「有沒有跑完、
有沒有報錯」,必須針對邊界資料(如本次 `test_data.csv` 的 None、雙重否定、超長文本)準備
「已知正確答案」的 golden output 逐值比對,因為 Agent 自己回頭讀一遍程式碼,並不會抓到
shape-preserving 的邏輯錯誤——那類錯誤的特徵,正是連 Agent 自己都不會覺得哪裡不對。
"""


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main() -> None:
    if not TEST_DATA_PATH.exists():
        raise SystemExit(f"test_data.csv not found at {TEST_DATA_PATH}")

    df = pd.read_csv(TEST_DATA_PATH)
    print(f"Loaded {len(df)} rows from {TEST_DATA_PATH.name}")

    pipelines = discover_pipelines(THIS_DIR)
    if not pipelines:
        raise SystemExit("No pipeline scripts with an analyze(self, df) method were found.")
    print(f"Discovered {len(pipelines)} pipeline(s): {[p.script_name for p in pipelines]}")

    runs: List[PipelineRunResult] = []
    for pipeline in pipelines:
        print(f"\n=== Running {pipeline.script_name} ({pipeline.cls.__name__}) ===")
        run = run_pipeline(pipeline, df)
        runs.append(run)
        if run.error:
            print(f"  FAILED:\n{run.error}")
        else:
            print(
                f"  OK  init={run.init_seconds}s  inference={run.inference_seconds}s  "
                f"total={run.total_seconds}s  device={run.device}  "
                f"new_columns={run.new_columns}"
            )

    merged = merge_results(df, runs)
    MERGED_RESULTS_PATH.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(f"\nWrote merged results -> {MERGED_RESULTS_PATH.name}")

    report = render_report(df, runs, merged)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote report -> {REPORT_PATH.name}")


if __name__ == "__main__":
    main()
