"""
Type definitions and model configuration for the sentiment analysis pipeline.
Combines 6 fine-tuned healthcare models (cjen1008) and 7 pretrained general models.
Total: 13 models.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ModelType(str, Enum):
    # ── Fine-tuned healthcare models (cjen1008) ───────────────────────────────
    BERT_HC_V2          = "bert_hc_v2"          # BERT Healthcare v2
    DISTILROBERTA_HC_V2 = "distilroberta_hc_v2" # DistilRoBERTa Healthcare v2
    DISTILBERT_HC_V2    = "distilbert_hc_v2"    # DistilBERT Healthcare v2
    BERT_HC             = "bert_hc"             # BERT Healthcare v1
    DISTILBERT_HC       = "distilbert_hc"       # DistilBERT Healthcare v1
    DISTILROBERTA_HC    = "distilroberta_hc"    # DistilRoBERTa Healthcare v1
    # ── Pretrained general-purpose models ─────────────────────────────────────
    DEFAULT  = "default"    # DistilBERT SST-2
    ROBERTA  = "roberta"    # NLP Town BERT Multilingual
    EMOTION  = "emotion"    # GoEmotions DistilRoBERTa
    AMAZON   = "amazon"     # Amazon Reviews DistilBERT
    TWITTER  = "twitter"    # CardiffNLP Twitter RoBERTa
    SST2     = "sst2"       # BERT base uncased SST-2
    ZEROSHOT = "zeroshot"   # BART Large MNLI (zero-shot)


SUPPORTED_MODELS: Dict[str, Dict] = {
    # ── Fine-tuned healthcare models ──────────────────────────────────────────
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
    # ── Pretrained general-purpose models ─────────────────────────────────────
    ModelType.DEFAULT: {
        "hf_id":   "distilbert-base-uncased-finetuned-sst-2-english",
        "labels":  ["NEGATIVE", "POSITIVE"],
        "display": "DistilBERT SST-2",
        "task":    "POSITIVE / NEGATIVE",
    },
    ModelType.ROBERTA: {
        "hf_id":     "nlptown/bert-base-multilingual-uncased-sentiment",
        "labels":    ["1 STAR", "2 STARS", "3 STARS", "4 STARS", "5 STARS"],
        "label_map": {
            "1 star":  "1 STAR",
            "2 stars": "2 STARS",
            "3 stars": "3 STARS",
            "4 stars": "4 STARS",
            "5 stars": "5 STARS",
        },
        "display": "BERT Multilingual",
        "task":    "1–5 star rating",
    },
    ModelType.EMOTION: {
        "hf_id":   "j-hartmann/emotion-english-distilroberta-base",
        "labels":  ["ANGER", "DISGUST", "FEAR", "JOY", "NEUTRAL", "SADNESS", "SURPRISE"],
        "display": "GoEmotions",
        "task":    "7-class emotion",
    },
    ModelType.AMAZON: {
        "hf_id":     "sohan-ai/sentiment-analysis-model-amazon-reviews",
        "tokenizer": "distilbert-base-uncased",
        "labels":    ["NEGATIVE", "POSITIVE"],
        "label_map": {"LABEL_0": "NEGATIVE", "LABEL_1": "POSITIVE"},
        "display":   "Amazon Reviews BERT",
        "task":      "POSITIVE / NEGATIVE",
    },
    ModelType.TWITTER: {
        "hf_id":     "cardiffnlp/twitter-roberta-base-sentiment-latest",
        "labels":    ["NEGATIVE", "NEUTRAL", "POSITIVE"],
        "label_map": {"Negative": "NEGATIVE", "Neutral": "NEUTRAL", "Positive": "POSITIVE"},
        "display":   "RoBERTa Twitter",
        "task":      "NEGATIVE / NEUTRAL / POSITIVE",
    },
    ModelType.SST2: {
        "hf_id":     "textattack/bert-base-uncased-SST-2",
        "tokenizer": "bert-base-uncased",
        "labels":    ["NEGATIVE", "POSITIVE"],
        "label_map": {"LABEL_0": "NEGATIVE", "LABEL_1": "POSITIVE"},
        "display":   "BERT SST-2",
        "task":      "POSITIVE / NEGATIVE",
    },
    ModelType.ZEROSHOT: {
        "hf_id":            "facebook/bart-large-mnli",
        "pipeline_task":    "zero-shot-classification",
        "candidate_labels": ["positive", "negative", "neutral"],
        "labels":           ["POSITIVE", "NEGATIVE", "NEUTRAL"],
        "display":          "BART Large MNLI",
        "task":             "Zero-shot Sentiment",
    },
}

# Human-readable dropdown labels → ModelType
MODEL_LABEL_TO_TYPE: Dict[str, str] = {
    # Fine-tuned healthcare
    "BERT Healthcare v2  (NEGATIVE / NEUTRAL / POSITIVE)":          ModelType.BERT_HC_V2,
    "DistilRoBERTa Healthcare v2  (NEGATIVE / NEUTRAL / POSITIVE)": ModelType.DISTILROBERTA_HC_V2,
    "DistilBERT Healthcare v2  (NEGATIVE / NEUTRAL / POSITIVE)":    ModelType.DISTILBERT_HC_V2,
    "BERT Healthcare  (NEGATIVE / NEUTRAL / POSITIVE)":             ModelType.BERT_HC,
    "DistilBERT Healthcare  (NEGATIVE / NEUTRAL / POSITIVE)":       ModelType.DISTILBERT_HC,
    "DistilRoBERTa Healthcare  (NEGATIVE / NEUTRAL / POSITIVE)":    ModelType.DISTILROBERTA_HC,
    # Pretrained general-purpose
    "DistilBERT SST-2  (POSITIVE / NEGATIVE)":          ModelType.DEFAULT,
    "BERT Multilingual  (1–5 star rating)":              ModelType.ROBERTA,
    "GoEmotions  (7 emotions)":                          ModelType.EMOTION,
    "Amazon Reviews BERT  (POSITIVE / NEGATIVE)":        ModelType.AMAZON,
    "RoBERTa Twitter  (NEGATIVE / NEUTRAL / POSITIVE)":  ModelType.TWITTER,
    "BERT SST-2  (POSITIVE / NEGATIVE)":                 ModelType.SST2,
    "BART Large MNLI  (Zero-shot Sentiment)":             ModelType.ZEROSHOT,
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
