"""
Transformer model inference: sentiment classification and per-word distribution.
All three pipelines are lazy-loaded and cached on first use.
"""

from typing import Dict, List, Tuple

import numpy as np
from scipy.special import softmax
from transformers import (
    pipeline, Pipeline,
    AutoTokenizer, AutoConfig, AutoModelForSequenceClassification,
)

from .models import ModelType, SUPPORTED_MODELS, WordDistribution

# ── Pipeline cache ────────────────────────────────────────────────────────────
_pipelines: Dict[str, Pipeline] = {}

# ── Direct model cache (AutoModel path for models needing ranking) ────────────
_direct_models: Dict[str, tuple] = {}  # key → (tokenizer, config, model)


def _get_direct_model(model_type) -> tuple:
    """Load and cache (tokenizer, config, model) for direct inference."""
    key = model_type.value if hasattr(model_type, "value") else model_type
    if key not in _direct_models:
        cfg           = SUPPORTED_MODELS[key]
        hf_id         = cfg["hf_id"]
        tokenizer_id  = cfg.get("tokenizer", hf_id)  # respect tokenizer override (e.g. AMAZON)
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
    tokenizer, config, model = _get_direct_model(model_type)
    ordered_labels = SUPPORTED_MODELS[model_type.value if hasattr(model_type, "value") else model_type]["labels"]

    import torch
    encoded = tokenizer(text, padding=True, truncation=True, max_length=512, return_tensors="pt")
    with torch.no_grad():
        output = model(**encoded)
    scores = output.logits[0].numpy()
    scores = softmax(scores)

    ranking = np.argsort(scores)[::-1]
    top_label = config.id2label[ranking[0]]

    label_map = SUPPORTED_MODELS[model_type.value if hasattr(model_type, "value") else model_type].get("label_map", {})
    top_label_norm = label_map.get(top_label, top_label.upper())

    score_map = {
        label_map.get(config.id2label[i], config.id2label[i].upper()): float(scores[i])
        for i in range(len(scores))
    }
    probabilities = [score_map.get(l, 0.0) for l in ordered_labels]

    return top_label_norm, probabilities


def _get_pipeline(model_type) -> Pipeline:
    # In Python 3.11, str(ModelType.DEFAULT) returns "ModelType.DEFAULT" not "default".
    # Use .value to get the plain string key reliably across all Python versions.
    key = model_type.value if hasattr(model_type, "value") else model_type
    if key not in _pipelines:
        cfg           = SUPPORTED_MODELS[key]
        hf_id         = cfg["hf_id"]
        tokenizer     = cfg.get("tokenizer", hf_id)
        pipeline_task = cfg.get("pipeline_task", "sentiment-analysis")
        extra = {} if pipeline_task != "sentiment-analysis" else {"top_k": None}
        _pipelines[key] = pipeline(pipeline_task, model=hf_id, tokenizer=tokenizer, **extra)
    return _pipelines[key]


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_sentiment(
    text: str,
    model_type: str = ModelType.DEFAULT,
) -> Tuple[str, List[float]]:
    """
    Run sentiment inference on *text* with the chosen model.

    Returns:
        (sentiment_label, probabilities)
        probabilities align with SUPPORTED_MODELS[model_type]['labels'].
    """
    # Direct AutoModel inference: softmax → argsort → id2label ranking
    if model_type in (ModelType.ROBERTA, ModelType.TWITTER, ModelType.DEFAULT, ModelType.SST2, ModelType.AMAZON):
        return _sentiment_labels(text, model_type)

    classifier = _get_pipeline(model_type)

    # Zero-shot classification has a different call signature and result format
    if model_type == ModelType.ZEROSHOT:
        candidate_labels = SUPPORTED_MODELS[ModelType.ZEROSHOT]["candidate_labels"]
        ordered_labels   = SUPPORTED_MODELS[ModelType.ZEROSHOT]["labels"]
        raw = classifier(text, candidate_labels=candidate_labels)
        # normalize to uppercase — model may return labels in any case
        score_map = {label.upper(): score for label, score in zip(raw["labels"], raw["scores"])}
        sentiment = max(score_map, key=score_map.get)
        probabilities = [score_map.get(l, 0.0) for l in ordered_labels]
        return sentiment, probabilities

    # EMOTION (GoEmotions) — pipeline only
    raw = classifier(text)
    # top_k=None wraps output in an extra list for single-string input
    results = raw[0] if raw and isinstance(raw[0], list) else raw

    emotion_labels = SUPPORTED_MODELS[ModelType.EMOTION]["labels"]
    score_map  = {r["label"].upper(): r["score"] for r in results}
    sentiment  = max(score_map, key=score_map.get)
    probabilities = [score_map.get(l, 0.0) for l in emotion_labels]

    return sentiment, probabilities


def get_word_distribution(
    words: List[str],
    model_type: str = ModelType.DEFAULT,
) -> WordDistribution:
    """
    Score each word individually and aggregate into a distribution.

    Returns a WordDistribution with keys matching the model's label set,
    all lowercased for consistency.
    """
    if model_type == ModelType.EMOTION:
        emotion_labels = SUPPORTED_MODELS[ModelType.EMOTION]["labels"]
        counters: Dict[str, int] = {e.lower(): 0 for e in emotion_labels}
        word_lists: Dict[str, List[str]] = {e.lower(): [] for e in emotion_labels}
        for word in words:
            ws, _ = analyze_sentiment(word, model_type)
            key = ws.lower()
            if key in counters:
                counters[key] += 1
                word_lists[key].append(word)
    elif model_type == ModelType.ROBERTA:
        _star_bucket = {
            "1 star": "negative", "2 stars": "negative",
            "3 stars": "neutral",
            "4 stars": "positive", "5 stars": "positive",
        }
        counters   = {"positive": 0, "neutral": 0, "negative": 0}
        word_lists = {"positive": [], "neutral": [], "negative": []}
        for word in words:
            ws, _ = analyze_sentiment(word, model_type)
            key = _star_bucket.get(ws.lower(), "neutral")
            counters[key] += 1
            word_lists[key].append(word)

    else:
        counters = {"positive": 0, "neutral": 0, "negative": 0}
        word_lists = {"positive": [], "neutral": [], "negative": []}
        for word in words:
            ws, _ = analyze_sentiment(word, model_type)
            key = ws.lower()
            if key in counters:
                counters[key] += 1
                word_lists[key].append(word)

    return WordDistribution(distribution=counters, word_lists=word_lists)
