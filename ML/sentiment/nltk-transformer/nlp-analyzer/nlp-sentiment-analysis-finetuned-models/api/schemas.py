"""Pydantic request and response schemas for the sentiment analysis API."""

from typing import Dict, List
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Text to analyse (4–300 words)")
    model_type: str = Field(
        "bert_hc_v2",
        description=(
            "One of: 'bert_hc_v2' (BERT Healthcare v2), "
            "'distilroberta_hc_v2' (DistilRoBERTa Healthcare v2), "
            "'distilbert_hc_v2' (DistilBERT Healthcare v2), "
            "'bert_hc' (BERT Healthcare), "
            "'distilbert_hc' (DistilBERT Healthcare), "
            "'distilroberta_hc' (DistilRoBERTa Healthcare)"
        ),
    )


class NEREntity(BaseModel):
    text: str
    label: str


class AnalyzeResponse(BaseModel):
    sentiment: str
    probabilities: List[float]
    labels: List[str]
    model_type: str
    cleaned_text: str
    tokenized_text: List[str]
    lemmatized_text: List[str]
    ner: List[NEREntity]
    word_distribution: Dict[str, int]
    total_words: int


class HealthResponse(BaseModel):
    status: str
    models_loaded: List[str]


class WarmupResponse(BaseModel):
    status: str
    models: Dict[str, str]   # model_key → "already warm" | "loaded in Xs" | "error: ..."
