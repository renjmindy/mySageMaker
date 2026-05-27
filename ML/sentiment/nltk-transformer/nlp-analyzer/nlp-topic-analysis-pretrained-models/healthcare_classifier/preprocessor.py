"""
Text preprocessing pipeline following the notebook:
  healthcare-med-distilroberta-lda-topicanapipeline.ipynb — cells 20-22.

Pipeline:
  1. Expand contractions  (e.g. "don't" → "do not")
  2. Lowercase
  3. Remove URLs, @mentions, #hashtags, special characters
  4. Tokenize
  5. Lemmatize
  6. Remove English stop-words (NLTK)

Matches the notebook's `TextPreprocessor` sklearn transformer exactly.
"""

from __future__ import annotations

import os
import re
from typing import List, Union

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.base import BaseEstimator, TransformerMixin

# ── NLTK data bootstrap ────────────────────────────────────────────────────────
NLTK_DIR = os.environ.get("NLTK_DATA", os.path.join(os.getcwd(), "nltk_data"))
os.makedirs(NLTK_DIR, exist_ok=True)
if NLTK_DIR not in nltk.data.path:
    nltk.data.path.insert(0, NLTK_DIR)

for _pkg in ["punkt", "punkt_tab", "wordnet", "stopwords", "averaged_perceptron_tagger"]:
    try:
        nltk.download(_pkg, download_dir=NLTK_DIR, quiet=True)
    except Exception:
        pass

_lemmatizer = WordNetLemmatizer()
_stop_words_en = set(stopwords.words("english"))


class TextPreprocessor(BaseEstimator, TransformerMixin):
    """
    Scikit-learn-compatible text preprocessor mirroring the notebook pipeline.
    Handles str, list[str], and pd.Series inputs.
    """

    # ── contraction expansion ──────────────────────────────────────────────
    def expand_contractions(self, text: str) -> str:
        try:
            import contractions as _c
            return _c.fix(text)
        except ImportError:
            # Fallback: common contractions only
            pairs = [
                ("won't", "will not"), ("can't", "cannot"), ("n't", " not"),
                ("'re", " are"), ("'s", " is"), ("'d", " would"),
                ("'ll", " will"), ("'ve", " have"), ("'m", " am"),
            ]
            for contraction, expansion in pairs:
                text = text.replace(contraction, expansion)
            return text

    def preprocess_text(self, text: str) -> str:
        if not isinstance(text, str) or not text.strip():
            return ""
        text = self.expand_contractions(text)
        text = text.lower()
        # Remove URLs and www links
        text = re.sub(r"http\S+|www\S+", "", text)
        # Remove @mentions and #hashtags
        text = re.sub(r"@\w+|#\w+", "", text)
        # Space-pad then remove punctuation/special characters
        text = re.sub(r"([^\w\s])", r" \1 ", text)
        text = re.sub(r"[^\w\s]", "", text)
        # Tokenize, lemmatize, remove stopwords
        tokens = word_tokenize(text)
        clean_tokens = [
            _lemmatizer.lemmatize(word)
            for word in tokens
            if word not in _stop_words_en and word.isalpha() and len(word) > 1
        ]
        return " ".join(clean_tokens)

    def fit(self, X, y=None):  # noqa: N803
        return self

    def transform(self, X, y=None) -> Union[str, List[str]]:  # noqa: N803
        # pandas is optional — only available in the full Gradio/FastAPI env
        try:
            import pandas as pd
            if isinstance(X, pd.Series):
                return X.apply(self.preprocess_text)
        except ImportError:
            pass
        if isinstance(X, str):
            return self.preprocess_text(X)
        if isinstance(X, list):
            return [self.preprocess_text(t) for t in X]
        # numpy array / anything else
        return [self.preprocess_text(str(t)) for t in X]
