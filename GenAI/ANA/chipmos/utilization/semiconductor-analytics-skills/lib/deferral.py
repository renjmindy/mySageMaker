"""
Deferral guard for impact-quantification.

While `impact-quantification/status.json` says "deferred": true, no deliverable may quote money, margin,
payback or throughput (units per hour) figures. The checkers (executive summary, insight brief, dashboard
spec, QA gate) call `check()` and FAIL on any match. Lifting the deferral is an explicit edit of that file.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "05-stakeholder-communication/impact-quantification/status.json"

PATTERNS = [
    r"(?:US|NT|HK)?\$\s?\d|[€£¥]\s?\d",                                         # currency symbol + number
    r"\b\d[\d,.]*\s?(?:k|m|million|thousand)?\s?(?:USD|NTD|TWD|EUR|dollars?)\b",  # number + currency word
    r"\b\d[\d,.]*\s*(?:units|dies|devices|chips|pcs)\s*(?:/|per)\s*(?:hour|hr|h|day)\b",  # throughput
    r"\bUPH\b\s*(?:of|=|:)?\s*\d",                                              # UPH with a number
    r"\b(?:margin|revenue|payback|ROI|savings?)\b[^.\n|]{0,30}\d[\d,.]*",        # money words with a number
]


def is_deferred(path: Path = STATUS) -> bool:
    try:
        return bool(json.loads(Path(path).read_text(encoding="utf-8")).get("deferred", True))
    except (OSError, ValueError):
        return True  # no readable status = stay deferred


def business_figures(text: str) -> list[str]:
    """Money / margin / throughput figures found in `text` (HTML comments and markup are ignored)."""
    body = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", body, flags=re.DOTALL)
    found = []
    for pat in PATTERNS:
        found += [m.group(0).strip() for m in re.finditer(pat, body, flags=re.IGNORECASE)]
    return found


def check(text: str, status_path: Path = STATUS) -> list[str]:
    """Figures that are not allowed right now (empty when the deferral has been lifted)."""
    return business_figures(text) if is_deferred(status_path) else []
