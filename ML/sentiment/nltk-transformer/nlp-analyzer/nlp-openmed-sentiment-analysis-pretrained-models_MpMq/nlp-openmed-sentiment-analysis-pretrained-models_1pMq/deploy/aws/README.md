# AWS Lambda Deployment

Deploy the NLP Sentiment Analysis API to AWS Lambda with API Gateway.

## Free Tier

- **Lambda**: 1 million requests/month, 400,000 GB-seconds compute
- **API Gateway**: 1 million API calls/month
- **ECR**: 500 MB storage/month

## Prerequisites

1. **AWS CLI** configured
   ```bash
   aws configure
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
export STACK_NAME=nlp-sentiment      # CloudFormation stack name (default)
export AWS_REGION=us-east-1          # AWS region
export STAGE=prod                    # prod | staging | dev
```

## Manual Steps

```bash
# 1. Build Lambda image
docker build --platform linux/amd64 -f deploy/aws/Dockerfile -t nlp-sentiment .

# 2. Push to ECR
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
aws ecr create-repository --repository-name nlp-sentiment
aws ecr get-login-password | docker login --username AWS --password-stdin ${ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com
docker tag nlp-sentiment:latest ${ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com/nlp-sentiment:latest
docker push ${ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com/nlp-sentiment:latest

# 3. SAM deploy
sam deploy \
  --template-file deploy/aws/template.yaml \
  --stack-name nlp-sentiment-prod \
  --capabilities CAPABILITY_IAM \
  --image-repository ${ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com/nlp-sentiment \
  --parameter-overrides Stage=prod
```

## Testing

```bash
ENDPOINT="https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod"

# Health check
curl "${ENDPOINT}/api/v1/health"

# Analyse sentiment (DistilBERT)
curl -X POST "${ENDPOINT}/api/v1/analyze" \
  -H 'Content-Type: application/json' \
  -d '{"text": "This product is absolutely amazing I love everything about it", "model_type": "default"}'

# Analyse emotion (GoEmotions)
curl -X POST "${ENDPOINT}/api/v1/analyze" \
  -H 'Content-Type: application/json' \
  -d '{"text": "The patient feels anxious and scared about the upcoming procedure", "model_type": "emotion"}'
```

## Cleanup

```bash
sam delete --stack-name nlp-sentiment-prod
aws ecr delete-repository --repository-name nlp-sentiment --force
```

## Performance Notes

- **Memory**: 3 GB (required for three transformer models simultaneously)
- **Ephemeral storage**: 2 GB
- **Timeout**: 120 seconds
- **Cold start**: ~30–60 s (three models + spaCy); warm requests ~500 ms–2 s
- Models are baked into the container image at build time to minimise cold starts

## Cost Estimate

For typical usage (10,000 requests/month):
- **Lambda**: Free tier (under 1 M requests)
- **API Gateway**: Free tier (under 1 M requests)
- **Estimated Cost**: $0/month
