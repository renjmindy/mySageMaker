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
    Hybrid Trigger: Handles API Gateway (proxied) and Lambda Test Tab (direct).
    Performs real-time Sentiment Analysis.
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # 1. SMART PARSING: Detect the source of the trigger
        if 'body' in event:
            # Triggered via API Gateway (Proxy Integration)
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            input_text = body.get('text', '')
        else:
            # Triggered via Lambda "Test" tab or direct invocation
            input_text = event.get('text', '')

        # 2. Validation
        if not input_text:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No 'text' provided. Format: {'text': 'message'}"})
            }

        # 3. Synchronous Real-time call to Comprehend
        # Limit to 5,000 characters for real-time sentiment API
        response = comprehend.detect_sentiment(
            Text=input_text[:5000],
            LanguageCode='en'
        )

        # 4. Construct the response
        payload = {
            "status": "Success",
            "sentiment": response.get('Sentiment'),
            "scores": response.get('SentimentScore'),
            "analyzed_text_sample": input_text[:50] + "..." if len(input_text) > 50 else input_text
        }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*" # Required for CORS
            },
            "body": json.dumps(payload, indent=4)
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }