"""
Base Anomaly Detector

Abstract base class for anomaly detectors.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import time


class AnomalyType(Enum):
    """Types of anomalies"""
    PERFORMANCE = "performance"      # Response time outliers
    RESOURCE = "resource"            # CPU/memory usage spikes
    ERROR_RATE = "error_rate"        # Elevated error rates
    DATA_CONSISTENCY = "data_consistency"  # Data integrity issues
    BEHAVIORAL = "behavioral"        # Unusual behavior patterns
    CONSTRAINT = "constraint"        # Constraint violations
    THRESHOLD = "threshold"          # Threshold crossings


@dataclass
class AnomalyResult:
    """
    Result of anomaly detection

    Contains information about detected anomalies.
    """
    is_anomaly: bool
    anomaly_type: Optional[AnomalyType] = None
    severity: str = "low"  # low, medium, high, critical
    confidence: float = 0.0  # 0-1
    description: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    affected_tests: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "is_anomaly": self.is_anomaly,
            "anomaly_type": self.anomaly_type.value if self.anomaly_type else None,
            "severity": self.severity,
            "confidence": self.confidence,
            "description": self.description,
            "metrics": self.metrics,
            "context": self.context,
            "timestamp": self.timestamp,
            "affected_tests": self.affected_tests,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'AnomalyResult':
        """Create from dictionary"""
        if data.get("anomaly_type"):
            data["anomaly_type"] = AnomalyType(data["anomaly_type"])
        return cls(**data)


@dataclass
class MetricData:
    """
    Metric data point for analysis

    Represents a single measurement for anomaly detection.
    """
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    test_id: Optional[str] = None
    operation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThresholdConfig:
    """
    Threshold configuration for anomaly detection

    Defines how thresholds are determined and adjusted.
    """
    upper_bound: Optional[float] = None
    lower_bound: Optional[float] = None
    adaptive: bool = True
    window_size: int = 100  # Number of samples for adaptive threshold
    std_multiplier: float = 3.0  # Standard deviations for threshold
    percentile: float = 95.0  # Percentile for threshold
    min_samples: int = 10  # Minimum samples before detection

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "upper_bound": self.upper_bound,
            "lower_bound": self.lower_bound,
            "adaptive": self.adaptive,
            "window_size": self.window_size,
            "std_multiplier": self.std_multiplier,
            "percentile": self.percentile,
            "min_samples": self.min_samples,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ThresholdConfig':
        """Create from dictionary"""
        return cls(**data)


class BaseDetector(ABC):
    """
    Abstract base class for anomaly detectors

    All anomaly detectors should inherit from this class.
    """

    def __init__(self, name: str, config: Optional[Dict] = None):
        """
        Initialize detector

        Args:
            name: Detector name
            config: Optional configuration
        """
        self.name = name
        self.config = config or {}
        self._enabled = True
        self._detection_count = 0

    @abstractmethod
    def detect(self, metrics: List[MetricData]) -> AnomalyResult:
        """
        Detect anomalies in metrics

        Args:
            metrics: List of metric data points

        Returns:
            AnomalyResult with detection findings
        """
        pass

    def is_enabled(self) -> bool:
        """Check if detector is enabled"""
        return self._enabled

    def enable(self) -> None:
        """Enable the detector"""
        self._enabled = True

    def disable(self) -> None:
        """Disable the detector"""
        self._enabled = False

    def get_stats(self) -> Dict:
        """Get detector statistics"""
        return {
            "name": self.name,
            "enabled": self._enabled,
            "detection_count": self._detection_count,
        }


class DetectorRegistry:
    """
    Registry for anomaly detectors

    Manages multiple detectors and coordinates detection.
    """

    def __init__(self):
        """Initialize registry"""
        self._detectors: Dict[str, BaseDetector] = {}
        self._detection_history: List[AnomalyResult] = []

    def register(self, detector: BaseDetector) -> None:
        """Register a detector"""
        self._detectors[detector.name] = detector

    def unregister(self, name: str) -> None:
        """Unregister a detector"""
        if name in self._detectors:
            del self._detectors[name]

    def get(self, name: str) -> Optional[BaseDetector]:
        """Get a detector by name"""
        return self._detectors.get(name)

    def list_detectors(self) -> List[str]:
        """List all registered detector names"""
        return list(self._detectors.keys())

    def detect_all(self, metrics: List[MetricData]) -> List[AnomalyResult]:
        """
        Run all enabled detectors

        Args:
            metrics: Metrics to analyze

        Returns:
            List of anomaly results from all detectors
        """
        results = []

        for detector in self._detectors.values():
            if detector.is_enabled():
                result = detector.detect(metrics)
                detector._detection_count += 1
                results.append(result)

        # Store in history
        self._detection_history.extend(results)

        return results

    def get_enabled_detectors(self) -> List[BaseDetector]:
        """Get all enabled detectors"""
        return [
            d for d in self._detectors.values()
            if d.is_enabled()
        ]

    def get_history(self, limit: int = 100) -> List[AnomalyResult]:
        """Get recent detection history"""
        return self._detection_history[-limit:]

    def clear_history(self) -> None:
        """Clear detection history"""
        self._detection_history.clear()


__all__ = [
    "AnomalyType",
    "AnomalyResult",
    "MetricData",
    "ThresholdConfig",
    "BaseDetector",
    "DetectorRegistry",
]
