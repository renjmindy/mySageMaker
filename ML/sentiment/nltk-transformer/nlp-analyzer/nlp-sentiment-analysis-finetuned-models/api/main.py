"""
FastAPI application for the NLP Sentiment Analysis REST API.

Run with:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

app = FastAPI(
    title="NLP OpenMed Sentiment Analysis API",
    description=(
        "HIPAA-aware NLP pipeline with 13 Transformer models: "
        "6 fine-tuned healthcare models (cjen1008/*) + 7 pretrained general-purpose models. "
        "Performs OpenMed PII redaction, full preprocessing (cleaning, tokenisation, stemming, "
        "lemmatisation, NER, POS) then runs sentiment inference."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1", tags=["sentiment"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
