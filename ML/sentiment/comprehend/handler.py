import json
import logging
import boto3
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger()
logger.setLevel(logging.INFO)

comprehend = boto3.client('comprehend')


def _detect_pii(record):
    """Single detect_pii_entities call; derives both redaction and offsets."""
    patient_id = record.get('patient_id')
    text = record.get('text', '')[:10000]

    try:
        response = comprehend.detect_pii_entities(Text=text, LanguageCode='en')
        entities = response.get('Entities', [])

        redacted = text
        for entity in sorted(entities, key=lambda x: x['BeginOffset'], reverse=True):
            begin, end, etype = entity['BeginOffset'], entity['EndOffset'], entity['Type']
            redacted = redacted[:begin] + f"[{etype}]" + redacted[end:]

        return patient_id, {"redacted_text": redacted, "pii_entities": entities}, None
    except Exception as e:
        return patient_id, None, str(e)


def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event

        patient_records = body.get('data', [])
        if not patient_records:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No data provided. Format: {'data': [{'patient_id': 'ID', 'text': '...'}]}"})
            }

        # batch_detect_sentiment caps at 5 000 chars and 25 items per call
        text_list = [r.get('text', '')[:5000] for r in patient_records]

        with ThreadPoolExecutor() as executor:
            sentiment_future = executor.submit(
                comprehend.batch_detect_sentiment,
                TextList=text_list,
                LanguageCode='en'
            )
            pii_futures = {
                executor.submit(_detect_pii, record): i
                for i, record in enumerate(patient_records)
            }

            sentiment_response = sentiment_future.result()
            pii_by_index = {}
            for future in as_completed(pii_futures):
                i = pii_futures[future]
                pii_by_index[i] = future.result()  # (patient_id, data, error)

        sentiment_by_idx = {r['Index']: r for r in sentiment_response.get('ResultList', [])}
        sentiment_err_by_idx = {e['Index']: e for e in sentiment_response.get('ErrorList', [])}

        results = []
        errors = []

        for i, record in enumerate(patient_records):
            patient_id = record.get('patient_id')
            _, pii_data, pii_error = pii_by_index[i]

            if pii_error:
                errors.append({"patient_id": patient_id, "error": pii_error})
                continue

            entry = {
                "patient_id": patient_id,
                "text_preview": record.get('text', '')[:50] + "...",
                "redacted_text": pii_data["redacted_text"],
                "pii_entities": pii_data["pii_entities"],
                "pii_entity_count": len(pii_data["pii_entities"]),
            }

            if i in sentiment_by_idx:
                s = sentiment_by_idx[i]
                entry["sentiment"] = s.get('Sentiment')
                entry["sentiment_scores"] = s.get('SentimentScore')
            elif i in sentiment_err_by_idx:
                e = sentiment_err_by_idx[i]
                errors.append({
                    "patient_id": patient_id,
                    "error": f"Sentiment: {e.get('ErrorMessage')}"
                })

            results.append(entry)

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
            "body": json.dumps({"error": str(e)})
        }
