"""
Boundary Value Generator

Generates test cases at boundary values of input parameters.
"""
from typing import Any, Dict, List, Optional, Set
import time

from generators.base import (
    BaseTestGenerator, TestCase, GenerationResult, Slot, GenerationStrategy
)


class BoundaryValueGenerator(BaseTestGenerator):
    """
    Boundary Value Generator

    Generates test cases at boundary values (min, max, just below/above)
    to catch edge case bugs.
    """

    def __init__(self, slots: List[Slot], operations: List[str],
                 config: Optional[Dict] = None):
        """
        Initialize boundary value generator

        Args:
            slots: List of input parameter slots
            operations: List of operations to generate tests for
            config: Configuration options
                - include_zero: Include zero values
                - include_negative: Include negative values
                - epsilon: Small value for near-boundary tests
        """
        super().__init__(slots, operations, config)
        self.include_zero = config.get("include_zero", True) if config else True
        self.include_negative = config.get("include_negative", True) if config else True
        self.epsilon = config.get("epsilon", 1) if config else 1

    def generate(self, count: int, operation: Optional[str] = None,
                 context: Optional[Dict] = None) -> GenerationResult:
        """
        Generate boundary value test cases

        Args:
            count: Number of test cases to generate
            operation: Specific operation to generate for
            context: Additional context

        Returns:
            GenerationResult with generated test cases
        """
        start_time = time.time()
        test_cases = []

        # Determine operations to generate for
        ops = [operation] if operation else self.operations

        for op in ops:
            # Generate boundary combinations
            boundary_tests = self._generate_boundary_tests(op, count)
            test_cases.extend(boundary_tests)

        # Deduplicate
        unique_cases = self._deduplicate(test_cases)

        # Trim to requested count
        unique_cases = unique_cases[:count]

        generation_time = time.time() - start_time

        return GenerationResult(
            test_cases=unique_cases,
            strategy=GenerationStrategy.BOUNDARY,
            generation_time=generation_time,
            total_generated=len(test_cases),
            unique_count=len(unique_cases),
            coverage_estimate=self._estimate_coverage(unique_cases),
            metadata={
                "include_zero": self.include_zero,
                "epsilon": self.epsilon,
            }
        )

    def _generate_boundary_tests(self, operation: str,
                                  count: int) -> List[TestCase]:
        """Generate boundary tests for an operation"""
        slot_names = self.get_slot_names(operation)
        tests = []

        # Get boundary values for each slot
        slot_boundaries = {}
        for slot_name in slot_names:
            slot = self.slots.get(slot_name)
            if slot:
                slot_boundaries[slot_name] = self._get_boundary_values(slot)

        # Generate combinations
        # Strategy: vary one parameter at a time at its boundaries
        for slot_name, boundaries in slot_boundaries.items():
            for value in boundaries:
                if value is None:
                    continue

                slot_values = {}
                # Set default values for other slots
                for other_slot in slot_names:
                    other = self.slots.get(other_slot)
                    if other:
                        # Use a nominal value
                        slot_values[other_slot] = self._get_nominal_value(other)

                # Set the boundary value for this slot
                slot_values[slot_name] = value

                tests.append(TestCase(
                    test_id=self.generate_test_id(operation),
                    operation=operation,
                    slot_values=slot_values,
                    metadata={"boundary_type": f"{slot_name}={value}"},
                ))

                if len(tests) >= count:
                    break

            if len(tests) >= count:
                break

        return tests

    def _get_boundary_values(self, slot: Slot) -> List[Any]:
        """Get boundary values for a slot"""
        boundaries = []

        if slot.data_type == "int":
            # Min, max, and near values
            if slot.min_value is not None:
                boundaries.extend([
                    slot.min_value,
                    slot.min_value + self.epsilon,
                    slot.min_value - self.epsilon if self.include_negative else None,
                ])

            if slot.max_value is not None:
                boundaries.extend([
                    slot.max_value,
                    slot.max_value - self.epsilon,
                    slot.max_value + self.epsilon,
                ])

            if self.include_zero:
                boundaries.append(0)

            # Special: 1, -1
            boundaries.extend([1, -1])

        elif slot.data_type == "float":
            # Similar to int but with float epsilon
            if slot.min_value is not None:
                boundaries.extend([
                    slot.min_value,
                    slot.min_value + float(self.epsilon),
                ])

            if slot.max_value is not None:
                boundaries.extend([
                    slot.max_value,
                    slot.max_value - float(self.epsilon),
                ])

            if self.include_zero:
                boundaries.append(0.0)

            # Special: 1.0, -1.0
            boundaries.extend([1.0, -1.0])

        elif slot.data_type == "str":
            # String boundaries: empty, very long, special characters
            boundaries.extend([
                "",  # Empty
                " ",  # Single space
                "a",  # Single character
                "0",  # Numeric string
            ])

        elif slot.data_type == "bool":
            boundaries.extend([True, False])

        elif slot.data_type == "list":
            # List boundaries: empty, single element
            boundaries.extend([
                [],  # Empty
                [1.0],  # Single element
            ])

        # Add default value if different
        if slot.default_value is not None:
            boundaries.append(slot.default_value)

        # Filter None and deduplicate
        seen = set()
        result = []
        for b in boundaries:
            if b is not None and str(b) not in seen:
                seen.add(str(b))
                result.append(b)

        return result

    def _get_nominal_value(self, slot: Slot) -> Any:
        """Get a nominal (normal) value for a slot"""
        if slot.default_value is not None:
            return slot.default_value

        if slot.allowed_values:
            return list(slot.allowed_values)[0]

        if slot.data_type == "int":
            min_val = slot.min_value or 1
            max_val = slot.max_value or 100
            return (min_val + max_val) // 2

        elif slot.data_type == "float":
            min_val = slot.min_value or 0.0
            max_val = slot.max_value or 1.0
            return (min_val + max_val) / 2.0

        elif slot.data_type == "str":
            return "test"

        elif slot.data_type == "bool":
            return True

        elif slot.data_type == "list":
            return [1.0, 2.0, 3.0]

        return None

    def _estimate_coverage(self, test_cases: List[TestCase]) -> float:
        """
        Estimate coverage based on boundary coverage

        For boundary analysis, we check how many unique boundary
        values are covered per slot.
        """
        if not test_cases:
            return 0.0

        coverage_scores = []

        for slot_name, slot in self.slots.items():
            boundaries = set(self._get_boundary_values(slot))
            covered = set()

            for tc in test_cases:
                if slot_name in tc.slot_values:
                    value = tc.slot_values[slot_name]
                    # Check if this is near a boundary
                    for b in boundaries:
                        if self._is_near_boundary(value, b, slot):
                            covered.add(str(b))
                            break

            if boundaries:
                coverage_scores.append(len(covered) / len(boundaries))

        return sum(coverage_scores) / len(coverage_scores) if coverage_scores else 0.0

    def _is_near_boundary(self, value: Any, boundary: Any, slot: Slot) -> bool:
        """Check if a value is near a boundary"""
        if value is None or boundary is None:
            return False

        if isinstance(value, (int, float)):
            return abs(value - boundary) <= self.epsilon

        return str(value) == str(boundary)


__all__ = ["BoundaryValueGenerator"]
