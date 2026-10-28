"""
Simple readability scorer (sentence length, long words) - stdlib only.

Usage:
    python readability_scorer.py --text "..."
    python readability_scorer.py --input draft.md
"""

import argparse
import re


def score(text: str) -> dict:
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    words = re.findall(r"[A-Za-z0-9'%-]+", text)
    long_words = [w for w in words if len(w) >= 10]
    avg = len(words) / max(1, len(sentences))
    return {
        "sentences": len(sentences),
        "words": len(words),
        "avg_words_per_sentence": round(avg, 1),
        "long_words_pct": round(len(long_words) / max(1, len(words)) * 100, 1),
        "verdict": "OK" if avg <= 20 else "too dense - split sentences",
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
