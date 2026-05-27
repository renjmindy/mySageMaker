"""
AWS Lambda handler — Healthcare PREM Topic Classification API.

Endpoint contract (via API Gateway HTTP proxy integration):
────────────────────────────────────────────────────────────
POST /classify
  Body (JSON):
    {
      "texts":  ["Patient text 1 ...", "Patient text 2 ..."],  // required
      "models": ["all"]  | ["bertopic_mini","lda","nmf",...],  // optional, default "all"
      "top_n":  3                                               // optional, default 3
    }

  Response 200:
    {
      "results": [
        {
          "text": "Patient text 1 ...",
          "classifications": {
            "bertopic_mini":  {"topic_id":0,"topic_name":"Clinical Staff",
                               "confidence":0.82,"top_topics":[...]},
            "bertopic_mpnet": {...},
            "lda":            {...},
            "lsi":            {...},
            "hdp":            {...},
            "nmf":            {...}
          }
        },
        ...
      ],
      "model_status": {"bertopic_mini": true, ...}
    }

GET /health
  Response 200:
    {"status": "ok", "models_loaded": {"bertopic_mini": true, ...}}

EventBridge warm-up event (sent every 5 min by CloudFormation rule):
    {"source": "aws.events", "detail-type": "ScheduledEvent",
     "detail": {"action": "warmup"}}
  → Lambda loads all models (no-op if already loaded), returns 200.

Single-text convenience:
    {"text": "...", ...}  — wraps in list automatically.
────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── Ensure project root is importable ────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Global singleton — persists across warm Lambda invocations ────────────────
from healthcare_classifier import HealthcareTopicClassifier

_classifier: HealthcareTopicClassifier | None = None


def _get_classifier() -> HealthcareTopicClassifier:
    global _classifier
    if _classifier is None:
        logger.info("Cold start: initialising HealthcareTopicClassifier ...")
        t0 = time.time()
        _classifier = HealthcareTopicClassifier()
        # Eagerly load all models so the first real request is fast
        timings = _classifier.load_all()
        logger.info(
            "All models loaded in %.1fs — timings: %s",
            time.time() - t0,
            json.dumps(timings),
        )
    return _classifier


# ── Response helpers ──────────────────────────────────────────────────────────

def _ok(body: dict, status: int = 200) -> dict:
    return {
        "statusCode": status,
        "headers":    {"Content-Type": "application/json",
                       "Access-Control-Allow-Origin": "*"},
        "body":       json.dumps(body),
    }


def _err(message: str, status: int = 400) -> dict:
    return _ok({"error": message}, status)


# ── Main handler ──────────────────────────────────────────────────────────────

def handler(event: dict, context) -> dict:
    """
    AWS Lambda entry-point.

    Supports:
      • API Gateway HTTP API proxy (event has httpMethod / routeKey)
      • Direct Lambda invocation (event has "texts" or "text")
      • EventBridge scheduled warm-up (event has source == "aws.events")
    """
    logger.info("Event: %s", json.dumps(event)[:512])

    # ── EventBridge warm-up ───────────────────────────────────────────────
    if event.get("source") == "aws.events":
        clf = _get_classifier()  # loads all models
        return _ok({"status": "warm", "models": clf.status()})

    # ── Routing (API Gateway HTTP API or REST API) ────────────────────────
    http_method = (
        event.get("httpMethod")                            # REST API
        or (event.get("requestContext") or {})             # HTTP API
           .get("http", {}).get("method", "")
    ).upper()

    raw_path = (
        event.get("path", "")
        or event.get("rawPath", "")
    ).rstrip("/") or "/"

    # Parse body
    body_str = event.get("body", "{}")
    if event.get("isBase64Encoded"):
        import base64
        body_str = base64.b64decode(body_str or "e30=").decode()
    try:
        body: dict = json.loads(body_str or "{}")
    except json.JSONDecodeError:
        return _err("Request body is not valid JSON", 400)

    # ── GET /health ───────────────────────────────────────────────────────
    if http_method == "GET" or (not http_method and raw_path == "/health"):
        clf = _get_classifier()
        return _ok({"status": "ok", "models_loaded": clf.status()})

    # ── Direct invocation without HTTP wrapper ────────────────────────────
    # (e.g. boto3 client.invoke(..., Payload=json.dumps({...})))
    if not http_method:
        body = event  # the whole event IS the payload

    # ── POST /classify (or direct invocation) ────────────────────────────
    # Resolve texts
    if "text" in body and "texts" not in body:
        body["texts"] = [body["text"]]

    texts = body.get("texts")
    if not texts or not isinstance(texts, list):
        return _err('Field "texts" must be a non-empty list of strings.', 422)
    if not all(isinstance(t, str) for t in texts):
        return _err('All items in "texts" must be strings.', 422)
    if len(texts) > 500:
        return _err("Maximum 500 texts per request.", 422)

    models = body.get("models", ["all"])
    if isinstance(models, str):
        models = [models]

    top_n = body.get("top_n", 3)
    try:
        top_n = int(top_n)
    except (TypeError, ValueError):
        top_n = 3

    # Run classification
    clf = _get_classifier()
    t0  = time.time()
    try:
        results = clf.classify(texts=texts, models=models, top_n=top_n)
    except ValueError as exc:
        return _err(str(exc), 422)
    except Exception as exc:
        logger.exception("Classification failed: %s", exc)
        return _err("Internal classification error — check Lambda logs.", 500)

    elapsed = round(time.time() - t0, 3)
    logger.info("Classified %d texts in %.3fs", len(texts), elapsed)

    return _ok(
        {
            "results":      results,
            "model_status": clf.status(),
            "elapsed_sec":  elapsed,
        }
    )
