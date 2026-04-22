import json
import os
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

comprehend = boto3.client('comprehend')

def lambda_handler(event, context):
    #logger.info(f"Received event: {json.dumps(event)}")
    if 'body' in event:
        # Just log that we received a request and how many records are in it
        try:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            record_count = len(body.get('data', []))
            logger.info(f"Processing request with {record_count} records.")
        except:
            logger.info("Received request (unable to parse record count).")
    
    try:
        # 1. SMART PARSING
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
            
        # Get the list of patient records
        patient_records = body.get('data', [])

        if not patient_records:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No data provided. Format: {'data': [{'patient_id': 'ID', 'text': '...'}]}"})
            }

        # 2. PREPARE BATCH
        # Extract just the text for Comprehend, capped at 5000 chars
        text_list = [record.get('text', '')[:5000] for record in patient_records]
        
        # 3. BATCH CALL TO COMPREHEND
        response = comprehend.batch_detect_sentiment(
            TextList=text_list,
            LanguageCode='en'
        )

        # 4. RECONSTRUCT RESULTS WITH PATIENT_ID
        # Comprehend returns 'ResultList' where index matches input text_list index
        results = []
        for result in response.get('ResultList', []):
            idx = result['Index']
            results.append({
                "patient_id": patient_records[idx].get('patient_id'),
                "sentiment": result.get('Sentiment'),
                "scores": result.get('SentimentScore'),
                "text_preview": text_list[idx][:50] + "..."
            })

        # Capture individual errors (e.g., if one text was empty or unsupported)
        errors = []
        for err in response.get('ErrorList', []):
            idx = err['Index']
            errors.append({
                "patient_id": patient_records[idx].get('patient_id'),
                "error_code": err.get('ErrorCode'),
                "error_message": err.get('ErrorMessage')
            })

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