"""
The code is developed using reference from
https://docs.aws.amazon.com/code-samples/latest/catalog/python-comprehend-comprehend_detect.py.html
"""

import json
import os
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

comprehend = boto3.client('comprehend')

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # 1. SMART PARSING (Consistent with Sentiment Code)
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
            
        patient_records = body.get('data', [])

        if not patient_records:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No data provided."})
            }

        # 2. PROCESS RECORDS
        results = []
        errors = []

        for record in patient_records:
            patient_id = record.get('patient_id')
            input_text = record.get('text', '')

            if not input_text:
                errors.append({"patient_id": patient_id, "error": "Empty text"})
                continue

            try:
                # 3. CALL COMPREHEND (PII is single-call only)
                # Capped at 10,000 bytes (standard PII limit)
                response = comprehend.detect_pii_entities(
                    Text=input_text[:10000],
                    LanguageCode='en'
                )
                entities = response.get('Entities', [])

                # 4. REDACTION LOGIC
                redacted_text = input_text[:10000]
                for entity in sorted(entities, key=lambda x: x['BeginOffset'], reverse=True):
                    begin = entity['BeginOffset']
                    end = entity['EndOffset']
                    etype = entity['Type']
                    redacted_text = redacted_text[:begin] + f"[{etype}]" + redacted_text[end:]

                results.append({
                    "patient_id": patient_id,
                    "redacted_text": redacted_text,
                    "entity_count": len(entities)
                })

            except Exception as e:
                errors.append({
                    "patient_id": patient_id, 
                    "error": str(e)
                })

        # 5. RETURN UNIFIED RESPONSE (Matches Sentiment Structure)
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "status": "Success",
                "results": results,
                "errors": errors
            }, indent=4)
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
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