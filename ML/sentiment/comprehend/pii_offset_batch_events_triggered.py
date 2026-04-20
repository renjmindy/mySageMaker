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
        # 1. SMART PARSING (Matches Sentiment Structure)
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
            
        # Get the list of patient records from the 'data' key
        patient_records = body.get('data', [])

        if not patient_records:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No data provided. Format: {'data': [{'patient_id': 'ID', 'text': '...'}]}"})
            }

        # 2. PREPARE RESULTS AND ERROR LISTS
        results = []
        errors = []

        # 3. PROCESS EACH RECORD (Looping because PII has no Batch API)
        for record in patient_records:
            patient_id = record.get('patient_id')
            input_text = record.get('text', '')

            if not input_text:
                errors.append({
                    "patient_id": patient_id, 
                    "error": "No text provided for this record."
                })
                continue

            try:
                # 4. Synchronous call to Comprehend for Offset Data
                # Capped at 10,000 bytes for PII real-time limits
                response = comprehend.detect_pii_entities(
                    Text=input_text[:10000],
                    LanguageCode='en'
                )
                
                entities = response.get('Entities', [])

                results.append({
                    "patient_id": patient_id,
                    "entities": entities,
                    "entity_count": len(entities),
                    "text_preview": input_text[:50] + "..."
                })

            except Exception as e:
                # Catch errors for a specific record without failing the whole batch
                errors.append({
                    "patient_id": patient_id,
                    "error": str(e)
                })

        # 5. RETURN UNIFIED BATCH RESPONSE
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "status": "Success",
                "processed_count": len(results),
                "results": results,
                "errors": errors
            }, indent=4)
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "statusCode": 500, 
            "body": json.dumps({"error": "Internal Server Error", "details": str(e)})
        }