"""
Text preprocessing for topic analysis:
  - Basic cleaning and normalisation
  - spaCy-based data cleansing (lemmatise, remove stops/punct/nums/custom words)
  - Gensim bigram creation + Dictionary/corpus
"""

import csv
import os
import re
from typing import Dict, List, Tuple

import nltk
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

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
_stop_words = set(stopwords.words("english"))

# ── Lazy spaCy singleton ──────────────────────────────────────────────────────
_nlp = None

def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        _nlp = spacy.load("en_core_web_md")
    return _nlp


# ── Basic cleaning ────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Lowercase, remove URLs/emails/punctuation, normalise whitespace."""
    text = text.lower()
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"\S+@\S+", "", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize_and_lemmatize(text: str) -> List[str]:
    tokens = word_tokenize(clean_text(text))
    return [
        _lemmatizer.lemmatize(t)
        for t in tokens
        if t not in _stop_words and len(t) > 2
    ]


def preprocess_batch(texts: List[str]) -> List[str]:
    """Return cleaned (not lemmatized) texts for transformer models."""
    return [clean_text(t) for t in texts]


def preprocess_batch_classical(texts: List[str]) -> List[str]:
    """Return lemmatized, stop-word-free strings for LDA/NMF."""
    return [" ".join(tokenize_and_lemmatize(t)) for t in texts]


# ── spaCy data cleansing ──────────────────────────────────────────────────────

def clean_texts_spacy(
    texts: List[str],
    extra_stopwords: List[str] | None = None,
) -> List[List[str]]:
    """
    Per-document spaCy cleansing: lemmatise each token, remove stop words,
    punctuation, numbers, and any caller-supplied extra stop words.

    Args:
        texts:            raw documents
        extra_stopwords:  additional words to exclude (e.g. ['I', 'said'])

    Returns:
        cleaned_texts: list of token lists, one per document
    """
    nlp = _get_nlp()
    extra = set(w.lower() for w in (extra_stopwords or []))

    cleaned_texts: List[List[str]] = []
    for text in texts:
        doc = nlp(text)
        tokens = [
            word.lemma_.lower()
            for word in doc
            if not word.is_stop
            and not word.is_punct
            and not word.like_num
            and word.text.lower() not in extra
            and len(word.lemma_.strip()) > 1
        ]
        cleaned_texts.append(tokens)
    return cleaned_texts


# ── POS tagging ───────────────────────────────────────────────────────────────

def get_pos_tags(texts: List[str]) -> List[List[Tuple[str, str, str]]]:
    """
    Run spaCy POS tagging on a list of documents.

    Returns:
        List of token lists per document. Each token is (text, pos_, tag_).
        Whitespace-only tokens are excluded.
    """
    nlp = _get_nlp()
    results: List[List[Tuple[str, str, str]]] = []
    for text in texts:
        doc = nlp(text)
        results.append([
            (token.text, token.pos_, token.tag_)
            for token in doc
            if not token.is_space
        ])
    return results


# ── NER tagging ───────────────────────────────────────────────────────────────

def get_ner_tags(texts: List[str]) -> List[List[Tuple[int, int, str, str]]]:
    """
    Run spaCy NER on a list of documents.

    Returns:
        List of entity lists per document.
        Each entity is (start_char, end_char, entity_text, label_).
    """
    nlp = _get_nlp()
    results: List[List[Tuple[int, int, str, str]]] = []
    for text in texts:
        doc = nlp(text)
        results.append([
            (ent.start_char, ent.end_char, ent.text, ent.label_)
            for ent in doc.ents
        ])
    return results


# ── Dependency parsing ────────────────────────────────────────────────────────

def get_dep_parse(texts: List[str]) -> Dict:
    """
    Run spaCy dependency parsing on a list of documents.

    Returns dict with three parallel lists (one entry per document):
        noun_chunks  – list of (chunk_text, root_text, dep_, head_text)
        token_deps   – list of (token_text, dep_, head_text, head_pos_, [children])
        svgs         – displaCy arc-diagram SVG strings
    """
    import random
    from spacy import displacy

    nlp = _get_nlp()
    options = {
        "distance": 120,
        "compact":  True,
        "color":    "#000000",   # arc label colour
        "bg":       "#ffffff",   # SVG background
        "font":     "Source Sans Pro",
    }

    noun_chunks_all: List = []
    token_deps_all:  List = []
    svgs:            List[str] = []

    for text in texts:
        doc = nlp(text)

        # Noun chunks: (chunk, root, dependency relation, head)
        noun_chunks_all.append([
            (chunk.text, chunk.root.text, chunk.root.dep_, chunk.root.head.text)
            for chunk in doc.noun_chunks
        ])

        # Token-level deps: (token, dep, head_text, head_pos, children)
        token_deps_all.append([
            (token.text, token.dep_, token.head.text,
             token.head.pos_, [str(c) for c in token.children])
            for token in doc
            if token.dep_ and not token.is_space
        ])

        # displaCy SVG with a unique ID to avoid browser rendering conflicts
        svg = displacy.render(doc, style="dep", jupyter=False, options=options)
        uid = f"displacy-{random.randint(0, 999999)}"
        svg = svg.replace('id="displacy"', f'id="{uid}"')
        svg = svg.replace('id="displacy-svg"', f'id="{uid}"')

        # Step 1: rewrite every fill/stroke to black (arcs, arrows, boxes).
        # White (#ffffff) is preserved for the background rect.
        import re as _re
        svg = _re.sub(
            r'(fill|stroke)="(?!#ffffff|#FFFFFF|none|transparent)([^"]*)"',
            lambda m: f'{m.group(1)}="#000000"',
            svg,
        )
        svg = _re.sub(
            r'(fill|stroke)\s*:\s*(?!#ffffff|#FFFFFF|none|transparent)([^;}"]*)',
            lambda m: f'{m.group(1)}: #000000',
            svg,
        )

        # Step 2: override text elements to navy blue + bold via <style>.
        # CSS rules override SVG presentation attributes, so this wins over Step 1.
        _text_style = (
            "<style>"
            "text, .displacy-word, .displacy-tag {"
            "  fill: #000080 !important;"
            "  font-weight: bold !important;"
            "}"
            "</style>"
        )
        svg = svg.replace("</svg>", _text_style + "</svg>")
        svgs.append(svg)

    return {"noun_chunks": noun_chunks_all, "token_deps": token_deps_all, "svgs": svgs}


# ── Gensim bigram creation ────────────────────────────────────────────────────

def create_bigrams(
    cleaned_texts: List[List[str]],
    min_count: int = 2,
    threshold: float = 10.0,
) -> Tuple[List[List[str]], object, List[List[Tuple[int, int]]]]:
    """
    Build gensim bigram model, apply it to cleaned_texts, then create
    a Dictionary and bag-of-words corpus.

    Args:
        cleaned_texts:  output of clean_texts_spacy()
        min_count:      minimum frequency for a bigram to be kept
        threshold:      higher → fewer bigrams

    Returns:
        (bc_texts, dictionary, corpus)
        - bc_texts:    token lists with bigrams inserted  (e.g. ['wait_time', ...])
        - dictionary:  gensim Dictionary
        - corpus:      list of bag-of-words [(word_id, count), ...]
    """
    import gensim
    from gensim.corpora import Dictionary

    bigram_model = gensim.models.phrases.Phrases(
        cleaned_texts,
        min_count=min_count,
        threshold=threshold,
    )
    bc_texts = [bigram_model[line] for line in cleaned_texts]

    dictionary = Dictionary(bc_texts)
    corpus = [dictionary.doc2bow(text) for text in bc_texts]

    return bc_texts, dictionary, corpus


# ── Combined pipeline ─────────────────────────────────────────────────────────

def full_preprocess(
    texts: List[str],
    extra_stopwords: List[str] | None = None,
) -> Dict:
    """
    Run the full preprocessing pipeline and return all intermediate results.

    Returns dict with keys:
        cleaned_texts   - spaCy token lists (one per doc)
        bc_texts        - token lists with bigrams
        dictionary      - gensim Dictionary
        corpus          - bag-of-words corpus
        sample_tokens   - first doc tokens (for display)
        sample_bigrams  - first doc bigram tokens (for display)
        sample_bow      - first doc BOW (for display)
    """
    cleaned_texts = clean_texts_spacy(texts, extra_stopwords)
    bc_texts, dictionary, corpus = create_bigrams(cleaned_texts)

    return {
        "cleaned_texts": cleaned_texts,
        "bc_texts":      bc_texts,
        "dictionary":    dictionary,
        "corpus":        corpus,
        "sample_tokens": cleaned_texts[0] if cleaned_texts else [],
        "sample_bigrams": bc_texts[0] if bc_texts else [],
        "sample_bow":    corpus[0] if corpus else [],
    }


# ── File I/O ──────────────────────────────────────────────────────────────────

def parse_input(raw: str) -> List[str]:
    """Split raw textarea input into individual documents (one per line)."""
    return [line.strip() for line in raw.splitlines() if line.strip()]


def read_file_path(path: str) -> List[str]:
    """Read .txt or .csv file and return list of documents."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    if ext == ".csv":
        docs = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                line = " ".join(row).strip()
                if line:
                    docs.append(line)
        return docs
    return []
