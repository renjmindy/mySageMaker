#!/bin/bash
# Google Cloud Run Deployment — NLP Sentiment Analysis

set -e

PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-nlp-sentiment}"
MODE="${MODE:-api}"   # api or ui

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}NLP Sentiment Analysis — GCP Deploy${NC}"
echo -e "${GREEN}========================================${NC}"

# ── Prerequisites ────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 &> /dev/null; then
    echo -e "${RED}Error: Not logged in${NC}"
    echo "Run: gcloud auth login"
    exit 1
fi

if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}Error: No GCP project ID set${NC}"
        echo "Run: gcloud config set project YOUR_PROJECT_ID"
        echo "Or:  export GCP_PROJECT_ID=your-project-id"
        exit 1
    fi
fi

echo -e "${GREEN}Project: ${PROJECT_ID}  Region: ${REGION}  Mode: ${MODE}${NC}"

# ── Enable APIs ──────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Enabling required GCP APIs...${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    --project="$PROJECT_ID"

# ── Build & push via Cloud Build ─────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo -e "\n${YELLOW}Building image with Cloud Build (this will take several minutes)...${NC}"
gcloud builds submit \
    --tag "${IMAGE_NAME}:latest" \
    --project="$PROJECT_ID" \
    --timeout=2400s

# ── Deploy to Cloud Run ──────────────────────────────────────────────────────
TARGET_PORT=8000
if [ "$MODE" = "ui" ]; then
    TARGET_PORT=7860
fi

echo -e "\n${YELLOW}Deploying to Cloud Run (mode=${MODE}, port=${TARGET_PORT})...${NC}"
gcloud run deploy "$SERVICE_NAME" \
    --image "${IMAGE_NAME}:latest" \
    --platform managed \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --memory 2Gi \
    --cpu 2 \
    --timeout 120s \
    --concurrency 5 \
    --min-instances 0 \
    --max-instances 5 \
    --port "$TARGET_PORT" \
    --allow-unauthenticated \
    --set-env-vars "MODE=${MODE},PORT=${TARGET_PORT}"

# ── Output ───────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --platform managed --region "$REGION" --project "$PROJECT_ID" \
    --format 'value(status.url)')

echo -e "\n${GREEN}Service URL:${NC} ${SERVICE_URL}"

if [ "$MODE" = "ui" ]; then
    echo -e "\n${YELLOW}Open in browser:${NC} ${SERVICE_URL}"
else
    echo -e "\n${YELLOW}Quick test:${NC}"
    echo "curl '${SERVICE_URL}/api/v1/health'"
    echo ""
    echo "curl -X POST '${SERVICE_URL}/api/v1/analyze' \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{\"text\": \"This product is absolutely amazing I love everything about it\", \"model_type\": \"default\"}'"
fi
