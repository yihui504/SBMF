"""
Trend Analyzer

Analyzes trends in test results over time.
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict


class TrendDirection(Enum):
    """Trend direction"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    UNKNOWN = "unknown"


@dataclass
class TrendPoint:
    """A single data point in a trend"""
    timestamp: float
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Trend:
    """
    A detected trend

    Represents a pattern in data over time.
    """
    metric_name: str
    direction: TrendDirection
    start_value: float
    end_value: float
    change_percent: float
    confidence: float  # 0-1
    data_points: int
    timespan: float  # In seconds
    description: str

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "metric_name": self.metric_name,
            "direction": self.direction.value,
            "start_value": self.start_value,
            "end_value": self.end_value,
            "change_percent": self.change_percent,
            "confidence": self.confidence,
            "data_points": self.data_points,
            "timespan": self.timespan,
            "description": self.description,
        }


class TrendAnalyzer:
    """
    Trend Analyzer

    Analyzes trends in test results over time.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize trend analyzer

        Args:
            config: Configuration options
                - min_points: Minimum data points for trend analysis (default: 5)
                - time_window: Time window for trend analysis (default: 3600s)
        """
        self.config = config or {}
        self.min_points = config.get("min_points", 5) if config else 5
        self.time_window = config.get("time_window", 3600) if config else 3600

        # Time series data
        self._time_series: Dict[str, List[TrendPoint]] = defaultdict(list)

    def add_data_point(self, metric_name: str, value: float,
                       metadata: Optional[Dict] = None) -> None:
        """
        Add a data point to time series

        Args:
            metric_name: Name of the metric
            value: Value of the metric
            metadata: Optional metadata
        """
        point = TrendPoint(
            timestamp=time.time(),
            value=value,
            metadata=metadata or {}
        )

        self._time_series[metric_name].append(point)

        # Limit data points to last 1000
        if len(self._time_series[metric_name]) > 1000:
            self._time_series[metric_name] = self._time_series[metric_name][-1000:]

    def analyze_trends(self) -> List[Trend]:
        """
        Analyze all trends

        Returns:
            List of detected trends
        """
        trends = []
        current_time = time.time()

        for metric_name, points in self._time_series.items():
            # Filter points within time window
            recent_points = [
                p for p in points
                if current_time - p.timestamp <= self.time_window
            ]

            if len(recent_points) < self.min_points:
                continue

            # Analyze trend for this metric
            trend = self._analyze_metric_trend(metric_name, recent_points)
            if trend:
                trends.append(trend)

        return trends

    def _analyze_metric_trend(self, metric_name: str,
                              points: List[TrendPoint]) -> Optional[Trend]:
        """Analyze trend for a specific metric"""
        if len(points) < 2:
            return None

        # Sort by timestamp
        sorted_points = sorted(points, key=lambda p: p.timestamp)

        # Calculate trend
        start_value = sorted_points[0].value
        end_value = sorted_points[-1].value

        # Calculate change percentage
        if start_value == 0:
            change_percent = 0.0
        else:
            change_percent = ((end_value - start_value) / abs(start_value)) * 100

        # Determine direction
        if abs(change_percent) < 5:  # Less than 5% change
            direction = TrendDirection.STABLE
        elif change_percent > 0:
            direction = TrendDirection.INCREASING
        else:
            direction = TrendDirection.DECREASING

        # Calculate confidence based on consistency
        # (Simplified - real implementation would use statistical tests)
        values = [p.value for p in sorted_points]
        if len(values) >= 3:
            # Check if values consistently move in one direction
            increases = sum(1 for i in range(1, len(values)) if values[i] > values[i-1])
            decreases = sum(1 for i in range(1, len(values)) if values[i] < values[i-1])

            consistency = max(increases, decreases) / (len(values) - 1)
            confidence = consistency
        else:
            confidence = 0.5

        # Calculate timespan
        timespan = sorted_points[-1].timestamp - sorted_points[0].timestamp

        # Generate description
        description = self._generate_description(
            metric_name, direction, start_value, end_value, change_percent
        )

        return Trend(
            metric_name=metric_name,
            direction=direction,
            start_value=start_value,
            end_value=end_value,
            change_percent=change_percent,
            confidence=confidence,
            data_points=len(sorted_points),
            timespan=timespan,
            description=description,
        )

    def _generate_description(self, metric_name: str, direction: TrendDirection,
                             start_value: float, end_value: float,
                             change_percent: float) -> str:
        """Generate trend description"""
        if direction == TrendDirection.STABLE:
            return f"{metric_name} has remained stable around {end_value:.1f}"
        elif direction == TrendDirection.INCREASING:
            return f"{metric_name} has increased by {abs(change_percent):.1f}% (from {start_value:.1f} to {end_value:.1f})"
        else:
            return f"{metric_name} has decreased by {abs(change_percent):.1f}% (from {start_value:.1f} to {end_value:.1f})"

    def predict_next(self, metric_name: str,
                     horizon: int = 5) -> Optional[Dict]:
        """
        Predict future values for a metric

        Args:
            metric_name: Name of the metric
            horizon: Number of data points to predict ahead

        Returns:
            Prediction results or None
        """
        points = self._time_series.get(metric_name, [])

        if len(points) < 3:
            return None

        # Simple linear regression prediction
        # (More sophisticated methods could be used)
        sorted_points = sorted(points, key=lambda p: p.timestamp)

        # Calculate average rate of change
        if len(sorted_points) >= 2:
            total_change = sorted_points[-1].value - sorted_points[0].value
            total_time = sorted_points[-1].timestamp - sorted_points[0].timestamp

            if total_time > 0:
                rate = total_change / total_time

                # Predict next values
                predictions = []
                last_point = sorted_points[-1]

                for i in range(1, horizon + 1):
                    predicted_value = last_point.value + (rate * i * 60)  # Assume 1 minute intervals
                    predictions.append(predicted_value)

                return {
                    "metric_name": metric_name,
                    "current_value": last_point.value,
                    "predicted_values": predictions,
                    "trend_rate": rate,
                    "confidence": 0.6,  # Moderate confidence for linear prediction
                }

        return None

    def get_time_series(self, metric_name: str,
                        limit: int = 100) -> List[TrendPoint]:
        """
        Get time series data for a metric

        Args:
            metric_name: Name of the metric
            limit: Maximum number of points to return

        Returns:
            List of trend points
        """
        points = self._time_series.get(metric_name, [])
        return points[-limit:]

    def get_all_metrics(self) -> List[str]:
        """Get list of all tracked metrics"""
        return list(self._time_series.keys())

    def clear_metric(self, metric_name: str) -> None:
        """Clear data for a metric"""
        if metric_name in self._time_series:
            del self._time_series[metric_name]

    def clear_all(self) -> None:
        """Clear all trend data"""
        self._time_series.clear()

    def get_stats(self) -> Dict:
        """Get analyzer statistics"""
        total_points = sum(len(points) for points in self._time_series.values())

        return {
            "total_metrics": len(self._time_series),
            "total_data_points": total_points,
            "avg_points_per_metric": total_points / len(self._time_series) if self._time_series else 0,
        }


__all__ = [
    "TrendDirection",
    "TrendPoint",
    "Trend",
    "TrendAnalyzer",
]
