---
title: NLP Topic Analysis Apr 2026
emoji: 📊
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: "6.13.0"
app_file: ui/app.py
pinned: false
license: mit
---

# NLP Topic Analysis v0.0 (April 2026)

Automatic topic discovery from a batch of documents using pretrained Transformer models and classical NLP methods.

## Models

| Model | Approach | Topics |
|---|---|---|
| **BERTopic (MiniLM)** | Sentence embeddings + UMAP + HDBSCAN | Auto |
| **BERTopic (MPNet)** | Sentence embeddings + UMAP + HDBSCAN | Auto |
| **LSI** | SVD on TF-IDF (gensim) | Slider |
| **HDP** | Hierarchical Dirichlet Process | Auto |
| **LDA** | Latent Dirichlet Allocation | Slider |
| **NMF** | Non-negative Matrix Factorization | Slider |

## Features

- Per-document NER highlighting, POS tagging, bigram detection, dependency parsing
- Interactive pyLDAvis topic maps (LDA, HDP, NMF)
- BERTopic built-in visualizations: intertopic distance, barchart, heatmap, hierarchy, document embedding map
