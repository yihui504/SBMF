"""
Agent Tool Registry

Manages registration and discovery of agent tools.
"""
import time
from typing import Any, Dict, List, Optional, Type
from pathlib import Path

from agent.tools.base_tool import BaseTool, ToolCapability, ToolResult, ToolStatus


class ToolRegistry:
    """
    Registry for agent tools

    Manages tool registration, discovery, and execution.
    """

    def __init__(self):
        """Initialize tool registry"""
        self._tools: Dict[str, BaseTool] = {}
        self._capabilities: Dict[str, ToolCapability] = {}

    # ================================================================
    # Tool Registration
    # ================================================================

    def register(self, tool: BaseTool, name: Optional[str] = None) -> None:
        """
        Register a tool

        Args:
            tool: Tool instance to register
            name: Optional name (defaults to tool class name)
        """
        tool_name = name or tool.__class__.__name__
        self._tools[tool_name] = tool
        self._capabilities[tool_name] = tool.get_capability()

    def register_class(self, tool_class: Type[BaseTool],
                      name: Optional[str] = None,
                      **kwargs) -> None:
        """
        Register a tool class (instantiates it)

        Args:
            tool_class: Tool class to register
            name: Optional name
            **kwargs: Arguments for tool instantiation
        """
        tool = tool_class(**kwargs)
        self.register(tool, name)

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool

        Args:
            name: Tool name

        Returns:
            True if unregistered, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            del self._capabilities[name]
            return True
        return False

    # ================================================================
    # Tool Discovery
    # ================================================================

    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self._tools.keys())

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self._tools.get(name)

    def get_capability(self, name: str) -> Optional[ToolCapability]:
        """Get tool capability"""
        return self._capabilities.get(name)

    def get_all_capabilities(self) -> Dict[str, ToolCapability]:
        """Get all tool capabilities"""
        return self._capabilities.copy()

    def find_tools_by_capability(self, keyword: str) -> List[str]:
        """
        Find tools by capability keyword

        Args:
            keyword: Keyword to search for

        Returns:
            List of tool names matching the keyword
        """
        results = []
        keyword_lower = keyword.lower()

        for name, capability in self._capabilities.items():
            if (keyword_lower in name.lower() or
                keyword_lower in capability.description.lower()):
                results.append(name)

        return results

    # ================================================================
    # Tool Execution
    # ================================================================

    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute a tool

        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool parameters

        Returns:
            ToolResult from execution
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Tool not found: {tool_name}"
            )

        # Validate parameters
        validation_error = tool.validate_params(kwargs)
        if validation_error:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=validation_error
            )

        # Execute with timing
        import time
        start_time = time.time()
        try:
            result = tool.execute(**kwargs)
            execution_time = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time
            return result
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                execution_time_ms=execution_time
            )

    # ================================================================
    # Registry Statistics
    # ================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        tool_stats = {}

        for name, tool in self._tools.items():
            tool_stats[name] = tool.get_stats()

        return {
            "total_tools": len(self._tools),
            "safe_tools": sum(1 for c in self._capabilities.values()
                            if c.is_safe),
            "tool_stats": tool_stats,
        }


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_global_registry() -> ToolRegistry:
    """Get the global tool registry"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


__all__ = [
    "ToolRegistry",
    "get_global_registry",
]
