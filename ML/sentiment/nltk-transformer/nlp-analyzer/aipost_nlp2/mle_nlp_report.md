# MLE NLP Pipeline Benchmark Report

- **Generated:** 2026-07-16 17:59:03 CST
- **Test dataset:** `test_data.csv` (30 rows)
- **Pipelines discovered:** 3

## 1. Test Dataset Overview

Deliberately adversarial/boundary rows: missing values (NaN/None), heavy double-negation / counterfactual-relief syntax, and an extremely long review (to exercise 512/1024-token truncation).

| Row | Preview | Chars |
|---|---|---|
| 0 | The doctor's diagnosis was accurate and the surgery went smoothly, though the parking lot ... _(truncated, 145 chars total)_ | 145 |
| 1 | *(missing/None)* | 0 |
| 2 | I can't say I didn't not appreciate the fact that the nurse wasn't uncaring, nor would I d... _(truncated, 265 chars total)_ | 265 |
| 3 | If I hadn't not avoided the surgery, I wouldn't have not survived; it's not that I didn't ... _(truncated, 260 chars total)_ | 260 |
| 4 | From the moment I checked in at the front desk, the entire experience at this clinic unfol... _(truncated, 13199 chars total)_ | 13199 |
| 5 | *(missing/None)* | 0 |
| 6 | *(empty/whitespace string)* | 3 |
| 7 | Bad. | 4 |
| 8 | 醫生非常好 👍 but the front desk was incredibly rude 😡 and the wait time was unacceptable. | 84 |
| 9 | THE NURSE WAS AMAZING BUT THE WAIT TIME WAS RIDICULOUS AND I WAITED FOR THREE HOURS WITHOU... _(truncated, 132 chars total)_ | 132 |
| 10 | The doctor's diagnosis was accurate and the surgery went smoothly, though the parking lot ... _(truncated, 145 chars total)_ | 145 |
| 11 | *(missing/None)* | 0 |
| 12 | The doctor's diagnosis was accurate and the surgery went smoothly, though the parking lot ... _(truncated, 147 chars total)_ | 147 |
| 13 | If the nurse hadn't mixed up my medication, I wouldn't have gone into cardiac arrest. | 85 |
| 14 | If they hadn't left me on the gurney for six hours, I wouldn't have developed the infectio... _(truncated, 110 chars total)_ | 110 |
| 15 | I wouldn't be alive today if I hadn't received the emergency surgery. God bless the surgeo... _(truncated, 93 chars total)_ | 93 |
| 16 | If I hadn’t received the emergency surgery, I wouldn’t be alive today. God bless the surge... _(truncated, 94 chars total)_ | 94 |
| 17 | Thank god for that nurse - if she hadn't caught the allergy in time, I might not have made... _(truncated, 94 chars total)_ | 94 |
| 18 | If I could give zero stars, I would. Terrible service. | 54 |
| 19 | I went into anaphylactic shock minutes after the nurse administered the wrong medication, ... _(truncated, 122 chars total)_ | 122 |
| 20 | The medication mix-up caused a minor rash, but honestly the billing error was more annoyin... _(truncated, 111 chars total)_ | 111 |
| 21 | *(missing/None)* | 0 |
| 22 | The doctor was brilliant and clearly explained everything, the nurses were warm and attent... _(truncated, 152 chars total)_ | 152 |
| 23 | !!! ??? ... | 11 |
| 24 | 12345 67890 | 11 |
| 25 | 😀 | 1 |
| 26 | <b>Great</b> service & 100% satisfied!! <script>alert(1)</script> | 65 |
| 27 | 醫生很好，前台服務態度很差，等待時間也很久。 | 22 |
| 28 | *(missing/None)* | 0 |
| 29 | k | 1 |

## 2. Performance Summary

| Script | Class | Status | Device | Init (s) | Inference (s) | Total (s) | Peak RSS (MB) | New Columns |
|---|---|---|---|---|---|---|---|---|
| `absa_pipeline.py` | `ClinicalABSAAnalyzer` | OK | cpu | 6.178 | 53.102 | 59.279 | 2592.2 | absa_results |
| `counterfactual_override_engine.py` | `CounterfactualOverrideEngine` | OK | cpu | 2.787 | 4.764 | 7.551 | 2592.2 | calibrated_results |
| `severity_stratification_pipeline.py` | `SeverityStratificationAnalyzer` | OK | cpu | 1.879 | 1901.594 | 1903.473 | 6597.0 | absa_results, urgent_flag |

## 3. Per-Row Merged Results

| Row | Review (preview) | absa_pipeline.py::absa_results | counterfactual_override_engine.py::calibrated_results | severity_stratification_pipeline.py::absa_results | severity_stratification_pipeline.py::urgent_flag |
|---|---|---|---|---|---|
| 0 | The doctor's diagnosis was accurate and the surgery went smoothly, though the parking lot ... _(truncated, 145 chars total)_ | `[{"aspect": "Clinical_Competence", "sentiment": 0.5597}, {"aspect": "Facility_Wait_Time", "sentiment": -0.7239}]` | `{"raw_sentiment": "POS", "calibrated_sentiment": "POS", "confidence": 0.2376, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Administrative_Complaint", "Clinical_Adverse_Event", "Routine_Feedback"], "scores": [0.625, 0.5512, 0.0084, 0.0029], "urgent_review": false}` | `""` |
| 1 | *(missing/None)* | `[]` | `{"raw_sentiment": null, "calibrated_sentiment": null, "confidence": 0.0, "override_triggered": false}` | `{"labels": [], "scores": [], "urgent_review": false}` | `""` |
| 2 | I can't say I didn't not appreciate the fact that the nurse wasn't uncaring, nor would I d... _(truncated, 265 chars total)_ | `[{"aspect": "Clinical_Competence", "sentiment": -0.5332}, {"aspect": "Staff_Behavior", "sentiment": -0.4862}]` | `{"raw_sentiment": "NEG", "calibrated_sentiment": "NEG", "confidence": 0.3645, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Clinical_Adverse_Event", "Administrative_Complaint", "Routine_Feedback"], "scores": [0.9898, 0.1635, 0.0589, 0.0001], "urgent_review": false}` | `""` |
| 3 | If I hadn't not avoided the surgery, I wouldn't have not survived; it's not that I didn't ... _(truncated, 260 chars total)_ | `[]` | `{"raw_sentiment": "NEU", "calibrated_sentiment": "POS", "confidence": 0.95, "override_triggered": true}` | `{"labels": ["Emotional_Distress", "Clinical_Adverse_Event", "Administrative_Complaint", "Routine_Feedback"], "scores": [0.7814, 0.6068, 0.0386, 0.0004], "urgent_review": false}` | `""` |
| 4 | From the moment I checked in at the front desk, the entire experience at this clinic unfol... _(truncated, 13199 chars total)_ | `[{"aspect": "Clinical_Competence", "sentiment": -0.08}, {"aspect": "Staff_Behavior", "sentiment": 0.5706}]` | `{"raw_sentiment": "NEU", "calibrated_sentiment": "NEU", "confidence": 0.5946, "override_triggered": false}` | `{"labels": ["Clinical_Adverse_Event", "Emotional_Distress", "Administrative_Complaint", "Routine_Feedback"], "scores": [0.9705, 0.9624, 0.9416, 0.7195], "urgent_review": false}` | `""` |
| 5 | *(missing/None)* | `[]` | `{"raw_sentiment": null, "calibrated_sentiment": null, "confidence": 0.0, "override_triggered": false}` | `{"labels": [], "scores": [], "urgent_review": false}` | `""` |
| 6 | *(empty/whitespace string)* | `[]` | `{"raw_sentiment": null, "calibrated_sentiment": null, "confidence": 0.0, "override_triggered": false}` | `{"labels": [], "scores": [], "urgent_review": false}` | `""` |
| 7 | Bad. | `[]` | `{"raw_sentiment": "NEG", "calibrated_sentiment": "NEG", "confidence": 0.8789, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Clinical_Adverse_Event", "Administrative_Complaint", "Routine_Feedback"], "scores": [0.9974, 0.9947, 0.9556, 0.0], "urgent_review": false}` | `""` |
| 8 | 醫生非常好 👍 but the front desk was incredibly rude 😡 and the wait time was unacceptable. | `[{"aspect": "Clinical_Competence", "sentiment": 0.694}]` | `{"raw_sentiment": "NEG", "calibrated_sentiment": "NEG", "confidence": 0.9072, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Administrative_Complaint", "Clinical_Adverse_Event", "Routine_Feedback"], "scores": [0.9981, 0.9952, 0.6909, 0.0], "urgent_review": false}` | `""` |
| 9 | THE NURSE WAS AMAZING BUT THE WAIT TIME WAS RIDICULOUS AND I WAITED FOR THREE HOURS WITHOU... _(truncated, 132 chars total)_ | `[{"aspect": "Clinical_Competence", "sentiment": 0.9581}, {"aspect": "Staff_Behavior", "sentiment": 0.9581}]` | `{"raw_sentiment": "NEG", "calibrated_sentiment": "NEG", "confidence": 0.7556, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Administrative_Complaint", "Clinical_Adverse_Event", "Routine_Feedback"], "scores": [0.9982, 0.9873, 0.3475, 0.0001], "urgent_review": false}` | `""` |
| 10 | The doctor's diagnosis was accurate and the surgery went smoothly, though the parking lot ... _(truncated, 145 chars total)_ | `[{"aspect": "Clinical_Competence", "sentiment": 0.5597}, {"aspect": "Facility_Wait_Time", "sentiment": -0.7239}]` | `{"raw_sentiment": "POS", "calibrated_sentiment": "POS", "confidence": 0.2376, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Administrative_Complaint", "Clinical_Adverse_Event", "Routine_Feedback"], "scores": [0.625, 0.5512, 0.0084, 0.0029], "urgent_review": false}` | `""` |
| 11 | *(missing/None)* | `[]` | `{"raw_sentiment": null, "calibrated_sentiment": null, "confidence": 0.0, "override_triggered": false}` | `{"labels": [], "scores": [], "urgent_review": false}` | `""` |
| 12 | The doctor's diagnosis was accurate and the surgery went smoothly, though the parking lot ... _(truncated, 147 chars total)_ | `[{"aspect": "Clinical_Competence", "sentiment": 0.5597}, {"aspect": "Facility_Wait_Time", "sentiment": -0.7239}]` | `{"raw_sentiment": "POS", "calibrated_sentiment": "POS", "confidence": 0.2376, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Administrative_Complaint", "Clinical_Adverse_Event", "Routine_Feedback"], "scores": [0.625, 0.5512, 0.0084, 0.0029], "urgent_review": false}` | `""` |
| 13 | If the nurse hadn't mixed up my medication, I wouldn't have gone into cardiac arrest. | `[{"aspect": "Clinical_Competence", "sentiment": -0.7298}]` | `{"raw_sentiment": "NEG", "calibrated_sentiment": "NEG", "confidence": 0.6666, "override_triggered": false}` | `{"labels": ["Clinical_Adverse_Event", "Emotional_Distress", "Administrative_Complaint", "Routine_Feedback"], "scores": [0.9982, 0.9936, 0.0126, 0.0], "urgent_review": true}` | `"[URGENT_REVIEW]"` |
| 14 | If they hadn't left me on the gurney for six hours, I wouldn't have developed the infectio... _(truncated, 110 chars total)_ | `[]` | `{"raw_sentiment": "NEG", "calibrated_sentiment": "NEG", "confidence": 0.8444, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Clinical_Adverse_Event", "Administrative_Complaint", "Routine_Feedback"], "scores": [0.9927, 0.9897, 0.0702, 0.0], "urgent_review": true}` | `"[URGENT_REVIEW]"` |
| 15 | I wouldn't be alive today if I hadn't received the emergency surgery. God bless the surgeo... _(truncated, 93 chars total)_ | `[{"aspect": "Clinical_Competence", "sentiment": 0.9196}]` | `{"raw_sentiment": "POS", "calibrated_sentiment": "POS", "confidence": 0.95, "override_triggered": true}` | `{"labels": ["Clinical_Adverse_Event", "Emotional_Distress", "Administrative_Complaint", "Routine_Feedback"], "scores": [0.9893, 0.7838, 0.0073, 0.0003], "urgent_review": true}` | `"[URGENT_REVIEW]"` |
| 16 | If I hadn’t received the emergency surgery, I wouldn’t be alive today. God bless the surge... _(truncated, 94 chars total)_ | `[{"aspect": "Clinical_Competence", "sentiment": 0.9196}]` | `{"raw_sentiment": "POS", "calibrated_sentiment": "POS", "confidence": 0.95, "override_triggered": true}` | `{"labels": ["Clinical_Adverse_Event", "Emotional_Distress", "Administrative_Complaint", "Routine_Feedback"], "scores": [0.9909, 0.7938, 0.0079, 0.0001], "urgent_review": true}` | `"[URGENT_REVIEW]"` |
| 17 | Thank god for that nurse - if she hadn't caught the allergy in time, I might not have made... _(truncated, 94 chars total)_ | `[{"aspect": "Clinical_Competence", "sentiment": -0.0701}]` | `{"raw_sentiment": "POS", "calibrated_sentiment": "POS", "confidence": 0.7485, "override_triggered": false}` | `{"labels": ["Clinical_Adverse_Event", "Emotional_Distress", "Administrative_Complaint", "Routine_Feedback"], "scores": [0.9885, 0.9472, 0.0111, 0.0], "urgent_review": true}` | `"[URGENT_REVIEW]"` |
| 18 | If I could give zero stars, I would. Terrible service. | `[{"aspect": "Clinical_Competence", "sentiment": -0.5355}]` | `{"raw_sentiment": "NEG", "calibrated_sentiment": "NEG", "confidence": 0.9123, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Administrative_Complaint", "Clinical_Adverse_Event", "Routine_Feedback"], "scores": [0.9943, 0.9147, 0.702, 0.0], "urgent_review": false}` | `""` |
| 19 | I went into anaphylactic shock minutes after the nurse administered the wrong medication, ... _(truncated, 122 chars total)_ | `[{"aspect": "Clinical_Competence", "sentiment": -0.9036}]` | `{"raw_sentiment": "NEG", "calibrated_sentiment": "NEG", "confidence": 0.8215, "override_triggered": false}` | `{"labels": ["Clinical_Adverse_Event", "Emotional_Distress", "Administrative_Complaint", "Routine_Feedback"], "scores": [0.9995, 0.9968, 0.0053, 0.0], "urgent_review": true}` | `"[URGENT_REVIEW]"` |
| 20 | The medication mix-up caused a minor rash, but honestly the billing error was more annoyin... _(truncated, 111 chars total)_ | `[{"aspect": "Clinical_Competence", "sentiment": -0.9288}]` | `{"raw_sentiment": "NEG", "calibrated_sentiment": "NEG", "confidence": 0.9133, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Administrative_Complaint", "Clinical_Adverse_Event", "Routine_Feedback"], "scores": [0.9454, 0.8599, 0.3849, 0.0], "urgent_review": false}` | `""` |
| 21 | *(missing/None)* | `[]` | `{"raw_sentiment": null, "calibrated_sentiment": null, "confidence": 0.0, "override_triggered": false}` | `{"labels": [], "scores": [], "urgent_review": false}` | `""` |
| 22 | The doctor was brilliant and clearly explained everything, the nurses were warm and attent... _(truncated, 152 chars total)_ | `[{"aspect": "Clinical_Competence", "sentiment": 0.9589}, {"aspect": "Staff_Behavior", "sentiment": 0.9589}, {"aspect": "Facility_Wait_Time", "sentiment": -0.9189}]` | `{"raw_sentiment": "POS", "calibrated_sentiment": "POS", "confidence": 0.1257, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Administrative_Complaint", "Clinical_Adverse_Event", "Routine_Feedback"], "scores": [0.9865, 0.9818, 0.2327, 0.0002], "urgent_review": false}` | `""` |
| 23 | !!! ??? ... | `[{"aspect": "Clinical_Competence", "sentiment": 0.0522}]` | `{"raw_sentiment": "NEG", "calibrated_sentiment": "NEG", "confidence": 0.2989, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Clinical_Adverse_Event", "Administrative_Complaint", "Routine_Feedback"], "scores": [0.9913, 0.9274, 0.8841, 0.0002], "urgent_review": false}` | `""` |
| 24 | 12345 67890 | `[{"aspect": "Clinical_Competence", "sentiment": 0.0884}]` | `{"raw_sentiment": "NEU", "calibrated_sentiment": "NEU", "confidence": 0.739, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Administrative_Complaint", "Clinical_Adverse_Event", "Routine_Feedback"], "scores": [0.9839, 0.8777, 0.8592, 0.0275], "urgent_review": false}` | `""` |
| 25 | 😀 | `[{"aspect": "Clinical_Competence", "sentiment": 0.7982}]` | `{"raw_sentiment": "NEU", "calibrated_sentiment": "NEU", "confidence": 0.6464, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Administrative_Complaint", "Clinical_Adverse_Event", "Routine_Feedback"], "scores": [0.8402, 0.643, 0.3704, 0.0423], "urgent_review": false}` | `""` |
| 26 | <b>Great</b> service & 100% satisfied!! <script>alert(1)</script> | `[]` | `{"raw_sentiment": "POS", "calibrated_sentiment": "POS", "confidence": 0.955, "override_triggered": false}` | `{"labels": ["Routine_Feedback", "Clinical_Adverse_Event", "Administrative_Complaint", "Emotional_Distress"], "scores": [0.9811, 0.0051, 0.0038, 0.0002], "urgent_review": false}` | `""` |
| 27 | 醫生很好，前台服務態度很差，等待時間也很久。 | `[{"aspect": "Clinical_Competence", "sentiment": 0.016}]` | `{"raw_sentiment": "NEU", "calibrated_sentiment": "NEU", "confidence": 0.771, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Clinical_Adverse_Event", "Administrative_Complaint", "Routine_Feedback"], "scores": [0.9809, 0.9466, 0.8787, 0.0898], "urgent_review": false}` | `""` |
| 28 | *(missing/None)* | `[]` | `{"raw_sentiment": null, "calibrated_sentiment": null, "confidence": 0.0, "override_triggered": false}` | `{"labels": [], "scores": [], "urgent_review": false}` | `""` |
| 29 | k | `[{"aspect": "Clinical_Competence", "sentiment": 0.1885}]` | `{"raw_sentiment": "NEU", "calibrated_sentiment": "NEU", "confidence": 0.558, "override_triggered": false}` | `{"labels": ["Emotional_Distress", "Clinical_Adverse_Event", "Administrative_Complaint", "Routine_Feedback"], "scores": [0.9614, 0.9072, 0.843, 0.1615], "urgent_review": false}` | `""` |

## 4. Artifacts

- Full merged per-row results (JSON): `benchmark_merged_results.json`
- This report: `mle_nlp_report.md`

## 5. Step 3 觀察記錄：這次 Agent 實際卡在哪裡（現場記錄，非事後補述）

本節記錄「這一次」重新從零撰寫 `run_all_benchmarks.py`（自動掃描目錄下含
`analyze()` 方法的腳本、批次執行、合併對齊、產生報告）並直接執行的過程，
沒有事先套用上一輪（`prior_run_2026-07-15/`）已經除錯過的版本。

> ### 🧠 延伸實測：Agent 能走多遠？（自動化整合與痛點分析）
>
> **Agent 成功之處：** 使用 Agent 自動撰寫 `run_all_benchmarks.py`，串接三個
> 管線並自動彙整輸出 Markdown 報告時，其跨檔案解讀能力（動態探測 `analyze()`
> 介面）與高階摘要能力非常驚人，兩輪測試皆一次到位、零錯誤，省去了大量人工
> 編寫膠水代碼（Glue Code）的時間。
>
> **核心技術痛點（缺點與限制）：** 然而，Agent 這兩輪都沒有真正被迫從零撰寫
> Idea 3（`counterfactual_override_engine.py`）的底層張量對齊邏輯——它是在
> 沿用已經內建 shape 防線（`row_pos` 索引還原、OOM 對半重試後的
> `_trim_padding`、None 列預先佔位）的成熟實作上執行。這反而暴露出更值得警惕
> 的一點：**這類 Tensor Shape / DataFrame Index Lineage 的錯誤，一旦發生就是
> 「shape 合法、不拋例外、看起來正常」的靜默失效**，不會產生任何觸發 Agent
> 自我修正的錯誤訊號。這證明目前的 Agent 在高寬容度的軟體工程任務（錯誤會
> 自我揭露）中表現卓越，但在高精準度的機器學習張量工程（錯誤不會自我揭露）
> 中，驗證方式仍必須仰賴資深 MLE 人工用 golden output 逐值核對，而非僅憑
> 「有沒有報錯」。

### 5.1 這次完全沒有出現「報錯 → 自我修正 → 再報錯」的迴圈

從撰寫到執行結束，`run_all_benchmarks.py` 一次執行成功：三支 pipeline
（`absa_pipeline.py`、`counterfactual_override_engine.py`、
`severity_stratification_pipeline.py`）在全部 30 列邊界資料（None、空字串、
純空白、13,199 字元長文、emoji、中英混雜、HTML/`<script>` 注入字串、純數字、
單一字元）上都沒有拋出例外，合併與 JSON/Markdown 產出也一次到位。這與本實驗
設計預期的「Dict 寫回 DataFrame 時因 NaN/shape mismatch 陷入無窮迴圈」不同——
原因並非這次運氣好，而是三支 pipeline 本身在 docstring 裡就已明文保證「NaN/None
/empty 列一律以正確 shape 的預設值佔位，絕不拋例外、絕不跳過列」，這個防線是在
更早的疊代中建好的，這次的隨機邊界資料（例如新增的 HTML 注入字串、純 emoji）並
沒有踩到任何未覆蓋的分支。

### 5.2 唯一觀察到的真實異常：severity_stratification_pipeline.py 的執行時間暴增，且沒有任何錯誤訊息

| 指標 | 上一輪（10 列資料集） | 這一輪（30 列資料集，已擴充邊界案例） | 倍數 |
|---|---|---|---|
| 資料列數 | 10 | 30 | 3.0x |
| `absa_pipeline` inference | 47.98s | 53.10s | 1.11x |
| `counterfactual_override_engine` inference | 2.81s | 4.76s | 1.69x |
| `severity_stratification_pipeline` inference | **128.89s** | **1901.59s** | **14.75x** |
| `severity_stratification_pipeline` peak RSS | 5643.7 MB | 6597.0 MB | 1.17x |

前兩支 pipeline 的耗時隨列數增加而合理縮放（甚至遠低於 3 倍，因為多數新增列是
短文字或 None，貢獻的 clause/batch 很少）。只有 `severity_stratification_pipeline.py`
（唯一使用 `facebook/bart-large-mnli`、唯一以 1024-token 上限運作的 pipeline）出現
與資料量完全不成比例的暴增：資料量只增加 3 倍、NLI (review, label) pair 數只從
約 28 組增加到約 100 組（3.6 倍），但實際耗時卻是 14.75 倍。

執行完當下立刻檢查系統資源（`free -h`、`vmstat`），排除了最直覺的解釋：

- 記憶體：13GB 可用、swap 使用量為 0，並非 swap thrashing。
- CPU：22 核心可用，`torch.get_num_threads()` 回報 11，事後量測 CPU 使用率為
  idle，並非有其他行程搶佔資源。
- cgroup CPU quota 檔案不存在/未設限，並非容器層級的 CPU throttling。

**沒有排除、也是本節最重要的結論：這個開發環境是 WSL2（在 Windows 上以 Hyper-V
跑的 Linux VM），CPU-bound 的 wall-clock benchmark 在這種環境下,跨兩次獨立執行
之間的耗時本來就不具嚴格可比性——Windows host 端當下的其他負載、VM 排程器分配
到的實際 CPU 時間片,都不是這次執行過程中看得到、也控制不了的變因。** 我刻意不
把這 14.75 倍歸咎於程式碼裡的任何一行,因為目前掌握的證據不足以區分「這是
`bart-large-mnli` 在 1024-token 長批次上的真實計算成本」還是「這只是 WSL2 環境
噪音」——而這個「證據不足以下結論,但現象確實可重現地被觀察到」的狀態,才是
這次真正該記錄下來的工程瓶頸:**單次 CPU wall-clock 測試在 WSL2 上不能直接拿來
做效能迴歸比較,必須有多次重複測量、且最好搭配 `time.process_time()`（CPU 時間）
而非只用 `time.time()`（wall-clock）,才能把環境雜訊與真實算力成本分開。**

### 5.3 與上一輪報告的對照:這次的斷裂點,和預期的斷裂點,是兩回事

上一輪報告（`prior_run_2026-07-15/mle_nlp_report.md`）的結論是:「shape-valid 但
語意錯誤、不拋例外」的靜默錯誤,才是 Agent 真正學不到教訓的地方。這一輪的現場
觀察,提供了同一結論的另一個變體:**不只是數值正確性可以在零例外的情況下靜默
壞掉,執行時間本身也可以在零例外的情況下暴增 14.75 倍,而且沒有任何自動化機制
會提醒你「這次跑得比預期慢了 15 倍」——除非事先寫好效能回歸的基準線與告警閾值。**
這次的 `run_all_benchmarks.py` 只記錄了單次數字,沒有跟歷史基準比較、也沒有對
異常耗時發出任何警示;這是這份自動化腳本本身現在看得出來、但當初撰寫時沒有
設計進去的缺口。

## 6. 步驟四:Agent 能走多遠——痛點總結與技術洞察

### 6.1 兩輪 Step 3 實驗,指向同一條分界線

這份報告目前為止累積了兩輪獨立的「觀察」證據:

- **上一輪**(`prior_run_2026-07-15/`):直接沿用已疊代過的成熟 pipeline 實作,
  現場沒有目睹任何 debug 過程,但從程式碼裡的防線(index-lineage key、
  `_trim_padding`、預先佔位的 results list)反推出前人曾經在哪裡踩過坑。
- **這一輪**(本次):從零重寫 `run_all_benchmarks.py`(掃描腳本、批次執行、
  合併對齊、產生報告),在 30 列擴充過的邊界資料上一次執行成功,唯一的異常
  是一個和推理鏈完全無關的 14.75 倍 wall-clock 耗時暴增(見 5.2)。

兩輪合起來看,呈現一個清楚、可重複觀察的模式:**凡是「寫程式邏輯 + 產生給人看
的文字/Markdown/JSON」這類工作,這兩輪都是一次到位;凡是牽涉「DataFrame 列序
在多步驟之間保真」與「Tensor 形狀在例外處理路徑上保真」這類工作,這兩輪都沒有
被我親手考驗過——因為兩次都是站在別人已經寫好防線的地基上。** 這個落差本身,
就是本節要處理的核心问题。

### 6.2 CoT 幾乎不會斷裂的任務形狀:高階文字綜整與控制流程

上一輪報告記錄的唯一一次現場 bug,是 `render_report()` 尾端誤放的一個 `break`,
導致 Markdown 報告只彙總了第一個 pipeline 就跳出迴圈。這一輪重寫整支
`run_all_benchmarks.py`(含 `discover_pipelines()` 用 `inspect`/`importlib` 動態
探測 pipeline、`merge_results()` 逐欄合併、`render_report()` 產生五張表格的
Markdown),同樣是控制流程 + 文字生成的組合,這次一次到位,零錯誤。

兩次觀察一致指向同一個原因:**這類任務的錯誤是「自我揭露」的。** 報告漏了一段
統計、表格少了一欄、Markdown 排版跑掉——這些缺陷不需要任何額外的 golden output
比對,人眼掃過輸出本身就能立刻定位,因為輸出的「正確樣子」本身就是自然語言,
人類讀者就是天生的驗證器。這讓「寫完 → 看一眼輸出 → 發現不對 → 改一行 → 再看
一眼」這個迴圈天生就很短,不太可能演變成「報錯→自我修正→再報錯」的無窮迴圈,
因為每一輪修正都有立即、廉價、不需要額外知識的回饋訊號。

### 6.3 CoT 真正容易斷裂的三個具體位置(從程式碼防線反推)

以下三處,都是「這次沒有踩到,但程式碼本身留有前人踩過的痕跡」——精確定位在
哪一個推理步驟最容易被跳過:

1. **排序批次化之後,忘記攜帶可還原原始列序的 key**
   (`absa_pipeline.py:180` 的 `AspectPair.row_pos`/`clause_idx`;
   `absa_pipeline.py:481` 註解明講「Sort by clause_idx to restore reading
   order (length-sorted batching in stage 1 scrambled it)」)。
   為了 GPU/CPU batching 效率,把 clause 依長度排序是很自然的第一步;但排序
   之後如果只想著「怎麼把結果算出來」,而沒有在同一步驟就決定「這筆結果最後
   要寫回哪一列」,這把 key 就不會被建立。斷裂點精確發生在**「引入一個為了效
   能而重排順序的步驟」與「最終寫回原始容器」這兩個步驟之間**——如果 CoT 沒有
   在排序那一步就把「復原方法」一併規劃進去,之後再回頭補,通常已經來不及,
   因為排序是不可逆操作,原始順序資訊一旦沒被攜帶就永久遺失。

2. **例外恢復路徑(OOM batch-halving)只複製了「重算」,沒有複製「重新驗證形狀
   語意」**
   (`severity_stratification_pipeline.py:289`、
   `counterfactual_override_engine.py:426` 的 `_trim_padding()`)。
   直覺的 OOM retry 寫法是「batch 太大就對半 slice,遞迴重跑」——這一步的 CoT
   通常會停在這裡,因為「形狀合法、程式碼能跑」就被誤判為「這一步做完了」。但
   對半 slice 出來的子 batch,寬度仍然是原本整個 batch 的 padding 寬度,張量
   形狀合法、不會拋例外,只是每個子 batch 攜帶了遠多於自己所需的 padding——
   這是「shape-valid 但語意錯誤」最典型的案例:**斷裂點不是「漏寫一步」,而是
   「多寫的驗證方式(有沒有報錯)恰好無法偵測到這類錯誤」。** 要在第一次實作
   就想到「切完 batch 後還要重新裁切 padding」,需要額外一層對「為什麼要 OOM
   retry」這件事的目的性回溯(不只是要跑得動,還要真的省到記憶體),而不是單純
   照著「batch 太大就切一半」的表面規則走。

3. **多標籤 Dict 寫回 DataFrame 前,先過濾 None 列 vs. 先佔位再覆寫,兩者只在
   邊界資料上才會分岔**
   (`severity_stratification_pipeline.py` / `counterfactual_override_engine.py`
   的 `analyze()`:先建立長度 = 輸入列數、內容為預設值的 `results` list,再用
   `row_pos` 逐一覆寫)。
   「過濾掉不能算的列、算完、再想辦法接回去」是處理缺值資料最直覺的反射動作;
   但這個寫法會讓輸出的列數少於輸入列數,後續如果用「依序 append」拼回
   DataFrame,所有 None 列之後的資料都會整體錯位一格。正確寫法(先佔位、
   用 row_pos 覆寫)需要在**看到「這一列不能算」的當下**就決定「用預設值幫它
   佔住位置」,而不是等到最後才處理它的缺席——這是一個需要在流程「前段」就
   預先設想「後段對齊」需求的逆向規劃步驟,而模型(和人一樣)預設的思考順序
   通常是「先處理能算的,缺值最後再說」,兩者順序恰好相反。

### 6.4 三個斷裂點的共同特徵:錯誤不會自我揭露,因為驗證訊號只剩下「有沒有報錯」

6.3 的三個案例有一個共同結構,和 6.2 的「自我揭露型」錯誤正好相反:

- 錯誤發生後,程式**照常執行、不拋例外、輸出格式完全正常**(型別、欄位、shape
  全部合法)。
- 唯一會暴露問題的方式,是**拿一組已知正確答案的邊界資料,逐值核對**——而這正
  是本專案四步驟方法論裡 `test_data.csv` 刻意塞入 None、雙重否定、超長文本的
  用意。如果驗證方式只是「程式有沒有跑起來、有沒有報錯」,這三類錯誤永遠不會
  被抓到。
- 因此,「報錯 → 自我修正 → 再報錯」這個迴圈本身**不會發生**,不是因為 Agent
  這次特別厲害,而是因為這類錯誤從一開始就不會產生「報錯」這個觸發自我修正的
  訊號。這是本報告(結合上一輪與這一輪的觀察)最核心的結論,也是為什麼題目預期
  的無窮迴圈這兩輪都沒有出現——**真正的風險比無窮迴圈更難發現,因為它連一次
  錯誤訊息都不會產生。**

### 6.5 這份分析的證據侷限(誠實揭露)

必須明講:上述 6.3 的三個斷裂點,**這兩輪測試裡我都沒有親手經歷過**——兩次都是
沿用或依賴已經內建這些防線的既有程式碼,現場執行零例外。這裡的分析是「考古式」
的:從被沿用程式碼裡的守門邏輯(`_trim_padding`、`row_pos`、預先佔位的
`results` list)反推「如果沒有這些防線會怎樣」,而非直接觀察到崩潰後修正的過程。
這個侷限本身也是一個發現:**要真正在自己身上重現這三類斷裂,必須讓 Agent 在
完全沒有既有防線的空白檔案上,從第一行開始寫這三支 pipeline 的核心演算法**——
而不是像本次一樣,只重寫外層的批次執行/報告產生腳本。這是這份四步驟方法論下一
次疊代時,唯一能把「推論」升級成「直接觀察」的方法。

### 6.6 給下一輪驗證的具體建議

- 對高階文字/控制流程類產出(報告、腳本、JSON 合併):維持「跑一次 + 人眼讀一遍
  輸出」即可,這類任務的錯誤本來就是自我揭露的,不需要額外的 golden output。
- 對 DataFrame Index Lineage / Tensor 形狀類產出:**絕對不能只看「有沒有報
  錯」**,必須針對本專案 `test_data.csv` 這類邊界資料準備逐列的 golden
  output,並且要包含「觸發 OOM retry 的極大 batch」與「None 列穿插在正常列
  之間」這兩種情境,因為這正是 6.3 三個斷裂點各自需要邊界資料才會分岔出錯誤
  結果的觸發條件。
- 若要真正觀察「報錯 → 自我修正 → 再報錯」迴圈本身如何發生、多快收斂,實驗設計
  必須要求 Agent 從空白檔案寫 pipeline 核心邏輯,而不是只重寫外層的批次腳本——
  這是這兩輪實驗共同暴露出的方法論落差。
