"""
Race Condition Detector

Detects potential race conditions in concurrent operations.
"""
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict

from concurrency.scenario_generator import (
    ConcurrentScenario, ConcurrentOperation, OperationType, ConflictType
)


class RaceType(Enum):
    """Types of race conditions"""
    DATA_RACE = "data_race"              # Unsynchronized access to shared data
    CHECK_THEN_ACT = "check_then_act"    # TOCTOU (Time-of-check-time-of-use)
    DEADLOCK = "deadlock"                # Circular wait condition
    LIVELock = "livelock"                # Processes keep running but make no progress
    ATOMICITY_VIOLATION = "atomicity"    # Operation not atomic as expected


@dataclass
class RaceCondition:
    """
    A detected or potential race condition
    """
    race_id: str
    race_type: RaceType
    severity: str  # low, medium, high, critical
    description: str
    involved_operations: List[str]  # op_ids
    resource_id: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    mitigation_suggestion: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "race_id": self.race_id,
            "race_type": self.race_type.value,
            "severity": self.severity,
            "description": self.description,
            "involved_operations": self.involved_operations,
            "resource_id": self.resource_id,
            "evidence": self.evidence,
            "mitigation_suggestion": self.mitigation_suggestion,
        }


@dataclass
class ExecutionTrace:
    """
    Trace of operation execution for race analysis
    """
    op_id: str
    operation_type: OperationType
    resource_id: str
    start_time: float
    end_time: float
    thread_id: int
    success: bool
    error_message: str = ""
    access_pattern: str = ""  # read, write, delete

    def duration(self) -> float:
        """Get operation duration"""
        return self.end_time - self.start_time

    def overlaps_with(self, other: 'ExecutionTrace') -> bool:
        """Check if this operation overlaps in time with another"""
        return not (self.end_time <= other.start_time or self.start_time >= other.end_time)


class RaceConditionDetector:
    """
    Race Condition Detector

    Analyzes execution traces to detect potential race conditions.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize race detector

        Args:
            config: Configuration options
        """
        self.config = config or {}
        self._traces: List[ExecutionTrace] = []
        self._detected_races: List[RaceCondition] = []
        self._race_count = 0

    def record_execution(self, trace: ExecutionTrace) -> None:
        """
        Record an execution trace

        Args:
            trace: Execution trace to record
        """
        self._traces.append(trace)

    def analyze_scenario(self, scenario: ConcurrentScenario,
                         execution_results: List[Dict]) -> List[RaceCondition]:
        """
        Analyze a scenario for race conditions

        Args:
            scenario: The scenario that was executed
            execution_results: Results from executing operations

        Returns:
            List of detected race conditions
        """
        races = []

        # Build traces from results
        traces = self._build_traces(scenario, execution_results)

        # Detect write-write races
        races.extend(self._detect_write_write_races(traces))

        # Detect read-write races
        races.extend(self._detect_read_write_races(traces))

        # Potential deadlock detection
        races.extend(self._detect_potential_deadlocks(traces))

        # Check for atomicity violations
        races.extend(self._detect_atomicity_violations(traces))

        self._detected_races.extend(races)
        return races

    def _build_traces(self, scenario: ConcurrentScenario,
                      results: List[Dict]) -> List[ExecutionTrace]:
        """Build execution traces from scenario and results"""
        traces = []

        for i, (op, result) in enumerate(zip(scenario.operations, results)):
            trace = ExecutionTrace(
                op_id=op.op_id,
                operation_type=op.operation_type,
                resource_id=op.resource_id,
                start_time=result.get("start_time", time.time()),
                end_time=result.get("end_time", time.time()),
                thread_id=result.get("thread_id", i),
                success=result.get("success", True),
                error_message=result.get("error", ""),
                access_pattern=self._get_access_pattern(op.operation_type),
            )
            traces.append(trace)

        return traces

    def _get_access_pattern(self, op_type: OperationType) -> str:
        """Get access pattern for operation type"""
        if op_type in [OperationType.INSERT, OperationType.BATCH_INSERT, OperationType.UPDATE]:
            return "write"
        elif op_type == OperationType.DELETE:
            return "delete"
        else:
            return "read"

    def _detect_write_write_races(self, traces: List[ExecutionTrace]) -> List[RaceCondition]:
        """Detect write-write race conditions"""
        races = []
        write_ops = [t for t in traces if t.access_pattern == "write"]

        # Group by resource
        by_resource = defaultdict(list)
        for trace in write_ops:
            by_resource[trace.resource_id].append(trace)

        # Check for overlapping writes to same resource
        for resource, resource_traces in by_resource.items():
            for i, t1 in enumerate(resource_traces):
                for t2 in resource_traces[i+1:]:
                    if t1.overlaps_with(t2):
                        # Potential write-write race
                        race = RaceCondition(
                            race_id=self._generate_race_id(),
                            race_type=RaceType.DATA_RACE,
                            severity="medium",
                            description=f"Concurrent writes to {resource}",
                            involved_operations=[t1.op_id, t2.op_id],
                            resource_id=resource,
                            evidence={
                                "overlap_duration": min(t1.end_time, t2.end_time) -
                                                   max(t1.start_time, t2.start_time),
                                "operation_times": {
                                    t1.op_id: (t1.start_time, t1.end_time),
                                    t2.op_id: (t2.start_time, t2.end_time),
                                }
                            },
                            mitigation_suggestion="Use atomic operations or proper locking"
                        )
                        races.append(race)

        return races

    def _detect_read_write_races(self, traces: List[ExecutionTrace]) -> List[RaceCondition]:
        """Detect read-write race conditions"""
        races = []

        # Group by resource
        by_resource = defaultdict(list)
        for trace in traces:
            by_resource[trace.resource_id].append(trace)

        # Check for overlapping reads and writes
        for resource, resource_traces in by_resource.items():
            read_ops = [t for t in resource_traces if t.access_pattern == "read"]
            write_ops = [t for t in resource_traces if t.access_pattern in ["write", "delete"]]

            for read_op in read_ops:
                for write_op in write_ops:
                    if read_op.overlaps_with(write_op):
                        race = RaceCondition(
                            race_id=self._generate_race_id(),
                            race_type=RaceType.DATA_RACE,
                            severity="low",
                            description=f"Read during write to {resource}",
                            involved_operations=[read_op.op_id, write_op.op_id],
                            resource_id=resource,
                            evidence={
                                "read_time": (read_op.start_time, read_op.end_time),
                                "write_time": (write_op.start_time, write_op.end_time),
                            },
                            mitigation_suggestion="Use read locks or versioning"
                        )
                        races.append(race)

        return races

    def _detect_potential_deadlocks(self, traces: List[ExecutionTrace]) -> List[RaceCondition]:
        """Detect potential deadlocks"""
        races = []

        # Look for operations that took unusually long
        current_time = time.time()
        for trace in traces:
            duration = trace.duration()

            # Very slow operations might indicate deadlock
            if duration > 30.0:  # 30 seconds
                race = RaceCondition(
                    race_id=self._generate_race_id(),
                    race_type=RaceType.DEADLOCK,
                    severity="high",
                    description=f"Possible deadlock: {trace.op_id} took {duration:.1f}s",
                    involved_operations=[trace.op_id],
                    resource_id=trace.resource_id,
                    evidence={"duration": duration},
                    mitigation_suggestion="Check for circular wait conditions and lock ordering"
                )
                races.append(race)

            # Operations that haven't finished
            if trace.end_time == 0 or current_time - trace.start_time > 60.0:
                if not trace.success:
                    race = RaceCondition(
                        race_id=self._generate_race_id(),
                        race_type=RaceType.LIVELock,
                        severity="critical",
                        description=f"Operation {trace.op_id} appears stuck",
                        involved_operations=[trace.op_id],
                        resource_id=trace.resource_id,
                        evidence={"stalled_for": current_time - trace.start_time},
                        mitigation_suggestion="Verify lock timeout and retry mechanisms"
                    )
                    races.append(race)

        return races

    def _detect_atomicity_violations(self, traces: List[ExecutionTrace]) -> List[RaceCondition]:
        """Detect atomicity violations"""
        races = []

        # Check for check-then-act patterns
        # (This is simplified - real detection would require more analysis)
        for trace in traces:
            if not trace.success and "conflict" in trace.error_message.lower():
                race = RaceCondition(
                    race_id=self._generate_race_id(),
                    race_type=RaceType.ATOMICITY_VIOLATION,
                    severity="medium",
                    description=f"Atomicity violation: {trace.error_message}",
                    involved_operations=[trace.op_id],
                    resource_id=trace.resource_id,
                    evidence={"error": trace.error_message},
                    mitigation_suggestion="Use atomic operations or proper transaction isolation"
                )
                races.append(race)

        return races

    def get_detected_races(self) -> List[RaceCondition]:
        """Get all detected race conditions"""
        return self._detected_races

    def get_races_by_severity(self, severity: str) -> List[RaceCondition]:
        """Get races by severity level"""
        return [r for r in self._detected_races if r.severity == severity]

    def get_races_by_resource(self, resource_id: str) -> List[RaceCondition]:
        """Get races for a specific resource"""
        return [r for r in self._detected_races if r.resource_id == resource_id]

    def clear(self) -> None:
        """Clear all detection data"""
        self._traces.clear()
        self._detected_races.clear()

    def get_stats(self) -> Dict:
        """Get detector statistics"""
        severity_counts = defaultdict(int)
        for race in self._detected_races:
            severity_counts[race.severity] += 1

        return {
            "total_traces": len(self._traces),
            "total_races_detected": len(self._detected_races),
            "by_severity": dict(severity_counts),
            "by_type": {
                rt.value: len([r for r in self._detected_races if r.race_type == rt])
                for rt in RaceType
            }
        }

    def _generate_race_id(self) -> str:
        """Generate a unique race ID"""
        self._race_count += 1
        return f"RACE_{self._race_count:04d}"


__all__ = [
    "RaceType",
    "RaceCondition",
    "ExecutionTrace",
    "RaceConditionDetector",
]
