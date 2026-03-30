"""
sentiment_pipeline.py
---------------------
Dual-use module:
  • Imported in the notebook  → use build_sentiment_pipeline() / run_sentiment_pipeline()
  • Submitted to SageMaker   → run as __main__ via PySparkProcessor

SageMaker Processing Job I/O
-----------------------------
  Input  : /opt/ml/processing/input   (parquet pre-converted from xlsx)
  Output : /opt/ml/processing/output/data

Sentiment NLP pipeline stages
------------------------------
  DocumentAssembler → SentenceDetector → Tokenizer → Normalizer
  → Lemmatizer → StopWordsCleaner → SentimentDetector → Finisher
  + VADER polarity UDF  (compound, pos, neg, neu)

CLI argument (optional)
------------------------
  sys.argv[1]  text column to process  (default: "text")
"""

import os, sys, subprocess, glob, shutil, traceback

LEMMA_URL      = "https://s3.amazonaws.com/auxdata.johnsnowlabs.com/public/resources/en/lemma-corpus-small/lemmas_small.txt"
SENTIMENT_URL  = "https://s3.amazonaws.com/auxdata.johnsnowlabs.com/public/resources/en/sentiment-corpus/default-sentiment-dict.txt"
LEMMA_LOCAL    = "/tmp/lemmas_small.txt"
SENTIMENT_LOCAL = "/tmp/default-sentiment-dict.txt"
# file:// prefix forces Spark-NLP's ResourceHelper (Hadoop FileSystem API) to use
# the local filesystem instead of resolving against the HDFS default FS.
LEMMA_PATH     = "file:///tmp/lemmas_small.txt"
SENTIMENT_PATH = "file:///tmp/default-sentiment-dict.txt"


def _download_dicts():
    import urllib.request
    for url, local in [(LEMMA_URL, LEMMA_LOCAL), (SENTIMENT_URL, SENTIMENT_LOCAL)]:
        if not os.path.exists(local):
            print(f"Downloading {url} ...", flush=True)
            urllib.request.urlretrieve(url, local)
            print(f"  Saved to {local}", flush=True)
        else:
            print(f"  {local} already present", flush=True)
    return LEMMA_PATH, SENTIMENT_PATH


# ══════════════════════════════════════════════════════════════════════════════
# Module-level functions  (importable from the notebook)
# All sparknlp imports are deferred inside functions so the module can be
# imported even before sparknlp is pip-installed (SageMaker container case).
# ══════════════════════════════════════════════════════════════════════════════

def build_sentiment_pipeline(
    text_col: str,
    lemma_dict: str,
    sentiment_dict: str,
    stopwords: list = None,
):
    """
    Construct the Sentiment NLP Pipeline.

    Parameters
    ----------
    text_col       : input string column name
    lemma_dict     : local path to lemmas_small.txt
    sentiment_dict : local path to default-sentiment-dict.txt
    stopwords      : custom stop-word list; downloads NLTK English list if None

    Returns
    -------
    pyspark.ml.Pipeline
    """
    import nltk
    from sparknlp.base     import DocumentAssembler, Finisher
    from sparknlp.annotator import (
        SentenceDetector, Tokenizer, Normalizer,
        Lemmatizer, StopWordsCleaner, SentimentDetector,
    )
    from pyspark.ml import Pipeline

    if stopwords is None:
        nltk.download("popular", quiet=True)
        stopwords = nltk.corpus.stopwords.words("english")

    document_assembler = (
        DocumentAssembler()
        .setInputCol(text_col)
        .setOutputCol("document")
    )
    sentence_detector = (
        SentenceDetector()
        .setInputCols(["document"])
        .setOutputCol("sentence")
    )
    tokenizer = (
        Tokenizer()
        .setInputCols(["sentence"])
        .setOutputCol("token")
    )
    normalizer = (
        Normalizer()
        .setInputCols(["token"])
        .setOutputCol("normalized")
        .setLowercase(True)
    )
    lemmatizer = (
        Lemmatizer()
        .setInputCols(["normalized"])
        .setOutputCol("lemma")
        .setDictionary(lemma_dict, key_delimiter="->", value_delimiter="\t")
    )
    stopwords_cleaner = (
        StopWordsCleaner()
        .setInputCols(["lemma"])
        .setOutputCol("clean_lemma")
        .setStopWords(stopwords)
    )
    sentiment_detector = (
        SentimentDetector()
        .setInputCols(["lemma", "sentence"])
        .setOutputCol("sentiment_score")
        .setDictionary(sentiment_dict, ",")
    )
    finisher = (
        Finisher()
        .setInputCols(["sentiment_score", "clean_lemma"])
        .setOutputCols(["finished_sentiment", "finished_tokens"])
    )

    return Pipeline().setStages([
        document_assembler,
        sentence_detector,
        tokenizer,
        normalizer,
        lemmatizer,
        stopwords_cleaner,
        sentiment_detector,
        finisher,
    ])


def run_sentiment_pipeline(
    df,
    text_col: str,
    lemma_dict: str = None,
    sentiment_dict: str = None,
    stopwords: list = None,
):
    """
    Fit and transform *df* through the sentiment NLP pipeline.
    Also adds VADER polarity scores (compound, pos, neg, neu).

    Parameters
    ----------
    df             : pyspark.sql.DataFrame  containing *text_col*
    text_col       : input column name
    lemma_dict     : local path to lemmas_small.txt  (auto-downloaded if None)
    sentiment_dict : local path to default-sentiment-dict.txt (auto-downloaded if None)
    stopwords      : optional custom stop-word list

    Returns
    -------
    pyspark.sql.DataFrame  with finished_sentiment, finished_tokens,
                           sentiment_label, vader_compound, vader_pos,
                           vader_neg, vader_neu, vader_label
    """
    import nltk
    from pyspark.sql import functions as F
    from pyspark.sql import types as T

    if lemma_dict is None or sentiment_dict is None:
        lemma_dict, sentiment_dict = _download_dicts()

    nltk.download("vader_lexicon", quiet=True)
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    _analyzer = SentimentIntensityAnalyzer()

    @F.udf(T.MapType(T.StringType(), T.DoubleType()))
    def vader_udf(text):
        if text is None:
            return {"compound": 0.0, "pos": 0.0, "neg": 0.0, "neu": 1.0}
        import nltk
        nltk.download("vader_lexicon", quiet=True)
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        scores = SentimentIntensityAnalyzer().polarity_scores(text)
        return {k: float(v) for k, v in scores.items()}

    pipeline  = build_sentiment_pipeline(text_col, lemma_dict, sentiment_dict, stopwords=stopwords)
    processed = pipeline.fit(df).transform(df)

    processed = (
        processed
        .withColumn("vader_scores",   vader_udf(F.col(text_col)))
        .withColumn("vader_compound", F.col("vader_scores")["compound"])
        .withColumn("vader_pos",      F.col("vader_scores")["pos"])
        .withColumn("vader_neg",      F.col("vader_scores")["neg"])
        .withColumn("vader_neu",      F.col("vader_scores")["neu"])
        .drop("vader_scores")
        .withColumn(
            "sentiment_label",
            F.when(F.size(F.col("finished_sentiment")) > 0,
                   F.col("finished_sentiment")[0])
             .otherwise(F.lit("na"))
        )
        .withColumn(
            "vader_label",
            F.when(F.col("vader_compound") >= 0.05,  F.lit("positive"))
             .when(F.col("vader_compound") <= -0.05, F.lit("negative"))
             .otherwise(F.lit("neutral"))
        )
    )
    return processed


def run_multi_column_sentiment_pipeline(
    df,
    text_cols: list,
    lemma_dict: str = None,
    sentiment_dict: str = None,
    stopwords: list = None,
):
    """
    Run run_sentiment_pipeline() for each column in *text_cols*.
    Output columns are prefixed with the source column name, e.g.
      aspects_text  →  aspects_text_sentiment_label, aspects_text_vader_compound, …
      suggestions_text → suggestions_text_sentiment_label, …

    Parameters
    ----------
    df             : pyspark.sql.DataFrame
    text_cols      : list of input column names to analyse
    lemma_dict     : local path to lemmas_small.txt  (auto-downloaded if None)
    sentiment_dict : local path to default-sentiment-dict.txt (auto-downloaded if None)
    stopwords      : optional custom stop-word list

    Returns
    -------
    pyspark.sql.DataFrame  with original columns plus prefixed sentiment columns
                           for every text column requested
    """
    from pyspark.sql import functions as F

    if lemma_dict is None or sentiment_dict is None:
        lemma_dict, sentiment_dict = _download_dicts()

    # Stable join key
    df = df.withColumn("_row_id", F.monotonically_increasing_id())

    result = df
    _OUTPUT_COLS = [
        "finished_sentiment", "finished_tokens",
        "sentiment_label",
        "vader_compound", "vader_pos", "vader_neg", "vader_neu",
        "vader_label",
    ]

    for col_name in text_cols:
        print(f"Running sentiment pipeline on column: '{col_name}' ...", flush=True)
        processed = run_sentiment_pipeline(
            df, col_name,
            lemma_dict=lemma_dict,
            sentiment_dict=sentiment_dict,
            stopwords=stopwords,
        )
        # Keep only the join key + newly produced output columns
        slim = processed.select(
            "_row_id",
            *[F.col(c).alias(f"{col_name}_{c}") for c in _OUTPUT_COLS],
        )
        result = result.join(slim, on="_row_id", how="left")

    result = result.drop("_row_id")
    return result


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

    # ── Text columns (first CLI arg, comma-separated; default "aspects_text") ──
    TEXT_COLS = [c.strip() for c in sys.argv[1].split(",")] if len(sys.argv) > 1 else ["aspects_text"]
    print(f"TEXT_COLS : {TEXT_COLS}", flush=True)

    # ── Download resource dicts ───────────────────────────────────────────────
    lemma_dict, sentiment_dict = _download_dicts()

    # ── Start Spark ───────────────────────────────────────────────────────────
    try:
        spark = (
            SparkSession.builder
            .appName("SparkNLP-SentimentPipeline")
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

    # ── Clean text column ────────────────────────────────────────────────────
    @F.udf(T.StringType())
    def lower_clean_str(s):
        if s is None:
            return None
        punc = "!'\"#$&()*+,-./:;<=>?@[\\]^_`{|}~"
        lowercased = s.lower()
        for c in punc:
            lowercased = lowercased.replace(c, "")
        return lowercased.strip() or None

    for c in TEXT_COLS:
        if c in df.columns:
            df = df.withColumn(c, lower_clean_str(F.col(c)))
    # Filter rows where at least one text column is non-null/non-empty
    from functools import reduce
    filter_cond = reduce(
        lambda a, b: a | b,
        [F.col(c).isNotNull() & (F.trim(F.col(c)) != "") for c in TEXT_COLS
         if c in df.columns],
    )
    df_clean = df.filter(filter_cond)
    for c in TEXT_COLS:
        if c in df.columns:
            print(f"Non-null rows for '{c}': {df_clean.filter(F.col(c).isNotNull() & (F.trim(F.col(c)) != '')).count()}", flush=True)
        else:
            print(f"WARNING: column '{c}' not found in schema — skipping", flush=True)

    TEXT_COLS = [c for c in TEXT_COLS if c in df.columns]

    # ── NLTK stop-words ───────────────────────────────────────────────────────
    nltk.download("popular", quiet=True)
    stopwords_list = nltk.corpus.stopwords.words("english")

    # ── Run multi-column sentiment pipeline ───────────────────────────────────
    print(f"Running sentiment NLP pipeline on columns: {TEXT_COLS} ...", flush=True)
    processed = run_multi_column_sentiment_pipeline(
        df_clean,
        text_cols=TEXT_COLS,
        lemma_dict=lemma_dict,
        sentiment_dict=sentiment_dict,
        stopwords=stopwords_list,
    )
    print(f"Output columns: {processed.columns}", flush=True)
    for c in TEXT_COLS:
        processed.select(c, f"{c}_sentiment_label", f"{c}_vader_label",
                         f"{c}_vader_compound").show(10, truncate=80)

    # ── Write to /tmp first, then copy to output mount ────────────────────────
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
