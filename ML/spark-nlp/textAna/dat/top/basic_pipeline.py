"""
basic_pipeline.py
-----------------
Dual-use module:
  • Imported in the notebook  → use build_basic_pipeline() / run_basic_pipeline()
  • Submitted to SageMaker   → run as __main__ via PySparkProcessor

SageMaker Processing Job I/O
-----------------------------
  Input  : /opt/ml/processing/input   (lemmatised parquet from lem_ana job)
  Output : /opt/ml/processing/output/data

Basic NLP pipeline stages
--------------------------
  DocumentAssembler → Tokenizer → Normalizer → LemmatizerModel
  → StopWordsCleaner → PerceptronModel (pos_anc)
  → NGramGenerator  → Finisher

CLI argument (optional)
------------------------
  sys.argv[1]  text column to process  (default: "aspects_text")
"""

import os, sys, subprocess, glob, shutil, traceback


# ══════════════════════════════════════════════════════════════════════════════
# Module-level functions  (importable from the notebook)
# All sparknlp imports are deferred inside functions so the module can be
# imported even before sparknlp is pip-installed (SageMaker container case).
# ══════════════════════════════════════════════════════════════════════════════

def build_basic_pipeline(text_col: str, stopwords: list = None):
    """
    Construct the basic NLP Pipeline.

    Parameters
    ----------
    text_col  : input string column name
    stopwords : custom stop-word list; downloads NLTK English list if None

    Returns
    -------
    pyspark.ml.Pipeline
    """
    import nltk
    from sparknlp.base     import DocumentAssembler, Finisher
    from sparknlp.annotator import (
        Tokenizer, Normalizer, LemmatizerModel,
        StopWordsCleaner, NGramGenerator, PerceptronModel,
    )
    from pyspark.ml import Pipeline

    if stopwords is None:
        nltk.download("popular", quiet=True)
        stopwords = nltk.corpus.stopwords.words("english")

    documentAssembler = (
        DocumentAssembler()
        .setInputCol(text_col)
        .setOutputCol("document")
    )
    tokenizer = (
        Tokenizer()
        .setInputCols(["document"])
        .setOutputCol("tokenized")
    )
    normalizer = (
        Normalizer()
        .setInputCols(["tokenized"])
        .setOutputCol("normalized")
        .setLowercase(True)
    )
    lemmatizer = (
        LemmatizerModel.pretrained()
        .setInputCols(["normalized"])
        .setOutputCol("lemmatized")
    )
    stopwords_cleaner = (
        StopWordsCleaner()
        .setInputCols(["lemmatized"])
        .setOutputCol("unigrams")
        .setStopWords(stopwords)
    )
    pos_tagger = (
        PerceptronModel.pretrained("pos_anc")
        .setInputCols(["document", "lemmatized"])
        .setOutputCol("pos")
    )
    ngrammer = (
        NGramGenerator()
        .setInputCols(["lemmatized"])
        .setOutputCol("ngrams")
        .setN(3)
        .setEnableCumulative(True)
        .setDelimiter("_")
    )
    finisher = (
        Finisher()
        .setInputCols(["unigrams", "ngrams", "pos"])
    )

    return Pipeline().setStages([
        documentAssembler,
        tokenizer,
        normalizer,
        lemmatizer,
        stopwords_cleaner,
        pos_tagger,
        ngrammer,
        finisher,
    ])


def run_basic_pipeline(df, text_col: str, stopwords: list = None):
    """
    Fit and transform *df* through the basic NLP pipeline.

    ``finished_pos`` is converted from array → space-joined string so it
    can be fed directly into pos_pipeline.run_pos_pipeline().

    Parameters
    ----------
    df        : pyspark.sql.DataFrame  containing *text_col*
    text_col  : input column name
    stopwords : optional custom stop-word list

    Returns
    -------
    pyspark.sql.DataFrame  with finished_unigrams, finished_ngrams,
                           finished_pos (space-joined string)
    """
    from pyspark.sql import functions as F
    from pyspark.sql import types as T

    pipeline  = build_basic_pipeline(text_col, stopwords=stopwords)
    processed = pipeline.fit(df).transform(df)

    udf_join_arr = F.udf(lambda x: " ".join(x), T.StringType())
    processed = processed.withColumn(
        "finished_pos", udf_join_arr(F.col("finished_pos"))
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
         "spark-nlp==5.5.3", "nltk", "pandas<2.0"],
        capture_output=True, text=True,
    )
    print(f"pip exit={pip_result.returncode}", flush=True)
    if pip_result.returncode != 0:
        print("pip stderr:", pip_result.stderr[-3000:], flush=True)

    try:
        import nltk
        import sparknlp
        from pyspark.sql import SparkSession
        from pyspark.sql import functions as F
        from pyspark.sql import types as T
        from pyspark.sql.functions import concat_ws
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

    # ── Text column (first CLI arg, default "aspects_text") ──────────────────
    TEXT_COL = sys.argv[1] if len(sys.argv) > 1 else "aspects_text"
    print(f"TEXT_COL : {TEXT_COL}", flush=True)

    # ── Start Spark ───────────────────────────────────────────────────────────
    try:
        spark = (
            SparkSession.builder
            .appName("SparkNLP-BasicPipeline")
            .config("spark.jsl.settings.pretrained.cache_folder", CACHE_DIR)
            .getOrCreate()
        )
        print(f"Spark {spark.version} started", flush=True)
    except Exception:
        print("SPARKSESSION ERROR:", flush=True)
        traceback.print_exc()
        sys.exit(1)

    # ── Read input parquet (file://) ──────────────────────────────────────────
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

    # ── Flatten lemmatised keyword arrays → text strings ─────────────────────
    def join_keywords(df, src_col, out_col):
        return df.withColumn(
            out_col,
            F.when(
                F.col(src_col).isNull() | (F.size(F.col(src_col)) == 0),
                F.lit(None).cast(T.StringType()),
            ).otherwise(concat_ws(" ", F.col(src_col)))
        )

    df = join_keywords(df, "lemmatized_keywords_aspects",     "aspects_text")
    df = join_keywords(df, "lemmatized_keywords_suggestions", "suggestions_text")

    df_clean = df.filter(F.col(TEXT_COL).isNotNull())
    print(f"Non-null rows for '{TEXT_COL}': {df_clean.count()}", flush=True)

    # ── NLTK stop-words ───────────────────────────────────────────────────────
    nltk.download("popular", quiet=True)
    stopwords_list = nltk.corpus.stopwords.words("english")

    # ── Run basic pipeline ────────────────────────────────────────────────────
    print("Running basic NLP pipeline ...", flush=True)
    processed = run_basic_pipeline(df_clean, text_col=TEXT_COL, stopwords=stopwords_list)
    print(f"Output columns: {processed.columns}", flush=True)

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
