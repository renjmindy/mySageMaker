# NLP Sentiment Analysis - Docker Image
# Supports both API (port 8000) and UI/Gradio (port 7860) modes
#
# Build:  docker build -t nlp-sentiment .
# API:    docker run -p 8000:8000 -e MODE=api nlp-sentiment
# UI:     docker run -p 7860:7860 -e MODE=ui  nlp-sentiment

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/.cache/huggingface \
    NLTK_DATA=/app/nltk_data \
    MPLCONFIGDIR=/app/.config/matplotlib \
    MODE=api \
    PORT=8000

# System dependencies (needed by wordcloud / Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gcc \
    g++ \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Install Python dependencies (layer cached separately from app code)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_md

# Pre-download NLTK data to the writable directory
RUN mkdir -p ${NLTK_DATA} && python - <<'PY'
import nltk, os
for pkg in ["punkt", "punkt_tab", "wordnet", "averaged_perceptron_tagger"]:
    nltk.download(pkg, download_dir=os.environ["NLTK_DATA"], quiet=True)
PY

# Pre-download all three HuggingFace models (faster cold starts)
RUN mkdir -p ${HF_HOME} && python - <<'PY'
from transformers import pipeline
pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment")
pipeline("sentiment-analysis", model="j-hartmann/emotion-english-distilroberta-base")
print("All models pre-loaded.")
PY

# Create matplotlib config dir
RUN mkdir -p ${MPLCONFIGDIR}

# Copy application code
COPY src/       ./src/
COPY api/       ./api/
COPY ui/        ./ui/
COPY examples/  ./examples/
COPY lambda_handler.py ./

RUN chown -R appuser:appuser /app
USER appuser

# Expose both ports (API: 8000, Gradio UI: 7860)
EXPOSE 8000 7860

# Health check (works for both modes)
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/v1/health || curl -f http://localhost:${PORT}/ || exit 1

# Switch on MODE at runtime
CMD if [ "$MODE" = "ui" ]; then \
        python -m ui.app; \
    else \
        uvicorn api.main:app --host 0.0.0.0 --port ${PORT}; \
    fi
