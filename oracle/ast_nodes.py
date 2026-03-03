"""
Oracle AST Nodes

定义 Oracle 验证逻辑使用的 AST 节点类型。
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Union, Optional
from enum import Enum


# ================================================================
# AST Node Types
# ================================================================

class ASTNodeType(Enum):
    """AST 节点类型"""
    COMPARISON = "comparison"
    FIELD_ACCESS = "field_access"
    SLOT_REFERENCE = "slot_reference"
    FILTER_VALIDATION = "filter_validation"
    LOGICAL_AND = "logical_and"
    LOGICAL_OR = "logical_or"
    LOGICAL_NOT = "logical_not"
    LITERAL = "literal"


class ComparisonOperator(Enum):
    """比较操作符"""
    EQ = "=="
    NE = "!="
    GT = ">"
    GE = ">="
    LT = "<"
    LE = "<="
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"


# ================================================================
# AST Node Classes
# ================================================================

@dataclass(frozen=True)
class ASTNode:
    """AST 节点基类"""
    pass


@dataclass(frozen=True)
class LiteralNode(ASTNode):
    """字面量节点"""
    value: Any = None
    node_type: ASTNodeType = ASTNodeType.LITERAL


@dataclass(frozen=True)
class ComparisonNode(ASTNode):
    """比较节点

    Example:
        left: slot_value
        operator: GT
        right: 100
    """
    left: 'ASTNode'
    operator: ComparisonOperator
    right: 'ASTNode'
    node_type: ASTNodeType = ASTNodeType.COMPARISON


@dataclass(frozen=True)
class FieldAccessNode(ASTNode):
    """字段访问节点

    用于访问结果对象的字段，如:
    - result.status
    - result.rows[0].id
    - result.error.message

    Example:
        object_path: ["result", "status"]
        object_path: ["result", "error", "message"]
    """
    object_path: List[str]
    node_type: ASTNodeType = ASTNodeType.FIELD_ACCESS


@dataclass(frozen=True)
class SlotReferenceNode(ASTNode):
    """语义槽引用节点

    用于引用 Contract 中的语义槽值

    Example:
        slot_name: "dimension"
        scope: "COLLECTION"
    """
    slot_name: str
    scope: Optional[str] = None  # None 表示自动推断
    node_type: ASTNodeType = ASTNodeType.SLOT_REFERENCE


@dataclass(frozen=True)
class FilterValidationNode(ASTNode):
    """过滤验证节点

    用于验证过滤条件是否被满足

    Example:
        filter_reference: "result.filter"
        result_field: "result.count"
    """
    filter_reference: str  # 引用 test_case.filters 中的 filter
    result_field: str     # 引用 result 中的字段路径
    node_type: ASTNodeType = ASTNodeType.FILTER_VALIDATION


@dataclass(frozen=True)
class LogicalAndNode(ASTNode):
    """逻辑与节点

    Example:
        operands: [condition1, condition2]
    """
    operands: List['ASTNode']
    node_type: ASTNodeType = ASTNodeType.LOGICAL_AND


@dataclass(frozen=True)
class LogicalOrNode(ASTNode):
    """逻辑或节点

    Example:
        operands: [condition1, condition2]
    """
    operands: List['ASTNode']
    node_type: ASTNodeType = ASTNodeType.LOGICAL_OR


@dataclass(frozen=True)
class LogicalNotNode(ASTNode):
    """逻辑非节点

    Example:
        operand: condition
    """
    operand: 'ASTNode'
    node_type: ASTNodeType = ASTNodeType.LOGICAL_NOT


# ================================================================
# Composite Nodes (for convenience)
# ================================================================

# Type alias for any AST node
AnyNode = Union[
    LiteralNode,
    ComparisonNode,
    FieldAccessNode,
    SlotReferenceNode,
    FilterValidationNode,
    LogicalAndNode,
    LogicalOrNode,
    LogicalNotNode,
]


# ================================================================
# Helper Functions
# ================================================================

def slot_ref(slot_name: str, scope: Optional[str] = None) -> SlotReferenceNode:
    """创建语义槽引用节点的便捷函数

    Args:
        slot_name: 槽名称
        scope: 作用域（可选）

    Returns:
        SlotReferenceNode: 槽引用节点
    """
    return SlotReferenceNode(
        slot_name=slot_name,
        scope=scope
    )


def field_access(*path: str) -> FieldAccessNode:
    """创建字段访问节点的便捷函数

    Args:
        *path: 字段路径，如 "result", "status"

    Returns:
        FieldAccessNode: 字段访问节点

    Example:
        field_access("result", "status") → result.status
        field_access("result", "error", "message") → result.error.message
    """
    return FieldAccessNode(object_path=list(path))


def literal(value: Any) -> LiteralNode:
    """创建字面量节点的便捷函数

    Args:
        value: 字面量值

    Returns:
        LiteralNode: 字面量节点
    """
    return LiteralNode(value=value)


def compare(left: AnyNode, op: ComparisonOperator, right: AnyNode) -> ComparisonNode:
    """创建比较节点的便捷函数

    Args:
        left: 左操作数
        op: 比较操作符
        right: 右操作数

    Returns:
        ComparisonNode: 比较节点
    """
    return ComparisonNode(
        left=left,
        operator=op,
        right=right
    )


def logical_and(*operands: AnyNode) -> LogicalAndNode:
    """创建逻辑与节点的便捷函数

    Args:
        *operands: 操作数列表

    Returns:
        LogicalAndNode: 逻辑与节点
    """
    return LogicalAndNode(operands=list(operands))


def logical_or(*operands: AnyNode) -> LogicalOrNode:
    """创建逻辑或节点的便捷函数

    Args:
        *operands: 操作数列表

    Returns:
        LogicalOrNode: 逻辑或节点
    """
    return LogicalOrNode(operands=list(operands))


def logical_not(operand: AnyNode) -> LogicalNotNode:
    """创建逻辑非节点的便捷函数

    Args:
        operand: 操作数

    Returns:
        LogicalNotNode: 逻辑非节点
    """
    return LogicalNotNode(operand=operand)


__all__ = [
    # Enums
    "ASTNodeType",
    "ComparisonOperator",
    # Node Classes
    "ASTNode",
    "LiteralNode",
    "ComparisonNode",
    "FieldAccessNode",
    "SlotReferenceNode",
    "FilterValidationNode",
    "LogicalAndNode",
    "LogicalOrNode",
    "LogicalNotNode",
    # Type Alias
    "AnyNode",
    # Helper Functions
    "slot_ref",
    "field_access",
    "literal",
    "compare",
    "logical_and",
    "logical_or",
    "logical_not",
]
