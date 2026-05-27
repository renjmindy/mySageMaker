"""
Unified healthcare topic classifier — orchestrates all six models.

Usage:
    from healthcare_classifier import HealthcareTopicClassifier

    clf = HealthcareTopicClassifier()
    clf.load_all()          # pre-warms every model

    results = clf.classify(
        texts=["The doctor was excellent..."],
        models=["all"],     # or specific model keys
        top_n=3,
    )

Response structure (one entry per input text):
    {
        "text": str,
        "classifications": {
            "bertopic_mini":  {"topic_id": 0, "topic_name": "Clinical Staff",
                               "confidence": 0.85, "top_topics": [...]},
            "bertopic_mpnet": {...},
            "lda":            {...},
            "lsi":            {...},
            "hdp":            {...},
            "nmf":            {...},
        }
    }
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from .bert_classifier import BertTopicZeroShotClassifier
from .classical import LDAClassifier, LSIClassifier, HDPClassifier, NMFClassifier

# ── Model keys ────────────────────────────────────────────────────────────────
ALL_MODELS = ["bertopic_mini", "bertopic_mpnet", "lda", "lsi", "hdp", "nmf"]

_BERT_CONFIGS = {
    "bertopic_mini":  "sentence-transformers/all-MiniLM-L6-v2",
    "bertopic_mpnet": "sentence-transformers/all-mpnet-base-v2",
}


class HealthcareTopicClassifier:
    """
    Singleton-friendly orchestrator that lazy-loads each of the six models.

    Models are loaded once into memory and reused across Lambda invocations
    (via Python's global module scope in the handler).
    """

    def __init__(self) -> None:
        # BERTopic zero-shot
        self._bert_mini  = BertTopicZeroShotClassifier(_BERT_CONFIGS["bertopic_mini"])
        self._bert_mpnet = BertTopicZeroShotClassifier(_BERT_CONFIGS["bertopic_mpnet"])
        # Classical
        self._lda = LDAClassifier()
        self._lsi = LSIClassifier()
        self._hdp = HDPClassifier()
        self._nmf = NMFClassifier()

        self._model_map: Dict[str, Any] = {
            "bertopic_mini":  self._bert_mini,
            "bertopic_mpnet": self._bert_mpnet,
            "lda":            self._lda,
            "lsi":            self._lsi,
            "hdp":            self._hdp,
            "nmf":            self._nmf,
        }

    # ── Loading ────────────────────────────────────────────────────────────
    def load_all(self) -> Dict[str, float]:
        """
        Pre-load every model into memory.
        Returns a dict of model_name → seconds_taken.
        """
        timings: Dict[str, float] = {}
        for name, model in self._model_map.items():
            if not model.is_loaded():
                t0 = time.time()
                if hasattr(model, "load"):
                    model.load()
                else:
                    # BERTopic zero-shot: trigger _load via a dummy call
                    from .topics import TOPIC_DESCRIPTIONS
                    model._load()
                timings[name] = round(time.time() - t0, 2)
            else:
                timings[name] = 0.0
        return timings

    def load_model(self, model_name: str) -> float:
        """Load a single model by name. Returns seconds taken."""
        model = self._model_map.get(model_name)
        if model is None:
            raise ValueError(f"Unknown model '{model_name}'. Valid: {ALL_MODELS}")
        if not model.is_loaded():
            t0 = time.time()
            if hasattr(model, "load"):
                model.load()
            else:
                model._load()
            return round(time.time() - t0, 2)
        return 0.0

    # ── Classification ─────────────────────────────────────────────────────
    def classify(
        self,
        texts: List[str],
        models: Optional[List[str]] = None,
        top_n: int = 3,
    ) -> List[Dict]:
        """
        Classify a list of texts using the requested models.

        Args:
            texts:  list of raw input strings (at least 1 required).
            models: list of model keys or ["all"]. Defaults to ["all"].
            top_n:  number of top topics included in each result.

        Returns:
            List of result dicts, one per input text.
        """
        if not texts:
            return []

        # Resolve model list
        if not models or models == ["all"]:
            active_models = ALL_MODELS
        else:
            unknown = [m for m in models if m not in self._model_map]
            if unknown:
                raise ValueError(
                    f"Unknown model(s): {unknown}. Valid keys: {ALL_MODELS}"
                )
            active_models = models

        # Lazy-load each requested model
        for name in active_models:
            if not self._model_map[name].is_loaded():
                self.load_model(name)

        # Run classifiers
        all_model_results: Dict[str, List[Dict]] = {}
        for name in active_models:
            all_model_results[name] = self._model_map[name].classify(texts, top_n=top_n)

        # Assemble per-text output
        output: List[Dict] = []
        for i, text in enumerate(texts):
            classifications: Dict[str, Dict] = {}
            for name in active_models:
                classifications[name] = all_model_results[name][i]
            output.append({"text": text, "classifications": classifications})

        return output

    # ── Status ─────────────────────────────────────────────────────────────
    def status(self) -> Dict[str, bool]:
        """Return load state for every model."""
        return {name: model.is_loaded() for name, model in self._model_map.items()}
