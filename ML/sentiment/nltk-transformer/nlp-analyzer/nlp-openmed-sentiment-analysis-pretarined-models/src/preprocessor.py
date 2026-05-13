"""
Text preprocessing pipeline: cleaning, normalisation, tokenisation,
stemming, lemmatisation, NER, and POS tagging.
"""

import csv
import os
import re
from typing import List, Tuple

import nltk
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
import spacy
from spacy import displacy

# ── NLTK data directory ──────────────────────────────────────────────────────
NLTK_DIR = os.environ.get("NLTK_DATA", os.path.join(os.getcwd(), "nltk_data"))
os.makedirs(NLTK_DIR, exist_ok=True)
if NLTK_DIR not in nltk.data.path:
    nltk.data.path.insert(0, NLTK_DIR)

for _pkg in ["punkt", "punkt_tab", "wordnet", "averaged_perceptron_tagger"]:
    try:
        nltk.download(_pkg, download_dir=NLTK_DIR, quiet=True)
    except Exception:
        pass

# ── Lazy singletons ──────────────────────────────────────────────────────────
_nlp: spacy.Language | None = None
_stemmer = PorterStemmer()


def _get_nlp() -> spacy.Language:
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_md")
    return _nlp


# ── Public API ───────────────────────────────────────────────────────────────

def preprocess_text(text: str) -> Tuple[
    str, str, str,
    List[str], List[str], List[str],
    List[Tuple[str, str]], List[Tuple[str, str]],
]:
    """
    Full NLP preprocessing pipeline.

    Returns:
        cleaned_text, removed_text, normalized_text,
        tokenized_text, stemmed_tokens, lemmatized_tokens,
        ner, pos
    """
    nlp = _get_nlp()

    text = re.sub(r"\s+", " ", text).strip()
    doc = nlp(text)

    cleaned_text = " ".join([
        token.text for token in doc
        if not token.is_stop and not token.is_punct
        and not token.like_url and not token.like_email
    ])
    removed_text = " ".join([
        token.text for token in doc
        if token.is_stop or token.is_punct
        or token.like_url or token.like_email
    ])

    normalized_text = cleaned_text.lower()
    tokenized_text = word_tokenize(normalized_text)

    normalized_doc = nlp(" ".join(tokenized_text))
    pos = [(t.text, t.pos_) for t in normalized_doc if t.pos_ != "SPACE"]
    stemmed_tokens = [_stemmer.stem(w) for w in tokenized_text]
    lemmatized_tokens = [t.lemma_ for t in normalized_doc]
    ner = [(ent.text, ent.label_) for ent in doc.ents]

    return (
        cleaned_text, removed_text, normalized_text,
        tokenized_text, stemmed_tokens, lemmatized_tokens,
        ner, pos,
    )


_NER_COLORS = {
    # light gray-green → dark gray-green
    "CARDINAL":   "#556B2F",
    "MONEY":      "#556B2F",
    "ORDINAL":    "#556B2F",
    "PERCENT":    "#556B2F",
    "QUANTITY":   "#556B2F",
    # light teal → dark teal
    "DATE":       "#00695C",
    "TIME":       "#00695C",
    # light yellow → dark yellow
    "EVENT":      "#B8860B",
    # muted teal → teal
    "FAC":        "#20B2AA",
    # light orange → dark orange
    "GPE":        "#D2691E",
    # orange → dark orange
    "LOC":        "#CC5500",
    # light purple → dark purple
    "NORP":       "#6A0DAD",
    # cyan → royal blue
    "ORG":        "#4169E1",
    # light green → dark green
    "PRODUCT":    "#228B22",
    # light lavender → dark lavender
    "WORK_OF_ART": "#7B2FBE",
}


def get_ner_html(text: str) -> str:
    """Return spaCy displacy inline entity HTML for the given text."""
    nlp = _get_nlp()
    doc = nlp(text)
    if not doc.ents:
        return "<p style='color:#6b7280;font-style:italic;'>No named entities found.</p>"
    html = displacy.render(
        doc, style="ent", page=False, jupyter=False,
        options={"colors": _NER_COLORS},
    )
    return f'<div style="line-height:2.5;font-size:0.95rem;">{html}</div>'


def read_file_path(path: str) -> str | None:
    """Read a file on disk (.txt or .csv) and return its content as a string."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    if ext == ".csv":
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            return " ".join(" ".join(row) for row in reader)
    return None


def read_file(file) -> str | None:
    """Read a Flask-style uploaded file object (.txt or .csv)."""
    if file.filename.endswith(".txt"):
        return file.read().decode("utf-8")
    if file.filename.endswith(".csv"):
        reader = csv.reader(file.read().decode("utf-8").splitlines())
        return " ".join(" ".join(row) for row in reader)
    return None
