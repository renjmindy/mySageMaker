"""
Spark-NLP lemmatisation processing script.
Executed inside a SageMaker PySparkProcessor container via spark-submit.

Reads the YAKE keyword columns produced by key_yake_ner_sagemaker.ipynb:
  yake_keywords_aspects      -> lemmatized_keywords_aspects
  yake_keywords_suggestions  -> lemmatized_keywords_suggestions

All intermediate I/O uses file:// (no HDFS).
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
    from sparknlp.annotator import Tokenizer, LemmatizerModel
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

# ── Pretrained model cache → /tmp (writable inside container) ────────────────
CACHE_DIR = "/tmp/sparknlp_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# ── Start Spark ───────────────────────────────────────────────────────────────
try:
    spark = (
        SparkSession.builder
        .appName("SparkNLP-LemAna")
        .config("spark.jsl.settings.pretrained.cache_folder", CACHE_DIR)
        .getOrCreate()
    )
    print(f"Spark {spark.version} started", flush=True)
except Exception:
    print("SPARKSESSION ERROR:", flush=True)
    traceback.print_exc()
    sys.exit(1)

# ── Read input parquet (file://) ─────────────────────────────────────────────
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

# ── Columns to lemmatise (array<string> → array<string>) ─────────────────────
COLS = {
    "yake_keywords_aspects":     "lemmatized_keywords_aspects",
    "yake_keywords_suggestions": "lemmatized_keywords_suggestions",
}
missing = [c for c in COLS if c not in spark_df.columns]
if missing:
    raise ValueError(
        f"Expected columns {list(COLS)} not found. "
        f"Available: {spark_df.columns}"
    )
print(f"Will lemmatise columns: {list(COLS.keys())}", flush=True)

# ── Load lemmatiser once (shared across both columns) ─────────────────────────
print("Loading LemmatizerModel (lemma_antbnc, en) ...", flush=True)
lemmatizer = (
    LemmatizerModel.pretrained("lemma_antbnc", "en")
    .setInputCols(["token"])
    .setOutputCol("lemma")
)
print("LemmatizerModel loaded.", flush=True)

# ── Build pipeline ────────────────────────────────────────────────────────────
def build_lemma_pipeline(input_col: str) -> Pipeline:
    """
    Expects input_col to be a plain string column.
    Returns a Pipeline: DocumentAssembler -> Tokenizer -> LemmatizerModel.
    """
    doc = (
        DocumentAssembler()
        .setInputCol(input_col)
        .setOutputCol("document")
        .setCleanupMode("shrink")
    )
    tok = (
        Tokenizer()
        .setInputCols(["document"])
        .setOutputCol("token")
    )
    return Pipeline(stages=[doc, tok, lemmatizer])

# ── Process each column ───────────────────────────────────────────────────────
result_df = spark_df
for src_col, out_col in COLS.items():
    print(f"  Lemmatising: {src_col} -> {out_col}", flush=True)

    # Flatten array<string> to a single whitespace-joined string
    tmp_col = "_lem_input"
    working_df = result_df.withColumn(
        tmp_col,
        F.when(
            F.col(src_col).isNull() | (F.size(F.col(src_col)) == 0),
            F.lit("")
        ).otherwise(
            F.concat_ws(" ", F.col(src_col))
        )
    )

    pipeline = build_lemma_pipeline(tmp_col)
    # Fit on a tiny dummy frame so the pipeline is stateless
    dummy = spark.createDataFrame([[""]], [tmp_col])
    model = pipeline.fit(dummy)
    transformed = model.transform(working_df)

    # Collect lemmatised tokens back into an array, dedup
    result_df = (
        transformed
        .withColumn(out_col, F.array_distinct(F.col("lemma.result")))
        .drop("document", "token", "lemma", tmp_col)
    )
    print(f"    Done.", flush=True)

# ── Select original columns + new lemma columns in order ─────────────────────
output_cols = spark_df.columns + list(COLS.values())
output_df   = result_df.select(output_cols)

print(f"Output : {output_df.count()} rows, columns: {output_df.columns}", flush=True)

# ── Write to /tmp first, then copy to output mount (file://) ─────────────────
# Spark's overwrite mode deletes the target directory before writing.
# The SageMaker bind-mount blocks that delete, so we write to /tmp and
# copy the resulting parquet files manually.
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
