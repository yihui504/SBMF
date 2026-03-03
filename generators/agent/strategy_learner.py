"""
Strategy Learner

Learns from historical test results to improve test generation strategies.
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json
import time
from collections import Counter, defaultdict


@dataclass
class BugOccurrence:
    """Record of a bug occurrence"""
    operation: str
    slot_values: Dict[str, Any]
    error_type: str
    error_message: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "operation": self.operation,
            "slot_values": self.slot_values,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'BugOccurrence':
        return cls(**data)


@dataclass
class EffectivePattern:
    """An effective test pattern that found bugs"""
    description: str
    operation: str
    slot_template: Dict[str, Any]  # Template with wildcards
    bugs_found: int = 0
    last_seen: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "description": self.description,
            "operation": self.operation,
            "slot_template": self.slot_template,
            "bugs_found": self.bugs_found,
            "last_seen": self.last_seen,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'EffectivePattern':
        return cls(**data)


class StrategyLearner:
    """
    Strategy Learner

    Analyzes historical test results to identify effective patterns
    and improve future test generation.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize strategy learner

        Args:
            storage_path: Path to store learned patterns
        """
        self.storage_path = storage_path or Path("test_strategy_learning.json")

        # Learning data
        self._bug_history: List[BugOccurrence] = []
        self._effective_patterns: List[EffectivePattern] = []
        self._slot_effectiveness: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._operation_bug_rate: Dict[str, Tuple[int, int]] = {}  # (bugs, total)

        self._load()

    def record_bug(self, operation: str, slot_values: Dict[str, Any],
                   error_type: str, error_message: str) -> None:
        """
        Record a bug occurrence

        Args:
            operation: Operation where bug occurred
            slot_values: Input values that triggered the bug
            error_type: Type of error
            error_message: Error message
        """
        bug = BugOccurrence(
            operation=operation,
            slot_values=slot_values,
            error_type=error_type,
            error_message=error_message
        )

        self._bug_history.append(bug)

        # Update effectiveness metrics
        self._update_effectiveness(bug)

        # Extract and store patterns
        self._extract_patterns(bug)

        # Save after each bug for persistence
        self._save()

    def _update_effectiveness(self, bug: BugOccurrence) -> None:
        """Update effectiveness metrics based on bug"""
        for slot_name, value in bug.slot_values.items():
            # Track which values led to bugs
            value_key = self._categorize_value(value)
            self._slot_effectiveness[slot_name][value_key] += 1

    def _categorize_value(self, value: Any) -> str:
        """Categorize a value for pattern learning"""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return str(value)
        elif isinstance(value, int):
            if value < 0:
                return "negative"
            elif value == 0:
                return "zero"
            elif value == 1:
                return "one"
            elif value > 1000:
                return "large_positive"
            else:
                return "positive"
        elif isinstance(value, float):
            if value < 0.0:
                return "negative_float"
            elif value == 0.0:
                return "zero_float"
            elif value > 1.0:
                return "large_float"
            else:
                return "small_float"
        elif isinstance(value, str):
            if not value:
                return "empty_string"
            elif len(value) == 1:
                return "single_char"
            elif len(value) > 100:
                return "long_string"
            else:
                return "normal_string"
        elif isinstance(value, list):
            if not value:
                return "empty_list"
            elif len(value) == 1:
                return "single_element_list"
            else:
                return "multi_element_list"
        else:
            return "other"

    def _extract_patterns(self, bug: BugOccurrence) -> None:
        """Extract effective patterns from bug occurrence"""
        # Create a pattern template
        template = {}
        for slot_name, value in bug.slot_values.items():
            template[slot_name] = self._categorize_value(value)

        # Check if similar pattern exists
        for pattern in self._effective_patterns:
            if (pattern.operation == bug.operation and
                self._patterns_match(pattern.slot_template, template)):
                pattern.bugs_found += 1
                pattern.last_seen = time.time()
                return

        # Create new pattern
        pattern = EffectivePattern(
            description=f"Bug pattern for {bug.operation}",
            operation=bug.operation,
            slot_template=template,
            bugs_found=1
        )
        self._effective_patterns.append(pattern)

    def _patterns_match(self, template1: Dict, template2: Dict) -> bool:
        """Check if two pattern templates are similar"""
        if len(template1) != len(template2):
            return False

        matches = 0
        for key in template1:
            if key in template2 and template1[key] == template2[key]:
                matches += 1

        return matches >= len(template1) * 0.8  # 80% similarity

    def get_effective_values(self, slot_name: str, top_n: int = 5) -> List[Tuple[str, int]]:
        """
        Get most effective values for a slot

        Args:
            slot_name: Name of the slot
            top_n: Number of top values to return

        Returns:
            List of (value_category, count) tuples
        """
        if slot_name not in self._slot_effectiveness:
            return []

        effectiveness = self._slot_effectiveness[slot_name]
        return sorted(effectiveness.items(), key=lambda x: -x[1])[:top_n]

    def get_effective_patterns(self, operation: Optional[str] = None,
                                min_bugs: int = 1) -> List[EffectivePattern]:
        """
        Get effective patterns

        Args:
            operation: Filter by operation, or None for all
            min_bugs: Minimum bug count

        Returns:
            List of effective patterns
        """
        patterns = self._effective_patterns

        if operation:
            patterns = [p for p in patterns if p.operation == operation]

        patterns = [p for p in patterns if p.bugs_found >= min_bugs]

        return sorted(patterns, key=lambda p: -p.bugs_found)

    def get_test_suggestions(self, operation: str,
                              count: int = 10) -> List[Dict[str, Any]]:
        """
        Get test suggestions based on learning

        Args:
            operation: Operation to generate suggestions for
            count: Number of suggestions

        Returns:
            List of suggested test configurations
        """
        suggestions = []

        # Get effective patterns for this operation
        patterns = self.get_effective_patterns(operation, min_bugs=1)

        for pattern in patterns[:count]:
            suggestions.append({
                "operation": operation,
                "slot_template": pattern.slot_template,
                "bugs_found": pattern.bugs_found,
                "confidence": min(pattern.bugs_found / 10.0, 1.0),
            })

        return suggestions

    def get_stats(self) -> Dict:
        """Get learner statistics"""
        return {
            "total_bugs_recorded": len(self._bug_history),
            "effective_patterns": len(self._effective_patterns),
            "slots_tracked": len(self._slot_effectiveness),
            "operations_tracked": len(self._operation_bug_rate),
        }

    def _save(self) -> None:
        """Save learning data to disk"""
        try:
            data = {
                "version": "1.0",
                "bug_history": [b.to_dict() for b in self._bug_history],
                "effective_patterns": [p.to_dict() for p in self._effective_patterns],
                "slot_effectiveness": dict(self._slot_effectiveness),
                "operation_bug_rate": {
                    op: {"bugs": bugs, "total": total}
                    for op, (bugs, total) in self._operation_bug_rate.items()
                },
            }

            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"[WARNING] Failed to save learning data: {e}")

    def _load(self) -> None:
        """Load learning data from disk"""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                self._bug_history = [
                    BugOccurrence.from_dict(b) for b in data.get("bug_history", [])
                ]
                self._effective_patterns = [
                    EffectivePattern.from_dict(p) for p in data.get("effective_patterns", [])
                ]

                # Load slot effectiveness
                self._slot_effectiveness = defaultdict(lambda: defaultdict(int))
                for slot_name, values in data.get("slot_effectiveness", {}).items():
                    self._slot_effectiveness[slot_name] = defaultdict(int, values)

                # Load operation bug rates
                self._operation_bug_rate = {}
                for op, rate_data in data.get("operation_bug_rate", {}).items():
                    self._operation_bug_rate[op] = (
                        rate_data["bugs"], rate_data["total"]
                    )

        except Exception as e:
            print(f"[WARNING] Failed to load learning data: {e}")

    def clear(self) -> None:
        """Clear all learning data"""
        self._bug_history.clear()
        self._effective_patterns.clear()
        self._slot_effectiveness.clear()
        self._operation_bug_rate.clear()

        if self.storage_path.exists():
            self.storage_path.unlink()


__all__ = ["StrategyLearner", "BugOccurrence", "EffectivePattern"]
