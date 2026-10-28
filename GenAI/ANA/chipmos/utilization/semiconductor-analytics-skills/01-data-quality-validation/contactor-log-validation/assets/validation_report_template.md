# Contactor Log Validation Report

**Handler**: [REQUIRED]   **Side(s)**: [REQUIRED]   **Period**: [REQUIRED]   **Analyst**: [REQUIRED]

## 1. Volume
| Side | Rows | Valid rows | Dropped (256) | Dropped (N/A>0) |
|---|---|---|---|---|
| front | [REQUIRED] | | | |
| rear | [REQUIRED] | | | |

## 2. Noise
| Side | Rows w/ out-of-range IDs | Rows w/ duplicates | count != list |
|---|---|---|---|
| front | [REQUIRED] | | |
| rear | [REQUIRED] | | |

## 3. Flagged days
| Date | Side | Finding | Severity | Decision (keep / exclude / caveat) |
|---|---|---|---|---|
| [REQUIRED] | | | | |

## 4. Exclusions handed to analysis
[REQUIRED - list dates/time ranges and the reason]

## 5. Upstream fixes requested
[OPTIONAL - e.g. tighten OCR separator detection for IDs like "1917"]
