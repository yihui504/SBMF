"""
Mutation Strategies

Intelligent mutation strategies for fuzzing.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import random
import copy


class MutationStrategy(Enum):
    """Types of mutation strategies"""
    RANDOM = "random"                    # Random value changes
    BOUNDARY = "boundary"                # Boundary value fuzzing
    BIT_FLIP = "bit_flip"                # Flip individual bits
    ARITHMETIC = "arithmetic"            # Arithmetic operations
    DICTIONARY = "dictionary"            # Dictionary-based mutations
    SPLICING = "splicing"                # Input splicing
    CROSSOVER = "crossover"               # Crossover two inputs
    STRUCTURE = "structure"              # Structure mutation
    INTERESTING = "interesting"          # Feedback-driven
    HYBRID = "hybrid"                    # Combination of strategies


@dataclass
class Mutation:
    """A mutation operation"""
    strategy: MutationStrategy
    description: str
    apply_func: callable


class Mutator:
    """
    Mutator

    Applies mutations to test inputs.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize mutator

        Args:
            config: Configuration options
        """
        self.config = config or {}
        self.strategies = [
            MutationStrategy.RANDOM,
            MutationStrategy.BOUNDARY,
            MutationStrategy.ARITHMETIC,
            MutationStrategy.DICTIONARY,
            MutationStrategy.SPLICING,
            MutationStrategy.CROSSOVER,
        ]
        self._mutation_count = 0

    def mutate(self, input_data: Dict[str, Any],
              strategy: Optional[MutationStrategy] = None) -> Dict[str, Any]:
        """
        Mutate an input

        Args:
            input_data: Input to mutate
            strategy: Specific strategy to use (random if None)

        Returns:
            Mutated input
        """
        if strategy is None:
            strategy = random.choice(self.strategies)

        # Create a copy to mutate
        mutated = copy.deepcopy(input_data)

        if strategy == MutationStrategy.RANDOM:
            mutated = self._random_mutation(mutated)
        elif strategy == MutationStrategy.BOUNDARY:
            mutated = self._boundary_mutation(mutated)
        elif strategy == MutationStrategy.ARITHMETIC:
            mutated = self._arithmetic_mutation(mutated)
        elif strategy == MutationStrategy.DICTIONARY:
            mutated = self._dictionary_mutation(mutated)
        elif strategy == MutationStrategy.SPLICING:
            mutated = self._splicing_mutation(mutated)
        elif strategy == MutationStrategy.CROSSOVER:
            mutated = self._crossover_mutation(mutated, input_data)
        else:
            # Default to random
            mutated = self._random_mutation(mutated)

        self._mutation_count += 1
        return mutated

    def _random_mutation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply random mutation"""
        if not input_data:
            return input_data

        # Pick a random key to mutate
        key = random.choice(list(input_data.keys()))
        value = input_data[key]

        # Mutate based on type
        if isinstance(value, int):
            if random.random() < 0.5:
                input_data[key] = random.randint(0, value * 2)
            else:
                input_data[key] = value + random.randint(-100, 100)
        elif isinstance(value, float):
            input_data[key] = value * random.uniform(0.5, 2.0)
        elif isinstance(value, str):
            # Random string mutation
            mutations = [
                self._insert_random_chars,
                self._delete_random_chars,
                self._replace_random_chars,
                self._duplicate_substring,
            ]
            mut_func = random.choice(mutations)
            input_data[key] = mut_func(value)
        elif isinstance(value, list):
            if value:
                if random.random() < 0.5:
                    # Modify random element
                    idx = random.randint(0, len(value) - 1)
                    if isinstance(value[idx], (int, float)):
                        value[idx] = random.randint(-1000, 1000)
                else:
                    # Add/remove element
                    if random.random() < 0.5 and len(value) < 100:
                        value.append(random.randint(0, 100))
                    elif value:
                        value.pop(random.randint(0, len(value) - 1))

        return input_data

    def _boundary_mutation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply boundary-focused mutation"""
        boundary_values = {
            "int": [0, 1, -1, 2147483647, -2147483648, 2147483647],
            "positive": [1, 2, 65535, 2147483647],
            "negative": [-1, -2, -65535, -2147483648],
        }

        for key, value in input_data.items():
            if isinstance(value, int):
                # Pick a boundary value
                if random.random() < 0.5:
                    input_data[key] = random.choice(boundary_values["int"])
                else:
                    # Use extreme values
                    input_data[key] = random.choice([
                        0, 1, -1, 255, 256, 65535, 65536,
                        2147483647, 2147483648, 999999999
                    ])
            elif isinstance(value, str):
                # String boundaries
                input_data[key] = random.choice([
                    "", " ", "\t", "\n", "\r", "\\", "/",
                    "a" * 10000,  # Very long string
                    "\x00",  # Null byte
                ])

        return input_data

    def _arithmetic_mutation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply arithmetic mutation"""
        for key, value in input_data.items():
            if isinstance(value, (int, float)):
                operations = [
                    lambda v: v + random.randint(-10, 10),
                    lambda v: v - random.randint(-10, 10),
                    lambda v: v * random.choice([2, 3, 5, 7, 11]),
                    lambda v: v // random.choice([2, 3, 5, 7, 11]) if v != 0 else v,
                    lambda v: v ^ random.randint(1, 255),  # XOR
                    lambda v: ~v,  # Bitwise NOT
                ]
                input_data[key] = random.choice(operations)(value)
            elif isinstance(value, list) and value:
                idx = random.randint(0, len(value) - 1)
                if isinstance(value[idx], (int, float)):
                    input_data[key][idx] = random.choice(operations)(value[idx])

        return input_data

    def _dictionary_mutation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply dictionary-based mutation"""
        dictionaries = {
            "metric_type": ["INVALID", "", "\n\t\r", "L" * 1000, "COSINE", "IP", "L2"],
            "operation": ["", "invalid", "INSERT", "delete", "search; DROP TABLE"],
        }

        for key, value in input_data.items():
            if key in dictionaries:
                input_data[key] = random.choice(dictionaries[key])
            elif isinstance(value, str):
                # String dictionary mutations
                interesting_strings = [
                    "", "\n", "\r\n", "\t", "\\", "/", "//", "/*", "*/",
                    "'", "\"", "`", "$", ";", "&", "|", "&&", "||",
                    "<script>", "</script>", "${}", "%{",
                    "{{", "}}", "{{{", "}}}",
                    "../../", "..\\..", "%00", "%u0000",
                ]
                input_data[key] = random.choice(interesting_strings)

        return input_data

    def _splicing_mutation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply splicing mutation"""
        for key, value in input_data.items():
            if isinstance(value, str) and len(value) > 2:
                # Slice the string
                start = random.randint(0, len(value) - 2)
                end = random.randint(start + 1, len(value))

                # Either remove or duplicate
                if random.random() < 0.5:
                    # Remove slice
                    input_data[key] = value[:start] + value[end:]
                else:
                    # Duplicate slice
                    input_data[key] = value[:start] + value[start:end] + value[end:]

        return input_data

    def _crossover_mutation(self, input_data: Dict[str, Any],
                            other_input: Optional[Dict] = None) -> Dict[str, Any]:
        """Apply crossover mutation"""
        if not other_input:
            # For crossover, we need a second input
            # For now, return random mutation
            return self._random_mutation(input_data)

        # Perform crossover: swap random keys
        keys = list(input_data.keys())
        if len(keys) > 1:
            # Swap some values
            num_swaps = random.randint(1, len(keys))
            for _ in range(num_swaps):
                key1, key2 = random.sample(keys, 2)
                input_data[key1], input_data[key2] = input_data[key2], input_data[key1]

        return input_data

    def _insert_random_chars(self, s: str) -> str:
        """Insert random characters into string"""
        if not s:
            return "AAAA"

        pos = random.randint(0, len(s))
        chars = "AAAA" + random.choice(["BBBB", "\x00", "\n", "\r"])
        return s[:pos] + chars + s[pos:]

    def _delete_random_chars(self, s: str) -> str:
        """Delete random characters from string"""
        if len(s) <= 1:
            return s

        start = random.randint(0, len(s) - 1)
        end = min(start + random.randint(1, 5), len(s))
        return s[:start] + s[end:]

    def _replace_random_chars(self, s: str) -> str:
        """Replace random characters"""
        if not s:
            return "AAAA"

        result = list(s)
        for _ in range(random.randint(1, min(5, len(s)))):
            idx = random.randint(0, len(s) - 1)
            result[idx] = random.choice(["A", "B", "\x00", "\n", "\t"])

        return "".join(result)

    def _duplicate_substring(self, s: str) -> str:
        """Duplicate a substring"""
        if len(s) < 2:
            return s + s

        start = random.randint(0, len(s) - 2)
        end = random.randint(start + 1, len(s))
        substring = s[start:end]

        return s[:start] + substring + substring + s[start:]

    def get_stats(self) -> Dict:
        """Get mutator statistics"""
        return {
            "total_mutations": self._mutation_count,
            "available_strategies": len(self.strategies),
        }


__all__ = [
    "MutationStrategy",
    "Mutation",
    "Mutator",
]
