"""
Enhanced Fuzzer

Feedback-driven fuzzing with intelligent mutation.
"""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import random
import time

from fuzzing.mutation import Mutator, MutationStrategy
from fuzzing.feedback import FeedbackAnalyzer
from fuzzing.corpus import TestCorpus


class FuzzerState(Enum):
    """Fuzzer execution states"""
    INIT = "init"
    CALIBRATION = "calibration"
    FUZZING = "fuzzing"
    DONE = "done"


@dataclass
class FuzzerConfig:
    """Configuration for fuzzer"""
    max_iterations: int = 10000
    max_duration: float = 300.0  # 5 minutes
    timeout_per_test: float = 5.0
    calibration_runs: int = 100
    mutation_rate: float = 0.1
    crossover_rate: float = 0.05
    enable_feedback: bool = True
    save_crashes: bool = True
    save_corpus: bool = True
    corpus_dir: Optional[str] = "fuzz_corpus"
    crash_dir: Optional[str] = "fuzz_crashes"

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "max_iterations": self.max_iterations,
            "max_duration": self.max_duration,
            "timeout_per_test": self.timeout_per_test,
            "calibration_runs": self.calibration_runs,
            "mutation_rate": self.mutation_rate,
            "crossover_rate": self.crossover_rate,
            "enable_feedback": self.enable_feedback,
            "save_crashes": self.save_crashes,
            "save_corpus": self.save_corpus,
        }


@dataclass
class FuzzResult:
    """Result of a single fuzz execution"""
    test_input: Dict[str, Any]
    status: str  # success, crash, timeout, error
    execution_time: float
    error: str = ""
    coverage: Dict = field(default_factory=dict)
    crashed: bool = False
    hung: bool = False
    unique_crash: bool = False
    unique_coverage: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "test_input": self.test_input,
            "status": self.status,
            "execution_time": self.execution_time,
            "error": self.error,
            "coverage": self.coverage,
            "crashed": self.crashed,
            "hung": self.hung,
            "unique_crash": self.unique_crash,
            "unique_coverage": self.unique_coverage,
        }


class Fuzzer:
    """
    Enhanced Fuzzer

    Feedback-driven fuzzing with intelligent mutation strategies.
    """

    def __init__(self, config: Optional[FuzzerConfig] = None):
        """
        Initialize fuzzer

        Args:
            config: Fuzzer configuration
        """
        self.config = config or FuzzerConfig()
        self.state = FuzzerState.INIT
        self.iteration = 0
        self.start_time = 0.0

        # Components
        self.mutator = Mutator(config=self.config.__dict__ if config else {})
        self.feedback = FeedbackAnalyzer() if self.config.enable_feedback else None
        self.corpus = TestCorpus(self.config.corpus_dir) if self.config.save_corpus else None

        # Results tracking
        self.crashes: List[FuzzResult] = []
        self.hangs: List[FuzzResult] = []
        self.unique_crashes: set = set()
        self.coverage_history: List[Dict] = []

        # Statistics
        self.total_executions = 0
        self.crash_count = 0
        self.unique_crash_count = 0
        self.hang_count = 0

    def initialize(self, initial_inputs: List[Dict[str, Any]],
                   execute_func: Callable) -> None:
        """
        Initialize fuzzer with seed inputs

        Args:
            initial_inputs: Initial seed inputs
            execute_func: Function to execute a test input
        """
        self.state = FuzzerState.CALIBRATION
        self.start_time = time.time()

        # Calibrate with initial inputs
        for test_input in initial_inputs[:self.config.calibration_runs]:
            result = self._execute_input(test_input, execute_func)
            if self.corpus and result.status == "success":
                self.corpus.add(test_input, result.coverage)

        self.state = FuzzerState.FUZZING

    def run(self, initial_inputs: List[Dict[str, Any]],
            execute_func: Callable) -> List[FuzzResult]:
        """
        Run the fuzzer

        Args:
            initial_inputs: Initial seed inputs
            execute_func: Function to execute a test input

        Returns:
            List of crash results
        """
        self.initialize(initial_inputs, execute_func)

        while self._should_continue():
            # Get next input to test
            test_input = self._generate_input()

            # Execute the test
            result = self._execute_input(test_input, execute_func)

            # Process result
            self._process_result(result)

            self.iteration += 1

        self.state = FuzzerState.DONE
        return self.crashes

    def _should_continue(self) -> bool:
        """Check if fuzzer should continue"""
        # Check iteration limit
        if self.iteration >= self.config.max_iterations:
            return False

        # Check time limit
        if time.time() - self.start_time >= self.config.max_duration:
            return False

        return True

    def _generate_input(self) -> Dict[str, Any]:
        """
        Generate next fuzz input

        Uses feedback to guide mutation if enabled.
        """
        if self.corpus and self.corpus.size() > 0:
            # Get interesting input from corpus
            base_input = self.corpus.get_random()
        else:
            # Use random input
            base_input = self._generate_random_input()

        # Mutate
        if random.random() < self.config.mutation_rate:
            return self.mutator.mutate(base_input)
        else:
            return base_input

    def _generate_random_input(self) -> Dict[str, Any]:
        """Generate a random test input"""
        # Simple random generation - should be customized per target
        return {
            "operation": random.choice(["insert", "search", "delete"]),
            "dimension": random.randint(1, 4096),
            "metric_type": random.choice(["L2", "IP", "COSINE"]),
            "top_k": random.randint(1, 100),
        }

    def _execute_input(self, test_input: Dict[str, Any],
                       execute_func: Callable) -> FuzzResult:
        """
        Execute a fuzz test input

        Args:
            test_input: Input to test
            execute_func: Function to execute the test

        Returns:
            FuzzResult
        """
        self.total_executions += 1

        start_time = time.time()
        status = "success"
        error = ""
        crashed = False
        hung = False
        coverage = {}

        try:
            # Execute with timeout using threading
            import threading
            import queue

            result_queue = queue.Queue()

            def worker():
                try:
                    result = execute_func(test_input)
                    result_queue.put(("success", result))
                except Exception as e:
                    result_queue.put(("error", str(e)))

            thread = threading.Thread(target=worker)
            thread.daemon = True
            thread.start()

            # Wait for completion or timeout
            thread.join(timeout=self.config.timeout_per_test)

            if thread.is_alive():
                # Timeout - thread is still running
                status = "timeout"
                hung = True
            else:
                # Thread completed
                if not result_queue.empty():
                    status, data = result_queue.get()

                    if status == "error":
                        crashed = True
                        error = data
                    elif isinstance(data, dict):
                        status = data.get("status", "success")
                        error = data.get("error", "")
                        coverage = data.get("coverage", {})
                    else:
                        status = "success"

        except Exception as e:
            # Unexpected error
            status = "error"
            error = str(e)
            crashed = True

        exec_time = time.time() - start_time

        result = FuzzResult(
            test_input=test_input,
            status=status,
            execution_time=exec_time,
            error=error,
            coverage=coverage,
            crashed=crashed,
            hung=hung,
        )

        return result

    def _process_result(self, result: FuzzResult) -> None:
        """Process a fuzz result"""
        # Track crashes
        if result.crashed:
            self.crash_count += 1
            self.crashes.append(result)

            # Check if unique crash
            crash_hash = hash(str(result.test_input))
            if crash_hash not in self.unique_crashes:
                result.unique_crash = True
                self.unique_crash_count += 1
                self.unique_crashes.add(crash_hash)

        # Track hangs
        if result.hung:
            self.hang_count += 1
            self.hangs.append(result)

        # Add interesting inputs to corpus
        if self.corpus:
            # Check for unique coverage
            if self._is_interesting_coverage(result.coverage):
                result.unique_coverage = True
                self.corpus.add(result.test_input, result.coverage)

        # Track coverage over time
        self.coverage_history.append({
            "iteration": self.iteration,
            "timestamp": time.time(),
            "coverage": result.coverage,
        })

    def _is_interesting_coverage(self, coverage: Dict) -> bool:
        """Check if coverage is interesting (new paths covered)"""
        if not self.coverage_history:
            return True

        # Simple heuristic: check if coverage increased
        # Real implementation would track edge coverage
        return coverage.get("total", 0) > 0

    def get_stats(self) -> Dict:
        """Get fuzzer statistics"""
        duration = time.time() - self.start_time if self.start_time > 0 else 0

        return {
            "state": self.state.value,
            "iteration": self.iteration,
            "duration": duration,
            "total_executions": self.total_executions,
            "crash_count": self.crash_count,
            "unique_crash_count": self.unique_crash_count,
            "hang_count": self.hang_count,
            "executions_per_second": self.total_executions / duration if duration > 0 else 0,
            "corpus_size": self.corpus.size() if self.corpus else 0,
        }


__all__ = [
    "FuzzerState",
    "FuzzerConfig",
    "FuzzResult",
    "Fuzzer",
]
