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

handler = Mangum(app, lifespan="off")
