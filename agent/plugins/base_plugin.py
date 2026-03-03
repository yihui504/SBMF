"""
Agent Plugin Base Class

Base class for agent plugins with standardized interface.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class PluginStatus(Enum):
    """Plugin status"""
    LOADED = "loaded"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


@dataclass
class PluginInfo:
    """Plugin metadata"""
    name: str
    version: str
    description: str
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginResult:
    """Result from a plugin operation"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BasePlugin(ABC):
    """
    Base class for agent plugins

    Plugins extend agent capabilities with modular, swappable components.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize plugin

        Args:
            config: Plugin configuration
        """
        self.config = config or {}
        self._status = PluginStatus.LOADED
        self._enabled = True

    @abstractmethod
    def get_info(self) -> PluginInfo:
        """
        Get plugin information

        Returns:
            PluginInfo describing this plugin
        """
        pass

    def initialize(self) -> PluginResult:
        """
        Initialize the plugin

        Called after plugin is loaded.

        Returns:
            PluginResult indicating success or failure
        """
        self._status = PluginStatus.ACTIVE
        return PluginResult(success=True)

    def shutdown(self) -> PluginResult:
        """
        Shutdown the plugin

        Called before plugin is unloaded.

        Returns:
            PluginResult indicating success or failure
        """
        self._status = PluginStatus.INACTIVE
        return PluginResult(success=True)

    def enable(self) -> None:
        """Enable the plugin"""
        self._enabled = True
        if self._status == PluginStatus.INACTIVE:
            self._status = PluginStatus.ACTIVE

    def disable(self) -> None:
        """Disable the plugin"""
        self._enabled = False
        self._status = PluginStatus.INACTIVE

    def is_enabled(self) -> bool:
        """Check if plugin is enabled"""
        return self._enabled

    def get_status(self) -> PluginStatus:
        """Get plugin status"""
        return self._status

    def get_config(self) -> Dict:
        """Get plugin configuration"""
        return self.config.copy()

    def update_config(self, config: Dict) -> None:
        """Update plugin configuration"""
        self.config.update(config)

    # ================================================================
    # Plugin Hooks (Optional)
    # ================================================================

    def on_agent_start(self) -> None:
        """Called when agent starts"""
        pass

    def on_agent_stop(self) -> None:
        """Called when agent stops"""
        pass

    def on_task_start(self, task: str) -> None:
        """Called when agent starts a task"""
        pass

    def on_task_complete(self, task: str, result: Any) -> None:
        """Called when agent completes a task"""
        pass

    def on_error(self, error: Exception) -> None:
        """Called when an error occurs"""
        pass


__all__ = [
    "PluginStatus",
    "PluginInfo",
    "PluginResult",
    "BasePlugin",
]
