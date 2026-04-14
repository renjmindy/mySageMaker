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
output_key = "output/comprehend_response.json"

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
        job_name = f'comprehend_job_{now:%Y-%m-%d-%H-%M}'
        
        # Using Amazon Comprehend client
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/comprehend.html
        comprehend = boto3.client('comprehend')
        
        try:
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/comprehend.html#Comprehend.Client.start_sentiment_detection_job
            # start_sentiment_detection_job: Starts an asynchronous sentiment detection job for a 
            # collection of documents using the operation to track the status of a job.
            response_sentiment_detection_job = comprehend.start_sentiment_detection_job(
                        InputDataConfig={
                            'S3Uri': job_uri,
                            'InputFormat': 'ONE_DOC_PER_LINE',
                        },
                        OutputDataConfig={
                            'S3Uri': f's3://{output_bucket}/output/'
                        },
                        JobName=job_name,
                        LanguageCode='en',
                        DataAccessRoleArn=data_arn,
                    )
            
            # Writing the success result.
            sentiment_result = {"Status":"Success", "Info":f"Analysis Job {job_name} Started"}
        
            # Finally the response will be written in the S3 bucket output folder.
            # Using S3 client to upload the response file
            s3.put_object(
                Bucket=output_bucket,
                Key=output_key,
                Body=json.dumps(response_sentiment_detection_job, sort_keys=True, indent=4)
            )
        
        except Exception as e:
            sentiment_result = {"Status":"Failed", "Reason":json.dumps(e, default=str,sort_keys=True, indent=4)}
        
        return sentiment_result
        
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
# DATA_ARN - arn:aws:iam::024303312597:role/comprehend-lambda-function-role-e3cfe2c0
# INPUT_BUCKET - amazon-comprehend-input-bucket-024303312597-e3cfe2c0
# OUTPUT_BUCKET - amazon-comprehend-output-bucket-024303312597-e3cfe2c0