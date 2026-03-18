import logging
import sagemaker
from sagemaker.core.local import LocalSession

logging.getLogger("sagemaker.config").setLevel(logging.WARNING)

# Initialize the local session
sagemaker_session = LocalSession()
sagemaker_session.config = {'local': {'local_code': True}}

# PASTE YOUR ROLE ARN HERE
role = 'arn:aws:iam::493644444178:role/SageMakerLocalExecutionRole'

# Test: Try to get the default S3 bucket (verifies AWS connectivity)
try:
    bucket = sagemaker_session.default_bucket()
    print(f"Success! Connected to bucket: {bucket}")
except Exception as e:
    print(f"Error: {e}")
