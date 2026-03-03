"""
Tests for M1: Adaptive Anomaly Detection
"""
import pytest
import tempfile
import time
from pathlib import Path

from detectors.base import (
    AnomalyType, AnomalyResult, MetricData, ThresholdConfig,
    BaseDetector, DetectorRegistry
)
from detectors.threshold_manager import AdaptiveThresholdManager, ThresholdState
from detectors.statistical_detector import StatisticalAnomalyDetector
from detectors.pattern_learner import (
    PatternType, AnomalyPattern, AnomalyPatternLearner
)


# ================================================================
# Base Classes Tests
# ================================================================

class TestAnomalyResult:
    """Test AnomalyResult class"""

    def test_creation(self):
        """Test creating an anomaly result"""
        result = AnomalyResult(
            is_anomaly=True,
            anomaly_type=AnomalyType.PERFORMANCE,
            severity="high",
            confidence=0.8
        )

        assert result.is_anomaly
        assert result.anomaly_type == AnomalyType.PERFORMANCE
        assert result.severity == "high"

    def test_to_dict(self):
        """Test serialization to dict"""
        result = AnomalyResult(
            is_anomaly=True,
            anomaly_type=AnomalyType.PERFORMANCE,
            metrics={"response_time": 5000}
        )

        data = result.to_dict()
        assert data["is_anomaly"]
        assert data["anomaly_type"] == "performance"
        assert data["metrics"]["response_time"] == 5000

    def test_from_dict(self):
        """Test deserialization from dict"""
        data = {
            "is_anomaly": True,
            "anomaly_type": "performance",
            "severity": "high",
            "confidence": 0.8,
            "description": "",
            "metrics": {},
            "context": {},
            "timestamp": time.time(),
            "affected_tests": [],
        }

        result = AnomalyResult.from_dict(data)
        assert result.is_anomaly
        assert result.anomaly_type == AnomalyType.PERFORMANCE


class TestMetricData:
    """Test MetricData class"""

    def test_creation(self):
        """Test creating metric data"""
        metric = MetricData(
            name="response_time",
            value=123.45,
            test_id="TEST_001",
            operation="search"
        )

        assert metric.name == "response_time"
        assert metric.value == 123.45
        assert metric.test_id == "TEST_001"


# ================================================================
# Threshold Manager Tests
# ================================================================

class TestAdaptiveThresholdManager:
    """Test adaptive threshold manager"""

    def test_initialization(self):
        """Test threshold manager initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "thresholds.json"
            manager = AdaptiveThresholdManager(storage_path)
            stats = manager.get_stats()

            assert stats["total_metrics"] == 0

    def test_configure(self):
        """Test configuring thresholds"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "thresholds.json"
            manager = AdaptiveThresholdManager(storage_path)

            config = ThresholdConfig(
                upper_bound=100.0,
                adaptive=True,
                std_multiplier=3.0
            )

            manager.configure("cpu_usage", config)

            stats = manager.get_stats()
            assert stats["total_metrics"] == 1

    def test_update_and_check(self):
        """Test updating thresholds and checking values"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "thresholds.json"
            manager = AdaptiveThresholdManager(storage_path)

            config = ThresholdConfig(
                upper_bound=100.0,
                adaptive=True,
                std_multiplier=2.0,
                min_samples=3
            )

            manager.configure("test_metric", config)

            # Add normal values
            for value in [10, 12, 11, 13, 10, 12, 11, 14, 10, 12]:
                manager.update("test_metric", value)

            # Check normal value
            is_anomaly, reason = manager.check("test_metric", 12)
            assert not is_anomaly

            # Check anomalous value
            is_anomaly, reason = manager.check("test_metric", 50)
            assert is_anomaly
            assert "exceeds" in reason.lower()

    def test_get_thresholds(self):
        """Test getting threshold info"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "thresholds.json"
            manager = AdaptiveThresholdManager(storage_path)

            config = ThresholdConfig(adaptive=True, min_samples=2)
            manager.configure("test_metric", config)

            # Add some values
            for value in [10, 12, 11]:
                manager.update("test_metric", value)

            thresholds = manager.get_thresholds("test_metric")
            assert thresholds is not None
            assert "upper_bound" in thresholds
            assert "mean" in thresholds

    def test_persistence(self):
        """Test threshold persistence"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "thresholds.json"

            manager1 = AdaptiveThresholdManager(storage_path)
            manager1.configure("test_metric", ThresholdConfig(adaptive=True))
            manager1.update("test_metric", 100.0)

            # Create new manager with same storage
            manager2 = AdaptiveThresholdManager(storage_path)
            thresholds = manager2.get_thresholds("test_metric")

            assert thresholds is not None


# ================================================================
# Statistical Detector Tests
# ================================================================

class TestStatisticalAnomalyDetector:
    """Test statistical anomaly detector"""

    def test_initialization(self):
        """Test detector initialization"""
        detector = StatisticalAnomalyDetector()

        assert detector.name == "statistical"
        assert detector.is_enabled()

    def test_detect_no_anomaly(self):
        """Test detection with normal values"""
        detector = StatisticalAnomalyDetector()

        metrics = [
            MetricData(name="response_time", value=100),
            MetricData(name="response_time", value=110),
            MetricData(name="response_time", value=95),
        ]

        result = detector.detect(metrics)

        assert not result.is_anomaly

    def test_detect_anomaly(self):
        """Test detection with anomalous value"""
        detector = StatisticalAnomalyDetector()

        # First add normal values to train
        normal_metrics = [
            MetricData(name="response_time", value=value)
            for value in [100, 105, 98, 102, 99] * 3
        ]
        detector.detect(normal_metrics)

        # Now add anomalous value
        anomalous_metrics = [
            MetricData(name="response_time", value=10000),  # Huge spike
        ]

        result = detector.detect(anomalous_metrics)

        assert result.is_anomaly
        assert result.anomaly_type == AnomalyType.PERFORMANCE

    def test_z_score_detection(self):
        """Test Z-score anomaly detection"""
        detector = StatisticalAnomalyDetector()

        values = [100, 102, 98, 101, 99, 103, 97, 100, 100, 100, 500]  # Last is outlier
        anomalies = detector.detect_z_score(values, threshold=2.0)

        # The outlier at index 10 should be detected
        assert len(anomalies) > 0
        assert 10 in anomalies  # Index of 500

    def test_iqr_detection(self):
        """Test IQR anomaly detection"""
        detector = StatisticalAnomalyDetector()

        values = [10, 12, 11, 13, 10, 12, 100]  # Last is outlier
        anomalies = detector.detect_iqr(values)

        assert len(anomalies) > 0

    def test_configure_metric(self):
        """Test configuring specific metric"""
        detector = StatisticalAnomalyDetector()

        config = ThresholdConfig(
            upper_bound=50.0,
            adaptive=False
        )

        detector.configure_metric("custom_metric", config)

        thresholds = detector.get_threshold_info("custom_metric")
        assert thresholds is not None


# ================================================================
# Pattern Learner Tests
# ================================================================

class TestAnomalyPatternLearner:
    """Test anomaly pattern learner"""

    def test_initialization(self):
        """Test learner initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "patterns.json"
            learner = AnomalyPatternLearner(storage_path)

            stats = learner.get_stats()
            assert stats["total_patterns"] == 0

    def test_record_anomaly(self):
        """Test recording an anomaly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "patterns.json"
            learner = AnomalyPatternLearner(storage_path)

            anomaly = AnomalyResult(
                is_anomaly=True,
                anomaly_type=AnomalyType.PERFORMANCE,
                severity="high",
                metrics={"response_time": 5000},
                context={"operation": "search"}
            )

            learner.record_anomaly(anomaly)

            stats = learner.get_stats()
            assert stats["total_anomalies_recorded"] == 1

    def test_pattern_extraction(self):
        """Test pattern extraction from anomalies"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "patterns.json"
            learner = AnomalyPatternLearner(storage_path)

            # Record similar anomalies
            for i in range(5):
                anomaly = AnomalyResult(
                    is_anomaly=True,
                    anomaly_type=AnomalyType.PERFORMANCE,
                    metrics={"response_time": 5000 + i * 100},
                    context={"operation": "search"}
                )
                learner.record_anomaly(anomaly)

            patterns = learner.get_patterns(min_occurrences=1)
            assert len(patterns) > 0

            # Check that pattern occurrence count increased
            pattern = patterns[0]
            assert pattern.occurrence_count >= 1

    def test_correlated_metrics(self):
        """Test detection of correlated metrics"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "patterns.json"
            learner = AnomalyPatternLearner(storage_path)

            # Record anomalies with multiple metrics
            for _ in range(3):
                anomaly = AnomalyResult(
                    is_anomaly=True,
                    metrics={"cpu_usage": 90, "memory_usage": 85}
                )
                learner.record_anomaly(anomaly)

            correlated = learner.get_correlated_metrics()
            assert len(correlated) > 0

    def test_predict_next(self):
        """Test prediction of next anomalies"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "patterns.json"
            learner = AnomalyPatternLearner(storage_path)

            # Record some anomalies
            for _ in range(5):
                anomaly = AnomalyResult(
                    is_anomaly=True,
                    anomaly_type=AnomalyType.PERFORMANCE,
                    metrics={"response_time": 5000},
                    context={"operation": "search"}
                )
                learner.record_anomaly(anomaly)

            predictions = learner.predict_next(context={"operation": "search"})
            # Should have some predictions after learning
            assert isinstance(predictions, list)

    def test_persistence(self):
        """Test pattern persistence"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "patterns.json"

            learner1 = AnomalyPatternLearner(storage_path)

            anomaly = AnomalyResult(
                is_anomaly=True,
                anomaly_type=AnomalyType.PERFORMANCE,
                metrics={"response_time": 5000}
            )

            learner1.record_anomaly(anomaly)

            # Create new learner with same storage
            learner2 = AnomalyPatternLearner(storage_path)
            stats = learner2.get_stats()

            assert stats["total_anomalies_recorded"] == 1


# ================================================================
# Detector Registry Tests
# ================================================================

class TestDetectorRegistry:
    """Test detector registry"""

    def test_register_and_unregister(self):
        """Test registering and unregistering detectors"""
        registry = DetectorRegistry()

        # Create detectors with different names
        config1 = {"z_score_threshold": 3.0}
        config2 = {"z_score_threshold": 2.5}

        detector1 = StatisticalAnomalyDetector(config1)
        detector1.name = "detector1"

        detector2 = StatisticalAnomalyDetector(config2)
        detector2.name = "detector2"

        registry.register(detector1)
        registry.register(detector2)

        assert len(registry.list_detectors()) == 2

        registry.unregister("detector1")
        assert len(registry.list_detectors()) == 1

    def test_detect_all(self):
        """Test running all detectors"""
        registry = DetectorRegistry()

        detector = StatisticalAnomalyDetector()
        registry.register(detector)

        metrics = [
            MetricData(name="response_time", value=100)
        ]

        results = registry.detect_all(metrics)

        assert len(results) == 1

    def test_get_enabled_detectors(self):
        """Test getting enabled detectors"""
        registry = DetectorRegistry()

        detector = StatisticalAnomalyDetector()
        registry.register(detector)

        enabled = registry.get_enabled_detectors()
        assert len(enabled) == 1

        detector.disable()
        enabled = registry.get_enabled_detectors()
        assert len(enabled) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
