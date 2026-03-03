"""
Random Test Generator

Generates random test cases within defined slot constraints.
"""
import random
from typing import Any, Dict, List, Optional
import time

from generators.base import (
    BaseTestGenerator, TestCase, GenerationResult, Slot, GenerationStrategy
)


class RandomTestGenerator(BaseTestGenerator):
    """
    Random Test Generator

    Generates test cases by randomly selecting values within
    the constraints defined by slots.
    """

    def __init__(self, slots: List[Slot], operations: List[str],
                 config: Optional[Dict] = None):
        """
        Initialize random test generator

        Args:
            slots: List of input parameter slots
            operations: List of operations to generate tests for
            config: Configuration options
                - seed: Random seed for reproducibility
                - invalid_ratio: Ratio of invalid tests to generate (0-1)
                - max_attempts: Max attempts to generate valid test
        """
        super().__init__(slots, operations, config)
        self.seed = config.get("seed") if config else None
        self.invalid_ratio = config.get("invalid_ratio", 0.1) if config else 0.1
        self.max_attempts = config.get("max_attempts", 100) if config else 100

        if self.seed is not None:
            random.seed(self.seed)

    def generate(self, count: int, operation: Optional[str] = None,
                 context: Optional[Dict] = None) -> GenerationResult:
        """
        Generate random test cases

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
            for _ in range(count // len(ops) + 1):
                if len(test_cases) >= count:
                    break

                # Generate with retry for validity
                for attempt in range(self.max_attempts):
                    test_case = self._generate_random_test(op)

                    # Check if we want invalid tests
                    should_be_invalid = random.random() < self.invalid_ratio

                    if should_be_invalid or self.validate_test_case(test_case):
                        test_cases.append(test_case)
                        break

        # Trim to exact count
        test_cases = test_cases[:count]

        # Deduplicate
        unique_cases = self._deduplicate(test_cases)

        generation_time = time.time() - start_time

        return GenerationResult(
            test_cases=unique_cases,
            strategy=GenerationStrategy.RANDOM,
            generation_time=generation_time,
            total_generated=len(test_cases),
            unique_count=len(unique_cases),
            coverage_estimate=self._estimate_coverage(unique_cases),
            metadata={
                "seed": self.seed,
                "invalid_ratio": self.invalid_ratio,
            }
        )

    def _generate_random_test(self, operation: str) -> TestCase:
        """Generate a single random test case"""
        slot_names = self.get_slot_names(operation)
        slot_values = {}

        for slot_name in slot_names:
            slot = self.slots.get(slot_name)
            if slot:
                slot_values[slot_name] = self._generate_random_value(slot)

        return TestCase(
            test_id=self.generate_test_id(operation),
            operation=operation,
            slot_values=slot_values,
        )

    def _generate_random_value(self, slot: Slot) -> Any:
        """Generate a random value for a slot"""
        # If allowed values specified, pick from them
        if slot.allowed_values:
            return random.choice(list(slot.allowed_values))

        # Generate based on data type
        if slot.data_type == "int":
            min_val = slot.min_value or -999999
            max_val = slot.max_value or 999999
            return random.randint(min_val, max_val)

        elif slot.data_type == "float":
            min_val = slot.min_value or -999999.0
            max_val = slot.max_value or 999999.0
            return random.uniform(min_val, max_val)

        elif slot.data_type == "str":
            # Generate random string
            length = random.randint(1, 50)
            chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
            return ''.join(random.choice(chars) for _ in range(length))

        elif slot.data_type == "bool":
            return random.choice([True, False])

        elif slot.data_type == "list":
            # Generate list of random length
            length = random.randint(0, 10)
            return [random.random() for _ in range(length)]

        else:
            # Default: return None or default value
            return slot.default_value

    def _estimate_coverage(self, test_cases: List[TestCase]) -> float:
        """
        Estimate input space coverage

        This is a simplified heuristic. Actual coverage would require
        more sophisticated analysis.
        """
        if not test_cases:
            return 0.0

        # Count unique values per slot
        unique_values = {}
        for tc in test_cases:
            for slot_name, value in tc.slot_values.items():
                if slot_name not in unique_values:
                    unique_values[slot_name] = set()
                unique_values[slot_name].add(str(value))

        # Estimate: average unique ratio across slots
        ratios = []
        for slot_name, slot in self.slots.items():
            if slot_name in unique_values:
                # Assume 100 possible values as baseline for estimation
                unique_count = len(unique_values[slot_name])
                ratios.append(min(unique_count / 100.0, 1.0))

        return sum(ratios) / len(ratios) if ratios else 0.0


__all__ = ["RandomTestGenerator"]
