#!/usr/bin/env bash
# Build the combined nlp-openmed-local image and export it as a .tar.gz
# that can be shared and run on any machine with Docker — no internet needed.
#
# Run from the nlp-openmed-sentiment-analysis-finetuned-models/ directory:
#   bash scripts/package-image.sh
#
# Output:  nlp-openmed-local.tar.gz  (in the current directory)
# Size:    expect ~8–12 GB (14 HF models + spaCy + NLTK baked in)

set -euo pipefail

IMAGE_NAME="nlp-openmed-local"
IMAGE_TAG="latest"
OUTPUT_FILE="nlp-openmed-local.tar.gz"

# Resolve the ML/ parent directory (4 levels up from this project)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ML_DIR="$(cd "${PROJECT_DIR}/../../../.." && pwd)"
DOCKERFILE="${PROJECT_DIR}/Dockerfile.local"

echo "========================================="
echo "  NLP OpenMed — Local Image Packager"
echo "========================================="
echo "  Build context : ${ML_DIR}"
echo "  Dockerfile    : ${DOCKERFILE}"
echo "  Image         : ${IMAGE_NAME}:${IMAGE_TAG}"
echo "  Output        : ${PROJECT_DIR}/${OUTPUT_FILE}"
echo "========================================="
echo ""
echo "Step 1/2 — Building Docker image (this may take 20–40 min on first run)..."
echo ""

docker build \
  --file "${DOCKERFILE}" \
  --tag "${IMAGE_NAME}:${IMAGE_TAG}" \
  "${ML_DIR}"

echo ""
echo "Step 2/2 — Exporting image to ${OUTPUT_FILE} ..."
echo ""

docker save "${IMAGE_NAME}:${IMAGE_TAG}" | gzip > "${PROJECT_DIR}/${OUTPUT_FILE}"

SIZE=$(du -sh "${PROJECT_DIR}/${OUTPUT_FILE}" | cut -f1)
echo ""
echo "========================================="
echo "  Done!  ${OUTPUT_FILE}  (${SIZE})"
echo "========================================="
echo ""
echo "Share ${OUTPUT_FILE} with the recipient, along with load-and-run.sh."
echo "The recipient only needs Docker installed — no internet access required."
