#!/bin/bash
# AWS Lambda Container Image Deployment — NLP Sentiment Analysis

set -e

STACK_NAME="${STACK_NAME:-nlp-sentiment}"
REGION="${AWS_REGION:-us-east-1}"
STAGE="${STAGE:-prod}"
IMAGE_NAME="nlp-sentiment"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}NLP Sentiment Analysis — AWS Deploy${NC}"
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

# ── Ensure lambda_handler.py exists ─────────────────────────────────────────
if [ ! -f lambda_handler.py ]; then
    echo -e "\n${YELLOW}Creating lambda_handler.py...${NC}"
    cat > lambda_handler.py << 'EOF'
from mangum import Mangum
from api.main import app

handler = Mangum(app, lifespan="off")
EOF
fi

# Ensure mangum is in requirements
if ! grep -q "mangum" requirements.txt; then
    echo "mangum>=0.17.0" >> requirements.txt
fi

# ── ECR repository ───────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Setting up ECR repository...${NC}"
aws ecr describe-repositories --repository-names "$IMAGE_NAME" --region "$REGION" &>/dev/null || \
    aws ecr create-repository --repository-name "$IMAGE_NAME" --region "$REGION"

# Authenticate Docker to ECR
aws ecr get-login-password --region "$REGION" | \
    docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# ── Build & push ─────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Building Docker image (this will take several minutes — models are large)...${NC}"
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
echo -e "\n${YELLOW}Quick test:${NC}"
echo "curl '${API_ENDPOINT}/api/v1/health'"
echo ""
echo "curl -X POST '${API_ENDPOINT}/api/v1/analyze' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"text\": \"This product is absolutely amazing I love everything about it\", \"model_type\": \"default\"}'"
