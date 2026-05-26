"""
Basic usage example for the NLP Healthcare Sentiment Analysis library.

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
        "The patient is recovering well and responding positively to treatment. "
        "The care team is satisfied with the progress.",

        "The patient reported severe side effects and persistent pain after the procedure. "
        "The treatment outcome was very disappointing.",

        "The patient reports feeling overwhelmed and anxious about the upcoming surgery. "
        "She expressed fear about the anesthesia but showed surprising resilience.",
    ]

    # Run all 6 healthcare models on the clinical note
    for model_type in ModelType:
        demo(texts[2], model_type)

    # Also compare v1 vs v2 BERT on positive and negative examples
    print(f"\n{'='*60}")
    print("── BERT Healthcare v1 vs v2 comparison ──")
    demo(texts[0], ModelType.BERT_HC)
    demo(texts[0], ModelType.BERT_HC_V2)
    demo(texts[1], ModelType.BERT_HC)
    demo(texts[1], ModelType.BERT_HC_V2)
