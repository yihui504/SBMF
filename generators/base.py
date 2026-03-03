"""
Base Test Generator

Abstract base class for all test generators.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import time


class GenerationStrategy(Enum):
    """Test generation strategies"""
    RANDOM = "random"
    BOUNDARY = "boundary"
    COMBINATORIAL = "pairwise"
    ADAPTIVE = "adaptive"
    HYBRID = "hybrid"
    AGENT = "agent"  # Agent-driven adaptive strategy


@dataclass
class TestCase:
    """
    A generated test case

    Simple data structure that represents a test case.
    """
    test_id: str
    operation: str  # insert, search, delete, etc.
    slot_values: Dict[str, Any]  # Input parameter values
    preconditions: List[str] = field(default_factory=list)
    expected_status: str = "SUCCESS"  # SUCCESS, FAILURE, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "test_id": self.test_id,
            "operation": self.operation,
            "slot_values": self.slot_values,
            "preconditions": self.preconditions,
            "expected_status": self.expected_status,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'TestCase':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class GenerationResult:
    """
    Result of test generation

    Contains generated test cases and metadata about the generation process.
    """
    test_cases: List[TestCase]
    strategy: GenerationStrategy
    generation_time: float
    total_generated: int
    unique_count: int
    coverage_estimate: float = 0.0  # Estimated input coverage (0-1)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "test_cases": [tc.to_dict() for tc in self.test_cases],
            "strategy": self.strategy.value,
            "generation_time": self.generation_time,
            "total_generated": self.total_generated,
            "unique_count": self.unique_count,
            "coverage_estimate": self.coverage_estimate,
            "metadata": self.metadata,
        }


@dataclass
class Slot:
    """
    Represents an input parameter slot

    A slot defines a parameter with its domain constraints.
    """
    name: str
    data_type: str  # int, float, str, bool, list, etc.
    required: bool = True
    default_value: Any = None
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    allowed_values: Optional[Set[Any]] = None
    description: str = ""

    def validate(self, value: Any) -> bool:
        """
        Validate a value against slot constraints

        Args:
            value: Value to validate

        Returns:
            True if value is valid
        """
        # Check required
        if self.required and value is None:
            return False

        # Check type
        if value is not None:
            type_map = {
                "int": int,
                "float": (int, float),
                "str": str,
                "bool": bool,
                "list": list,
                "dict": dict,
            }
            expected_type = type_map.get(self.data_type)
            if expected_type and not isinstance(value, expected_type):
                return False

        # Check min/max
        if self.min_value is not None and value is not None:
            if value < self.min_value:
                return False

        if self.max_value is not None and value is not None:
            if value > self.max_value:
                return False

        # Check allowed values
        if self.allowed_values is not None and value is not None:
            if value not in self.allowed_values:
                return False

        return True


class BaseTestGenerator(ABC):
    """
    Abstract base class for test generators

    All test generators should inherit from this class and implement
    the generate method.
    """

    def __init__(self, slots: List[Slot], operations: List[str],
                 config: Optional[Dict] = None):
        """
        Initialize test generator

        Args:
            slots: List of input parameter slots
            operations: List of operations to generate tests for
            config: Optional configuration
        """
        self.slots = {s.name: s for s in slots}
        self.operations = operations
        self.config = config or {}
        self._generated_count = 0
        self._test_history: List[TestCase] = []

    @abstractmethod
    def generate(self, count: int, operation: Optional[str] = None,
                 context: Optional[Dict] = None) -> GenerationResult:
        """
        Generate test cases

        Args:
            count: Number of test cases to generate
            operation: Specific operation to generate for (None = all operations)
            context: Additional context for generation

        Returns:
            GenerationResult with generated test cases
        """
        pass

    def generate_test_id(self, operation: str) -> str:
        """
        Generate a unique test ID

        Args:
            operation: Operation name

        Returns:
            Unique test ID
        """
        self._generated_count += 1
        return f"{operation}_{self._generated_count:06d}"

    def get_slot_names(self, operation: str) -> List[str]:
        """
        Get relevant slot names for an operation

        Args:
            operation: Operation name

        Returns:
            List of slot names
        """
        # For now, return all slots
        # Subclasses can override to filter by operation
        return list(self.slots.keys())

    def validate_test_case(self, test_case: TestCase) -> bool:
        """
        Validate a generated test case

        Args:
            test_case: Test case to validate

        Returns:
            True if valid
        """
        for slot_name, value in test_case.slot_values.items():
            slot = self.slots.get(slot_name)
            if slot and not slot.validate(value):
                return False
        return True

    def get_stats(self) -> Dict:
        """
        Get generator statistics

        Returns:
            Statistics dictionary
        """
        return {
            "total_generated": self._generated_count,
            "history_size": len(self._test_history),
            "slots": len(self.slots),
            "operations": len(self.operations),
        }

    def _deduplicate(self, test_cases: List[TestCase]) -> List[TestCase]:
        """
        Remove duplicate test cases

        Args:
            test_cases: List of test cases

        Returns:
            Deduplicated list
        """
        seen = set()
        unique = []

        for tc in test_cases:
            # Create hashable representation
            key = (tc.operation, tuple(sorted(tc.slot_values.items())))
            if key not in seen:
                seen.add(key)
                unique.append(tc)

        return unique


__all__ = [
    "GenerationStrategy",
    "TestCase",
    "GenerationResult",
    "Slot",
    "BaseTestGenerator",
]
