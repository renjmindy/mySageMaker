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
output_key = 'output'

def lambda_handler(event, context):
    """
    Real-time PII detection: Reads file content from S3 and gets 
    immediate results from Amazon Comprehend.
    """
    logger.info(event)
    
    results = []

    for record in event['Records']:
        # 1. Get the S3 Bucket and Key
        bucket_name = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        
        # Skip if the event is for a folder creation (ends with /)
        if key.endswith('/'):
            continue

        try:
            # 2. Read the file content from S3
            # Note: real-time 'detect_pii_entities' has a limit of 10KB per request.
            file_obj = s3.get_object(Bucket=bucket_name, Key=key)
            file_content = file_obj['Body'].read().decode('utf-8')

            # 3. Synchronous (Real-time) call to Comprehend
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/comprehend/client/detect_pii_entities.html
            response = comprehend.detect_pii_entities(
                Text=file_content,
                LanguageCode='en'
            )

            # 4. Prepare output path (e.g., input/file.txt -> output/file.txt.json)
            output_key = f"realtime_output/{key[6:]}.json"

            # 5. Save the results back to S3 immediately
            s3.put_object(
                Bucket=output_bucket,
                Key=output_key,
                Body=json.dumps(response, indent=4)
            )

            logger.info(f"Successfully processed {key} and saved to {output_key}")
            results.append({"file": key, "status": "Success"})

        except Exception as e:
            logger.error(f"Error processing {key}: {str(e)}")
            results.append({"file": key, "status": "Failed", "error": str(e)})

    return {
        "statusCode": 200,
        "body": json.dumps(results)
    }