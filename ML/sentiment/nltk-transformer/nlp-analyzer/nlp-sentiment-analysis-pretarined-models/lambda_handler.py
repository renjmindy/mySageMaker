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
    # Warmup / scheduled events that arrive without requestContext or httpMethod
    # (e.g. a direct EventBridge invocation whose Input omits those keys) must
    # not reach Mangum — it cannot infer a handler and will raise RuntimeError.
    if "httpMethod" not in event and "requestContext" not in event:
        return {"statusCode": 200, "body": "warm"}
    return _mangum(event, context)
