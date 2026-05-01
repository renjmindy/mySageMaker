# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NLP Topic Analysis v0.0 — automatic topic discovery from a batch of documents. Supports six models: BERTopic (MiniLM / MPNet), LSI, HDP, LDA, and NMF. Deployed as a Hugging Face Space (Gradio) and optionally as a FastAPI REST service or AWS Lambda.

## Running the App

```bash
# Activate the virtual environment first
source .venv/bin/activate

# Run the Gradio UI locally (http://localhost:7861)
python ui/app.py

# Run the FastAPI REST API (http://localhost:8001, docs at /docs)
python -m api.main

# Run a quick programmatic example
python examples/basic_usage.py
```

Environment variable overrides:
- `GRADIO_PORT` — port for the Gradio server (default `7861`)
- `NLTK_DATA` — path where NLTK downloads are stored (default `./nltk_data/`)

## Installing Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# spaCy model is installed via the whl URL already in requirements.txt
```

NLTK data packages (`punkt`, `punkt_tab`, `wordnet`, `stopwords`, `averaged_perceptron_tagger`) are downloaded automatically on first import of `src/preprocessor.py`.

## Architecture

The codebase has three layers:

**`src/` — core library**
- `models.py` — `ModelType` enum, `SUPPORTED_MODELS` registry, `TopicInfo` / `DocumentResult` / `TopicResult` dataclasses. All model configuration lives here.
- `preprocessor.py` — two preprocessing paths: (1) `preprocess_batch` (basic cleaning for BERTopic) and (2) `full_preprocess` (spaCy lemmatisation → gensim bigrams → Dictionary + corpus, for classical models). Also exposes `get_pos_tags`, `get_ner_tags`, `get_dep_parse` (all using lazy-loaded `en_core_web_md`).
- `topic_modeler.py` — inference logic for all six model types. `run_topic_model_with_viz` is the main entry point; it returns a `TopicResult` and an HTML string for visualizations. Models are not cached between calls.
- `visualizer.py` — generates HTML output: BERTopic uses Plotly charts (intertopic distance via PCA fallback for small datasets, barchart, heatmap, hierarchy, document map); LDA/HDP use pyLDAvis; NMF uses a custom pyLDAvis normalization. All Plotly figures are base64-encoded into iframes to bypass Gradio's script-tag sanitizer.

**`ui/app.py` — Gradio frontend**
Single-file UI. `run_analysis()` wires together all `src/` calls and returns five outputs: summary HTML, two Plotly figures, document table HTML, and visualization HTML. The document table combines NER highlights, POS badges, bigram pills, and displaCy arc diagrams per row. Deployed as a Hugging Face Space (`app_file: ui/app.py` in `README.md` YAML front matter).

**`api/` — FastAPI REST API**
- `POST /api/v1/topics` — accepts `TopicRequest` (texts, model_type, n_topics), returns `TopicResponse`
- `GET /api/v1/health`
- `lambda_handler.py` at the repo root wraps the FastAPI app with Mangum for AWS Lambda deployment.

## Key Design Notes

- **BERTopic requires ≥ 3 documents.** UMAP parameters are clamped to `[2, n-1]` for small datasets; `init="random"` avoids the spectral decomposition that fails when `n` is small.
- **Topic count:** BERTopic and HDP determine topic count automatically; the `n_topics` slider only affects LSI, LDA, and NMF.
- **Gensim models share one preprocessing path:** `full_preprocess` runs spaCy → bigrams → gensim corpus. LSI, HDP, and LDA all receive the same dictionary and corpus from this pipeline.
- **NMF pyLDAvis:** requires manual normalization of `components_` and `doc_topic_matrix` into probability distributions before calling `pyLDAvis.prepare`.
- **displaCy SVG post-processing:** arc colors are rewritten to black and text is overridden to navy bold via injected `<style>` to ensure readability in the dark-background UI.
- **NLTK data directory** is placed in `./nltk_data/` (gitignored) and added to `nltk.data.path` at import time so the downloaded packages are found without modifying the system NLTK path.
