"""
Flag analytics and semiconductor-data jargon in a draft and suggest plain wording.

Three kinds of term, because a word filter alone flags plain English ("a site visit", "a burst pipe"):
  * unambiguous jargon  - flagged anywhere (OCR, bootstrap, backtest, split-half, count-list gap, ...)
  * ambiguous words     - plain English elsewhere (site, availability, interval, burst, cluster, null,
                          sensitivity, chronic ...): flagged only when the text is about this domain
                          (at least two domain cue words such as position, handler, reading, capacity)
  * codes               - case-sensitive status labels and identifiers (PERSISTENT, RESOLVED, MAD, err_01,
                          snake_case names, assumption ids A8, "2x2", p = 0.07)

`detect(text)` returns [(term, count, plain wording)] sorted by count, so existing callers keep working.

Usage:
    python jargon_detector.py --text "Front availability is 91% after excluding read failures"
    python jargon_detector.py --input draft.md
"""

import argparse
import re

UNAMBIGUOUS = {
    "read failure": "a screen capture that could not be read",
    "ocr": "automatic text reading of screenshots",
    "time-weighted": "weighted by how long each reading was valid",
    "unweighted": "plain average",
    "debounce": "ignore very short blips",
    "z-score": "how unusual a value is",
    "pareto": "ranked contribution chart",
    "closed site": "test position that cannot test",
    "oee": "overall equipment effectiveness (availability x speed x yield)",
    "lower bound": "at least this much",
    "near-full": "readings that look like a failed screen read",
    "bootstrap": "repeated resampling to estimate uncertainty",
    "permutation": "a shuffling test",
    "level shift": "lasting change",
    "carry-forward": "assuming the last reading still held",
    "backtest": "checking a rule against past data",
    "in-sample": "tested on the same data it was designed on",
    "out-of-sample": "tested on data it was not designed on",
    "split-half": "comparing the first and second half",
    "block alignment": "how many closed positions form complete blocks",
    "count-list gap": "difference between the reported count and the list",
    "false-alarm rate": "how often an alert fires needlessly",
    "data gate": "automatic data check",
    "waiver": "approved exception",
    "hypertable": "a time-partitioned database table",
    "sensitivity analysis": "checking how much the answer changes if a rule changes",
    "closure episode": "one stretch of a position being closed",
}
AMBIGUOUS = {
    "site": "test position",
    "availability": "share of positions able to test",
    "interval": "plausible range",
    "burst": "short spell of unusual readings",
    "cluster": "group of neighbouring positions",
    "null": "missing value",
    "sensitivity": "how much the answer changes if a rule changes",
    "chronic": "out of service most of the time",
    "transient": "short-lived",
    "intermittent": "partly out of service",
    "recency": "what is happening now",
}
CODES = [  # (regex, label, plain) - case-sensitive
    (r"\bPERSISTENT\b", "PERSISTENT", "closed long-term"),
    (r"\bRESOLVED\b", "RESOLVED", "reopened"),
    (r"\bINTERMITTENT\b", "INTERMITTENT", "partly closed"),
    (r"\bCURRENT\b", "CURRENT", "closed now"),
    (r"\bNEW\b", "NEW", "closed recently"),
    (r"\bMAD\b", "MAD", "typical day-to-day variation"),
    (r"\bA\d{1,2}\b", "assumption id", "spell the rule out in words"),
    (r"\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b", "field name", "describe the field in words"),
    (r"\b2x2\b", "2x2", "a block of four neighbouring positions"),
    (r"\bp\s?=\s?0?\.\d+", "p-value", "how likely this is by chance"),
    (r"\bDataFormatError\b", "DataFormatError", "a file with the wrong layout"),
]
DOMAIN_CUES = {"position", "positions", "handler", "contactor", "reading", "readings", "screen", "capacity", "closed",
               "oee", "front", "rear", "hifix", "fab", "test", "tested", "testing"}
MIN_CUES = 2


def is_domain_text(text: str) -> bool:
    return len(DOMAIN_CUES & set(re.findall(r"[a-z]+", text.lower()))) >= MIN_CUES


def detect(text: str, domain: bool | None = None) -> list[tuple[str, int, str]]:
    low = text.lower()
    domain = is_domain_text(text) if domain is None else domain
    out = []
    pools = [UNAMBIGUOUS] + ([AMBIGUOUS] if domain else [])
    for pool in pools:
        for term, plain in pool.items():
            n = len(re.findall(rf"\b{re.escape(term)}(?:s|es)?\b", low))  # plural forms count too
            if n:
                out.append((term, n, plain))
    for rx, label, plain in CODES:
        n = len(re.findall(rx, text))
        if n:
            out.append((label, n, plain))
    return sorted(out, key=lambda x: -x[1])


GLOSSARY = {**UNAMBIGUOUS, **AMBIGUOUS}  # kept for callers that read the terms


def main():
    ap = argparse.ArgumentParser(description="Jargon detector")
    ap.add_argument("--text")
    ap.add_argument("--input")
    args = ap.parse_args()
    text = args.text or (open(args.input, encoding="utf-8").read() if args.input else
                         "Availability is 91% after dropping read failures; OCR noise is time-weighted out.")
    hits = detect(text)
    if not hits:
        print("no jargon found")
        return
    print(f"{len(hits)} jargon terms:")
    for term, n, plain in hits:
        print(f"  {term!r} x{n} -> say: {plain}")


if __name__ == "__main__":
    main()
