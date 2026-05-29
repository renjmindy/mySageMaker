---
title: OpenMedRedacted Patient Report Measures NLP Sentiments
emoji: 🏥
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 6.13.0
app_file: app.py
pinned: false
license: mit
short_description: HIPAA-aware sentiment analysis, PHI redacted first
---

# OpenMedRedacted Patient Report Measures NLP Sentiments

HIPAA-aware sentiment analysis for patient report measures. Automatically redacts Protected Health Information (PHI) via the OpenMed PII De-identification API before running multi-model Transformer inference — so clinical feedback is analyzed without exposing names, dates, MRNs, or other HIPAA identifiers. Supports 7 pretrained models (DistilBERT, RoBERTa, GoEmotions, BART zero-shot, and more) with full NLP preprocessing, word-level sentiment distribution, NER, POS tagging, and downloadable PDF reports.
