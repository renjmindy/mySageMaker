# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
# Create and activate a virtual environment (Python 3.11)
python -m venv .venv && source .venv/bin/activate

# Install dependencies (includes spaCy model wheel and CPU-only PyTorch)
pip install --upgrade pip && pip install -r requirements.txt

# Gradio UI — primary interface (http://localhost:7860)
python ui/app.py

# FastAPI REST API (http://localhost:8000, docs at /docs)
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

## Docker

```bash
docker build -t nlp-sentiment .
docker run -p 7860:7860 nlp-sentiment
```

The Dockerfile pre-downloads all three HF models and NLTK data so there are no first-request delays.

## Project structure

```
src/                    # Core library
  models.py             # ModelType enum, SUPPORTED_MODELS config, dataclasses
  preprocessor.py       # NLP preprocessing pipeline (spaCy + NLTK)
  analyzer.py           # Transformer inference, lazy pipeline cache
api/                    # FastAPI REST API
  main.py               # App + CORS middleware
  routes.py             # /api/v1/health and /api/v1/analyze endpoints
  schemas.py            # Pydantic request / response models
ui/                     # Gradio web interface
  app.py                # Two-tab UI: Analyze + About
examples/
  basic_usage.py        # Standalone script demonstrating the src/ API
sentiment_model.py      # Backward-compat shim (re-exports from src/)
```

## Architecture

The pipeline runs in this order for every request:

1. **`src/preprocessor.preprocess_text`** — spaCy cleans the text (stop words, punct, URLs), normalises, tokenises (NLTK), stems (Porter), lemmatises, extracts NER and POS tags.
2. **`src/analyzer.analyze_sentiment`** — lazy-loads the chosen HuggingFace pipeline on first call, runs inference on the joined lemmatised text.
3. **`src/analyzer.get_word_distribution`** — scores each individual lemma to build the per-word distribution chart.

### Models

| Key | HuggingFace model ID | Labels |
|-----|----------------------|--------|
| `default` | `distilbert-base-uncased-finetuned-sst-2-english` | POSITIVE / NEGATIVE |
| `roberta` | `cardiffnlp/twitter-roberta-base-sentiment` | LABEL_0→NEGATIVE, LABEL_1→NEUTRAL, LABEL_2→POSITIVE |
| `emotion` | `j-hartmann/emotion-english-distilroberta-base` | ANGER, DISGUST, FEAR, JOY, NEUTRAL, SADNESS, SURPRISE |

Pipelines are cached in `src/analyzer._pipelines` (a module-level dict) — loaded once, reused for all subsequent calls.

### Input constraints

- Minimum 4 words, maximum 300 words
- Accepted file uploads: `.txt` and `.csv`

### NLTK data

Bundled under `nltk_data/` (punkt, punkt_tab, wordnet, averaged_perceptron_tagger). `src/preprocessor.py` also calls `nltk.download()` as a no-op fallback. Data directory is read from the `NLTK_DATA` env var (defaults to `<cwd>/nltk_data`).
