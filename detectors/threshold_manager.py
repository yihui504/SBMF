"""
Adaptive Threshold Manager

Manages self-tuning thresholds for anomaly detection.
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json
import time
import statistics

from detectors.base import ThresholdConfig, MetricData


@dataclass
class ThresholdState:
    """State of an adaptive threshold"""
    metric_name: str
    upper_bound: float
    lower_bound: float
    mean: float
    std: float
    sample_count: int
    last_updated: float
    history: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "metric_name": self.metric_name,
            "upper_bound": self.upper_bound,
            "lower_bound": self.lower_bound,
            "mean": self.mean,
            "std": self.std,
            "sample_count": self.sample_count,
            "last_updated": self.last_updated,
            "history": self.history[-100:],  # Limit history size
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ThresholdState':
        """Create from dictionary"""
        return cls(**data)


class AdaptiveThresholdManager:
    """
    Adaptive Threshold Manager

    Automatically adjusts thresholds based on observed data
    using statistical methods (mean, std, percentiles).
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize threshold manager

        Args:
            storage_path: Path to persist threshold state
        """
        self.storage_path = storage_path or Path("threshold_state.json")
        self._states: Dict[str, ThresholdState] = {}
        self._configs: Dict[str, ThresholdConfig] = {}
        self._load()

    def configure(self, metric_name: str, config: ThresholdConfig) -> None:
        """
        Configure thresholds for a metric

        Args:
            metric_name: Name of the metric
            config: Threshold configuration
        """
        self._configs[metric_name] = config

        # Initialize state if not exists
        if metric_name not in self._states:
            self._states[metric_name] = ThresholdState(
                metric_name=metric_name,
                upper_bound=config.upper_bound or float('inf'),
                lower_bound=config.lower_bound or float('-inf'),
                mean=0.0,
                std=0.0,
                sample_count=0,
                last_updated=time.time(),
                history=[]
            )

        self._save()

    def update(self, metric_name: str, value: float) -> None:
        """
        Update threshold with new value

        Args:
            metric_name: Name of the metric
            value: New observed value
        """
        config = self._configs.get(metric_name)
        if not config or not config.adaptive:
            return

        state = self._states.get(metric_name)
        if not state:
            state = ThresholdState(
                metric_name=metric_name,
                upper_bound=float('inf'),
                lower_bound=float('-inf'),
                mean=0.0,
                std=0.0,
                sample_count=0,
                last_updated=time.time(),
                history=[]
            )
            self._states[metric_name] = state

        # Add to history
        state.history.append(value)
        if len(state.history) > config.window_size:
            state.history.pop(0)

        # Update statistics
        state.sample_count += 1

        # Only update thresholds if we have enough samples
        if len(state.history) >= config.min_samples:
            state.mean = statistics.mean(state.history)

            if len(state.history) >= 2:
                state.std = statistics.stdev(state.history)
            else:
                state.std = 0.0

            # Update bounds using standard deviation
            if config.std_multiplier > 0:
                state.upper_bound = state.mean + config.std_multiplier * state.std
                state.lower_bound = max(0, state.mean - config.std_multiplier * state.std)

            # Update bounds using percentile
            if config.percentile > 0:
                sorted_values = sorted(state.history)
                idx = int(len(sorted_values) * config.percentile / 100)
                idx = min(idx, len(sorted_values) - 1)
                upper_percentile = sorted_values[idx]

                # Use max of std-based and percentile-based
                state.upper_bound = max(state.upper_bound, upper_percentile)

            state.last_updated = time.time()

        self._save()

    def check(self, metric_name: str, value: float) -> Tuple[bool, str]:
        """
        Check if value exceeds thresholds

        Args:
            metric_name: Name of the metric
            value: Value to check

        Returns:
            Tuple of (is_anomaly, reason)
        """
        config = self._configs.get(metric_name)
        state = self._states.get(metric_name)

        if not config or not state:
            return False, "No threshold configured"

        # Check upper bound
        if config.upper_bound is not None and value > config.upper_bound:
            return True, f"Exceeds static upper bound: {value} > {config.upper_bound}"

        if state.upper_bound < float('inf') and value > state.upper_bound:
            return True, f"Exceeds adaptive upper bound: {value} > {state.upper_bound:.2f}"

        # Check lower bound
        if config.lower_bound is not None and value < config.lower_bound:
            return True, f"Below static lower bound: {value} < {config.lower_bound}"

        if state.lower_bound > float('-inf') and value < state.lower_bound:
            return True, f"Below adaptive lower bound: {value} < {state.lower_bound:.2f}"

        return False, "Within normal range"

    def get_thresholds(self, metric_name: str) -> Optional[Dict]:
        """
        Get current thresholds for a metric

        Args:
            metric_name: Name of the metric

        Returns:
            Dictionary with threshold info or None
        """
        state = self._states.get(metric_name)
        config = self._configs.get(metric_name)

        if not state or not config:
            return None

        return {
            "metric_name": metric_name,
            "upper_bound": state.upper_bound,
            "lower_bound": state.lower_bound,
            "mean": state.mean,
            "std": state.std,
            "sample_count": state.sample_count,
            "adaptive": config.adaptive,
            "config": config.to_dict(),
        }

    def batch_update(self, metrics: List[MetricData]) -> None:
        """
        Update thresholds with multiple metrics

        Args:
            metrics: List of metric data points
        """
        for metric in metrics:
            self.update(metric.name, metric.value)

    def reset(self, metric_name: str) -> None:
        """
        Reset threshold state for a metric

        Args:
            metric_name: Name of the metric
        """
        if metric_name in self._states:
            del self._states[metric_name]
        if metric_name in self._configs:
            del self._configs[metric_name]
        self._save()

    def reset_all(self) -> None:
        """Reset all thresholds"""
        self._states.clear()
        self._configs.clear()
        self._save()

    def get_stats(self) -> Dict:
        """Get threshold manager statistics"""
        return {
            "total_metrics": len(self._states),
            "adaptive_metrics": sum(
                1 for c in self._configs.values()
                if c.adaptive
            ),
            "total_samples": sum(
                s.sample_count for s in self._states.values()
            ),
        }

    def _save(self) -> None:
        """Save threshold state to disk"""
        try:
            data = {
                "version": "1.0",
                "states": {
                    name: state.to_dict()
                    for name, state in self._states.items()
                },
                "configs": {
                    name: config.to_dict()
                    for name, config in self._configs.items()
                },
            }

            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"[WARNING] Failed to save threshold state: {e}")

    def _load(self) -> None:
        """Load threshold state from disk"""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                for name, state_data in data.get("states", {}).items():
                    self._states[name] = ThresholdState.from_dict(state_data)

                for name, config_data in data.get("configs", {}).items():
                    self._configs[name] = ThresholdConfig.from_dict(config_data)

        except Exception as e:
            print(f"[WARNING] Failed to load threshold state: {e}")


__all__ = [
    "ThresholdState",
    "AdaptiveThresholdManager",
]
