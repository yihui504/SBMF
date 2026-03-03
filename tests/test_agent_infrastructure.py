"""
Tests for Agent Infrastructure
"""
import pytest
import tempfile
from pathlib import Path

from agent.memory import AgentMemory, MemoryType, MemoryItem
from agent.context import AgentContext, ContextScope, DatabaseType, SystemState
from agent.monitor import AgentMonitor, ExecutionRecord, monitor_operation
from agent.tools.base_tool import BaseTool, ToolCapability, ToolResult, ToolStatus
from agent.tools.registry import ToolRegistry
from agent.tools.executor import ParallelExecutor, ExecutionTask
from agent.plugins.base_plugin import BasePlugin, PluginInfo, PluginStatus
from agent.plugins.registry import PluginRegistry
from agent.runtime import AgentRuntime, AgentConfig


# ================================================================
# Memory Tests
# ================================================================

class TestAgentMemory:
    """Test agent memory system"""

    def test_memory_initialization(self):
        """Test memory initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = AgentMemory("test_agent", Path(tmpdir))
            assert memory.agent_id == "test_agent"
            assert memory.get_stats()["long_term_count"] == 0

    def test_store_and_retrieve(self):
        """Test storing and retrieving values"""
        memory = AgentMemory("test_agent")
        memory.store("key1", "value1", MemoryType.SHORT_TERM)
        assert memory.retrieve("key1") == "value1"

    def test_memory_hierarchy(self):
        """Test memory type hierarchy"""
        memory = AgentMemory("test_agent")

        memory.store("key", "short_term", MemoryType.SHORT_TERM)
        memory.store("key", "long_term", MemoryType.LONG_TERM)
        memory.store("key", "working", MemoryType.WORKING)

        # Working memory has highest priority
        assert memory.retrieve("key") == "working"

    def test_search_memory(self):
        """Test searching memory"""
        memory = AgentMemory("test_agent")

        memory.store("test1", "value1", MemoryType.SHORT_TERM,
                    metadata={"type": "test"})
        memory.store("test2", "value2", MemoryType.SHORT_TERM,
                    metadata={"type": "production"})

        # Search by specific metadata key
        results = memory.search({"type": "test"})
        assert len(results) == 1
        assert results[0].key == "test1"

    def test_long_term_persistence(self):
        """Test long-term memory persistence"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir)

            # Create and store data
            memory1 = AgentMemory("test_agent", storage_path)
            memory1.store("persistent_key", "persistent_value", MemoryType.LONG_TERM)

            # Create new instance and verify data persisted
            memory2 = AgentMemory("test_agent", storage_path)
            assert memory2.retrieve("persistent_key") == "persistent_value"


# ================================================================
# Context Tests
# ================================================================

class TestAgentContext:
    """Test agent context system"""

    def test_context_initialization(self):
        """Test context initialization"""
        context = AgentContext("test_agent")
        assert context.agent_id == "test_agent"
        assert context._database_type == DatabaseType.UNKNOWN

    def test_context_hierarchy(self):
        """Test context hierarchy"""
        context = AgentContext("test_agent")

        context.set_global("global_key", "global_value")
        context.set_session("session_key", "session_value")
        context.set_task("task_key", "task_value")

        # Task context should override
        assert context.get("task_key") == "task_value"
        assert context.get("session_key") == "session_value"
        assert context.get("global_key") == "global_value"

    def test_database_type(self):
        """Test database type tracking"""
        context = AgentContext("test_agent")
        context.set_database_type(DatabaseType.MILVUS)

        assert context.get_database_type() == DatabaseType.MILVUS
        assert context.get("database_type") == DatabaseType.MILVUS

    def test_system_state(self):
        """Test system state tracking"""
        context = AgentContext("test_agent")
        context.update_system_state(cpu_usage=75.0, memory_usage=60.0)

        state = context.get_system_state()
        assert state.cpu_usage == 75.0
        assert state.memory_usage == 60.0

    def test_load_detection(self):
        """Test load detection"""
        context = AgentContext("test_agent")
        assert not context.is_under_load()

        context.update_system_state(cpu_usage=90.0)
        assert context.is_under_load()

    def test_context_snapshot(self):
        """Test context snapshot and restore"""
        context1 = AgentContext("test_agent")
        context1.set_task("task1", "value1")

        snapshot = context1.snapshot()

        context2 = AgentContext("test_agent")
        context2.restore(snapshot)

        assert context2.get("task1") == "value1"


# ================================================================
# Monitor Tests
# ================================================================

class TestAgentMonitor:
    """Test agent monitor"""

    def test_monitor_initialization(self):
        """Test monitor initialization"""
        monitor = AgentMonitor("test_agent")
        assert monitor.agent_id == "test_agent"

    def test_operation_tracking(self):
        """Test operation tracking"""
        monitor = AgentMonitor("test_agent")

        monitor.start_operation("test_operation")
        duration = monitor.end_operation()

        assert duration is not None
        assert duration >= 0

    def test_execution_records(self):
        """Test execution record creation"""
        monitor = AgentMonitor("test_agent")

        monitor.start_operation("op1")
        monitor.end_operation(success=True)

        monitor.start_operation("op2")
        monitor.end_operation(success=False, error="Test error")

        records = list(monitor._executions)
        assert len(records) == 2
        assert records[0].success
        assert not records[1].success
        assert records[1].error == "Test error"

    def test_average_duration(self):
        """Test average duration calculation"""
        import time
        monitor = AgentMonitor("test_agent")

        for _ in range(3):
            monitor.start_operation("test")
            time.sleep(0.001)  # Small delay to ensure non-zero duration
            monitor.end_operation()

        avg = monitor.get_average_duration("test")
        assert avg is not None
        assert avg >= 0  # Allow 0 if very fast

    def test_monitor_decorator(self):
        """Test monitor decorator"""
        monitor = AgentMonitor("test_agent")

        @monitor_operation(monitor, "decorated_func")
        def test_func():
            return 42

        result = test_func()
        assert result == 42

        # Verify operation was tracked
        assert len(monitor._executions) == 1
        assert monitor._executions[0].operation == "decorated_func"

    def test_context_manager(self):
        """Test monitor as context manager"""
        monitor = AgentMonitor("test_agent")

        with monitor:
            monitor.start_operation("context_test")
            pass  # Do nothing

        # Verify operation was tracked
        assert len(monitor._executions) >= 1


# ================================================================
# Tool System Tests
# ================================================================

class DummyTool(BaseTool):
    """Dummy tool for testing"""

    def get_capability(self) -> ToolCapability:
        return ToolCapability(
            name="dummy_tool",
            description="A dummy test tool",
            parameters={"input": {"type": "string"}},
            required_params=[],
            returns="string"
        )

    def execute(self, **kwargs) -> ToolResult:
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=f"Processed: {kwargs.get('input', 'default')}"
        )


class TestToolSystem:
    """Test tool system"""

    def test_tool_execution(self):
        """Test tool execution"""
        tool = DummyTool()
        result = tool.execute(input="test")

        assert result.is_success()
        assert result.data == "Processed: test"

    def test_tool_registry(self):
        """Test tool registry"""
        registry = ToolRegistry()
        tool = DummyTool()

        registry.register(tool, "dummy")

        assert "dummy" in registry.list_tools()
        assert registry.get_tool("dummy") is tool

    def test_tool_execution_through_registry(self):
        """Test tool execution through registry"""
        registry = ToolRegistry()
        tool = DummyTool()
        registry.register(tool, "dummy_tool")  # Specify name explicitly

        result = registry.execute("dummy_tool", input="test")

        assert result.is_success()
        assert result.data == "Processed: test"

    def test_parallel_executor(self):
        """Test parallel executor"""
        executor = ParallelExecutor(max_workers=2)

        def func(x):
            return x * 2

        tasks = [
            ExecutionTask(id="t1", func=func, args=(1,)),
            ExecutionTask(id="t2", func=func, args=(2,)),
            ExecutionTask(id="t3", func=func, args=(3,)),
        ]

        with executor:
            results = executor.execute_batch(tasks)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert {r.task_id for r in results} == {"t1", "t2", "t3"}

    def test_parallel_map(self):
        """Test parallel map operation"""
        executor = ParallelExecutor(max_workers=2)

        def double(x):
            return x * 2

        with executor:
            results = executor.map(double, [1, 2, 3, 4, 5])

        # Results may be in different order due to parallel execution
        assert sorted(results) == [2, 4, 6, 8, 10]


# ================================================================
# Plugin System Tests
# ================================================================

class DummyPlugin(BasePlugin):
    """Dummy plugin for testing"""

    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name="dummy_plugin",
            version="1.0.0",
            description="A dummy test plugin"
        )


class TestPluginSystem:
    """Test plugin system"""

    def test_plugin_initialization(self):
        """Test plugin initialization"""
        plugin = DummyPlugin()
        assert plugin.get_info().name == "dummy_plugin"
        assert plugin.is_enabled()

    def test_plugin_lifecycle(self):
        """Test plugin lifecycle"""
        plugin = DummyPlugin()

        assert plugin.get_status() == PluginStatus.LOADED

        result = plugin.initialize()
        assert result.success
        assert plugin.get_status() == PluginStatus.ACTIVE

        result = plugin.shutdown()
        assert result.success
        assert plugin.get_status() == PluginStatus.INACTIVE

    def test_plugin_enable_disable(self):
        """Test plugin enable/disable"""
        plugin = DummyPlugin()
        plugin.initialize()

        plugin.disable()
        assert not plugin.is_enabled()

        plugin.enable()
        assert plugin.is_enabled()

    def test_plugin_registry(self):
        """Test plugin registry"""
        registry = PluginRegistry()
        plugin = DummyPlugin()

        success = registry.register(plugin)
        assert success

        assert "dummy_plugin" in registry.list_plugins()

        info = registry.get_plugin_info("dummy_plugin")
        assert info.version == "1.0.0"

    def test_plugin_config_update(self):
        """Test plugin config update"""
        plugin = DummyPlugin(config={"key": "value"})

        assert plugin.get_config()["key"] == "value"

        plugin.update_config({"new_key": "new_value"})
        assert plugin.get_config()["new_key"] == "new_value"
        assert plugin.get_config()["key"] == "value"  # Original preserved


# ================================================================
# Runtime Tests
# ================================================================

class TestAgentRuntime:
    """Test agent runtime"""

    def test_runtime_initialization(self):
        """Test runtime initialization"""
        config = AgentConfig(agent_id="test_agent")
        runtime = AgentRuntime(config)

        assert runtime.config.agent_id == "test_agent"
        assert not runtime.is_running()

    def test_runtime_lifecycle(self):
        """Test runtime lifecycle"""
        config = AgentConfig(agent_id="test_agent")
        runtime = AgentRuntime(config)

        runtime.start()
        assert runtime.is_running()

        runtime.stop()
        assert not runtime.is_running()

    def test_context_operations(self):
        """Test context operations through runtime"""
        config = AgentConfig(agent_id="test_agent")
        runtime = AgentRuntime(config)

        runtime.set_context("key", "value")
        assert runtime.get_context("key") == "value"

    def test_memory_operations(self):
        """Test memory operations through runtime"""
        config = AgentConfig(agent_id="test_agent", enable_memory=True)
        runtime = AgentRuntime(config)

        runtime.remember("test_key", "test_value")
        assert runtime.recall("test_key") == "test_value"

    def test_execute_task(self):
        """Test task execution"""
        config = AgentConfig(agent_id="test_agent")
        runtime = AgentRuntime(config)
        runtime.start()

        def test_function(x):
            return x * 2

        result = runtime.execute_task("multiply", test_function, 5)
        assert result == 10

        runtime.stop()

    def test_get_stats(self):
        """Test getting statistics"""
        config = AgentConfig(agent_id="test_agent")
        runtime = AgentRuntime(config)

        stats = runtime.get_stats()
        assert "agent_id" in stats
        assert stats["agent_id"] == "test_agent"
        assert not stats["running"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
