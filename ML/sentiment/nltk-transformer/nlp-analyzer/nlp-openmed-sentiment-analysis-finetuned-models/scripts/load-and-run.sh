#!/usr/bin/env bash
# Load the nlp-openmed-local image and start both APIs.
#
# Prerequisites: Docker installed (https://docs.docker.com/get-docker/)
# Usage:         bash load-and-run.sh
#
# Place this script in the same directory as nlp-openmed-local.tar.gz
# and run it — that's all the recipient needs to do.

set -euo pipefail

IMAGE_FILE="nlp-openmed-local.tar.gz"
IMAGE_NAME="nlp-openmed-local:latest"
CONTAINER_NAME="nlp-openmed"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHIVE="${SCRIPT_DIR}/${IMAGE_FILE}"

echo "========================================="
echo "  NLP OpenMed — Local Setup"
echo "========================================="

# ── Check Docker is available ─────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo ""
  echo "ERROR: Docker is not installed or not in PATH."
  echo "Install Docker from https://docs.docker.com/get-docker/ and re-run."
  exit 1
fi

# ── Load image (skip if already loaded) ──────────────────────────────────────
if docker image inspect "${IMAGE_NAME}" &>/dev/null; then
  echo "  Image already loaded — skipping import."
else
  if [[ ! -f "${ARCHIVE}" ]]; then
    echo ""
    echo "ERROR: ${IMAGE_FILE} not found in ${SCRIPT_DIR}"
    echo "Place nlp-openmed-local.tar.gz alongside this script and re-run."
    exit 1
  fi
  echo "  Loading image from ${IMAGE_FILE} ..."
  docker load < "${ARCHIVE}"
  echo "  Image loaded successfully."
fi

# ── Remove stale container if present ────────────────────────────────────────
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "  Removing existing container '${CONTAINER_NAME}' ..."
  docker rm -f "${CONTAINER_NAME}"
fi

# ── Start container ───────────────────────────────────────────────────────────
echo ""
echo "  Starting container '${CONTAINER_NAME}' ..."
docker run -d \
  --name "${CONTAINER_NAME}" \
  --restart unless-stopped \
  -p 8000:8000 \
  -p 8001:8001 \
  "${IMAGE_NAME}"

echo ""
echo "========================================="
echo "  Container started!"
echo ""
echo "  Sentiment Analysis API  →  http://localhost:8000/docs"
echo "  PII De-identification   →  http://localhost:8001/docs"
echo ""
echo "  Both services are warming up. The health check turns green"
echo "  ~2–3 minutes after start (models loading into memory)."
echo ""
echo "  To check status:  docker ps"
echo "  To view logs:     docker logs -f ${CONTAINER_NAME}"
echo "  To stop:          docker stop ${CONTAINER_NAME}"
echo "  To remove:        docker rm -f ${CONTAINER_NAME}"
echo "========================================="
