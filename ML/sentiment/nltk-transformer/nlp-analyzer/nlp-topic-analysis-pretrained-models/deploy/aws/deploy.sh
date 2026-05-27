#!/usr/bin/env bash
# =============================================================================
# deploy.sh — End-to-end deployment for the Healthcare PREM Topic Classifier
#
# Steps:
#   1. Resolve configuration (AWS account, region, app name)
#   2. Authenticate Docker with ECR
#   3. Build the multi-stage Docker image (includes model training)
#   4. Push the image to ECR
#   5. Deploy / update the CloudFormation stack
#      (ECR · Lambda · API Gateway · EventBridge warm-up rule · IAM)
#   6. Print the API endpoint and a cURL example
#
# Prerequisites:
#   • AWS CLI v2 installed and configured (aws configure)
#   • Docker daemon running
#   • Sufficient IAM permissions:
#       ecr:*, lambda:*, apigatewayv2:*, cloudformation:*, iam:*, events:*
#
# Usage:
#   cd <repo-root>
#   bash deploy/aws/deploy.sh [--region <aws-region>] [--app <app-name>]
#
# Options:
#   --region    AWS region (default: $AWS_DEFAULT_REGION or ap-southeast-2)
#   --app       Application name used for all resource names
#               (default: healthcare-topic-classifier)
#   --stack     CloudFormation stack name (default: <app>-stack)
#   --memory    Lambda memory in MB (default: 5120)
#   --timeout   Lambda timeout in seconds (default: 300)
#   --no-build  Skip Docker build (use last locally built image)
#   --no-push   Skip Docker push (image must already exist in ECR)
# =============================================================================
set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
APP_NAME="healthcare-topic-classifier"
REGION="${AWS_DEFAULT_REGION:-ap-southeast-2}"
STACK_NAME=""            # auto-derived below
LAMBDA_MEMORY=5120
LAMBDA_TIMEOUT=300
DO_BUILD=true
DO_PUSH=true
IMAGE_TAG="latest"

# ── Parse arguments ───────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --region)   REGION="$2";        shift 2 ;;
    --app)      APP_NAME="$2";      shift 2 ;;
    --stack)    STACK_NAME="$2";    shift 2 ;;
    --memory)   LAMBDA_MEMORY="$2"; shift 2 ;;
    --timeout)  LAMBDA_TIMEOUT="$2";shift 2 ;;
    --no-build) DO_BUILD=false;     shift   ;;
    --no-push)  DO_PUSH=false;      shift   ;;
    --tag)      IMAGE_TAG="$2";     shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

[[ -z "$STACK_NAME" ]] && STACK_NAME="${APP_NAME}-stack"

# ── Resolve project root (two dirs above this script) ─────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "═══════════════════════════════════════════════════════════"
echo "  Healthcare PREM Topic Classifier — Deployment"
echo "═══════════════════════════════════════════════════════════"
echo "  App name   : ${APP_NAME}"
echo "  AWS region : ${REGION}"
echo "  Stack name : ${STACK_NAME}"
echo "  Project    : ${PROJECT_ROOT}"
echo "═══════════════════════════════════════════════════════════"

# ── 1. Resolve AWS account ID ─────────────────────────────────────────────────
echo ""
echo "[1/6] Resolving AWS account ..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region "${REGION}")
echo "      Account ID : ${ACCOUNT_ID}"
ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
ECR_REPO_URI="${ECR_REGISTRY}/${APP_NAME}"
IMAGE_URI="${ECR_REPO_URI}:${IMAGE_TAG}"
echo "      Image URI  : ${IMAGE_URI}"

# ── 2. ECR login ──────────────────────────────────────────────────────────────
echo ""
echo "[2/6] Authenticating with ECR ..."
aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

# Ensure ECR repo exists (stack may create it, but we need it before push)
aws ecr describe-repositories --repository-names "${APP_NAME}" \
  --region "${REGION}" > /dev/null 2>&1 \
  || aws ecr create-repository --repository-name "${APP_NAME}" \
       --image-scanning-configuration scanOnPush=true \
       --region "${REGION}"
echo "      ECR repository ready."

# ── 3. Docker build ───────────────────────────────────────────────────────────
if [[ "${DO_BUILD}" == "true" ]]; then
  echo ""
  echo "[3/6] Building Docker image (this includes model training — ~10 min) ..."
  cd "${PROJECT_ROOT}"
  docker build \
    --platform linux/amd64 \
    -f deploy/aws/Dockerfile.healthcare \
    -t "${APP_NAME}:${IMAGE_TAG}" \
    -t "${IMAGE_URI}" \
    .
  echo "      Build complete."
else
  echo ""
  echo "[3/6] Skipping Docker build (--no-build)."
  # Re-tag local image for ECR push
  docker tag "${APP_NAME}:${IMAGE_TAG}" "${IMAGE_URI}" 2>/dev/null || true
fi

# ── 4. Docker push ────────────────────────────────────────────────────────────
if [[ "${DO_PUSH}" == "true" ]]; then
  echo ""
  echo "[4/6] Pushing image to ECR ..."
  docker push "${IMAGE_URI}"
  echo "      Push complete."
else
  echo ""
  echo "[4/6] Skipping Docker push (--no-push)."
fi

# ── 5. CloudFormation deploy ──────────────────────────────────────────────────
echo ""
echo "[5/6] Deploying CloudFormation stack '${STACK_NAME}' ..."
cd "${SCRIPT_DIR}"
aws cloudformation deploy \
  --stack-name "${STACK_NAME}" \
  --template-file cloudformation.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}" \
  --parameter-overrides \
      AppName="${APP_NAME}" \
      ImageUri="${IMAGE_URI}" \
      LambdaMemoryMB="${LAMBDA_MEMORY}" \
      LambdaTimeoutSec="${LAMBDA_TIMEOUT}" \
  --no-fail-on-empty-changeset

echo "      Stack deployment complete."

# ── 6. Retrieve outputs and print summary ─────────────────────────────────────
echo ""
echo "[6/6] Retrieving stack outputs ..."
OUTPUTS=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query "Stacks[0].Outputs" \
  --output json)

API_ENDPOINT=$(echo "${OUTPUTS}" \
  | python3 -c "import json,sys; o={x['OutputKey']:x['OutputValue'] for x in json.load(sys.stdin)}; print(o.get('ClassifyUrl',''))")

HEALTH_URL=$(echo "${OUTPUTS}" \
  | python3 -c "import json,sys; o={x['OutputKey']:x['OutputValue'] for x in json.load(sys.stdin)}; print(o.get('HealthUrl',''))")

# ── Retrieve API key value ─────────────────────────────────────────────────────
echo "      Retrieving API key ..."
API_KEY_VALUE=$(aws apigateway get-api-keys \
  --region "${REGION}" \
  --include-values \
  --query "items[?contains(name,'${APP_NAME}')].value | [0]" \
  --output text)

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅  Deployment successful!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  API Key:  ${API_KEY_VALUE}"
echo "  Header:   x-api-key: ${API_KEY_VALUE}"
echo ""
echo "  Health check:"
echo "    curl ${HEALTH_URL} -H 'x-api-key: ${API_KEY_VALUE}'"
echo ""
echo "  Classify endpoint:"
echo "    ${API_ENDPOINT}"
echo ""
echo "  Example cURL:"
cat <<CURL
    curl -s -X POST '${API_ENDPOINT}' \\
      -H 'Content-Type: application/json' \\
      -H 'x-api-key: ${API_KEY_VALUE}' \\
      -d '{
        "texts": [
          "Dr Smith was very thorough and answered all my questions.",
          "I waited over two hours past my appointment time.",
          "The Zedoc portal kept crashing when I tried to book online.",
          "The car park was very limited and difficult to navigate."
        ],
        "models": ["all"],
        "top_n": 3
      }' | python3 -m json.tool
CURL
echo ""
echo "  EventBridge warmup rule: every 5 minutes (all 6 models)"
echo "═══════════════════════════════════════════════════════════"
