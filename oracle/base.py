"""
Oracle Base Types

定义 Oracle 层的核心数据类型。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from oracle.ast_nodes import ASTNode, AnyNode


# ================================================================
# Enums
# ================================================================

class OracleCategory(Enum):
    """Oracle 类别"""
    MONOTONICITY = "monotonicity"
    CONSISTENCY = "consistency"
    CORRECTNESS = "correctness"
    PERFORMANCE = "performance"
    CUSTOM = "custom"


class Severity(Enum):
    """严重性级别"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ================================================================
# Core Types
# ================================================================

@dataclass(frozen=True)
class Precondition:
    """前置条件

    Oracle 检查前需要满足的条件
    """
    name: str
    condition: str  # 可转换为 AST 的条件表达式


@dataclass(frozen=True)
class TriggerCondition:
    """Oracle 触发条件

    定义 Oracle 何时应该被触发
    """
    required_operations: List[str] = field(default_factory=list)
    required_slots: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[Precondition] = field(default_factory=list)
    exclude_conditions: List[AnyNode] = field(default_factory=list)


@dataclass(frozen=True)
class ValidationLogic:
    """验证逻辑

    Oracle 的核心验证逻辑，以 AST 根节点表示
    """
    root: ASTNode


@dataclass(frozen=True)
class OracleDefinition:
    """Oracle 定义

    完整定义一个 Oracle 的所有信息
    """
    oracle_id: str
    name: str
    category: OracleCategory
    description: str
    trigger_condition: TriggerCondition
    validation_logic: ValidationLogic
    severity: Severity
    evidence_required: bool = False


@dataclass
class OracleResult:
    """Oracle 检查结果

    Oracle 检查的执行结果
    """
    oracle_id: str
    passed: bool
    details: str
    violated_slots: Optional[List[str]] = None
    evidence: Optional[Dict[str, Any]] = None
    location: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于机器可读输出）

        Returns:
            Dict[str, Any]: 结果的字典表示
        """
        return {
            "oracle_id": self.oracle_id,
            "passed": self.passed,
            "details": self.details,
            "violated_slots": self.violated_slots,
            "evidence": self.evidence,
            "location": self.location,
        }


# ================================================================
# TestCase and ExecutionResult (simplified for Phase 3)
# ================================================================

@dataclass
class TestCase:
    """测试用例（简化版）

    Phase 3: 简化定义，Phase 4 会扩展
    """
    test_id: str
    operation: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    slot_values: Dict[str, Any] = field(default_factory=dict)  # Contract 槽的值


@dataclass
class ExecutionResult:
    """执行结果（简化版）

    Phase 3: 简化定义，Phase 4 会扩展
    """
    status: str  # "SUCCESS" or "FAILURE"
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    rows_affected: Optional[int] = None
    execution_time: Optional[float] = None


__all__ = [
    # Enums
    "OracleCategory",
    "Severity",
    # Core Types
    "Precondition",
    "TriggerCondition",
    "ValidationLogic",
    "OracleDefinition",
    "OracleResult",
    # Test Types
    "TestCase",
    "ExecutionResult",
]
