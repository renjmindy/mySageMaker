"""AWS Lambda entry-point. Wraps the FastAPI app with Mangum."""
from mangum import Mangum
from api.main import app

# Pre-load the default model at container startup so the first API Gateway
# call (max 29 s) doesn't block on model weight loading (~60-120 s).
try:
    from src.analyzer import _get_direct_model
    from src.models import ModelType
    _get_direct_model(ModelType.DEFAULT)
except Exception:
    pass

_mangum = Mangum(app, lifespan="off")


def handler(event, context):
    # Only forward events that match one of Mangum's three handler types:
    #   REST API  → has "httpMethod"
    #   HTTP API  → has "version" 1.0 or 2.0
    #   ALB       → has requestContext.elb
    # Everything else (EventBridge, SQS, direct-invoke test payloads, …)
    # is treated as a warmup ping and short-circuited here.
    is_http = (
        "httpMethod" in event
        or event.get("version") in ("1.0", "2.0")
        or bool(event.get("requestContext", {}).get("elb"))
    )
    if not is_http:
        return {"statusCode": 200, "body": "warm"}
    try:
        return _mangum(event, context)
    except RuntimeError:
        # Malformed or unrecognised event shape — treat as warmup rather than crash.
        return {"statusCode": 200, "body": "warm"}
