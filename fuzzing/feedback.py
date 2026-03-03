"""
Feedback Analyzer

Analyzes test results to guide fuzzing.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import time


class CoverageType(Enum):
    """Types of coverage to track"""
    EDGE = "edge"           # Edge coverage
    BRANCH = "branch"       # Branch coverage
    INPUT = "input"         # Input space coverage
    CODE = "code"           # Code coverage


@dataclass
class CoverageData:
    """
    Coverage data for feedback
    """
    total_edges: int = 0
    covered_edges: int = 0
    total_branches: int = 0
    covered_branches: int = 0
    edges: List[int] = field(default_factory=list)
    branches: List[int] = field(default_factory=list)
    input_hash: str = ""

    def coverage_percentage(self) -> float:
        """Calculate overall coverage percentage"""
        total = self.total_edges + self.total_branches
        if total == 0:
            return 0.0
        covered = self.covered_edges + self.covered_branches
        return (covered / total) * 100

    def new_coverage(self) -> set:
        """Get newly covered elements"""
        return (set(self.edges) | set(self.branches)) - \
               (set(getattr(self, '_prev_edges', [])) | set(getattr(self, '_prev_branches', [])))

    def save_state(self) -> None:
        """Save current state for comparison"""
        self._prev_edges = self.edges.copy()
        self._prev_branches = self.branches.copy()


class FeedbackAnalyzer:
    """
    Feedback Analyzer

    Analyzes test results to provide feedback for fuzzing.
    """

    def __init__(self):
        """Initialize feedback analyzer"""
        self._coverage_history: List[CoverageData] = []
        self._interesting_inputs: List[Dict] = []

    def analyze_result(self, test_input: Dict, result: Dict) -> Dict:
        """
        Analyze a test result

        Args:
            test_input: The input that was tested
            result: Execution result

        Returns:
            Feedback analysis
        """
        feedback = {
            "interesting": False,
            "reason": "",
            "priority": "low",
            "suggestions": [],
        }

        # Priority hierarchy (higher number = higher priority)
        PRIORITY_LEVELS = {"critical": 4, "high": 3, "medium": 2, "low": 1}

        def set_priority(priority: str) -> None:
            """Set priority only if it's higher than current"""
            current_level = PRIORITY_LEVELS.get(feedback["priority"], 0)
            new_level = PRIORITY_LEVELS.get(priority, 0)
            if new_level > current_level:
                feedback["priority"] = priority

        # Check for crashes
        if result.get("crashed") or result.get("status") == "error":
            feedback["interesting"] = True
            feedback["reason"] = "Crash detected"
            set_priority("critical")
            feedback["suggestions"].append("Explore around this input")

        # Check for new coverage
        coverage = result.get("coverage", {})
        if coverage:
            new_coverage = self._get_new_coverage(coverage)
            if new_coverage:
                feedback["interesting"] = True
                feedback["reason"] = f"New coverage: {len(new_coverage)} elements"
                set_priority("medium")
                feedback["suggestions"].append("Mutate this input further")

        # Check for timeouts
        if result.get("hung") or result.get("status") == "timeout":
            feedback["interesting"] = True
            feedback["reason"] = "Timeout detected"
            set_priority("low")
            feedback["suggestions"].append("Reduce input size")

        # Check for unique error messages (but not if already critical)
        error = result.get("error", "")
        if error and self._is_unique_error(error):
            feedback["interesting"] = True
            if feedback["priority"] != "critical":
                feedback["reason"] = "Unique error message"
            set_priority("high")
            feedback["suggestions"].append("Investigate this error")

        return feedback

    def _get_new_coverage(self, coverage: Dict) -> set:
        """Get newly covered elements"""
        # Simplified - real implementation would track properly
        return set()

    def _is_unique_error(self, error: str) -> bool:
        """Check if error is unique"""
        # For simplicity, assume all errors are potentially unique
        # Real implementation would track seen errors
        return len(error) > 0

    def get_coverage_trend(self) -> Dict:
        """
        Get coverage trend over time

        Returns:
            Trend analysis
        """
        if len(self._coverage_history) < 2:
            return {"message": "Insufficient data"}

        recent = self._coverage_history[-20:]

        coverage_values = [c.coverage_percentage() for c in recent]

        return {
            "current_coverage": coverage_values[-1] if coverage_values else 0,
            "trend": "increasing" if coverage_values[-1] > coverage_values[0] else "stable",
            "values": coverage_values,
        }

    def add_interesting_input(self, test_input: Dict, priority: str) -> None:
        """Add an interesting input to the pool"""
        self._interesting_inputs.append({
            "input": test_input,
            "priority": priority,
            "timestamp": time.time(),
        })

        # Limit size
        if len(self._interesting_inputs) > 1000:
            # Keep high priority ones
            self._interesting_inputs = sorted(
                self._interesting_inputs,
                key=lambda x: {"critical": 3, "high": 2, "medium": 1, "low": 0}.get(x["priority"], 0),
                reverse=True
            )[:1000]

    def get_interesting_inputs(self, limit: int = 100) -> List[Dict]:
        """Get interesting inputs for mutation"""
        return [item["input"] for item in self._interesting_inputs[:limit]]

    def get_stats(self) -> Dict:
        """Get analyzer statistics"""
        return {
            "coverage_samples": len(self._coverage_history),
            "interesting_inputs": len(self._interesting_inputs),
        }


__all__ = [
    "CoverageType",
    "CoverageData",
    "FeedbackAnalyzer",
]
