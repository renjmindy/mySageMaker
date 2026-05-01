"""FastAPI route handlers for the topic analysis REST API."""

import os, sys
from fastapi import APIRouter, HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.topic_modeler import run_topic_model
from src.models import SUPPORTED_MODELS
from .schemas import (
    TopicRequest, TopicResponse,
    TopicInfoResponse, DocumentResultResponse, HealthResponse,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")


@router.post("/topics", response_model=TopicResponse)
def topics(req: TopicRequest):
    if len(req.texts) < 2:
        raise HTTPException(status_code=422, detail="Provide at least 2 documents.")
    if len(req.texts) > 1000:
        raise HTTPException(status_code=422, detail="Maximum 1000 documents per request.")
    if req.model_type not in SUPPORTED_MODELS:
        valid = list(SUPPORTED_MODELS.keys())
        raise HTTPException(status_code=422, detail=f"model_type must be one of {valid}.")

    result = run_topic_model(req.texts, req.model_type, req.n_topics)

    return TopicResponse(
        model_type=result.model_type,
        num_topics=result.num_topics,
        outlier_count=result.outlier_count,
        topics=[
            TopicInfoResponse(
                topic_id=t.topic_id,
                keywords=t.keywords,
                scores=t.scores,
                doc_count=t.doc_count,
            )
            for t in result.topics
        ],
        documents=[
            DocumentResultResponse(
                doc_id=d.doc_id,
                text=d.text,
                topic_id=d.topic_id,
                topic_keywords=d.topic_keywords,
                probability=d.probability,
            )
            for d in result.documents
        ],
    )
