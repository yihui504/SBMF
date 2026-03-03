"""
Tests for M3: Enhanced Fuzzing
"""
import pytest
import tempfile
import time
from pathlib import Path

from fuzzing.fuzzer import Fuzzer, FuzzerConfig, FuzzResult, FuzzerState
from fuzzing.mutation import Mutator, MutationStrategy
from fuzzing.feedback import FeedbackAnalyzer, CoverageData
from fuzzing.corpus import TestCorpus as FuzzCorpus, CorpusMinimizer
from fuzzing.agent import FuzzingAgent, FuzzingSession


# ================================================================
# Mutator Tests
# ================================================================

class TestMutator:
    """Test mutator"""

    def test_initialization(self):
        """Test mutator initialization"""
        mutator = Mutator()

        stats = mutator.get_stats()
        assert stats["total_mutations"] == 0

    def test_random_mutation(self):
        """Test random mutation"""
        mutator = Mutator()

        input_data = {"dimension": 512, "metric_type": "L2", "top_k": 10}
        mutated = mutator.mutate(input_data, MutationStrategy.RANDOM)

        assert mutated is not input_data
        assert "dimension" in mutated

    def test_boundary_mutation(self):
        """Test boundary mutation"""
        mutator = Mutator()

        input_data = {"dimension": 512, "metric_type": "L2"}
        mutated = mutator.mutate(input_data, MutationStrategy.BOUNDARY)

        # Should have extreme values
        assert "dimension" in mutated

    def test_arithmetic_mutation(self):
        """Test arithmetic mutation"""
        mutator = Mutator()

        input_data = {"dimension": 512, "top_k": 10}
        mutated = mutator.mutate(input_data, MutationStrategy.ARITHMETIC)

        assert "dimension" in mutated

    def test_string_mutation(self):
        """Test string mutation"""
        mutator = Mutator()

        input_data = {"collection": "test_collection"}
        mutated = mutator.mutate(input_data, MutationStrategy.RANDOM)

        assert "collection" in mutated


# ================================================================
# Fuzzer Tests
# ================================================================

class TestFuzzer:
    """Test fuzzer"""

    def test_initialization(self):
        """Test fuzzer initialization"""
        config = FuzzerConfig(max_iterations=10)
        fuzzer = Fuzzer(config)

        assert fuzzer.state == FuzzerState.INIT

    def test_generate_random_input(self):
        """Test random input generation"""
        fuzzer = Fuzzer()

        input_data = fuzzer._generate_random_input()

        assert "operation" in input_data
        assert "dimension" in input_data

    def test_calculate_stats(self):
        """Test statistics calculation"""
        fuzzer = Fuzzer()

        stats = fuzzer.get_stats()

        assert "total_executions" in stats
        assert stats["total_executions"] == 0

    def test_execute_input_success(self):
        """Test executing input that succeeds"""
        fuzzer = Fuzzer(FuzzerConfig(timeout_per_test=1.0))

        def execute_func(test_input):
            return {"status": "success", "coverage": {}}

        result = fuzzer._execute_input({"dimension": 512}, execute_func)

        assert result.status == "success"
        assert not result.crashed

    def test_execute_input_crash(self):
        """Test executing input that crashes"""
        fuzzer = Fuzzer(FuzzerConfig(timeout_per_test=1.0))

        def execute_func(test_input):
            raise ValueError("Test crash")

        result = fuzzer._execute_input({"dimension": 512}, execute_func)

        assert result.status == "error"
        assert result.crashed

    def test_execute_input_timeout(self):
        """Test executing input that times out"""
        fuzzer = Fuzzer(FuzzerConfig(timeout_per_test=0.1))

        def execute_func(test_input):
            time.sleep(1)  # Sleep longer than timeout
            return {"status": "success"}

        result = fuzzer._execute_input({"dimension": 512}, execute_func)

        assert result.status == "timeout"
        assert result.hung

    def test_should_continue(self):
        """Test continuation logic"""
        fuzzer = Fuzzer(FuzzerConfig(max_iterations=5))

        fuzzer.start_time = time.time()

        # Should continue
        assert fuzzer._should_continue()

        # Increment past limit
        fuzzer.iteration = 10

        # Should not continue
        assert not fuzzer._should_continue()


# ================================================================
# Feedback Analyzer Tests
# ================================================================

class TestFeedbackAnalyzer:
    """Test feedback analyzer"""

    def test_initialization(self):
        """Test analyzer initialization"""
        analyzer = FeedbackAnalyzer()

        stats = analyzer.get_stats()
        assert stats["interesting_inputs"] == 0

    def test_analyze_crash(self):
        """Test analyzing crash result"""
        analyzer = FeedbackAnalyzer()

        test_input = {"dimension": 99999}
        result = {
            "crashed": True,
            "error": "Dimension error"
        }

        feedback = analyzer.analyze_result(test_input, result)

        assert feedback["interesting"]
        assert feedback["priority"] == "critical"

    def test_analyze_timeout(self):
        """Test analyzing timeout result"""
        analyzer = FeedbackAnalyzer()

        test_input = {"dimension": 512}
        result = {"hung": True, "status": "timeout"}

        feedback = analyzer.analyze_result(test_input, result)

        assert feedback["interesting"]

    def test_analyze_success(self):
        """Test analyzing success result"""
        analyzer = FeedbackAnalyzer()

        test_input = {"dimension": 512}
        result = {"status": "success"}

        feedback = analyzer.analyze_result(test_input, result)

        # Success without new coverage is not interesting
        assert not feedback["interesting"]


# ================================================================
# Corpus Tests
# ================================================================

class TestCorpus:
    """Test corpus management"""

    def test_initialization(self):
        """Test corpus initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            corpus = FuzzCorpus(str(Path(tmpdir) / "corpus"))

            assert corpus.size() == 0

    def test_add_entry(self):
        """Test adding entries"""
        with tempfile.TemporaryDirectory() as tmpdir:
            corpus = FuzzCorpus(str(Path(tmpdir) / "corpus"))

            corpus.add({"dimension": 512}, {"total": 100})

            assert corpus.size() == 1

    def test_get_random(self):
        """Test getting random entry"""
        with tempfile.TemporaryDirectory() as tmpdir:
            corpus = FuzzCorpus(str(Path(tmpdir) / "corpus"))

            corpus.add({"dimension": 512}, {})

            result = corpus.get_random()

            assert result is not None


# ================================================================
# Corpus Minimizer Tests
# ================================================================

class TestCorpusMinimizer:
    """Test corpus minimizer"""

    def test_minimize(self):
        """Test test case minimization"""
        minimizer = CorpusMinimizer()

        original = {
            "dimension": 99999,
            "metric_type": "INVALID",
            "top_k": 999,
            "collection": "test"
        }

        def execute_func(test_input):
            # Simplified: dimension > 1000 causes error
            if test_input.get("dimension", 0) > 1000:
                return {"status": "error"}
            return {"status": "success"}

        minimized = minimizer.minimize(original, execute_func)

        # Should be minimized (may remove extra keys)
        assert "dimension" in minimized  # Core bug trigger should remain

    def test_preserve_essential(self):
        """Test that essential values are preserved"""
        minimizer = CorpusMinimizer()

        # Input with bug: dimension > 32768
        original = {"dimension": 99999, "metric_type": "L2"}

        def execute_func(test_input):
            if test_input.get("dimension", 0) > 32768:
                return {"status": "error"}
            return {"status": "success"}

        minimized = minimizer.minimize(original, execute_func)

        # Essential bug trigger should be preserved
        assert minimized["dimension"] > 32768 or minimized.get("dimension", 0) > 32768


# ================================================================
# Fuzzing Agent Tests
# ================================================================

class TestFuzzingAgent:
    """Test fuzzing agent"""

    def test_initialization(self):
        """Test agent initialization"""
        agent = FuzzingAgent()

        assert agent.fuzzer is not None
        assert agent.mutator is not None

    def test_fuzz_session(self):
        """Test fuzzing session"""
        agent = FuzzingAgent(FuzzerConfig(max_iterations=50, max_duration=5.0))

        initial_inputs = [
            {"dimension": 512, "metric_type": "L2"},
            {"dimension": 1024, "metric_type": "IP"},
        ]

        def execute_func(test_input):
            if test_input.get("dimension", 0) > 50000:
                return {"status": "error", "error": "Too large"}
            return {"status": "success", "coverage": {}}

        session = agent.fuzz(initial_inputs, execute_func)

        assert session.session_id is not None
        assert session.total_iterations >= 0
        assert session.total_executions > 0

    def test_minimize_crash(self):
        """Test crash minimization"""
        agent = FuzzingAgent()

        crash_input = {
            "dimension": 99999,
            "metric_type": "INVALID",
            "top_k": 999,
        }

        def execute_func(test_input):
            if test_input.get("dimension", 0) > 32768:
                return {"status": "error"}
            return {"status": "success"}

        minimized = agent.minimize_crash(crash_input, execute_func)

        # Should be minimized
        assert "dimension" in minimized

    def test_get_stats(self):
        """Test getting statistics"""
        agent = FuzzingAgent()

        stats = agent.get_stats()

        assert "agent_stats" in stats
        assert "fuzzer_stats" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
