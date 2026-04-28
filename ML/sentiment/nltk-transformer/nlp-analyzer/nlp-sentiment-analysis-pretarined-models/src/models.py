"""
Type definitions and model configuration for the sentiment analysis pipeline.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ModelType(str, Enum):
    DEFAULT = "default"   # DistilBERT SST-2
    ROBERTA = "roberta"   # NLP Town BERT Multilingual
    EMOTION = "emotion"   # GoEmotions DistilRoBERTa
    AMAZON  = "amazon"    # Amazon Reviews DistilBERT
    TWITTER = "twitter"   # CardiffNLP Twitter RoBERTa
    SST2     = "sst2"      # BERT base uncased SST-2
    ZEROSHOT = "zeroshot"  # BART Large MNLI (zero-shot)


SUPPORTED_MODELS: Dict[str, Dict] = {
    ModelType.DEFAULT: {
        "hf_id":       "distilbert-base-uncased-finetuned-sst-2-english",
        "labels":      ["NEGATIVE", "POSITIVE"],
        "display":     "DistilBERT SST-2",
        "task":        "POSITIVE / NEGATIVE",
    },
    ModelType.ROBERTA: {
        "hf_id":       "nlptown/bert-base-multilingual-uncased-sentiment",
        "labels":      ["1 STAR", "2 STARS", "3 STARS", "4 STARS", "5 STARS"],
        "label_map":   {
            "1 star":  "1 STAR",
            "2 stars": "2 STARS",
            "3 stars": "3 STARS",
            "4 stars": "4 STARS",
            "5 stars": "5 STARS",
        },
        "display":     "BERT Multilingual",
        "task":        "1–5 star rating",
    },
    ModelType.EMOTION: {
        "hf_id":       "j-hartmann/emotion-english-distilroberta-base",
        "labels":      ["ANGER", "DISGUST", "FEAR", "JOY", "NEUTRAL", "SADNESS", "SURPRISE"],
        "display":     "GoEmotions",
        "task":        "7-class emotion",
    },
    ModelType.AMAZON: {
        "hf_id":       "sohan-ai/sentiment-analysis-model-amazon-reviews",
        "tokenizer":   "distilbert-base-uncased",
        "labels":      ["NEGATIVE", "POSITIVE"],
        "label_map":   {"LABEL_0": "NEGATIVE", "LABEL_1": "POSITIVE"},
        "display":     "Amazon Reviews BERT",
        "task":        "POSITIVE / NEGATIVE",
    },
    ModelType.TWITTER: {
        "hf_id":       "cardiffnlp/twitter-roberta-base-sentiment-latest",
        "labels":      ["NEGATIVE", "NEUTRAL", "POSITIVE"],
        "label_map":   {"Negative": "NEGATIVE", "Neutral": "NEUTRAL", "Positive": "POSITIVE"},
        "display":     "RoBERTa Twitter",
        "task":        "NEGATIVE / NEUTRAL / POSITIVE",
    },
    ModelType.SST2: {
        "hf_id":       "textattack/bert-base-uncased-SST-2",
        "tokenizer":   "bert-base-uncased",
        "labels":      ["NEGATIVE", "POSITIVE"],
        "label_map":   {"LABEL_0": "NEGATIVE", "LABEL_1": "POSITIVE"},
        "display":     "BERT SST-2",
        "task":        "POSITIVE / NEGATIVE",
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
