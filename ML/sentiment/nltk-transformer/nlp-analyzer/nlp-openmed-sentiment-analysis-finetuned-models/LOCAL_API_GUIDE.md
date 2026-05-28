# Local Deployment & API Usage Guide
### NLP OpenMed Sentiment Analysis + PII De-identification

**Audience:** Junior software engineers setting up and calling the APIs locally  
**Last updated:** May 2026

---

## Table of Contents

1. [What This System Does](#1-what-this-system-does)
2. [How It Works — The Big Picture](#2-how-it-works--the-big-picture)
3. [Prerequisites](#3-prerequisites)
4. [Getting the Docker Image](#4-getting-the-docker-image)
   - [Option A — You received a `.tar.gz` file](#option-a--you-received-a-targz-file)
   - [Option B — You have the source code](#option-b--you-have-the-source-code)
5. [Starting the Container](#5-starting-the-container)
6. [Verifying Everything Is Running](#6-verifying-everything-is-running)
7. [Calling the PII De-identification API](#7-calling-the-pii-de-identification-api)
   - [7.1 Detect PII entities](#71-detect-pii-entities)
   - [7.2 De-identify text](#72-de-identify-text)
   - [7.3 Replacement strategies explained](#73-replacement-strategies-explained)
   - [7.4 Batch process multiple records](#74-batch-process-multiple-records)
   - [7.5 List all supported entity types](#75-list-all-supported-entity-types)
8. [Calling the Sentiment Analysis API](#8-calling-the-sentiment-analysis-api)
   - [8.1 Analyse text sentiment](#81-analyse-text-sentiment)
   - [8.2 Choosing a model](#82-choosing-a-model)
   - [8.3 Understanding the response](#83-understanding-the-response)
9. [The Recommended Workflow — PII First, Then Sentiment](#9-the-recommended-workflow--pii-first-then-sentiment)
10. [Python Examples (Copy-Paste Ready)](#10-python-examples-copy-paste-ready)
11. [Interactive API Docs (Swagger UI)](#11-interactive-api-docs-swagger-ui)
12. [Troubleshooting](#12-troubleshooting)
13. [Stopping and Cleaning Up](#13-stopping-and-cleaning-up)
14. [Quick Reference Card](#14-quick-reference-card)

---

## 1. What This System Does

This package gives you **two REST APIs** running inside a single Docker container on your laptop — no internet connection, no cloud account, no API keys required after setup.

| API | Port | What it does |
|-----|------|--------------|
| **PII De-identification** | `8001` | Finds and removes protected health information (names, dates, SSNs, MRNs, etc.) from clinical text to comply with HIPAA |
| **Sentiment Analysis** | `8000` | Classifies the emotional tone of clinical text using 13 different AI models |

**Why two APIs?** Clinical text often contains sensitive patient data. The recommended workflow is to **de-identify first** (strip out patient names, dates, etc.) and **then run sentiment analysis** on the anonymised text. The two APIs are already wired together inside the container to do this automatically.

---

## 2. How It Works — The Big Picture

```
Your laptop
┌──────────────────────────────────────────────────────────────────┐
│   Docker container  (everything runs offline inside here)        │
│                                                                  │
│   ┌─────────────────────────┐    ┌──────────────────────────┐   │
│   │   PII De-identification │    │  Sentiment Analysis API  │   │
│   │   API  (port 8001)      │◄───│  (port 8000)             │   │
│   │                         │    │  • 13 AI models          │   │
│   │   • OpenMed NER model   │    │  • NLP preprocessing     │   │
│   │   • HIPAA 18 identifiers│    │  • word distribution     │   │
│   └─────────────────────────┘    └──────────────────────────┘   │
│                                                                  │
│   All AI models are baked into the image — no downloads needed  │
└───────────────┬─────────────────────────────┬────────────────────┘
                ↓                             ↓
         localhost:8001                  localhost:8000
         (PII API)                       (Sentiment API)
```

---

## 3. Prerequisites

You only need **Docker** installed. You do not need Python, pip, or any other tools on your machine.

### Install Docker

| Your OS | Link |
|---------|------|
| Windows 10/11 | https://docs.docker.com/desktop/install/windows-install/ |
| macOS | https://docs.docker.com/desktop/install/mac-install/ |
| Ubuntu / Debian | https://docs.docker.com/engine/install/ubuntu/ |

After installing, verify Docker works by opening a terminal (or PowerShell on Windows) and running:

```bash
docker --version
```

You should see something like:
```
Docker version 27.0.3, build 7d4bcd8
```

> **Tip for Windows users:** Make sure Docker Desktop is running (you'll see the Docker whale icon in your taskbar) before you run any commands.

---

## 4. Getting the Docker Image

There are two ways to get the image. Pick the one that applies to you.

---

### Option A — You received a `.tar.gz` file

This is the most common case. You were sent two files:
- `nlp-openmed-local.tar.gz` — the Docker image (large file, ~8–12 GB)
- `load-and-run.sh` — a helper script

Place both files in the same folder, then run:

```bash
bash load-and-run.sh
```

That's it. The script will:
1. Load the image into Docker
2. Start the container
3. Print the URLs where the APIs are available

If you prefer to do it manually (step by step):

```bash
# Step 1 — Load the image (this imports it into Docker)
docker load < nlp-openmed-local.tar.gz

# Step 2 — Start the container (jump to Section 5)
```

> **How long does loading take?** Loading a 10 GB image typically takes 3–8 minutes depending on your disk speed. You will see a progress bar.

---

### Option B — You have the source code

If you have cloned both repositories, build the image yourself:

```bash
# Navigate to the sentiment analysis project
cd nlp-openmed-sentiment-analysis-finetuned-models

# Run the build script (takes 20–40 minutes the first time)
bash scripts/package-image.sh
```

The script builds the image and saves it as `nlp-openmed-local.tar.gz` in the same directory. First-time builds are slow because all 14 AI models are downloaded from HuggingFace and baked into the image. Subsequent builds use Docker's layer cache and are much faster.

---

## 5. Starting the Container

Once the image is loaded, start it with:

```bash
docker run -d \
  --name nlp-openmed \
  --restart unless-stopped \
  -p 8000:8000 \
  -p 8001:8001 \
  nlp-openmed-local:latest
```

**What these flags mean:**

| Flag | Meaning |
|------|---------|
| `-d` | Run in the background (detached mode) |
| `--name nlp-openmed` | Give the container a name so you can refer to it easily |
| `--restart unless-stopped` | Restart automatically if Docker restarts (e.g., after reboot) |
| `-p 8000:8000` | Map port 8000 on your laptop to port 8000 in the container (Sentiment API) |
| `-p 8001:8001` | Map port 8001 on your laptop to port 8001 in the container (PII API) |

You should see a long container ID printed, which means it started successfully.

**Check that it is running:**
```bash
docker ps
```

Expected output:
```
CONTAINER ID   IMAGE                   STATUS                    PORTS
a3b4c5d6e7f8   nlp-openmed-local:...   Up 5 seconds (health: starting)   0.0.0.0:8000->8000/tcp, 0.0.0.0:8001->8001/tcp
```

---

## 6. Verifying Everything Is Running

The AI models take **2–3 minutes to load** after the container starts. The status will change from `(health: starting)` to `(healthy)`.

### Check health via terminal

```bash
# Check the Sentiment Analysis API
curl http://localhost:8000/api/v1/health

# Check the PII De-identification API
curl http://localhost:8001/api/v1/health
```

**Sentiment API healthy response:**
```json
{
  "status": "ok",
  "models_loaded": []
}
```

**PII API healthy response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_name": "OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1",
  "version": "1.0.0"
}
```

> **If you get "connection refused":** The container is still warming up. Wait 30 seconds and try again.

### View live logs

```bash
docker logs -f nlp-openmed
```

Press `Ctrl+C` to stop watching logs (the container keeps running).

---

## 7. Calling the PII De-identification API

The PII API runs at `http://localhost:8001`. It removes protected health information from clinical text.

All requests use:
- Method: `POST`
- Content-Type: `application/json`

---

### 7.1 Detect PII Entities

Find all PII in text without replacing it — useful when you want to see what would be detected before committing to de-identification.

**Endpoint:** `POST http://localhost:8001/api/v1/detect`

**Request fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | Yes | — | The clinical text to analyse |
| `confidence_threshold` | float | No | `0.5` | Only return entities with confidence above this value (0.0–1.0) |

**cURL example:**
```bash
curl -X POST http://localhost:8001/api/v1/detect \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Patient John Smith (DOB: 03/15/1985, MRN: 78432) was admitted on 01/10/2024. Contact: 555-123-4567."
  }'
```

**Expected response:**
```json
{
  "entities": [
    {
      "entity_type": "NAME",
      "text": "John Smith",
      "start": 8,
      "end": 18,
      "confidence": 0.9932
    },
    {
      "entity_type": "DATE",
      "text": "03/15/1985",
      "start": 25,
      "end": 35,
      "confidence": 0.9871
    },
    {
      "entity_type": "MRN",
      "text": "78432",
      "start": 42,
      "end": 47,
      "confidence": 0.8654
    },
    {
      "entity_type": "DATE",
      "text": "01/10/2024",
      "start": 63,
      "end": 73,
      "confidence": 0.9741
    },
    {
      "entity_type": "PHONE",
      "text": "555-123-4567",
      "start": 84,
      "end": 96,
      "confidence": 0.9912
    }
  ],
  "entity_count": 5,
  "text_length": 97
}
```

**Response fields explained:**

| Field | Meaning |
|-------|---------|
| `entity_type` | What kind of PII was found (NAME, DATE, SSN, MRN, PHONE, etc.) |
| `text` | The exact text that was detected as PII |
| `start` / `end` | Character positions in the original text (useful for highlighting) |
| `confidence` | How confident the AI is that this is PII (0 = unsure, 1 = certain) |
| `entity_count` | Total number of PII items found |

---

### 7.2 De-identify Text

Replace all PII in the text with safe placeholders.

**Endpoint:** `POST http://localhost:8001/api/v1/deidentify`

**Request fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | Yes | — | The text to de-identify |
| `strategy` | string | No | `"placeholder"` | How to replace PII (see Section 7.3) |
| `entity_types` | list of strings | No | `null` | Only redact these types (e.g. `["NAME", "SSN"]`). Omit to redact everything. |
| `confidence_threshold` | float | No | `0.5` | Minimum confidence to treat as PII |

**cURL example:**
```bash
curl -X POST http://localhost:8001/api/v1/deidentify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Patient John Smith (DOB: 03/15/1985, MRN: 78432) was admitted on 01/10/2024. Contact: 555-123-4567.",
    "strategy": "placeholder"
  }'
```

**Expected response:**
```json
{
  "deidentified_text": "Patient [NAME] (DOB: [DATE], MRN: [MRN]) was admitted on [DATE]. Contact: [PHONE].",
  "entities_found": [
    { "entity_type": "NAME",  "text": "John Smith",   "start": 8,  "end": 18, "confidence": 0.9932 },
    { "entity_type": "DATE",  "text": "03/15/1985",   "start": 25, "end": 35, "confidence": 0.9871 },
    { "entity_type": "MRN",   "text": "78432",        "start": 42, "end": 47, "confidence": 0.8654 },
    { "entity_type": "DATE",  "text": "01/10/2024",   "start": 63, "end": 73, "confidence": 0.9741 },
    { "entity_type": "PHONE", "text": "555-123-4567", "start": 84, "end": 96, "confidence": 0.9912 }
  ],
  "replacements_made": {
    "John Smith":   "[NAME]",
    "03/15/1985":   "[DATE]",
    "78432":        "[MRN]",
    "01/10/2024":   "[DATE]",
    "555-123-4567": "[PHONE]"
  },
  "entity_count": 5
}
```

**Redact only specific entity types** (e.g. only names and SSNs, leave dates as-is):
```bash
curl -X POST http://localhost:8001/api/v1/deidentify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Patient John Smith (DOB: 03/15/1985, SSN: 123-45-6789) reported pain.",
    "strategy": "placeholder",
    "entity_types": ["NAME", "SSN"]
  }'
```

---

### 7.3 Replacement Strategies Explained

| Strategy | Description | Example output |
|----------|-------------|----------------|
| `"placeholder"` | Generic label in brackets | `John Smith` → `[NAME]` |
| `"redact"` | Black bar of the same length | `John Smith` → `██████████` |
| `"consistent"` | Same entity always gets the same fake value — useful for analysis where you need to track that "Patient A" appears multiple times | `John Smith` → `Alex Johnson` (always the same fake name) |
| `"hash"` | Deterministic pseudonym based on a hash — same input always produces the same output, but it is not reversible | `John Smith` → `[NAME-a3f2c]` |

**When to use which:**
- Use `placeholder` when the output is just for downstream NLP processing (most common)
- Use `redact` when producing reports shown to humans
- Use `consistent` when studying how the same patient appears across multiple records
- Use `hash` when you need referential integrity but cannot store the original values

---

### 7.4 Batch Process Multiple Records

Process many patient notes in a single request (up to 100 records per call).

**Endpoint:** `POST http://localhost:8001/api/v1/batch`

```bash
curl -X POST http://localhost:8001/api/v1/batch \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {
        "patient_id": "PT-001",
        "text": "Mary Johnson, 42, presented with chest pain on 02/20/2024."
      },
      {
        "patient_id": "PT-002",
        "text": "Robert Davis (MRN 55521) discharged on 03/01/2024, phone 555-987-6543."
      }
    ],
    "strategy": "placeholder"
  }'
```

**Expected response:**
```json
{
  "results": [
    {
      "patient_id": "PT-001",
      "original_text": "Mary Johnson, 42, presented with chest pain on 02/20/2024.",
      "deidentified_text": "[NAME], 42, presented with chest pain on [DATE].",
      "entity_count": 2
    },
    {
      "patient_id": "PT-002",
      "original_text": "Robert Davis (MRN 55521) discharged on 03/01/2024, phone 555-987-6543.",
      "deidentified_text": "[NAME] (MRN [MRN]) discharged on [DATE], phone [PHONE].",
      "entity_count": 4
    }
  ],
  "total_entities": 6,
  "documents_processed": 2
}
```

> **Note:** The `patient_id` you send is returned as-is — it is never treated as PII. Use it to match results back to your source records.

---

### 7.5 List All Supported Entity Types

```bash
curl http://localhost:8001/api/v1/entities
```

This returns all 22 entity types with descriptions and examples. Useful for understanding what the model can detect.

---

## 8. Calling the Sentiment Analysis API

The Sentiment API runs at `http://localhost:8000`. It classifies the emotional tone of text using 13 different AI models.

---

### 8.1 Analyse Text Sentiment

**Endpoint:** `POST http://localhost:8000/api/v1/analyze`

**Request fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | Yes | — | Text to analyse (minimum 4 words, maximum 300 words) |
| `model_type` | string | No | `"bert_hc_v2"` | Which AI model to use (see Section 8.2) |

**cURL example:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The nursing staff were incredibly kind and attentive. The room was clean and I felt well cared for throughout my stay.",
    "model_type": "bert_hc_v2"
  }'
```

---

### 8.2 Choosing a Model

There are 13 models available, split into two groups:

#### Healthcare Fine-tuned Models (recommended for clinical text)

| `model_type` value | Display name | Output labels |
|--------------------|--------------|---------------|
| `bert_hc_v2` | BERT Healthcare v2 | NEGATIVE / NEUTRAL / POSITIVE |
| `distilroberta_hc_v2` | DistilRoBERTa Healthcare v2 | NEGATIVE / NEUTRAL / POSITIVE |
| `distilbert_hc_v2` | DistilBERT Healthcare v2 | NEGATIVE / NEUTRAL / POSITIVE |
| `bert_hc` | BERT Healthcare | NEGATIVE / NEUTRAL / POSITIVE |
| `distilbert_hc` | DistilBERT Healthcare | NEGATIVE / NEUTRAL / POSITIVE |
| `distilroberta_hc` | DistilRoBERTa Healthcare | NEGATIVE / NEUTRAL / POSITIVE |

#### General-Purpose Pretrained Models

| `model_type` value | Display name | Output labels |
|--------------------|--------------|---------------|
| `default` | DistilBERT SST-2 | NEGATIVE / POSITIVE |
| `roberta` | BERT Multilingual | 1 STAR / 2 STARS / 3 STARS / 4 STARS / 5 STARS |
| `emotion` | GoEmotions | ANGER / DISGUST / FEAR / JOY / NEUTRAL / SADNESS / SURPRISE |
| `amazon` | Amazon Reviews BERT | NEGATIVE / POSITIVE |
| `twitter` | RoBERTa Twitter | NEGATIVE / NEUTRAL / POSITIVE |
| `sst2` | BERT SST-2 | NEGATIVE / POSITIVE |
| `zeroshot` | BART Large MNLI | POSITIVE / NEGATIVE / NEUTRAL |

**Which model should I use?**
- For clinical/patient feedback text → start with `bert_hc_v2`
- For detecting specific emotions (anger, fear, joy, etc.) → use `emotion`
- For star-rating style scoring → use `roberta`
- When you are not sure of the category → use `zeroshot`

---

### 8.3 Understanding the Response

```json
{
  "sentiment": "POSITIVE",
  "probabilities": [0.0234, 0.0412, 0.9354],
  "labels": ["NEGATIVE", "NEUTRAL", "POSITIVE"],
  "model_type": "bert_hc_v2",
  "redacted_text": "The nursing staff were incredibly kind and attentive...",
  "cleaned_text": "nursing staff incredibly kind attentive room clean felt well cared stay",
  "tokenized_text": ["nursing", "staff", "incredibly", "kind", "attentive", "room", "clean", "felt", "well", "cared", "stay"],
  "lemmatized_text": ["nurse", "staff", "incredibly", "kind", "attentive", "room", "clean", "feel", "well", "care", "stay"],
  "ner": [],
  "word_distribution": {
    "positive": 8,
    "neutral": 2,
    "negative": 1
  },
  "total_words": 11
}
```

**Response fields explained:**

| Field | Meaning |
|-------|---------|
| `sentiment` | The top predicted label (e.g. `"POSITIVE"`) |
| `probabilities` | Confidence scores for each label — they add up to 1.0 |
| `labels` | The label names, in the same order as `probabilities` |
| `model_type` | Which model produced this result |
| `redacted_text` | Text after PII was automatically removed by the internal PII service |
| `cleaned_text` | Text after NLP preprocessing (stop words removed, etc.) |
| `tokenized_text` | Individual words extracted from the text |
| `lemmatized_text` | Words reduced to their root form (e.g. "caring" → "care") |
| `ner` | Named entities found in the text (e.g. organisation names) |
| `word_distribution` | How many words scored as positive / neutral / negative |
| `total_words` | Number of words that were analysed |

**Reading probabilities:**  
If `labels` is `["NEGATIVE", "NEUTRAL", "POSITIVE"]` and `probabilities` is `[0.0234, 0.0412, 0.9354]`, that means the model is **93.5% confident** the text is POSITIVE, 4.1% neutral, and 2.3% negative.

---

## 9. The Recommended Workflow — PII First, Then Sentiment

When you have real patient data, always de-identify before analysing. Here is the safe, step-by-step workflow:

**Step 1 — Send raw clinical text to the PII API:**
```bash
curl -X POST http://localhost:8001/api/v1/deidentify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Patient Emma Brown (MRN 44123, DOB 06/12/1978) states she is very pleased with Dr. Wilson'\''s care.",
    "strategy": "placeholder"
  }'
```

**Step 2 — Take the `deidentified_text` from the response:**
```
"Patient [NAME] (MRN [MRN], DOB [DATE]) states she is very pleased with [PROVIDER]'\''s care."
```

**Step 3 — Send the de-identified text to the Sentiment API:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Patient [NAME] (MRN [MRN], DOB [DATE]) states she is very pleased with [PROVIDER]'\''s care.",
    "model_type": "bert_hc_v2"
  }'
```

> **Good news:** The Sentiment API already does this automatically. When you send text directly to `/analyze`, it calls the PII service internally, strips PHI, and then runs sentiment on the clean text. The `redacted_text` field in the response shows you exactly what was analysed. You only need to call the PII API separately if you want more control over the redaction (e.g. choosing a different strategy or only redacting certain entity types).

---

## 10. Python Examples (Copy-Paste Ready)

Make sure you have `requests` installed:
```bash
pip install requests
```

### De-identify a single note

```python
import requests

PII_URL = "http://localhost:8001/api/v1"

note = (
    "Patient Sarah Lee (DOB: 07/04/1990, SSN: 234-56-7890, MRN: 99812) "
    "was seen by Dr. James Patel on 04/15/2024 at City General Hospital. "
    "She reported moderate lower back pain. Phone: 617-555-0198."
)

response = requests.post(
    f"{PII_URL}/deidentify",
    json={"text": note, "strategy": "placeholder"}
)
response.raise_for_status()

result = response.json()
print("De-identified text:")
print(result["deidentified_text"])
print(f"\nEntities removed: {result['entity_count']}")
for entity in result["entities_found"]:
    print(f"  [{entity['entity_type']}]  '{entity['text']}'  (confidence: {entity['confidence']:.0%})")
```

**Output:**
```
De-identified text:
Patient [NAME] (DOB: [DATE], SSN: [SSN], MRN: [MRN]) was seen by [PROVIDER] on [DATE] at [ORGANIZATION]. She reported moderate lower back pain. Phone: [PHONE].

Entities removed: 7
  [NAME]          'Sarah Lee'           (confidence: 99%)
  [DATE]          '07/04/1990'          (confidence: 99%)
  [SSN]           '234-56-7890'         (confidence: 98%)
  [MRN]           '99812'               (confidence: 87%)
  [PROVIDER]      'Dr. James Patel'     (confidence: 96%)
  [DATE]          '04/15/2024'          (confidence: 98%)
  [ORGANIZATION]  'City General Hospital' (confidence: 83%)
```

---

### Analyse sentiment with multiple models

```python
import requests

SENTIMENT_URL = "http://localhost:8000/api/v1"

text = (
    "The waiting time was unacceptably long and nobody explained what was happening. "
    "I felt anxious and ignored for over two hours."
)

models_to_try = ["bert_hc_v2", "emotion", "zeroshot"]

for model in models_to_try:
    response = requests.post(
        f"{SENTIMENT_URL}/analyze",
        json={"text": text, "model_type": model}
    )
    response.raise_for_status()
    result = response.json()

    print(f"\nModel: {model}")
    print(f"  Sentiment: {result['sentiment']}")
    for label, prob in zip(result["labels"], result["probabilities"]):
        bar = "█" * int(prob * 20)
        print(f"  {label:<12} {prob:.1%}  {bar}")
```

**Output:**
```
Model: bert_hc_v2
  Sentiment: NEGATIVE
  NEGATIVE     89.3%  ██████████████████
  NEUTRAL       7.1%  █
  POSITIVE      3.6%  

Model: emotion
  Sentiment: ANGER
  ANGER        42.1%  ████████
  DISGUST      18.3%  ███
  FEAR         21.4%  ████
  JOY           1.2%  
  NEUTRAL       5.8%  █
  SADNESS      10.1%  ██
  SURPRISE      1.1%  

Model: zeroshot
  Sentiment: NEGATIVE
  POSITIVE      4.2%  
  NEGATIVE     88.7%  █████████████████
  NEUTRAL       7.1%  █
```

---

### Full pipeline — batch de-identify then analyse

```python
import requests

PII_URL  = "http://localhost:8001/api/v1"
NLP_URL  = "http://localhost:8000/api/v1"

patient_notes = [
    {"patient_id": "PT-001", "text": "James Carter (MRN 11423) had an excellent experience. Dr. Kim was thorough and reassuring."},
    {"patient_id": "PT-002", "text": "Alice Wong (MRN 22841) waited 4 hours in A&E with no updates. Very distressing experience."},
    {"patient_id": "PT-003", "text": "The physiotherapy team at St. Mark's helped Michael Brown recover fully. Outstanding care."},
]

# Step 1 — De-identify all notes in one batch call
batch_response = requests.post(
    f"{PII_URL}/batch",
    json={"data": patient_notes, "strategy": "placeholder"}
)
batch_response.raise_for_status()
batch_result = batch_response.json()

print(f"De-identified {batch_result['documents_processed']} notes, "
      f"removed {batch_result['total_entities']} PII entities.\n")

# Step 2 — Analyse sentiment for each de-identified note
for record in batch_result["results"]:
    sentiment_response = requests.post(
        f"{NLP_URL}/analyze",
        json={"text": record["deidentified_text"], "model_type": "bert_hc_v2"}
    )
    sentiment_response.raise_for_status()
    sentiment = sentiment_response.json()

    print(f"Patient {record['patient_id']}:")
    print(f"  De-identified : {record['deidentified_text']}")
    print(f"  Sentiment     : {sentiment['sentiment']}  "
          f"(confidence: {max(sentiment['probabilities']):.0%})")
    print()
```

---

## 11. Interactive API Docs (Swagger UI)

Both APIs come with built-in interactive documentation. Open these in your browser:

| API | URL |
|-----|-----|
| Sentiment Analysis | http://localhost:8000/docs |
| PII De-identification | http://localhost:8001/docs |

The Swagger UI lets you:
- Browse every endpoint and see what fields are accepted
- Try requests directly in the browser (no cURL or code needed)
- See the exact response format for each endpoint

This is especially useful when you are exploring the API for the first time or testing edge cases.

---

## 12. Troubleshooting

### "Connection refused" when calling the API

The models are still loading. Wait 2–3 minutes after starting the container and try again.

```bash
# Watch the container logs to see when models are ready
docker logs -f nlp-openmed
```

Look for lines like `Application startup complete.` — that means the service is ready.

---

### The container exits immediately after starting

Check the logs for the error:
```bash
docker logs nlp-openmed
```

Common causes:
- **Port already in use** — Another application is using port 8000 or 8001. Stop it, or run the container on different ports:
  ```bash
  docker run -d --name nlp-openmed -p 8080:8000 -p 8081:8001 nlp-openmed-local:latest
  # Then use localhost:8080 and localhost:8081
  ```
- **Not enough memory** — The container needs at least 8 GB of RAM. Check Docker Desktop settings → Resources → Memory.

---

### "Image not found" error

```bash
# List all images Docker has loaded
docker images

# If nlp-openmed-local is not listed, load it:
docker load < nlp-openmed-local.tar.gz
```

---

### HTTP 422 "Text must be at least 4 words"

The Sentiment API requires a minimum of 4 words. Make sure your text is not too short.

---

### HTTP 422 "Text must not exceed 300 words"

The Sentiment API has a 300-word limit. Split long documents into chunks if needed.

---

### I want to reset and start fresh

```bash
# Stop and remove the container
docker stop nlp-openmed
docker rm nlp-openmed

# Start again
docker run -d --name nlp-openmed --restart unless-stopped \
  -p 8000:8000 -p 8001:8001 nlp-openmed-local:latest
```

---

## 13. Stopping and Cleaning Up

**Stop the container (keeps it and the image on your machine):**
```bash
docker stop nlp-openmed
```

**Start it again later:**
```bash
docker start nlp-openmed
```

**Remove the container entirely (but keep the image):**
```bash
docker rm -f nlp-openmed
```

**Remove the image to free up disk space (~10 GB):**
```bash
docker rmi nlp-openmed-local:latest
```

**See all running containers:**
```bash
docker ps
```

**See all containers including stopped ones:**
```bash
docker ps -a
```

---

## 14. Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────────┐
│                    QUICK REFERENCE                                  │
├─────────────────────────────────────────────────────────────────────┤
│  Start container                                                    │
│  docker run -d --name nlp-openmed -p 8000:8000 -p 8001:8001 \      │
│    nlp-openmed-local:latest                                         │
│                                                                     │
│  Stop container                                                     │
│  docker stop nlp-openmed                                            │
│                                                                     │
│  View logs                                                          │
│  docker logs -f nlp-openmed                                         │
├─────────────────────────────────────────────────────────────────────┤
│  PII API  →  http://localhost:8001                                  │
│    POST /api/v1/detect        Find PII without changing text        │
│    POST /api/v1/deidentify    Replace PII with placeholders         │
│    POST /api/v1/batch         Process up to 100 records at once     │
│    GET  /api/v1/entities      List all 22 supported entity types    │
│    GET  /api/v1/health        Check if the PII model is loaded      │
│                                                                     │
│  Sentiment API  →  http://localhost:8000                            │
│    POST /api/v1/analyze       Classify sentiment of text            │
│    GET  /api/v1/health        Check which models are loaded         │
│    GET  /api/v1/warmup        Pre-load all 13 models into memory    │
├─────────────────────────────────────────────────────────────────────┤
│  Interactive docs (try in browser)                                  │
│    http://localhost:8000/docs   Sentiment API                       │
│    http://localhost:8001/docs   PII API                             │
├─────────────────────────────────────────────────────────────────────┤
│  Sentiment model_type values                                        │
│    bert_hc_v2          Healthcare BERT v2        (recommended)      │
│    distilroberta_hc_v2 Healthcare DistilRoBERTa v2                  │
│    distilbert_hc_v2    Healthcare DistilBERT v2                     │
│    bert_hc             Healthcare BERT                              │
│    distilbert_hc       Healthcare DistilBERT                        │
│    distilroberta_hc    Healthcare DistilRoBERTa                     │
│    default             DistilBERT SST-2                             │
│    roberta             BERT Multilingual (1–5 stars)                │
│    emotion             GoEmotions (7 emotions)                      │
│    amazon              Amazon Reviews BERT                          │
│    twitter             RoBERTa Twitter                              │
│    sst2                BERT SST-2                                   │
│    zeroshot            BART Large MNLI                              │
├─────────────────────────────────────────────────────────────────────┤
│  PII replacement strategies                                         │
│    placeholder   [NAME], [DATE], [SSN] ...  (default, recommended)  │
│    redact        ██████████                                         │
│    consistent    Same entity → same fake value                      │
│    hash          Deterministic pseudonym                            │
└─────────────────────────────────────────────────────────────────────┘
```
