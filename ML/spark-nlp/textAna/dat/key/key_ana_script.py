"""
Spark-NLP YAKE! keyword extraction processing script.
Executed inside a SageMaker PySparkProcessor container via spark-submit.

Processes two redacted text columns:
  - redacted_aspects      -> yake_keywords_aspects
  - redacted_suggestions  -> yake_keywords_suggestions
"""
import os, sys, subprocess, glob, shutil, traceback

# ── Early diagnostics ─────────────────────────────────────────────────────────
print("=" * 60, flush=True)
print(f"Python  : {sys.version}", flush=True)
print(f"CWD     : {os.getcwd()}", flush=True)
print("=" * 60, flush=True)

# ── Install Python-side spark-nlp bindings (JAR loaded via --jars) ────────────
pip_result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "spark-nlp==5.5.3", "pandas<2.0"],
    capture_output=True, text=True,
)
print(f"pip exit={pip_result.returncode}", flush=True)
if pip_result.returncode != 0:
    print("pip stderr:", pip_result.stderr[-3000:], flush=True)

try:
    import sparknlp
    from sparknlp.base import DocumentAssembler
    from sparknlp.annotator import SentenceDetector, Tokenizer, YakeKeywordExtraction
    from pyspark.ml import Pipeline
    from pyspark.sql import SparkSession
    import pyspark.sql.functions as F
    print(f"Imports OK — spark-nlp {sparknlp.version()}", flush=True)
except Exception:
    print("IMPORT ERROR:", flush=True)
    traceback.print_exc()
    sys.exit(1)

INPUT_DIR  = "/opt/ml/processing/input"
OUTPUT_DIR = "/opt/ml/processing/output"

# ── Start Spark ───────────────────────────────────────────────────────────────
try:
    spark = SparkSession.builder.appName("SparkNLP-KeyAna").getOrCreate()
    print(f"Spark {spark.version} started", flush=True)
except Exception:
    print("SPARKSESSION ERROR:", flush=True)
    traceback.print_exc()
    sys.exit(1)

# ── Read input parquet ────────────────────────────────────────────────────────
parquet_files = (
    glob.glob(os.path.join(INPUT_DIR, "**/*.parquet"), recursive=True)
    + glob.glob(os.path.join(INPUT_DIR, "*.parquet"))
)
if not parquet_files:
    raise FileNotFoundError(f"No parquet files found under {INPUT_DIR}")

print(f"Reading parquet from: {INPUT_DIR}", flush=True)
spark_df = spark.read.parquet("file://" + INPUT_DIR)
print(f"Input  : {spark_df.count()} rows × {len(spark_df.columns)} columns", flush=True)
spark_df.printSchema()

# ── Columns to extract keywords from ──────────────────────────────────────────
TEXT_COLS = {
    "redacted_aspects":     "yake_keywords_aspects",
    "redacted_suggestions": "yake_keywords_suggestions",
}
missing = [c for c in TEXT_COLS if c not in spark_df.columns]
if missing:
    raise ValueError(
        f"Expected columns {list(TEXT_COLS)} not found. "
        f"Available: {spark_df.columns}"
    )
print(f"Will extract keywords from: {list(TEXT_COLS.keys())}", flush=True)

# ── Build YAKE! pipeline ──────────────────────────────────────────────────────
def build_yake_pipeline(input_col: str) -> Pipeline:
    doc = (
        DocumentAssembler()
        .setInputCol(input_col)
        .setOutputCol("document")
    )
    sent = (
        SentenceDetector()
        .setInputCols(["document"])
        .setOutputCol("sentence")
    )
    tok = (
        Tokenizer()
        .setInputCols(["sentence"])
        .setOutputCol("token")
    )
    yake = (
        YakeKeywordExtraction()
        .setInputCols(["token"])
        .setOutputCol("keywords")
        .setMinNGrams(1)
        .setMaxNGrams(3)
        .setNKeywords(30)
        .setThreshold(1.5)
        .setWindowSize(3)
    )
    return Pipeline(stages=[doc, sent, tok, yake])

result_df = spark_df
for src_col, out_col in TEXT_COLS.items():
    print(f"  Processing column: {src_col} -> {out_col}", flush=True)
    working_df = result_df.withColumn("_text_input", F.col(src_col))
    pipeline = build_yake_pipeline("_text_input")
    empty_fit = spark.createDataFrame([[""]], ["_text_input"])
    model = pipeline.fit(empty_fit)
    transformed = model.transform(working_df)
    result_df = transformed.withColumn(
        out_col, F.array_distinct(F.col("keywords.result"))
    ).drop("document", "sentence", "token", "keywords", "_text_input")
    print(f"    Done.", flush=True)

# ── Select original columns + new keyword columns ─────────────────────────────
output_cols = spark_df.columns + list(TEXT_COLS.values())
output_df   = result_df.select(output_cols)

print(f"Output : {output_df.count()} rows, columns: {output_df.columns}", flush=True)

# ── Write output parquet ──────────────────────────────────────────────────────
# The SageMaker bind-mount at /opt/ml/processing/output blocks Java FileSystem
# delete operations (including Spark's overwrite-mode pre-delete). Work around:
# 1. Write to /tmp (unrestricted) via Spark.
# 2. Copy the resulting parquet files to the output mount using Python shutil.
# SageMaker will then upload /opt/ml/processing/output/data -> OUTPUT_S3.

TMP_PATH = "/tmp/spark_output"
if os.path.exists(TMP_PATH):
    shutil.rmtree(TMP_PATH)

output_df.coalesce(1).write.mode("overwrite").parquet("file://" + TMP_PATH)
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
