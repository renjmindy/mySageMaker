"""
lda_pipeline.py
---------------
SageMaker PySparkProcessor script — CountVectorizer → IDF → LDA.

No Spark-NLP required; plain PySpark only.

SageMaker Processing Job I/O
-----------------------------
  Input  : /opt/ml/processing/input   (parquet from pos_pipeline job)
  Output : /opt/ml/processing/output/data/
              term_frequency/   parquet  term, frequency
              topic_cloud/      parquet  topic, term, termWeights
              topic_scores/     parquet  reviewText, topicNo, wordCount
              topic_words/      parquet  topic, topicWords (array<string>)
              vocab.json        JSON     vocabulary list

CLI arguments (optional)
------------------------
  sys.argv[1]  text column used as reviewText  (default: "aspects_text")
  sys.argv[2]  number of LDA topics            (default: 20)
  sys.argv[3]  LDA max iterations              (default: 10)
"""

import os, sys, subprocess, glob, shutil, json, traceback


if __name__ == "__main__":

    # ── Early diagnostics ────────────────────────────────────────────────────
    print("=" * 60, flush=True)
    print(f"Python  : {sys.version}", flush=True)
    print(f"CWD     : {os.getcwd()}", flush=True)
    print("=" * 60, flush=True)

    # ── Install deps (no spark-nlp needed) ───────────────────────────────────
    pip_result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "pandas<2.0"],
        capture_output=True, text=True,
    )
    print(f"pip exit={pip_result.returncode}", flush=True)
    if pip_result.returncode != 0:
        print("pip stderr:", pip_result.stderr[-3000:], flush=True)

    try:
        import numpy as np
        from pyspark.sql import SparkSession, Row
        from pyspark.sql import functions as F
        from pyspark.sql import types as T
        from pyspark.ml.clustering import LDA
        from pyspark.ml.linalg import DenseVector
        from pyspark.ml.feature import CountVectorizer, IDF
        from pyspark.sql.functions import (
            trim, monotonically_increasing_id, explode, concat_ws,
        )
        print("Imports OK", flush=True)
    except Exception:
        print("IMPORT ERROR:", flush=True)
        traceback.print_exc()
        sys.exit(1)

    # ── Paths ─────────────────────────────────────────────────────────────────
    INPUT_DIR  = "/opt/ml/processing/input"
    OUTPUT_DIR = "/opt/ml/processing/output"

    # ── CLI args ──────────────────────────────────────────────────────────────
    TEXT_COL   = sys.argv[1] if len(sys.argv) > 1 else "aspects_text"
    NUM_TOPICS = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    MAX_ITER   = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    print(f"TEXT_COL={TEXT_COL}  NUM_TOPICS={NUM_TOPICS}  MAX_ITER={MAX_ITER}", flush=True)

    # ── Start Spark (plain PySpark — no Spark-NLP) ────────────────────────────
    try:
        spark = (
            SparkSession.builder
            .appName("TopAna-LDA")
            .config("spark.driver.memory", "16G")
            .config("spark.driver.maxResultSize", "4000M")
            .config("spark.executor.memory", "20G")
            .getOrCreate()
        )
        print(f"Spark {spark.version} started", flush=True)
    except Exception:
        traceback.print_exc()
        sys.exit(1)

    # ── Read pos_pipeline output ──────────────────────────────────────────────
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

    # ── Vectorization ─────────────────────────────────────────────────────────
    print("Fitting CountVectorizer ...", flush=True)
    tfizer    = CountVectorizer(inputCol="final", outputCol="tf_features")
    tf_model  = tfizer.fit(df)
    tf_result = tf_model.transform(df)

    print("Fitting IDF ...", flush=True)
    idfizer      = IDF(inputCol="tf_features", outputCol="tf_idf_features")
    idf_model    = idfizer.fit(tf_result)
    tfidf_result = idf_model.transform(tf_result)

    vocab = tf_model.vocabulary
    print(f"Vocabulary size: {len(vocab)}", flush=True)

    # ── LDA ───────────────────────────────────────────────────────────────────
    print(f"Fitting LDA (k={NUM_TOPICS}, maxIter={MAX_ITER}) ...", flush=True)
    lda       = LDA(k=NUM_TOPICS, maxIter=MAX_ITER, featuresCol="tf_idf_features")
    lda_model = lda.fit(tfidf_result)

    lda_topics_df = lda_model.describeTopics(NUM_TOPICS)
    print("LDA done.", flush=True)

    # ── Build output DataFrames ───────────────────────────────────────────────

    # 1. topic_words
    udf_to_words = F.udf(
        lambda idxs: [vocab[i] for i in idxs],
        T.ArrayType(T.StringType())
    )
    topic_words_df = (
        lda_model
        .describeTopics(NUM_TOPICS)
        .withColumn("topicWords", udf_to_words(F.col("termIndices")))
        .select("topic", "topicWords")
    )

    # 2. topic_cloud
    explode_indices = (
        lda_topics_df
        .select(lda_topics_df.topic, explode(lda_topics_df.termIndices))
        .withColumnRenamed("col", "termIndices")
        .withColumn("id", monotonically_increasing_id())
    )
    explode_terms = (
        explode_indices.rdd
        .map(lambda x: Row(topic=x["topic"], term=vocab[x["termIndices"]], id=x["id"]))
        .toDF()
    )
    explode_weights = (
        lda_topics_df
        .select(explode(lda_topics_df.termWeights))
        .withColumnRenamed("col", "termWeights")
        .withColumn("id", monotonically_increasing_id())
    )
    topic_cloud_df = (
        explode_terms
        .join(explode_weights, "id", "outer")
        .drop("id")
        .orderBy("topic")
    )

    # 3. term_frequency
    vocab_freq = (
        tfidf_result
        .select("finished_unigrams")
        .rdd.flatMap(lambda x: x[0])
        .toDF(schema=T.StringType())
        .toDF("term")
        .rdd.countByValue()
    )
    term_frequency_df = spark.createDataFrame(
        [Row(term=t[0], frequency=int(f)) for t, f in vocab_freq.items()],
    ).orderBy("frequency", ascending=False)

    # 4. topic_scores  (reviewText, topicNo, wordCount)
    def find_topic(v):
        arr = v.toArray()
        return int(np.argmax(arr)) if arr.sum() > 0 else None

    udf_topic     = F.udf(find_topic, T.IntegerType())
    topic_scores  = lda_model.transform(tfidf_result)
    topic_scores  = topic_scores.withColumn("topicNo", udf_topic(F.col("topicDistribution")))
    topic_scores  = topic_scores.filter(F.col("topicNo") >= 0)
    topic_scores_with_counts = topic_scores.withColumn(
        "wordCount",
        F.when(
            F.col(TEXT_COL).isNotNull() & (F.length(trim(F.col(TEXT_COL))) > 0),
            F.size(F.split(trim(F.col(TEXT_COL)), r"\s+"))
        ).otherwise(0)
    ).select(TEXT_COL, "topicNo", "wordCount").withColumnRenamed(TEXT_COL, "reviewText")

    # ── Write all outputs via /tmp then copy to output mount ──────────────────
    TMP_BASE = "/tmp/lda_output"
    OUT_DATA = os.path.join(OUTPUT_DIR, "data")
    if os.path.exists(TMP_BASE):
        shutil.rmtree(TMP_BASE)
    os.makedirs(TMP_BASE, exist_ok=True)
    os.makedirs(OUT_DATA, exist_ok=True)

    def write_parquet(df, name):
        tmp = os.path.join(TMP_BASE, name)
        df.coalesce(1).write.mode("overwrite").parquet("file://" + tmp)
        dst = os.path.join(OUT_DATA, name)
        shutil.copytree(tmp, dst)
        print(f"  Written {name}", flush=True)

    write_parquet(topic_words_df,             "topic_words")
    write_parquet(topic_cloud_df,             "topic_cloud")
    write_parquet(term_frequency_df,          "term_frequency")
    write_parquet(topic_scores_with_counts,   "topic_scores")

    # vocab as JSON
    vocab_path = os.path.join(OUT_DATA, "vocab.json")
    with open(vocab_path, "w") as vf:
        json.dump(vocab, vf)
    print("  Written vocab.json", flush=True)

    print(f"\nAll outputs ready at: {OUT_DATA}", flush=True)
    spark.stop()
    print("Done.", flush=True)
