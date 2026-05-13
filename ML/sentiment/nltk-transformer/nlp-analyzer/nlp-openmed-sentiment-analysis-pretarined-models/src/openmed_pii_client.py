"""
OpenMed PII De-identification client.

Calls the deployed OpenMed API to redact PHI from clinical text
before running sentiment analysis.

Config (via environment variables or .env):
    OPENMED_PII_BASE_URL  — API gateway base URL
    OPENMED_PII_API_KEY   — x-api-key value
"""

import os
import logging

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_BASE_URL = os.getenv("OPENMED_PII_BASE_URL", "").rstrip("/")
_API_KEY  = os.getenv("OPENMED_PII_API_KEY", "")
_HEADERS  = {"x-api-key": _API_KEY, "Content-Type": "application/json"}
_TIMEOUT  = 30  # seconds


def redact_pii(text: str, strategy: str = "placeholder", confidence_threshold: float = 0.5) -> tuple[str, int]:
    """
    Send *text* to the OpenMed PII API and return the de-identified version.

    Returns:
        (redacted_text, entity_count)

    Falls back to the original text on any API error so the sentiment
    pipeline is never blocked by a PII service outage.
    """
    if not _BASE_URL or not _API_KEY:
        logger.warning("OpenMed PII API not configured — skipping redaction.")
        return text, 0

    url = f"{_BASE_URL}/api/v1/deidentify"
    payload = {
        "text": text,
        "strategy": strategy,
        "confidence_threshold": confidence_threshold,
    }

    try:
        response = requests.post(url, json=payload, headers=_HEADERS, timeout=_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("deidentified_text", text), data.get("entity_count", 0)
    except requests.exceptions.Timeout:
        logger.error("OpenMed PII API timed out — using original text.")
        return text, 0
    except requests.exceptions.RequestException as exc:
        logger.error("OpenMed PII API error: %s — using original text.", exc)
        return text, 0
