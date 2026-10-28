"""
Flag analytics and semiconductor-data jargon in a draft and suggest plain wording.

Usage:
    python jargon_detector.py --text "Front availability is 91% after excluding read failures"
    python jargon_detector.py --input draft.md
"""

import argparse
import re

GLOSSARY = {
    "read failure": "a screen capture that could not be read",
    "ocr": "automatic text reading of screenshots",
    "time-weighted": "weighted by how long each reading was valid",
    "err_01": "reported closed-site count",
    "err_02": "list of closed sites",
    "debounce": "ignore very short blips",
    "mad": "typical day-to-day variation",
    "z-score": "how unusual a value is",
    "null": "missing value",
    "pareto": "ranked contribution chart",
    "cluster": "group of neighbouring sites",
    "closed site": "test position that cannot test",
    "availability": "share of positions able to test",
    "oee": "overall equipment effectiveness (availability x speed x yield)",
    "sensitivity": "how much the answer changes if a rule changes",
    "lower bound": "at least this much",
}


def detect(text: str) -> list[tuple[str, int, str]]:
    low = text.lower()
    out = []
    for term, plain in GLOSSARY.items():
        n = len(re.findall(rf"\b{re.escape(term)}\b", low))
        if n:
            out.append((term, n, plain))
    return sorted(out, key=lambda x: -x[1])


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
