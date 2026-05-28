# =============================================================================
# Dockerfile  —  Healthcare PREM Topic Classifier  •  Local / Standalone image
#
# Serves the Healthcare PREM Topic Classifier REST API via FastAPI + uvicorn.
# No cloud account or internet connection required after the image is built.
# All six models (BERTopic MiniLM/MPNet, LDA, LSI, HDP, NMF) are pre-baked:
#   • Sentence-transformer weights cached at /app/hf_cache
#   • Classical models (LDA/LSI/HDP/NMF) trained on the 225-sentence PREM seed
#     corpus at build time and saved to /app/models
#   • NLTK data downloaded to /app/nltk_data
#
# Endpoints:
#   GET  /health   — model load status
#   POST /classify — classify patient feedback into 15 PREM topics
#   GET  /docs     — interactive Swagger UI
#
# Build:
#   docker build -t nlp-topic-api .
#
# Run:
#   docker run --rm -p 8001:8001 nlp-topic-api
#
# Share the image:
#   docker save nlp-topic-api | gzip > nlp-topic-api.tar.gz   # export
#   docker load < nlp-topic-api.tar.gz                        # recipient loads
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# ── System dependencies ───────────────────────────────────────────────────────
# build-essential: gcc/g++ for hdbscan / umap native extensions
# libgomp1:        OpenMP runtime required by numpy / scikit-learn at runtime
# curl:            used by the Docker healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────────────────────
# Layered early so Docker cache is reused when only source code changes.
COPY requirements.api.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --prefer-binary \
      --extra-index-url https://download.pytorch.org/whl/cpu \
      -r requirements.api.txt \
 && rm requirements.api.txt

# ── Pre-cache sentence-transformer weights ────────────────────────────────────
# HF_HOME is the single cache root used by sentence-transformers 5.x.
# Removing SENTENCE_TRANSFORMERS_HOME / TRANSFORMERS_CACHE avoids the
# old-format path conflict that prevents offline loading at runtime.
ENV HF_HOME=/app/hf_cache
ENV HF_HUB_DISABLE_IMPLICIT_TOKEN=1

RUN python - <<'EOF'
from sentence_transformers import SentenceTransformer
import os

print("Downloading all-MiniLM-L6-v2 ...")
SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
print("Downloading all-mpnet-base-v2 ...")
SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

# Ensure all cache files are world-readable
for root, dirs, files in os.walk("/app/hf_cache"):
    for d in dirs:
        os.chmod(os.path.join(root, d), 0o755)
    for f in files:
        os.chmod(os.path.join(root, f), 0o644)

print("Sentence-transformer weights cached.")
EOF

# ── Pre-download NLTK data ────────────────────────────────────────────────────
ENV NLTK_DATA=/app/nltk_data

RUN python - <<'EOF'
import nltk, os
os.makedirs(os.environ["NLTK_DATA"], exist_ok=True)
for pkg in ["punkt", "punkt_tab", "wordnet", "stopwords", "averaged_perceptron_tagger"]:
    nltk.download(pkg, download_dir=os.environ["NLTK_DATA"], quiet=False)
print("NLTK data downloaded.")
EOF

# ── Verify spaCy model ────────────────────────────────────────────────────────
RUN python -c "import spacy; spacy.load('en_core_web_md'); print('spaCy en_core_web_md OK')"

# ── Application source ────────────────────────────────────────────────────────
# Copied last so edits to src/ or api/ don't invalidate the heavy layers above.
COPY src/ ./src/
COPY api/ ./api/
COPY healthcare_classifier/ ./healthcare_classifier/
COPY scripts/ ./scripts/

# ── Train classical healthcare models (LDA / NMF / LSI / HDP) ────────────────
# Fits all four models on the 225-sentence PREM seed corpus (15 topics × 15
# sentences) and saves the serialized pipelines to /app/models/ so they are
# baked into the image for fully offline inference at runtime.
ENV MODEL_DIR=/app/models
RUN python scripts/train_models.py

# ── Runtime environment ───────────────────────────────────────────────────────
ENV TRANSFORMERS_OFFLINE=1
ENV HF_HUB_OFFLINE=1
ENV TOKENIZERS_PARALLELISM=false

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "api.healthcare_app:app", "--host", "0.0.0.0", "--port", "8001"]
