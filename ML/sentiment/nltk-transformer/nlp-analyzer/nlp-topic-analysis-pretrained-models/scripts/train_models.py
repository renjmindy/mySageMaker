#!/usr/bin/env python3
"""
Train all classical healthcare topic models and save them to MODEL_DIR.

Run once at Docker build time:
    python scripts/train_models.py

This script follows the notebook pipeline (cells 41-51, 76-78):
  • LDA   — TextPreprocessor → CountVectorizer → LatentDirichletAllocation
  • NMF   — TextPreprocessor → TfidfVectorizer  → NMF
  • LSI   — NLTK lemmatize   → Dictionary/corpus  → LsiModel
  • HDP   — NLTK lemmatize   → Dictionary/corpus  → HdpModel

Topic-alignment: after each unsupervised model discovers N_TOPICS topics,
we greedily match each model-topic to the closest predefined PREM topic by
Jaccard overlap of the top keywords.

Outputs (saved to MODEL_DIR, default /app/models):
  • lda_pipeline.joblib   — {"pipeline": Pipeline, "alignment": dict}
  • nmf_pipeline.joblib   — {"pipeline": Pipeline, "alignment": dict}
  • lsi_data.joblib       — {"model": LsiModel, "dictionary": Dictionary, "alignment": dict}
  • hdp_data.joblib       — {"model": HdpModel, "dictionary": Dictionary,
                             "n_topics": int, "alignment": dict}
"""

import os
import sys
import time

# Ensure project root is on the path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import joblib
import numpy as np

from healthcare_classifier.topics import (
    TOPIC_KEYWORDS, N_TOPICS,
    get_seed_texts, get_seed_labels,
)
from healthcare_classifier.preprocessor import TextPreprocessor

MODEL_DIR = os.environ.get("MODEL_DIR", "/app/models")
os.makedirs(MODEL_DIR, exist_ok=True)

print(f"MODEL_DIR = {MODEL_DIR}")

# ── Shared seed corpus ────────────────────────────────────────────────────────
seed_texts  = get_seed_texts()   # 225 strings
seed_labels = get_seed_labels()  # 225 ints (0-14)

print(f"Seed corpus: {len(seed_texts)} documents, {N_TOPICS} topics")

preprocessor = TextPreprocessor()


# ── Topic alignment helper (also used by classical.py at load time) ───────────
def _kw_overlap(model_words, topic_idx):
    model_set   = set(w.lower() for w in model_words)
    defined_set = set(w.lower() for w in TOPIC_KEYWORDS[topic_idx])
    if not model_set or not defined_set:
        return 0.0
    inter = model_set & defined_set
    return len(inter) / len(model_set | defined_set)


def build_alignment(model_topic_words: dict) -> dict:
    """Greedy assignment: model_topic_idx → predefined_topic_idx."""
    n_model = len(model_topic_words)
    scores  = np.zeros((n_model, N_TOPICS))
    for m_idx, words in model_topic_words.items():
        for p_idx in range(N_TOPICS):
            scores[m_idx, p_idx] = _kw_overlap(words, p_idx)

    alignment: dict = {}
    used: set = set()
    for m_idx in sorted(range(n_model), key=lambda i: scores[i].max(), reverse=True):
        remaining = [p for p in range(N_TOPICS) if p not in used]
        if not remaining:
            remaining = list(range(N_TOPICS))
        best_p = max(remaining, key=lambda p: scores[m_idx, p])
        alignment[m_idx] = best_p
        used.add(best_p)
    return alignment


# ═══════════════════════════════════════════════════════════════════════════════
# 1. LDA (sklearn) — notebook cells 49-51
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[1/4] Training LDA (sklearn) ...")
t0 = time.time()

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation

lda_pipeline = Pipeline([
    ("preprocessor", TextPreprocessor()),
    ("vectorizer",   CountVectorizer(min_df=1, max_df=0.95, max_features=5000,
                                     stop_words="english")),
    ("lda",          LatentDirichletAllocation(
                         n_components=N_TOPICS,
                         max_iter=50,
                         learning_method="batch",
                         random_state=42,
                         doc_topic_prior=0.1,
                         topic_word_prior=0.01,
                     )),
])
lda_pipeline.fit(seed_texts)

# Extract top words per model topic for alignment
lda_model    = lda_pipeline.named_steps["lda"]
vectorizer   = lda_pipeline.named_steps["vectorizer"]
feature_names = vectorizer.get_feature_names_out()

model_topic_words = {}
for tid, component in enumerate(lda_model.components_):
    top_idx = component.argsort()[-20:][::-1]
    model_topic_words[tid] = [feature_names[i] for i in top_idx]

lda_alignment = build_alignment(model_topic_words)
joblib.dump({"pipeline": lda_pipeline, "alignment": lda_alignment},
            os.path.join(MODEL_DIR, "lda_pipeline.joblib"))
print(f"   ✅ LDA saved  ({time.time()-t0:.1f}s)")
for m_idx, p_idx in sorted(lda_alignment.items()):
    from healthcare_classifier.topics import TOPIC_NAMES
    print(f"      model-topic-{m_idx:02d} → {p_idx:2d}: {TOPIC_NAMES[p_idx]}")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. NMF (sklearn with TF-IDF)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[2/4] Training NMF (sklearn) ...")
t0 = time.time()

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF

nmf_pipeline = Pipeline([
    ("preprocessor", TextPreprocessor()),
    ("vectorizer",   TfidfVectorizer(min_df=1, max_df=0.95, max_features=5000,
                                     stop_words="english")),
    ("nmf",          NMF(n_components=N_TOPICS, random_state=42, max_iter=400)),
])
nmf_pipeline.fit(seed_texts)

nmf_model     = nmf_pipeline.named_steps["nmf"]
tfidf_vec     = nmf_pipeline.named_steps["vectorizer"]
tfidf_features = tfidf_vec.get_feature_names_out()

nmf_topic_words = {}
for tid, component in enumerate(nmf_model.components_):
    top_idx = component.argsort()[-20:][::-1]
    nmf_topic_words[tid] = [tfidf_features[i] for i in top_idx]

nmf_alignment = build_alignment(nmf_topic_words)
joblib.dump({"pipeline": nmf_pipeline, "alignment": nmf_alignment},
            os.path.join(MODEL_DIR, "nmf_pipeline.joblib"))
print(f"   ✅ NMF saved  ({time.time()-t0:.1f}s)")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. LSI (gensim)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[3/4] Training LSI (gensim) ...")
t0 = time.time()

from gensim.corpora import Dictionary
from gensim.models import LsiModel

# Tokenize using same TextPreprocessor → split
cleaned_texts = preprocessor.transform(seed_texts)
tokenized     = [t.split() for t in cleaned_texts]

lsi_dictionary = Dictionary(tokenized)
lsi_corpus     = [lsi_dictionary.doc2bow(tok) for tok in tokenized]

lsi_model = LsiModel(lsi_corpus, id2word=lsi_dictionary, num_topics=N_TOPICS)

lsi_topic_words = {}
for tid in range(N_TOPICS):
    raw = lsi_model.show_topic(tid, topn=20)
    lsi_topic_words[tid] = [w for w, _ in raw]

lsi_alignment = build_alignment(lsi_topic_words)
joblib.dump({
    "model":      lsi_model,
    "dictionary": lsi_dictionary,
    "alignment":  lsi_alignment,
}, os.path.join(MODEL_DIR, "lsi_data.joblib"))
print(f"   ✅ LSI saved  ({time.time()-t0:.1f}s)")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. HDP (gensim)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[4/4] Training HDP (gensim) ...")
t0 = time.time()

from gensim.models import HdpModel

hdp_dictionary = lsi_dictionary  # reuse same dictionary
hdp_corpus     = lsi_corpus      # reuse same corpus

hdp_model = HdpModel(hdp_corpus, id2word=hdp_dictionary)

# Get active topics (HDP is non-parametric — variable count)
raw_topics = hdp_model.show_topics(num_topics=50, num_words=20, formatted=False)
hdp_topic_words = {tid: [w for w, _ in words] for tid, words in raw_topics}
n_hdp_topics    = len(hdp_topic_words)
print(f"   HDP found {n_hdp_topics} active topics")

hdp_alignment = build_alignment(hdp_topic_words)
joblib.dump({
    "model":      hdp_model,
    "dictionary": hdp_dictionary,
    "n_topics":   n_hdp_topics,
    "alignment":  hdp_alignment,
}, os.path.join(MODEL_DIR, "hdp_data.joblib"))
print(f"   ✅ HDP saved  ({time.time()-t0:.1f}s)")


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 60)
print("All classical models trained and saved successfully.")
saved = [f for f in os.listdir(MODEL_DIR) if f.endswith(".joblib")]
for f in sorted(saved):
    size_mb = os.path.getsize(os.path.join(MODEL_DIR, f)) / 1e6
    print(f"  {f:40s}  {size_mb:.1f} MB")
print("═" * 60)
