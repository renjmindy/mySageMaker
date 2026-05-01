"""
Type definitions and model configuration for the topic analysis pipeline.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ModelType(str, Enum):
    BERTOPIC_MINI  = "bertopic_mini"   # BERTopic + all-MiniLM-L6-v2  (fast)
    BERTOPIC_MPNET = "bertopic_mpnet"  # BERTopic + all-mpnet-base-v2  (quality)
    LSI            = "lsi"             # Latent Semantic Indexing  (gensim)
    HDP            = "hdp"             # Hierarchical Dirichlet Process  (gensim)
    LDA            = "lda"             # Latent Dirichlet Allocation  (gensim)
    NMF            = "nmf"             # Non-negative Matrix Factorization  (sklearn)


SUPPORTED_MODELS: Dict[str, Dict] = {
    ModelType.BERTOPIC_MINI: {
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "display":         "BERTopic (MiniLM)",
        "description":     "Fast transformer-based topic discovery",
        "type":            "bertopic",
    },
    ModelType.BERTOPIC_MPNET: {
        "embedding_model": "sentence-transformers/all-mpnet-base-v2",
        "display":         "BERTopic (MPNet)",
        "description":     "Higher quality transformer-based topic discovery",
        "type":            "bertopic",
    },
    ModelType.LSI: {
        "display":     "LSI",
        "description": "Latent Semantic Indexing — SVD on TF-IDF, fast and deterministic",
        "type":        "gensim",
    },
    ModelType.HDP: {
        "display":     "HDP",
        "description": "Hierarchical Dirichlet Process — Bayesian, auto topic count",
        "type":        "gensim",
    },
    ModelType.LDA: {
        "display":     "LDA",
        "description": "Latent Dirichlet Allocation — gensim corpus, interpretable",
        "type":        "gensim",
    },
    ModelType.NMF: {
        "display":     "NMF",
        "description": "Non-negative Matrix Factorization — TF-IDF, good for short texts",
        "type":        "sklearn",
    },
}

MODEL_LABEL_TO_TYPE: Dict[str, str] = {
    "BERTopic (MiniLM)  — fast transformer":       ModelType.BERTOPIC_MINI,
    "BERTopic (MPNet)   — quality transformer":     ModelType.BERTOPIC_MPNET,
    "LSI                — latent semantic indexing": ModelType.LSI,
    "HDP                — auto topic count":         ModelType.HDP,
    "LDA                — gensim corpus":            ModelType.LDA,
    "NMF                — matrix factorization":     ModelType.NMF,
}


@dataclass
class TopicInfo:
    topic_id:   int
    keywords:   List[str]          # top words for this topic
    scores:     List[float]        # keyword weights
    doc_count:  int                # number of docs assigned to this topic


@dataclass
class DocumentResult:
    doc_id:    int
    text:      str
    topic_id:  int
    topic_keywords: List[str]
    probability: float             # confidence of assignment


@dataclass
class TopicResult:
    model_type:   str
    num_topics:   int
    topics:       List[TopicInfo]
    documents:    List[DocumentResult]
    outlier_count: int             # docs assigned to topic -1 (BERTopic noise)
