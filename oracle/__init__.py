"""
Oracle Layer - 语义验证层

提供 Oracle 定义、AST 节点、Oracle 检查器等核心组件。
"""

# ================================================================
# AST Nodes
# ================================================================

from oracle.ast_nodes import (
    ASTNodeType,
    ComparisonOperator,
    ASTNode,
    LiteralNode,
    ComparisonNode,
    FieldAccessNode,
    SlotReferenceNode,
    FilterValidationNode,
    LogicalAndNode,
    LogicalOrNode,
    LogicalNotNode,
    AnyNode,
    slot_ref,
    field_access,
    literal,
    compare,
    logical_and,
    logical_or,
    logical_not,
)

# ================================================================
# Base Types
# ================================================================

from oracle.base import (
    OracleCategory,
    Severity,
    Precondition,
    TriggerCondition,
    ValidationLogic,
    OracleDefinition,
    OracleResult,
    TestCase,
    ExecutionResult,
)

# ================================================================
# Oracle Checker
# ================================================================

from oracle.checker import (
    OracleChecker,
    OracleCheckerRegistry,
    register_oracle,
    get_oracle,
    get_all_oracles,
    get_oracles_by_category,
    _global_registry,
)

# ================================================================
# Built-in Checkers
# ================================================================

from oracle.checkers import (
    RangeConstraintOracle,
    EnumConstraintOracle,
    RelationalConstraintOracle,
    StatusValidationOracle,
)

# ================================================================
# Public API
# ================================================================

__all__ = [
    # AST Nodes
    "ASTNodeType",
    "ComparisonOperator",
    "ASTNode",
    "LiteralNode",
    "ComparisonNode",
    "FieldAccessNode",
    "SlotReferenceNode",
    "FilterValidationNode",
    "LogicalAndNode",
    "LogicalOrNode",
    "LogicalNotNode",
    "AnyNode",
    "slot_ref",
    "field_access",
    "literal",
    "compare",
    "logical_and",
    "logical_or",
    "logical_not",
    # Base Types
    "OracleCategory",
    "Severity",
    "Precondition",
    "TriggerCondition",
    "ValidationLogic",
    "OracleDefinition",
    "OracleResult",
    "TestCase",
    "ExecutionResult",
    # Oracle Checker
    "OracleChecker",
    "OracleCheckerRegistry",
    "register_oracle",
    "get_oracle",
    "get_all_oracles",
    "get_oracles_by_category",
    # Built-in Checkers
    "RangeConstraintOracle",
    "EnumConstraintOracle",
    "RelationalConstraintOracle",
    "StatusValidationOracle",
]
