"""AWS Lambda entry-point. Wraps the FastAPI app with Mangum."""
from mangum import Mangum
from api.main import app

handler = Mangum(app, lifespan="off")
