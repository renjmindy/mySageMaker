"""
Zero-Shot Severity & Emotion Stratification pipeline for clinical
Patient-Reported Measure (PRM) survey text.

Architecture
------------
Each review is scored against four non-exclusive candidate labels using
'facebook/bart-large-mnli' as a zero-shot NLI classifier (Yin et al. entailment
formulation): for every (review, label) pair, the label is converted into a
hypothesis ("This text describes {label}.") and paired with the review as the
NLI premise. The model's entailment logit measures how strongly the review
implies that hypothesis.

Because the four labels are NOT mutually exclusive (a review can simultaneously
describe an adverse event AND emotional distress), each label's probability is
computed independently rather than via a single softmax across all four. This
is standard "multi_label=True" zero-shot-classification behavior: per label,
we softmax over just that label's [contradiction, entailment] logit pair
(discarding the "neutral" logit, which only matters for single-label,
mutually-exclusive classification) and keep the entailment component. Scores
therefore do NOT sum to 1.0 across labels -- each is an independent
P(label applies | text) estimate.

This raw-model implementation (batched tokenizer + model forward passes via a
PyTorch DataLoader) is used instead of `transformers.pipeline
("zero-shot-classification")` so batching, padding, dtype, device placement,
and OOM handling are fully explicit and controllable.

Severity heuristic
-------------------
`urgent_review` is a transparent, auditable rule on top of the model's raw
output (not a learned decision boundary), so a clinical reviewer can trace
exactly why any row was flagged. It requires BOTH:
  1. P("Clinical_Adverse_Event") > URGENT_REVIEW_THRESHOLD (0.75), and
  2. that score exceeds every non-clinical label's score by at least
     URGENT_REVIEW_MARGIN (0.15).
Flagged rows also carry the string "[URGENT_REVIEW]" in a dedicated
'urgent_flag' DataFrame column (empty string otherwise), so downstream
consumers can filter on either the boolean or the string marker.

Condition 2 exists because independent multi-label NLI scoring (see above)
tends to give moderately-high entailment probabilities to topically-adjacent
but non-clinical text (e.g. a billing or waiting-room complaint can score
well above threshold on "Clinical_Adverse_Event" purely from general
negative-review phrasing overlap). Requiring a clear margin over the
*non-clinical* labels (Administrative_Complaint, Routine_Feedback)
suppresses that class of false positive.

The margin deliberately excludes "Emotional_Distress" from the comparison:
genuine adverse events routinely co-occur with high distress scores (someone
describing fainting is, correctly, also scored as distressed), so requiring
Clinical_Adverse_Event to *outscore* Emotional_Distress produced false
negatives on real adverse-event reports during testing (a report of fainting
after a new prescription was suppressed because Emotional_Distress scored a
statistically insignificant 0.001 higher). Emotional_Distress is not a
competing explanation for the same text the way a billing or facility
complaint is, so it is excluded from the margin check.

Each candidate label also uses a hand-written, maximally discriminative
hypothesis (see LABEL_HYPOTHESES) rather than a single generic template,
which further sharpens the Clinical Adverse Event boundary specifically.

Robustness guarantees
----------------------
- CUDA OOM on any batch triggers recursive batch halving down to batch size 1
  before giving up, so a conservative default batch size is not required.
- Batches are length-sorted to minimize padding waste (peak GPU memory is set
  by the longest sequence in a batch, not the average).
- Rows are addressed positionally, never by index label, so duplicate or
  non-unique DataFrame indexes cannot crash or silently merge results.
- NaN/None/empty/whitespace rows and non-string scalars are normalized up
  front; unusable rows get a well-formed empty result rather than raising or
  shifting row alignment.
- GPU cache cleanup runs in a finally block, so an exception mid-analysis does
  not strand cached CUDA blocks.
"""

from __future__ import annotations

import contextlib
import gc
from typing import Any, Dict, List, NamedTuple, Optional

import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

MODEL_NAME = "facebook/bart-large-mnli"

# BART's learned positional embeddings support sequences up to 1024 tokens
# (vs. 512 for BERT-family encoders); both tokenizer calls enforce this.
MAX_SEQUENCE_LENGTH = 1024

CANDIDATE_LABELS: List[str] = [
    "Clinical_Adverse_Event",
    "Emotional_Distress",
    "Administrative_Complaint",
    "Routine_Feedback",
]

# Hand-written, maximally discriminative hypothesis per label, instead of a
# single generic template ("This text describes {label}."). A generic
# template leaves "Clinical Adverse Event" and "Operational/Logistical
# Complaint" semantically close for any negatively-toned review, which is
# what drove the false positives seen in testing (a billing/waiting-room
# complaint scoring >0.70 on Clinical Adverse Event). Spelling out concrete,
# mutually distinguishing criteria per label sharpens every boundary.
LABEL_HYPOTHESES: Dict[str, str] = {
    "Clinical_Adverse_Event": (
        "This patient describes a dangerous medical side effect, injury, "
        "medication error, or clinical emergency requiring urgent medical "
        "attention."
    ),
    "Emotional_Distress": (
        "This patient describes feeling emotional distress, such as fear, "
        "anxiety, sadness, or frustration about their care experience."
    ),
    "Administrative_Complaint": (
        "This patient describes a non-medical administrative or logistical "
        "problem, such as billing, scheduling, wait times, parking, or "
        "facility conditions."
    ),
    "Routine_Feedback": (
        "This patient gives routine or positive feedback on their care "
        "experience with no complaint or safety concern."
    ),
}

URGENT_REVIEW_LABEL = "Clinical_Adverse_Event"
URGENT_REVIEW_THRESHOLD = 0.75

# String marker written to the dedicated 'urgent_flag' DataFrame column for
# flagged rows (empty string otherwise).
URGENT_REVIEW_FLAG = "[URGENT_REVIEW]"

# Minimum lead Clinical_Adverse_Event's score must hold over the NON-CLINICAL
# labels before urgent_review is set. "Emotional_Distress" is intentionally
# excluded from this comparison: it legitimately co-occurs with genuine
# adverse events (fainting is distressing), so requiring CAE to outscore it
# produced false negatives on real adverse-event reports during testing. The
# margin only needs to rule out competing non-clinical explanations.
URGENT_REVIEW_MARGIN = 0.15
_URGENT_REVIEW_MARGIN_COMPARISON_LABELS = frozenset(
    {"Administrative_Complaint", "Routine_Feedback"}
)


# --------------------------------------------------------------------------- #
# Batch records
# --------------------------------------------------------------------------- #


class LabelPair(NamedTuple):
    """One (review, candidate-label) unit for independent entailment scoring."""

    row_pos: int
    label: str
    premise: str


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


class SeverityStratificationAnalyzer:
    """Batched, GPU-optimized zero-shot severity/emotion stratifier for PRM survey text."""

    def __init__(
        self,
        device: Optional[str] = None,
        batch_size: int = 16,
        urgent_review_threshold: float = URGENT_REVIEW_THRESHOLD,
        urgent_review_margin: float = URGENT_REVIEW_MARGIN,
    ) -> None:
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.batch_size = batch_size
        self.urgent_review_threshold = urgent_review_threshold
        self.urgent_review_margin = urgent_review_margin

        # fp16 halves activation/weight memory on GPU with negligible accuracy
        # loss for inference-only workloads; CPU stays in fp32 (no fp16 kernels).
        self._torch_dtype = torch.float16 if self.device == "cuda" else torch.float32

        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = self._load_model(MODEL_NAME)

        # exclude="not" prevents matching "not_entailment" first: harmless for
        # bart-large-mnli's 3-class labels, but 2-class NLI checkpoints (e.g.
        # the DeBERTa zeroshot family) would otherwise silently select the
        # not_entailment index and invert every score on a checkpoint swap.
        id2label = self.model.config.id2label
        self._entailment_idx = self._find_label_index(
            id2label, include="entailment", exclude="not"
        )
        self._contradiction_idx = self._find_label_index(id2label, include="contradiction")

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
        return model.to(self.device).eval()

    @staticmethod
    def _find_label_index(
        id2label: Dict[int, str], include: str, exclude: Optional[str] = None
    ) -> int:
        for idx, label in id2label.items():
            lower = label.lower()
            if include in lower and (exclude is None or exclude not in lower):
                return int(idx)
        raise ValueError(f"Could not find label containing '{include}' in {id2label}")

    def _autocast(self):
        # torch.autocast(device_type="cuda") must never be entered on
        # CPU-only builds, so CPU inference gets a plain nullcontext instead.
        if self.device == "cuda":
            return torch.autocast(device_type="cuda", dtype=torch.float16)
        return contextlib.nullcontext()

    # ------------------------------------------------------------------ #
    # OOM-safe batched forward pass
    # ------------------------------------------------------------------ #

    def _forward_logits(self, encoded: Dict[str, torch.Tensor]) -> torch.Tensor:
        """
        Run one padded batch through the model and return raw logits on CPU,
        shape (batch_size, num_labels).

        `encoded` tensors arrive on CPU and are only moved to the GPU inside
        this call. On CUDA OOM the batch is split in half along the batch
        dimension (dim 0) and each half is retried recursively, so a
        transient memory spike degrades throughput instead of crashing the
        whole job. Only a single 1024-token row that cannot fit by itself
        re-raises, since that is a genuine capacity limit.
        """
        moved = None
        try:
            moved = {k: v.to(self.device) for k, v in encoded.items()}
            with self._autocast():
                logits = self.model(**moved).logits  # (batch_size, num_labels)
            return logits.float().cpu()
        except torch.cuda.OutOfMemoryError:
            # Drop our references to the failed batch's GPU input tensors
            # BEFORE calling empty_cache(): they are still live locals inside
            # this except block, and empty_cache() cannot release memory that
            # referenced tensors occupy — without this, the halved retries
            # below run against a more constrained GPU than necessary.
            del moved
            batch_size = encoded["input_ids"].shape[0]
            if batch_size == 1:
                raise
            torch.cuda.empty_cache()
            half = batch_size // 2
            # CPU slices, re-trimmed: the collate padded every row to the
            # longest sequence in the ORIGINAL batch, and row-slicing does not
            # shrink that column width. Trimming each half to its own longest
            # row actually reduces the retry's memory footprint — the whole
            # point of retrying smaller.
            first = self._trim_padding({k: v[:half] for k, v in encoded.items()})
            second = self._trim_padding({k: v[half:] for k, v in encoded.items()})
            return torch.cat([self._forward_logits(first), self._forward_logits(second)], dim=0)

    @staticmethod
    def _trim_padding(encoded: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """
        Drop trailing all-pad columns beyond the longest real sequence in the
        (sliced) batch. Assumes right-padding, which is the BART tokenizer
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
        Normalize one raw cell to a usable string, or None if the row must be
        skipped. Handles: str, None, float('nan')/pd.NA/pd.NaT, numeric
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

    def _build_label_pairs(self, texts: List[Optional[str]]) -> List[LabelPair]:
        """
        Flatten every usable review into (row_pos, label, premise) records --
        one per candidate label -- for batched independent entailment scoring.
        None entries (missing/unusable rows) are skipped entirely and yield an
        empty result downstream, without shifting any other row's position.

        The result is sorted by premise length so each DataLoader batch
        contains similar-length sequences: with dynamic padding, peak GPU
        memory per batch is set by the LONGEST sequence in it, so mixing one
        1024-token review into a batch of short reviews would pad every row
        to 1024. Sorting makes short batches genuinely short. Correctness is
        unaffected because every record carries its own (row_pos, label)
        routing information.
        """
        pairs = [
            LabelPair(row_pos=row_pos, label=label, premise=text)
            for row_pos, text in enumerate(texts)
            if text is not None
            for label in CANDIDATE_LABELS
        ]
        pairs.sort(key=lambda p: len(p.premise))
        return pairs

    # ------------------------------------------------------------------ #
    # Batched zero-shot inference
    # ------------------------------------------------------------------ #

    @torch.inference_mode()
    def _run_classification(self, texts: List[Optional[str]]) -> Dict[int, Dict[str, float]]:
        """
        Returns {row_pos: {label: probability, ...}} with one independent
        entailment probability per candidate label for every usable row.
        Rows with no usable text are simply absent from the returned dict.
        """
        pairs = self._build_label_pairs(texts)
        per_row: Dict[int, Dict[str, float]] = {}
        if not pairs:
            return per_row

        def collate(batch: List[LabelPair]):
            premises = [p.premise for p in batch]
            hypotheses = [LABEL_HYPOTHESES[p.label] for p in batch]
            # tokenizer(text, text_pair, ...) packs premise+hypothesis into a
            # single <s> premise </s></s> hypothesis </s> sequence per row --
            # the standard NLI input format expected by this checkpoint.
            # truncation="only_first" trims ONLY the premise (the review text)
            # when over 1024 tokens, so the candidate-label hypothesis is
            # never cut off.
            encoded = self.tokenizer(
                premises,
                hypotheses,
                truncation="only_first",
                max_length=MAX_SEQUENCE_LENGTH,
                padding=True,
                return_tensors="pt",
            )
            return dict(encoded), batch

        loader = DataLoader(
            ListDataset(pairs),
            batch_size=self.batch_size,
            shuffle=False,
            collate_fn=collate,
        )

        for encoded, batch in loader:
            # input_ids / attention_mask shape: (batch_size, seq_len_in_batch)
            # -- seq_len is the max token length within this batch only,
            # since padding=True (dynamic padding) rather than a fixed 1024.
            logits = self._forward_logits(encoded)  # (batch_size, num_labels)
            # Multi-label scoring: for each row, take only its [contradiction,
            # entailment] logit pair and softmax over just those two, ignoring
            # "neutral". This yields an independent P(label applies) per row
            # rather than a single distribution shared across all 4 labels.
            pair_logits = logits[:, [self._contradiction_idx, self._entailment_idx]]  # (batch_size, 2)
            entail_probs = torch.softmax(pair_logits, dim=-1)[:, 1].tolist()  # (batch_size,)

            for item, prob in zip(batch, entail_probs):
                per_row.setdefault(item.row_pos, {})[item.label] = float(prob)

        return per_row

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def analyze(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run the full severity/emotion stratification pipeline over
        `df['review_text']` and return a copy of `df` with a new
        'absa_results' column containing, per row, a dict of the form
        {"labels": [...], "scores": [...], "urgent_review": bool}, with
        labels/scores sorted descending by score, plus an 'urgent_flag'
        column holding the string "[URGENT_REVIEW]" for flagged rows and ""
        otherwise. Rows that are NaN/None/empty/unusable get
        {"labels": [], "scores": [], "urgent_review": False} so every row in
        the output DataFrame stays aligned 1:1 with the input.
        """
        if "review_text" not in df.columns:
            raise ValueError("Input DataFrame must contain a 'review_text' column.")

        # Everything below is positional (0..n-1). Index labels are never
        # used for routing, so duplicate labels (e.g. after pd.concat without
        # ignore_index) can neither crash nor merge unrelated rows.
        texts = [self._coerce_text(v) for v in df["review_text"].tolist()]
        results: List[Dict[str, Any]] = [
            {"labels": [], "scores": [], "urgent_review": False} for _ in texts
        ]

        try:
            per_row = self._run_classification(texts)
            for row_pos, label_scores in per_row.items():
                # Sort descending by score, matching standard
                # zero-shot-classification pipeline output ordering.
                ranked = sorted(label_scores.items(), key=lambda kv: kv[1], reverse=True)
                labels = [label for label, _ in ranked]
                scores = [round(score, 4) for _, score in ranked]

                cae_score = label_scores.get(URGENT_REVIEW_LABEL, 0.0)
                competing_scores = [
                    s
                    for lbl, s in label_scores.items()
                    if lbl in _URGENT_REVIEW_MARGIN_COMPARISON_LABELS
                ]
                # Requires both an absolute threshold AND a clear lead over the
                # non-clinical competing labels (see module docstring
                # "Severity heuristic" for why Emotional Distress is excluded).
                exceeds_threshold = cae_score > self.urgent_review_threshold
                has_clear_margin = (
                    not competing_scores
                    or (cae_score - max(competing_scores)) >= self.urgent_review_margin
                )
                urgent = exceeds_threshold and has_clear_margin

                results[row_pos] = {"labels": labels, "scores": scores, "urgent_review": urgent}
        finally:
            # Cleanup runs even if inference raised (including an unrecoverable
            # OOM): release cached CUDA blocks back to the driver and drop any
            # lingering batch tensors so the process/GPU stays usable.
            if self.device == "cuda":
                torch.cuda.empty_cache()
            gc.collect()

        result_df = df.copy()
        # Plain positional column assignment — safe for any index, including
        # duplicated or non-integer labels.
        result_df["absa_results"] = results
        result_df["urgent_flag"] = [
            URGENT_REVIEW_FLAG if r["urgent_review"] else "" for r in results
        ]
        return result_df


# --------------------------------------------------------------------------- #
# Sample execution
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import os

    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data.csv")
    df = pd.read_csv(csv_path)

    analyzer = SeverityStratificationAnalyzer()
    result = analyzer.analyze(df)

    pd.set_option("display.max_colwidth", None)
    for i, row in result.iterrows():
        print(f"\n[Row {i}] {row['review_text']!r}")
        print(f"  absa_results = {row['absa_results']}")
        print(f"  urgent_flag  = {row['urgent_flag']!r}")
