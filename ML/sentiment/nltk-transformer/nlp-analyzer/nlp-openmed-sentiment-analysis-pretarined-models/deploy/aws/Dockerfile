# AWS Lambda container image — NLP Sentiment Analysis API
# Builds for linux/amd64 (Lambda requirement)
#
# Build:  docker build --platform linux/amd64 -f deploy/aws/Dockerfile -t nlp-sentiment-lambda .
# Test:   docker run -p 9000:8080 nlp-sentiment-lambda
#         curl -X POST http://localhost:9000/2015-03-31/functions/function/invocations \
#              -d '{"httpMethod":"GET","path":"/api/v1/health","headers":{},"body":null}'

FROM public.ecr.aws/lambda/python:3.12

# Build tools needed by tokenizers / spaCy (Amazon Linux 2023 uses dnf)
RUN dnf install -y gcc gcc-c++ && dnf clean all

WORKDIR /var/task

# ── Python dependencies (API only — no Gradio / Plotly / PDF libs) ────────────
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    "torch>=2.1.1" \
    "scipy>=1.11.0" \
    "numpy>=1.26.4" \
    "transformers>=4.44.2" \
    "tokenizers>=0.19.1" \
    "accelerate>=0.26.0" \
    "spacy>=3.7.0" \
    "https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.8.0/en_core_web_md-3.8.0-py3-none-any.whl" \
    "nltk>=3.9.1" \
    "fastapi>=0.104.0" \
    "pydantic>=2.9.0" \
    "mangum>=0.17.0"

# ── NLTK data bundled into image ──────────────────────────────────────────────
ENV NLTK_DATA=/var/task/nltk_data
RUN mkdir -p ${NLTK_DATA} && python - <<'PY'
import nltk, os
for pkg in ["punkt", "punkt_tab", "wordnet", "averaged_perceptron_tagger"]:
    nltk.download(pkg, download_dir=os.environ["NLTK_DATA"], quiet=True)
PY

# ── Pre-download all 7 HuggingFace models ─────────────────────────────────────
# Baked into image → zero download delay at runtime (cold start = model load only)
# Uses AutoModel (same path as analyzer.py) so weights are cached identically
ENV HF_HOME=/var/task/.cache/huggingface \
    TRANSFORMERS_CACHE=/var/task/.cache/huggingface
RUN mkdir -p ${HF_HOME} && python - <<'PY'
import os
os.environ["HF_HOME"] = "/var/task/.cache/huggingface"

from transformers import AutoTokenizer, AutoConfig, AutoModelForSequenceClassification, pipeline

# 5 direct-inference models (AutoModel path used by analyzer.py)
direct = [
    ("distilbert-base-uncased-finetuned-sst-2-english", None),
    ("nlptown/bert-base-multilingual-uncased-sentiment", None),
    ("sohan-ai/sentiment-analysis-model-amazon-reviews", "distilbert-base-uncased"),
    ("cardiffnlp/twitter-roberta-base-sentiment-latest", None),
    ("textattack/bert-base-uncased-SST-2",               "bert-base-uncased"),
]
for hf_id, tok_id in direct:
    print(f"Caching {hf_id} ...")
    AutoTokenizer.from_pretrained(tok_id or hf_id)
    AutoConfig.from_pretrained(hf_id)
    AutoModelForSequenceClassification.from_pretrained(hf_id)

# GoEmotions — pipeline path
print("Caching j-hartmann/emotion-english-distilroberta-base ...")
pipeline("sentiment-analysis", model="j-hartmann/emotion-english-distilroberta-base", top_k=None)

# Zero-shot — pipeline path
print("Caching facebook/bart-large-mnli ...")
pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

print("All 7 models cached.")
PY

# ── Application source ────────────────────────────────────────────────────────
COPY src/              ./src/
COPY api/              ./api/
COPY lambda_handler.py .

CMD ["lambda_handler.handler"]
