"""
Healthcare Topic Classifier — unified six-model topic classification.

Models: bertopic_mini, bertopic_mpnet, lsi, hdp, lda, nmf
Topics: 15 predefined PREM (Patient Reported Experience Measure) categories
"""
from .classifier import HealthcareTopicClassifier

__all__ = ["HealthcareTopicClassifier"]
