"""
Database Utilities

Common utilities for database adapters including connection pooling,
retry logic, and health checking.
"""
import time
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class HealthStatus(Enum):
    """Database health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Health check result"""
    status: HealthStatus
    latency_ms: float
    error: Optional[str] = None
    extra_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionStats:
    """Connection statistics"""
    total_attempts: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    total_latency_ms: float = 0.0
    last_error: Optional[str] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_attempts == 0:
            return 0.0
        return self.successful_connections / self.total_attempts

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency"""
        if self.successful_connections == 0:
            return 0.0
        return self.total_latency_ms / self.successful_connections


class ConnectionPool:
    """Simple connection pool for database adapters

    Note: This is a lightweight implementation. For production use,
    consider using dedicated connection pooling libraries.
    """

    def __init__(self,
                 adapter_factory: Callable,
                 max_connections: int = 10,
                 max_idle_time: float = 300.0):
        """
        Initialize connection pool

        Args:
            adapter_factory: Function that creates new adapter instances
            max_connections: Maximum number of connections
            max_idle_time: Maximum idle time before connection is closed
        """
        self.adapter_factory = adapter_factory
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time

        self._pool: List[Any] = []
        self._in_use: Dict[int, float] = {}
        self._lock = threading.Lock()
        self._stats = ConnectionStats()

    def acquire(self, timeout: float = 5.0) -> Optional[Any]:
        """
        Acquire a connection from the pool

        Args:
            timeout: Maximum time to wait for connection

        Returns:
            Adapter instance or None if unavailable
        """
        start_time = time.time()
        self._stats.total_attempts += 1

        while time.time() - start_time < timeout:
            with self._lock:
                # Check for available connection
                if self._pool:
                    adapter = self._pool.pop()
                    self._in_use[id(adapter)] = time.time()
                    self._stats.successful_connections += 1
                    return adapter

                # Create new connection if under limit
                if len(self._in_use) < self.max_connections:
                    adapter = self.adapter_factory()
                    if adapter.connect():
                        self._in_use[id(adapter)] = time.time()
                        self._stats.successful_connections += 1
                        return adapter

            # Wait before retrying
            time.sleep(0.1)

        self._stats.failed_connections += 1
        return None

    def release(self, adapter: Any) -> None:
        """
        Release a connection back to the pool

        Args:
            adapter: Adapter instance to release
        """
        with self._lock:
            adapter_id = id(adapter)
            if adapter_id in self._in_use:
                del self._in_use[adapter_id]

                # Check if connection is still valid
                if adapter.is_connected():
                    self._pool.append(adapter)
                else:
                    # Close and remove invalid connection
                    try:
                        adapter.disconnect()
                    except Exception:
                        pass

    def close_all(self) -> None:
        """Close all connections in the pool"""
        with self._lock:
            # Close pooled connections
            for adapter in self._pool:
                try:
                    adapter.disconnect()
                except Exception:
                    pass
            self._pool.clear()

            # Close in-use connections
            for adapter_id in list(self._in_use.keys()):
                # Can't close in-use connections safely
                pass
            self._in_use.clear()

    def get_stats(self) -> ConnectionStats:
        """Get connection statistics"""
        return self._stats

    @property
    def available(self) -> int:
        """Get number of available connections"""
        return len(self._pool)

    @property
    def in_use_count(self) -> int:
        """Get number of in-use connections"""
        return len(self._in_use)


class RetryPolicy:
    """Retry policy for database operations"""

    def __init__(self,
                 max_retries: int = 3,
                 base_delay: float = 0.1,
                 max_delay: float = 5.0,
                 backoff_factor: float = 2.0):
        """
        Initialize retry policy

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries
            max_delay: Maximum delay between retries
            backoff_factor: Multiplier for delay after each retry
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    def get_delay(self, attempt: int) -> float:
        """Get delay for a specific retry attempt"""
        delay = self.base_delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)

    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Determine if operation should be retried"""
        if attempt >= self.max_retries:
            return False

        # Don't retry certain errors
        if isinstance(error, (ValueError, KeyError)):
            return False

        return True


def with_retry(policy: RetryPolicy):
    """Decorator for retrying database operations

    Args:
        policy: Retry policy to use

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(policy.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if not policy.should_retry(attempt, e):
                        raise

                    if attempt < policy.max_retries:
                        delay = policy.get_delay(attempt)
                        time.sleep(delay)

            raise last_error
        return wrapper
    return decorator


class DatabaseHealthChecker:
    """Health checker for database connections"""

    def __init__(self, check_interval: float = 30.0):
        """
        Initialize health checker

        Args:
            check_interval: Seconds between health checks
        """
        self.check_interval = check_interval
        self._results: Dict[str, List[HealthCheckResult]] = defaultdict(list)
        self._lock = threading.Lock()

    def check_health(self, adapter: Any,
                     adapter_name: str = "adapter") -> HealthCheckResult:
        """
        Check health of a database adapter

        Args:
            adapter: Database adapter to check
            adapter_name: Name of the adapter

        Returns:
            Health check result
        """
        start_time = time.time()
        status = HealthStatus.UNKNOWN
        error = None
        extra_info = {}

        try:
            # Check if connected
            if not adapter.is_connected():
                status = HealthStatus.UNHEALTHY
                error = "Not connected"
            else:
                # Try to get capabilities (lightweight operation)
                capabilities = adapter.get_capabilities()
                status = HealthStatus.HEALTHY
                extra_info["operations"] = len(capabilities.supported_operations)
                extra_info["distributed"] = capabilities.distributed

        except TimeoutError as e:
            status = HealthStatus.UNHEALTHY
            error = f"Timeout: {e}"
        except ConnectionError as e:
            status = HealthStatus.UNHEALTHY
            error = f"Connection error: {e}"
        except Exception as e:
            status = HealthStatus.DEGRADED
            error = str(e)

        latency_ms = (time.time() - start_time) * 1000

        result = HealthCheckResult(
            status=status,
            latency_ms=latency_ms,
            error=error,
            extra_info=extra_info
        )

        # Store result
        with self._lock:
            self._results[adapter_name].append(result)
            # Keep only last 100 results
            if len(self._results[adapter_name]) > 100:
                self._results[adapter_name] = self._results[adapter_name][-100:]

        return result

    def get_health_history(self,
                           adapter_name: str,
                           limit: int = 10) -> List[HealthCheckResult]:
        """
        Get health check history for an adapter

        Args:
            adapter_name: Name of the adapter
            limit: Maximum number of results to return

        Returns:
            List of health check results
        """
        with self._lock:
            history = self._results.get(adapter_name, [])
            return history[-limit:]

    def get_overall_status(self, adapter_name: str) -> HealthStatus:
        """Get overall health status for an adapter"""
        history = self.get_health_history(adapter_name, limit=10)
        if not history:
            return HealthStatus.UNKNOWN

        # Check recent results
        recent = history[-5:] if len(history) >= 5 else history
        unhealthy_count = sum(1 for r in recent if r.status == HealthStatus.UNHEALTHY)

        if unhealthy_count == 0:
            return HealthStatus.HEALTHY
        elif unhealthy_count >= len(recent) // 2:
            return HealthStatus.UNHEALTHY
        else:
            return HealthStatus.DEGRADED


__all__ = [
    "HealthStatus",
    "HealthCheckResult",
    "ConnectionStats",
    "ConnectionPool",
    "RetryPolicy",
    "with_retry",
    "DatabaseHealthChecker",
]
