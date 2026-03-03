"""
Agent Performance Monitor

Monitors agent performance, identifies bottlenecks, and provides
real-time feedback for optimization.
"""
import time
import threading
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque


@dataclass
class PerformanceMetric:
    """A single performance metric"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionRecord:
    """Record of an agent execution"""
    agent_id: str
    operation: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentMonitor:
    """
    Agent Performance Monitor

    Tracks execution time, resource usage, and performance metrics
    for agents to identify bottlenecks and optimize performance.
    """

    def __init__(self, agent_id: str, max_history: int = 1000):
        """
        Initialize agent monitor

        Args:
            agent_id: Agent to monitor
            max_history: Maximum records to keep
        """
        self.agent_id = agent_id
        self.max_history = max_history

        # Execution history
        self._executions: deque[ExecutionRecord] = deque(maxlen=max_history)
        self._metrics: deque[PerformanceMetric] = deque(maxlen=max_history)

        # Current operation tracking
        self._current_operation: Optional[str] = None
        self._operation_start_time: Optional[float] = None
        self._operation_metadata: Dict = {}

        # Performance thresholds
        self._thresholds = {
            "slow_operation_ms": 1000.0,
            "warning_operation_ms": 500.0,
            "high_memory_usage_mb": 500.0,
        }

        # Thread safety
        self._lock = threading.Lock()

        # Aggregated stats
        self._operation_stats: Dict[str, Dict] = {}

    # ================================================================
    # Execution Tracking
    # ================================================================

    def start_operation(self, operation: str, **metadata) -> None:
        """
        Start tracking an operation

        Args:
            operation: Operation name
            **metadata: Additional metadata
        """
        self._current_operation = operation
        self._operation_start_time = time.time()
        self._operation_metadata = metadata

    def end_operation(self, success: bool = True,
                     error: Optional[str] = None) -> Optional[float]:
        """
        End tracking an operation

        Args:
            success: Whether operation succeeded
            error: Error message if failed

        Returns:
            Operation duration in milliseconds, or None if no operation was tracked
        """
        if self._current_operation is None:
            return None

        end_time = time.time()
        duration_ms = (end_time - self._operation_start_time) * 1000

        record = ExecutionRecord(
            agent_id=self.agent_id,
            operation=self._current_operation,
            start_time=datetime.fromtimestamp(self._operation_start_time),
            end_time=datetime.fromtimestamp(end_time),
            duration_ms=duration_ms,
            success=success,
            error=error,
            metadata=self._operation_metadata.copy()
        )

        with self._lock:
            self._executions.append(record)
            self._update_operation_stats(record)

        self._current_operation = None
        self._operation_start_time = None
        self._operation_metadata = {}

        return duration_ms

    # ================================================================
    # Metrics Recording
    # ================================================================

    def record_metric(self, name: str, value: float, unit: str = "",
                     **metadata) -> None:
        """
        Record a performance metric

        Args:
            name: Metric name
            value: Metric value
            unit: Unit of measurement
            **metadata: Additional metadata
        """
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            metadata=metadata
        )
        self._metrics.append(metric)

    # ================================================================
    # Performance Analysis
    # ================================================================

    def get_average_duration(self, operation: Optional[str] = None) -> Optional[float]:
        """
        Get average execution duration

        Args:
            operation: Specific operation, or all operations

        Returns:
            Average duration in milliseconds
        """
        with self._lock:
            records = list(self._executions)

            if operation:
                records = [r for r in records if r.operation == operation]

            if not records:
                return None

            durations = [r.duration_ms for r in records if r.duration_ms is not None]
            if not durations:
                return None

            return sum(durations) / len(durations)

    def get_percentile_duration(self, percentile: float,
                                operation: Optional[str] = None) -> Optional[float]:
        """
        Get percentile execution duration

        Args:
            percentile: Percentile (0-100)
            operation: Specific operation, or all operations

        Returns:
            Percentile duration in milliseconds
        """
        with self._lock:
            records = list(self._executions)

            if operation:
                records = [r for r in records if r.operation == operation]

            if not records:
                return None

            durations = sorted([r.duration_ms for r in records
                              if r.duration_ms is not None])
            if not durations:
                return None

            index = int(len(durations) * percentile / 100)
            return durations[min(index, len(durations) - 1)]

    def get_slow_operations(self, threshold_ms: Optional[float] = None) -> List[ExecutionRecord]:
        """
        Get slow operations

        Args:
            threshold_ms: Duration threshold, or use configured threshold

        Returns:
            List of slow operation records
        """
        threshold = threshold_ms or self._thresholds["slow_operation_ms"]

        return [r for r in self._executions
                if r.duration_ms and r.duration_ms > threshold]

    def get_error_rate(self, operation: Optional[str] = None) -> Optional[float]:
        """
        Get error rate

        Args:
            operation: Specific operation, or all operations

        Returns:
            Error rate (0-1)
        """
        with self._lock:
            records = list(self._executions)

            if operation:
                records = [r for r in records if r.operation == operation]

            if not records:
                return None

            total = len(records)
            errors = sum(1 for r in records if not r.success)

            return errors / total if total > 0 else 0.0

    def get_throughput(self, operation: Optional[str] = None,
                      window_seconds: float = 60.0) -> Optional[float]:
        """
        Get operations per second

        Args:
            operation: Specific operation, or all operations
            window_seconds: Time window for calculation

        Returns:
            Throughput (operations/second)
        """
        cutoff = datetime.now() - timedelta(seconds=window_seconds)

        records = [r for r in self._executions if r.start_time >= cutoff]

        if operation:
            records = [r for r in records if r.operation == operation]

        if not records:
            return None

        return len(records) / window_seconds

    def _update_operation_stats(self, record: ExecutionRecord) -> None:
        """Update operation statistics"""
        if record.operation not in self._operation_stats:
            self._operation_stats[record.operation] = {
                "count": 0,
                "total_duration_ms": 0.0,
                "success_count": 0,
                "error_count": 0,
            }

        stats = self._operation_stats[record.operation]
        stats["count"] += 1
        stats["total_duration_ms"] += record.duration_ms or 0.0
        if record.success:
            stats["success_count"] += 1
        else:
            stats["error_count"] += 1

    # ================================================================
    # Performance Insights
    # ================================================================

    def identify_bottlenecks(self) -> List[Dict]:
        """
        Identify performance bottlenecks

        Returns:
            List of bottleneck descriptions
        """
        bottlenecks = []

        # Check for slow operations
        slow_ops = self.get_slow_operations()
        if slow_ops:
            # Group by operation type
            by_op = {}
            for record in slow_ops:
                op = record.operation
                if op not in by_op:
                    by_op[op] = []
                by_op[op].append(record)

            for op, records in by_op.items():
                avg_duration = sum(r.duration_ms for r in records) / len(records)
                bottlenecks.append({
                    "type": "slow_operation",
                    "operation": op,
                    "average_duration_ms": avg_duration,
                    "count": len(records),
                    "severity": "high" if avg_duration > self._thresholds["slow_operation_ms"] else "medium"
                })

        # Check for high error rate
        error_rate = self.get_error_rate()
        if error_rate and error_rate > 0.05:  # 5% error rate
            bottlenecks.append({
                "type": "high_error_rate",
                "error_rate": error_rate,
                "severity": "high" if error_rate > 0.1 else "medium"
            })

        return bottlenecks

    def get_performance_summary(self) -> Dict:
        """
        Get comprehensive performance summary

        Returns:
            Performance summary dictionary
        """
        return {
            "agent_id": self.agent_id,
            "total_executions": len(self._executions),
            "average_duration_ms": self.get_average_duration(),
            "p95_duration_ms": self.get_percentile_duration(95),
            "p99_duration_ms": self.get_percentile_duration(99),
            "error_rate": self.get_error_rate(),
            "bottlenecks": self.identify_bottlenecks(),
            "throughput_per_sec": self.get_throughput(),
        }

    # ================================================================
    # Configuration
    # ================================================================

    def set_threshold(self, name: str, value: float) -> None:
        """Set a performance threshold"""
        self._thresholds[name] = value

    def get_threshold(self, name: str) -> Optional[float]:
        """Get a performance threshold"""
        return self._thresholds.get(name)

    # ================================================================
    # Context Manager Support
    # ================================================================

    def __enter__(self):
        """Start monitoring context"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End monitoring context"""
        success = exc_type is None
        error = str(exc_val) if exc_val else None
        self.end_operation(success=success, error=error)


# ================================================================
# Decorators
# ================================================================

def monitor_operation(monitor: AgentMonitor, operation: Optional[str] = None):
    """
    Decorator to monitor function execution

    Args:
        monitor: AgentMonitor instance
        operation: Operation name (defaults to function name)
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            monitor.start_operation(op_name)
            try:
                result = func(*args, **kwargs)
                monitor.end_operation(success=True)
                return result
            except Exception as e:
                monitor.end_operation(success=False, error=str(e))
                raise
        return wrapper
    return decorator


__all__ = [
    "PerformanceMetric",
    "ExecutionRecord",
    "AgentMonitor",
    "monitor_operation",
]
