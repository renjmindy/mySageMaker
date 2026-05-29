# Azure Container Apps Deployment

Deploy the NLP Sentiment Analysis app to Azure Container Apps.  
Supports both API mode (FastAPI on port 8000) and UI mode (Gradio on port 7860).

## Free Tier

- **Azure Container Apps**: 180,000 vCPU-seconds/month, 360,000 GB-seconds/month
- **Azure Container Registry (Basic)**: First 5 GB storage free

## Prerequisites

1. **Azure CLI**
   ```bash
   # macOS
   brew install azure-cli
   # Linux: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
   ```

2. **Login**
   ```bash
   az login
   # If multiple subscriptions:
   az account set --subscription YOUR_SUBSCRIPTION_ID
   ```

## Quick Deploy

```bash
# From project root
chmod +x deploy/azure/deploy.sh

# Deploy API (default)
./deploy/azure/deploy.sh

# Deploy Gradio UI
MODE=ui ./deploy/azure/deploy.sh
```

## Configuration

```bash
export AZURE_RESOURCE_GROUP=nlp-sentiment-rg   # Resource group name
export AZURE_LOCATION=eastus                    # Azure region
export APP_NAME=nlp-sentiment                   # Container App name
export ACR_NAME=nlpsentimentacr                 # Registry name (globally unique)
export MODE=api                                 # api | ui
```

## Manual Deployment

```bash
# 1. Create resource group
az group create --name nlp-sentiment-rg --location eastus

# 2. Create ACR
az acr create --resource-group nlp-sentiment-rg --name nlpsentimentacr --sku Basic --admin-enabled true

# 3. Build and push image
az acr build --registry nlpsentimentacr --image nlp-sentiment:latest .

# 4. Deploy Container App (API mode)
az containerapp create \
  --name nlp-sentiment \
  --resource-group nlp-sentiment-rg \
  --image nlpsentimentacr.azurecr.io/nlp-sentiment:latest \
  --target-port 8000 \
  --ingress external \
  --cpu 2 --memory 4Gi \
  --min-replicas 0 --max-replicas 5 \
  --env-vars MODE=api PORT=8000

# 5. Deploy UI mode (separate service)
az containerapp create \
  --name nlp-sentiment-ui \
  --resource-group nlp-sentiment-rg \
  --image nlpsentimentacr.azurecr.io/nlp-sentiment:latest \
  --target-port 7860 \
  --ingress external \
  --cpu 2 --memory 4Gi \
  --min-replicas 0 --max-replicas 3 \
  --env-vars MODE=ui PORT=7860
```

## Testing

```bash
APP_URL=$(az containerapp show \
  --name nlp-sentiment --resource-group nlp-sentiment-rg \
  --query properties.configuration.ingress.fqdn -o tsv)
APP_URL="https://${APP_URL}"

# Health check
curl "${APP_URL}/api/v1/health"

# DistilBERT sentiment
curl -X POST "${APP_URL}/api/v1/analyze" \
  -H 'Content-Type: application/json' \
  -d '{"text": "This product is absolutely amazing I love everything about it", "model_type": "default"}'

# RoBERTa Twitter sentiment
curl -X POST "${APP_URL}/api/v1/analyze" \
  -H 'Content-Type: application/json' \
  -d '{"text": "Absolutely terrible experience, would not recommend to anyone", "model_type": "roberta"}'

# GoEmotions
curl -X POST "${APP_URL}/api/v1/analyze" \
  -H 'Content-Type: application/json' \
  -d '{"text": "The patient feels anxious and scared about the upcoming procedure", "model_type": "emotion"}'
```

## Cleanup

```bash
# Delete everything in the resource group
az group delete --name nlp-sentiment-rg --yes --no-wait
```

## Performance Notes

- **CPU**: 2 vCPUs (inference is CPU-bound; three models run in the same process)
- **Memory**: 4 GB (DistilBERT + RoBERTa + GoEmotions + spaCy ~2–3 GB)
- **Concurrency**: 5 requests/instance
- **Cold start**: ~30–60 s; warm requests ~500 ms–2 s
- Min replicas = 0 → scales to zero between requests to save cost

## Cost Estimate

For typical usage (10,000 requests/month):
- **Container Apps**: Free tier (under 180,000 vCPU-seconds)
- **Container Registry**: ~$5/month (Basic tier)
- **Log Analytics**: ~$2.76/GB ingested
- **Estimated Cost**: $5–10/month
