"""
Test Corpus Management

Manages test corpus for fuzzing.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
import json
import hashlib
import time


@dataclass
class CorpusEntry:
    """
    An entry in the test corpus
    """
    input_data: Dict[str, Any]
    coverage: Dict[str, Any] = field(default_factory=dict)
    execution_count: int = 0
    last_used: float = field(default_factory=time.time)
    crashes_found: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "input_data": self.input_data,
            "coverage": self.coverage,
            "execution_count": self.execution_count,
            "last_used": self.last_used,
            "crashes_found": self.crashes_found,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'CorpusEntry':
        """Create from dictionary"""
        return cls(**data)


class TestCorpus:
    """
    Test Corpus

    Manages interesting test inputs for fuzzing.
    """

    def __init__(self, corpus_dir: Optional[str] = None,
                 max_size: int = 10000):
        """
        Initialize test corpus

        Args:
            corpus_dir: Directory to save corpus
            max_size: Maximum corpus size
        """
        self.corpus_dir = Path(corpus_dir) if corpus_dir else None
        self.max_size = max_size
        self._entries: List[CorpusEntry] = []

        if self.corpus_dir:
            self._load()

    def add(self, input_data: Dict[str, Any],
            coverage: Optional[Dict] = None) -> None:
        """
        Add input to corpus

        Args:
            input_data: Test input
            coverage: Coverage data
        """
        # Check if already exists
        input_hash = self._hash_input(input_data)
        for entry in self._entries:
            if self._hash_input(entry.input_data) == input_hash:
                # Update existing entry
                entry.execution_count += 1
                entry.last_used = time.time()
                if coverage:
                    entry.coverage.update(coverage)
                return

        # Create new entry
        entry = CorpusEntry(
            input_data=input_data,
            coverage=coverage or {},
            execution_count=1,
        )

        self._entries.append(entry)

        # Limit size
        if len(self._entries) > self.max_size:
            self._entries = self._entries[:self.max_size]

        # Save periodically
        if len(self._entries) % 100 == 0:
            self._save()

    def get_random(self) -> Dict[str, Any]:
        """Get a random input from corpus"""
        if not self._entries:
            return {}

        # Weight by interestingness (execution_count, crashes)
        weights = [e.execution_count + 1 for e in self._entries]
        total = sum(weights)

        import random
        r = random.uniform(0, total)

        cumulative = 0
        for i, entry in enumerate(self._entries):
            cumulative += weights[i]
            if r <= cumulative:
                return entry.input_data

        return self._entries[0].input_data

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all inputs"""
        return [e.input_data for e in self._entries]

    def size(self) -> int:
        """Get corpus size"""
        return len(self._entries)

    def _hash_input(self, input_data: Dict) -> str:
        """Hash input data"""
        normalized = json.dumps(input_data, sort_keys=True)
        return hashlib.md5(normalized.encode()).hexdigest()

    def _load(self) -> None:
        """Load corpus from disk"""
        if not self.corpus_dir:
            return

        corpus_file = self.corpus_dir / "corpus.json"

        if not corpus_file.exists():
            return

        try:
            with open(corpus_file, 'r') as f:
                data = json.load(f)
                self._entries = [CorpusEntry.from_dict(e) for e in data]

        except Exception as e:
            print(f"[WARNING] Failed to load corpus: {e}")

    def _save(self) -> None:
        """Save corpus to disk"""
        if not self.corpus_dir:
            return

        self.corpus_dir.mkdir(parents=True, exist_ok=True)

        corpus_file = self.corpus_dir / "corpus.json"

        try:
            data = [e.to_dict() for e in self._entries]
            with open(corpus_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"[WARNING] Failed to save corpus: {e}")

    def clear(self) -> None:
        """Clear corpus"""
        self._entries.clear()


class CorpusMinimizer:
    """
    Corpus Minimizer

    Minimizes failing test cases to their essential components.
    """

    def __init__(self):
        """Initialize corpus minimizer"""

    def minimize(self, test_input: Dict[str, Any],
                 execute_func: callable) -> Dict[str, Any]:
        """
        Minimize a failing test case

        Args:
            test_input: Original failing input
            execute_func: Function to test if input still fails

        Returns:
            Minimized input
        """
        minimized = test_input.copy()

        for key in list(test_input.keys()):
            # Try removing each key
            test_case = minimized.copy()
            del test_case[key]

            # Check if it still fails
            result = execute_func(test_case)

            if self._is_failing(result):
                # Key is not needed, remove from minimized
                minimized = test_case
            else:
                # Key is needed, keep it
                # Try minimizing the value
                minimized[key] = self._minimize_value(
                    key, minimized[key], execute_func
                )

        return minimized

    def _minimize_value(self, key: str, value: Any,
                         execute_func: callable) -> Any:
        """Minimize a specific value"""
        # For numeric values, try reducing
        if isinstance(value, (int, float)):
            current = value

            # Try halving
            while current != 0:
                test_case = {key: current // 2}

                result = execute_func(test_case)

                if self._is_failing(result):
                    current = current // 2
                else:
                    break

            return current

        # For strings, try shortening
        elif isinstance(value, str) and len(value) > 1:
            # Try removing half
            while len(value) > 1:
                test_value = value[:len(value)//2]

                result = execute_func({key: test_value})

                if self._is_failing(result):
                    value = test_value
                else:
                    break

            return value

        return value

    def _is_failing(self, result: Dict) -> bool:
        """Check if result indicates a failure"""
        return result.get("status") in ["error", "timeout", "crash"]


__all__ = [
    "CorpusEntry",
    "TestCorpus",
    "CorpusMinimizer",
]
