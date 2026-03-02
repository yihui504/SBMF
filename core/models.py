"""
Core data models for Semantic Bug Mining Framework.

This module defines all enum types used throughout the framework.
Following the design specification in docs/design/003-data-models.md
"""

from enum import Enum


# ================================================================
# 基础枚举
# ================================================================

class SlotType(Enum):
    """槽类型"""
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    ENUM = "enum"
    BOOLEAN = "boolean"
    VECTOR = "vector"


class SlotScope(Enum):
    """槽作用域"""
    DATABASE = "DATABASE"
    COLLECTION = "COLLECTION"
    PARTITION = "PARTITION"
    INDEX = "INDEX"
    REPLICA = "REPLICA"


class BugType(Enum):
    """Bug 类型"""
    TYPE_1 = "TYPE_1"  # 非法操作成功
    TYPE_2 = "TYPE_2"  # 错误不可诊断
    TYPE_3 = "TYPE_3"  # 合法操作失败
    TYPE_4 = "TYPE_4"  # 语义违背


class ExecutionStatus(Enum):
    """执行状态"""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    CRASH = "CRASH"
    TIMEOUT = "TIMEOUT"
    PRECONDITION_FAILED = "PRECONDITION_FAILED"


class Severity(Enum):
    """严重程度"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ErrorCategory(Enum):
    """错误分类"""
    INFRA_SUSPECT = "infra_suspect"
    PRODUCT_SUSPECT = "product_suspect"
    PRECONDITION_FAILED = "precondition_failed"


class OracleCategory(Enum):
    """Oracle 类别"""
    MONOTONICITY = "monotonicity"
    CONSISTENCY = "consistency"
    CORRECTNESS = "correctness"
    PERFORMANCE = "performance"


class ASTNodeType(Enum):
    """AST 节点类型"""
    COMPARISON = "comparison"
    FIELD_ACCESS = "field_access"
    SLOT_REFERENCE = "slot_reference"
    FILTER_VALIDATION = "filter_validation"
    LOGICAL_AND = "logical_and"
    LOGICAL_OR = "logical_or"
    LOGICAL_NOT = "logical_not"


class ComparisonOperator(Enum):
    """比较操作符"""
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="
    EQUAL = "=="
    NOT_EQUAL = "!="


class EvidenceSource(Enum):
    """证据来源"""
    OFFICIAL_DOCUMENTATION = "official_documentation"
    CODE_ANALYSIS = "code_analysis"
    LLM_DISCOVERED = "llm_discovered"
    MANUAL = "manual"


class ReviewStatus(Enum):
    """审核状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RuleType(Enum):
    """规则类型"""
    RELATIONAL = "relational"
    RANGE = "range"
    CONDITIONAL = "conditional"
    ENUM = "enum"


# ================================================================
# 数据模型
# ================================================================

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set, Callable


@dataclass
class SlotDependency:
    """槽依赖关系"""
    slot_name: str
    reason: Optional[str] = None


@dataclass
class Slot:
    """槽定义"""
    slot_name: str
    description: str
    type: SlotType
    scope: SlotScope
    depends_on: List[SlotDependency] = field(default_factory=list)


@dataclass
class CoreSlot(Slot):
    """核心槽定义"""
    constraints: Optional['SlotConstraints'] = None


@dataclass
class SlotConstraints:
    """槽约束"""
    range: Optional['RangeConstraint'] = None
    enum: Optional['EnumConstraint'] = None


@dataclass
class RangeConstraint:
    """范围约束"""
    min: Optional[float] = None
    max: Optional[float] = None
    inclusive: bool = True


@dataclass
class EnumConstraint:
    """枚举约束"""
    values: List[Any]


@dataclass
class Rule:
    """规则定义"""
    rule_id: str
    type: RuleType
    severity: Severity
    enabled: bool
    priority: int


@dataclass
class RelationalRule(Rule):
    """关系规则"""
    operator: ComparisonOperator
    reference_slot: str
    error_message: str


@dataclass
class Contract:
    """契约定义"""
    database_name: str
    version: str
    core_slots: List[CoreSlot] = field(default_factory=list)


@dataclass
class TestCase:
    """测试用例"""
    test_id: str
    operation: str
    slot_values: Dict[str, Any]
    raw_parameters: Dict[str, Any]
    is_legal: bool
    scope: SlotScope

    def get_slot_value(self, slot_name: str) -> Optional[Any]:
        """获取指定槽的值"""
        return self.slot_values.get(slot_name)


@dataclass
class ExecutionResult:
    """执行结果"""
    status: ExecutionStatus
    result_data: Optional[Any]
    error: Optional[Exception]
    elapsed_seconds: float


@dataclass
class GateResult:
    """门控结果"""
    passed: bool
    reason: str
    coverage_report: Optional['CoverageReport'] = None


@dataclass
class TestExecutionResult:
    """测试执行完整结果"""
    status: ExecutionStatus
    error: Optional[Exception]
    result_data: Optional[Any]
    elapsed_seconds: float
    gate_result: Optional['GateResult'] = None
    rule_evaluation_result: Optional['RuleEvaluationResult'] = None
    bug_type_derivation: Optional['BugTypeDerivation'] = None
