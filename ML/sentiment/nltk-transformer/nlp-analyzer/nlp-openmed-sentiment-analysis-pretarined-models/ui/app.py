"""
Gradio web interface for NLP Sentiment Analysis.

Architecture:
  src/preprocessor.py  → NLP preprocessing pipeline
  src/analyzer.py      → Transformer model inference
  src/models.py        → type definitions & model config
  ui/app.py            → this Gradio UI
"""

import os
import sys
import tempfile

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from wordcloud import WordCloud
import plotly.graph_objects as go
import gradio as gr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import ModelType, SUPPORTED_MODELS, MODEL_LABEL_TO_TYPE, PreprocessResult
from src.preprocessor import preprocess_text, read_file_path, get_ner_html
from src.analyzer import analyze_sentiment, get_word_distribution
from src.openmed_pii_client import redact_pii

# ── Sample texts ──────────────────────────────────────────────────────────────
SAMPLES = {
    "Positive (Product Review)": (
        "This product is absolutely amazing. I love everything about it. "
        "The quality is outstanding and the customer service was fantastic. "
        "I would highly recommend this to everyone. Best purchase I have ever made!"
    ),
    "Negative (Movie Review)": (
        "This film was a complete waste of time and money. The plot made no sense, "
        "the acting was terrible, and the ending was deeply disappointing. "
        "I regret watching it and would not recommend it to anyone."
    ),
    "Mixed (Restaurant Review)": (
        "The food at this restaurant was delicious and the portions were generous. "
        "However, the service was extremely slow and the prices were too high for "
        "what you get. The ambiance was nice though, and I might give it another try."
    ),
    "Clinical Note (Emotion)": (
        "The patient reports feeling overwhelmed and anxious about the upcoming surgery. "
        "She expressed fear about the anesthesia and sadness about being away from her "
        "family. Despite this, she showed surprising resilience and determination to recover."
    ),
    "Neutral (News Excerpt)": (
        "The committee met on Tuesday to review the quarterly budget report. "
        "Members discussed several proposals related to infrastructure spending. "
        "A final decision is expected to be announced by the end of the fiscal year."
    ),
    "NER Demo (People / Orgs / Places)": (
        "Apple CEO Tim Cook announced in San Francisco on Monday that the company "
        "plans to invest $2 billion in the United States by 2026. The deal was "
        "co-signed by Microsoft president Satya Nadella and reviewed by the "
        "European Commission in Brussels. Goldman Sachs and JPMorgan will advise "
        "on the transaction, which is expected to close by Q3."
    ),
}

MODEL_CHOICES = list(MODEL_LABEL_TO_TYPE.keys())

SENTIMENT_COLORS = {
    "POSITIVE": "#27ae60",
    "NEGATIVE": "#e74c3c",
    "NEUTRAL":  "#f39c12",
    "ANGER":    "#e74c3c",
    "DISGUST":  "#e74c3c",
    "FEAR":     "#e74c3c",
    "SADNESS":  "#e74c3c",
    "JOY":      "#27ae60",
    "SURPRISE": "#27ae60",
    # Star-rating model (BERT Multilingual)
    "1 STAR":   "#8B0000",
    "2 STARS":  "#e74c3c",
    "3 STARS":  "#f39c12",
    "4 STARS":  "#27ae60",
    "5 STARS":  "#1B5E20",
}

EMOTION_EMOJI = {
    "ANGER":    "🤬",
    "DISGUST":  "🤢",
    "FEAR":     "😨",
    "JOY":      "😀",
    "NEUTRAL":  "😐",
    "SADNESS":  "😭",
    "SURPRISE": "😲",
}

# ── Sentiment colormap: dark-red → yellow → blue → dark-green ────────────────
_SENTIMENT_CMAP = LinearSegmentedColormap.from_list(
    "sentiment",
    [(0.00, "#8B0000"), (0.33, "#FFD700"), (0.67, "#1565C0"), (1.00, "#1B5E20")],
)

# Score in [0, 1] for each sentiment category (0 = most negative, 1 = most positive)
_CATEGORY_SCORE = {
    "negative": 0.00,
    "anger":    0.04,
    "disgust":  0.08,
    "fear":     0.12,
    "sadness":  0.18,
    "neutral":  0.50,
    "surprise": 0.65,
    "joy":      0.92,
    "positive": 1.00,
}

# ── Chart helpers ─────────────────────────────────────────────────────────────

def _prob_chart(probabilities, labels, display_labels=None):
    if display_labels is None:
        display_labels = labels
    colors = [SENTIMENT_COLORS.get(l, "#95a5a6") for l in labels]
    fig = go.Figure(go.Bar(
        x=probabilities,
        y=display_labels,
        orientation="h",
        marker_color=colors,
        text=[f"{p:.1%}" for p in probabilities],
        textposition="outside",
        textfont=dict(size=11, color="#000000", family="Arial Black, Arial, sans-serif"),
    ))
    fig.update_layout(
        title=dict(text="Prediction Confidence", font=dict(size=20, color="#000000", family="Arial Black, Arial, sans-serif")),
        xaxis=dict(
            title=dict(text="Confidence", standoff=12),
            range=[0, 1.25], tickformat=".0%",
        ),
        height=max(240, len(labels) * 58),
        margin=dict(l=20, r=60, t=55, b=50),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(size=13, color="#000000", family="Arial Black, Arial, sans-serif"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(0,0,0,0.12)")
    return fig


def _wordcloud_fig(text, word_dist=None):
    # Build word → score mapping from the distribution
    word_score: dict = {}
    if word_dist:
        for category, words in word_dist.word_lists.items():
            score = _CATEGORY_SCORE.get(category.lower(), 0.5)
            for word in words:
                word_score[word.lower()] = score

    def _color_func(word, font_size, position, orientation, random_state=None, **kwargs):
        score = word_score.get(word.lower(), 0.5)
        r, g, b, _ = _SENTIMENT_CMAP(score)
        return f"rgb({int(r * 255)}, {int(g * 255)}, {int(b * 255)})"

    wc_obj = WordCloud(
        width=900, height=360, background_color="white",
        color_func=_color_func, max_words=100,
    ).generate(text)

    fig, (ax_wc, ax_cb) = plt.subplots(
        2, 1, figsize=(9, 4.4),
        gridspec_kw={"height_ratios": [10, 1]},
    )
    ax_wc.imshow(wc_obj, interpolation="bilinear")
    ax_wc.axis("off")

    # Colorbar legend
    gradient = np.linspace(0, 1, 256).reshape(1, -1)
    ax_cb.imshow(gradient, aspect="auto", cmap=_SENTIMENT_CMAP)
    ax_cb.set_xticks([0, 85, 170, 255])
    ax_cb.set_xticklabels(["Most Negative", "Neutral", "Positive", "Most Positive"], fontsize=8)
    ax_cb.set_yticks([])
    ax_cb.spines[:].set_visible(False)

    plt.tight_layout(pad=0.5)
    return fig


def _dist_chart(distribution, display_labels=None):
    labels = [k.upper() for k in distribution]
    if display_labels is None:
        display_labels = labels
    values = list(distribution.values())
    colors = [SENTIMENT_COLORS.get(l, "#95a5a6") for l in labels]
    fig = go.Figure(go.Bar(
        x=display_labels,
        y=values,
        marker_color=colors,
        text=values,
        textposition="outside",
        textfont=dict(size=11, color="#000000", family="Arial Black, Arial, sans-serif"),
    ))
    fig.update_layout(
        title=dict(text="Per-word Sentiment Distribution", font=dict(size=20, color="#000000", family="Arial Black, Arial, sans-serif")),
        yaxis=dict(title=dict(text="Word count", standoff=12), range=[0, max(values) + 5]),
        xaxis=dict(title=dict(text="", standoff=12)),
        height=370,
        margin=dict(l=60, r=40, t=55, b=90),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(size=13, color="#000000", family="Arial Black, Arial, sans-serif"),
    )
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.12)")
    return fig


# ── Token chip renderer ───────────────────────────────────────────────────────

def _tokens_html(words, info=""):
    chips = "".join(
        f'<span style="background:#0d2680;color:#ffffff;border-radius:50px;'
        f'padding:4px 14px;font-size:0.82rem;display:inline-block;'
        f'margin:3px 2px;white-space:nowrap;">{word}</span>'
        for word in words
    )
    return f'<div style="display:flex;flex-wrap:wrap;gap:2px;padding:4px 0;">{chips}</div>'


# ── Report builder ────────────────────────────────────────────────────────────

def _fig_to_png_bytes(fig):
    """Return a BytesIO PNG of a matplotlib or Plotly figure, or None if fig is None."""
    if fig is None:
        return None
    from io import BytesIO
    if hasattr(fig, "to_image"):  # Plotly figure
        return BytesIO(fig.to_image(format="png", width=900, height=400, scale=1.5))
    buf = BytesIO()             # Matplotlib figure
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    buf.seek(0)
    return buf


def _build_pdf_report(text, sentiment, model_label, probabilities, labels, preprocess, word_dist, prob_fig, wc_fig, dist_fig):
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image as RLImage, HRFlowable,
    )

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        rightMargin=0.75 * inch, leftMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()

    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=18, spaceAfter=4, alignment=TA_CENTER)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, spaceBefore=12, spaceAfter=4,
                        textColor=colors.HexColor("#2c3e50"))
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9, leading=14)
    mono = ParagraphStyle("mono", parent=styles["Code"], fontSize=8, leading=12, leftIndent=12)
    caption = ParagraphStyle("caption", parent=styles["Normal"], fontSize=8, textColor=colors.gray, alignment=TA_CENTER)

    def section(title):
        return [
            Spacer(1, 6),
            Paragraph(title, h2),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#bdc3c7"), spaceAfter=4),
        ]

    story = []

    # ── Title ──────────────────────────────────────────────────────────────────
    story.append(Paragraph("NLP Sentiment Analysis Report", h1))
    story.append(Spacer(1, 4))
    from datetime import datetime
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", caption))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2980b9"), spaceAfter=10))

    # ── Summary table ──────────────────────────────────────────────────────────
    story += section("Summary")
    sent_color = colors.HexColor(SENTIMENT_COLORS.get(sentiment, "#7f8c8d"))
    conf_str = "  |  ".join(f"{l}: {p:.1%}" for l, p in zip(labels, probabilities))
    table_data = [
        [Paragraph("<b>Model</b>", body), Paragraph(model_label, body)],
        [Paragraph("<b>Sentiment</b>", body),
         Paragraph(f'<font color="{SENTIMENT_COLORS.get(sentiment, "#7f8c8d")}"><b>{sentiment}</b></font>', body)],
        [Paragraph("<b>Confidence</b>", body), Paragraph(conf_str, body)],
    ]
    tbl = Table(table_data, colWidths=[1.4 * inch, 5.5 * inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ecf0f1")),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#bdc3c7")),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(tbl)

    # ── Original text ──────────────────────────────────────────────────────────
    story += section("Original Text")
    story.append(Paragraph(text.replace("\n", "<br/>"), body))

    # ── Preprocessing ──────────────────────────────────────────────────────────
    story += section("Preprocessing Pipeline")
    preproc_rows = [
        ("Cleaned",    preprocess.cleaned_text),
        ("Removed",    preprocess.removed_text),
        ("Normalized", preprocess.normalized_text),
        ("Tokenized",  ", ".join(preprocess.tokenized_text)),
        ("Stemmed",    " ".join(preprocess.stemmed_text)),
        ("Lemmatized", " ".join(preprocess.lemmatized_text)),
        ("Word count", str(len(preprocess.tokenized_text))),
    ]
    pre_data = [[Paragraph(f"<b>{k}</b>", body), Paragraph(v, mono)] for k, v in preproc_rows]
    pre_tbl = Table(pre_data, colWidths=[1.1 * inch, 5.8 * inch])
    pre_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8f9fa")),
        ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#dee2e6")),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(pre_tbl)

    # ── Charts ────────────────────────────────────────────────────────────────
    usable_width = doc.width  # points between margins

    story += section("Charts")
    for fig, title in [(prob_fig, "Confidence Scores"), (wc_fig, "Word Cloud"), (dist_fig, "Per-word Distribution")]:
        img_bytes = _fig_to_png_bytes(fig)
        if img_bytes:
            img = RLImage(img_bytes, width=usable_width, height=usable_width * 0.42)
            story.append(img)
            story.append(Paragraph(title, caption))
            story.append(Spacer(1, 8))

    # ── NER ───────────────────────────────────────────────────────────────────
    story += section("Named Entities (NER)")
    if preprocess.ner:
        ner_data = [[Paragraph("<b>Entity</b>", body), Paragraph("<b>Label</b>", body)]]
        ner_data += [[Paragraph(e[0], mono), Paragraph(e[1], body)] for e in preprocess.ner]
        ner_tbl = Table(ner_data, colWidths=[3.35 * inch, 3.55 * inch])
        ner_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2980b9")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#bdc3c7")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(ner_tbl)
    else:
        story.append(Paragraph("No named entities found.", body))

    # ── POS tags ──────────────────────────────────────────────────────────────
    story += section("POS Tags")
    if preprocess.pos:
        pos_data = [[Paragraph("<b>Word</b>", body), Paragraph("<b>POS</b>", body)]]
        pos_data += [[Paragraph(w, mono), Paragraph(t, body)] for w, t in preprocess.pos]
        pos_tbl = Table(pos_data, colWidths=[3.35 * inch, 3.55 * inch])
        pos_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#27ae60")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#bdc3c7")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(pos_tbl)
    else:
        story.append(Paragraph("No POS tags available.", body))

    # ── Word distribution ─────────────────────────────────────────────────────
    story += section("Word-level Distribution")
    dist_data = [[Paragraph("<b>Category</b>", body), Paragraph("<b>Count</b>", body), Paragraph("<b>Words</b>", body)]]
    for label, words in word_dist.word_lists.items():
        dist_data.append([
            Paragraph(label.upper(), body),
            Paragraph(str(len(words)), body),
            Paragraph(", ".join(words) or "—", mono),
        ])
    dist_tbl = Table(dist_data, colWidths=[1.2 * inch, 0.7 * inch, 5.0 * inch])
    dist_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8e44ad")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#bdc3c7")),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(dist_tbl)

    doc.build(story)
    buf.seek(0)

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(buf.read())
    tmp.close()
    return tmp.name


def _build_html_report(text, sentiment, model_label, probabilities, labels, preprocess, word_dist, prob_fig, wc_fig, dist_fig):
    import base64
    import html as _html
    from io import BytesIO
    from datetime import datetime

    # Plotly chart divs (CDN loaded in <head>)
    prob_div = prob_fig.to_html(full_html=False, include_plotlyjs=False) if prob_fig else ""
    dist_div = dist_fig.to_html(full_html=False, include_plotlyjs=False) if dist_fig else ""

    # Word-cloud → base64 PNG
    wc_html = ""
    if wc_fig:
        buf = BytesIO()
        wc_fig.savefig(buf, format="png", dpi=96, bbox_inches="tight")
        buf.seek(0)
        wc_b64 = base64.b64encode(buf.read()).decode()
        wc_html = f"<img src='data:image/png;base64,{wc_b64}' style='width:100%;border-radius:8px;' alt='Word Cloud'>"

    sent_color = SENTIMENT_COLORS.get(sentiment, "#7f8c8d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _esc(s):
        return _html.escape(str(s))

    # Confidence score rows with inline bars
    conf_rows = "".join(
        f"<tr><td>{_esc(l)}</td><td class='num'>{p:.1%}</td>"
        f"<td><div style='background:#eef2fa;border-radius:4px;height:16px;overflow:hidden;'>"
        f"<div style='background:{SENTIMENT_COLORS.get(l.upper(), '#95a5a6')};"
        f"height:16px;width:{p*100:.1f}%;'></div></div></td></tr>"
        for l, p in zip(labels, probabilities)
    )

    # NER table
    if preprocess.ner:
        ner_rows = "".join(f"<tr><td>{_esc(e[0])}</td><td>{_esc(e[1])}</td></tr>" for e in preprocess.ner)
        ner_section = (
            f"<table><thead><tr><th>Entity</th><th>Label</th></tr></thead>"
            f"<tbody>{ner_rows}</tbody></table>"
        )
    else:
        ner_section = "<p class='small'>No named entities found.</p>"

    # POS table
    if preprocess.pos:
        pos_rows = "".join(f"<tr><td>{_esc(w)}</td><td>{_esc(t)}</td></tr>" for w, t in preprocess.pos)
        pos_section = (
            f"<table><thead><tr><th>Word</th><th>POS</th></tr></thead>"
            f"<tbody>{pos_rows}</tbody></table>"
        )
    else:
        pos_section = "<p class='small'>No POS tags found.</p>"

    # Word-distribution table
    dist_rows = "".join(
        f"<tr><td>{_esc(k.upper())}</td><td class='num'>{len(v)}</td>"
        f"<td>{_esc(', '.join(v)) or '&mdash;'}</td></tr>"
        for k, v in word_dist.word_lists.items()
    )

    html_out = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NLP Sentiment Report &mdash; {_esc(sentiment)}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  :root {{
    --navy:#002185; --navy-2:#1e2761; --navy-deep:#001054; --navy-ink:#0f172a;
    --ice:#cadcfc; --ice-soft:#eaf1ff; --ice-deeper:#c8d6f0;
    --gold:#ffb81c; --gold-soft:#fff4d1; --gold-deep:#b88200;
    --bg:#f6f8fc; --paper:#ffffff; --rule:#d7e0ee; --muted:#5b6b82;
    --green:#0f8a5f; --green-soft:#e8f6f0; --green-deep:#0a6244;
    --red:#b8312a; --red-soft:#fdecea;
    --amber:#b06b00; --amber-soft:#fff4dc;
    --shadow-md:0 1px 2px rgba(11,27,69,.04),0 8px 24px rgba(11,27,69,.05);
  }}
  *{{box-sizing:border-box;}}
  html{{scroll-behavior:smooth;}}
  body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Helvetica Neue",Arial,sans-serif;
        color:var(--navy-ink);background:var(--bg);line-height:1.6;font-size:15.5px;}}
  .wrap{{max-width:1080px;margin:0 auto;padding:28px 32px 80px;}}
  a{{color:var(--navy);}}

  .topbar{{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.93);
           backdrop-filter:saturate(140%) blur(8px);border-bottom:1px solid var(--rule);
           margin:-28px -32px 20px;padding:10px 32px;display:flex;align-items:center;gap:12px;font-size:13px;}}
  .topbar .logo{{font-family:Cambria,Georgia,serif;color:var(--navy);font-weight:700;font-size:16px;
                 display:flex;align-items:center;gap:8px;}}
  .topbar .logo::before{{content:"";width:18px;height:18px;background:var(--navy);border-radius:3px;}}
  .topbar .spacer{{flex:1;}}
  .topbar .stamp{{color:var(--muted);}}
  .topbar button{{appearance:none;border:1px solid var(--rule);background:white;color:var(--navy);
                  padding:6px 14px;border-radius:999px;font-family:inherit;font-size:12.5px;cursor:pointer;}}
  .topbar button:hover{{background:var(--ice-soft);border-color:var(--navy);}}
  .topbar button.primary{{background:var(--navy);color:white;border-color:var(--navy);}}

  .hero{{background:linear-gradient(140deg,var(--navy-deep),var(--navy) 55%,var(--navy-2));
         color:white;border-radius:16px;padding:44px 44px 36px;
         position:relative;overflow:hidden;box-shadow:var(--shadow-md);}}
  .hero::after{{content:"";position:absolute;right:-100px;top:-100px;width:320px;height:320px;
                background:radial-gradient(circle,rgba(255,184,28,.32) 0%,rgba(255,184,28,0) 70%);}}
  .hero .eyebrow{{font-size:11px;letter-spacing:4px;text-transform:uppercase;
                  color:var(--gold);font-weight:700;margin:0 0 14px;}}
  .hero h1{{font-size:34px;line-height:1.15;margin:0 0 14px;
            font-family:Cambria,Georgia,serif;font-weight:700;}}
  .hero .subtitle{{font-size:17px;color:var(--ice);max-width:820px;margin:0 0 22px;}}
  .gold-stripe{{width:56px;height:4px;background:var(--gold);border-radius:2px;margin-bottom:16px;}}
  .hero .meta{{display:flex;flex-wrap:wrap;gap:14px 28px;padding-top:18px;
               border-top:1px solid rgba(255,255,255,.18);font-size:13.5px;color:var(--ice);}}
  .hero .meta b{{color:white;}}

  section{{margin:38px 0;scroll-margin-top:70px;}}
  h2{{font-family:Cambria,Georgia,serif;font-size:26px;color:var(--navy);margin:0 0 8px;
      display:flex;align-items:baseline;gap:14px;}}
  h2 .num{{font-size:12px;letter-spacing:3px;color:var(--gold-deep);font-weight:700;font-family:-apple-system,sans-serif;}}
  h3{{font-family:Cambria,Georgia,serif;font-size:20px;color:var(--navy-2);margin:28px 0 10px;}}
  h4{{font-size:13.5px;color:var(--navy);text-transform:uppercase;letter-spacing:1.5px;margin:16px 0 8px;}}
  p{{margin:8px 0 14px;}}
  .small{{font-size:13px;color:var(--muted);}}

  .card{{background:var(--paper);border:1px solid var(--rule);border-radius:12px;
         padding:22px 26px;box-shadow:var(--shadow-md);}}
  .card.tone-warn{{background:var(--amber-soft);border-color:#f4d99a;}}
  .card.tone-info{{background:var(--ice-soft);border-color:var(--ice-deeper);}}

  table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:14px;
         background:var(--paper);border:1px solid var(--rule);border-radius:8px;overflow:hidden;}}
  th{{background:var(--navy);color:white;text-align:left;padding:10px 12px;
      font-size:12px;letter-spacing:.6px;text-transform:uppercase;}}
  td{{padding:10px 12px;border-top:1px solid var(--rule);vertical-align:top;color:#000000;}}
  tr:nth-child(even) td{{background:#fbfcfe;}}
  td.num{{font-variant-numeric:tabular-nums;font-family:ui-monospace,Menlo,monospace;}}

  .callout{{border-left:4px solid var(--gold);background:var(--gold-soft);
            border-radius:0 12px 12px 0;padding:14px 20px;margin:18px 0;}}
  .callout strong{{color:var(--navy);}}
  .callout.warn{{border-color:var(--amber);background:var(--amber-soft);}}
  .callout.info{{border-color:var(--navy);background:var(--ice-soft);}}

  .plot-card{{background:var(--paper);border:1px solid var(--rule);
              border-radius:14px;padding:24px;margin:16px 0;box-shadow:var(--shadow-md);}}

  .toc{{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:18px 22px;}}
  .toc ol{{margin:8px 0 0;padding-left:22px;}}
  .toc a{{text-decoration:none;}}
  .toc a:hover{{text-decoration:underline;}}

  pre{{background:#0b1b45;color:#e9efff;padding:14px 16px;border-radius:8px;overflow-x:auto;
       font-size:13px;line-height:1.5;border-left:3px solid var(--gold);margin:10px 0;
       font-family:ui-monospace,Menlo,monospace;white-space:pre-wrap;word-break:break-word;}}

  footer{{margin-top:48px;padding:20px 0 0;border-top:1px solid var(--rule);
          font-size:13px;color:var(--muted);}}
  footer b{{color:var(--navy);}}

  @media print{{
    body{{background:white;}} .topbar{{display:none!important;}}
    .hero,.card,.plot-card{{box-shadow:none;break-inside:avoid;}}
    section{{break-inside:avoid-page;}}
  }}
  @media(max-width:760px){{
    .hero{{padding:28px 22px;}} .hero h1{{font-size:24px;}}
    .wrap{{padding:18px 16px 50px;}}
  }}
</style>
</head>
<body>
<div class="wrap">

<nav class="topbar" aria-label="Document actions">
  <div class="logo">NLP Sentiment Analysis</div>
  <span class="spacer"></span>
  <span class="stamp">Generated: {now}</span>
  <button type="button" onclick="window.print()" class="primary">Download / Print PDF</button>
</nav>

<header class="hero">
  <div class="gold-stripe"></div>
  <p class="eyebrow">OpenMed HIPAA-Aware &middot; Patient Report Measures &middot; NLP Sentiment Analysis</p>
  <h1>Sentiment: <span style="color:{sent_color};">{_esc(sentiment)}</span></h1>
  <p class="subtitle">Full NLP preprocessing pipeline with PHI redaction, transformer inference, and word-level sentiment distribution.</p>
  <div class="meta">
    <div><b>Model</b> &middot; {_esc(model_label)}</div>
    <div><b>Words</b> &middot; {len(preprocess.tokenized_text)}</div>
    <div><b>Generated</b> &middot; {now}</div>
  </div>
</header>

<aside class="toc" style="margin-top:20px" aria-label="Contents">
  <h4 style="margin:0 0 4px;color:var(--navy);font-size:13.5px;text-transform:uppercase;letter-spacing:1px;">Contents</h4>
  <ol>
    <li><a href="#summary">Summary</a></li>
    <li><a href="#pii">PII Redaction (OpenMed)</a></li>
    <li><a href="#preprocessing">Preprocessing Pipeline</a></li>
    <li><a href="#charts">Charts</a></li>
    <li><a href="#ner">Named Entities (NER)</a></li>
    <li><a href="#pos">POS Tags</a></li>
    <li><a href="#distribution">Word-level Distribution</a></li>
  </ol>
</aside>

<section id="summary">
  <h2><span class="num">01</span> Summary</h2>
  <table>
    <thead><tr><th>Field</th><th>Value</th></tr></thead>
    <tbody>
      <tr><td>Model</td><td>{_esc(model_label)}</td></tr>
      <tr><td>Sentiment</td><td><b style="color:{sent_color};">{_esc(sentiment)}</b></td></tr>
      <tr><td>Word count</td><td>{len(preprocess.tokenized_text)}</td></tr>
      <tr><td>Generated</td><td>{now}</td></tr>
    </tbody>
  </table>
  <h3>Confidence Scores</h3>
  <table>
    <thead><tr><th>Label</th><th>Score</th><th>Bar</th></tr></thead>
    <tbody>{conf_rows}</tbody>
  </table>
</section>

<section id="pii">
  <h2><span class="num">02</span> PII Redaction (OpenMed)</h2>
  <div class="callout warn">
    <strong>PHI was redacted by the OpenMed PII De-identification API before any analysis.</strong>
    All downstream results are based on the redacted text shown below.
  </div>
  <pre>{_esc(preprocess.original_text)}</pre>
</section>

<section id="preprocessing">
  <h2><span class="num">03</span> Preprocessing Pipeline</h2>
  <table>
    <thead><tr><th>Stage</th><th>Output</th></tr></thead>
    <tbody>
      <tr><td><b>Cleaned</b></td><td>{_esc(preprocess.cleaned_text)}</td></tr>
      <tr><td><b>Removed</b></td><td>{_esc(preprocess.removed_text)}</td></tr>
      <tr><td><b>Normalized</b></td><td>{_esc(preprocess.normalized_text)}</td></tr>
      <tr><td><b>Tokenized</b></td><td>{_esc(', '.join(preprocess.tokenized_text))}</td></tr>
      <tr><td><b>Stemmed</b></td><td>{_esc(' '.join(preprocess.stemmed_text))}</td></tr>
      <tr><td><b>Lemmatized</b></td><td>{_esc(' '.join(preprocess.lemmatized_text))}</td></tr>
    </tbody>
  </table>
</section>

<section id="charts">
  <h2><span class="num">04</span> Charts</h2>
  <div class="plot-card">{prob_div}</div>
  <div class="plot-card">
    <h4>Word Cloud</h4>
    {wc_html if wc_html else "<p class='small'>Word cloud not available.</p>"}
  </div>
  <div class="plot-card">{dist_div}</div>
</section>

<section id="ner">
  <h2><span class="num">05</span> Named Entities (NER)</h2>
  {ner_section}
</section>

<section id="pos">
  <h2><span class="num">06</span> POS Tags</h2>
  {pos_section}
</section>

<section id="distribution">
  <h2><span class="num">07</span> Word-level Distribution</h2>
  <table>
    <thead><tr><th>Category</th><th>Count</th><th>Words</th></tr></thead>
    <tbody>{dist_rows}</tbody>
  </table>
</section>

<footer>
  <p>Generated by <b>NLP Sentiment Analysis</b> &middot; OpenMed HIPAA-aware pipeline &middot;
     Model: <b>{_esc(model_label)}</b> &middot; {now}</p>
</footer>

</div>
<script>
document.querySelectorAll('a[href^="#"]').forEach(el => {{
  el.addEventListener("click", e => {{
    const t = document.querySelector(el.getAttribute("href"));
    if (!t) return;
    e.preventDefault();
    t.scrollIntoView({{ behavior: "smooth", block: "start" }});
  }});
}});
</script>
</body>
</html>"""

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8")
    tmp.write(html_out)
    tmp.close()
    return tmp.name


def _build_report(text, sentiment, model_label, probabilities, labels, preprocess, word_dist):
    conf_str = "  |  ".join(f"{l}: {p:.1%}" for l, p in zip(labels, probabilities))
    ner_str = ", ".join(f"{e[0]} ({e[1]})" for e in preprocess.ner) or "None"
    pos_str = ", ".join(f"{w} ({t})" for w, t in preprocess.pos)

    lines = [
        "NLP SENTIMENT ANALYSIS REPORT",
        "=" * 60,
        f"Model:     {model_label}",
        f"Sentiment: {sentiment}",
        f"Scores:    {conf_str}",
        "",
        "ORIGINAL TEXT",
        "-" * 40,
        text,
        "",
        "PREPROCESSING PIPELINE",
        "-" * 40,
        f"Cleaned:    {preprocess.cleaned_text}",
        f"Removed:    {preprocess.removed_text}",
        f"Normalized: {preprocess.normalized_text}",
        f"Tokenized:  {', '.join(preprocess.tokenized_text)}",
        f"Stemmed:    {' '.join(preprocess.stemmed_text)}",
        f"Lemmatized: {' '.join(preprocess.lemmatized_text)}",
        f"Total words: {len(preprocess.tokenized_text)}",
        "",
        "NAMED ENTITIES (NER)",
        "-" * 40,
        ner_str,
        "",
        "POS TAGS",
        "-" * 40,
        pos_str,
        "",
        "WORD-LEVEL DISTRIBUTION",
        "-" * 40,
    ]
    for label, words in word_dist.word_lists.items():
        lines.append(f"  {label.upper()} ({len(words)}): {', '.join(words) or '-'}")

    return "\n".join(lines)


# ── Main analysis callback ────────────────────────────────────────────────────

_N_OUTPUTS = 16  # must match outputs list below


def run_analysis(text_input, file_obj, model_label):
    # 16 outputs: sentiment_html, prob_fig, wc_fig, dist_fig,
    #             redacted_html,
    #             cleaned, removed, normalized, tokenized, stemmed, lemmatized,
    #             ner_html, pos_str, txt_path, pdf_path, html_path
    empty = ("", None, None, None, "", "", "", "", "", "", "", "", "", None, None, None)

    def _err(msg):
        return (f"<p style='color:red'>{msg}</p>",) + empty[1:]

    # Resolve input
    file_text = None
    if file_obj is not None:
        path = file_obj if isinstance(file_obj, str) else getattr(file_obj, "path", getattr(file_obj, "name", None))
        if path:
            file_text = read_file_path(path)
    text = (file_text or text_input or "").strip()

    if not text:
        return _err("Please provide text or upload a file.")

    wc_count = len(text.split())
    if wc_count < 4:
        return _err("Please provide at least 4 words.")
    if wc_count > 300:
        return _err("Input exceeds 300-word limit.")

    try:
        # ── Step 1: Redact PII via OpenMed API ────────────────────────────
        redacted_text, pii_count = redact_pii(text)
        if pii_count > 0:
            redacted_html = (
                f"<div style='background:#fff8e1;border-left:4px solid #f39c12;"
                f"padding:10px 14px;border-radius:4px;font-family:monospace;white-space:pre-wrap;'>"
                f"<b style='color:#e67e22;'>⚠ {pii_count} PII entity/entities redacted before analysis</b><br><br>"
                f"<span style='color:#000000;'>{redacted_text}</span>"
                f"</div>"
            )
        else:
            redacted_html = (
                "<div style='background:#f0fff4;border-left:4px solid #27ae60;"
                "padding:10px 14px;border-radius:4px;'>"
                "<b style='color:#27ae60;'>✓ No PII detected — text passed through unchanged</b>"
                "</div>"
            )

        # Use redacted text for all downstream analysis
        text = redacted_text

        model_type = MODEL_LABEL_TO_TYPE.get(model_label, ModelType.DEFAULT)
        config = SUPPORTED_MODELS[model_type]
        labels = config["labels"]

        # Preprocess
        cleaned, removed, normalized, tokenized, stemmed, lemmatized, ner, pos = preprocess_text(text)
        preprocess = PreprocessResult(
            original_text=text, cleaned_text=cleaned, removed_text=removed,
            normalized_text=normalized, tokenized_text=tokenized,
            stemmed_text=stemmed, lemmatized_text=lemmatized, ner=ner, pos=pos,
        )

        lemmatized_str = " ".join(lemmatized)

        # Sentiment inference on original text to preserve negations and context
        sentiment, probabilities = analyze_sentiment(text, model_type)
        while len(probabilities) < len(labels):
            probabilities.append(0.0)

        # Word distribution
        word_dist = get_word_distribution(lemmatized, model_type)

        # Emoji display labels for emotion model
        if model_type == ModelType.EMOTION:
            display_labels = [f"{l} {EMOTION_EMOJI.get(l, '')}" for l in labels]
            dist_display_labels = [
                f"{k.upper()} {EMOTION_EMOJI.get(k.upper(), '')}"
                for k in word_dist.distribution
            ]
            sentiment_display = f"{sentiment} {EMOTION_EMOJI.get(sentiment, '')}"
        else:
            display_labels = labels
            dist_display_labels = None
            sentiment_display = sentiment

        # Charts
        prob_fig = _prob_chart(probabilities, labels, display_labels)
        wc_fig = _wordcloud_fig(lemmatized_str, word_dist) if lemmatized_str.strip() else None
        dist_fig = _dist_chart(word_dist.distribution, dist_display_labels)

        # Sentiment card HTML
        color = SENTIMENT_COLORS.get(sentiment, "#7f8c8d")
        sentiment_html = f"""
<div style="text-align:center;padding:20px;border-radius:10px;
            background:{color}18;border:2px solid {color};margin:4px 0">
  <div style="font-size:2rem;font-weight:700;color:{color}">{sentiment_display}</div>
  <div style="color:#666;margin-top:6px">{config['display']} &nbsp;·&nbsp; {len(tokenized)} words</div>
</div>"""

        # Preprocessing text outputs
        ner_html = get_ner_html(text)
        pos_str  = "".join(
            f'<span style="display:inline-block;margin:3px 4px;padding:3px 10px;'
            f'background:#2563eb;color:#fff;border-radius:20px;font-size:0.82rem;">'
            f'{w} <span style="opacity:0.75;font-size:0.75rem;">({t})</span></span>'
            for w, t in pos
        ) or "<p style='color:#6b7280;font-style:italic;'>No POS tags found.</p>"

        # Build downloadable reports (text + PDF)
        report_text = _build_report(
            text, sentiment, model_label, probabilities, labels, preprocess, word_dist
        )
        txt_tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
        txt_tmp.write(report_text)
        txt_tmp.close()

        pdf_path = _build_pdf_report(
            text, sentiment, model_label, probabilities, labels, preprocess, word_dist,
            prob_fig, wc_fig, dist_fig,
        )

        html_path = _build_html_report(
            text, sentiment, model_label, probabilities, labels, preprocess, word_dist,
            prob_fig, wc_fig, dist_fig,
        )

        return (
            sentiment_html,
            prob_fig,
            wc_fig,
            dist_fig,
            redacted_html,
            _tokens_html(cleaned.split()),
            _tokens_html(removed.split()),
            _tokens_html(normalized.split()),
            _tokens_html(tokenized, "Breaks text into individual words (tokens) for word-by-word analysis"),
            _tokens_html(stemmed,   "Reduces words to their root forms to group similar meanings together"),
            _tokens_html(lemmatized,"Reduces words to their root forms to group similar meanings together"),
            ner_html,
            pos_str,
            txt_tmp.name,
            pdf_path,
            html_path,
        )

    except Exception as exc:
        import traceback
        return _err(f"Analysis failed: {exc}<br><pre>{traceback.format_exc()}</pre>")


def load_sample(name):
    return SAMPLES.get(name, "")


# ── Gradio layout ─────────────────────────────────────────────────────────────

_CSS = """
.gradio-container { max-width: 1280px !important; margin: 0 auto; }
.tab-nav button { font-size: 0.92rem; }
"""

SAMPLE_NAMES = list(SAMPLES.keys())

with gr.Blocks(title="NLP Sentiment Analysis") as demo:

    gr.Markdown("""
# NLP Sentiment Analysis

Full NLP preprocessing pipeline + pretrained Transformer inference.
Covers cleaning · tokenisation · stemming · lemmatisation · NER · POS tagging · word cloud.

**Input limit:** 4 – 300 words &nbsp;|&nbsp; **File upload:** `.txt`, `.csv`
""")

    with gr.Row():
        sample_dd = gr.Dropdown(
            choices=SAMPLE_NAMES, value=SAMPLE_NAMES[0],
            label="Load sample text", scale=4,
        )
        load_btn = gr.Button("Load", variant="secondary", scale=1)

    gr.Markdown("---")

    with gr.Tabs():

        # ── Tab 1: Analyze ────────────────────────────────────────────────
        with gr.TabItem("Analyze"):
            with gr.Row(equal_height=False):
                with gr.Column(scale=1):
                    text_input = gr.Textbox(
                        label="Text input",
                        placeholder="Paste text here (4 – 300 words)…",
                        lines=11, max_lines=22,
                    )
                    file_input = gr.File(
                        label="Or upload file (.txt / .csv)",
                        file_types=[".txt", ".csv"],
                    )
                    model_dd = gr.Dropdown(
                        choices=MODEL_CHOICES, value=MODEL_CHOICES[0],
                        label="Model",
                    )
                    analyze_btn = gr.Button("Analyze", variant="primary")

                with gr.Column(scale=1):
                    sentiment_out = gr.HTML(label="Overall Sentiment")
                    prob_plot = gr.Plot(show_label=False)

            with gr.Row():
                wc_plot   = gr.Plot(show_label=False)
                dist_plot = gr.Plot(show_label=False)

            with gr.Accordion("PII Redaction (OpenMed)", open=True):
                gr.HTML(
                    '<span style="background:#e67e22;color:#ffffff;border-radius:20px;'
                    'padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">'
                    'Redacted Text</span>'
                    '<div style="font-size:0.75rem;color:#6b7280;margin-top:4px;margin-left:4px;">'
                    'PHI redacted by the OpenMed PII API before sentiment analysis</div>'
                )
                redacted_out = gr.HTML()

            with gr.Accordion("Preprocessing Pipeline", open=False):
                with gr.Row():
                    with gr.Column():
                        gr.HTML('<span style="background:#2563eb;color:#ffffff;border-radius:20px;padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">Cleaned</span><div style="font-size:0.75rem;color:#6b7280;margin-top:4px;margin-left:4px;">Removes special characters, extra spaces, and unwanted elements to prepare clean text for analysis</div>')
                        cleaned_out = gr.HTML()
                    with gr.Column():
                        gr.HTML('<span style="background:#2563eb;color:#ffffff;border-radius:20px;padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">Removed (stop words / punct)</span>')
                        removed_out = gr.HTML()
                with gr.Row():
                    with gr.Column():
                        gr.HTML('<span style="background:#2563eb;color:#ffffff;border-radius:20px;padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">Normalized</span><div style="font-size:0.75rem;color:#6b7280;margin-top:4px;margin-left:4px;">Converts text to lowercase and standardizes formatting for consistent analysis</div>')
                        normalized_out = gr.HTML()
                    with gr.Column():
                        gr.HTML('<span style="background:#2563eb;color:#ffffff;border-radius:20px;padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">Tokenized</span><div style="font-size:0.75rem;color:#6b7280;margin-top:4px;margin-left:4px;">Breaks text into individual words (tokens) for word-by-word analysis</div>')
                        tokenized_out = gr.HTML()
                with gr.Row():
                    with gr.Column():
                        gr.HTML('<span style="background:#2563eb;color:#ffffff;border-radius:20px;padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">Stemmed</span><div style="font-size:0.75rem;color:#6b7280;margin-top:4px;margin-left:4px;">Reduces words to their root forms to group similar meanings together</div>')
                        stemmed_out = gr.HTML()
                    with gr.Column():
                        gr.HTML('<span style="background:#2563eb;color:#ffffff;border-radius:20px;padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">Lemmatized</span><div style="font-size:0.75rem;color:#6b7280;margin-top:4px;margin-left:4px;">Reduces words to their root forms to group similar meanings together</div>')
                        lemmatized_out = gr.HTML()

            with gr.Accordion("NER & POS Tags", open=False):
                with gr.Row():
                    with gr.Column():
                        gr.HTML('<span style="background:#2563eb;color:#ffffff;border-radius:20px;padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">Named Entities (NER)</span>')
                        ner_out = gr.HTML()
                    with gr.Column():
                        gr.HTML('<span style="background:#2563eb;color:#ffffff;border-radius:20px;padding:3px 12px;font-size:0.85rem;font-weight:600;display:inline-block;">POS Tags</span>')
                        pos_out = gr.HTML()

            with gr.Row():
                report_file      = gr.File(label="Download Report (.txt)", interactive=False)
                report_file_pdf  = gr.File(label="Download Report (.pdf)", interactive=False)
                report_file_html = gr.File(label="Download Report (.html)", interactive=False)

        # ── Tab 2: About ──────────────────────────────────────────────────
        with gr.TabItem("About"):
            gr.Markdown("""
## Models

| Key | HuggingFace model | Labels |
|-----|-------------------|--------|
| `default` | `distilbert-base-uncased-finetuned-sst-2-english` | POSITIVE / NEGATIVE |
| `roberta` | `cardiffnlp/twitter-roberta-base-sentiment` | NEGATIVE / NEUTRAL / POSITIVE |
| `emotion` | `j-hartmann/emotion-english-distilroberta-base` | ANGER · DISGUST · FEAR · JOY · NEUTRAL · SADNESS · SURPRISE |

## NLP Pipeline (per request)

1. **Clean** — strip stop words, punctuation, URLs, emails (spaCy `en_core_web_md`)
2. **Normalise** — lowercase
3. **Tokenise** — NLTK word tokeniser
4. **Stem** — Porter Stemmer
5. **Lemmatise** — spaCy lemmatiser
6. **NER** — spaCy named-entity recognition
7. **POS tag** — spaCy part-of-speech tagger
8. **Inference** — HuggingFace pipeline on the lemmatised text
9. **Word-level** — each lemma is scored individually to build the distribution chart

## Project Structure

```
src/
  models.py        # type definitions & model config
  preprocessor.py  # NLP preprocessing pipeline
  analyzer.py      # transformer inference
api/
  main.py          # FastAPI app
  routes.py        # REST endpoints
  schemas.py       # Pydantic request/response models
ui/
  app.py           # this Gradio interface
examples/
  basic_usage.py   # standalone script example
```
""")

    # ── Event wiring ──────────────────────────────────────────────────────────
    load_btn.click(fn=load_sample, inputs=[sample_dd], outputs=[text_input])

    _outputs = [
        sentiment_out, prob_plot, wc_plot, dist_plot,
        redacted_out,
        cleaned_out, removed_out, normalized_out,
        tokenized_out, stemmed_out, lemmatized_out,
        ner_out, pos_out, report_file, report_file_pdf, report_file_html,
    ]
    analyze_btn.click(
        fn=run_analysis,
        inputs=[text_input, file_input, model_dd],
        outputs=_outputs,
    )


# ── Launch ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    _on_spaces = os.getenv("SPACE_ID") is not None
    demo.launch(
        server_name="0.0.0.0" if not _on_spaces else None,
        server_port=int(os.getenv("GRADIO_PORT", 7860)) if not _on_spaces else None,
        share=os.getenv("GRADIO_SHARE", "false").lower() == "true",
        ssr_mode=False,
        theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate"),
        css=_CSS,
    )
