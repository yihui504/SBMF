"""
Combinatorial Test Generator

Implements pairwise (all-pairs) combinatorial test generation.
"""
from typing import Any, Dict, List, Optional, Set, Tuple
import itertools
import time

from generators.base import (
    BaseTestGenerator, TestCase, GenerationResult, Slot, GenerationStrategy
)


class PairwiseGenerator(BaseTestGenerator):
    """
    Pairwise (All-Pairs) Combinatorial Test Generator

    Generates test cases such that every possible pair of parameter
    values is covered at least once. This provides good coverage with
    fewer test cases than full combinatorial explosion.
    """

    def __init__(self, slots: List[Slot], operations: List[str],
                 config: Optional[Dict] = None):
        """
        Initialize pairwise generator

        Args:
            slots: List of input parameter slots
            operations: List of operations to generate tests for
            config: Configuration options
                - values_per_slot: Number of values to test per slot
                - max_combinations: Maximum number of combinations to generate
        """
        super().__init__(slots, operations, config)
        self.values_per_slot = config.get("values_per_slot", 3) if config else 3
        self.max_combinations = config.get("max_combinations", 1000) if config else 1000

    def generate(self, count: int, operation: Optional[str] = None,
                 context: Optional[Dict] = None) -> GenerationResult:
        """
        Generate pairwise test cases

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
            # Generate pairwise tests
            pairwise_tests = self._generate_pairwise_tests(op, count)
            test_cases.extend(pairwise_tests)

        # Deduplicate
        unique_cases = self._deduplicate(test_cases)

        # Trim to requested count
        unique_cases = unique_cases[:count]

        generation_time = time.time() - start_time

        return GenerationResult(
            test_cases=unique_cases,
            strategy=GenerationStrategy.COMBINATORIAL,
            generation_time=generation_time,
            total_generated=len(test_cases),
            unique_count=len(unique_cases),
            coverage_estimate=self._estimate_pair_coverage(unique_cases),
            metadata={
                "values_per_slot": self.values_per_slot,
            }
        )

    def _generate_pairwise_tests(self, operation: str,
                                  count: int) -> List[TestCase]:
        """Generate pairwise tests for an operation"""
        slot_names = self.get_slot_names(operation)

        # Select values for each slot
        slot_values = {}
        for slot_name in slot_names:
            slot = self.slots.get(slot_name)
            if slot:
                slot_values[slot_name] = self._select_test_values(slot)

        # Generate all combinations of pairs
        tests = []

        # For each pair of slots, generate combinations
        for i, slot1 in enumerate(slot_names):
            for slot2 in slot_names[i+1:]:
                for val1 in slot_values[slot1]:
                    for val2 in slot_values[slot2]:
                        # Create test with this pair
                        test_slot_values = {}

                        # Set the pair values
                        test_slot_values[slot1] = val1
                        test_slot_values[slot2] = val2

                        # Set nominal values for other slots
                        for other_slot in slot_names:
                            if other_slot != slot1 and other_slot != slot2:
                                other_slot_obj = self.slots.get(other_slot)
                                if other_slot_obj and slot_values.get(other_slot):
                                    # Use first value as nominal
                                    test_slot_values[other_slot] = list(slot_values[other_slot])[0]

                        tests.append(TestCase(
                            test_id=self.generate_test_id(operation),
                            operation=operation,
                            slot_values=test_slot_values,
                            metadata={"pair": f"{slot1}={val1}, {slot2}={val2}"},
                        ))

                        if len(tests) >= count:
                            return tests

        return tests

    def _select_test_values(self, slot: Slot) -> Set[Any]:
        """Select a set of test values for a slot"""
        values = set()

        # Add boundary values if defined
        if slot.min_value is not None:
            values.add(slot.min_value)
        if slot.max_value is not None:
            values.add(slot.max_value)

        # Add default value
        if slot.default_value is not None:
            values.add(slot.default_value)

        # Add from allowed values
        if slot.allowed_values:
            values.update(list(slot.allowed_values)[:self.values_per_slot])

        # Add some typical values based on type
        if len(values) < self.values_per_slot:
            if slot.data_type == "int":
                min_val = slot.min_value or 0
                max_val = slot.max_value or 100
                step = max(1, (max_val - min_val) // (self.values_per_slot + 1))
                for i in range(self.values_per_slot):
                    values.add(min_val + i * step)

            elif slot.data_type == "float":
                min_val = slot.min_value or 0.0
                max_val = slot.max_value or 1.0
                step = (max_val - min_val) / (self.values_per_slot + 1)
                for i in range(self.values_per_slot):
                    values.add(min_val + i * step)

            elif slot.data_type == "str":
                values.update(["", "test", "a_very_long_string_name"])

            elif slot.data_type == "bool":
                values.update([True, False])

            elif slot.data_type == "list":
                values.update([[], [1.0], [1.0, 2.0, 3.0]])

        # Convert to set and limit
        result = set(values)
        while len(result) > self.values_per_slot:
            result.pop()

        return result

    def _estimate_pair_coverage(self, test_cases: List[TestCase]) -> float:
        """
        Estimate pairwise coverage

        Count how many unique pairs are covered.
        """
        if not test_cases:
            return 0.0

        slot_names = list(self.slots.keys())
        if len(slot_names) < 2:
            return 1.0

        # Get all possible pairs
        all_pairs = set()
        for i, slot1 in enumerate(slot_names):
            for slot2 in slot_names[i+1:]:
                all_pairs.add((slot1, slot2))

        # Count covered pairs
        covered_pairs = set()

        for tc in test_cases:
            for slot1, slot2 in all_pairs:
                if slot1 in tc.slot_values and slot2 in tc.slot_values:
                    covered_pairs.add((slot1, slot2))

        return len(covered_pairs) / len(all_pairs) if all_pairs else 0.0


class OrthogonalArrayGenerator(BaseTestGenerator):
    """
    Orthogonal Array Generator

    Generates orthogonal arrays for balanced combinatorial testing.
    Simplified implementation for common cases.
    """

    def __init__(self, slots: List[Slot], operations: List[str],
                 config: Optional[Dict] = None):
        """
        Initialize orthogonal array generator

        Args:
            slots: List of input parameter slots
            operations: List of operations to generate tests for
            config: Configuration options
                - strength: Interaction strength (2 = pairwise)
        """
        super().__init__(slots, operations, config)
        self.strength = config.get("strength", 2) if config else 2

    def generate(self, count: int, operation: Optional[str] = None,
                 context: Optional[Dict] = None) -> GenerationResult:
        """
        Generate orthogonal array test cases

        This is a simplified implementation. Full OA generation
        requires complex algorithms.
        """
        start_time = time.time()

        # For now, fall back to pairwise
        # A full implementation would use existing OA libraries
        # or implement the IPO (In-Parameter-Order) algorithm
        pairwise_gen = PairwiseGenerator(
            list(self.slots.values()),
            self.operations,
            self.config
        )

        result = pairwise_gen.generate(count, operation, context)
        result.strategy = GenerationStrategy.COMBINATORIAL

        return result


__all__ = [
    "PairwiseGenerator",
    "OrthogonalArrayGenerator",
]
