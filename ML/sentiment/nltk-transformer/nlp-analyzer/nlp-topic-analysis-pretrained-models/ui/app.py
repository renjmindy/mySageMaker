"""
Gradio web interface for NLP Topic Analysis.
"""

import os, sys, html as _html
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import gradio as gr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import ModelType, SUPPORTED_MODELS, MODEL_LABEL_TO_TYPE
from src.preprocessor import parse_input, read_file_path, full_preprocess, get_pos_tags, get_ner_tags, get_dep_parse
from src.topic_modeler import run_topic_model_with_viz

# ── Colour palette per topic ───────────────────────────────────────────────────
_TOPIC_COLORS = [
    "#2563eb", "#16a34a", "#dc2626", "#d97706", "#7c3aed",
    "#0891b2", "#be185d", "#65a30d", "#ea580c", "#6366f1",
    "#0d9488", "#b45309", "#9333ea", "#15803d", "#b91c1c",
    "#1d4ed8", "#047857", "#c2410c", "#7e22ce", "#0369a1",
]

def _topic_color(tid: int) -> str:
    if tid == -1:
        return "#9ca3af"
    return _TOPIC_COLORS[tid % len(_TOPIC_COLORS)]


# ── POS tag colours & badge renderer ──────────────────────────────────────────

_POS_COLORS = {
    "NOUN":  "#2563eb",   # blue
    "PROPN": "#0891b2",   # cyan
    "VERB":  "#16a34a",   # green
    "AUX":   "#65a30d",   # lime
    "ADJ":   "#d97706",   # amber
    "ADV":   "#7c3aed",   # purple
    "PRON":  "#be185d",   # pink
    "NUM":   "#ea580c",   # orange
    "PUNCT": "#6b7280",   # grey
    "DET":   "#6b7280",
    "ADP":   "#6b7280",
    "CCONJ": "#6b7280",
    "SCONJ": "#6b7280",
    "PART":  "#6b7280",
    "INTJ":  "#9333ea",
    "SYM":   "#6b7280",
    "X":     "#6b7280",
}

def _pos_badge(token: str, pos: str, tag: str) -> str:
    color = _POS_COLORS.get(pos, "#6b7280")
    return (
        f'<span title="{tag}" style="display:inline-block;margin:2px 3px;'
        f'padding:4px 8px 3px 8px;background:{color}22;border:1px solid {color};'
        f'border-radius:6px;text-align:center;min-width:36px;">'
        f'<span style="display:block;color:#e2e8f0;font-size:0.82rem;">{token}</span>'
        f'<span style="display:block;color:{color};font-size:0.68rem;'
        f'font-weight:700;letter-spacing:0.04em;">{pos}</span>'
        f'</span>'
    )


# ── NER colours & inline highlighter ─────────────────────────────────────────

_NER_COLORS = {
    "PERSON":       "#dc2626",   # red
    "ORG":          "#2563eb",   # blue
    "GPE":          "#16a34a",   # green  (countries, cities)
    "LOC":          "#0891b2",   # cyan   (mountains, rivers)
    "DATE":         "#d97706",   # amber
    "TIME":         "#d97706",   # amber
    "MONEY":        "#7c3aed",   # purple
    "PRODUCT":      "#0891b2",   # cyan
    "EVENT":        "#be185d",   # pink
    "FAC":          "#65a30d",   # lime   (buildings, airports)
    "NORP":         "#ea580c",   # orange (nationalities, groups)
    "WORK_OF_ART":  "#9333ea",   # violet
    "LAW":          "#0369a1",   # dark blue
    "LANGUAGE":     "#047857",   # dark green
    "PERCENT":      "#6b7280",
    "QUANTITY":     "#6b7280",
    "CARDINAL":     "#6b7280",
    "ORDINAL":      "#6b7280",
}

def _ner_html(text: str, entities: list) -> str:
    """Render text with NER entity spans highlighted inline."""
    if not entities:
        return _html.escape(text)
    parts = []
    prev = 0
    for start, end, ent_text, label in sorted(entities, key=lambda x: x[0]):
        parts.append(_html.escape(text[prev:start]))
        color = _NER_COLORS.get(label, "#6b7280")
        parts.append(
            f'<mark style="background:{color}28;border-bottom:2px solid {color};'
            f'border-radius:3px;padding:1px 4px;color:#e2e8f0;font-style:normal;">'
            f'{_html.escape(ent_text)}'
            f'<span style="font-size:0.67rem;font-weight:700;color:{color};'
            f'vertical-align:super;margin-left:3px;">{label}</span>'
            f'</mark>'
        )
        prev = end
    parts.append(_html.escape(text[prev:]))
    return "".join(parts)


# ── Charts ─────────────────────────────────────────────────────────────────────

def _keywords_chart(topics) -> go.Figure:
    """Horizontal bar chart of top keywords per topic."""
    if not topics:
        return go.Figure()

    fig = go.Figure()
    for t in topics:
        color = _topic_color(t.topic_id)
        fig.add_trace(go.Bar(
            name=f"Topic {t.topic_id}",
            y=t.keywords[:8][::-1],
            x=t.scores[:8][::-1],
            orientation="h",
            marker_color=color,
            text=[f"{s:.3f}" for s in t.scores[:8][::-1]],
            textposition="outside",
            textfont=dict(color="black", size=11),
        ))

    fig.update_layout(
        barmode="group",
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Arial", size=12, color="black"),
        legend=dict(font=dict(color="black", size=11)),
        xaxis=dict(title="Score", color="black",
                   tickfont=dict(color="black"), gridcolor="#e5e7eb"),
        yaxis=dict(color="black", tickfont=dict(color="black")),
        margin=dict(l=10, r=20, t=30, b=10),
        height=max(450, len(topics) * 90 + 150),
    )
    return fig


def _distribution_chart(topics) -> go.Figure:
    """Vertical bar: document count per topic."""
    if not topics:
        return go.Figure()

    ids     = [f"Topic {t.topic_id}" for t in topics]
    counts  = [t.doc_count for t in topics]
    colors  = [_topic_color(t.topic_id) for t in topics]

    fig = go.Figure(go.Bar(
        x=ids, y=counts, marker_color=colors,
        text=counts, textposition="outside",
        textfont=dict(color="black", size=12, family="Arial Black"),
    ))
    fig.update_layout(
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Arial", size=12, color="black"),
        xaxis=dict(color="black", tickfont=dict(color="black")),
        yaxis=dict(
            color="black", tickfont=dict(color="black"),
            gridcolor="#e5e7eb",
            range=[0, max(counts) + max(counts) * 0.15 + 1],
        ),
        margin=dict(l=10, r=10, t=30, b=10),
        height=525,
    )
    return fig


_DEP_COLORS = {
    "nsubj": "#2563eb", "nsubjpass": "#1d4ed8",
    "dobj":  "#16a34a", "iobj":      "#15803d",
    "ROOT":  "#dc2626",
    "attr":  "#d97706", "acomp":     "#b45309",
    "amod":  "#7c3aed", "advmod":    "#6d28d9",
    "prep":  "#0891b2", "pobj":      "#0e7490",
    "aux":   "#65a30d", "auxpass":   "#4d7c0f",
    "compound": "#ea580c", "poss":   "#c2410c",
    "det":   "#6b7280", "punct":     "#6b7280",
    "cc":    "#6b7280", "conj":      "#9333ea",
    "relcl": "#be185d", "acl":       "#9d174d",
    "mark":  "#6b7280", "xcomp":     "#0369a1",
    "ccomp": "#0369a1", "advcl":     "#0d9488",
}

def _dep_section_html(noun_chunks: list, token_deps: list, svg: str) -> str:
    """Render noun chunks, token dep table, and displaCy arc diagram."""

    # ── Noun chunk pills ─────────────────────────────────────────────────────
    chunk_pills = ""
    for chunk_text, root_text, dep_, head_text in noun_chunks:
        color = _DEP_COLORS.get(dep_, "#6b7280")
        chunk_pills += (
            f'<span style="display:inline-block;margin:3px 4px;padding:4px 10px;'
            f'background:{color}22;border:1px solid {color};border-radius:8px;'
            f'font-size:0.8rem;color:#e2e8f0;" '
            f'title="root: {root_text} | dep: {dep_} | head: {head_text}">'
            f'<b style="color:#fff;">{_html.escape(chunk_text)}</b>'
            f'<span style="color:{color};font-size:0.7rem;font-weight:700;'
            f'margin-left:6px;">↳ {dep_} → {_html.escape(head_text)}</span>'
            f'</span>'
        )
    if not chunk_pills:
        chunk_pills = "<span style='color:#6b7280;font-size:0.8rem;font-style:italic;'>No noun chunks found.</span>"

    # ── Token dep badges ─────────────────────────────────────────────────────
    _DEP_EXCLUDE = {
        "punct", "det", "appos", "nummod", "cc", "neg", "npadvmod",
        "dative", "prt", "mark", "agent", "quantmod", "pcomp",
        "expl", "case", "intj",
    }
    dep_badges = ""
    for tok_text, dep_, head_text, head_pos, children in token_deps:
        if dep_.lower() in _DEP_EXCLUDE:
            continue
        color = _DEP_COLORS.get(dep_, "#6b7280")
        child_str = f" [{', '.join(children)}]" if children else ""
        dep_badges += (
            f'<span title="dep: {dep_} | head: {head_text} ({head_pos}){child_str}" '
            f'style="display:inline-block;margin:2px 3px;padding:3px 8px 2px 8px;'
            f'background:{color}22;border:1px solid {color};border-radius:6px;'
            f'text-align:center;min-width:36px;">'
            f'<span style="display:block;color:#e2e8f0;font-size:0.8rem;">{_html.escape(tok_text)}</span>'
            f'<span style="display:block;color:{color};font-size:0.67rem;'
            f'font-weight:700;letter-spacing:0.03em;">{dep_}</span>'
            f'</span>'
        )

    # ── displaCy SVG ─────────────────────────────────────────────────────────
    wrapped_svg = (
        f'<div style="background:#ffffff;border-radius:8px;padding:16px 20px;'
        f'overflow-x:auto;margin-top:10px;border:1px solid #334155;">'
        f'{svg}</div>'
    )

    return f"""
<div style="border-top:1px solid #1e293b;margin-top:10px;padding-top:10px;">
  <div style="font-size:0.75rem;font-weight:700;color:#94a3b8;
              letter-spacing:0.06em;margin-bottom:6px;">NOUN CHUNKS</div>
  <div style="line-height:2.4;margin-bottom:10px;">{chunk_pills}</div>

  <div style="font-size:0.75rem;font-weight:700;color:#94a3b8;
              letter-spacing:0.06em;margin-bottom:6px;">DEPENDENCY TAGS</div>
  <div style="line-height:2.6;margin-bottom:6px;">{dep_badges}</div>

  <div style="font-size:0.75rem;font-weight:700;color:#94a3b8;
              letter-spacing:0.06em;margin-bottom:4px;">ARC DIAGRAM</div>
  {wrapped_svg}
</div>"""


def _doc_table_html(documents, pos_data: list = None, ner_data: list = None,
                    dep_data: dict = None, bigram_data: list = None) -> str:
    """HTML table of document → topic assignments with NER highlights, POS, bigrams, and deps."""
    rows = ""
    for d in documents:
        color  = _topic_color(d.topic_id)
        label  = f"Topic {d.topic_id}" if d.topic_id != -1 else "Outlier"
        kws    = ", ".join(d.topic_keywords[:5]) if d.topic_keywords else "—"
        prob   = f"{d.probability:.1%}" if d.probability else "—"

        # NER: highlight entity spans inline in the original text
        ents = ner_data[d.doc_id] if ner_data and d.doc_id < len(ner_data) else []
        doc_text_html = _ner_html(d.text, ents)

        # POS: coloured badges beneath the text
        pos_row = ""
        if pos_data and d.doc_id < len(pos_data):
            badges = "".join(
                _pos_badge(tok, pos, tag)
                for tok, pos, tag in pos_data[d.doc_id]
                if pos not in ("PUNCT", "ADP", "DET", "CCONJ", "PART", "X")
            )
            pos_row = (
                f'<div style="border-top:1px solid #1e293b;margin-top:8px;padding-top:6px;">'
                f'<div style="font-size:0.75rem;font-weight:700;color:#94a3b8;'
                f'letter-spacing:0.06em;margin-bottom:4px;">POS TAGS</div>'
                f'<div style="line-height:2.6;">{badges}</div></div>'
            )

        bigram_row = ""
        if bigram_data and d.doc_id < len(bigram_data):
            tokens = bigram_data[d.doc_id]
            badges = "".join(
                _pill(t, "#16a34a" if "_" in t else "#2563eb") for t in tokens
            ) or "<i style='color:#9ca3af'>—</i>"
            bigram_count = sum(1 for t in tokens if "_" in t)
            bigram_row = (
                f'<div style="border-top:1px solid #1e293b;margin-top:8px;padding-top:6px;">'
                f'<div style="font-size:0.75rem;font-weight:700;color:#94a3b8;'
                f'letter-spacing:0.06em;margin-bottom:4px;">'
                f'BIGRAMS '
                f'<span style="font-weight:400;color:#6b7280;">'
                f'({len(tokens)} tokens · {bigram_count} bigrams detected'
                f'<span style="color:#16a34a;"> ■</span> green'
                f')</span></div>'
                f'<div style="line-height:2.6;">{badges}</div></div>'
            )

        dep_row = ""
        if dep_data and d.doc_id < len(dep_data["svgs"]):
            dep_row = _dep_section_html(
                dep_data["noun_chunks"][d.doc_id],
                dep_data["token_deps"][d.doc_id],
                dep_data["svgs"][d.doc_id],
            )

        rows += f"""
        <tr style="background:#0f172a;border-bottom:1px solid #334155;">
          <td style="padding:8px 10px;color:#ffffff;white-space:nowrap;vertical-align:top;">{d.doc_id + 1}</td>
          <td style="padding:8px 10px;color:#ffffff;word-break:break-word;white-space:normal;vertical-align:top;line-height:1.8;">
            <div style="margin-bottom:4px;font-size:0.75rem;font-weight:700;color:#94a3b8;letter-spacing:0.06em;">DOCUMENT</div>
            <div style="line-height:1.8;">{doc_text_html}</div>{pos_row}{bigram_row}{dep_row}
          </td>
          <td style="padding:8px 10px;white-space:nowrap;vertical-align:top;">
            <span style="background:{color};color:#fff;border-radius:12px;
                         padding:2px 10px;font-size:0.82rem;">{label}</span>
          </td>
          <td style="padding:8px 10px;color:#ffffff;font-size:0.85rem;word-break:break-word;vertical-align:top;">{kws}</td>
          <td style="padding:8px 10px;color:#ffffff;white-space:nowrap;vertical-align:top;">{prob}</td>
        </tr>"""

    return f"""
<div style="overflow-x:auto;">
<table style="width:100%;border-collapse:collapse;font-family:Arial,sans-serif;font-size:0.9rem;background:#0f172a;border-radius:8px;overflow:hidden;">
  <thead>
    <tr style="background:#1e293b;border-bottom:2px solid #334155;">
      <th style="padding:10px 10px;text-align:left;color:#ffffff;white-space:nowrap;">#</th>
      <th style="padding:10px 10px;text-align:left;color:#ffffff;">Document, NER · POS · Bigrams · Dependency</th>
      <th style="padding:10px 10px;text-align:left;color:#ffffff;white-space:nowrap;">Topic</th>
      <th style="padding:10px 10px;text-align:left;color:#ffffff;">Keywords</th>
      <th style="padding:10px 10px;text-align:left;color:#ffffff;white-space:nowrap;">Confidence</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
</div>"""


def _summary_html(result) -> str:
    cfg = SUPPORTED_MODELS[result.model_type]
    cards = ""
    for t in result.topics:
        color = _topic_color(t.topic_id)
        kws   = " · ".join(t.keywords[:6])
        cards += f"""
        <div style="border:2px solid {color};border-radius:10px;padding:12px 16px;
                    background:{color}12;margin:6px;">
          <div style="font-weight:700;color:{color};font-size:1rem;">
            Topic {t.topic_id} &nbsp;
            <span style="font-size:0.8rem;color:#6b7280;font-weight:400;">
              {t.doc_count} docs
            </span>
          </div>
          <div style="color:#ffffff;font-size:0.88rem;margin-top:4px;">{kws}</div>
        </div>"""

    outlier_note = (
        f'<p style="color:#9ca3af;font-size:0.85rem;margin-top:8px;">'
        f'⚠ {result.outlier_count} document(s) could not be assigned to a topic (outliers).</p>'
        if result.outlier_count else ""
    )

    return f"""
<div>
  <p style="color:#ffffff;font-size:0.9rem;margin-bottom:8px;">
    <b>{cfg['display']}</b> &nbsp;·&nbsp; {result.num_topics} topics discovered
    &nbsp;·&nbsp; {len(result.documents)} documents
  </p>
  <div style="display:flex;flex-wrap:wrap;">{cards}</div>
  {outlier_note}
</div>"""


# ── Preprocessing display ─────────────────────────────────────────────────────

def _pill(word: str, color: str = "#2563eb") -> str:
    return (
        f'<span style="display:inline-block;margin:3px 4px;padding:3px 10px;'
        f'background:{color};color:#fff;border-radius:20px;font-size:0.82rem;">'
        f'{word}</span>'
    )


def _preprocess_html(prep: dict) -> str:
    """Render data cleansing + bigram results as HTML."""
    tokens  = prep["sample_tokens"]
    bigrams = prep["sample_bigrams"]
    bow     = prep["sample_bow"]
    d       = prep["dictionary"]

    bow_items = ", ".join(
        f"<b style='color:#fff'>{d[wid]}</b>"
        f"<span style='color:#94a3b8'>:{cnt}</span>"
        for wid, cnt in bow[:20]
    )

    return f"""
<div style="background:#0f172a;border-radius:10px;padding:16px;font-family:Arial,sans-serif;">

  <div>
    <span style="background:#7c3aed;color:#fff;border-radius:20px;padding:3px 14px;
                 font-size:0.85rem;font-weight:600;display:inline-block;margin-bottom:8px;">
      Bag-of-Words Corpus &nbsp;<span style="font-weight:400;font-size:0.78rem;">
      (Dictionary · doc2bow · first 20 terms)</span>
    </span>
    <p style="color:#94a3b8;font-size:0.8rem;margin:0 0 6px 0;">
      Vocabulary size: {len(d)} unique terms &nbsp;|&nbsp; {len(prep['corpus'])} documents
    </p>
    <p style="color:#e2e8f0;font-size:0.83rem;line-height:1.8;">{bow_items}</p>
  </div>

</div>"""


# ── Main analysis function ─────────────────────────────────────────────────────

def run_analysis(text_input, file_obj, model_label, n_topics):
    empty = ("", None, None, "", "")

    def _err(msg):
        return (f"<p style='color:red'>{msg}</p>",) + empty[1:]

    # Resolve input
    docs = []
    if file_obj is not None:
        path = file_obj if isinstance(file_obj, str) else getattr(file_obj, "path", getattr(file_obj, "name", None))
        if path:
            docs = read_file_path(path)
    if not docs and text_input:
        docs = parse_input(text_input)

    if not docs:
        return _err("Please paste documents (one per line) or upload a file.")
    if len(docs) < 2:
        return _err("Please provide at least 2 documents.")
    if len(docs) > 1000:
        return _err("Maximum 1000 documents per request.")

    model_type = MODEL_LABEL_TO_TYPE.get(model_label, ModelType.BERTOPIC_MINI)

    try:
        prep           = full_preprocess(docs)
        pos_data       = get_pos_tags(docs)
        ner_data       = get_ner_tags(docs)
        dep_data       = get_dep_parse(docs)
        result, viz_html = run_topic_model_with_viz(docs, model_type, int(n_topics))
        summary        = _summary_html(result)
        kw_chart       = _keywords_chart(result.topics)
        dist_chart     = _distribution_chart(result.topics)
        doc_table      = _doc_table_html(result.documents, pos_data, ner_data, dep_data,
                                          bigram_data=prep["bc_texts"])
        return summary, kw_chart, dist_chart, doc_table, viz_html

    except Exception as exc:
        import traceback
        return _err(f"Analysis failed: {exc}<br><pre>{traceback.format_exc()}</pre>")


# ── Sample texts ───────────────────────────────────────────────────────────────

_SAMPLES = {
    "Patient Feedback (Healthcare)": """\
The wait time was over two hours and nobody explained the delay.
Dr Smith was very thorough and took time to explain my diagnosis clearly.
The reception staff were rude and unhelpful when I called to reschedule.
My medication was changed without any explanation and I had side effects.
The nurses were incredibly kind and made me feel comfortable during my stay.
The hospital parking is expensive and there are never enough spaces.
I was not informed about the procedure risks beforehand.
The follow-up appointment was easy to book and the doctor remembered my case.
Billing department sent me an incorrect invoice and took weeks to fix it.
The specialist explained everything patiently and answered all my questions.""",

    "Product Reviews (E-commerce)": """\
The battery life on this phone is terrible, barely lasts half a day.
Delivery was fast and the packaging was secure, product arrived in perfect condition.
The customer service team resolved my issue within minutes, very impressed.
This laptop runs hot and the fan is constantly loud during basic tasks.
Great value for money, works exactly as described in the listing.
The return process was a nightmare, took three weeks to get my refund.
Screen quality is stunning, colours are vivid and viewing angles are excellent.
The size chart was completely wrong, had to return two sizes before finding the right one.
Setup was straightforward and the instructions were clear and easy to follow.
Build quality feels cheap, plastic creaks and buttons feel loose.""",
}

SAMPLE_NAMES = list(_SAMPLES.keys())

# ── Gradio layout ──────────────────────────────────────────────────────────────

_CSS = """
/* ── Full-width layout ───────────────────────────────────────────────────── */
.gradio-container,
.gradio-container > .main,
.gradio-container > .main > .wrap,
.gradio-container .prose  { max-width: 100% !important; width: 100% !important; }
.gradio-container          { padding-left: 24px !important; padding-right: 24px !important; }

/* ── Block panel padding & font scale (≈1.5×) ────────────────────────────── */
.block { padding: 24px 28px !important; width: 100% !important; box-sizing: border-box !important; }

/* Labels */
label > span, .label-wrap span { font-size: 1.1rem !important; font-weight: 600 !important; }

/* Dropdown & select controls */
.wrap, .svelte-1occ011 { font-size: 1.1rem !important; min-height: 54px !important; }
.dropdown-arrow { width: 20px !important; height: 20px !important; }

/* Slider */
input[type=range] { height: 10px !important; }
.range-slider { padding: 12px 0 !important; }

/* Textbox */
textarea { font-size: 1.05rem !important; line-height: 1.7 !important; padding: 14px !important; }

/* File upload drop zone */
.upload-container { min-height: 240px !important; font-size: 1.1rem !important; }
.upload-container .icon-wrap svg { width: 52px !important; height: 52px !important; }

/* Run button */
button.primary { font-size: 1.15rem !important; padding: 16px 28px !important; min-height: 58px !important; }

/* ── Bar chart panels — white background on container divs only ──────────── */
.js-plotly-plot,
.js-plotly-plot .plotly,
.js-plotly-plot .svg-container  { background: #ffffff !important; }
"""

with gr.Blocks(title="NLP Topic Analysis v0.0 (April 2026)", fill_width=True, css=_CSS) as demo:

    gr.HTML("""
<div style="padding:18px 4px 10px 4px;">
  <h1 style="font-size:2.6rem;font-weight:800;margin:0 0 10px 0;line-height:1.2;">
    NLP Topic Analysis <span style="font-size:1.5rem;font-weight:500;color:#94a3b8;">v0.0 (April 2026)</span>
  </h1>
  <p style="font-size:1.15rem;margin:0 0 8px 0;line-height:1.6;">
    Automatic topic discovery from a batch of documents using pretrained Transformer models
    (BERTopic) or classical methods (LDA, NMF).
  </p>
  <p style="font-size:1.05rem;margin:0;color:#94a3b8;">
    <strong>Input:</strong> one document per line, or upload a <code>.txt</code> / <code>.csv</code> file
    &nbsp;|&nbsp; <strong>Min:</strong> 2 docs &nbsp;|&nbsp; <strong>Max:</strong> 1000 docs
  </p>
</div>
""")

    with gr.Row():
        with gr.Column(scale=2):
            model_dropdown = gr.Dropdown(
                choices=list(MODEL_LABEL_TO_TYPE.keys()),
                value=list(MODEL_LABEL_TO_TYPE.keys())[0],
                label="Model",
            )
            n_topics_slider = gr.Slider(
                minimum=2, maximum=20, value=5, step=1,
                label="Number of topics (LDA / NMF only — ignored for BERTopic)",
            )
            sample_dropdown = gr.Dropdown(
                choices=[""] + SAMPLE_NAMES,
                value="",
                label="Load sample",
            )
            file_upload = gr.File(
                label="Upload .txt or .csv",
                file_types=[".txt", ".csv"],
                height=240,
            )
            run_btn = gr.Button("Discover Topics", variant="primary")

        with gr.Column(scale=3):
            text_input = gr.Textbox(
                label="Documents (one per line)",
                lines=24,
                placeholder="Paste your documents here, one per line…",
            )

    # ── Outputs ────────────────────────────────────────────────────────────────
    summary_out = gr.HTML(label="Summary")

    with gr.Row():
        with gr.Column():
            gr.HTML('<span style="background:#2563eb;color:#fff;border-radius:20px;'
                    'padding:3px 14px;font-size:0.85rem;font-weight:600;'
                    'display:inline-block;margin:8px 0;">Topic Keywords</span>')
            kw_chart_out = gr.Plot(show_label=False)
        with gr.Column():
            gr.HTML('<span style="background:#2563eb;color:#fff;border-radius:20px;'
                    'padding:3px 14px;font-size:0.85rem;font-weight:600;'
                    'display:inline-block;margin:8px 0;">Topic Distribution</span>')
            dist_chart_out = gr.Plot(show_label=False)

    gr.HTML('<span style="background:#2563eb;color:#fff;border-radius:20px;'
            'padding:3px 14px;font-size:0.85rem;font-weight:600;'
            'display:inline-block;margin:8px 0;">Document → Topic Assignments</span>')
    doc_table_out = gr.HTML()

    gr.HTML('<hr style="border:none;border-top:1px solid #334155;margin:24px 0 16px 0;">'
            '<span style="background:#7c3aed;color:#fff;border-radius:20px;'
            'padding:3px 16px;font-size:0.9rem;font-weight:700;'
            'display:inline-block;margin-bottom:12px;">Topic Visualizations</span>')
    viz_out = gr.HTML()

    # ── Interactions ───────────────────────────────────────────────────────────
    sample_dropdown.change(
        fn=lambda name: _SAMPLES.get(name, ""),
        inputs=sample_dropdown,
        outputs=text_input,
    )

    run_btn.click(
        fn=run_analysis,
        inputs=[text_input, file_upload, model_dropdown, n_topics_slider],
        outputs=[summary_out, kw_chart_out, dist_chart_out, doc_table_out, viz_out],
    )

    # ── About tab info ─────────────────────────────────────────────────────────
    with gr.Accordion("About the models", open=False):
        gr.Markdown("""
| Model | Approach | Topic count | Best for |
|---|---|---|---|
| **BERTopic (MiniLM)** | Sentence embeddings + UMAP + HDBSCAN | Auto | Fast automatic topic discovery |
| **BERTopic (MPNet)** | Sentence embeddings + UMAP + HDBSCAN | Auto | Higher quality, slower |
| **LSI** | SVD on TF-IDF (gensim corpus) | Slider | Fast, deterministic, linear algebra |
| **HDP** | Hierarchical Dirichlet Process (gensim corpus) | Auto | Fully Bayesian, auto topic count |
| **LDA** | Latent Dirichlet Allocation (gensim corpus) | Slider | Interpretable probabilistic model |
| **NMF** | Non-negative Matrix Factorization (TF-IDF) | Slider | Short texts, sparse topics |

All three gensim models (LSI, HDP, LDA) run on the **same cleaned corpus**: spaCy lemmatisation → stop/punct/num removal → gensim bigrams → Dictionary + doc2bow.
**BERTopic** and **HDP** determine the number of topics automatically — the slider is ignored.
""")

_on_spaces = os.getenv("SPACE_ID") is not None

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0" if not _on_spaces else None,
        server_port=int(os.getenv("GRADIO_PORT", 7861)) if not _on_spaces else None,
    )
