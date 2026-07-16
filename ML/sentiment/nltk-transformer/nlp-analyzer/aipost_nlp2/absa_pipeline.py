"""
Aspect-Based Sentiment Analysis (ABSA) pipeline for clinical Patient-Reported
Measure (PRM) survey text.

Architecture
------------
This is a two-stage NLI-driven pipeline rather than a single fine-tuned ABSA
head (no public checkpoint exists for these three custom clinical aspects,
so training a token-classification head is out of scope here):

  Stage 1 - Aspect Detection (zero-shot NLI / entailment):
      Each clause in a review is checked for entailment against a hypothesis
      describing each of the three clinical aspects. A clause is assigned to
      an aspect only if that aspect's entailment probability clears an
      absolute floor AND is close to the clause's best-scoring aspect (see
      ASPECT_DOMINANCE_RATIO for why both conditions are needed). This is
      standard zero-shot-classification machinery, but implemented here as
      raw batched tokenizer + model forward passes (rather than the
      high-level `pipeline()` helper) so that batching is fully explicit and
      controllable via a PyTorch DataLoader.

  Stage 2 - Aspect-Level Sentiment Scoring:
      For every (review, aspect) pair with >=1 qualifying clause, the
      qualifying clause(s) are concatenated in reading order and scored with
      a sentiment classifier. The classifier's positive/negative
      probabilities are converted to a single signed polarity score
      P(positive) - P(negative) in [-1.0, +1.0]; with the 3-class checkpoint
      any probability mass on "neutral" simply shrinks the magnitude
      toward 0.

Model note
----------
The checkpoint 'google/deberta-v3-base' is a *raw pretrained encoder* with no
classification head, so it cannot perform NLI/zero-shot entailment out of the
box (it would produce random logits from an untrained head). Instead we use
'MoritzLaurer/deberta-v3-base-zeroshot-v1.1-all-33', which is the same
DeBERTa-v3-base backbone fine-tuned specifically for zero-shot entailment
classification, as a drop-in AutoModelForSequenceClassification checkpoint.

For sentiment polarity we use 'cardiffnlp/twitter-roberta-base-sentiment-latest',
a 3-class (negative/neutral/positive) RoBERTa sentiment head. The more common
SST-2 DistilBERT checkpoint was tried first and mis-signed healthcare-domain
fragments ("Clean facilities and very short wait times." scored -0.54):
SST-2 is movie-review data, where words like "short" carry negative valence.
The Twitter-trained model handles short, informal, domain-shifted review
fragments far better, and its explicit neutral class keeps weakly-opinionated
text near 0 instead of forcing a confident sign.

Both model names are read from module-level constants, so swapping either
checkpoint (e.g. to a larger DeBERTa-v3-large NLI model) requires no other
code changes.

Robustness guarantees
---------------------
- CUDA OOM on any batch triggers recursive batch halving down to batch size 1
  before giving up, so a conservative default batch size is not required.
- Batches are length-sorted to minimize padding waste (peak GPU memory is set
  by the longest sequence in a batch, not the average).
- Rows are addressed positionally, never by index label, so duplicate or
  non-unique DataFrame indexes (common after pd.concat) cannot crash or
  silently merge results.
- NaN/None/empty/whitespace rows and non-string scalars are normalized up
  front; unusable rows yield [] rather than raising.
- Per-clause character caps bound tokenizer CPU/RAM cost on pathological
  inputs (e.g. megabyte-long rows with no punctuation) before the 512-token
  model truncation ever applies.
- GPU cache cleanup runs in a finally block, so an exception mid-analysis
  does not strand cached CUDA blocks.
"""

from __future__ import annotations

import contextlib
import gc
import re
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# DeBERTa-v3-base backbone fine-tuned for zero-shot NLI entailment (see module
# docstring for why this checkpoint is used instead of the bare base model).
ASPECT_MODEL_NAME = "MoritzLaurer/deberta-v3-base-zeroshot-v1.1-all-33"

# 3-class (negative/neutral/positive) sentiment classifier. See the module
# docstring "Model note" for why this replaces the SST-2 DistilBERT head.
SENTIMENT_MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"

# Every transformer encoder used here (DeBERTa-v3-base, RoBERTa-base) has a
# 512-token absolute positional limit; both tokenizer calls enforce this.
MAX_SEQUENCE_LENGTH = 512

# English averages ~4 characters/token, so 512 tokens is well under ~2,500
# characters. Capping each clause at 4,000 characters BEFORE tokenization
# bounds tokenizer CPU/RAM cost on pathological rows (e.g. a multi-megabyte
# string with no sentence punctuation would otherwise be fully tokenized
# three times per aspect just to be truncated to 512 tokens anyway).
MAX_CLAUSE_CHARS = 4000

# Hypothesis templates used as the NLI "hypothesis" half of each
# (premise=clause, hypothesis=aspect description) pair. Phrasing them as
# complete declarative sentences maximizes entailment-model accuracy.
ASPECT_HYPOTHESES: Dict[str, str] = {
    "Clinical_Competence": (
        "This text is about a doctor's or clinician's medical skill, "
        "diagnostic accuracy, or clinical competence."
    ),
    "Staff_Behavior": (
        "This text is about the friendliness, helpfulness, or behavior of "
        "nurses or front desk staff."
    ),
    "Facility_Wait_Time": (
        "This text is about waiting time, facility cleanliness, or parking."
    ),
}

# Canonical aspect ordering for deterministic output lists.
_ASPECT_ORDER: Dict[str, int] = {a: i for i, a in enumerate(ASPECT_HYPOTHESES)}

# Absolute floor: minimum entailment probability for a clause to be
# considered "about" a given aspect at all. 0.5 is the nominal decision
# boundary for a binary entailment / not_entailment classifier.
ENTAILMENT_THRESHOLD = 0.5

# Relative dominance rule: within one clause, an aspect is kept only if its
# entailment probability is >= this fraction of the clause's BEST aspect
# score. The floor alone cannot separate true from false assignments because
# this checkpoint's absolute probabilities are poorly calibrated across
# clauses: "The parking was terrible." scores a *false* 0.68 on
# Clinical_Competence, while a genuinely mixed clause ("the front desk staff
# was incredibly rude and the wait time was an absolute nightmare") scores
# its *true* aspects only 0.62 (Staff_Behavior) and 0.60
# (Facility_Wait_Time) — no absolute threshold sits between 0.62 and 0.68.
# Within a clause, however, the pattern is clean: true co-aspects score
# within ~3% of the clause max, while topically-adjacent false positives sit
# at ~70% of it (0.68 vs. the 0.95 that Facility_Wait_Time correctly gets
# for the parking clause). 0.8 separates those two regimes with wide margin
# on both sides, while still allowing genuinely multi-aspect clauses to keep
# every near-tied aspect.
ASPECT_DOMINANCE_RATIO = 0.8

# Sentence boundary splitter: split after ., !, or ? followed by whitespace.
# Kept dependency-free (no nltk/spacy) so the script has no extra runtime
# downloads beyond the two HF checkpoints.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# Clause boundary splitter: a single sentence frequently praises one aspect
# and criticizes another within one contrastive sentence (e.g. "...a miracle,
# but the staff was rude..."). Without this second-pass split, the whole
# sentence would be sentiment-scored as one blended unit for every aspect it
# entails, hiding the sign difference between clauses. Splitting on
# contrastive conjunctions (dropping the conjunction itself) isolates each
# clause so it can be entailment-checked and sentiment-scored independently.
_CLAUSE_SPLIT_RE = re.compile(
    r"\s*,?\s+\b(?:but|however|although|though|yet|whereas)\b,?\s*", re.IGNORECASE
)


# --------------------------------------------------------------------------- #
# Batch records
# --------------------------------------------------------------------------- #


class AspectPair(NamedTuple):
    """One (clause, aspect-hypothesis) candidate for entailment scoring.

    `row_pos` is the POSITIONAL row number in the DataFrame (0..n-1), never
    the index label: index labels may be duplicated (e.g. after pd.concat)
    and label-based writes would then crash or merge unrelated rows.
    `clause_idx` preserves reading order so clauses can be re-concatenated
    in their original order after length-sorted batching.
    """

    row_pos: int
    clause_idx: int
    aspect: str
    clause: str


class SentimentItem(NamedTuple):
    """One (review-row, aspect) unit of text to be sentiment-scored."""

    row_pos: int
    aspect: str
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


class ClinicalABSAAnalyzer:
    """Batched, GPU-optimized aspect-based sentiment analyzer for PRM survey text."""

    def __init__(
        self,
        device: Optional[str] = None,
        aspect_batch_size: int = 32,
        sentiment_batch_size: int = 32,
        entailment_threshold: float = ENTAILMENT_THRESHOLD,
        aspect_dominance_ratio: float = ASPECT_DOMINANCE_RATIO,
    ) -> None:
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.aspect_batch_size = aspect_batch_size
        self.sentiment_batch_size = sentiment_batch_size
        self.entailment_threshold = entailment_threshold
        self.aspect_dominance_ratio = aspect_dominance_ratio

        # fp16 halves activation/weight memory on GPU with negligible accuracy
        # loss for inference-only workloads; CPU stays in fp32 (no fp16 kernels).
        self._torch_dtype = torch.float16 if self.device == "cuda" else torch.float32

        self.aspect_tokenizer = AutoTokenizer.from_pretrained(ASPECT_MODEL_NAME)
        self.aspect_model = self._load_model(ASPECT_MODEL_NAME)

        self.sentiment_tokenizer = AutoTokenizer.from_pretrained(SENTIMENT_MODEL_NAME)
        self.sentiment_model = self._load_model(SENTIMENT_MODEL_NAME)

        # Resolve label indices dynamically from each model's config instead of
        # hardcoding 0/1, so the pipeline stays correct if either checkpoint is
        # swapped for one with a different id2label ordering.
        self._entailment_idx = self._find_label_index(
            self.aspect_model.config.id2label, include="entailment", exclude="not"
        )
        self._positive_idx = self._find_label_index(
            self.sentiment_model.config.id2label, include="positive"
        )
        self._negative_idx = self._find_label_index(
            self.sentiment_model.config.id2label, include="negative"
        )

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
        # CPU-only builds (even with enabled=False some torch versions warn
        # or raise), so CPU inference gets a plain nullcontext instead.
        if self.device == "cuda":
            return torch.autocast(device_type="cuda", dtype=torch.float16)
        return contextlib.nullcontext()

    # ------------------------------------------------------------------ #
    # OOM-safe batched forward pass
    # ------------------------------------------------------------------ #

    def _forward_probs(self, model, encoded: Dict[str, torch.Tensor]) -> torch.Tensor:
        """
        Run one padded batch through `model` and return softmax probabilities
        on CPU, shape (batch_size, num_labels).

        `encoded` tensors arrive on CPU and are only moved to the GPU inside
        this call. On CUDA OOM the batch is split in half along the batch
        dimension (dim 0) and each half is retried recursively, so a
        transient memory spike degrades throughput instead of crashing the
        whole job. Only a single 512-token row that cannot fit by itself
        re-raises, since that is a genuine capacity limit.
        """
        try:
            moved = {k: v.to(self.device) for k, v in encoded.items()}
            with self._autocast():
                logits = model(**moved).logits  # (batch_size, num_labels)
            # .float() upcasts fp16 logits before softmax for numerical
            # stability; .cpu() frees the GPU copy as soon as we return.
            return torch.softmax(logits.float(), dim=-1).cpu()
        except torch.cuda.OutOfMemoryError:
            batch_size = encoded["input_ids"].shape[0]
            if batch_size == 1:
                raise
            torch.cuda.empty_cache()
            half = batch_size // 2
            first = {k: v[:half] for k, v in encoded.items()}  # CPU slices
            second = {k: v[half:] for k, v in encoded.items()}
            return torch.cat(
                [
                    self._forward_probs(model, first),
                    self._forward_probs(model, second),
                ],
                dim=0,
            )

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

    @staticmethod
    def _split_clauses(text: str) -> List[str]:
        """
        Split review text into non-empty clauses: first on ./!/? sentence
        boundaries, then on contrastive conjunctions (but/however/although/...)
        within each sentence, so oppositely-valenced clauses about different
        aspects are never merged into one sentiment-scoring unit. Each clause
        is capped at MAX_CLAUSE_CHARS (see constant for rationale).
        """
        clauses: List[str] = []
        for sentence in _SENTENCE_SPLIT_RE.split(text.strip()):
            for clause in _CLAUSE_SPLIT_RE.split(sentence):
                clause = clause.strip()
                if clause:
                    clauses.append(clause[:MAX_CLAUSE_CHARS])
        return clauses

    def _build_aspect_pairs(self, texts: List[Optional[str]]) -> List[AspectPair]:
        """
        Flatten every usable review into (row_pos, clause_idx, aspect, clause)
        records — one per clause per candidate aspect — for batched
        entailment scoring. None entries (missing/unusable rows) are skipped
        entirely and yield [] downstream.

        The result is sorted by clause length so each DataLoader batch
        contains similar-length sequences: with dynamic padding, peak GPU
        memory per batch is set by the LONGEST sequence in it, so mixing one
        512-token clause into a batch of 10-token clauses would pad all 32
        rows to 512. Sorting makes short batches genuinely short. Correctness
        is unaffected because every record carries its own (row_pos, aspect)
        routing information.
        """
        pairs: List[AspectPair] = []
        for row_pos, text in enumerate(texts):
            if text is None:
                continue
            for clause_idx, clause in enumerate(self._split_clauses(text)):
                for aspect in ASPECT_HYPOTHESES:
                    pairs.append(AspectPair(row_pos, clause_idx, aspect, clause))
        pairs.sort(key=lambda p: len(p.clause))
        return pairs

    # ------------------------------------------------------------------ #
    # Stage 1: aspect detection via batched NLI entailment
    # ------------------------------------------------------------------ #

    @torch.inference_mode()
    def _run_aspect_detection(
        self, texts: List[Optional[str]]
    ) -> Dict[Tuple[int, str], List[Tuple[int, str]]]:
        """
        Returns {(row_pos, aspect): [(clause_idx, clause), ...]} containing
        only clauses that pass BOTH the absolute floor
        (`self.entailment_threshold`) and the per-clause relative dominance
        rule (`self.aspect_dominance_ratio`; see the constant's comment).
        Deciding per clause requires all of a clause's aspect scores, so
        probabilities are accumulated across batches first and thresholding
        happens afterwards (length-sorted batching gives no guarantee that a
        clause's three aspect pairs land in the same batch).
        """
        pairs = self._build_aspect_pairs(texts)
        assigned: Dict[Tuple[int, str], List[Tuple[int, str]]] = {}
        if not pairs:
            return assigned

        def collate(batch: List[AspectPair]):
            premises = [p.clause for p in batch]
            hypotheses = [ASPECT_HYPOTHESES[p.aspect] for p in batch]
            # tokenizer(text, text_pair, ...) packs premise+hypothesis into a
            # single [CLS] premise [SEP] hypothesis [SEP] sequence per row --
            # the standard NLI input format expected by this checkpoint.
            # truncation="only_first" trims ONLY the premise when over 512
            # tokens, so the aspect hypothesis is never cut off.
            encoded = self.aspect_tokenizer(
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
            batch_size=self.aspect_batch_size,
            shuffle=False,
            collate_fn=collate,
        )

        # Pass 1: accumulate every clause's per-aspect entailment probability.
        clause_probs: Dict[Tuple[int, int], Dict[str, float]] = {}
        clause_texts: Dict[Tuple[int, int], str] = {}
        for encoded, batch in loader:
            # input_ids / attention_mask shape: (batch_size, seq_len_in_batch)
            # -- seq_len is the max token length within this batch only,
            # since padding=True (dynamic padding) rather than a fixed 512.
            probs = self._forward_probs(self.aspect_model, encoded)
            entail_probs = probs[:, self._entailment_idx].tolist()  # (batch_size,)

            for pair, prob in zip(batch, entail_probs):
                key = (pair.row_pos, pair.clause_idx)
                clause_probs.setdefault(key, {})[pair.aspect] = prob
                clause_texts[key] = pair.clause

        # Pass 2: per clause, keep aspects that clear the absolute floor AND
        # score close enough to the clause's best aspect.
        for (row_pos, clause_idx), aspect_probs in clause_probs.items():
            dominance_floor = self.aspect_dominance_ratio * max(aspect_probs.values())
            for aspect, prob in aspect_probs.items():
                if prob >= self.entailment_threshold and prob >= dominance_floor:
                    assigned.setdefault((row_pos, aspect), []).append(
                        (clause_idx, clause_texts[(row_pos, clause_idx)])
                    )

        return assigned

    # ------------------------------------------------------------------ #
    # Stage 2: aspect-level sentiment scoring via batched sentiment model
    # ------------------------------------------------------------------ #

    @torch.inference_mode()
    def _run_sentiment_scoring(
        self, assigned: Dict[Tuple[int, str], List[Tuple[int, str]]]
    ) -> Dict[Tuple[int, str], float]:
        """
        For each (row_pos, aspect) key, concatenate its qualifying clauses in
        original reading order and score sentiment in [-1.0, +1.0] as
        P(positive) - P(negative).
        """
        items = [
            SentimentItem(
                row_pos=row_pos,
                aspect=aspect,
                # Sort by clause_idx to restore reading order (length-sorted
                # batching in stage 1 scrambled it).
                text=" ".join(clause for _, clause in sorted(clauses)),
            )
            for (row_pos, aspect), clauses in assigned.items()
        ]
        # Same length-sorted batching rationale as _build_aspect_pairs.
        items.sort(key=lambda it: len(it.text))
        scores: Dict[Tuple[int, str], float] = {}
        if not items:
            return scores

        def collate(batch: List[SentimentItem]):
            texts = [item.text for item in batch]
            encoded = self.sentiment_tokenizer(
                texts,
                truncation=True,
                max_length=MAX_SEQUENCE_LENGTH,
                padding=True,
                return_tensors="pt",
            )
            return dict(encoded), batch

        loader = DataLoader(
            ListDataset(items),
            batch_size=self.sentiment_batch_size,
            shuffle=False,
            collate_fn=collate,
        )

        for encoded, batch in loader:
            # input_ids / attention_mask shape: (batch_size, seq_len_in_batch)
            probs = self._forward_probs(self.sentiment_model, encoded)  # (batch_size, 2)
            pos = probs[:, self._positive_idx]  # (batch_size,)
            neg = probs[:, self._negative_idx]  # (batch_size,)
            # pos - neg is bounded in [-1.0, +1.0]; probability mass on the
            # model's "neutral" class shrinks the magnitude toward 0, which
            # is exactly the desired behavior for weakly-opinionated text.
            polarity = (pos - neg).tolist()

            for item, score in zip(batch, polarity):
                scores[(item.row_pos, item.aspect)] = round(float(score), 4)

        return scores

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def analyze(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run the full ABSA pipeline over `df['review_text']` and return a copy
        of `df` with a new 'absa_results' column containing, per row, a list
        of {"aspect": str, "sentiment": float} dicts (empty list if the row
        is NaN/empty/unusable or no aspect was detected).
        """
        if "review_text" not in df.columns:
            raise ValueError("Input DataFrame must contain a 'review_text' column.")

        # Everything below is positional (0..n-1). Index labels are never
        # used for routing, so duplicate labels (e.g. after pd.concat without
        # ignore_index) can neither crash .at[] nor merge unrelated rows.
        texts = [self._coerce_text(v) for v in df["review_text"].tolist()]
        # One result slot per row, pre-filled with []: guarantees well-formed
        # output (never NaN/missing) for every row, including unusable input.
        results: List[List[dict]] = [[] for _ in texts]

        try:
            assigned = self._run_aspect_detection(texts)
            scores = self._run_sentiment_scoring(assigned)

            for (row_pos, aspect), score in scores.items():
                results[row_pos].append({"aspect": aspect, "sentiment": score})
            # Deterministic aspect ordering within each row's result list.
            for row in results:
                row.sort(key=lambda d: _ASPECT_ORDER[d["aspect"]])
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
        return result_df


# --------------------------------------------------------------------------- #
# Sample execution
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import os

    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data.csv")
    df = pd.read_csv(csv_path)

    analyzer = ClinicalABSAAnalyzer()
    result = analyzer.analyze(df)

    pd.set_option("display.max_colwidth", None)
    for i, row in result.iterrows():
        print(f"\n[Row {i}] {row['review_text']!r}")
        print(f"  absa_results = {row['absa_results']}")
