# Google Cloud Run Deployment

Deploy the NLP Sentiment Analysis app to Google Cloud Run.  
Both API mode (port 8000) and Gradio UI mode (port 7860) are supported.

## Free Tier

- **Cloud Run**: 2 million requests/month, 180,000 vCPU-seconds, 360,000 GB-seconds
- **Container Registry**: 0.5 GB storage free

## Prerequisites

1. **Google Cloud SDK**
   ```bash
   # macOS
   brew install google-cloud-sdk
   # Linux: https://cloud.google.com/sdk/docs/install
   ```

2. **Authenticate and set project**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

## Quick Deploy

```bash
# From project root
chmod +x deploy/gcp/deploy.sh

# Deploy API (default)
./deploy/gcp/deploy.sh

# Deploy Gradio UI
MODE=ui ./deploy/gcp/deploy.sh
```

## Configuration

```bash
export GCP_PROJECT_ID=my-project       # GCP project ID (required)
export GCP_REGION=us-central1          # Region (default: us-central1)
export SERVICE_NAME=nlp-sentiment      # Cloud Run service name
export MODE=api                        # api | ui
```

## Manual Deployment

```bash
# Enable APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com

# Build and push
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/nlp-sentiment --timeout=2400s

# Deploy API
gcloud run deploy nlp-sentiment \
  --image gcr.io/YOUR_PROJECT_ID/nlp-sentiment \
  --platform managed \
  --region us-central1 \
  --memory 2Gi --cpu 2 \
  --timeout 120s --concurrency 5 \
  --allow-unauthenticated \
  --set-env-vars MODE=api,PORT=8000

# Deploy Gradio UI
gcloud run deploy nlp-sentiment-ui \
  --image gcr.io/YOUR_PROJECT_ID/nlp-sentiment \
  --platform managed \
  --region us-central1 \
  --memory 2Gi --cpu 2 \
  --port 7860 \
  --allow-unauthenticated \
  --set-env-vars MODE=ui,PORT=7860
```

## CI/CD with Cloud Build

```bash
# Trigger a build manually
gcloud builds submit --config deploy/gcp/cloudbuild.yaml \
  --substitutions _REGION=us-central1

# Or connect your GitHub repo to Cloud Build for automatic deploys on push
```

## Testing

```bash
SERVICE_URL=$(gcloud run services describe nlp-sentiment \
  --platform managed --region us-central1 --format 'value(status.url)')

# Health check
curl "${SERVICE_URL}/api/v1/health"

# DistilBERT sentiment
curl -X POST "${SERVICE_URL}/api/v1/analyze" \
  -H 'Content-Type: application/json' \
  -d '{"text": "This product is absolutely amazing I love everything about it", "model_type": "default"}'

# GoEmotions
curl -X POST "${SERVICE_URL}/api/v1/analyze" \
  -H 'Content-Type: application/json' \
  -d '{"text": "The patient feels anxious and scared about the upcoming procedure", "model_type": "emotion"}'
```

## Cleanup

```bash
gcloud run services delete nlp-sentiment --region us-central1
gcloud container images delete gcr.io/YOUR_PROJECT_ID/nlp-sentiment --force-delete-tags
```

## Performance Notes

- **Memory**: 2 GB (recommended for all three models loaded simultaneously)
- **CPU**: 2 vCPUs
- **Concurrency**: 5 requests/instance (model inference is CPU-bound)
- **Cold start**: ~30–60 s; warm requests ~500 ms–2 s
- Min instances = 0 → scales to zero to save cost

## Cost Estimate

For typical usage (10,000 requests/month):
- **Cloud Run**: Free tier
- **Container Registry**: ~$0.03/GB/month
- **Estimated Cost**: $0–1/month
