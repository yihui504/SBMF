"""
Anomaly Pattern Learner

Learns patterns from detected anomalies to improve future detection.
"""
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import json
import time
from collections import Counter, defaultdict

from detectors.base import AnomalyResult, AnomalyType, MetricData


class PatternType(Enum):
    """Types of anomaly patterns"""
    SPIKE = "spike"                    # Sudden increase
    DROP = "drop"                      # Sudden decrease
    DRIFT = "drift"                    # Gradual change
    CYCLIC = "cyclic"                  # Periodic behavior
    CORRELATED = "correlated"          # Multiple related metrics
    CONTEXT_SPECIFIC = "context_specific"  # Specific operations/scenarios


@dataclass
class AnomalyPattern:
    """
    A learned anomaly pattern

    Represents a recurring pattern in anomalies.
    """
    pattern_id: str
    name: str
    pattern_type: PatternType
    description: str

    # Detection criteria
    metric_conditions: Dict[str, Dict]  # metric_name -> condition
    context_conditions: Dict[str, Any]  # operation, database, etc.

    # Statistics
    occurrence_count: int = 0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    confidence: float = 0.0  # 0-1

    # Related
    related_patterns: List[str] = field(default_factory=list)
    mitigation_suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "pattern_type": self.pattern_type.value,
            "description": self.description,
            "metric_conditions": self.metric_conditions,
            "context_conditions": self.context_conditions,
            "occurrence_count": self.occurrence_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "confidence": self.confidence,
            "related_patterns": self.related_patterns,
            "mitigation_suggestions": self.mitigation_suggestions,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'AnomalyPattern':
        """Create from dictionary"""
        data["pattern_type"] = PatternType(data["pattern_type"])
        return cls(**data)

    def matches(self, anomaly: AnomalyResult) -> bool:
        """
        Check if anomaly matches this pattern

        Args:
            anomaly: Anomaly to check

        Returns:
            True if anomaly matches pattern
        """
        # Check anomaly type
        if not anomaly.context:
            return False

        # Check metric conditions
        for metric_name, condition in self.metric_conditions.items():
            if metric_name not in anomaly.metrics:
                continue

            value = anomaly.metrics[metric_name]

            # Check value conditions
            if "min_value" in condition and value < condition["min_value"]:
                return False
            if "max_value" in condition and value > condition["max_value"]:
                return False

        return True


class AnomalyPatternLearner:
    """
    Anomaly Pattern Learner

    Learns patterns from historical anomalies to improve detection
    and provide insights.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize pattern learner

        Args:
            storage_path: Path to persist learned patterns
        """
        self.storage_path = storage_path or Path("anomaly_patterns.json")
        self._patterns: Dict[str, AnomalyPattern] = {}
        self._anomaly_history: List[Dict] = []
        self._metric_cooccurrence: Dict[Tuple[str, str], int] = Counter()
        self._context_frequency: Dict[str, Counter] = defaultdict(Counter)

        self._load()

    def record_anomaly(self, anomaly: AnomalyResult) -> None:
        """
        Record an anomaly for learning

        Args:
            anomaly: Anomaly to record
        """
        if not anomaly.is_anomaly:
            return

        # Store in history
        record = {
            "type": anomaly.anomaly_type.value if anomaly.anomaly_type else None,
            "severity": anomaly.severity,
            "metrics": anomaly.metrics.copy(),
            "context": anomaly.context.copy(),
            "timestamp": anomaly.timestamp,
        }
        self._anomaly_history.append(record)

        # Limit history size
        if len(self._anomaly_history) > 1000:
            self._anomaly_history = self._anomaly_history[-1000:]

        # Update co-occurrence statistics
        metric_names = list(anomaly.metrics.keys())
        for i, m1 in enumerate(metric_names):
            for m2 in metric_names[i+1:]:
                self._metric_cooccurrence[(m1, m2)] += 1

        # Update context frequency
        if anomaly.context:
            for key, value in anomaly.context.items():
                self._context_frequency[key][str(value)] += 1

        # Extract and update patterns
        self._extract_patterns(anomaly)

        # Save after each recording for persistence in tests
        self._save()

    def _extract_patterns(self, anomaly: AnomalyResult) -> None:
        """Extract patterns from anomaly"""
        if not anomaly.is_anomaly or not anomaly.metrics:
            return

        # Create pattern ID based on metrics and context
        metric_keys = tuple(sorted(anomaly.metrics.keys()))
        context_key = str(anomaly.context.get("operation", "any"))
        pattern_key = (metric_keys, context_key)

        # Check if similar pattern exists
        for pattern in self._patterns.values():
            if pattern.matches(anomaly):
                # Update existing pattern
                pattern.occurrence_count += 1
                pattern.last_seen = anomaly.timestamp
                pattern.confidence = min(pattern.occurrence_count / 10.0, 1.0)
                return

        # Create new pattern
        pattern_type = self._infer_pattern_type(anomaly)
        pattern_id = f"PATTERN_{len(self._patterns) + 1:04d}"

        pattern = AnomalyPattern(
            pattern_id=pattern_id,
            name=f"{anomaly.anomaly_type.value if anomaly.anomaly_type else 'unknown'}_{context_key}",
            pattern_type=pattern_type,
            description=f"Pattern: {anomaly.description}",
            metric_conditions=self._extract_metric_conditions(anomaly),
            context_conditions={"operation": context_key},
            occurrence_count=1,
            confidence=0.1,
            mitigation_suggestions=self._generate_mitigation_suggestions(anomaly),
        )

        self._patterns[pattern_id] = pattern

    def _infer_pattern_type(self, anomaly: AnomalyResult) -> PatternType:
        """Infer pattern type from anomaly"""
        # Check if multiple metrics are affected
        if len(anomaly.metrics) > 2:
            return PatternType.CORRELATED

        # Check context for cyclic patterns
        if anomaly.context and "time" in anomaly.context:
            return PatternType.CYCLIC

        # Check severity for spike vs drop
        values = list(anomaly.metrics.values())
        if values:
            avg_value = sum(values) / len(values)
            if avg_value > 100:  # Arbitrary threshold
                return PatternType.SPIKE
            elif avg_value < 10:
                return PatternType.DROP

        return PatternType.CONTEXT_SPECIFIC

    def _extract_metric_conditions(self, anomaly: AnomalyResult) -> Dict[str, Dict]:
        """Extract metric conditions from anomaly"""
        conditions = {}

        for metric_name, value in anomaly.metrics.items():
            conditions[metric_name] = {
                "min_value": value * 0.9,  # 10% tolerance
                "max_value": value * 1.1,
                "typical_value": value,
            }

        return conditions

    def _generate_mitigation_suggestions(self, anomaly: AnomalyResult) -> List[str]:
        """Generate mitigation suggestions for anomaly"""
        suggestions = []

        if anomaly.anomaly_type == AnomalyType.PERFORMANCE:
            suggestions.append("Consider optimizing query performance")
            suggestions.append("Check for resource bottlenecks")
        elif anomaly.anomaly_type == AnomalyType.RESOURCE:
            suggestions.append("Scale up resources or optimize usage")
            suggestions.append("Check for memory leaks")
        elif anomaly.anomaly_type == AnomalyType.ERROR_RATE:
            suggestions.append("Review error logs for root cause")
            suggestions.append("Check API compatibility")

        return suggestions

    def get_patterns(self, pattern_type: Optional[PatternType] = None,
                     min_occurrences: int = 1) -> List[AnomalyPattern]:
        """
        Get learned patterns

        Args:
            pattern_type: Filter by pattern type
            min_occurrences: Minimum occurrence count

        Returns:
            List of patterns
        """
        patterns = list(self._patterns.values())

        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]

        patterns = [p for p in patterns if p.occurrence_count >= min_occurrences]

        return sorted(patterns, key=lambda p: -p.occurrence_count)

    def get_correlated_metrics(self) -> List[Tuple[str, str, int]]:
        """
        Get frequently co-occurring metrics

        Returns:
            List of (metric1, metric2, cooccurrence_count) tuples
        """
        return [
            (m1, m2, count)
            for (m1, m2), count in self._metric_cooccurrence.most_common(20)
        ]

    def get_context_insights(self) -> Dict[str, Dict]:
        """
        Get insights about anomaly contexts

        Returns:
            Dictionary mapping context keys to value frequencies
        """
        return {
            key: dict(counter.most_common(10))
            for key, counter in self._context_frequency.items()
        }

    def predict_next(self, context: Optional[Dict] = None) -> List[Dict]:
        """
        Predict likely next anomalies based on patterns

        Args:
            context: Current context

        Returns:
            List of predicted anomalies with probabilities
        """
        predictions = []

        for pattern in self._patterns.values():
            # Check if context matches
            if context and pattern.context_conditions:
                match = True
                for key, value in pattern.context_conditions.items():
                    if context.get(key) != value:
                        match = False
                        break
                if not match:
                    continue

            # Calculate prediction probability
            probability = min(pattern.confidence * pattern.occurrence_count / 10.0, 1.0)

            if probability > 0.3:
                predictions.append({
                    "pattern_id": pattern.pattern_id,
                    "name": pattern.name,
                    "probability": probability,
                    "type": pattern.pattern_type.value,
                    "description": pattern.description,
                })

        return sorted(predictions, key=lambda p: -p["probability"])

    def get_stats(self) -> Dict:
        """Get learner statistics"""
        return {
            "total_patterns": len(self._patterns),
            "total_anomalies_recorded": len(self._anomaly_history),
            "pattern_types": {
                pt.value: len([p for p in self._patterns.values() if p.pattern_type == pt])
                for pt in PatternType
            },
        }

    def _save(self) -> None:
        """Save patterns to disk"""
        try:
            data = {
                "version": "1.0",
                "patterns": {
                    pid: pattern.to_dict()
                    for pid, pattern in self._patterns.items()
                },
                "anomaly_history": self._anomaly_history[-100:],  # Limit history
                "metric_cooccurrence": {
                    f"{m1},{m2}": count
                    for (m1, m2), count in self._metric_cooccurrence.items()
                },
            }

            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"[WARNING] Failed to save patterns: {e}")

    def _load(self) -> None:
        """Load patterns from disk"""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                for pid, pattern_data in data.get("patterns", {}).items():
                    self._patterns[pid] = AnomalyPattern.from_dict(pattern_data)

                self._anomaly_history = data.get("anomaly_history", [])

                # Load co-occurrence
                for key, count in data.get("metric_cooccurrence", {}).items():
                    m1, m2 = key.split(",")
                    self._metric_cooccurrence[(m1, m2)] = count

        except Exception as e:
            print(f"[WARNING] Failed to load patterns: {e}")

    def clear(self) -> None:
        """Clear all learned patterns"""
        self._patterns.clear()
        self._anomaly_history.clear()
        self._metric_cooccurrence.clear()
        self._context_frequency.clear()


__all__ = [
    "PatternType",
    "AnomalyPattern",
    "AnomalyPatternLearner",
]
