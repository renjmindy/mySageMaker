"""
Type definitions and model configuration for the sentiment analysis pipeline.
Fine-tuned healthcare sentiment models by cjen1008.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ModelType(str, Enum):
    BERT_HC_V2          = "bert_hc_v2"          # BERT Healthcare v2
    DISTILROBERTA_HC_V2 = "distilroberta_hc_v2" # DistilRoBERTa Healthcare v2
    DISTILBERT_HC_V2    = "distilbert_hc_v2"    # DistilBERT Healthcare v2
    BERT_HC             = "bert_hc"             # BERT Healthcare v1
    DISTILBERT_HC       = "distilbert_hc"       # DistilBERT Healthcare v1
    DISTILROBERTA_HC    = "distilroberta_hc"    # DistilRoBERTa Healthcare v1


SUPPORTED_MODELS: Dict[str, Dict] = {
    ModelType.BERT_HC_V2: {
        "hf_id":     "cjen1008/bert-healthcare-sentiment_v2",
        "labels":    ["NEGATIVE", "NEUTRAL", "POSITIVE"],
        "label_map": {"LABEL_0": "NEGATIVE", "LABEL_1": "NEUTRAL", "LABEL_2": "POSITIVE"},
        "display":   "BERT Healthcare v2",
        "task":      "NEGATIVE / NEUTRAL / POSITIVE",
    },
    ModelType.DISTILROBERTA_HC_V2: {
        "hf_id":     "cjen1008/distilroberta-healthcare-sentiment_v2",
        "labels":    ["NEGATIVE", "NEUTRAL", "POSITIVE"],
        "label_map": {"LABEL_0": "NEGATIVE", "LABEL_1": "NEUTRAL", "LABEL_2": "POSITIVE"},
        "display":   "DistilRoBERTa Healthcare v2",
        "task":      "NEGATIVE / NEUTRAL / POSITIVE",
    },
    ModelType.DISTILBERT_HC_V2: {
        "hf_id":     "cjen1008/distilbert-healthcare-sentiment_v2",
        "labels":    ["NEGATIVE", "NEUTRAL", "POSITIVE"],
        "label_map": {"LABEL_0": "NEGATIVE", "LABEL_1": "NEUTRAL", "LABEL_2": "POSITIVE"},
        "display":   "DistilBERT Healthcare v2",
        "task":      "NEGATIVE / NEUTRAL / POSITIVE",
    },
    ModelType.BERT_HC: {
        "hf_id":     "cjen1008/bert-healthcare-sentiment",
        "labels":    ["NEGATIVE", "NEUTRAL", "POSITIVE"],
        "label_map": {"negative": "NEGATIVE", "neutral": "NEUTRAL", "positive": "POSITIVE"},
        "display":   "BERT Healthcare",
        "task":      "NEGATIVE / NEUTRAL / POSITIVE",
    },
    ModelType.DISTILBERT_HC: {
        "hf_id":     "cjen1008/distilbert-healthcare-sentiment",
        "labels":    ["NEGATIVE", "NEUTRAL", "POSITIVE"],
        "label_map": {"negative": "NEGATIVE", "neutral": "NEUTRAL", "positive": "POSITIVE"},
        "display":   "DistilBERT Healthcare",
        "task":      "NEGATIVE / NEUTRAL / POSITIVE",
    },
    ModelType.DISTILROBERTA_HC: {
        "hf_id":     "cjen1008/distilroberta-healthcare-sentiment",
        "labels":    ["NEGATIVE", "NEUTRAL", "POSITIVE"],
        "label_map": {"negative": "NEGATIVE", "neutral": "NEUTRAL", "positive": "POSITIVE"},
        "display":   "DistilRoBERTa Healthcare",
        "task":      "NEGATIVE / NEUTRAL / POSITIVE",
    },
}

# Human-readable dropdown labels → ModelType
MODEL_LABEL_TO_TYPE: Dict[str, str] = {
    "BERT Healthcare v2  (NEGATIVE / NEUTRAL / POSITIVE)":          ModelType.BERT_HC_V2,
    "DistilRoBERTa Healthcare v2  (NEGATIVE / NEUTRAL / POSITIVE)": ModelType.DISTILROBERTA_HC_V2,
    "DistilBERT Healthcare v2  (NEGATIVE / NEUTRAL / POSITIVE)":    ModelType.DISTILBERT_HC_V2,
    "BERT Healthcare  (NEGATIVE / NEUTRAL / POSITIVE)":             ModelType.BERT_HC,
    "DistilBERT Healthcare  (NEGATIVE / NEUTRAL / POSITIVE)":       ModelType.DISTILBERT_HC,
    "DistilRoBERTa Healthcare  (NEGATIVE / NEUTRAL / POSITIVE)":    ModelType.DISTILROBERTA_HC,
}


@dataclass
class PreprocessResult:
    original_text:   str
    cleaned_text:    str
    removed_text:    str
    normalized_text: str
    tokenized_text:  List[str]
    stemmed_text:    List[str]
    lemmatized_text: List[str]
    ner:             List[Tuple[str, str]]
    pos:             List[Tuple[str, str]]


@dataclass
class WordDistribution:
    distribution: Dict[str, int]        # label → count
    word_lists:   Dict[str, List[str]]  # label → words


@dataclass
class SentimentResult:
    sentiment:     str
    probabilities: List[float]
    model_type:    str
    labels:        List[str]
    preprocess:    PreprocessResult
    word_dist:     WordDistribution
