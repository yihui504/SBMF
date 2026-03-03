"""
Agent Tool Base Class

Base class for agent tools with standardized interface.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class ToolStatus(Enum):
    """Tool execution status"""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class ToolResult:
    """Result of a tool execution"""
    status: ToolStatus
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: Optional[float] = None

    def is_success(self) -> bool:
        """Check if execution was successful"""
        return self.status == ToolStatus.SUCCESS

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class ToolCapability:
    """Describes what a tool can do"""
    name: str
    description: str
    parameters: Dict[str, Any]  # Parameter schema
    required_params: List[str]
    returns: str  # Return type description
    is_safe: bool = True  # Whether tool is safe to use


class BaseTool(ABC):
    """
    Base class for agent tools

    Tools provide agents with capabilities to interact with the framework
    and external systems. All tools must inherit from this class.
    """

    def __init__(self):
        self._call_count = 0
        self._total_time_ms = 0.0

    @abstractmethod
    def get_capability(self) -> ToolCapability:
        """
        Get tool capability description

        Returns:
            ToolCapability describing this tool
        """
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool

        Args:
            **kwargs: Tool parameters

        Returns:
            ToolResult with execution outcome
        """
        pass

    def validate_params(self, params: Dict[str, Any]) -> Optional[str]:
        """
        Validate tool parameters

        Args:
            params: Parameters to validate

        Returns:
            None if valid, error message if invalid
        """
        capability = self.get_capability()

        # Check required parameters
        for param in capability.required_params:
            if param not in params:
                return f"Missing required parameter: {param}"

        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get tool usage statistics"""
        avg_time = (self._total_time_ms / self._call_count
                   if self._call_count > 0 else 0.0)

        return {
            "call_count": self._call_count,
            "total_time_ms": self._total_time_ms,
            "average_time_ms": avg_time,
        }

    def reset_stats(self) -> None:
        """Reset usage statistics"""
        self._call_count = 0
        self._total_time_ms = 0.0


__all__ = [
    "ToolStatus",
    "ToolResult",
    "ToolCapability",
    "BaseTool",
]
