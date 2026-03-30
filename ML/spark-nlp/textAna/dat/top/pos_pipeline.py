"""
pos_pipeline.py
---------------
Dual-use module:
  • Imported in the notebook  → use build_pos_pipeline() / run_pos_pipeline()
  • Submitted to SageMaker   → run as __main__ via PySparkProcessor

SageMaker Processing Job I/O
-----------------------------
  Input  : /opt/ml/processing/input   (parquet from basic_pipeline job)
  Output : /opt/ml/processing/output/data

Extended POS-tag n-gram pipeline stages
----------------------------------------
  DocumentAssembler → Tokenizer → NGramGenerator → Finisher

After the pipeline, filter_pos and filter_pos_combs are applied to produce:
  filtered_unigrams  – unigrams keeping POS tags in ['JJ','NN','NNS','VB','VBP']
  filtered_ngrams    – n-grams with valid POS-tag bigram/trigram sequences
  final              – filtered_unigrams + filtered_ngrams concatenated
"""

import os, sys, subprocess, glob, shutil, traceback


# ══════════════════════════════════════════════════════════════════════════════
# POS filter constants
# ══════════════════════════════════════════════════════════════════════════════

UNIGRAM_POS_TAGS = ["JJ", "NN", "NNS", "VB", "VBP"]


# ══════════════════════════════════════════════════════════════════════════════
# Module-level functions  (importable from the notebook)
# All sparknlp/pyspark imports are deferred inside functions.
# ══════════════════════════════════════════════════════════════════════════════

def filter_pos(words, pos_tags):
    """
    Keep unigrams whose POS tag is in UNIGRAM_POS_TAGS.

    Parameters
    ----------
    words    : list[str]  finished_unigrams
    pos_tags : list[str]  finished_pos  (array form, after pos_pipeline)
    """
    return [word for word, pos in zip(words, pos_tags)
            if pos in UNIGRAM_POS_TAGS]


def filter_pos_combs(words, pos_tags):
    """
    Keep bi-/trigrams whose POS-tag sequence matches valid combinations.

    Bigrams  : first  ∈ UNIGRAM_POS_TAGS  AND  second ∈ [JJ, NN, NNS]
    Trigrams : first  ∈ UNIGRAM_POS_TAGS  AND  second ∈ [JJ, NN, NNS, VB, VBP]
               AND  third ∈ [NN, NNS]

    Parameters
    ----------
    words    : list[str]  finished_ngrams
    pos_tags : list[str]  finished_pos_ngrams
    """
    return [word for word, pos in zip(words, pos_tags)
            if (len(pos.split("_")) == 2 and
                pos.split("_")[0] in ["JJ", "NN", "NNS", "VB", "VBP"] and
                pos.split("_")[1] in ["JJ", "NN", "NNS"])
            or (len(pos.split("_")) == 3 and
                pos.split("_")[0] in ["JJ", "NN", "NNS", "VB", "VBP"] and
                pos.split("_")[1] in ["JJ", "NN", "NNS", "VB", "VBP"] and
                pos.split("_")[2] in ["NN", "NNS"])]


def _get_udfs():
    """Return (udf_filter_pos, udf_filter_pos_combs) — deferred registration."""
    from pyspark.sql import functions as F
    from pyspark.sql import types as T
    udf_fp  = F.udf(filter_pos,       T.ArrayType(T.StringType()))
    udf_fpc = F.udf(filter_pos_combs, T.ArrayType(T.StringType()))
    return udf_fp, udf_fpc


# Convenience references (populated on first import in notebook env)
try:
    from pyspark.sql import functions as F
    from pyspark.sql import types as T
    udf_filter_pos       = F.udf(filter_pos,       T.ArrayType(T.StringType()))
    udf_filter_pos_combs = F.udf(filter_pos_combs, T.ArrayType(T.StringType()))
except Exception:
    udf_filter_pos = udf_filter_pos_combs = None


def build_pos_pipeline():
    """
    Construct the extended POS-tag n-gram Pipeline.

    Reads ``finished_pos`` (space-joined string from basic_pipeline) and
    produces ``finished_pos`` (array) and ``finished_pos_ngrams``.

    Returns
    -------
    pyspark.ml.Pipeline
    """
    from sparknlp.base     import DocumentAssembler, Finisher
    from sparknlp.annotator import Tokenizer, NGramGenerator
    from pyspark.ml import Pipeline

    pos_documentAssembler = (
        DocumentAssembler()
        .setInputCol("finished_pos")
        .setOutputCol("pos_document")
    )
    pos_tokenizer = (
        Tokenizer()
        .setInputCols(["pos_document"])
        .setOutputCol("pos")
    )
    pos_ngrammer = (
        NGramGenerator()
        .setInputCols(["pos"])
        .setOutputCol("pos_ngrams")
        .setN(3)
        .setEnableCumulative(True)
        .setDelimiter("_")
    )
    pos_finisher = (
        Finisher()
        .setInputCols(["pos", "pos_ngrams"])
    )

    return Pipeline().setStages([
        pos_documentAssembler,
        pos_tokenizer,
        pos_ngrammer,
        pos_finisher,
    ])


def run_pos_pipeline(df):
    """
    Fit and transform *df* through the extended POS n-gram pipeline,
    then apply filter_pos and filter_pos_combs to produce
    filtered_unigrams, filtered_ngrams, and final.

    Parameters
    ----------
    df : pyspark.sql.DataFrame
        Output of basic_pipeline.run_basic_pipeline().
        Must contain finished_pos (space-joined string),
        finished_unigrams, and finished_ngrams.

    Returns
    -------
    pyspark.sql.DataFrame
        Input columns plus filtered_unigrams, filtered_ngrams, final.
    """
    from pyspark.sql import functions as F

    udf_fp, udf_fpc = _get_udfs()

    pipeline  = build_pos_pipeline()
    processed = pipeline.fit(df).transform(df)

    processed = processed.withColumn(
        "filtered_unigrams",
        udf_fp(F.col("finished_unigrams"), F.col("finished_pos")),
    )
    processed = processed.withColumn(
        "filtered_ngrams",
        udf_fpc(F.col("finished_ngrams"), F.col("finished_pos_ngrams")),
    )
    processed = processed.withColumn(
        "final",
        F.concat(F.col("filtered_unigrams"), F.col("filtered_ngrams")),
    )
    return processed


# ══════════════════════════════════════════════════════════════════════════════
# SageMaker PySparkProcessor entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    # ── Early diagnostics ────────────────────────────────────────────────────
    print("=" * 60, flush=True)
    print(f"Python  : {sys.version}", flush=True)
    print(f"CWD     : {os.getcwd()}", flush=True)
    print("=" * 60, flush=True)

    # ── Install Python-side spark-nlp bindings (JAR loaded via --jars) ───────
    pip_result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q",
         "spark-nlp==5.5.3", "pandas<2.0"],
        capture_output=True, text=True,
    )
    print(f"pip exit={pip_result.returncode}", flush=True)
    if pip_result.returncode != 0:
        print("pip stderr:", pip_result.stderr[-3000:], flush=True)

    try:
        import sparknlp
        from pyspark.sql import SparkSession
        from pyspark.sql import functions as F
        from pyspark.sql import types as T
        print(f"Imports OK — spark-nlp {sparknlp.version()}", flush=True)
    except Exception:
        print("IMPORT ERROR:", flush=True)
        traceback.print_exc()
        sys.exit(1)

    # ── Paths ─────────────────────────────────────────────────────────────────
    INPUT_DIR  = "/opt/ml/processing/input"
    OUTPUT_DIR = "/opt/ml/processing/output"
    CACHE_DIR  = "/tmp/sparknlp_cache"
    os.makedirs(CACHE_DIR, exist_ok=True)

    # ── Start Spark ───────────────────────────────────────────────────────────
    try:
        spark = (
            SparkSession.builder
            .appName("SparkNLP-PosPipeline")
            .config("spark.jsl.settings.pretrained.cache_folder", CACHE_DIR)
            .getOrCreate()
        )
        print(f"Spark {spark.version} started", flush=True)
    except Exception:
        print("SPARKSESSION ERROR:", flush=True)
        traceback.print_exc()
        sys.exit(1)

    # ── Read input parquet (basic_pipeline output, file://) ──────────────────
    parquet_files = (
        glob.glob(os.path.join(INPUT_DIR, "**/*.parquet"), recursive=True)
        + glob.glob(os.path.join(INPUT_DIR, "*.parquet"))
    )
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found under {INPUT_DIR}")

    print(f"Reading parquet from: {INPUT_DIR}", flush=True)
    df = spark.read.parquet("file://" + INPUT_DIR)
    print(f"Input  : {df.count()} rows × {len(df.columns)} columns", flush=True)
    df.printSchema()

    # ── Re-register UDFs now that pyspark is available ───────────────────────
    udf_filter_pos       = F.udf(filter_pos,       T.ArrayType(T.StringType()))
    udf_filter_pos_combs = F.udf(filter_pos_combs, T.ArrayType(T.StringType()))

    # ── Run extended POS pipeline ─────────────────────────────────────────────
    print("Running extended POS pipeline ...", flush=True)
    processed = run_pos_pipeline(df)
    print(f"Output columns: {processed.columns}", flush=True)
    processed.select("filtered_unigrams", "filtered_ngrams", "final").show(5, truncate=80)

    # ── Write to /tmp first, then copy to output mount (file://) ─────────────
    TMP_PATH = "/tmp/spark_output"
    if os.path.exists(TMP_PATH):
        shutil.rmtree(TMP_PATH)

    processed.coalesce(1).write.mode("overwrite").parquet("file://" + TMP_PATH)
    print(f"Written to tmp: {TMP_PATH}", flush=True)

    out_dir = os.path.join(OUTPUT_DIR, "data")
    os.makedirs(out_dir, exist_ok=True)
    for fname in os.listdir(TMP_PATH):
        src = os.path.join(TMP_PATH, fname)
        dst = os.path.join(out_dir, fname)
        shutil.copy2(src, dst)
        print(f"  Copied {fname} -> {dst}", flush=True)

    print(f"Output ready at: {out_dir}", flush=True)
    spark.stop()
    print("Done.", flush=True)
