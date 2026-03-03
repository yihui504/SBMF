"""
Statistical Anomaly Detector

Detects anomalies using statistical methods.
"""
from typing import Dict, List, Optional
import statistics

from detectors.base import (
    BaseDetector, MetricData, AnomalyResult, AnomalyType, ThresholdConfig
)
from detectors.threshold_manager import AdaptiveThresholdManager


class StatisticalAnomalyDetector(BaseDetector):
    """
    Statistical Anomaly Detector

    Uses statistical methods (Z-score, IQR, percentiles) to detect anomalies.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize statistical detector

        Args:
            config: Configuration options
                - z_score_threshold: Z-score threshold (default: 3.0)
                - iqr_multiplier: IQR multiplier (default: 1.5)
                - min_samples: Minimum samples for detection (default: 10)
        """
        super().__init__("statistical", config)
        self.z_score_threshold = config.get("z_score_threshold", 3.0) if config else 3.0
        self.iqr_multiplier = config.get("iqr_multiplier", 1.5) if config else 1.5
        self.min_samples = config.get("min_samples", 10) if config else 10

        # Threshold manager for adaptive thresholds
        self.threshold_manager = AdaptiveThresholdManager()

        # Configure default thresholds
        self._configure_default_thresholds()

    def _configure_default_thresholds(self) -> None:
        """Configure default thresholds for common metrics"""
        default_configs = {
            "response_time": ThresholdConfig(
                upper_bound=5000.0,  # 5 seconds
                adaptive=True,
                std_multiplier=3.0,
                percentile=95.0,
                min_samples=self.min_samples,
            ),
            "cpu_usage": ThresholdConfig(
                upper_bound=90.0,  # 90%
                adaptive=True,
                std_multiplier=2.5,
                percentile=95.0,
                min_samples=self.min_samples,
            ),
            "memory_usage": ThresholdConfig(
                upper_bound=90.0,  # 90%
                adaptive=True,
                std_multiplier=2.5,
                percentile=95.0,
                min_samples=self.min_samples,
            ),
            "error_count": ThresholdConfig(
                upper_bound=10.0,
                adaptive=True,
                std_multiplier=3.0,
                percentile=95.0,
                min_samples=self.min_samples,
            ),
        }

        for metric_name, config in default_configs.items():
            self.threshold_manager.configure(metric_name, config)

    def detect(self, metrics: List[MetricData]) -> AnomalyResult:
        """
        Detect anomalies in metrics

        Args:
            metrics: List of metric data points

        Returns:
            AnomalyResult with detection findings
        """
        if not metrics:
            return AnomalyResult(is_anomaly=False)

        # Update thresholds with new data
        self.threshold_manager.batch_update(metrics)

        # Check each metric for anomalies
        anomalies = []
        affected_tests = []

        for metric in metrics:
            is_anomaly, reason = self.threshold_manager.check(
                metric.name, metric.value
            )

            if is_anomaly:
                anomalies.append({
                    "metric": metric.name,
                    "value": metric.value,
                    "reason": reason,
                })
                if metric.test_id:
                    affected_tests.append(metric.test_id)

        # Determine overall anomaly type and severity
        if not anomalies:
            return AnomalyResult(is_anomaly=False)

        # Classify anomaly type
        anomaly_type = self._classify_anomaly_type(anomalies)

        # Calculate severity
        severity = self._calculate_severity(anomalies)

        # Calculate confidence based on number of anomalies
        confidence = min(len(anomalies) / 5.0, 1.0)

        return AnomalyResult(
            is_anomaly=True,
            anomaly_type=anomaly_type,
            severity=severity,
            confidence=confidence,
            description=f"Detected {len(anomalies)} anomaly(s): {anomalies[0]['reason']}",
            metrics={m["metric"]: m["value"] for m in anomalies},
            context={"anomalies": anomalies},
            affected_tests=affected_tests,
        )

    def _classify_anomaly_type(self, anomalies: List[Dict]) -> AnomalyType:
        """Classify anomaly type based on affected metrics"""
        metric_names = [a["metric"] for a in anomalies]

        if any("time" in m.lower() or "latency" in m.lower() for m in metric_names):
            return AnomalyType.PERFORMANCE
        elif any("cpu" in m.lower() or "memory" in m.lower() for m in metric_names):
            return AnomalyType.RESOURCE
        elif any("error" in m.lower() for m in metric_names):
            return AnomalyType.ERROR_RATE
        elif any("threshold" in a["reason"].lower() for a in anomalies):
            return AnomalyType.THRESHOLD
        else:
            return AnomalyType.BEHAVIORAL

    def _calculate_severity(self, anomalies: List[Dict]) -> str:
        """Calculate severity based on anomaly extent"""
        # Count critical anomalies
        critical_count = 0
        high_count = 0

        for anomaly in anomalies:
            value = anomaly["value"]
            metric = anomaly["metric"]

            # Check thresholds for this metric
            thresholds = self.threshold_manager.get_thresholds(metric)
            if thresholds:
                upper = thresholds.get("upper_bound", float('inf'))
                # Calculate how much over threshold
                if upper < float('inf') and value > upper:
                    excess_ratio = (value - upper) / upper if upper > 0 else 1.0
                    if excess_ratio > 2.0:
                        critical_count += 1
                    elif excess_ratio > 1.0:
                        high_count += 1

        if critical_count > 0:
            return "critical"
        elif high_count > 0 or len(anomalies) > 3:
            return "high"
        elif len(anomalies) > 1:
            return "medium"
        else:
            return "low"

    def detect_z_score(self, values: List[float],
                       threshold: Optional[float] = None) -> List[int]:
        """
        Detect anomalies using Z-score method

        Args:
            values: List of values to analyze
            threshold: Z-score threshold (uses default if None)

        Returns:
            List of indices of anomalous values
        """
        threshold = threshold or self.z_score_threshold

        if len(values) < self.min_samples:
            return []

        mean = statistics.mean(values)
        if len(values) < 2:
            return []

        std = statistics.stdev(values)
        if std == 0:
            return []

        anomalies = []
        for i, value in enumerate(values):
            z_score = abs((value - mean) / std)
            if z_score > threshold:
                anomalies.append(i)

        return anomalies

    def detect_iqr(self, values: List[float]) -> List[int]:
        """
        Detect anomalies using IQR (Interquartile Range) method

        Args:
            values: List of values to analyze

        Returns:
            List of indices of anomalous values
        """
        if len(values) < 4:  # Need at least 4 for IQR
            return []

        sorted_values = sorted(values)
        n = len(sorted_values)

        # Calculate quartiles
        q1_idx = n // 4
        q3_idx = 3 * n // 4
        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]

        iqr = q3 - q1
        if iqr == 0:
            return []

        lower_bound = q1 - self.iqr_multiplier * iqr
        upper_bound = q3 + self.iqr_multiplier * iqr

        # Find anomalies
        anomalies = []
        for i, value in enumerate(values):
            if value < lower_bound or value > upper_bound:
                anomalies.append(i)

        return anomalies

    def configure_metric(self, metric_name: str, config: ThresholdConfig) -> None:
        """
        Configure thresholds for a specific metric

        Args:
            metric_name: Name of the metric
            config: Threshold configuration
        """
        self.threshold_manager.configure(metric_name, config)

    def get_threshold_info(self, metric_name: str) -> Optional[Dict]:
        """
        Get threshold information for a metric

        Args:
            metric_name: Name of the metric

        Returns:
            Dictionary with threshold info or None
        """
        return self.threshold_manager.get_thresholds(metric_name)

    def get_stats(self) -> Dict:
        """Get detector statistics"""
        base_stats = super().get_stats()
        base_stats.update({
            "threshold_stats": self.threshold_manager.get_stats(),
        })
        return base_stats


__all__ = ["StatisticalAnomalyDetector"]
