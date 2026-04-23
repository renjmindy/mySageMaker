#!/usr/bin/env bash
# PII Detection & Sentiment Analysis — AWS Deployment Script
# Uses AWS SAM with a Docker container image (no S3 bucket needed)

set -e

# ── Configuration ─────────────────────────────────────────────────────────────
STACK_NAME="${STACK_NAME:-pii-detection-api}"
REGION="${AWS_REGION:-us-east-1}"
STAGE="${STAGE:-prod}"
ECR_REPO="${ECR_REPO:-pii-detection-api}"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  PII Detection & Sentiment — AWS Deploy   ${NC}"
echo -e "${GREEN}============================================${NC}"

# ── Prerequisites ─────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

if ! command -v aws &>/dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    echo "Install: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

if ! command -v sam &>/dev/null; then
    echo -e "${RED}Error: AWS SAM CLI is not installed${NC}"
    echo "Install: pip install aws-sam-cli"
    exit 1
fi

if ! command -v docker &>/dev/null; then
    echo -e "${RED}Error: Docker is not installed or not running${NC}"
    echo "Install: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}Error: AWS credentials not configured${NC}"
    echo "Run: aws configure"
    exit 1
fi

echo -e "${GREEN}Prerequisites OK${NC}"

# ── ECR: ensure repository exists ─────────────────────────────────────────────
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}"

echo -e "\n${YELLOW}Ensuring ECR repository exists: ${ECR_REPO}${NC}"
aws ecr describe-repositories --repository-names "${ECR_REPO}" \
    --region "${REGION}" > /dev/null 2>&1 \
  || aws ecr create-repository --repository-name "${ECR_REPO}" \
       --region "${REGION}" > /dev/null
echo -e "${GREEN}ECR repository ready: ${ECR_URI}${NC}"

# ── ECR login ─────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Logging in to ECR...${NC}"
aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin \
      "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
echo -e "${GREEN}ECR login successful${NC}"

# ── Navigate to project root ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# ── SAM Build ─────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Building SAM application (Docker image)...${NC}"
sam build --template-file template.yaml
echo -e "${GREEN}Build complete${NC}"

# ── SAM Deploy ────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Deploying stack '${STACK_NAME}-${STAGE}' to ${REGION}...${NC}"
sam deploy \
    --stack-name "${STACK_NAME}-${STAGE}" \
    --image-repositories "AnalyzeFunction=${ECR_URI}" \
    --region "${REGION}" \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides "Stage=${STAGE}" \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset

# ── Summary ───────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}============================================${NC}"
echo -e "${GREEN}  Deployment complete!                      ${NC}"
echo -e "${GREEN}============================================${NC}"

API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}-${STAGE}" \
    --region "${REGION}" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text)

echo -e "\n${GREEN}API Endpoint:${NC} ${API_ENDPOINT}"
echo -e "\n${YELLOW}Test the API:${NC}"
echo "curl -X POST '${API_ENDPOINT}' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"data\": [{\"patient_id\": \"P001\", \"text\": \"John Smith, DOB 01/01/1980, feels great!\"}]}'"
