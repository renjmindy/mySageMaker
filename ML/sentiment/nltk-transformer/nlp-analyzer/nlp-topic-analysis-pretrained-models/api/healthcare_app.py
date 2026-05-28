"""FastAPI wrapper for the Healthcare PREM Topic Classifier.

Endpoints:
  GET  /health   — model load status
  POST /classify — classify patient feedback into 15 PREM topics
"""

import time
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from healthcare_classifier import HealthcareTopicClassifier

_classifier: Optional[HealthcareTopicClassifier] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _classifier
    _classifier = HealthcareTopicClassifier()
    _classifier.load_all()
    yield


app = FastAPI(
    title="Healthcare PREM Topic Classifier API",
    description=(
        "Classifies patient feedback into 15 predefined PREM "
        "(Patient Reported Experience Measure) topic categories using "
        "six NLP models: BERTopic (MiniLM / MPNet), LDA, LSI, HDP, and NMF. "
        "All models are pre-trained on the PREM seed corpus at build time — "
        "no internet connection required at runtime."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClassifyRequest(BaseModel):
    texts: Optional[List[str]] = Field(
        None,
        description="List of patient feedback texts to classify (use this or 'text').",
    )
    text: Optional[str] = Field(
        None,
        description="Single text shortcut — wrapped in a list automatically.",
    )
    models: List[str] = Field(
        default=["all"],
        description=(
            "Which models to run. Use [\"all\"] for all six, or any subset of: "
            "bertopic_mini, bertopic_mpnet, lda, lsi, hdp, nmf."
        ),
    )
    top_n: int = Field(
        default=3,
        ge=1,
        le=15,
        description="Number of top topics to include per result (1–15).",
    )


@app.get("/health")
def health():
    return {"status": "ok", "models_loaded": _classifier.status()}


@app.post("/classify")
def classify(req: ClassifyRequest):
    texts = req.texts
    if texts is None and req.text:
        texts = [req.text]
    if not texts:
        raise HTTPException(status_code=422, detail='Provide "text" or "texts".')
    if not all(isinstance(t, str) for t in texts):
        raise HTTPException(status_code=422, detail='All items in "texts" must be strings.')
    if len(texts) > 500:
        raise HTTPException(status_code=422, detail="Maximum 500 texts per request.")

    t0 = time.time()
    try:
        results = _classifier.classify(texts=texts, models=req.models, top_n=req.top_n)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {
        "results":      results,
        "model_status": _classifier.status(),
        "elapsed_sec":  round(time.time() - t0, 3),
    }
