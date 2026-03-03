"""
Concurrent Scenario Generator

Generates test scenarios for concurrent operations.
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random


class OperationType(Enum):
    """Types of operations for concurrent testing"""
    INSERT = "insert"
    SEARCH = "search"
    DELETE = "delete"
    UPDATE = "update"
    BATCH_INSERT = "batch_insert"


class ConflictType(Enum):
    """Types of conflicts to test"""
    WRITE_WRITE = "write_write"           # Two writes to same resource
    READ_WRITE = "read_write"             # Read during write
    DELETE_READ = "delete_read"           # Delete during read
    TRANSACTION_CONFLICT = "transaction"  # Transaction isolation issues
    RESOURCE_EXHAUSTION = "exhaustion"    # Too many concurrent operations


@dataclass
class ConcurrentOperation:
    """
    An operation in a concurrent scenario

    Represents a single operation that will run concurrently.
    """
    op_id: str
    operation_type: OperationType
    resource_id: str  # Collection, table, or resource name
    parameters: Dict[str, Any] = field(default_factory=dict)
    delay_ms: int = 0  # Delay before execution
    thread_id: Optional[int] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "op_id": self.op_id,
            "operation_type": self.operation_type.value,
            "resource_id": self.resource_id,
            "parameters": self.parameters,
            "delay_ms": self.delay_ms,
            "thread_id": self.thread_id,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ConcurrentOperation':
        """Create from dictionary"""
        data["operation_type"] = OperationType(data["operation_type"])
        return cls(**data)


@dataclass
class ConcurrentScenario:
    """
    A concurrent testing scenario

    Defines multiple operations that should run concurrently.
    """
    scenario_id: str
    name: str
    description: str
    operations: List[ConcurrentOperation]
    conflict_type: Optional[ConflictType] = None
    expected_behavior: str = "success"  # success, error, timeout, deadlock
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "operations": [op.to_dict() for op in self.operations],
            "conflict_type": self.conflict_type.value if self.conflict_type else None,
            "expected_behavior": self.expected_behavior,
            "metadata": self.metadata,
        }


class ConcurrentScenarioGenerator:
    """
    Concurrent Scenario Generator

    Generates test scenarios for concurrent operations to detect
    race conditions, deadlocks, and other concurrency issues.
    """

    def __init__(self, resources: List[str],
                 config: Optional[Dict] = None):
        """
        Initialize scenario generator

        Args:
            resources: List of resource names (collections, tables, etc.)
            config: Configuration options
                - max_concurrent: Maximum concurrent operations (default: 10)
                - include_delay: Add random delays (default: True)
        """
        self.resources = resources
        self.config = config or {}
        self.max_concurrent = config.get("max_concurrent", 10) if config else 10
        self.include_delay = config.get("include_delay", True) if config else True
        self._scenario_count = 0

    def generate_write_write_conflict(self, count: int = 5) -> List[ConcurrentScenario]:
        """
        Generate write-write conflict scenarios

        Multiple threads writing to the same resource.

        Args:
            count: Number of scenarios to generate

        Returns:
            List of concurrent scenarios
        """
        scenarios = []

        for _ in range(count):
            resource = random.choice(self.resources)

            operations = []
            num_writes = random.randint(2, min(self.max_concurrent, 5))

            for i in range(num_writes):
                op = ConcurrentOperation(
                    op_id=f"write_{i}",
                    operation_type=OperationType.INSERT,
                    resource_id=resource,
                    parameters={
                        "dimension": random.randint(64, 512),
                        "metric_type": random.choice(["L2", "IP", "COSINE"]),
                    },
                    delay_ms=random.randint(0, 10) if self.include_delay else 0,
                )
                operations.append(op)

            scenario = ConcurrentScenario(
                scenario_id=self._generate_scenario_id(),
                name=f"Write-Write Conflict on {resource}",
                description=f"Concurrent INSERT operations to {resource}",
                operations=operations,
                conflict_type=ConflictType.WRITE_WRITE,
                expected_behavior="success",  # Should handle gracefully
            )
            scenarios.append(scenario)

        return scenarios

    def generate_read_write_conflict(self, count: int = 5) -> List[ConcurrentScenario]:
        """
        Generate read-write conflict scenarios

        Reads happening during writes to test isolation.

        Args:
            count: Number of scenarios to generate

        Returns:
            List of concurrent scenarios
        """
        scenarios = []

        for _ in range(count):
            resource = random.choice(self.resources)

            operations = []
            num_ops = random.randint(3, min(self.max_concurrent, 6))

            # Mix of reads and writes
            for i in range(num_ops):
                is_write = i % 2 == 0

                op = ConcurrentOperation(
                    op_id=f"op_{i}",
                    operation_type=OperationType.INSERT if is_write else OperationType.SEARCH,
                    resource_id=resource,
                    parameters={
                        "dimension": random.randint(64, 512),
                        "top_k": random.randint(1, 100),
                    },
                    delay_ms=random.randint(0, 10) if self.include_delay else 0,
                )
                operations.append(op)

            scenario = ConcurrentScenario(
                scenario_id=self._generate_scenario_id(),
                name=f"Read-Write Conflict on {resource}",
                description=f"Concurrent SEARCH and INSERT operations to {resource}",
                operations=operations,
                conflict_type=ConflictType.READ_WRITE,
                expected_behavior="success",
            )
            scenarios.append(scenario)

        return scenarios

    def generate_delete_during_read(self, count: int = 3) -> List[ConcurrentScenario]:
        """
        Generate delete-during-read scenarios

        Tests behavior when resources are deleted during reads.

        Args:
            count: Number of scenarios to generate

        Returns:
            List of concurrent scenarios
        """
        scenarios = []

        for _ in range(count):
            resource = random.choice(self.resources)

            operations = [
                ConcurrentOperation(
                    op_id="read_0",
                    operation_type=OperationType.SEARCH,
                    resource_id=resource,
                    parameters={"top_k": 10},
                    delay_ms=5,  # Delay read
                ),
                ConcurrentOperation(
                    op_id="delete_1",
                    operation_type=OperationType.DELETE,
                    resource_id=resource,
                    parameters={"ids": [1, 2, 3]},
                    delay_ms=0,  # Delete happens during read
                ),
            ]

            scenario = ConcurrentScenario(
                scenario_id=self._generate_scenario_id(),
                name=f"Delete During Read on {resource}",
                description=f"DELETE operation during SEARCH on {resource}",
                operations=operations,
                conflict_type=ConflictType.DELETE_READ,
                expected_behavior="success",  # Should handle gracefully or return error
            )
            scenarios.append(scenario)

        return scenarios

    def generate_resource_exhaustion(self, count: int = 3) -> List[ConcurrentScenario]:
        """
        Generate resource exhaustion scenarios

        Tests behavior under high concurrent load.

        Args:
            count: Number of scenarios to generate

        Returns:
            List of concurrent scenarios
        """
        scenarios = []

        for _ in range(count):
            resource = random.choice(self.resources)

            operations = []
            num_ops = self.max_concurrent + random.randint(1, 5)  # Over capacity

            for i in range(num_ops):
                op = ConcurrentOperation(
                    op_id=f"op_{i}",
                    operation_type=random.choice([
                        OperationType.INSERT,
                        OperationType.SEARCH,
                        OperationType.BATCH_INSERT,
                    ]),
                    resource_id=resource,
                    parameters={
                        "dimension": random.randint(64, 512),
                        "batch_size": random.randint(10, 100) if random.random() > 0.7 else 1,
                    },
                    delay_ms=random.randint(0, 5) if self.include_delay else 0,
                )
                operations.append(op)

            scenario = ConcurrentScenario(
                scenario_id=self._generate_scenario_id(),
                name=f"Resource Exhaustion on {resource}",
                description=f"High load ({num_ops} concurrent ops) on {resource}",
                operations=operations,
                conflict_type=ConflictType.RESOURCE_EXHAUSTION,
                expected_behavior="success",  # Should queue or reject gracefully
            )
            scenarios.append(scenario)

        return scenarios

    def generate_batch_operations(self, count: int = 3) -> List[ConcurrentScenario]:
        """
        Generate batch operation scenarios

        Tests concurrent batch operations.

        Args:
            count: Number of scenarios to generate

        Returns:
            List of concurrent scenarios
        """
        scenarios = []

        for _ in range(count):
            resource = random.choice(self.resources)

            operations = []
            num_batches = random.randint(2, 4)

            for i in range(num_batches):
                op = ConcurrentOperation(
                    op_id=f"batch_{i}",
                    operation_type=OperationType.BATCH_INSERT,
                    resource_id=resource,
                    parameters={
                        "batch_size": random.randint(50, 200),
                        "dimension": random.randint(64, 512),
                    },
                    delay_ms=random.randint(0, 10) if self.include_delay else 0,
                )
                operations.append(op)

            scenario = ConcurrentScenario(
                scenario_id=self._generate_scenario_id(),
                name=f"Concurrent Batch Operations on {resource}",
                description=f"Multiple batch inserts to {resource}",
                operations=operations,
                conflict_type=ConflictType.WRITE_WRITE,
                expected_behavior="success",
            )
            scenarios.append(scenario)

        return scenarios

    def generate_all_scenarios(self) -> List[ConcurrentScenario]:
        """
        Generate all types of concurrent scenarios

        Returns:
            List of all generated scenarios
        """
        all_scenarios = []

        all_scenarios.extend(self.generate_write_write_conflict(3))
        all_scenarios.extend(self.generate_read_write_conflict(3))
        all_scenarios.extend(self.generate_delete_during_read(2))
        all_scenarios.extend(self.generate_resource_exhaustion(2))
        all_scenarios.extend(self.generate_batch_operations(2))

        return all_scenarios

    def _generate_scenario_id(self) -> str:
        """Generate a unique scenario ID"""
        self._scenario_count += 1
        return f"SCENARIO_{self._scenario_count:04d}"

    def get_stats(self) -> Dict:
        """Get generator statistics"""
        return {
            "total_scenarios_generated": self._scenario_count,
            "resources": len(self.resources),
            "max_concurrent": self.max_concurrent,
        }


__all__ = [
    "OperationType",
    "ConflictType",
    "ConcurrentOperation",
    "ConcurrentScenario",
    "ConcurrentScenarioGenerator",
]
