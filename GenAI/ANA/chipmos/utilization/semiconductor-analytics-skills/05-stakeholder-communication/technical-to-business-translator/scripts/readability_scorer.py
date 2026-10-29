"""
Readability scorer - stdlib only. Sentence length alone can be gamed (five three-word sentences full of
jargon score "OK"), so the verdict also uses jargon density and the longest sentence.

Each bullet, heading, table cell and sentence counts as a sentence.

    OK                          average <= 20 words, longest <= 40, jargon <= 2 per 100 words
    too dense - split sentences average > 20 or longest > 40
    jargon-dense                more than 2 jargon hits per 100 words

Usage:
    python readability_scorer.py --text "..."
    python readability_scorer.py --input draft.md
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jargon_detector  # noqa: E402

MAX_AVG, MAX_LONGEST, MAX_JARGON_PER_100 = 20, 40, 2.0


def segments(text: str) -> list[str]:
    segs = []
    for line in text.splitlines():
        line = re.sub(r"^\s*(?:[-*]|\d+\.|#+)\s*", "", line.strip().strip("|"))
        for cell in line.split("|"):
            segs += [s for s in re.split(r"(?<=[.!?])\s+", cell.strip()) if s and not re.fullmatch(r"[-: ]+", s)]
    return segs


def score(text: str, allow: tuple[str, ...] | set = ()) -> dict:
    segs = segments(text)
    lengths = [len(re.findall(r"[A-Za-z0-9'%-]+", s)) for s in segs]
    lengths = [n for n in lengths if n]
    words = sum(lengths)
    long_words = [w for w in re.findall(r"[A-Za-z0-9'%-]+", text) if len(w) >= 10]
    hits = sum(n for t, n, _ in jargon_detector.detect(text) if t not in allow)
    avg = words / max(1, len(lengths))
    density = hits / max(1, words) * 100
    if density > MAX_JARGON_PER_100:
        verdict = "jargon-dense"
    elif avg > MAX_AVG or max(lengths, default=0) > MAX_LONGEST:
        verdict = "too dense - split sentences"
    else:
        verdict = "OK"
    return {
        "sentences": len(lengths),
        "words": words,
        "avg_words_per_sentence": round(avg, 1),
        "max_sentence_words": max(lengths, default=0),
        "long_words_pct": round(len(long_words) / max(1, words) * 100, 1),
        "jargon_per_100_words": round(density, 1),
        "verdict": verdict,
    }


def main():
    ap = argparse.ArgumentParser(description="Readability scorer")
    ap.add_argument("--text")
    ap.add_argument("--input")
    args = ap.parse_args()
    text = args.text or (open(args.input, encoding="utf-8").read() if args.input else
                         "Front availability is 91 percent. Three clusters explain most of the loss.")
    for k, v in score(text).items():
        print(f"{k:24s} {v}")


if __name__ == "__main__":
    main()
