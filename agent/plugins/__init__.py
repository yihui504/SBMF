"""
Agent Plugin System

Provides a plugin architecture for extending agent capabilities.
"""

from agent.plugins.base_plugin import BasePlugin, PluginInfo, PluginStatus
from agent.plugins.registry import PluginRegistry

__all__ = [
    "BasePlugin",
    "PluginInfo",
    "PluginStatus",
    "PluginRegistry",
]
