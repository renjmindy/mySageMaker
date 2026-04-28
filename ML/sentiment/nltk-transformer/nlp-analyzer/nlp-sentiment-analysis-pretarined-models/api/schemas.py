"""Pydantic request and response schemas for the sentiment analysis API."""

from typing import Dict, List
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Text to analyse (4–300 words)")
    model_type: str = Field(
        "default",
        description=(
            "One of: 'default' (DistilBERT SST-2), 'roberta' (BERT Multilingual 5-star), "
            "'emotion' (GoEmotions 7-class), 'amazon' (Amazon Reviews), "
            "'twitter' (RoBERTa Twitter), 'sst2' (BERT SST-2), 'zeroshot' (BART MNLI)"
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
