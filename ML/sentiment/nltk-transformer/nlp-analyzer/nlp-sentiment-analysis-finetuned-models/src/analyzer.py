"""
Transformer model inference: sentiment classification and per-word distribution.
All six fine-tuned healthcare models use direct AutoModel inference (lazy-loaded
and cached on first use).
"""

from typing import Dict, List, Tuple

import numpy as np
from scipy.special import softmax
from transformers import (
    AutoTokenizer, AutoConfig, AutoModelForSequenceClassification,
)

from .models import ModelType, SUPPORTED_MODELS, WordDistribution

# ── Direct model cache ────────────────────────────────────────────────────────
_direct_models: Dict[str, tuple] = {}  # key → (tokenizer, config, model)


def _get_direct_model(model_type) -> tuple:
    """Load and cache (tokenizer, config, model) for direct inference."""
    key = model_type.value if hasattr(model_type, "value") else model_type
    if key not in _direct_models:
        cfg          = SUPPORTED_MODELS[key]
        hf_id        = cfg["hf_id"]
        tokenizer_id = cfg.get("tokenizer", hf_id)
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_id)
        config    = AutoConfig.from_pretrained(hf_id)
        model     = AutoModelForSequenceClassification.from_pretrained(hf_id)
        model.eval()
        _direct_models[key] = (tokenizer, config, model)
    return _direct_models[key]


def _sentiment_labels(text: str, model_type) -> Tuple[str, List[float]]:
    """
    Direct AutoModel inference: softmax → argsort ranking → id2label.
    Returns (top_label, probabilities_ordered_by_SUPPORTED_MODELS_labels).
    """
    key = model_type.value if hasattr(model_type, "value") else model_type
    tokenizer, config, model = _get_direct_model(model_type)
    ordered_labels = SUPPORTED_MODELS[key]["labels"]

    import torch
    encoded = tokenizer(text, padding=True, truncation=True, max_length=512, return_tensors="pt")
    with torch.no_grad():
        output = model(**encoded)
    scores = output.logits[0].numpy()
    scores = softmax(scores)

    ranking  = np.argsort(scores)[::-1]
    top_raw  = config.id2label[ranking[0]]

    label_map      = SUPPORTED_MODELS[key].get("label_map", {})
    top_label_norm = label_map.get(top_raw, top_raw.upper())

    score_map = {
        label_map.get(config.id2label[i], config.id2label[i].upper()): float(scores[i])
        for i in range(len(scores))
    }
    probabilities = [score_map.get(l, 0.0) for l in ordered_labels]

    return top_label_norm, probabilities


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_sentiment(
    text: str,
    model_type: str = ModelType.BERT_HC_V2,
) -> Tuple[str, List[float]]:
    """
    Run sentiment inference on *text* with the chosen healthcare model.

    Returns:
        (sentiment_label, probabilities)
        probabilities align with SUPPORTED_MODELS[model_type]['labels'],
        i.e. ["NEGATIVE", "NEUTRAL", "POSITIVE"].
    """
    return _sentiment_labels(text, model_type)


def get_word_distribution(
    words: List[str],
    model_type: str = ModelType.BERT_HC_V2,
) -> WordDistribution:
    """
    Score each word individually and aggregate into a distribution.

    Returns a WordDistribution with keys matching the model's label set,
    all lowercased for consistency.
    """
    counters:   Dict[str, int]       = {"negative": 0, "neutral": 0, "positive": 0}
    word_lists: Dict[str, List[str]] = {"negative": [], "neutral": [], "positive": []}
    for word in words:
        ws, _ = analyze_sentiment(word, model_type)
        key = ws.lower()
        if key in counters:
            counters[key] += 1
            word_lists[key].append(word)

    return WordDistribution(distribution=counters, word_lists=word_lists)
