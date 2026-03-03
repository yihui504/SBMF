"""
Agent Plugin Registry

Manages plugin registration, discovery, and lifecycle.
"""
import threading
from typing import Any, Dict, List, Optional, Type
from pathlib import Path

from agent.plugins.base_plugin import BasePlugin, PluginInfo, PluginResult, PluginStatus


class PluginRegistry:
    """
    Registry for agent plugins

    Manages plugin registration, loading, and lifecycle.
    """

    def __init__(self):
        """Initialize plugin registry"""
        self._plugins: Dict[str, BasePlugin] = {}
        self._plugin_info: Dict[str, PluginInfo] = {}
        self._lock = threading.Lock()

    # ================================================================
    # Plugin Registration
    # ================================================================

    def register(self, plugin: BasePlugin, name: Optional[str] = None) -> bool:
        """
        Register a plugin

        Args:
            plugin: Plugin instance
            name: Optional name (defaults to plugin info name)

        Returns:
            True if registered successfully
        """
        with self._lock:
            info = plugin.get_info()
            plugin_name = name or info.name

            # Check dependencies
            if not self._check_dependencies(info.dependencies):
                return False

            self._plugins[plugin_name] = plugin
            self._plugin_info[plugin_name] = info

            # Initialize plugin
            result = plugin.initialize()
            if not result.success:
                del self._plugins[plugin_name]
                del self._plugin_info[plugin_name]
                return False

            return True

    def register_class(self, plugin_class: Type[BasePlugin],
                       name: Optional[str] = None,
                       config: Optional[Dict] = None) -> bool:
        """
        Register a plugin class (instantiates it)

        Args:
            plugin_class: Plugin class
            name: Optional name
            config: Plugin configuration

        Returns:
            True if registered successfully
        """
        plugin = plugin_class(config)
        return self.register(plugin, name)

    def unregister(self, name: str) -> bool:
        """
        Unregister a plugin

        Args:
            name: Plugin name

        Returns:
            True if unregistered
        """
        with self._lock:
            if name not in self._plugins:
                return False

            plugin = self._plugins[name]
            plugin.shutdown()
            del self._plugins[name]
            del self._plugin_info[name]
            return True

    # ================================================================
    # Plugin Discovery
    # ================================================================

    def list_plugins(self) -> List[str]:
        """List all registered plugin names"""
        return list(self._plugins.keys())

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Get a plugin by name"""
        return self._plugins.get(name)

    def get_plugin_info(self, name: str) -> Optional[PluginInfo]:
        """Get plugin information"""
        return self._plugin_info.get(name)

    def get_all_info(self) -> Dict[str, PluginInfo]:
        """Get all plugin information"""
        return self._plugin_info.copy()

    def find_plugins_by_status(self, status: PluginStatus) -> List[str]:
        """Find plugins by status"""
        return [
            name for name, plugin in self._plugins.items()
            if plugin.get_status() == status
        ]

    # ================================================================
    # Plugin Operations
    # ================================================================

    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin"""
        plugin = self.get_plugin(name)
        if plugin:
            plugin.enable()
            return True
        return False

    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin"""
        plugin = self.get_plugin(name)
        if plugin:
            plugin.disable()
            return True
        return False

    def update_plugin_config(self, name: str, config: Dict) -> bool:
        """Update plugin configuration"""
        plugin = self.get_plugin(name)
        if plugin:
            plugin.update_config(config)
            return True
        return False

    # ================================================================
    # Plugin Events
    # ================================================================

    def notify_agent_start(self) -> None:
        """Notify all plugins that agent is starting"""
        for plugin in self._plugins.values():
            if plugin.is_enabled():
                plugin.on_agent_start()

    def notify_agent_stop(self) -> None:
        """Notify all plugins that agent is stopping"""
        for plugin in self._plugins.values():
            if plugin.is_enabled():
                plugin.on_agent_stop()

    def notify_task_start(self, task: str) -> None:
        """Notify plugins that a task is starting"""
        for plugin in self._plugins.values():
            if plugin.is_enabled():
                plugin.on_task_start(task)

    def notify_task_complete(self, task: str, result: Any) -> None:
        """Notify plugins that a task completed"""
        for plugin in self._plugins.values():
            if plugin.is_enabled():
                plugin.on_task_complete(task, result)

    def notify_error(self, error: Exception) -> None:
        """Notify plugins of an error"""
        for plugin in self._plugins.values():
            if plugin.is_enabled():
                plugin.on_error(error)

    # ================================================================
    # Dependency Management
    # ================================================================

    def _check_dependencies(self, dependencies: List[str]) -> bool:
        """Check if all dependencies are satisfied"""
        for dep in dependencies:
            if dep not in self._plugins:
                return False
        return True

    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """Get dependency graph"""
        graph = {}
        for name, info in self._plugin_info.items():
            graph[name] = info.dependencies
        return graph

    def get_load_order(self) -> List[str]:
        """
        Get plugin load order based on dependencies

        Returns:
            List of plugin names in load order
        """
        graph = self.get_dependency_graph()
        order = []
        visited = set()

        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            for dep in graph.get(name, []):
                visit(dep)
            order.append(name)

        for name in graph:
            visit(name)

        return order


# Global registry instance
_global_registry: Optional[PluginRegistry] = None


def get_global_registry() -> PluginRegistry:
    """Get the global plugin registry"""
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry


__all__ = [
    "PluginRegistry",
    "get_global_registry",
]
