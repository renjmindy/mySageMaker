"""
Spark-NLP de-identification processing script.
Executed inside a SageMaker PySparkProcessor container via spark-submit.
Models are pre-staged on S3 and mounted into /opt/ml/processing/models/.
"""
import os, sys, subprocess, glob, traceback, zipfile

# ── Early diagnostics (always visible in CloudWatch) ─────────────────────────
print("=" * 60, flush=True)
print(f"Python  : {sys.version}", flush=True)
print(f"CWD     : {os.getcwd()}", flush=True)
print(f"PATH    : {os.environ.get('PATH','')}", flush=True)
print("=" * 60, flush=True)

# ── Install Python-side bindings (JVM JAR is loaded via --jars) ───────────────
pip_result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "spark-nlp==5.5.3", "openpyxl", "pandas<2.0"],
    capture_output=True, text=True,
)
print(f"pip exit={pip_result.returncode}", flush=True)
if pip_result.returncode != 0:
    print("pip stdout:", pip_result.stdout[-3000:], flush=True)
    print("pip stderr:", pip_result.stderr[-3000:], flush=True)

try:
    import sparknlp
    from sparknlp.base import DocumentAssembler
    from sparknlp.annotator import Tokenizer, WordEmbeddingsModel, NerDLModel, NerConverter
    from pyspark.ml import Pipeline
    from pyspark.sql import SparkSession
    import pyspark.sql.functions as F
    import pandas as pd
    print(f"Imports OK — spark-nlp {sparknlp.version()}", flush=True)
    print(f"pandas  {pd.__version__}", flush=True)
except Exception:
    print("IMPORT ERROR:", flush=True)
    traceback.print_exc()
    sys.exit(1)

INPUT_DIR  = "/opt/ml/processing/input"
MODELS_DIR = "/opt/ml/processing/models"
OUTPUT_DIR = "/opt/ml/processing/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Unzip pre-staged models ───────────────────────────────────────────────────
LOCAL_MODELS = "/tmp/sparknlp_models"
os.makedirs(LOCAL_MODELS, exist_ok=True)

# SageMaker mounts each ProcessingInput source into a directory;
# the zip file lands inside that directory (not at the path itself).
for model_name, mount_subdir in [("glove_100d", "glove"), ("ner_dl", "ner")]:
    mount_dir = os.path.join(MODELS_DIR, mount_subdir)
    zips = glob.glob(os.path.join(mount_dir, "*.zip"))
    if not zips:
        raise FileNotFoundError(f"No zip found in {mount_dir}; contents: {os.listdir(mount_dir)}")
    zip_path  = zips[0]
    dest_path = os.path.join(LOCAL_MODELS, model_name)
    if not os.path.exists(dest_path):
        print(f"Unzipping {zip_path} → {dest_path}", flush=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest_path)
    print(f"  {model_name}: {os.listdir(dest_path)[:3]}", flush=True)

GLOVE_PATH = "file://" + os.path.join(LOCAL_MODELS, "glove_100d")
NER_PATH   = "file://" + os.path.join(LOCAL_MODELS, "ner_dl")

try:
    spark = SparkSession.builder.appName("SparkNLP-Redaction").getOrCreate()
    print(f"Spark {spark.version} started", flush=True)
except Exception:
    print("SPARKSESSION ERROR:", flush=True)
    traceback.print_exc()
    sys.exit(1)

# ── Read input ────────────────────────────────────────────────────────────────
xlsx_files = (
    glob.glob(os.path.join(INPUT_DIR, "**/*.xlsx"), recursive=True)
    + glob.glob(os.path.join(INPUT_DIR, "*.xlsx"))
)
if not xlsx_files:
    raise FileNotFoundError(f"No .xlsx files found under {INPUT_DIR}")

print(f"Reading: {xlsx_files[0]}", flush=True)
pdf = pd.read_excel(xlsx_files[0], dtype=str).fillna("")
sdf = spark.createDataFrame(pdf)
print(f"Input  : {sdf.count()} rows × {len(sdf.columns)} columns", flush=True)

print("\nActual DataFrame columns:")
for idx, c in enumerate(sdf.columns):
    print(f"  [{idx:02d}] {repr(c)}")

# ── Locate target columns ─────────────────────────────────────────────────────
COL_ASPECTS     = "Aspects positifs de l'expérience globale"
COL_SUGGESTIONS = "Suggestions d'amélioration de l'expérience globale"

def find_column(df, target):
    if target in df.columns:
        return target
    for c in df.columns:
        if c.strip() == target.strip():
            print(f"  WARNING: matched '{c}' for target '{target}' after stripping")
            return c
    return None

actual_aspects     = find_column(sdf, COL_ASPECTS)
actual_suggestions = find_column(sdf, COL_SUGGESTIONS)

if actual_aspects is None:
    raise ValueError(f"Column not found: {repr(COL_ASPECTS)}\nAvailable: {sdf.columns}")
if actual_suggestions is None:
    raise ValueError(f"Column not found: {repr(COL_SUGGESTIONS)}\nAvailable: {sdf.columns}")

print(f"aspects     → {repr(actual_aspects)}")
print(f"suggestions → {repr(actual_suggestions)}")

SAFE_ASPECTS     = "_nlp_aspects"
SAFE_SUGGESTIONS = "_nlp_suggestions"

sdf_safe = (
    sdf
    .withColumn(SAFE_ASPECTS,     sdf[actual_aspects])
    .withColumn(SAFE_SUGGESTIONS, sdf[actual_suggestions])
)

# ── NER pipeline ──────────────────────────────────────────────────────────────
TEXT_COLS = {
    SAFE_ASPECTS    : "entities_aspects",
    SAFE_SUGGESTIONS: "entities_suggestions",
}

result_df = sdf_safe
for i, (col_name, entities_col) in enumerate(TEXT_COLS.items()):
    print(f"\n[Pipeline {i+1}/{len(TEXT_COLS)}] NER on '{col_name}'", flush=True)

    doc  = DocumentAssembler().setInputCol(col_name).setOutputCol(f"_doc{i}")
    tok  = Tokenizer().setInputCols([f"_doc{i}"]).setOutputCol(f"_tok{i}")
    emb  = WordEmbeddingsModel.load(GLOVE_PATH) \
               .setInputCols([f"_doc{i}", f"_tok{i}"]).setOutputCol(f"_emb{i}")
    ner  = NerDLModel.load(NER_PATH) \
               .setInputCols([f"_doc{i}", f"_tok{i}", f"_emb{i}"]).setOutputCol(f"_ner{i}")
    conv = NerConverter() \
               .setInputCols([f"_doc{i}", f"_tok{i}", f"_ner{i}"]).setOutputCol(entities_col)

    pipeline  = Pipeline(stages=[doc, tok, emb, ner, conv])
    result_df = (
        pipeline.fit(result_df)
                .transform(result_df)
                .drop(f"_doc{i}", f"_tok{i}", f"_emb{i}", f"_ner{i}")
    )
    n = result_df.count()
    print(f"  Done — {n} rows", flush=True)

result_df = result_df.drop(SAFE_ASPECTS, SAFE_SUGGESTIONS)

# ── Write output ──────────────────────────────────────────────────────────────
out_path = "file://" + os.path.join(OUTPUT_DIR, "redacted")
result_df.coalesce(1).write.mode("overwrite").parquet(out_path)
print(f"\nSaved to: {out_path}", flush=True)

spark.stop()
