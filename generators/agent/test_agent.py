"""
Test Generation Agent

Intelligent agent for adaptive test generation with learning.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import random

from agent.runtime import AgentRuntime, AgentConfig
from agent.memory import AgentMemory, MemoryType
from generators.base import (
    BaseTestGenerator, TestCase, GenerationResult, Slot, GenerationStrategy
)
from generators.random_generator import RandomTestGenerator
from generators.boundary_generator import BoundaryValueGenerator
from generators.combinatorial import PairwiseGenerator
from generators.agent.cache import TestGenerationCache
from generators.agent.strategy_learner import StrategyLearner


@dataclass
class AgentGenerationStrategy:
    """A test generation strategy for the agent"""
    name: str
    generator: BaseTestGenerator
    weight: float = 1.0  # For weighted selection
    effective_for: List[str] = None  # Operations this is effective for

    def __post_init__(self):
        if self.effective_for is None:
            self.effective_for = []


class TestGenerationAgent:
    """
    Test Generation Agent

    Intelligent agent that:
    - Selects appropriate generation strategies
    - Learns from past results
    - Caches generated tests for performance
    - Adapts strategy based on effectiveness
    """

    def __init__(self, slots: List[Slot], operations: List[str],
                 config: Optional[Dict] = None):
        """
        Initialize test generation agent

        Args:
            slots: List of input parameter slots
            operations: List of operations to generate tests for
            config: Configuration options
                - enable_cache: Enable caching
                - enable_learning: Enable learning from bugs
                - cache_dir: Cache directory
                - learning_storage: Learning data storage path
        """
        self.slots = slots
        self.operations = operations
        self.config = config or {}

        # Initialize agent runtime
        agent_config = AgentConfig(
            agent_id="test_generation_agent",
            enable_monitoring=True,
            enable_memory=True
        )
        self.runtime = AgentRuntime(agent_config)

        # Initialize strategies
        self._strategies: List[AgentGenerationStrategy] = []
        self._initialize_strategies()

        # Initialize cache
        enable_cache = self.config.get("enable_cache", True)
        if enable_cache:
            cache_dir = self.config.get("cache_dir")
            self.cache = TestGenerationCache(
                cache_dir=cache_dir,
                enable_persistence=True
            )
        else:
            self.cache = None

        # Initialize learner
        enable_learning = self.config.get("enable_learning", True)
        if enable_learning:
            learning_storage = self.config.get("learning_storage")
            self.learner = StrategyLearner(storage_path=learning_storage)
        else:
            self.learner = None

        # Strategy effectiveness tracking
        self._strategy_scores: Dict[str, float] = {}

    def _initialize_strategies(self) -> None:
        """Initialize available generation strategies"""
        # Random generator
        random_gen = RandomTestGenerator(
            self.slots, self.operations,
            config={"seed": None, "invalid_ratio": 0.1}
        )
        self._strategies.append(AgentGenerationStrategy(
            name="random",
            generator=random_gen,
            weight=1.0,
            effective_for=[]
        ))

        # Boundary value generator
        boundary_gen = BoundaryValueGenerator(
            self.slots, self.operations,
            config={"include_zero": True, "epsilon": 1}
        )
        self._strategies.append(AgentGenerationStrategy(
            name="boundary",
            generator=boundary_gen,
            weight=1.5,  # Higher weight - boundaries often find bugs
            effective_for=["insert", "search", "delete"]
        ))

        # Pairwise generator
        pairwise_gen = PairwiseGenerator(
            self.slots, self.operations,
            config={"values_per_slot": 3}
        )
        self._strategies.append(AgentGenerationStrategy(
            name="pairwise",
            generator=pairwise_gen,
            weight=1.2,
            effective_for=[]
        ))

    def generate(self, count: int, operation: Optional[str] = None,
                 strategy: Optional[str] = None,
                 adaptive: bool = True) -> GenerationResult:
        """
        Generate test cases

        Args:
            count: Number of test cases to generate
            operation: Specific operation to generate for
            strategy: Specific strategy to use (None = auto-select)
            adaptive: Use adaptive strategy selection

        Returns:
            GenerationResult with generated test cases
        """
        self.runtime.start()

        try:
            # Select strategy
            selected_strategy = self._select_strategy(operation, strategy, adaptive)

            # Check cache
            if self.cache:
                cached = self.cache.get(
                    operation or "all",
                    count,
                    selected_strategy.name,
                    self.config
                )
                if cached is not None:
                    from generators.base import GenerationStrategy as BaseGenerationStrategy
                    return GenerationResult(
                        test_cases=cached[:count],
                        strategy=BaseGenerationStrategy.AGENT,
                        generation_time=0.0,
                        total_generated=len(cached),
                        unique_count=len(cached),
                        metadata={"cached": True}
                    )

            # Generate tests
            if self.runtime.monitor:
                self.runtime.monitor.start_operation("test_generation")
            result = selected_strategy.generator.generate(count, operation)
            if self.runtime.monitor:
                self.runtime.monitor.end_operation("test_generation", True)

            # Add learning-based suggestions if available
            if self.learner and operation:
                suggestions = self.learner.get_test_suggestions(operation, count // 2)
                if suggestions:
                    learning_tests = self._generate_from_suggestions(
                        suggestions, operation
                    )
                    result.test_cases.extend(learning_tests)

            # Cache results
            if self.cache:
                self.cache.put(
                    operation or "all",
                    count,
                    selected_strategy.name,
                    result.test_cases,
                    self.config
                )

            # Store in memory
            self.runtime.remember(
                f"generated_{operation or 'all'}_{count}",
                result.to_dict(),
                MemoryType.SHORT_TERM
            )

            return result

        finally:
            self.runtime.stop()

    def _select_strategy(self, operation: Optional[str],
                         specified_strategy: Optional[str],
                         adaptive: bool) -> AgentGenerationStrategy:
        """Select generation strategy"""
        # If strategy specified, use it
        if specified_strategy:
            for s in self._strategies:
                if s.name == specified_strategy:
                    return s
            raise ValueError(f"Unknown strategy: {specified_strategy}")

        if not adaptive:
            # Return default (first strategy)
            return self._strategies[0]

        # Adaptive selection based on effectiveness
        return self._adaptive_strategy_select(operation)

    def _adaptive_strategy_select(self, operation: Optional[str]) -> AgentGenerationStrategy:
        """Select strategy based on effectiveness and learning"""
        # Filter strategies effective for this operation
        if operation:
            effective = [
                s for s in self._strategies
                if not s.effective_for or operation in s.effective_for
            ]
        else:
            effective = self._strategies

        if not effective:
            effective = self._strategies

        # Weighted random selection
        weights = [s.weight for s in effective]
        total = sum(weights)

        if total == 0:
            return effective[0]

        rand = random.uniform(0, total)
        cumulative = 0

        for i, weight in enumerate(weights):
            cumulative += weight
            if rand <= cumulative:
                return effective[i]

        return effective[-1]

    def _generate_from_suggestions(self, suggestions: List[Dict],
                                    operation: str) -> List[TestCase]:
        """Generate tests from learned suggestions"""
        tests = []

        for i, suggestion in enumerate(suggestions):
            # Convert template to concrete values
            slot_values = {}
            for slot_name, category in suggestion["slot_template"].items():
                slot = next((s for s in self.slots if s.name == slot_name), None)
                if slot:
                    slot_values[slot_name] = self._value_from_category(category, slot)

            tests.append(TestCase(
                test_id=f"{operation}_learned_{i:06d}",
                operation=operation,
                slot_values=slot_values,
                metadata={
                    "learned": True,
                    "bugs_found": suggestion["bugs_found"],
                    "confidence": suggestion["confidence"],
                }
            ))

        return tests

    def _value_from_category(self, category: str, slot: Slot) -> Any:
        """Convert value category to concrete value"""
        if category == "null":
            return None
        elif category == "zero":
            return 0 if slot.data_type == "int" else 0.0
        elif category == "one":
            return 1
        elif category == "negative":
            return -1
        elif category == "large_positive":
            return slot.max_value or 10000
        elif category == "positive":
            return 100
        elif category == "empty_string":
            return ""
        elif category == "empty_list":
            return []
        elif category == "single_element_list":
            return [1.0]
        else:
            return slot.default_value

    def record_bug(self, test_case: TestCase, error_type: str,
                   error_message: str) -> None:
        """
        Record a bug found during testing

        Args:
            test_case: Test case that found the bug
            error_type: Type of error
            error_message: Error message
        """
        if self.learner:
            self.learner.record_bug(
                operation=test_case.operation,
                slot_values=test_case.slot_values,
                error_type=error_type,
                error_message=error_message
            )

    def get_effective_patterns(self, operation: Optional[str] = None) -> List[Dict]:
        """
        Get effective bug-finding patterns

        Args:
            operation: Filter by operation

        Returns:
            List of effective patterns
        """
        if not self.learner:
            return []

        patterns = self.learner.get_effective_patterns(operation)

        return [
            {
                "description": p.description,
                "operation": p.operation,
                "bugs_found": p.bugs_found,
                "slot_template": p.slot_template,
            }
            for p in patterns
        ]

    def get_statistics(self) -> Dict:
        """Get agent statistics"""
        stats = {
            "agent_stats": self.runtime.get_stats() if self.runtime else {},
        }

        if self.cache:
            stats["cache_stats"] = self.cache.get_stats()

        if self.learner:
            stats["learner_stats"] = self.learner.get_stats()

        return stats

    def clear_cache(self) -> None:
        """Clear the test generation cache"""
        if self.cache:
            self.cache.clear()

    def clear_learning(self) -> None:
        """Clear learned patterns"""
        if self.learner:
            self.learner.clear()


__all__ = ["TestGenerationAgent", "GenerationStrategy"]
