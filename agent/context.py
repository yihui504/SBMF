"""
Agent Context System

Provides context awareness capabilities for agents to understand
and adapt to different environments and scenarios.
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


class ContextScope(Enum):
    """Context scope levels"""
    GLOBAL = "global"       # Framework-wide context
    SESSION = "session"     # Current session context
    TASK = "task"          # Current task context
    OPERATION = "operation" # Current operation context


class DatabaseType(Enum):
    """Supported database types"""
    SEEKDB = "seekdb"
    MILVUS = "milvus"
    WEAVIATE = "weaviate"
    UNKNOWN = "unknown"


@dataclass
class SystemState:
    """Current system state"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_connections: int = 0
    test_count: int = 0
    bug_count: int = 0

@dataclass
class OperationContext:
    """Context for current operation"""
    operation_type: str = ""
    target_component: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    timeout: Optional[float] = None


@dataclass
class TestingContext:
    """Context for testing operations"""
    test_suite: str = ""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    coverage: float = 0.0


class AgentContext:
    """
    Agent Context System

    Maintains hierarchical context for agents to make informed decisions.
    Context flows from GLOBAL → SESSION → TASK → OPERATION
    """

    def __init__(self, agent_id: str):
        """
        Initialize agent context

        Args:
            agent_id: Unique identifier for the agent
        """
        self.agent_id = agent_id

        # Context hierarchy
        self._global_context: Dict[str, Any] = {}
        self._session_context: Dict[str, Any] = {}
        self._task_context: Dict[str, Any] = {}
        self._operation_context: Optional[OperationContext] = None

        # Specialized contexts
        self._system_state = SystemState()
        self._testing_context = TestingContext()
        self._database_type = DatabaseType.UNKNOWN

        # Context history
        self._context_history: List[Dict] = []

    # ================================================================
    # Context Hierarchy Management
    # ================================================================

    def set_global(self, key: str, value: Any) -> None:
        """Set global context (framework-wide)"""
        self._global_context[key] = value
        self._record_history("global", key, value)

    def set_session(self, key: str, value: Any) -> None:
        """Set session context (current session)"""
        self._session_context[key] = value
        self._record_history("session", key, value)

    def set_task(self, key: str, value: Any) -> None:
        """Set task context (current task)"""
        self._task_context[key] = value
        self._record_history("task", key, value)

    def set_operation(self, operation: OperationContext) -> None:
        """Set current operation context"""
        self._operation_context = operation

    # ================================================================
    # Context Retrieval
    # ================================================================

    def get(self, key: str, scope: Optional[ContextScope] = None) -> Optional[Any]:
        """
        Get context value by key

        Searches from most specific to least specific context:
        OPERATION → TASK → SESSION → GLOBAL
        """
        if scope:
            return self._get_from_scope(key, scope)

        # Search operation context first
        if self._operation_context:
            if hasattr(self._operation_context, key):
                return getattr(self._operation_context, key)
            if key in self._operation_context.parameters:
                return self._operation_context.parameters[key]

        # Search other contexts
        for storage in [self._task_context, self._session_context, self._global_context]:
            if key in storage:
                return storage[key]

        return None

    def get_all(self, scope: ContextScope) -> Dict[str, Any]:
        """Get all context for a specific scope"""
        return self._get_from_scope(None, scope).copy()

    # ================================================================
    # Specialized Context
    # ================================================================

    def set_database_type(self, db_type: DatabaseType) -> None:
        """Set current database type"""
        self._database_type = db_type
        self.set_global("database_type", db_type)

    def get_database_type(self) -> DatabaseType:
        """Get current database type"""
        return self._database_type

    def update_system_state(self, **kwargs) -> None:
        """Update system state"""
        for key, value in kwargs.items():
            if hasattr(self._system_state, key):
                setattr(self._system_state, key, value)

    def get_system_state(self) -> SystemState:
        """Get current system state"""
        return self._system_state

    def update_testing_context(self, **kwargs) -> None:
        """Update testing context"""
        for key, value in kwargs.items():
            if hasattr(self._testing_context, key):
                setattr(self._testing_context, key, value)

    def get_testing_context(self) -> TestingContext:
        """Get current testing context"""
        return self._testing_context

    # ================================================================
    # Context Awareness
    # ================================================================

    def is_under_load(self) -> bool:
        """Check if system is under load"""
        return (
            self._system_state.cpu_usage > 80.0 or
            self._system_state.memory_usage > 80.0
        )

    def is_degraded(self) -> bool:
        """Check if system performance is degraded"""
        return (
            self._system_state.cpu_usage > 90.0 or
            self._system_state.memory_usage > 90.0 or
            self._testing_context.failed_tests > self._testing_context.passed_tests
        )

    def get_test_pass_rate(self) -> float:
        """Get current test pass rate"""
        total = self._testing_context.total_tests
        if total == 0:
            return 1.0
        return self._testing_context.passed_tests / total

    def get_bug_density(self) -> float:
        """Get bug density (bugs per test)"""
        tests = self._testing_context.total_tests
        if tests == 0:
            return 0.0
        return self._testing_context.bug_count / tests

    # ================================================================
    # Context Operations
    # ================================================================

    def push_task(self, task_name: str) -> None:
        """Push a new task context"""
        self.set_task("current_task", task_name)
        self.set_task("task_start_time", datetime.now())

    def pop_task(self) -> None:
        """Pop current task context"""
        self._task_context.clear()

    def clear_operation_context(self) -> None:
        """Clear operation context"""
        self._operation_context = None

    def snapshot(self) -> Dict[str, Any]:
        """Create a snapshot of current context"""
        return {
            "agent_id": self.agent_id,
            "global": self._global_context.copy(),
            "session": self._session_context.copy(),
            "task": self._task_context.copy(),
            "operation": self._operation_context,
            "system_state": self._system_state,
            "testing_context": self._testing_context,
            "database_type": self._database_type,
        }

    def restore(self, snapshot: Dict[str, Any]) -> None:
        """Restore context from snapshot"""
        self._global_context = snapshot.get("global", {}).copy()
        self._session_context = snapshot.get("session", {}).copy()
        self._task_context = snapshot.get("task", {}).copy()
        self._operation_context = snapshot.get("operation")
        self._system_state = snapshot.get("system_state", SystemState())
        self._testing_context = snapshot.get("testing_context", TestingContext())
        self._database_type = snapshot.get("database_type", DatabaseType.UNKNOWN)

    # ================================================================
    # Private Methods
    # ================================================================

    def _get_from_scope(self, key: Optional[str], scope: ContextScope) -> Any:
        """Get value from specific scope"""
        if scope == ContextScope.GLOBAL:
            storage = self._global_context
        elif scope == ContextScope.SESSION:
            storage = self._session_context
        elif scope == ContextScope.TASK:
            storage = self._task_context
        elif scope == ContextScope.OPERATION:
            if self._operation_context:
                return self._operation_context
            return {}
        else:
            raise ValueError(f"Unknown scope: {scope}")

        if key is None:
            return storage
        return storage.get(key)

    def _record_history(self, scope: str, key: str, value: Any) -> None:
        """Record context change to history"""
        self._context_history.append({
            "timestamp": datetime.now().isoformat(),
            "scope": scope,
            "key": key,
            "value": str(value)[:100],  # Truncate long values
        })

        # Keep history manageable
        if len(self._context_history) > 1000:
            self._context_history = self._context_history[-500:]

    def get_history(self, limit: int = 100) -> List[Dict]:
        """Get context change history"""
        return self._context_history[-limit:]


__all__ = [
    "ContextScope",
    "DatabaseType",
    "SystemState",
    "OperationContext",
    "TestingContext",
    "AgentContext",
]
