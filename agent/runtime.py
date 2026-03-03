"""
Agent Runtime

Core runtime system for AI agents in the bug mining framework.
"""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

from agent.memory import AgentMemory, MemoryType
from agent.context import AgentContext
from agent.monitor import AgentMonitor
from agent.tools.registry import ToolRegistry, get_global_registry
from agent.plugins.registry import PluginRegistry, get_global_registry as get_plugin_registry


@dataclass
class AgentConfig:
    """Agent configuration"""
    agent_id: str
    agent_type: str = "generic"
    enable_monitoring: bool = True
    enable_memory: bool = True
    max_history: int = 1000
    storage_dir: Optional[str] = None


class AgentRuntime:
    """
    Agent Runtime System

    Provides the core runtime environment for agents, including:
    - Memory management
    - Context awareness
    - Performance monitoring
    - Tool execution
    - Plugin system
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize agent runtime

        Args:
            config: Agent configuration
        """
        self.config = config

        # Core components
        self.context = AgentContext(config.agent_id)
        self.monitor = AgentMonitor(config.agent_id) if config.enable_monitoring else None
        self.memory = AgentMemory(config.agent_id) if config.enable_memory else None

        # Create fresh registries for this runtime instance
        # (not using global singletons to avoid test pollution)
        from agent.tools.registry import ToolRegistry
        from agent.plugins.registry import PluginRegistry

        self.tools = ToolRegistry()
        self.plugins = PluginRegistry()

        # State
        self._running = False
        self._operation_count = 0

    # ================================================================
    # Lifecycle Management
    # ================================================================

    def start(self) -> None:
        """Start the agent runtime"""
        self._running = True
        self.plugins.notify_agent_start()

        if self.monitor:
            self.monitor.start_operation("agent_runtime")

        if self.memory:
            self.memory.store(
                "runtime_started",
                True,
                MemoryType.LONG_TERM,
                {"timestamp": self._operation_count}
            )

    def stop(self) -> None:
        """Stop the agent runtime"""
        self._running = False

        if self.monitor:
            duration = self.monitor.end_operation(success=True)
            self.plugins.notify_agent_stop()

        if self.memory:
            self.memory.store(
                "runtime_stopped",
                True,
                MemoryType.LONG_TERM,
                {"operation_count": self._operation_count}
            )

    def is_running(self) -> bool:
        """Check if runtime is running"""
        return self._running

    # ================================================================
    # Tool Execution
    # ================================================================

    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a tool

        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool parameters

        Returns:
            Tool execution result
        """
        if not self._running:
            raise RuntimeError("Agent runtime is not running")

        self._operation_count += 1

        # Update context
        self.context.set_operation(
            type(self.context).OperationContext(
                operation_type="tool_execution",
                target_component=tool_name,
                parameters=kwargs
            )
        )

        # Execute with monitoring
        if self.monitor:
            self.monitor.start_operation(f"tool_{tool_name}", **kwargs)

        try:
            result = self.tools.execute(tool_name, **kwargs)

            if self.monitor:
                self.monitor.end_operation(success=result.is_success())

            # Store in memory
            if self.memory and result.is_success():
                self.memory.store(
                    f"tool_result_{tool_name}",
                    result.data,
                    MemoryType.SHORT_TERM
                )

            return result

        except Exception as e:
            if self.monitor:
                self.monitor.end_operation(success=False, error=str(e))

            self.plugins.notify_error(e)
            raise

    # ================================================================
    # Memory Operations
    # ================================================================

    def remember(self, key: str, value: Any,
                 memory_type: MemoryType = MemoryType.SHORT_TERM,
                 metadata: Optional[Dict] = None) -> None:
        """
        Store information in memory

        Args:
            key: Memory key
            value: Value to store
            memory_type: Type of memory
            metadata: Optional metadata
        """
        if self.memory:
            self.memory.store(key, value, memory_type, metadata)

    def recall(self, key: str, memory_type: Optional[MemoryType] = None) -> Optional[Any]:
        """
        Retrieve information from memory

        Args:
            key: Memory key
            memory_type: Specific memory type

        Returns:
            Stored value or None
        """
        if self.memory:
            return self.memory.retrieve(key, memory_type)
        return None

    def search_memory(self, query: Dict) -> List:
        """Search memory by query"""
        if self.memory:
            return self.memory.search(query)
        return []

    def get_recent_memories(self, count: int = 10) -> List:
        """Get recent memories"""
        if self.memory:
            return self.memory.get_recent(count)
        return []

    # ================================================================
    # Context Operations
    # ================================================================

    def set_context(self, key: str, value: Any, scope: str = "task") -> None:
        """Set context value"""
        if scope == "global":
            self.context.set_global(key, value)
        elif scope == "session":
            self.context.set_session(key, value)
        elif scope == "task":
            self.context.set_task(key, value)

    def get_context(self, key: str) -> Optional[Any]:
        """Get context value"""
        return self.context.get(key)

    def is_under_load(self) -> bool:
        """Check if system is under load"""
        return self.context.is_under_load()

    # ================================================================ stress
    # Plugin Management
    # ================================================================

    def register_plugin(self, plugin, name: Optional[str] = None) -> bool:
        """Register a plugin"""
        return self.plugins.register(plugin, name)

    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin"""
        return self.plugins.enable_plugin(name)

    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin"""
        return self.plugins.disable_plugin(name)

    # ================================================================
    # Performance & Stats
    # ================================================================

    def get_performance_summary(self) -> Dict:
        """Get performance summary"""
        if self.monitor:
            return self.monitor.get_performance_summary()
        return {}

    def get_memory_stats(self) -> Dict:
        """Get memory statistics"""
        if self.memory:
            return self.memory.get_stats()
        return {}

    def get_stats(self) -> Dict:
        """Get overall statistics"""
        return {
            "agent_id": self.config.agent_id,
            "operation_count": self._operation_count,
            "running": self._running,
            "performance": self.get_performance_summary(),
            "memory": self.get_memory_stats(),
            "context": {
                "database_type": self.context.get_database_type().value,
                "is_under_load": self.context.is_under_load(),
                "test_pass_rate": self.context.get_test_pass_rate(),
            }
        }

    # ================================================================
    # Task Execution
    # ================================================================

    def execute_task(self, task: str, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a task with monitoring

        Args:
            task: Task name
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result
        """
        self.context.push_task(task)
        self.plugins.notify_task_start(task)

        if self.monitor:
            self.monitor.start_operation(f"task_{task}")

        try:
            result = func(*args, **kwargs)

            if self.monitor:
                self.monitor.end_operation(success=True)

            self.plugins.notify_task_complete(task, result)
            self.context.pop_task()

            return result

        except Exception as e:
            if self.monitor:
                self.monitor.end_operation(success=False, error=str(e))

            self.plugins.notify_error(e)
            self.context.pop_task()

            raise


__all__ = [
    "AgentConfig",
    "AgentRuntime",
]
