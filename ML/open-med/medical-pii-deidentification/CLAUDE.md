# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run Gradio web UI (http://localhost:7860)
python -m ui.app

# Run FastAPI server (http://localhost:8000, docs at /docs)
uvicorn api.main:app

# Run tests (fast, no model needed)
pytest tests/ -v

# Run slow tests that require model download
pytest tests/ -v -m slow

# Run a single test file
pytest tests/test_detector.py -v
```

## Architecture

The pipeline flows: `src/` (core library) → `api/` (FastAPI REST layer) → `ui/` (Gradio frontend).

**`src/` — core library**
- `entities.py`: Defines `EntityType` enum (21 HIPAA identifiers), `MODEL_LABEL_MAPPING` (model BIO labels → `EntityType`), and `HIPAA_ENTITIES` dict with replacement text per type.
- `pii_detector.py`: `PIIDetector` wraps a HuggingFace `token-classification` pipeline. Model is lazy-loaded on first `detect()` call. Uses a module-level singleton (`get_detector()`) for reuse in serverless environments. `aggregation_strategy="simple"` merges BIO tokens; overlapping same-type entities are merged in `_merge_overlapping()`.
- `deidentify.py`: `Deidentifier` takes a `PIIDetector` and a `ReplacementStrategy` (`PLACEHOLDER`, `CONSISTENT`, `REDACT`, `HASH`, `CUSTOM`). Replaces entities right-to-left by position to preserve offsets. `CONSISTENT` strategy maintains a per-session `_consistent_mapping` so the same entity text always maps to the same fake value.

**`api/` — REST API**
- `main.py`: FastAPI app with CORS middleware; pre-loads the model on startup (controlled by `PRELOAD_MODEL` env var).
- `routes.py`: Four endpoints under `/api/v1/`: `POST /detect`, `POST /deidentify`, `POST /batch`, `GET /health`, `GET /entities`. Uses a module-level `PIIDetector` singleton via FastAPI `Depends`.
- `schemas.py`: Pydantic v2 request/response models.

**`ui/app.py`**: Gradio interface wrapping `Deidentifier`.

## Environment Variables

Copy `.env.example` to `.env`. Key variables:
- `PII_MODEL`: HuggingFace model ID (default: `OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1`)
- `PRELOAD_MODEL`: Pre-load model at API startup (`true`/`false`)
- `PORT`: API port (default `8000`)
- `GRADIO_PORT`: UI port (default `7860`)

## Model

Default model is `OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1` (44M params, ~500 MB RAM). Any HuggingFace NER model can be substituted via `PII_MODEL`. The model label mapping in `src/entities.py:MODEL_LABEL_MAPPING` must cover the labels the chosen model emits.

## Tests

Tests marked `@pytest.mark.slow` download the model from HuggingFace (~500 MB) and require network access. Non-slow tests cover serialization and edge cases without loading the model.
