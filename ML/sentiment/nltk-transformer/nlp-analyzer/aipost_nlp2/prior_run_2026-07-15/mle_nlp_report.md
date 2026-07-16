# MLE NLP Pipeline Benchmark Report

- **Generated:** 2026-07-15 18:38:19 CST
- **Test dataset:** `test_data.csv` (10 rows)
- **Pipelines benchmarked:** 3

## 1. Test Dataset Overview

Deliberately adversarial/boundary rows: missing values (`None`), heavy double-negation / counterfactual-relief syntax, an extremely long review (to exercise 512/1024-token truncation), empty and whitespace-only strings, mixed-language/emoji text, and all-caps no-punctuation text.

| Row | Preview | Chars |
|---|---|---|
| 0 | The doctor's diagnosis was accurate and the surgery went smoothly, though the parking lot ... _(truncated, 145 chars total)_ | 145 |
| 1 | *(missing/None)* | 0 |
| 2 | I can't say I didn't not appreciate the fact that the nurse wasn't uncaring, nor would I d... _(truncated, 265 chars total)_ | 265 |
| 3 | If I hadn't not avoided the surgery, I wouldn't have not survived; it's not that I didn't ... _(truncated, 260 chars total)_ | 260 |
| 4 | From the moment I checked in at the front desk, the entire experience at this clinic unfol... _(truncated, 13199 chars total)_ | 13199 |
| 5 | *(missing/None)* | 0 |
| 6 | *(empty string)* | 3 |
| 7 | Bad. | 4 |
| 8 | 醫生非常好 👍 but the front desk was incredibly rude 😡 and the wait time was unacceptable. | 84 |
| 9 | THE NURSE WAS AMAZING BUT THE WAIT TIME WAS RIDICULOUS AND I WAITED FOR THREE HOURS WITHOU... _(truncated, 132 chars total)_ | 132 |

## 2. Performance Summary

| Script | Class | Device | Init (s) | Inference (s) | Total (s) | Peak RSS (MB) | New Columns | Status |
|---|---|---|---|---|---|---|---|---|
| `absa_pipeline.py` | `ClinicalABSAAnalyzer` | cpu | 6.786 | 47.98 | 54.767 | 2322.4 | `absa_results` | OK |
| `counterfactual_override_engine.py` | `CounterfactualOverrideEngine` | cpu | 2.906 | 2.811 | 5.717 | 2322.4 | `calibrated_results` | OK |
| `severity_stratification_pipeline.py` | `SeverityStratificationAnalyzer` | cpu | 1.971 | 128.889 | 130.86 | 5643.7 | `absa_results`, `urgent_flag` | OK |

## 3. Aggregate Insights

- `absa_pipeline`: **5/10** rows had at least one aspect detected.
- `counterfactual_override_engine`: counterfactual override triggered on **1/10** rows.
- `severity_stratification_pipeline`: **0/10** rows flagged `URGENT_REVIEW`.
- Of 10 rows, 3 are None/empty/whitespace-only; confirm above these produced well-formed empty/placeholder results rather than errors or row misalignment.

## 4. Per-Row Merged Results

| Row | Review (preview) | absa_pipeline.absa_results | counterfactual_override_engine.calibrated_results | severity_stratification_pipeline.absa_results | severity_stratification_pipeline.urgent_flag |
|---|---|---|---|---|---|
| 0 | The doctor's diagnosis was accurate and the surgery went smoothly, though the parking lot ... _(truncated, 145 chars total)_ | `[{"aspect": "Clinical_Competence", "sentiment": 0.5597}, {"aspect": "Facility_Wait_Time", "sentiment": -0.7239}]` | `{"raw_sentiment": "POS", "calibrated_sentiment": "POS", "confidence": 0.2376, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Administrative_Complaint", "Clinical_Adverse_Event", "Routine_Feedback"], "scores": [0.625, 0.5512, 0.0084, 0.0029], "urgent_review": false}` | `""` |
| 1 | *(missing/None)* | `[]` | `{"raw_sentiment": null, "calibrated_sentiment": null, "confidence": 0.0, "override_triggered": false}` | `{"labels": [], "scores": [], "urgent_review": false}` | `""` |
| 2 | I can't say I didn't not appreciate the fact that the nurse wasn't uncaring, nor would I d... _(truncated, 265 chars total)_ | `[{"aspect": "Clinical_Competence", "sentiment": -0.5332}, {"aspect": "Staff_Behavior", "sentiment": -0.4862}]` | `{"raw_sentiment": "NEG", "calibrated_sentiment": "NEG", "confidence": 0.3645, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Clinical_Adverse_Event", "Administrative_Complaint", "Routine_Feedback"], "scores": [0.9898, 0.1635, 0.0589, 0.0001], "urgent_review": false}` | `""` |
| 3 | If I hadn't not avoided the surgery, I wouldn't have not survived; it's not that I didn't ... _(truncated, 260 chars total)_ | `[]` | `{"raw_sentiment": "NEU", "calibrated_sentiment": "POS", "confidence": 0.95, "override_triggered": true}` | `{"labels": ["Emotional_Distress", "Clinical_Adverse_Event", "Administrative_Complaint", "Routine_Feedback"], "scores": [0.7814, 0.6068, 0.0386, 0.0004], "urgent_review": false}` | `""` |
| 4 | From the moment I checked in at the front desk, the entire experience at this clinic unfol... _(truncated, 13199 chars total)_ | `[{"aspect": "Clinical_Competence", "sentiment": -0.08}, {"aspect": "Staff_Behavior", "sentiment": 0.5706}]` | `{"raw_sentiment": "NEU", "calibrated_sentiment": "NEU", "confidence": 0.5946, "override_triggered": false}` | `{"labels": ["Clinical_Adverse_Event", "Emotional_Distress", "Administrative_Complaint", "Routine_Feedback"], "scores": [0.9705, 0.9624, 0.9416, 0.7195], "urgent_review": false}` | `""` |
| 5 | *(missing/None)* | `[]` | `{"raw_sentiment": null, "calibrated_sentiment": null, "confidence": 0.0, "override_triggered": false}` | `{"labels": [], "scores": [], "urgent_review": false}` | `""` |
| 6 | *(empty string)* | `[]` | `{"raw_sentiment": null, "calibrated_sentiment": null, "confidence": 0.0, "override_triggered": false}` | `{"labels": [], "scores": [], "urgent_review": false}` | `""` |
| 7 | Bad. | `[]` | `{"raw_sentiment": "NEG", "calibrated_sentiment": "NEG", "confidence": 0.8789, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Clinical_Adverse_Event", "Administrative_Complaint", "Routine_Feedback"], "scores": [0.9974, 0.9947, 0.9556, 0.0], "urgent_review": false}` | `""` |
| 8 | 醫生非常好 👍 but the front desk was incredibly rude 😡 and the wait time was unacceptable. | `[{"aspect": "Clinical_Competence", "sentiment": 0.694}]` | `{"raw_sentiment": "NEG", "calibrated_sentiment": "NEG", "confidence": 0.9072, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Administrative_Complaint", "Clinical_Adverse_Event", "Routine_Feedback"], "scores": [0.9981, 0.9952, 0.6909, 0.0], "urgent_review": false}` | `""` |
| 9 | THE NURSE WAS AMAZING BUT THE WAIT TIME WAS RIDICULOUS AND I WAITED FOR THREE HOURS WITHOU... _(truncated, 132 chars total)_ | `[{"aspect": "Clinical_Competence", "sentiment": 0.9581}, {"aspect": "Staff_Behavior", "sentiment": 0.9581}]` | `{"raw_sentiment": "NEG", "calibrated_sentiment": "NEG", "confidence": 0.7556, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Administrative_Complaint", "Clinical_Adverse_Event", "Routine_Feedback"], "scores": [0.9982, 0.9873, 0.3475, 0.0001], "urgent_review": false}` | `""` |

## 5. Artifacts

- Full merged per-row results (JSON): `benchmark_merged_results.json`
- This report: `mle_nlp_report.md`

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
