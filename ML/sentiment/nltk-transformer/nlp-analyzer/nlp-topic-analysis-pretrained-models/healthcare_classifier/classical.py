"""
Classical topic classifiers for the 15 PREM healthcare topics.

Models (all trained on the seed corpus — see topics.py):
  • LDA   — sklearn LatentDirichletAllocation (notebook pipeline, cell 49-51)
  • LSI   — gensim LsiModel
  • HDP   — gensim HdpModel
  • NMF   — sklearn NMF with TF-IDF

Each classifier:
  1. Loads its serialized model from /app/models/ (written by trainer.py)
  2. Preprocesses the input text through its specific pipeline
  3. Returns a topic distribution over the 15 predefined PREM topics
  4. Uses a learned index→topic alignment mapping (stored alongside the model)
"""

from __future__ import annotations

import os
import re
import pickle
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

import numpy as np

from .topics import TOPIC_NAMES, TOPIC_KEYWORDS, N_TOPICS
from .preprocessor import TextPreprocessor

MODEL_DIR = os.environ.get("MODEL_DIR", "/app/models")

# ── Shared helpers ─────────────────────────────────────────────────────────────

def _keyword_overlap_score(model_keywords: List[str], topic_idx: int) -> float:
    """
    Compute Jaccard-like overlap between a model topic's top words and the
    predefined keyword list for the given predefined topic index.
    """
    model_set   = set(w.lower() for w in model_keywords)
    defined_set = set(w.lower() for w in TOPIC_KEYWORDS[topic_idx])
    if not model_set or not defined_set:
        return 0.0
    intersection = model_set & defined_set
    return len(intersection) / len(model_set | defined_set)


def _build_alignment(model_topic_words: Dict[int, List[str]]) -> Dict[int, int]:
    """
    Greedy assignment of model topic indices → predefined topic indices.

    Computes a (n_model_topics × N_TOPICS) score matrix and greedily assigns
    each model topic to the best unassigned predefined topic.

    Returns: {model_topic_idx: predefined_topic_idx}
    """
    n_model = len(model_topic_words)
    score_matrix = np.zeros((n_model, N_TOPICS))
    for m_idx, keywords in model_topic_words.items():
        for p_idx in range(N_TOPICS):
            score_matrix[m_idx, p_idx] = _keyword_overlap_score(keywords, p_idx)

    alignment: Dict[int, int] = {}
    used_predefined: set = set()
    # Sort model topics by their max score (descending) for greedy assignment
    model_sorted = sorted(range(n_model), key=lambda i: score_matrix[i].max(), reverse=True)
    for m_idx in model_sorted:
        remaining = [p for p in range(N_TOPICS) if p not in used_predefined]
        if not remaining:
            remaining = list(range(N_TOPICS))
        best_p = max(remaining, key=lambda p: score_matrix[m_idx, p])
        alignment[m_idx] = best_p
        used_predefined.add(best_p)
    return alignment


# ── Base class ────────────────────────────────────────────────────────────────

class BaseClassicalClassifier(ABC):
    model_key: str  # e.g. "lda", "lsi", "hdp", "nmf"

    def __init__(self) -> None:
        self._alignment: Optional[Dict[int, int]] = None  # model_idx → predefined_idx
        self._loaded = False

    @abstractmethod
    def _load_model(self) -> None:
        """Load the serialized model from MODEL_DIR."""

    @abstractmethod
    def _get_distributions(self, texts: List[str]) -> np.ndarray:
        """
        Return array of shape (n_texts, n_model_topics) where each row is the
        probability distribution over model topic indices for one document.
        """

    def load(self) -> None:
        if not self._loaded:
            self._load_model()
            self._loaded = True

    def classify(self, texts: List[str], top_n: int = 3) -> List[Dict]:
        self.load()
        raw_dists = self._get_distributions(texts)  # (n_texts, n_model_topics)

        results: List[Dict] = []
        for dist in raw_dists:
            # Map from model topic indices to predefined topic indices
            predefined_scores = np.zeros(N_TOPICS)
            for m_idx, score in enumerate(dist):
                p_idx = self._alignment.get(m_idx, 0)
                predefined_scores[p_idx] = max(predefined_scores[p_idx], float(score))

            # Normalize
            total = predefined_scores.sum()
            if total > 0:
                predefined_scores /= total

            ranked_idx = np.argsort(predefined_scores)[::-1]
            best_idx   = int(ranked_idx[0])

            top_topics = [
                {
                    "topic_id":   int(ranked_idx[k]),
                    "topic_name": TOPIC_NAMES[int(ranked_idx[k])],
                    "score":      float(round(predefined_scores[ranked_idx[k]], 4)),
                }
                for k in range(min(top_n, N_TOPICS))
            ]

            results.append(
                {
                    "topic_id":   best_idx,
                    "topic_name": TOPIC_NAMES[best_idx],
                    "confidence": float(round(predefined_scores[best_idx], 4)),
                    "top_topics": top_topics,
                }
            )
        return results

    def is_loaded(self) -> bool:
        return self._loaded


# ── LDA (sklearn — notebook pipeline, cells 49-51) ───────────────────────────

class LDAClassifier(BaseClassicalClassifier):
    """
    Notebook-style pipeline:
      TextPreprocessor → CountVectorizer → LatentDirichletAllocation (n=15)
    Serialized as a single sklearn Pipeline by trainer.py.
    """
    model_key = "lda"

    def _load_model(self) -> None:
        import joblib
        path = os.path.join(MODEL_DIR, "lda_pipeline.joblib")
        data = joblib.load(path)
        self._pipeline  = data["pipeline"]  # sklearn Pipeline object
        self._alignment = data["alignment"]  # {model_idx: predefined_idx}

    def _get_distributions(self, texts: List[str]) -> np.ndarray:
        """Transform texts through TextPreprocessor + CountVectorizer → LDA."""
        dist = self._pipeline.transform(texts)  # (n, n_topics)
        # Normalize rows (LDA should already be normalized but ensure it)
        row_sums = dist.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        return dist / row_sums


# ── LSI (gensim) ──────────────────────────────────────────────────────────────

class LSIClassifier(BaseClassicalClassifier):
    """
    gensim LsiModel pipeline:
      spaCy clean → bigrams → Dictionary/corpus → LsiModel (n=15)
    Preprocessor uses NLTK-based lemmatization for Lambda (avoids spaCy dep).
    """
    model_key = "lsi"
    _preprocessor = TextPreprocessor()

    def _load_model(self) -> None:
        import joblib
        from gensim.models import LsiModel
        from gensim.corpora import Dictionary

        data = joblib.load(os.path.join(MODEL_DIR, "lsi_data.joblib"))
        self._lsi_model : LsiModel   = data["model"]
        self._dictionary: Dictionary = data["dictionary"]
        self._alignment              = data["alignment"]

    def _get_distributions(self, texts: List[str]) -> np.ndarray:
        cleaned = self._preprocessor.transform(texts)
        n_model_topics = self._lsi_model.num_topics
        dist = np.zeros((len(texts), n_model_topics))

        for i, text in enumerate(cleaned):
            tokens = text.split() if isinstance(text, str) else []
            bow    = self._dictionary.doc2bow(tokens)
            vec    = self._lsi_model[bow]  # list of (topic_id, score)
            for tid, score in vec:
                if 0 <= tid < n_model_topics:
                    dist[i, tid] = abs(float(score))
        # L1 normalise
        row_sums = dist.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        return dist / row_sums


# ── HDP (gensim) ──────────────────────────────────────────────────────────────

class HDPClassifier(BaseClassicalClassifier):
    """
    gensim HdpModel pipeline (Bayesian non-parametric, variable topic count).
    We cap at the first N_TOPICS active topics for alignment.
    """
    model_key = "hdp"
    _preprocessor = TextPreprocessor()

    def _load_model(self) -> None:
        import joblib
        from gensim.models import HdpModel
        from gensim.corpora import Dictionary

        data = joblib.load(os.path.join(MODEL_DIR, "hdp_data.joblib"))
        self._hdp_model : HdpModel   = data["model"]
        self._dictionary: Dictionary = data["dictionary"]
        self._n_topics              = data["n_topics"]   # actual active topics
        self._alignment             = data["alignment"]

    def _get_distributions(self, texts: List[str]) -> np.ndarray:
        cleaned = self._preprocessor.transform(texts)
        dist    = np.zeros((len(texts), self._n_topics))

        for i, text in enumerate(cleaned):
            tokens = text.split() if isinstance(text, str) else []
            bow    = self._dictionary.doc2bow(tokens)
            vec    = self._hdp_model[bow]
            for tid, score in vec:
                if 0 <= tid < self._n_topics:
                    dist[i, tid] = float(score)
        row_sums = dist.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        return dist / row_sums


# ── NMF (sklearn with TF-IDF) ─────────────────────────────────────────────────

class NMFClassifier(BaseClassicalClassifier):
    """
    sklearn NMF pipeline:
      TextPreprocessor → TfidfVectorizer → NMF (n=15)
    Serialized as a single sklearn Pipeline by trainer.py.
    """
    model_key = "nmf"

    def _load_model(self) -> None:
        import joblib
        data = joblib.load(os.path.join(MODEL_DIR, "nmf_pipeline.joblib"))
        self._pipeline  = data["pipeline"]
        self._alignment = data["alignment"]

    def _get_distributions(self, texts: List[str]) -> np.ndarray:
        dist = self._pipeline.transform(texts)  # (n, n_topics)
        # NMF output is non-negative; normalise to probabilities
        row_sums = dist.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        return dist / row_sums
