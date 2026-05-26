# AWS Lambda container image — NLP Healthcare Sentiment Analysis API
# Fine-tuned models by cjen1008 (bert / distilbert / distilroberta, v1 + v2)
# Builds for linux/amd64 (Lambda requirement)
#
# Build:  docker build --platform linux/amd64 --provenance=false \
#                      -f deploy/aws/Dockerfile -t nlp-hc-sentiment-lambda .
# Test:   docker run -p 9000:8080 nlp-hc-sentiment-lambda
#         curl -X POST http://localhost:9000/2015-03-31/functions/function/invocations \
#              -d '{"httpMethod":"GET","path":"/api/v1/health","resource":"/{proxy+}","headers":{},"multiValueHeaders":{},"queryStringParameters":null,"multiValueQueryStringParameters":null,"pathParameters":{"proxy":"api/v1/health"},"stageVariables":null,"requestContext":{"resourcePath":"/{proxy+}","httpMethod":"GET","stage":"local","requestId":"test"},"body":null,"isBase64Encoded":false}'

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

# ── Pre-download all 6 fine-tuned healthcare models ───────────────────────────
# Baked into image → zero download delay at runtime (cold start = model load only)
# All models use the direct AutoModel inference path (same as analyzer.py).
#   v2 models → LABEL_0/1/2 mapped to NEGATIVE/NEUTRAL/POSITIVE in analyzer
#   v1 models → native negative/neutral/positive labels
ENV HF_HOME=/var/task/.cache/huggingface \
    TRANSFORMERS_CACHE=/var/task/.cache/huggingface
RUN mkdir -p ${HF_HOME} && python - <<'PY'
import os
os.environ["HF_HOME"] = "/var/task/.cache/huggingface"

from transformers import AutoTokenizer, AutoConfig, AutoModelForSequenceClassification

models = [
    # (hf_id,                                           tokenizer_override)
    ("cjen1008/bert-healthcare-sentiment_v2",           None),
    ("cjen1008/distilroberta-healthcare-sentiment_v2",  None),
    ("cjen1008/distilbert-healthcare-sentiment_v2",     None),
    ("cjen1008/bert-healthcare-sentiment",              None),
    ("cjen1008/distilbert-healthcare-sentiment",        None),
    ("cjen1008/distilroberta-healthcare-sentiment",     None),
]

for hf_id, tok_id in models:
    print(f"Caching {hf_id} ...")
    AutoTokenizer.from_pretrained(tok_id or hf_id)
    AutoConfig.from_pretrained(hf_id)
    AutoModelForSequenceClassification.from_pretrained(hf_id)

print("All 6 healthcare models cached.")
PY

# ── Application source ────────────────────────────────────────────────────────
COPY src/              ./src/
COPY api/              ./api/
COPY lambda_handler.py .

CMD ["lambda_handler.handler"]
