#!/bin/bash
# Azure Container Apps Deployment — NLP Sentiment Analysis

set -e

RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-nlp-sentiment-rg}"
LOCATION="${AZURE_LOCATION:-eastus}"
APP_NAME="${APP_NAME:-nlp-sentiment}"
ACR_NAME="${ACR_NAME:-nlpsentimentacr}"   # Must be globally unique — suffix added below
MODE="${MODE:-api}"                        # api or ui

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}NLP Sentiment Analysis — Azure Deploy${NC}"
echo -e "${GREEN}========================================${NC}"

# ── Prerequisites ────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed${NC}"
    echo "Install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

if ! az account show &> /dev/null; then
    echo -e "${RED}Error: Not logged in to Azure${NC}"
    echo "Run: az login"
    exit 1
fi

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo -e "${GREEN}Subscription: ${SUBSCRIPTION_ID}  Location: ${LOCATION}  Mode: ${MODE}${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

# ── Resource group ───────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Creating resource group '${RESOURCE_GROUP}'...${NC}"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

# ── Azure Container Registry ─────────────────────────────────────────────────
echo -e "\n${YELLOW}Creating Azure Container Registry...${NC}"
# Append timestamp to ensure global uniqueness
ACR_NAME="${ACR_NAME}$(date +%s | tail -c 5)"
az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACR_NAME" \
    --sku Basic \
    --admin-enabled true \
    --output none

ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)

# ── Build & push via ACR Build ───────────────────────────────────────────────
echo -e "\n${YELLOW}Building and pushing Docker image (this will take several minutes)...${NC}"
az acr build \
    --registry "$ACR_NAME" \
    --image "${APP_NAME}:latest" \
    --file Dockerfile \
    . \
    --no-logs

# ── Container Apps setup ─────────────────────────────────────────────────────
echo -e "\n${YELLOW}Installing/upgrading Container Apps extension...${NC}"
az extension add --name containerapp --upgrade --yes

az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait

# ── ARM template deployment ──────────────────────────────────────────────────
TARGET_PORT=8000
if [ "$MODE" = "ui" ]; then
    TARGET_PORT=7860
fi

echo -e "\n${YELLOW}Deploying Container App (mode=${MODE}, port=${TARGET_PORT})...${NC}"
az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file deploy/azure/azure-deploy.json \
    --parameters containerAppName="$APP_NAME" \
    --parameters containerImage="${ACR_LOGIN_SERVER}/${APP_NAME}:latest" \
    --parameters containerRegistryServer="$ACR_LOGIN_SERVER" \
    --parameters containerRegistryUsername="$ACR_USERNAME" \
    --parameters containerRegistryPassword="$ACR_PASSWORD" \
    --parameters appMode="$MODE" \
    --parameters targetPort="$TARGET_PORT" \
    --output none

# ── Output ───────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"

APP_FQDN=$(az containerapp show \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.configuration.ingress.fqdn -o tsv)
APP_URL="https://${APP_FQDN}"

echo -e "\n${GREEN}App URL:${NC} ${APP_URL}"

if [ "$MODE" = "ui" ]; then
    echo -e "\n${YELLOW}Open in browser:${NC} ${APP_URL}"
else
    echo -e "\n${YELLOW}Quick test:${NC}"
    echo "curl '${APP_URL}/api/v1/health'"
    echo ""
    echo "curl -X POST '${APP_URL}/api/v1/analyze' \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{\"text\": \"This product is absolutely amazing I love everything about it\", \"model_type\": \"default\"}'"
fi

echo -e "\n${YELLOW}Resources created:${NC}"
echo "  Resource Group:     ${RESOURCE_GROUP}"
echo "  Container Registry: ${ACR_NAME}"
echo "  Container App:      ${APP_NAME}"
