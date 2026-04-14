"""
The code is developed using reference from
https://docs.aws.amazon.com/code-samples/latest/catalog/python-comprehend-comprehend_detect.py.html
"""

import json
import os
import logging
import boto3

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Boto3 Client
comprehend = boto3.client('comprehend')

def lambda_handler(event, context):
    """
    Hybrid Trigger: Handles API Gateway (proxied string) and 
    Lambda Test Tab (direct dictionary).
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # 1. SMART PARSING
        # API Gateway wraps the payload in a 'body' string.
        # Lambda Test Tab passes the payload as a raw dictionary.
        if 'body' in event:
            # Logic for API Gateway
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
            input_text = body.get('text', '')
        else:
            # Logic for direct Lambda Console "Test" events
            input_text = event.get('text', '')

        # 2. Validation & Character Limit (10KB for real-time)
        if not input_text:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No 'text' provided. Format: {'text': 'your content'}"})
            }

        # 3. Call Comprehend (Real-time Detect)
        # Slicing to 10,000 characters to prevent API size limit errors
        response = comprehend.detect_pii_entities(
            Text=input_text[:10000],
            LanguageCode='en'
        )
        entities = response.get('Entities', [])

        # 4. Redaction Logic (Reverse-Index replacement)
        redacted_text = input_text[:10000]
        for entity in sorted(entities, key=lambda x: x['BeginOffset'], reverse=True):
            begin = entity['BeginOffset']
            end = entity['EndOffset']
            etype = entity['Type']
            
            # Using [LABEL] format to keep redacted entities known
            redacted_text = redacted_text[:begin] + f"[{etype}]" + redacted_text[end:]

        # 5. Return JSON Response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"  # Required for frontend integration
            },
            "body": json.dumps({
                "status": "Success",
                "redacted_text": redacted_text,
                "entity_count": len(entities)
            }, indent=4)
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error", "details": str(e)})
        }