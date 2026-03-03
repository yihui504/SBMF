"""
Adaptive Anomaly Detection

Provides intelligent anomaly detection with self-tuning thresholds,
pattern learning, and plugin-based detection strategies.
"""

from detectors.base import BaseDetector, AnomalyResult, AnomalyType
from detectors.statistical_detector import StatisticalAnomalyDetector
from detectors.threshold_manager import AdaptiveThresholdManager
from detectors.pattern_learner import AnomalyPatternLearner
from detectors.anomaly_adapter import AnomalyDetectionAdapter, SimpleAnomalyResult, AnomalyDetectorCompatibility

__all__ = [
    "BaseDetector",
    "AnomalyResult",
    "AnomalyType",
    "StatisticalAnomalyDetector",
    "AdaptiveThresholdManager",
    "AnomalyPatternLearner",
    "AnomalyDetectionAdapter",
    "SimpleAnomalyResult",
    "AnomalyDetectorCompatibility",
]
