"""Pydantic request/response schemas for the topic analysis API."""

from typing import Dict, List
from pydantic import BaseModel, Field


class TopicRequest(BaseModel):
    texts: List[str] = Field(
        ...,
        min_length=1,
        description="List of documents to analyse (minimum 5 recommended)",
    )
    model_type: str = Field(
        "bertopic_mini",
        description=(
            "One of: 'bertopic_mini' (BERTopic + MiniLM), "
            "'bertopic_mpnet' (BERTopic + MPNet), "
            "'lda' (Latent Dirichlet Allocation), "
            "'nmf' (Non-negative Matrix Factorization)"
        ),
    )
    n_topics: int = Field(
        5,
        ge=2,
        le=20,
        description="Number of topics for LDA/NMF (ignored for BERTopic)",
    )


class TopicInfoResponse(BaseModel):
    topic_id:  int
    keywords:  List[str]
    scores:    List[float]
    doc_count: int


class DocumentResultResponse(BaseModel):
    doc_id:         int
    text:           str
    topic_id:       int
    topic_keywords: List[str]
    probability:    float


class TopicResponse(BaseModel):
    model_type:    str
    num_topics:    int
    outlier_count: int
    topics:        List[TopicInfoResponse]
    documents:     List[DocumentResultResponse]


class HealthResponse(BaseModel):
    status: str
