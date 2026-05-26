# AWS Lambda Deployment — NLP Healthcare Sentiment Analysis

Deploy the fine-tuned healthcare sentiment API (6 models by **cjen1008**) to AWS Lambda
with a single API Gateway endpoint. Region: **ap-southeast-2** (Sydney).

## Models deployed

| `model_type` | HuggingFace ID | Labels |
|---|---|---|
| `bert_hc_v2` *(default)* | `cjen1008/bert-healthcare-sentiment_v2` | NEGATIVE / NEUTRAL / POSITIVE |
| `distilroberta_hc_v2` | `cjen1008/distilroberta-healthcare-sentiment_v2` | NEGATIVE / NEUTRAL / POSITIVE |
| `distilbert_hc_v2` | `cjen1008/distilbert-healthcare-sentiment_v2` | NEGATIVE / NEUTRAL / POSITIVE |
| `bert_hc` | `cjen1008/bert-healthcare-sentiment` | NEGATIVE / NEUTRAL / POSITIVE |
| `distilbert_hc` | `cjen1008/distilbert-healthcare-sentiment` | NEGATIVE / NEUTRAL / POSITIVE |
| `distilroberta_hc` | `cjen1008/distilroberta-healthcare-sentiment` | NEGATIVE / NEUTRAL / POSITIVE |

## Free Tier

- **Lambda**: 1 million requests/month, 400,000 GB-seconds compute
- **API Gateway**: 1 million API calls/month
- **ECR**: 500 MB storage/month

## Prerequisites

1. **AWS CLI** configured for ap-southeast-2
   ```bash
   aws configure
   # Default region: ap-southeast-2
   ```

2. **AWS SAM CLI**
   ```bash
   pip install aws-sam-cli
   ```

3. **Docker** (for building the Lambda container image)

## Quick Deploy

```bash
# From project root
chmod +x deploy/aws/deploy.sh
./deploy/aws/deploy.sh
```

## Configuration

```bash
export STACK_NAME=nlp-hc-sentiment      # CloudFormation stack name (default)
export AWS_REGION=ap-southeast-2        # AWS region (Sydney)
export STAGE=prod                       # prod | staging | dev
```

## Manual Steps

```bash
REGION=ap-southeast-2
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

# 1. Build Lambda image
docker build --platform linux/amd64 --provenance=false \
  -f deploy/aws/Dockerfile -t nlp-hc-sentiment .

# 2. Push to ECR
aws ecr create-repository --repository-name nlp-hc-sentiment --region ${REGION}
aws ecr get-login-password --region ${REGION} | \
  docker login --username AWS --password-stdin ${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com
docker tag nlp-hc-sentiment:latest \
  ${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/nlp-hc-sentiment:latest
docker push ${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/nlp-hc-sentiment:latest

# 3. SAM deploy
sam deploy \
  --template-file deploy/aws/template.yaml \
  --stack-name nlp-hc-sentiment-prod \
  --region ${REGION} \
  --capabilities CAPABILITY_IAM \
  --image-repository ${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/nlp-hc-sentiment \
  --parameter-overrides Stage=prod
```

## Testing

```bash
ENDPOINT="https://YOUR_API_ID.execute-api.ap-southeast-2.amazonaws.com/prod"
API_KEY="your-api-key"

# Health check
curl -H "X-Api-Key: ${API_KEY}" "${ENDPOINT}/api/v1/health"

# BERT Healthcare v2 (default) — positive note
curl -X POST "${ENDPOINT}/api/v1/analyze" \
  -H 'Content-Type: application/json' \
  -H "X-Api-Key: ${API_KEY}" \
  -d '{"text": "The patient is recovering well and responding positively to treatment.", "model_type": "bert_hc_v2"}'

# DistilRoBERTa Healthcare v2 — negative note
curl -X POST "${ENDPOINT}/api/v1/analyze" \
  -H 'Content-Type: application/json' \
  -H "X-Api-Key: ${API_KEY}" \
  -d '{"text": "The patient reported severe side effects and persistent pain after the procedure.", "model_type": "distilroberta_hc_v2"}'

# BERT Healthcare v1 — neutral / mixed note
curl -X POST "${ENDPOINT}/api/v1/analyze" \
  -H 'Content-Type: application/json' \
  -H "X-Api-Key: ${API_KEY}" \
  -d '{"text": "The patient shows mixed results. Some improvement noted but fatigue persists.", "model_type": "bert_hc"}'
```

## Keep-Warm (EventBridge)

An **EventBridge rule** fires a synthetic `/api/v1/health` request to the Lambda
**every 5 minutes**, preventing cold starts. It is deployed automatically by the
SAM template (`WarmupRule` + `WarmupPermission`). No manual setup required.

Additionally, `lambda_handler.py` pre-loads `BERT Healthcare v2` at container
startup so the first real request is served without a model-weight loading delay.

## Cleanup

```bash
sam delete --stack-name nlp-hc-sentiment-prod --region ap-southeast-2
aws ecr delete-repository --repository-name nlp-hc-sentiment \
  --region ap-southeast-2 --force
```

## Performance Notes

- **Memory**: 3 GB (largest model is BERT base ~440 MB; sufficient for lazy-loaded models)
- **Ephemeral storage**: 2 GB
- **Timeout**: 3 minutes (first cold-start model load)
- **Cold start**: ~20–40 s (one model + spaCy); warm requests ~300 ms–1 s
- All 6 model weights are baked into the container image at build time

## Cost Estimate

For typical usage (10,000 requests/month):
- **Lambda**: Free tier (under 1 M requests)
- **API Gateway**: Free tier (under 1 M requests)
- **Estimated Cost**: $0/month
