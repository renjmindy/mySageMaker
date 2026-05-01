"""
Topic modeling inference: BERTopic, LSI, HDP, LDA, NMF.
Models are lazy-loaded and cached on first use.
"""

from typing import Dict, List, Tuple

from .models import ModelType, SUPPORTED_MODELS, TopicInfo, DocumentResult, TopicResult
from .preprocessor import preprocess_batch, preprocess_batch_classical, full_preprocess

# ── Model caches ──────────────────────────────────────────────────────────────
_bertopic_models: Dict[str, object] = {}   # key → BERTopic instance
_vectorizer_cache: Dict[str, object] = {}  # key → (vectorizer, model)


# ── BERTopic ──────────────────────────────────────────────────────────────────

def _run_bertopic(texts: List[str], model_type: str) -> Tuple[TopicResult, Dict]:
    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer
    from umap import UMAP

    cfg = SUPPORTED_MODELS[model_type]
    embedding_model_id = cfg["embedding_model"]

    cleaned = preprocess_batch_classical(texts)   # lowercase + no punctuation + no stop words
    n = len(cleaned)

    if n < 3:
        raise ValueError("BERTopic requires at least 3 documents.")

    # UMAP constraints for small datasets:
    #   n_neighbors  must be in [2, n-1]
    #   n_components must be < n
    #   init="random" skips spectral eigsh decomposition (which requires n_components+1 < n)
    umap_model = UMAP(
        n_neighbors=max(2, min(n - 1, 15)),
        n_components=max(2, min(n - 1, 5)),
        min_dist=0.0,
        metric="cosine",
        init="random",
        random_state=42,
    )

    embedding_model = SentenceTransformer(embedding_model_id)
    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        language="english",
        calculate_probabilities=True,
        verbose=False,
        min_topic_size=2,
    )
    topics, probs = topic_model.fit_transform(cleaned)

    topic_info_df = topic_model.get_topic_info()
    topic_infos: List[TopicInfo] = []
    for _, row in topic_info_df.iterrows():
        tid = row["Topic"]
        if tid == -1:
            continue
        words_scores = topic_model.get_topic(tid) or []
        keywords = [w for w, _ in words_scores[:10]]
        scores   = [s for _, s in words_scores[:10]]
        topic_infos.append(TopicInfo(
            topic_id=tid,
            keywords=keywords,
            scores=scores,
            doc_count=int(row["Count"]),
        ))

    doc_results: List[DocumentResult] = []
    for i, (text, tid) in enumerate(zip(texts, topics)):
        prob = float(probs[i][tid]) if tid != -1 and probs is not None else 0.0
        kws = []
        if tid != -1:
            words_scores = topic_model.get_topic(tid) or []
            kws = [w for w, _ in words_scores[:5]]
        doc_results.append(DocumentResult(
            doc_id=i, text=text, topic_id=int(tid),
            topic_keywords=kws, probability=prob,
        ))

    outliers = sum(1 for t in topics if t == -1)
    result = TopicResult(
        model_type=model_type,
        num_topics=len(topic_infos),
        topics=topic_infos,
        documents=doc_results,
        outlier_count=outliers,
    )
    viz_data = {"type": "bertopic", "model": topic_model, "docs": list(texts)}
    return result, viz_data


# ── NMF (scikit-learn / TF-IDF) ──────────────────────────────────────────────

def _run_sklearn(texts: List[str], model_type: str, n_topics: int = 5) -> Tuple[TopicResult, Dict]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import NMF

    prep = full_preprocess(texts)
    cleaned  = [" ".join(tokens) for tokens in prep["bc_texts"]]
    n_topics = min(n_topics, len(texts))

    vectorizer = TfidfVectorizer(max_df=0.95, min_df=1, max_features=1000)
    dtm        = vectorizer.fit_transform(cleaned)
    model      = NMF(n_components=n_topics, random_state=42, max_iter=400)

    doc_topic_matrix = model.fit_transform(dtm)
    feature_names    = vectorizer.get_feature_names_out()

    topic_infos: List[TopicInfo] = []
    for tid, component in enumerate(model.components_):
        top_idx  = component.argsort()[-10:][::-1]
        keywords = [feature_names[i] for i in top_idx]
        scores   = [float(component[i]) for i in top_idx]
        doc_count = int((doc_topic_matrix.argmax(axis=1) == tid).sum())
        topic_infos.append(TopicInfo(topic_id=tid, keywords=keywords,
                                     scores=scores, doc_count=doc_count))

    doc_results: List[DocumentResult] = []
    for i, (text, row) in enumerate(zip(texts, doc_topic_matrix)):
        tid  = int(row.argmax())
        prob = float(row[tid] / row.sum()) if row.sum() > 0 else 0.0
        doc_results.append(DocumentResult(
            doc_id=i, text=text, topic_id=tid,
            topic_keywords=topic_infos[tid].keywords[:5], probability=prob,
        ))

    result = TopicResult(model_type=model_type, num_topics=n_topics,
                         topics=topic_infos, documents=doc_results, outlier_count=0)
    viz_data = {
        "type": "nmf", "model": model, "dtm": dtm,
        "vectorizer": vectorizer, "doc_topic_matrix": doc_topic_matrix,
    }
    return result, viz_data


# ── Gensim (LSI / HDP / LDA) ─────────────────────────────────────────────────

def _run_gensim(texts: List[str], model_type: str, n_topics: int = 5) -> Tuple[TopicResult, Dict]:
    from gensim.models import LsiModel, LdaModel, HdpModel

    prep       = full_preprocess(texts)
    dictionary = prep["dictionary"]
    corpus     = prep["corpus"]
    n_topics   = min(n_topics, len(texts))

    if model_type == ModelType.LSI:
        model = LsiModel(corpus, id2word=dictionary, num_topics=n_topics)

        topic_infos: List[TopicInfo] = []
        for tid in range(n_topics):
            word_scores = model.show_topic(tid, topn=10)
            keywords = [w for w, _ in word_scores]
            scores   = [abs(float(s)) for _, s in word_scores]
            topic_infos.append(TopicInfo(topic_id=tid, keywords=keywords, scores=scores, doc_count=0))

        doc_results: List[DocumentResult] = []
        for i, (text, bow) in enumerate(zip(texts, corpus)):
            vec = model[bow]
            if not vec:
                tid, prob = 0, 0.0
            else:
                tid, prob = max(vec, key=lambda x: abs(x[1]))
                tid, prob = int(tid), abs(float(prob))
            topic_infos[tid].doc_count += 1
            doc_results.append(DocumentResult(
                doc_id=i, text=text, topic_id=tid,
                topic_keywords=topic_infos[tid].keywords[:5], probability=prob,
            ))

        result = TopicResult(model_type=model_type, num_topics=n_topics,
                             topics=topic_infos, documents=doc_results, outlier_count=0)
        viz_data = {"type": "lsi"}
        return result, viz_data

    elif model_type == ModelType.HDP:
        model = HdpModel(corpus, id2word=dictionary)
        raw_topics = model.show_topics(num_topics=50, num_words=10, formatted=False)

        topic_map: Dict[int, TopicInfo] = {}
        for tid, word_scores in raw_topics:
            keywords = [w for w, _ in word_scores]
            scores   = [float(s) for _, s in word_scores]
            topic_map[int(tid)] = TopicInfo(topic_id=int(tid), keywords=keywords,
                                            scores=scores, doc_count=0)

        doc_results = []
        for i, (text, bow) in enumerate(zip(texts, corpus)):
            vec = sorted(model[bow], key=lambda x: x[1], reverse=True)
            if not vec:
                tid, prob = 0, 0.0
            else:
                tid, prob = int(vec[0][0]), float(vec[0][1])
            ti = topic_map.get(tid)
            if ti:
                ti.doc_count += 1
            doc_results.append(DocumentResult(
                doc_id=i, text=text, topic_id=tid,
                topic_keywords=ti.keywords[:5] if ti else [], probability=prob,
            ))

        active = sorted([t for t in topic_map.values() if t.doc_count > 0],
                        key=lambda t: t.topic_id)
        result = TopicResult(model_type=model_type, num_topics=len(active),
                             topics=active, documents=doc_results, outlier_count=0)
        viz_data = {"type": "hdp", "model": model, "corpus": corpus, "dictionary": dictionary}
        return result, viz_data

    else:  # LDA via gensim
        model = LdaModel(corpus, id2word=dictionary, num_topics=n_topics,
                         random_state=42, passes=10, alpha="auto")

        topic_infos = []
        for tid in range(n_topics):
            word_scores = model.show_topic(tid, topn=10)
            keywords = [w for w, _ in word_scores]
            scores   = [float(s) for _, s in word_scores]
            topic_infos.append(TopicInfo(topic_id=tid, keywords=keywords, scores=scores, doc_count=0))

        doc_results = []
        for i, (text, bow) in enumerate(zip(texts, corpus)):
            topic_probs = model.get_document_topics(bow, minimum_probability=0.0)
            if not topic_probs:
                tid, prob = 0, 0.0
            else:
                tid, prob = max(topic_probs, key=lambda x: x[1])
                tid, prob = int(tid), float(prob)
            topic_infos[tid].doc_count += 1
            doc_results.append(DocumentResult(
                doc_id=i, text=text, topic_id=tid,
                topic_keywords=topic_infos[tid].keywords[:5], probability=prob,
            ))

        result = TopicResult(model_type=model_type, num_topics=n_topics,
                             topics=topic_infos, documents=doc_results, outlier_count=0)
        viz_data = {"type": "lda", "model": model, "corpus": corpus, "dictionary": dictionary}
        return result, viz_data


# ── Public API ────────────────────────────────────────────────────────────────

def run_topic_model(
    texts: List[str],
    model_type: str = ModelType.BERTOPIC_MINI,
    n_topics: int = 5,
) -> TopicResult:
    cfg = SUPPORTED_MODELS[model_type]
    if cfg["type"] == "bertopic":
        result, _ = _run_bertopic(texts, model_type)
    elif cfg["type"] == "gensim":
        result, _ = _run_gensim(texts, model_type, n_topics)
    else:
        result, _ = _run_sklearn(texts, model_type, n_topics)
    return result


def run_topic_model_with_viz(
    texts: List[str],
    model_type: str = ModelType.BERTOPIC_MINI,
    n_topics: int = 5,
) -> Tuple[TopicResult, str]:
    """Run topic modeling and generate visualization HTML. Returns (TopicResult, viz_html)."""
    from .visualizer import generate_viz_html

    cfg = SUPPORTED_MODELS[model_type]
    if cfg["type"] == "bertopic":
        result, viz_data = _run_bertopic(texts, model_type)
    elif cfg["type"] == "gensim":
        result, viz_data = _run_gensim(texts, model_type, n_topics)
    else:
        result, viz_data = _run_sklearn(texts, model_type, n_topics)

    viz_html = generate_viz_html(viz_data)
    return result, viz_html
