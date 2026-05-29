"""
Basic usage example for the NLP Sentiment Analysis library.

Run from the repo root:
    python examples/basic_usage.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.preprocessor import preprocess_text
from src.analyzer import analyze_sentiment, get_word_distribution
from src.models import ModelType, SUPPORTED_MODELS


def demo(text: str, model_type: str) -> None:
    config = SUPPORTED_MODELS[model_type]
    print(f"\n{'='*60}")
    print(f"Model : {config['display']}  ({config['task']})")
    print(f"Input : {text[:80]}{'...' if len(text) > 80 else ''}")

    # Preprocess
    cleaned, removed, normalized, tokenized, stemmed, lemmatized, ner, pos = preprocess_text(text)
    print(f"\nCleaned    : {cleaned[:80]}")
    print(f"Lemmatized : {' '.join(lemmatized[:12])}{'...' if len(lemmatized) > 12 else ''}")
    if ner:
        print(f"NER        : {ner}")

    # Overall sentiment
    lemmatized_str = " ".join(lemmatized)
    sentiment, probabilities = analyze_sentiment(lemmatized_str, model_type)
    labels = config["labels"]
    scores = "  |  ".join(f"{l}: {p:.1%}" for l, p in zip(labels, probabilities))
    print(f"\nSentiment  : {sentiment}")
    print(f"Scores     : {scores}")

    # Word distribution
    word_dist = get_word_distribution(lemmatized, model_type)
    print(f"Word dist  : {word_dist.distribution}")


if __name__ == "__main__":
    texts = [
        "This product is absolutely amazing. I love everything about it. "
        "The quality is outstanding and the customer service was fantastic.",

        "The film was a complete waste of time. The acting was terrible "
        "and the plot made no sense whatsoever. Very disappointing.",

        "The patient reports feeling overwhelmed and anxious about the upcoming surgery. "
        "She expressed fear about the anesthesia but showed surprising resilience.",
    ]

    for text in texts:
        demo(text, ModelType.DEFAULT)

    # Also run emotion model on the clinical note
    demo(texts[2], ModelType.EMOTION)
