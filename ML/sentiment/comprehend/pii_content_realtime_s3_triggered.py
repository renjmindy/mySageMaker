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

# Environment Variable for where to save the result
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')
output_key = "pii_output/pii_content_job_metadata.json"

def lambda_handler(event, context):
    logger.info(f"Received S3 event: {json.dumps(event)}")
    
    results = []

    try:
        # 1. Iterate through the S3 records in the event
        for record in event.get('Records', []):
            bucket_name = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])

            # Skip folder markers
            if key.endswith('/'):
                continue

            # 2. Fetch the file content from S3
            file_obj = s3.get_object(Bucket=bucket_name, Key=key)
            input_text = file_obj['Body'].read().decode('utf-8')

            if not input_text:
                logger.warning(f"File {key} is empty. Skipping.")
                continue

            # 3. Synchronous call to Comprehend (Real-time Detect)
            # Note: Max 10,000 bytes for real-time detection
            response = comprehend.detect_pii_entities(
                Text=input_text[:10000], 
                LanguageCode='en'
            )
            entities = response.get('Entities', [])

            # 4. Redaction Logic (Working backwards)
            redacted_text = input_text[:10000]
            for entity in sorted(entities, key=lambda x: x['BeginOffset'], reverse=True):
                begin = entity['BeginOffset']
                end = entity['EndOffset']
                etype = entity['Type']
                redacted_text = redacted_text[:begin] + f"[{etype}]" + redacted_text[end:]

            # 5. Save the Redacted Text back to S3
            #filename = os.path.basename(key)
            
            s3.put_object(
                Bucket=OUTPUT_BUCKET if OUTPUT_BUCKET else bucket_name,
                Key=output_key,
                Body=redacted_text
            )

            logger.info(f"Successfully redacted {key} and saved to {output_key}")
            results.append({"file": key, "status": "Success"})

        return {
            "statusCode": 200,
            "body": json.dumps(results)
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}