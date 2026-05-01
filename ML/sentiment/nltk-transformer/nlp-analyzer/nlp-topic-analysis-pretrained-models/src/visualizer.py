"""
Topic visualization: BERTopic built-in charts and pyLDAvis interactive maps.
"""
import base64
from typing import Any, Dict, List


def _plotly_fig_to_html(fig) -> str:
    """Render a Plotly figure inside a base64 iframe to bypass Gradio's script-tag sanitiser."""
    try:
        import plotly.io as pio
        full_html = pio.to_html(
            fig, include_plotlyjs="cdn", full_html=True,
            config={"responsive": True, "displayModeBar": True},
        )
        encoded = base64.b64encode(full_html.encode("utf-8")).decode("ascii")
        return (
            f'<iframe src="data:text/html;base64,{encoded}" '
            f'width="100%" height="680px" style="border:none;border-radius:8px;" '
            f'frameborder="0"></iframe>'
        )
    except Exception as e:
        return f"<p style='color:#f59e0b;'>Could not render: {e}</p>"


def _wrap_viz_panel(title: str, content: str, color: str = "#7c3aed") -> str:
    return (
        f'<div style="margin-bottom:28px;">'
        f'<span style="background:{color};color:#fff;border-radius:20px;'
        f'padding:3px 16px;font-size:0.85rem;font-weight:600;'
        f'display:inline-block;margin-bottom:10px;">{title}</span>'
        f'<div style="background:#ffffff;border-radius:10px;padding:12px 16px;'
        f'overflow-x:auto;min-height:60px;">{content}</div>'
        f'</div>'
    )


def _pyldavis_iframe(html_str: str) -> str:
    encoded = base64.b64encode(html_str.encode("utf-8")).decode("ascii")
    return (
        f'<iframe src="data:text/html;base64,{encoded}" '
        f'width="100%" height="820px" style="border:none;border-radius:8px;" '
        f'frameborder="0"></iframe>'
    )


# ── BERTopic ──────────────────────────────────────────────────────────────────

def _bertopic_intertopic_pca(topic_model: Any):
    """Intertopic distance map using PCA — works for any number of topics ≥ 2."""
    import numpy as np
    import plotly.graph_objects as go
    from sklearn.decomposition import PCA

    all_topic_ids = sorted(t for t in topic_model.get_topics() if t != -1)
    n = len(all_topic_ids)
    if n < 2:
        raise ValueError(f"Need ≥ 2 topics for intertopic map, got {n}")

    embeddings = np.array(topic_model.topic_embeddings_)
    # topic_embeddings_ row 0 is the outlier topic (-1), actual topics start at index 1
    outlier_offset = getattr(topic_model, "_outliers", 1)
    emb = embeddings[outlier_offset: outlier_offset + n]

    coords = PCA(n_components=2, random_state=42).fit_transform(emb)

    sizes = [topic_model.get_topic_freq(t) for t in all_topic_ids]
    max_s = max(sizes) or 1
    marker_sz = [max(14, int(60 * s / max_s)) for s in sizes]
    labels = [
        f"Topic {t}: " + " | ".join(w for w, _ in (topic_model.get_topic(t) or [])[:4])
        for t in all_topic_ids
    ]

    fig = go.Figure(go.Scatter(
        x=coords[:, 0], y=coords[:, 1],
        mode="markers+text",
        text=[f"T{t}" for t in all_topic_ids],
        textposition="top center",
        hovertext=labels, hoverinfo="text",
        marker=dict(
            size=marker_sz,
            color=list(range(n)),
            colorscale="Plasma",
            showscale=False,
            line=dict(width=1, color="#333"),
        ),
    ))
    fig.update_layout(
        title="<b>Intertopic Distance Map</b> (PCA layout)",
        xaxis=dict(title="PC 1", zeroline=False),
        yaxis=dict(title="PC 2", zeroline=False),
        height=550,
        paper_bgcolor="white",
        plot_bgcolor="#f8f9fa",
    )
    return fig


def _bertopic_documents_large(topic_model: Any, docs: List[str], marker_size: int = 14):
    """visualize_documents with enlarged markers (default BERTopic size is 5)."""
    fig = topic_model.visualize_documents(docs)
    for trace in fig.data:
        if hasattr(trace, "marker") and trace.marker is not None:
            current = trace.marker.size
            if isinstance(current, (int, float)) and current <= 12:
                trace.marker.size = marker_size
    return fig


def bertopic_viz_html(topic_model: Any, docs: List[str]) -> str:
    all_topic_ids = [t for t in topic_model.get_topics() if t != -1]
    n_topics = len(all_topic_ids)

    sections = []

    # Intertopic Distance Map — use PCA fallback for small models
    try:
        if n_topics >= 3:
            fig = topic_model.visualize_topics()
        else:
            fig = _bertopic_intertopic_pca(topic_model)
        content = _plotly_fig_to_html(fig)
    except Exception as e:
        try:
            fig = _bertopic_intertopic_pca(topic_model)
            content = _plotly_fig_to_html(fig)
        except Exception as e2:
            content = f"<p style='color:#f59e0b;font-size:0.85rem;'>Skipped: {e2}</p>"
    sections.append(_wrap_viz_panel("Intertopic Distance Map", content))

    # Remaining 4 charts
    for title, fn in [
        ("Top Keywords per Topic",   lambda: topic_model.visualize_barchart()),
        ("Topic Similarity Heatmap", lambda: topic_model.visualize_heatmap()),
        ("Topic Hierarchy",          lambda: topic_model.visualize_hierarchy()),
        ("Document Embedding Map",   lambda: _bertopic_documents_large(topic_model, docs)),
    ]:
        try:
            fig = fn()
            content = _plotly_fig_to_html(fig)
        except Exception as e:
            content = f"<p style='color:#f59e0b;font-size:0.85rem;'>Skipped: {e}</p>"
        sections.append(_wrap_viz_panel(title, content))

    return "\n".join(sections)


# ── pyLDAvis (LDA / HDP via gensim) ──────────────────────────────────────────

def pyldavis_gensim_html(model: Any, corpus, dictionary) -> str:
    try:
        import pyLDAvis
        import pyLDAvis.gensim_models as gensim_vis
        vis = gensim_vis.prepare(model, corpus, dictionary,
                                 sort_topics=False, mds="pcoa")
        return _wrap_viz_panel(
            "Interactive Topic Map (pyLDAvis)",
            _pyldavis_iframe(pyLDAvis.prepared_data_to_html(vis)),
        )
    except Exception as e:
        return _wrap_viz_panel(
            "Interactive Topic Map (pyLDAvis)",
            f"<p style='color:#f59e0b;font-size:0.85rem;'>pyLDAvis skipped: {e}</p>",
        )


# ── pyLDAvis (NMF via sklearn) ────────────────────────────────────────────────

def pyldavis_sklearn_html(nmf_model: Any, dtm, vectorizer, doc_topic_matrix) -> str:
    try:
        import numpy as np
        import pyLDAvis

        # Normalise NMF outputs into probability distributions for pyLDAvis
        topic_term = nmf_model.components_
        row_sums = topic_term.sum(axis=1, keepdims=True)
        topic_term_dists = topic_term / np.where(row_sums == 0, 1, row_sums)

        dt_sums = doc_topic_matrix.sum(axis=1, keepdims=True)
        doc_topic_dists = doc_topic_matrix / np.where(dt_sums == 0, 1, dt_sums)

        doc_lengths = np.asarray(dtm.sum(axis=1)).ravel().astype(int).tolist()
        vocab = vectorizer.get_feature_names_out().tolist()
        term_frequency = np.asarray(dtm.sum(axis=0)).ravel().tolist()

        vis = pyLDAvis.prepare(
            topic_term_dists=topic_term_dists,
            doc_topic_dists=doc_topic_dists,
            doc_lengths=doc_lengths,
            vocab=vocab,
            term_frequency=term_frequency,
            mds="pcoa",
            sort_topics=False,
        )
        return _wrap_viz_panel(
            "Interactive Topic Map (pyLDAvis)",
            _pyldavis_iframe(pyLDAvis.prepared_data_to_html(vis)),
        )
    except Exception as e:
        return _wrap_viz_panel(
            "Interactive Topic Map (pyLDAvis)",
            f"<p style='color:#f59e0b;font-size:0.85rem;'>pyLDAvis skipped: {e}</p>",
        )


# ── Dispatcher ────────────────────────────────────────────────────────────────

def generate_viz_html(viz_data: Dict) -> str:
    """
    Dispatch to the right visualizer based on viz_data["type"].

    Expected viz_data keys by type:
      "bertopic" → model (BERTopic), docs (List[str])
      "lda"/"hdp" → model (gensim), corpus, dictionary
      "nmf"       → model (NMF), dtm, vectorizer
      "lsi"       → (no viz support)
    """
    t = viz_data.get("type", "")
    if t == "bertopic":
        return bertopic_viz_html(viz_data["model"], viz_data["docs"])
    if t in ("lda", "hdp"):
        return pyldavis_gensim_html(
            viz_data["model"], viz_data["corpus"], viz_data["dictionary"]
        )
    if t == "nmf":
        return pyldavis_sklearn_html(
            viz_data["model"], viz_data["dtm"],
            viz_data["vectorizer"], viz_data["doc_topic_matrix"],
        )
    if t == "lsi":
        return _wrap_viz_panel(
            "Topic Visualization",
            "<p style='color:#6b7280;font-size:0.85rem;'>"
            "LSI (Latent Semantic Indexing) is not compatible with pyLDAvis — "
            "it produces signed values that cannot be treated as probabilities.</p>",
        )
    return ""
