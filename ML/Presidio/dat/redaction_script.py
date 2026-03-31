"""
Presidio PII redaction processing script.
Executed inside a SageMaker PySparkProcessor container via spark-submit.

No pre-staged models needed — Presidio and spaCy en_core_web_lg / fr_core_news_lg
are installed at job startup.  The container must have outbound internet access; for
VPC-only deployments, swap the spacy downloads for mounted S3 model packages.
"""
import os, sys, subprocess, glob, traceback

# ── Early diagnostics (always visible in CloudWatch) ─────────────────────────
print("=" * 60, flush=True)
print(f"Python  : {sys.version}", flush=True)
print(f"CWD     : {os.getcwd()}", flush=True)
print(f"PATH    : {os.environ.get('PATH','')}", flush=True)
print("=" * 60, flush=True)

# ── Install dependencies ───────────────────────────────────────────────────────
# Split into separate commands so a single failure doesn't block everything.
# spaCy is pinned to <3.8 — spaCy 3.8+ requires thinc>=8.3.12 which is not
# available in the sagemaker-spark-processing:3.3 container (Python 3.9).
# IMPORTANT: presidio and spaCy must be in the SAME pip command so the resolver
# sees the spaCy pin and doesn't pull in spaCy 3.8.x as a presidio dependency.
# pandas<2.0 is intentionally omitted; the container ships pandas 2.x which works.
_pip_cmds = [
    # Core data / excel deps — install first so xlsx reading always works
    [sys.executable, "-m", "pip", "install", "-q",
     "openpyxl", "langdetect"],
    # Presidio + spaCy in ONE command so the resolver honours the spaCy pin
    [sys.executable, "-m", "pip", "install", "-q",
     "presidio-analyzer>=2.2", "presidio-anonymizer>=2.2", "spacy>=3.4,<3.8"],
    # spaCy language models
    [sys.executable, "-m", "spacy", "download", "en_core_web_lg", "--quiet"],
    [sys.executable, "-m", "spacy", "download", "fr_core_news_lg", "--quiet"],
]

for cmd in _pip_cmds:
    r = subprocess.run(cmd, capture_output=True, text=True)
    tag = " ".join(cmd[-4:])
    print(f"$ {tag} → exit {r.returncode}", flush=True)
    if r.returncode != 0:
        print(r.stderr[-2000:], flush=True)

try:
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import udf
    from pyspark.sql.types import StringType
    import pyspark.sql.functions as F
    import pandas as pd
    print("Imports OK", flush=True)
    print(f"pandas  {pd.__version__}", flush=True)
except Exception:
    print("IMPORT ERROR:", flush=True)
    traceback.print_exc()
    sys.exit(1)

INPUT_DIR  = "/opt/ml/processing/input"
OUTPUT_DIR = "/opt/ml/processing/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

try:
    spark = SparkSession.builder.appName("Presidio-Redaction").getOrCreate()
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

# pandas 2.0 removed DataFrame.iteritems(); PySpark 3.3.x calls it internally
# when converting a pandas DataFrame to a Spark DataFrame.
if not hasattr(pd.DataFrame, "iteritems"):
    pd.DataFrame.iteritems = pd.DataFrame.items

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

# ── Presidio redaction UDF ────────────────────────────────────────────────────
# Entities to redact.  ORGANIZATION is intentionally excluded — mirrors the
# original Spark-NLP behaviour where ORG spans were left as-is.
ENTITIES = [
    "PERSON", "LOCATION", "DATE_TIME",
    "PHONE_NUMBER", "EMAIL_ADDRESS",
    "CREDIT_CARD", "IBAN_CODE",
    "IP_ADDRESS", "NRP",
]

# Module-level lazy singletons — initialised once per Spark executor process,
# not once per row, so the spaCy models are loaded only once per worker.
_analyzer   = None
_anonymizer = None

def _init_presidio():
    global _analyzer, _anonymizer
    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        from presidio_anonymizer import AnonymizerEngine
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": "en", "model_name": "en_core_web_lg"},
                {"lang_code": "fr", "model_name": "fr_core_news_lg"},
            ],
        })
        _analyzer   = AnalyzerEngine(
            nlp_engine=provider.create_engine(),
            supported_languages=["en", "fr"],
        )
        _anonymizer = AnonymizerEngine()

@udf(StringType())
def presidio_redact(text):
    """Detect and replace PII spans; returns redacted string with [ENTITY] tags."""
    if not text or not text.strip():
        return text
    _init_presidio()
    # Detect language; default to French (dataset is a French-language hospital survey)
    lang = "fr"
    if len(text.strip()) >= 20:
        try:
            from langdetect import detect
            detected = detect(text)
            if detected in ("en", "fr"):
                lang = detected
        except Exception:
            pass
    from presidio_anonymizer.entities import OperatorConfig
    operators = {
        entity: OperatorConfig("replace", {"new_value": f"[{entity}]"})
        for entity in ENTITIES
    }
    results  = _analyzer.analyze(text=text, entities=ENTITIES, language=lang)
    redacted = _anonymizer.anonymize(
        text=text, analyzer_results=results, operators=operators
    )
    return redacted.text

# ── Apply redaction to both columns ──────────────────────────────────────────
TEXT_COLS = {
    actual_aspects    : "redacted_aspects",
    actual_suggestions: "redacted_suggestions",
}

result_df = sdf
for src_col, out_col in TEXT_COLS.items():
    print(f"\n[Redact] '{src_col}' → '{out_col}'", flush=True)
    result_df = result_df.withColumn(out_col, presidio_redact(F.col(src_col)))

n = result_df.count()
print(f"\nRedaction complete — {n} rows", flush=True)

# ── Write output ──────────────────────────────────────────────────────────────
out_path = "file://" + os.path.join(OUTPUT_DIR, "redacted")
result_df.coalesce(1).write.mode("overwrite").parquet(out_path)
print(f"Saved to: {out_path}", flush=True)

spark.stop()
