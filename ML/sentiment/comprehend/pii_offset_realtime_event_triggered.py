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
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # 1. SMART PARSING: Check if 'body' exists (API Gateway) or if it's a direct test
        if 'body' in event:
            # Logic for real API Gateway calls
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            input_text = body.get('text', '')
        else:
            # Logic for direct Lambda Console "Test" events
            input_text = event.get('text', '')

        # 2. Validation
        if not input_text:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No 'text' provided. Ensure JSON looks like {'text': 'your data'}"})
            }

        # 3. Synchronous call to Comprehend
        response = comprehend.detect_pii_entities(
            Text=input_text,
            LanguageCode='en'
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "status": "Success",
                "entities": response.get('Entities', [])
            }, indent=4)
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}