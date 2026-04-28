"""FastAPI route handlers for the sentiment analysis REST API."""

import os
import sys

from fastapi import APIRouter, HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.preprocessor import preprocess_text
from src.analyzer import analyze_sentiment, get_word_distribution
from src.models import SUPPORTED_MODELS

from .schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse, NEREntity

router = APIRouter()

# tracks which pipelines have been loaded (for the health endpoint)
_loaded: list[str] = []


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", models_loaded=_loaded)


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    text = req.text.strip()
    words = text.split()

    if len(words) < 4:
        raise HTTPException(status_code=422, detail="Text must be at least 4 words.")
    if len(words) > 300:
        raise HTTPException(status_code=422, detail="Text must not exceed 300 words.")
    if req.model_type not in SUPPORTED_MODELS:
        valid = list(SUPPORTED_MODELS.keys())
        raise HTTPException(status_code=422, detail=f"model_type must be one of {valid}.")

    cleaned, removed, normalized, tokenized, stemmed, lemmatized, ner, pos = preprocess_text(text)

    sentiment, probabilities = analyze_sentiment(text, req.model_type)
    word_dist = get_word_distribution(lemmatized, req.model_type)

    labels = SUPPORTED_MODELS[req.model_type]["labels"]
    while len(probabilities) < len(labels):
        probabilities.append(0.0)

    if req.model_type not in _loaded:
        _loaded.append(req.model_type)

    return AnalyzeResponse(
        sentiment=sentiment,
        probabilities=probabilities[: len(labels)],
        labels=labels,
        model_type=req.model_type,
        cleaned_text=cleaned,
        tokenized_text=tokenized,
        lemmatized_text=lemmatized,
        ner=[NEREntity(text=e[0], label=e[1]) for e in ner],
        word_distribution=word_dist.distribution,
        total_words=len(tokenized),
    )
