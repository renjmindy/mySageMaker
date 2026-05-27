"""
BERTopic-backed zero-shot classifier for the 15 PREM healthcare topics.

Strategy (zero-shot cosine similarity):
  1. At load time: encode each topic's rich description with the model's
     SentenceTransformer (all-MiniLM-L6-v2 or all-mpnet-base-v2).
  2. At inference: encode input text, compute cosine similarity against
     all 15 topic embeddings, return the argmax as the predicted topic.

This approach uses BERTopic's underlying encoder in a guided, zero-shot
fashion — stable for single-document classification without needing to
retrain BERTopic's clustering layer for every new query.

Topic embeddings are computed once and cached after the first load.
"""

from __future__ import annotations

import numpy as np
from typing import Dict, List, Optional, Tuple

from .topics import TOPIC_NAMES, TOPIC_DESCRIPTIONS, N_TOPICS


class BertTopicZeroShotClassifier:
    """
    Zero-shot healthcare topic classifier using sentence embeddings.

    Args:
        embedding_model_id: HuggingFace model ID for SentenceTransformer.
            Use 'sentence-transformers/all-MiniLM-L6-v2' (bertopic_mini)
             or 'sentence-transformers/all-mpnet-base-v2' (bertopic_mpnet).
    """

    MODEL_NAME_MAP = {
        "sentence-transformers/all-MiniLM-L6-v2":  "bertopic_mini",
        "sentence-transformers/all-mpnet-base-v2":  "bertopic_mpnet",
    }

    def __init__(self, embedding_model_id: str) -> None:
        self.embedding_model_id = embedding_model_id
        self.model_name = self.MODEL_NAME_MAP.get(embedding_model_id, embedding_model_id)
        self._encoder = None
        self._topic_embeddings: Optional[np.ndarray] = None  # shape (N_TOPICS, dim)

    # ── lazy loader ────────────────────────────────────────────────────────
    def _load(self) -> None:
        if self._encoder is not None:
            return
        from sentence_transformers import SentenceTransformer
        self._encoder = SentenceTransformer(self.embedding_model_id)
        # Pre-compute topic description embeddings (N_TOPICS, dim)
        descriptions = [TOPIC_DESCRIPTIONS[i] for i in range(N_TOPICS)]
        self._topic_embeddings = self._encoder.encode(
            descriptions,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    # ── internal helpers ───────────────────────────────────────────────────
    @staticmethod
    def _cosine_similarity_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """a: (n, d), b: (m, d) — returns (n, m) cosine similarity matrix."""
        # Both are already L2-normalised by SentenceTransformer
        return a @ b.T

    # ── public API ─────────────────────────────────────────────────────────
    def classify(self, texts: List[str], top_n: int = 3) -> List[Dict]:
        """
        Classify a batch of texts.

        Args:
            texts:  list of raw (unsanitised) input strings.
            top_n:  number of top topics to include in the response.

        Returns:
            List of dicts, one per text:
            {
                "topic_id":   int,
                "topic_name": str,
                "confidence": float,   # cosine similarity score [0..1]
                "top_topics": [
                    {"topic_id": int, "topic_name": str, "score": float}, ...
                ]
            }
        """
        self._load()

        doc_embeddings: np.ndarray = self._encoder.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )  # (n_docs, dim)

        sim_matrix = self._cosine_similarity_matrix(
            doc_embeddings, self._topic_embeddings
        )  # (n_docs, N_TOPICS)

        results: List[Dict] = []
        for row in sim_matrix:
            # Shift to [0, 1] — cosine can be negative; shift by +1 then /2
            scores = (row + 1.0) / 2.0
            ranked_idx = np.argsort(scores)[::-1]
            best_idx   = int(ranked_idx[0])

            top_topics = [
                {
                    "topic_id":   int(ranked_idx[k]),
                    "topic_name": TOPIC_NAMES[int(ranked_idx[k])],
                    "score":      float(round(scores[ranked_idx[k]], 4)),
                }
                for k in range(min(top_n, N_TOPICS))
            ]

            results.append(
                {
                    "topic_id":   best_idx,
                    "topic_name": TOPIC_NAMES[best_idx],
                    "confidence": float(round(scores[best_idx], 4)),
                    "top_topics": top_topics,
                }
            )
        return results

    def is_loaded(self) -> bool:
        return self._encoder is not None
