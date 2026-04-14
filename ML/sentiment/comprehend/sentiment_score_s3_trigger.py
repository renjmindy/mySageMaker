"""
The code is developed using reference from
https://docs.aws.amazon.com/code-samples/latest/catalog/python-comprehend-comprehend_detect.py.html
"""

import json
import os
import logging
import boto3
from urllib.parse import unquote_plus

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Boto3 Clients
s3 = boto3.client('s3')
comprehend = boto3.client('comprehend')

# Environment Variables
output_bucket = os.environ['OUTPUT_BUCKET']

def lambda_handler(event, context):
    """
    Real-time Sentiment Analysis: Triggered by S3, reads file content,
    and performs immediate sentiment detection.
    """
    logger.info(f"Received event: {json.dumps(event)}")
    results = []

    for record in event.get('Records', []):
        # 1. Extract Bucket and Key from the event
        bucket_name = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        
        if key.endswith('/'):
            continue

        try:
            # 2. Download file content
            file_obj = s3.get_object(Bucket=bucket_name, Key=key)
            file_content = file_obj['Body'].read().decode('utf-8')

            # 3. Synchronous Real-time call to Comprehend
            # Note: Max text size for real-time is 5,000 characters
            response = comprehend.detect_sentiment(
                Text=file_content[:5000], 
                LanguageCode='en'
            )

            # 4. Prepare results and output path
            filename = os.path.basename(key)
            output_key = f"sentiment_results/{filename}.json"

            # 5. Save the analysis response back to S3
            s3.put_object(
                Bucket=output_bucket,
                Key=output_key,
                Body=json.dumps(response, indent=4, default=str)
            )

            logger.info(f"Successfully analyzed sentiment for {key}")
            results.append({"file": key, "status": "Success", "sentiment": response['Sentiment']})

        except Exception as e:
            logger.error(f"Error processing {key}: {str(e)}")
            results.append({"file": key, "status": "Failed", "error": str(e)})

    return {
        "statusCode": 200,
        "body": json.dumps(results)
    }