# AWS Lambda Deployment

Deploy the Medical PII De-identification API to AWS Lambda with API Gateway, ECR, and Provisioned Concurrency.

## Prerequisites

1. **AWS CLI** configured with sufficient permissions
   ```bash
   aws configure
   ```

2. **AWS SAM CLI**
   ```bash
   pip install aws-sam-cli
   ```

3. **Docker** (for building the container image)

## Quick Deploy

```bash
# From project root — deploys to us-east-1 by default
chmod +x deploy/aws/deploy.sh
./deploy/aws/deploy.sh
```

### Deploy to a specific region

```bash
STACK_NAME=medical-pii-removal-ap-southeast-2 AWS_REGION=ap-southeast-2 ./deploy/aws/deploy.sh
```

The script will:
1. Create an ECR repository in the target region
2. Build the Docker image (includes pre-baked model weights — no runtime download)
3. Push the image to ECR
4. Deploy the CloudFormation/SAM stack with API Gateway, API key, and usage plan

## Configuration

| Variable | Default | Description |
|---|---|---|
| `STACK_NAME` | `medical-pii-removal` | CloudFormation stack name prefix |
| `AWS_REGION` | `us-east-1` | Target AWS region |
| `STAGE` | `prod` | Deployment stage (`dev`, `staging`, `prod`) |

## Architecture

```
API Gateway (REST) → Lambda (container image) → HuggingFace NER model
       ↑                      ↑
   API Key auth         ECR image with
   Usage plan           pre-baked weights
```

**Key design decisions:**
- **Pre-baked model weights**: Model is downloaded into the Docker image at build time (`/var/task/hf_cache/hub/`). No HuggingFace network calls at runtime.
- **Offline mode**: `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` prevent any attempted downloads at runtime.
- **Lazy imports**: `torch` and `transformers` are imported only when the model is first used, keeping Lambda INIT fast.
- **Provisioned Concurrency**: One Lambda instance is kept permanently warm with the model pre-loaded — eliminates cold starts entirely.

## Lambda Configuration

| Setting | Value |
|---|---|
| Memory | 3008 MB |
| Timeout | 60 seconds |
| Architecture | x86_64 |
| Ephemeral storage | 2048 MB |
| Package type | Container image |
| Provisioned concurrency | 1 instance |

## API Access

All endpoints require an API key passed as `x-api-key` header. The key is printed at the end of a successful deploy. You can also retrieve it:

```bash
# Get API endpoint
aws cloudformation describe-stacks \
  --stack-name medical-pii-removal-prod \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text

# Get API key value
KEY_ID=$(aws cloudformation describe-stacks \
  --stack-name medical-pii-removal-prod \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiKeyId`].OutputValue' \
  --output text)

aws apigateway get-api-key --api-key "$KEY_ID" --include-value \
  --region us-east-1 --query 'value' --output text
```

## Usage Plan

Each deployment creates a usage plan with:

| Limit | Value |
|---|---|
| Rate limit | 10 req/s |
| Burst limit | 20 req |
| Monthly quota | 1,000 requests |

## Testing

```bash
BASE_URL="https://YOUR_API_ID.execute-api.REGION.amazonaws.com/prod"
API_KEY="your-api-key"

# Health check
curl "${BASE_URL}/api/v1/health" -H "x-api-key: ${API_KEY}"

# Detect PII
curl -X POST "${BASE_URL}/api/v1/detect" \
  -H 'Content-Type: application/json' \
  -H "x-api-key: ${API_KEY}" \
  -d '{"text": "Patient John Smith, DOB 01/15/1980, SSN 123-45-6789"}'

# De-identify
curl -X POST "${BASE_URL}/api/v1/deidentify" \
  -H 'Content-Type: application/json' \
  -H "x-api-key: ${API_KEY}" \
  -d '{"text": "Patient John Smith SSN 123-45-6789", "strategy": "placeholder"}'
```

Available `strategy` values: `placeholder`, `consistent`, `redact`, `hash`

## Cold Starts

With Provisioned Concurrency enabled, cold starts are eliminated — the Lambda instance is always warm with the model loaded. Response time is ~500ms–1s regardless of idle time.

If you disable Provisioned Concurrency (e.g., to reduce cost in dev), use this pre-warm command before serving traffic:

```bash
aws lambda invoke \
  --function-name medical-pii-removal-prod \
  --region YOUR_REGION \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "resource": "/api/v1/detect",
    "path": "/api/v1/detect",
    "httpMethod": "POST",
    "headers": {"Content-Type": "application/json"},
    "multiValueHeaders": {"Content-Type": ["application/json"]},
    "queryStringParameters": null,
    "multiValueQueryStringParameters": null,
    "pathParameters": null,
    "stageVariables": null,
    "requestContext": {
      "resourceId": "warmup",
      "requestId": "warmup-001",
      "stage": "prod",
      "resourcePath": "/{proxy+}",
      "httpMethod": "POST",
      "apiId": "YOUR_API_ID"
    },
    "body": "{\"text\": \"warmup\"}",
    "isBase64Encoded": false
  }' /tmp/warmup.json && echo "Lambda is warm"
```

This takes ~15–25s on a cold start. Subsequent API Gateway calls respond in ~1s.

## ECR Lifecycle Policy

The deploy script creates one ECR repository per region (`medical-pii-removal`). A lifecycle policy is automatically applied to delete untagged images after 1 day, keeping the repository clean after each redeploy.

To apply the policy manually:

```bash
aws ecr put-lifecycle-policy \
  --repository-name medical-pii-removal \
  --region YOUR_REGION \
  --lifecycle-policy-text '{
    "rules": [{
      "rulePriority": 1,
      "description": "Delete untagged images after 1 day",
      "selection": {"tagStatus": "untagged", "countType": "sinceImagePushed", "countUnit": "days", "countNumber": 1},
      "action": {"type": "expire"}
    }]
  }'
```

## Monitoring

```bash
# Tail live logs
aws logs tail /aws/lambda/medical-pii-removal-prod --region YOUR_REGION --follow

# Check errors in last hour
aws logs filter-log-events \
  --log-group-name /aws/lambda/medical-pii-removal-prod \
  --region YOUR_REGION \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s000)

# Check provisioned concurrency status
aws lambda list-provisioned-concurrency-configs \
  --function-name medical-pii-removal-prod \
  --region YOUR_REGION
```

## Cost Estimate

| Component | Free Tier | With Provisioned Concurrency |
|---|---|---|
| Lambda requests | 1M/month free | 1M/month free |
| Lambda compute | 400K GB-s free | ~$35–50/month (1 instance, 3GB) |
| API Gateway | 1M calls/month free | 1M calls/month free |
| ECR storage | 500 MB/month free | ~$1–2/month (3.7 GB image) |

For dev/staging environments, set `ProvisionedConcurrentExecutions: 0` in `template.yaml` to avoid the concurrency charge.

## Cleanup

```bash
sam delete --stack-name medical-pii-removal-prod --region YOUR_REGION
```
