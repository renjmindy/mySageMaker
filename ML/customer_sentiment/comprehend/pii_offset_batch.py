"""
The code is developed using reference from
https://docs.aws.amazon.com/code-samples/latest/catalog/python-comprehend-comprehend_detect.py.html
"""

import json
import os
import logging
import boto3
import datetime
from urllib.parse import unquote_plus

# It is a good practice to use proper logging.
# Here we are using the logging module of python.
# https://docs.python.org/3/library/logging.html

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Boto3 - s3 Client
# You will use the S3 client to upload a response file.
# More Info: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html
s3 = boto3.client('s3')

# Output bucket name
output_bucket = os.environ['OUTPUT_BUCKET']

# Data access role ARN
data_arn = os.environ['DATA_ARN']

# Declare the output file path and name.
output_key = "output/pii_detection_job_metadata.json"

def lambda_handler(event, context):
    """
    This code gets the S3 attributes from the trigger event,
    then invokes the transcribe api to analyze audio files asynchronously.
    """

    # log the event
    logger.info(event)
    # Iterate through the event
    for record in event['Records']:
        # Get the bucket name and key for the new file
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        
        # Using datetime to create a unique job name.
        now = datetime.datetime.now()
        job_uri = f's3://{bucket}/{key}'
        job_name = f'pii_detection_job_{now:%Y-%m-%d-%H-%M}'
        
        # Using Amazon Comprehend client
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/comprehend.html
        comprehend = boto3.client('comprehend')
        
        try:
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/comprehend/client/start_pii_entities_detection_job.html
            response = comprehend.start_pii_entities_detection_job(
                InputDataConfig={
                    'S3Uri': job_uri,
                    'InputFormat': 'ONE_DOC_PER_LINE',
                },
                OutputDataConfig={
                    'S3Uri': f's3://{output_bucket}/pii_output/'
                },
                Mode='ONLY_OFFSETS',  # Use 'ONLY_OFFSETS' to get the locations of PII, or 'ONLY_REDACTION' to mask it
                JobName=job_name,
                LanguageCode='en',
                DataAccessRoleArn=data_arn
            )
            
            logger.info(f"Started PII Detection Job: {response['JobId']}")

            # Log the job initiation response back to S3 for audit purposes
            s3.put_object(
                Bucket=output_bucket,
                Key=output_key,
                Body=json.dumps(response, sort_keys=True, indent=4, default=str)
            )
            
            pii_result = {"Status": "Success", "JobId": response['JobId'], "Info": f"PII Job {job_name} Started"}
        
        except Exception as e:
            logger.error(f"Error starting job: {str(e)}")
            pii_result = {"Status": "Failed", "Reason": str(e)}
        
        return pii_result
        
"""
You can use the code below to create a test event.
{
    "Records": [
                {
                "s3": {
                    "bucket": {
                    "name": "<Your_input_bucket_name>"
                    },
                    "object": {
                    "key": "input/sample_comprehend_file.txt"
                    }
                }
                }
            ]
}
"""