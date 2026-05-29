"""
Backward-compatibility shim.

The core logic now lives in src/.  This module re-exports the same
public symbols so that the legacy Flask app.py continues to work unchanged.
"""

from src.preprocessor import preprocess_text, read_file
from src.analyzer import analyze_sentiment
