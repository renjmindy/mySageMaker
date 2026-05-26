#!/bin/bash
# AWS Lambda Container Image Deployment — NLP Healthcare Sentiment Analysis
# Fine-tuned models by cjen1008 | Region: ap-southeast-2

set -e

STACK_NAME="${STACK_NAME:-nlp-hc-sentiment}"
REGION="${AWS_REGION:-ap-southeast-2}"
STAGE="${STAGE:-prod}"
IMAGE_NAME="nlp-hc-sentiment"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}NLP Healthcare Sentiment — AWS Deploy${NC}"
echo -e "${GREEN}Region: ${REGION}${NC}"
echo -e "${GREEN}========================================${NC}"

# ── Prerequisites ────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

for cmd in aws sam docker; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}Error: $cmd is not installed${NC}"
        exit 1
    fi
done

if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials not configured. Run: aws configure${NC}"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${IMAGE_NAME}"
echo -e "${GREEN}Prerequisites OK  (account: ${ACCOUNT_ID}, region: ${REGION})${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

# ── Ensure lambda_handler.py is correct ──────────────────────────────────────
if [ ! -f lambda_handler.py ]; then
    echo -e "\n${YELLOW}Creating lambda_handler.py...${NC}"
    cat > lambda_handler.py << 'EOF'
"""AWS Lambda entry-point. Wraps the FastAPI app with Mangum."""
from mangum import Mangum
from api.main import app

try:
    from src.analyzer import _get_direct_model
    from src.models import ModelType
    _get_direct_model(ModelType.BERT_HC_V2)
except Exception:
    pass

_mangum = Mangum(app, lifespan="off")

def handler(event, context):
    if "httpMethod" not in event and "requestContext" not in event:
        return {"statusCode": 200, "body": "warm"}
    return _mangum(event, context)
EOF
fi

# Ensure mangum is in requirements
if ! grep -q "mangum" requirements.txt; then
    echo "mangum>=0.17.0" >> requirements.txt
fi

# ── ECR repository ───────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Setting up ECR repository (${IMAGE_NAME}) in ${REGION}...${NC}"
aws ecr describe-repositories --repository-names "$IMAGE_NAME" --region "$REGION" &>/dev/null || \
    aws ecr create-repository --repository-name "$IMAGE_NAME" --region "$REGION"

# Authenticate Docker to ECR
aws ecr get-login-password --region "$REGION" | \
    docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# ── Build & push ─────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Building Docker image (this will take several minutes — 6 models are downloaded)...${NC}"
docker build --platform linux/amd64 --provenance=false \
    -t "${IMAGE_NAME}:latest" \
    -f deploy/aws/Dockerfile .

docker tag "${IMAGE_NAME}:latest" "${ECR_URI}:latest"

echo -e "\n${YELLOW}Pushing image to ECR...${NC}"
docker push "${ECR_URI}:latest"

# ── Handle stuck stacks ──────────────────────────────────────────────────────
STACK_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}-${STAGE}" \
    --region "$REGION" \
    --query 'Stacks[0].StackStatus' \
    --output text 2>/dev/null || echo "DOES_NOT_EXIST")

if [ "$STACK_STATUS" = "ROLLBACK_COMPLETE" ]; then
    echo -e "\n${YELLOW}Deleting failed stack before redeploying...${NC}"
    aws cloudformation delete-stack \
        --stack-name "${STACK_NAME}-${STAGE}" --region "$REGION"
    aws cloudformation wait stack-delete-complete \
        --stack-name "${STACK_NAME}-${STAGE}" --region "$REGION"
    echo -e "${GREEN}Stack deleted.${NC}"
fi

# ── SAM deploy ───────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Deploying with SAM...${NC}"
sam deploy \
    --template-file deploy/aws/template.yaml \
    --stack-name "${STACK_NAME}-${STAGE}" \
    --region "$REGION" \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides Stage="$STAGE" \
    --image-repository "${ECR_URI}" \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset

# ── Output ───────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"

API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}-${STAGE}" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text)

echo -e "\n${GREEN}API Endpoint:${NC} ${API_ENDPOINT}"

# ── Retrieve the generated API key value ─────────────────────────────────────
echo -e "\n${YELLOW}Retrieving API key...${NC}"
API_KEY_VALUE=$(aws apigateway get-api-keys \
    --region "$REGION" \
    --include-values \
    --query "items[?contains(name,'nlp-hc-sentiment')].value | [0]" \
    --output text 2>/dev/null || echo "")

if [ -n "$API_KEY_VALUE" ] && [ "$API_KEY_VALUE" != "None" ]; then
    echo -e "${GREEN}API Key:${NC} ${API_KEY_VALUE}"
else
    echo -e "${YELLOW}Could not auto-retrieve key. Run manually:${NC}"
    echo "aws apigateway get-api-keys --region ${REGION} --include-values --query \"items[?contains(name,'nlp-hc-sentiment')].{name:name,value:value}\" --output table"
    API_KEY_VALUE="<your-api-key>"
fi

echo -e "\n${YELLOW}Quick tests:${NC}"
echo "# Health check"
echo "curl -H 'X-Api-Key: ${API_KEY_VALUE}' '${API_ENDPOINT}/api/v1/health'"
echo ""
echo "# BERT Healthcare v2 (default)"
echo "curl -X POST '${API_ENDPOINT}/api/v1/analyze' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'X-Api-Key: ${API_KEY_VALUE}' \\"
echo "  -d '{\"text\": \"The patient is recovering well and responding positively to treatment.\", \"model_type\": \"bert_hc_v2\"}'"
echo ""
echo "# DistilBERT Healthcare v1"
echo "curl -X POST '${API_ENDPOINT}/api/v1/analyze' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'X-Api-Key: ${API_KEY_VALUE}' \\"
echo "  -d '{\"text\": \"The patient reported severe side effects and persistent pain after the procedure.\", \"model_type\": \"distilbert_hc\"}'"
