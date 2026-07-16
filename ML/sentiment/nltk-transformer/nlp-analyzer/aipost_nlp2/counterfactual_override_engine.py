"""
Counterfactual/negation-relief post-processor layer on top of a raw PyTorch
sentiment model, for clinical Patient-Reported Measure (PRM) survey text.

Architecture
------------
This is a two-stage pipeline operating directly on raw model logits (no
`transformers.pipeline()` helper):

  Stage 1 - Raw neural classification:
      'finiteautomata/bertweet-base-sentiment-analysis' (a RoBERTa/BERTweet
      encoder fine-tuned for 3-class NEG/NEU/POS tweet sentiment) is loaded
      manually via AutoModelForSequenceClassification + AutoTokenizer. The
      raw, un-softmaxed logits tensor is extracted from the model output,
      then torch.softmax(logits, dim=-1) is applied explicitly to obtain
      class probabilities. An entropy-based uncertainty metric is computed
      from those probabilities: normalized Shannon entropy in [0.0, 1.0]
      (0.0 = a one-hot, maximally confident distribution; 1.0 = uniform,
      maximally uncertain), and confidence = 1.0 - normalized_entropy.

  Stage 2 - Counterfactual/negation-relief override layer:
      This class of model is a shallow, lexically-driven tweet classifier:
      it has no mechanism for tracking whether a negation is embedded inside
      a counterfactual conditional. Clinical PRM text routinely contains a
      "relief" construction -- "If I hadn't received the surgery, I wouldn't
      be alive" -- whose surface tokens (hadn't, wouldn't, ...) are strongly
      negative-coded, but whose real-world meaning is gratitude/relief
      (strongly POSITIVE). A regex-based heuristic (see "Counterfactual
      detection" below) detects this specific double-negation relief
      pattern and overrides the calibrated label to POS with a fixed high
      confidence, independent of whatever the raw model predicted.

Why regex instead of spaCy dependency parsing
----------------------------------------------
The two sibling pipelines in this repo (severity_stratification_pipeline.py,
absa_pipeline.py) both deliberately avoid spaCy/nltk so the only runtime
downloads are the Hugging Face checkpoints already required for the neural
stage; this pipeline follows the same convention. A dependency-parse-based
detector could describe the same "if [negated protasis], [negated or
persisting-negative apodosis]" structure via neg/mark/advcl edges, but the
regex approach below targets exactly that grammatical shape without a third
model download, and is easier for a clinical reviewer to audit line-by-line.

Counterfactual detection
-------------------------
`detect_counterfactual_relief()` is NOT a general counterfactual-reasoning
detector -- it is a narrowly-scoped heuristic for one common
clinical-feedback construction. Matching is SENTENCE-SCOPED (a conditional's
two clauses live in one sentence; matching across sentence boundaries would
let a complaint in a later sentence -- "...I am still in pain and nobody
has called back." -- flip a genuinely negative review), apostrophes are
normalized (curly U+2019 from phones/Word would otherwise silently defeat
every contraction pattern), and BOTH clause orders are recognized. Within
one sentence it requires:

  1. An "if" clause containing a NEGATED auxiliary (hadn't, didn't, wasn't,
     weren't, couldn't, hasn't, doesn't -- contracted or spelled out).
     "even if" / "as if" are excluded: those are concessive/manner
     readings, not counterfactual conditions ("Even if the staff didn't
     mean to be rude, I'm still in pain" is a live complaint). This is the
     counterfactual protasis: a hypothetical, negated past action/state.
  2. A result clause (apodosis) -- after the protasis comma, or BEFORE the
     "if" clause in reversed order ("I wouldn't be alive today if I hadn't
     received the surgery") -- containing EITHER:
       a. a CONDITIONAL negated auxiliary (wouldn't/couldn't only;
          indicative wasn't/weren't are excluded because "recovery wasn't
          going well" is a statement of fact, not an unrealized outcome)
          paired with a positive-outcome word (alive, here, okay, fine,
          well, better, surviving, walking, breathing, made it) -- the
          classic double-negative relief: "I wouldn't be alive" implies
          "I am alive"; OR
       b. a persistence marker (still, continue(s/d) to, keep(ing) on)
          paired with a negative-state word (in pain, hurting, suffering,
          sick, bedridden, struggling, worse) -- "I'd still be in pain"
          implies the negated protasis action DID happen and the patient
          is NOT still in that bad state. In reversed clause order this
          additionally requires the conditional 'd/would before the
          marker, so the indicative "I'm still in pain even if..." can
          never fire it.

  Requiring a NEGATED auxiliary specifically in the "if" clause is what
  correctly EXCLUDES the superficially similar but semantically opposite
  reinforcement construction "If I could give zero stars, I would.
  Terrible service." -- "could"/"would" carry no negation, so no override
  fires and the genuinely negative review is left as the raw model scored
  it.

This heuristic will not catch every counterfactual phrasing in the wild
(e.g. one split across two sentences, or built on synonyms outside the
word lists above); it targets the specific construction this override
layer exists to correct, and is intentionally conservative to avoid
flipping genuinely negative reviews.

Robustness guarantees
----------------------
- All neural inference runs inside a strict `torch.no_grad()` context.
- CUDA OOM on any batch triggers recursive batch halving down to batch size
  1 before giving up, so a conservative default batch size is not required.
- Batches are length-sorted to minimize padding waste (peak GPU memory is
  set by the longest sequence in a batch, not the average).
- Tokenization truncates at the model's ACTUAL maximum sequence length
  (BertweetTokenizer.model_max_length, 128 tokens for this checkpoint --
  not the 512 tokens common to BERT/DeBERTa-family encoders).
- Rows are addressed positionally, never by index label, so duplicate or
  non-unique DataFrame indexes cannot crash or silently merge results.
- NaN/None/empty/whitespace rows and non-string scalars are normalized up
  front; unusable rows get a well-formed placeholder result (same dict
  schema, sentiment fields set to None) rather than raising or shifting
  row alignment.
- GPU cache cleanup runs in a finally block, so an exception mid-analysis
  does not strand cached CUDA blocks.
"""

from __future__ import annotations

import contextlib
import gc
import math
import re
from typing import Any, Dict, List, NamedTuple, Optional

import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

MODEL_NAME = "finiteautomata/bertweet-base-sentiment-analysis"

# Fallback only: used if the loaded tokenizer does not expose a sane
# model_max_length (BertweetTokenizer normally reports 128, well under the
# 512-token limit common to BERT/DeBERTa-family encoders).
DEFAULT_MAX_SEQUENCE_LENGTH = 128

# Fixed confidence reported whenever the counterfactual-relief override
# fires. The override is a deterministic rule match, not a model
# probability, so it is reported at a fixed high (but not absolute) value
# rather than borrowing the raw model's (unreliable, pre-correction)
# softmax confidence.
OVERRIDE_CONFIDENCE = 0.95

POSITIVE_LABEL = "POS"

# --------------------------------------------------------------------------- #
# Counterfactual/negation-relief detection
# --------------------------------------------------------------------------- #

# Real survey text arriving from phones/Word uses curly apostrophes
# (U+2019 etc.). Every contraction pattern below is written with the ASCII
# apostrophe, so variants are normalized before any matching -- otherwise
# "hadn’t" silently fails every pattern and the override never fires.
_APOSTROPHE_TRANSLATION = str.maketrans(
    {"‘": "'", "’": "'", "ʼ": "'", "`": "'", "´": "'"}
)

# Detection is scoped to ONE sentence at a time: the protasis and apodosis
# of a conditional live in the same sentence, and matching across sentence
# boundaries lets a relief cue in a later, unrelated sentence ("...I am
# still in pain and nobody has called back.") flip a genuinely negative
# review.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

_NEGATED_AUX = (
    r"(?:hadn't|had not|didn't|did not|wasn't|was not|weren't|were not|"
    r"couldn't|could not|wouldn't|would not|hasn't|has not|doesn't|does not)"
)

# Conditional negated auxiliaries allowed in the RESULT clause of pattern
# (a). Deliberately EXCLUDES indicative wasn't/weren't: "recovery wasn't
# going well" is a plain negative statement of fact, not an unrealized
# outcome, and allowing indicative forms lets ordinary complaints trigger
# the positive override.
_CONDITIONAL_NEGATED_AUX = r"(?:wouldn't|would not|couldn't|could not)"

# An "if" that is not part of "even if" / "as if": those are concessive /
# manner readings, not counterfactual conditions ("Even if the staff didn't
# mean to be rude, I'm still in pain" is a live complaint that must not
# flip). Fixed-width lookbehinds, applied everywhere \bif\b is used.
_CONDITIONAL_IF = r"(?<!even )(?<!as )\bif\b"

_POSITIVE_OUTCOME = (
    r"(?:alive|here|okay|ok|fine|well|better|surviv\w*|walk\w*|breath\w*|"
    r"made it|able to)"
)

_NEGATIVE_STATE = (
    r"(?:in pain|hurt\w*|suffer\w*|sick|bedridden|struggl\w*|worse|"
    r"discomfort)"
)

_PERSISTENCE_MARKER = r"(?:still|continue[sd]?\s+to|keep(?:ing)?\s+on)"

# Protasis: an "if" clause containing a negated auxiliary, ending at the
# first following comma. The remainder of the SENTENCE after that comma is
# captured as the apodosis (sentence splitting above guarantees it cannot
# drift into later sentences). [^,]{0,N} keeps the protasis scoped to one
# clause rather than spanning unrelated commas.
_IF_CLAUSE_RE = re.compile(
    rf"{_CONDITIONAL_IF}[^,]{{0,120}}?\b{_NEGATED_AUX}\b[^,]{{0,80}}?,"
    rf"\s*(?P<apodosis>.+)$",
    re.IGNORECASE,
)

# Apodosis pattern (a): a CONDITIONAL negated auxiliary paired with a
# positive-outcome word -- the classic double-negative relief ("I wouldn't
# be alive" implies "I am alive").
_RELIEF_NEGATED_POSITIVE_RE = re.compile(
    rf"\b{_CONDITIONAL_NEGATED_AUX}\b.{{0,40}}?\b{_POSITIVE_OUTCOME}\b",
    re.IGNORECASE,
)

# Apodosis pattern (b): a persistence marker paired with a negative-state
# word -- "I'd still be in pain" implies the negated protasis action DID
# happen, so the patient is NOT still in that bad state.
_RELIEF_PERSISTING_NEGATIVE_RE = re.compile(
    rf"\b{_PERSISTENCE_MARKER}\b.{{0,40}}?\b{_NEGATIVE_STATE}\b",
    re.IGNORECASE,
)

# Reversed clause order, equally common in real feedback: result clause
# first, "if" clause second ("I wouldn't be alive today if I hadn't
# received the surgery"). No comma is required in this order, so the
# comma-anchored protasis regex above cannot see it. Same sentence scope,
# same concessive-"if" exclusion.
_REVERSED_RELIEF_A_RE = re.compile(
    rf"\b{_CONDITIONAL_NEGATED_AUX}\b.{{0,40}}?\b{_POSITIVE_OUTCOME}\b"
    rf".{{0,80}}?{_CONDITIONAL_IF}.{{0,120}}?\b{_NEGATED_AUX}\b",
    re.IGNORECASE,
)

# Reversed pattern (b) additionally requires the CONDITIONAL 'd/would
# before the persistence marker ("I'd still be in pain if..."): the
# indicative form ("I'm still in pain even if...") is a live complaint,
# not relief.
_REVERSED_RELIEF_B_RE = re.compile(
    rf"\b(?:'d|would)\s+{_PERSISTENCE_MARKER}\b.{{0,40}}?\b{_NEGATIVE_STATE}\b"
    rf".{{0,80}}?{_CONDITIONAL_IF}.{{0,120}}?\b{_NEGATED_AUX}\b",
    re.IGNORECASE,
)


def detect_counterfactual_relief(text: str) -> bool:
    """
    Return True if `text` contains the "counterfactual relief" double
    negation construction (see module docstring "Counterfactual detection"
    for the exact rule and its deliberate scope/limits). Matching is
    sentence-scoped and apostrophe-normalized; both clause orders are
    recognized.
    """
    text = text.translate(_APOSTROPHE_TRANSLATION)
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        match = _IF_CLAUSE_RE.search(sentence)
        if match is not None:
            apodosis = match.group("apodosis")
            if _RELIEF_NEGATED_POSITIVE_RE.search(
                apodosis
            ) or _RELIEF_PERSISTING_NEGATIVE_RE.search(apodosis):
                return True
        if _REVERSED_RELIEF_A_RE.search(sentence) or _REVERSED_RELIEF_B_RE.search(
            sentence
        ):
            return True
    return False


# --------------------------------------------------------------------------- #
# Batch records
# --------------------------------------------------------------------------- #


class TextItem(NamedTuple):
    """One usable review, tagged with its positional row index."""

    row_pos: int
    text: str


class ListDataset(Dataset):
    """Minimal Dataset wrapper over a pre-built list of records."""

    def __init__(self, records: list):
        self.records = records

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int):
        return self.records[idx]


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #


class CounterfactualOverrideEngine:
    """
    Batched, GPU-optimized sentiment classifier with a rule-based
    counterfactual/negation-relief calibration layer for PRM survey text.
    """

    def __init__(
        self,
        device: Optional[str] = None,
        batch_size: int = 32,
        override_confidence: float = OVERRIDE_CONFIDENCE,
    ) -> None:
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.batch_size = batch_size
        self.override_confidence = override_confidence

        # fp16 halves activation/weight memory on GPU with negligible
        # accuracy loss for inference-only workloads; CPU stays in fp32
        # (no fp16 kernels).
        self._torch_dtype = torch.float16 if self.device == "cuda" else torch.float32

        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = self._load_model(MODEL_NAME)

        # BertweetTokenizer correctly reports 128 (not the 512-token limit
        # common to BERT/DeBERTa-family encoders); fall back to the module
        # constant only if a swapped-in tokenizer reports something absurd
        # (transformers uses a huge sentinel, e.g. 1e30, for "unbounded").
        reported = self.tokenizer.model_max_length
        self.max_sequence_length = (
            int(reported) if isinstance(reported, int) and reported < 100_000
            else DEFAULT_MAX_SEQUENCE_LENGTH
        )

        # Resolved dynamically from the model config rather than hardcoded,
        # so the pipeline stays correct if the checkpoint is swapped for one
        # with a different id2label ordering.
        self._id2label: Dict[int, str] = {
            idx: str(label).upper() for idx, label in self.model.config.id2label.items()
        }
        self._num_labels = len(self._id2label)

    def _load_model(self, name: str) -> AutoModelForSequenceClassification:
        try:
            model = AutoModelForSequenceClassification.from_pretrained(
                name, dtype=self._torch_dtype, low_cpu_mem_usage=True
            )
        except TypeError:
            # transformers < 4.56 only accepts the older `torch_dtype` kwarg.
            model = AutoModelForSequenceClassification.from_pretrained(
                name, torch_dtype=self._torch_dtype, low_cpu_mem_usage=True
            )
        # Belt-and-braces on top of the torch.no_grad() forward: with
        # requires_grad disabled at the parameter level, no code path
        # (including future refactors that forget the context manager) can
        # ever build an autograd graph through these weights.
        model.requires_grad_(False)
        return model.to(self.device).eval()

    def _autocast(self):
        # torch.autocast(device_type="cuda") must never be entered on
        # CPU-only builds, so CPU inference gets a plain nullcontext instead.
        if self.device == "cuda":
            return torch.autocast(device_type="cuda", dtype=torch.float16)
        return contextlib.nullcontext()

    # ------------------------------------------------------------------ #
    # OOM-safe batched forward pass
    # ------------------------------------------------------------------ #

    def _forward_probs(self, encoded: Dict[str, torch.Tensor]) -> torch.Tensor:
        """
        Run one padded batch through the model and return softmax
        probabilities on CPU, shape (batch_size, num_labels).

        `encoded` tensors arrive on CPU and are only moved to the GPU inside
        this call. On CUDA OOM the batch is split in half along the batch
        dimension (dim 0) and each half is retried recursively, so a
        transient memory spike degrades throughput instead of crashing the
        whole job. Only a single row that cannot fit by itself re-raises,
        since that is a genuine capacity limit.
        """
        moved = None
        try:
            moved = {k: v.to(self.device) for k, v in encoded.items()}
            with torch.no_grad(), self._autocast():
                logits = self.model(**moved).logits  # (batch_size, num_labels)
                # Strict dimension guard: a sequence-classification head
                # must emit exactly (batch_size, num_labels). A swapped-in
                # checkpoint with a token-classification head would emit
                # (batch, seq_len, labels) and otherwise corrupt every
                # downstream row silently instead of failing loudly here.
                expected = (moved["input_ids"].shape[0], self._num_labels)
                if tuple(logits.shape) != expected:
                    raise RuntimeError(
                        f"Model emitted logits of shape {tuple(logits.shape)}; "
                        f"expected (batch_size, num_labels) = {expected}. "
                        f"Is '{MODEL_NAME}' a sequence-classification checkpoint?"
                    )
                # Manual softmax over raw logits (never the pipeline()
                # helper), dim=-1 is the class dimension. .float() upcasts
                # fp16 logits before softmax for numerical stability.
                probs = torch.softmax(logits.float(), dim=-1)
            return probs.cpu()
        except torch.cuda.OutOfMemoryError:
            # Drop our references to the failed batch's GPU input tensors
            # BEFORE calling empty_cache(): they are still live locals here,
            # and empty_cache() cannot release memory that referenced
            # tensors occupy.
            del moved
            batch_size = encoded["input_ids"].shape[0]
            if batch_size == 1:
                raise
            torch.cuda.empty_cache()
            half = batch_size // 2
            # CPU slices, re-trimmed: the collate padded every row to the
            # longest sequence in the ORIGINAL batch, and row-slicing does
            # not shrink that column width. Trimming each half to its own
            # longest row genuinely reduces the retry's memory footprint --
            # the whole point of retrying smaller.
            first = self._trim_padding({k: v[:half] for k, v in encoded.items()})
            second = self._trim_padding({k: v[half:] for k, v in encoded.items()})
            return torch.cat(
                [self._forward_probs(first), self._forward_probs(second)], dim=0
            )

    @staticmethod
    def _trim_padding(encoded: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """
        Drop trailing all-pad columns beyond the longest real sequence in
        the (sliced) batch. Assumes right-padding, which is the tokenizer
        default and what the collate's padding=True produces.
        """
        seq_len = int(encoded["attention_mask"].sum(dim=1).max().item())
        return {k: (v[:, :seq_len] if v.dim() == 2 else v) for k, v in encoded.items()}

    # ------------------------------------------------------------------ #
    # Text preprocessing
    # ------------------------------------------------------------------ #

    @staticmethod
    def _coerce_text(value: Any) -> Optional[str]:
        """
        Normalize one raw cell to a usable string, or None if the row must
        be skipped. Handles: str, None, float('nan')/pd.NA/pd.NaT, numeric
        scalars (stringified), and non-scalar junk like lists/dicts (treated
        as missing rather than raising inside pd.isna).
        """
        if isinstance(value, str):
            text = value
        elif value is None:
            return None
        else:
            try:
                if pd.isna(value):
                    return None
            except (TypeError, ValueError):
                return None  # non-scalar (list/dict/array) — treat as missing
            text = str(value)
        text = text.strip()
        return text or None

    @staticmethod
    def _entropy_confidence(probs: List[float]) -> float:
        """
        Normalized-Shannon-entropy-based confidence in [0.0, 1.0]: 1.0 for a
        one-hot (maximally confident) distribution, 0.0 for a uniform
        (maximally uncertain) distribution over `len(probs)` classes.
        """
        eps = 1e-12
        entropy = -sum(p * math.log(p + eps) for p in probs)
        max_entropy = math.log(len(probs))
        normalized = entropy / max_entropy if max_entropy > 0 else 0.0
        return round(1.0 - normalized, 4)

    # ------------------------------------------------------------------ #
    # Stage 1: batched neural classification
    # ------------------------------------------------------------------ #

    def _run_classification(self, texts: List[Optional[str]]) -> Dict[int, List[float]]:
        """
        Returns {row_pos: [p_class_0, p_class_1, ...]} softmax probabilities
        for every usable row. Rows with no usable text are absent.
        """
        items = [
            TextItem(row_pos, text) for row_pos, text in enumerate(texts) if text is not None
        ]
        per_row: Dict[int, List[float]] = {}
        if not items:
            return per_row

        # Length-sorted so each DataLoader batch contains similar-length
        # sequences: with dynamic padding, peak memory per batch is set by
        # the LONGEST sequence in it, so mixing one long review into a batch
        # of short ones would pad every row up unnecessarily. Correctness is
        # unaffected because every record carries its own row_pos.
        items.sort(key=lambda it: len(it.text))

        def collate(batch: List[TextItem]):
            texts_batch = [item.text for item in batch]
            encoded = self.tokenizer(
                texts_batch,
                truncation=True,
                max_length=self.max_sequence_length,
                padding=True,
                return_tensors="pt",
            )
            return dict(encoded), batch

        loader = DataLoader(
            ListDataset(items),
            batch_size=self.batch_size,
            shuffle=False,
            collate_fn=collate,
        )

        for encoded, batch in loader:
            # input_ids / attention_mask shape: (batch_size, seq_len_in_batch)
            # -- seq_len is the max token length within this batch only,
            # since padding=True (dynamic padding) rather than a fixed
            # max_sequence_length.
            probs = self._forward_probs(encoded)  # (batch_size, num_labels)
            for item, row_probs in zip(batch, probs.tolist()):
                per_row[item.row_pos] = row_probs

        return per_row

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def analyze(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run the full raw-classification + counterfactual-override pipeline
        over `df['review_text']` and return a copy of `df` with a new
        'calibrated_results' column containing, per row, a dict of the form
        {"raw_sentiment": "NEG"/"NEU"/"POS", "calibrated_sentiment": str,
        "confidence": float, "override_triggered": bool}.

        Rows that are NaN/None/empty/unusable get a well-formed placeholder
        with the same four keys ("raw_sentiment"/"calibrated_sentiment" set
        to None, "confidence" 0.0, "override_triggered" False) so every row
        in the output DataFrame stays aligned 1:1 with the input.
        """
        if "review_text" not in df.columns:
            raise ValueError("Input DataFrame must contain a 'review_text' column.")

        # Everything below is positional (0..n-1). Index labels are never
        # used for routing, so duplicate labels (e.g. after pd.concat
        # without ignore_index) can neither crash nor merge unrelated rows.
        texts = [self._coerce_text(v) for v in df["review_text"].tolist()]
        results: List[Dict[str, Any]] = [
            {
                "raw_sentiment": None,
                "calibrated_sentiment": None,
                "confidence": 0.0,
                "override_triggered": False,
            }
            for _ in texts
        ]

        try:
            per_row_probs = self._run_classification(texts)
            for row_pos, probs in per_row_probs.items():
                raw_label_idx = max(range(self._num_labels), key=lambda i: probs[i])
                raw_sentiment = self._id2label[raw_label_idx]

                override_triggered = detect_counterfactual_relief(texts[row_pos])
                if override_triggered:
                    calibrated_sentiment = POSITIVE_LABEL
                    confidence = self.override_confidence
                else:
                    calibrated_sentiment = raw_sentiment
                    confidence = self._entropy_confidence(probs)

                results[row_pos] = {
                    "raw_sentiment": raw_sentiment,
                    "calibrated_sentiment": calibrated_sentiment,
                    "confidence": confidence,
                    "override_triggered": override_triggered,
                }
        finally:
            # Cleanup runs even if inference raised (including an
            # unrecoverable OOM): release cached CUDA blocks back to the
            # driver and drop any lingering batch tensors so the
            # process/GPU stays usable.
            if self.device == "cuda":
                torch.cuda.empty_cache()
            gc.collect()

        result_df = df.copy()
        # Plain positional column assignment — safe for any index,
        # including duplicated or non-integer labels.
        result_df["calibrated_results"] = results
        return result_df


# --------------------------------------------------------------------------- #
# Sample execution
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import os

    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data.csv")
    df = pd.read_csv(csv_path)

    engine = CounterfactualOverrideEngine()
    result = engine.analyze(df)

    pd.set_option("display.max_colwidth", None)
    for i, row in result.iterrows():
        print(f"\n[Row {i}] {row['review_text']!r}")
        print(f"  calibrated_results = {row['calibrated_results']}")
