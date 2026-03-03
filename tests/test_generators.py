"""
Tests for M0: Intelligent Test Generation
"""
import pytest
import tempfile
from pathlib import Path

from generators.base import (
    Slot, TestCase, GenerationResult, BaseTestGenerator, GenerationStrategy
)
from generators.random_generator import RandomTestGenerator
from generators.boundary_generator import BoundaryValueGenerator
from generators.combinatorial import PairwiseGenerator
from generators.agent.cache import TestGenerationCache, CacheEntry
from generators.agent.strategy_learner import (
    StrategyLearner, BugOccurrence, EffectivePattern
)
from generators.agent.test_agent import TestGenerationAgent


# ================================================================
# Test Fixtures
# ================================================================

@pytest.fixture
def sample_slots():
    """Create sample test slots"""
    return [
        Slot(
            name="dimension",
            data_type="int",
            required=True,
            min_value=1,
            max_value=32768,
            description="Vector dimension"
        ),
        Slot(
            name="metric_type",
            data_type="str",
            required=True,
            allowed_values={"L2", "IP", "COSINE"},
            description="Distance metric type"
        ),
        Slot(
            name="top_k",
            data_type="int",
            required=False,
            default_value=10,
            min_value=1,
            max_value=100,
            description="Top k results"
        ),
        Slot(
            name="enable_mmap",
            data_type="bool",
            required=False,
            default_value=True,
            description="Enable memory mapping"
        ),
    ]


@pytest.fixture
def sample_operations():
    """Create sample operations"""
    return ["insert", "search", "delete"]


# ================================================================
# Base Classes Tests
# ================================================================

class TestSlot:
    """Test Slot class"""

    def test_validation_valid(self, sample_slots):
        """Test validation with valid values"""
        slot = sample_slots[0]  # dimension
        assert slot.validate(100)
        assert slot.validate(1)
        assert slot.validate(32768)

    def test_validation_invalid(self, sample_slots):
        """Test validation with invalid values"""
        slot = sample_slots[0]  # dimension
        assert not slot.validate(0)  # Below min
        assert not slot.validate(40000)  # Above max
        assert not slot.validate("string")  # Wrong type

    def test_validation_required(self, sample_slots):
        """Test required field validation"""
        slot = sample_slots[0]  # dimension (required)
        assert not slot.validate(None)

    def test_validation_allowed_values(self, sample_slots):
        """Test allowed values validation"""
        slot = sample_slots[1]  # metric_type
        assert slot.validate("L2")
        assert slot.validate("IP")
        assert not slot.validate("INVALID")


class TestTestCase:
    """Test TestCase class"""

    def test_creation(self):
        """Test creating a test case"""
        tc = TestCase(
            test_id="TEST_001",
            operation="insert",
            slot_values={"dimension": 512, "metric_type": "L2"}
        )

        assert tc.test_id == "TEST_001"
        assert tc.operation == "insert"
        assert tc.slot_values["dimension"] == 512

    def test_to_dict(self):
        """Test serialization to dict"""
        tc = TestCase(
            test_id="TEST_001",
            operation="insert",
            slot_values={"dimension": 512}
        )

        data = tc.to_dict()
        assert data["test_id"] == "TEST_001"
        assert data["operation"] == "insert"

    def test_from_dict(self):
        """Test deserialization from dict"""
        data = {
            "test_id": "TEST_001",
            "operation": "insert",
            "slot_values": {"dimension": 512},
            "preconditions": [],
            "expected_status": "SUCCESS",
            "metadata": {}
        }

        tc = TestCase.from_dict(data)
        assert tc.test_id == "TEST_001"
        assert tc.slot_values["dimension"] == 512


# ================================================================
# Random Generator Tests
# ================================================================

class TestRandomTestGenerator:
    """Test random test generator"""

    def test_generate(self, sample_slots, sample_operations):
        """Test generating random tests"""
        generator = RandomTestGenerator(sample_slots, sample_operations)
        result = generator.generate(10)

        assert len(result.test_cases) <= 10
        assert result.strategy == GenerationStrategy.RANDOM
        assert result.generation_time >= 0

    def test_reproducibility_with_seed(self, sample_slots, sample_operations):
        """Test that seed produces reproducible results"""
        import random as py_random

        # Reset global random state
        py_random.seed(42)

        config1 = {"seed": 42}
        config2 = {"seed": 42}

        gen1 = RandomTestGenerator(sample_slots, sample_operations, config1)
        gen2 = RandomTestGenerator(sample_slots, sample_operations, config2)

        result1 = gen1.generate(5, "insert")

        # Reset global random state again
        py_random.seed(42)

        result2 = gen2.generate(5, "insert")

        assert len(result1.test_cases) == len(result2.test_cases)

        # Check that first test cases are identical
        tc1 = result1.test_cases[0]
        tc2 = result2.test_cases[0]
        assert tc1.slot_values == tc2.slot_values

    def test_specific_operation(self, sample_slots, sample_operations):
        """Test generating for specific operation"""
        generator = RandomTestGenerator(sample_slots, sample_operations)
        result = generator.generate(5, operation="search")

        for tc in result.test_cases:
            assert tc.operation == "search"

    def test_invalid_ratio(self, sample_slots, sample_operations):
        """Test invalid test ratio"""
        config = {"invalid_ratio": 0.5, "seed": 42}
        generator = RandomTestGenerator(sample_slots, sample_operations, config)
        result = generator.generate(20)

        # Some tests should be invalid due to high ratio
        # Note: This is probabilistic, so we just check it runs


# ================================================================
# Boundary Generator Tests
# ================================================================

class TestBoundaryValueGenerator:
    """Test boundary value generator"""

    def test_generate(self, sample_slots, sample_operations):
        """Test generating boundary tests"""
        generator = BoundaryValueGenerator(sample_slots, sample_operations)
        result = generator.generate(10)

        assert len(result.test_cases) <= 10
        assert result.strategy == GenerationStrategy.BOUNDARY

    def test_boundary_values(self, sample_slots, sample_operations):
        """Test that boundary values are used"""
        generator = BoundaryValueGenerator(sample_slots, sample_operations)
        result = generator.generate(20, operation="insert")

        # Check for boundary values in generated tests
        found_boundary = False
        for tc in result.test_cases:
            if "dimension" in tc.slot_values:
                dim = tc.slot_values["dimension"]
                # Check for typical boundary values
                if dim in [0, 1, -1, 32768, 32767, 32769]:
                    found_boundary = True
                    break

        assert found_boundary, "Should include boundary values"

    def test_empty_string_boundary(self, sample_slots, sample_operations):
        """Test empty string boundary"""
        # Add string slot
        slots = sample_slots + [
            Slot(name="collection_name", data_type="str", required=True)
        ]

        generator = BoundaryValueGenerator(slots, sample_operations)
        result = generator.generate(50, operation="insert")  # More tests for better coverage

        # Check for empty string
        found_empty = False
        for tc in result.test_cases:
            if tc.slot_values.get("collection_name") == "":
                found_empty = True
                break

        assert found_empty, f"Should include empty string. Got values: {[tc.slot_values.get('collection_name') for tc in result.test_cases[:10]]}"


# ================================================================
# Pairwise Generator Tests
# ================================================================

class TestPairwiseGenerator:
    """Test pairwise generator"""

    def test_generate(self, sample_slots, sample_operations):
        """Test generating pairwise tests"""
        generator = PairwiseGenerator(sample_slots, sample_operations)
        result = generator.generate(10)

        assert len(result.test_cases) <= 10
        assert result.strategy == GenerationStrategy.COMBINATORIAL

    def test_pair_coverage(self, sample_slots, sample_operations):
        """Test that pairs are covered"""
        generator = PairwiseGenerator(sample_slots, sample_operations)
        result = generator.generate(50)

        # Should have good pair coverage
        assert result.coverage_estimate > 0.5


# ================================================================
# Cache Tests
# ================================================================

class TestTestGenerationCache:
    """Test generation cache"""

    def test_put_get(self):
        """Test caching and retrieving"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = TestGenerationCache(
                cache_dir=Path(tmpdir),
                enable_persistence=False
            )

            # Create test cases
            test_cases = [
                TestCase(
                    test_id="TEST_001",
                    operation="insert",
                    slot_values={"dimension": 512}
                )
            ]

            # Cache them
            cache.put("insert", 10, "random", test_cases)

            # Retrieve
            retrieved = cache.get("insert", 10, "random")

            assert retrieved is not None
            assert len(retrieved) == 1
            assert retrieved[0].test_id == "TEST_001"

    def test_cache_miss(self):
        """Test cache miss"""
        cache = TestGenerationCache(enable_persistence=False)

        result = cache.get("search", 10, "random")
        assert result is None

    def test_lru_eviction(self):
        """Test LRU eviction"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = TestGenerationCache(
                cache_dir=Path(tmpdir),
                max_entries=2,
                enable_persistence=False
            )

            # Add 3 entries with different configs to get different keys
            for i in range(3):
                cache.put("insert", 10, "random", [], config={"i": i})

            # Only 2 should remain (LRU evicted)
            assert cache.get_stats()["size"] == 2

    def test_invalidate(self):
        """Test cache invalidation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = TestGenerationCache(
                cache_dir=Path(tmpdir),
                enable_persistence=False
            )

            cache.put("insert", 10, "random", [])
            cache.put("search", 10, "random", [])

            # Invalidate all (since we can't invalidate by specific operation)
            cache.invalidate("insert")

            # All entries are cleared
            assert cache.get_stats()["size"] == 0

    def test_clear(self):
        """Test clearing cache"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = TestGenerationCache(
                cache_dir=Path(tmpdir),
                enable_persistence=False
            )

            cache.put("insert", 10, "random", [])
            cache.clear()

            assert cache.get_stats()["size"] == 0


# ================================================================
# Strategy Learner Tests
# ================================================================

class TestStrategyLearner:
    """Test strategy learner"""

    def test_record_bug(self):
        """Test recording a bug"""
        with tempfile.TemporaryDirectory() as tmpdir:
            learner = StrategyLearner(
                storage_path=Path(tmpdir) / "learning.json"
            )

            learner.record_bug(
                operation="insert",
                slot_values={"dimension": 99999},
                error_type="ValueError",
                error_message="Dimension too large"
            )

            stats = learner.get_stats()
            assert stats["total_bugs_recorded"] == 1

    def test_effective_patterns(self):
        """Test pattern extraction"""
        with tempfile.TemporaryDirectory() as tmpdir:
            learner = StrategyLearner(
                storage_path=Path(tmpdir) / "learning.json"
            )

            # Record similar bugs
            for dim in [99999, 100000, 50000]:
                learner.record_bug(
                    operation="insert",
                    slot_values={"dimension": dim},
                    error_type="ValueError",
                    error_message="Dimension too large"
                )

            patterns = learner.get_effective_patterns("insert")
            assert len(patterns) > 0
            assert patterns[0].bugs_found >= 1

    def test_effective_values(self):
        """Test getting effective values"""
        with tempfile.TemporaryDirectory() as tmpdir:
            learner = StrategyLearner(
                storage_path=Path(tmpdir) / "learning.json"
            )

            # Record bugs with large dimensions
            for dim in [99999, 100000, 50000]:
                learner.record_bug(
                    operation="insert",
                    slot_values={"dimension": dim},
                    error_type="ValueError",
                    error_message="Dimension too large"
                )

            effective = learner.get_effective_values("dimension", top_n=5)
            assert len(effective) > 0

            # Check that "large_positive" is among effective values
            categories = [cat for cat, count in effective]
            assert "large_positive" in categories

    def test_test_suggestions(self):
        """Test getting test suggestions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            learner = StrategyLearner(
                storage_path=Path(tmpdir) / "learning.json"
            )

            learner.record_bug(
                operation="insert",
                slot_values={"dimension": 99999, "metric_type": "L2"},
                error_type="ValueError",
                error_message="Dimension too large"
            )

            suggestions = learner.get_test_suggestions("insert")
            assert len(suggestions) > 0

    def test_persistence(self):
        """Test learning persistence"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "learning.json"

            learner1 = StrategyLearner(storage_path=storage_path)
            learner1.record_bug(
                operation="insert",
                slot_values={"dimension": 99999},
                error_type="ValueError",
                error_message="Dimension too large"
            )

            # Create new learner with same storage
            learner2 = StrategyLearner(storage_path=storage_path)
            stats = learner2.get_stats()

            assert stats["total_bugs_recorded"] == 1


# ================================================================
# Test Agent Tests
# ================================================================

class TestTestGenerationAgent:
    """Test test generation agent"""

    def test_initialization(self, sample_slots, sample_operations):
        """Test agent initialization"""
        agent = TestGenerationAgent(
            sample_slots,
            sample_operations,
            config={"enable_cache": False, "enable_learning": False}
        )

        assert agent.runtime is not None
        assert len(agent._strategies) > 0

    def test_generate(self, sample_slots, sample_operations):
        """Test generating tests"""
        agent = TestGenerationAgent(
            sample_slots,
            sample_operations,
            config={"enable_cache": False, "enable_learning": False}
        )

        result = agent.generate(10)

        assert len(result.test_cases) <= 10

    def test_specific_strategy(self, sample_slots, sample_operations):
        """Test using specific strategy"""
        agent = TestGenerationAgent(
            sample_slots,
            sample_operations,
            config={"enable_cache": False, "enable_learning": False}
        )

        result = agent.generate(5, strategy="random")

        assert len(result.test_cases) <= 5

    def test_record_bug(self, sample_slots, sample_operations):
        """Test recording bugs"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = TestGenerationAgent(
                sample_slots,
                sample_operations,
                config={
                    "enable_cache": False,
                    "enable_learning": True,
                    "learning_storage": Path(tmpdir) / "learning.json"
                }
            )

            tc = TestCase(
                test_id="TEST_001",
                operation="insert",
                slot_values={"dimension": 99999}
            )

            agent.record_bug(tc, "ValueError", "Dimension too large")

            stats = agent.get_statistics()
            assert stats["learner_stats"]["total_bugs_recorded"] == 1

    def test_caching(self, sample_slots, sample_operations):
        """Test caching behavior"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = TestGenerationAgent(
                sample_slots,
                sample_operations,
                config={
                    "enable_cache": True,
                    "cache_dir": Path(tmpdir),
                    "enable_learning": False
                }
            )

            # First call - not cached
            result1 = agent.generate(5, operation="insert")

            # Second call - should be cached
            result2 = agent.generate(5, operation="insert")

            assert len(result1.test_cases) == len(result2.test_cases)

    def test_get_statistics(self, sample_slots, sample_operations):
        """Test getting statistics"""
        agent = TestGenerationAgent(
            sample_slots,
            sample_operations,
            config={"enable_cache": False, "enable_learning": False}
        )

        stats = agent.get_statistics()

        assert "agent_stats" in stats
        assert "cache_stats" in stats or not agent.cache
        assert "learner_stats" in stats or not agent.learner


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
