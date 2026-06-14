---
title: OpenMedRedacted Patient Report Measures NLP Sentiments
emoji: 🏥
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 6.13.0
app_file: app.py
pinned: false
license: mit
short_description: HIPAA-aware sentiment analysis, PHI redacted first
---

# OpenMedRedacted Patient Report Measures NLP Sentiments

HIPAA-aware sentiment analysis for patient report measures. Automatically redacts Protected Health Information (PHI) via the OpenMed PII De-identification API before running multi-model Transformer inference — so clinical feedback is analyzed without exposing names, dates, MRNs, or other HIPAA identifiers.

Supports **13 Transformer models**:

### Fine-tuned Healthcare Models (cjen1008)
| Key | Model | Labels |
|-----|-------|--------|
| `bert_hc_v2` | `cjen1008/bert-healthcare-sentiment_v2` | NEGATIVE / NEUTRAL / POSITIVE |
| `distilroberta_hc_v2` | `cjen1008/distilroberta-healthcare-sentiment_v2` | NEGATIVE / NEUTRAL / POSITIVE |
| `distilbert_hc_v2` | `cjen1008/distilbert-healthcare-sentiment_v2` | NEGATIVE / NEUTRAL / POSITIVE |
| `bert_hc` | `cjen1008/bert-healthcare-sentiment` | NEGATIVE / NEUTRAL / POSITIVE |
| `distilbert_hc` | `cjen1008/distilbert-healthcare-sentiment` | NEGATIVE / NEUTRAL / POSITIVE |
| `distilroberta_hc` | `cjen1008/distilroberta-healthcare-sentiment` | NEGATIVE / NEUTRAL / POSITIVE |

### Pretrained General-Purpose Models
| Key | Model | Labels |
|-----|-------|--------|
| `default` | `distilbert-base-uncased-finetuned-sst-2-english` | POSITIVE / NEGATIVE |
| `roberta` | `nlptown/bert-base-multilingual-uncased-sentiment` | 1–5 star rating |
| `emotion` | `j-hartmann/emotion-english-distilroberta-base` | 7-class emotion |
| `amazon` | `sohan-ai/sentiment-analysis-model-amazon-reviews` | POSITIVE / NEGATIVE |
| `twitter` | `cardiffnlp/twitter-roberta-base-sentiment-latest` | NEGATIVE / NEUTRAL / POSITIVE |
| `sst2` | `textattack/bert-base-uncased-SST-2` | POSITIVE / NEGATIVE |
| `zeroshot` | `facebook/bart-large-mnli` | Zero-shot Sentiment |

## Features

- **OpenMed PII Redaction** — strips names, phone numbers, emails, MRNs, dates before analysis
- **Full NLP pipeline** — cleaning · tokenisation · stemming · lemmatisation · NER · POS tagging
- **Word-level distribution** — each lemma scored individually; colour-coded word cloud
- **Time-Series & Forecast** — per-month sentiment trend charts across longitudinal patient notes
- **Downloadable reports** — PDF and TXT reports per analysis
- **REST API** — FastAPI backend with `/api/v1/analyze`, `/api/v1/warmup`, `/api/v1/health`
