"""
Contract DSL 语义层类型定义

定义语义验证和标准化过程中使用的类型系统。
包括：SlotKey、AST 节点、NormalizedConstraints、NormalizedRule 等。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from enum import Enum


# ================================================================
# SlotKey: 替代裸 Tuple
# ================================================================

@dataclass(frozen=True)
class SlotKey:
    """Slot 唯一标识符

    替代裸 Tuple[(scope, slot_name)]，提供类型安全和可读性。
    """
    scope: str
    slot_name: str

    def __str__(self) -> str:
        return f"{self.scope}.{self.slot_name}"

    def __hash__(self) -> int:
        return hash((self.scope, self.slot_name))

    def __eq__(self, other) -> object:
        if not isinstance(other, SlotKey):
            return NotImplemented
        return self.scope == other.scope and self.slot_name == other.slot_name

    @classmethod
    def from_str(cls, s: str) -> 'SlotKey':
        """从字符串解析 SlotKey

        Args:
            s: 格式为 "scope.slot_name" 的字符串

        Returns:
            SlotKey: 解析后的 SlotKey

        Raises:
            ValueError: 字符串格式无效
        """
        parts = s.split('.', 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid SlotKey string: '{s}'. Expected format: 'scope.slot_name'")
        return cls(scope=parts[0], slot_name=parts[1])

    @classmethod
    def from_string(cls, s: str) -> 'SlotKey':
        """from_string 别名，与 from_str 功能相同"""
        return cls.from_str(s)


# ================================================================
# AST 节点类型（条件规则使用）
# ================================================================

class ConditionNodeType(Enum):
    """条件节点类型"""
    OPERATION_EQUALS = "operation_equals"
    SLOT_EQUALS = "slot_equals"
    SLOT_IN_RANGE = "slot_in_range"
    AND = "and"
    OR = "or"
    NOT = "not"


@dataclass(frozen=True)
class OperationEqualsNode:
    """operation_equals 条件节点"""
    operation: str


@dataclass(frozen=True)
class SlotReference:
    """槽引用

    用于明确指定 slot 的 scope 和 name。
    """
    scope: str
    slot_name: str
    reason: Optional[str] = None

    def __str__(self) -> str:
        if self.reason:
            return f"{self.scope}.{self.slot_name} ({self.reason})"
        return f"{self.scope}.{self.slot_name}"

    @property
    def key(self) -> SlotKey:
        """转换为 SlotKey"""
        return SlotKey(scope=self.scope, slot_name=self.slot_name)


@dataclass(frozen=True)
class SlotEqualsNode:
    """slot_equals 条件节点"""
    slot: SlotReference  # 结构化引用，非 slot_name: str
    value: Any


@dataclass(frozen=True)
class SlotInRangeNode:
    """slot_in_range 条件节点"""
    slot: SlotReference  # 结构化引用
    min_value: Any
    max_value: Any


@dataclass(frozen=True)
class AndNode:
    """and 条件节点"""
    operands: List['ConditionNode']


@dataclass(frozen=True)
class OrNode:
    """or 条件节点"""
    operands: List['ConditionNode']


@dataclass(frozen=True)
class NotNode:
    """not 条件节点"""
    operand: 'ConditionNode'


# 条件节点的 Union 类型
ConditionNode = Union[
    OperationEqualsNode,
    SlotEqualsNode,
    SlotInRangeNode,
    AndNode,
    OrNode,
    NotNode,
]


# ================================================================
# 标准化约束类型
# ================================================================

@dataclass(frozen=True)
class NormalizedRangeConstraints:
    """标准化范围约束"""
    min: Optional[Union[int, float]]
    max: Optional[Union[int, float]]
    inclusive: bool


@dataclass(frozen=True)
class NormalizedEnumConstraints:
    """标准化枚举约束"""
    values: List[Any]
    strict: bool


@dataclass(frozen=True)
class NormalizedVectorConstraints:
    """标准化向量约束"""
    element_type: Optional[str]
    dimension_slot: Optional[str]


@dataclass(frozen=True)
class NormalizedConstraints:
    """标准化约束（类型安全，聚合所有约束类型）"""
    range: Optional[NormalizedRangeConstraints] = None
    enum: Optional[NormalizedEnumConstraints] = None
    vector: Optional[NormalizedVectorConstraints] = None


# ================================================================
# 标准化规则类型（Union 设计）
# ================================================================

@dataclass(frozen=True)
class NormalizedRelationalRule:
    """标准化关系规则"""
    operator: str
    reference_slot: SlotReference  # 引用已解析为 SlotReference
    error_message: str


@dataclass(frozen=True)
class NormalizedRangeRule:
    """标准化范围规则"""
    min_value: Any
    max_value: Any
    inclusive_min: bool
    inclusive_max: bool


@dataclass(frozen=True)
class NormalizedEnumRule:
    """标准化枚举规则"""
    allowed_values: List[Any]
    strict: bool


@dataclass(frozen=True)
class NormalizedConditionalRule:
    """标准化条件规则

    注意：即使 Phase 2 "不评估"，也必须完整保留 then/else 的结构化内容。
    这不是"改变业务含义"，而是"完整保留"。
    """
    condition: ConditionNode  # AST 节点，非 Dict
    then_rules: List['NormalizedRule']  # 递归定义，不能为空占位
    else_rules: Optional[List['NormalizedRule']] = None  # 递归定义


# 规则体的 Union 类型
NormalizedRuleBody = Union[
    NormalizedRelationalRule,
    NormalizedRangeRule,
    NormalizedEnumRule,
    NormalizedConditionalRule,
]


@dataclass(frozen=True)
class NormalizedRule:
    """标准化规则（Union body 设计）

    根据 type 字段，body 是对应的 Normalized*Rule 类型。
    """
    rule_id: str
    type: str
    severity: str
    enabled: bool
    priority: int
    body: NormalizedRuleBody  # Union 类型

    @property
    def is_relational(self) -> bool:
        return isinstance(self.body, NormalizedRelationalRule)

    @property
    def is_range(self) -> bool:
        return isinstance(self.body, NormalizedRangeRule)

    @property
    def is_enum(self) -> bool:
        return isinstance(self.body, NormalizedEnumRule)

    @property
    def is_conditional(self) -> bool:
        return isinstance(self.body, NormalizedConditionalRule)

    def get_active_rule(self) -> NormalizedRuleBody:
        """获取当前规则类型的实际内容"""
        return self.body
