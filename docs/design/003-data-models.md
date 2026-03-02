# 核心数据模型定义

**版本**: v1.1
**状态**: 冻结
**日期**: 2026-03-02

---

## 一、枚举类型定义

```python
from enum import Enum
from typing import Optional, List, Dict, Any, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime

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

class RuleType(Enum):
    """规则类型"""
    RELATIONAL = "relational"
    RANGE = "range"
    CONDITIONAL = "conditional"
    ENUM = "enum"
    TYPE = "type"

class Severity(Enum):
    """严重程度"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

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
    IN = "in"
    NOT_IN = "not_in"

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
```

---

## 二、Contract 层数据模型

```python
# ================================================================
# Contract 层数据模型
# ================================================================

@dataclass
class SlotDependency:
    """槽依赖"""
    slot_name: str
    reason: Optional[str] = None

@dataclass
class VersionRange:
    """版本范围"""
    min_version: str
    max_version: Optional[str] = None
    applicable_operations: Optional[List[str]] = None

@dataclass
class Evidence:
    """证据来源"""
    source: EvidenceSource
    url: Optional[str] = None
    document_path: Optional[str] = None
    excerpt: Optional[str] = None
    discovered_at: Optional[datetime] = None
    discovered_by: str = "human"
    reviewed_by: Optional[str] = None
    review_status: ReviewStatus = ReviewStatus.PENDING
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None

@dataclass
class Slot:
    """语义槽基类"""
    slot_name: str
    description: str
    type: SlotType
    scope: SlotScope
    depends_on: List[SlotDependency] = field(default_factory=list)
    rules: List['Rule'] = field(default_factory=list)

@dataclass
class CoreSlot(Slot):
    """核心语义槽"""
    constraints: Optional['SlotConstraints'] = None

@dataclass
class ExtendedSlot(Slot):
    """扩展语义槽"""
    version_range: Optional[VersionRange] = None
    evidence: Optional[Evidence] = None

@dataclass
class SlotConstraints:
    """槽约束"""
    range: Optional['RangeConstraint'] = None
    enum: Optional['EnumConstraint'] = None
    vector: Optional['VectorConstraint'] = None

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
class VectorConstraint:
    """向量约束"""
    element_type: str
    dimension_slot: str

@dataclass
class Rule:
    """规则基类"""
    rule_id: str
    type: RuleType
    severity: Severity
    enabled: bool
    priority: int = 100

@dataclass
class RelationalRule(Rule):
    """关系规则"""
    operator: ComparisonOperator
    reference_slot: str
    error_message: str

@dataclass
class RangeRule(Rule):
    """范围规则"""
    min_value: Any
    max_value: Any
    inclusive_min: bool
    inclusive_max: bool

@dataclass
class ConditionalRule(Rule):
    """条件规则"""
    condition: 'ASTNode'
    then_rules: List[Rule]
    else_rules: List[Rule] = field(default_factory=list)

@dataclass
class EnumRule(Rule):
    """枚举规则"""
    allowed_values: List[Any]
    strict: bool = True

@dataclass
class Contract:
    """契约"""
    database_name: str
    version: str
    core_slots: List[CoreSlot] = field(default_factory=list)
    extended_slots: List[ExtendedSlot] = field(default_factory=list)

    def get_slot(self, slot_name: str, scope: Optional[SlotScope] = None) -> Optional[Slot]:
        """获取槽"""
        slots = self.core_slots + self.extended_slots
        for slot in slots:
            if slot.slot_name == slot_name:
                if scope is None or slot.scope == scope:
                    return slot
        return None

    def get_all_slots(self) -> List[Slot]:
        """获取所有槽"""
        return list(self.core_slots) + list(self.extended_slots)
```

---

## 三、Oracle 层数据模型

```python
# ================================================================
# Oracle 层数据模型
# ================================================================

@dataclass
class ASTNode:
    """AST 节点基类"""
    node_type: ASTNodeType

@dataclass
class ComparisonNode(ASTNode):
    """比较节点"""
    node_type: ASTNodeType = ASTNodeType.COMPARISON
    left: 'ASTNode'
    operator: ComparisonOperator
    right: 'ASTNode'

@dataclass
class FieldAccessNode(ASTNode):
    """字段访问节点"""
    node_type: ASTNodeType = ASTNodeType.FIELD_ACCESS
    object_path: List[str]

@dataclass
class SlotReferenceNode(ASTNode):
    """语义槽引用节点"""
    node_type: ASTNodeType = ASTNodeType.SLOT_REFERENCE
    slot_name: str

@dataclass
class FilterValidationNode(ASTNode):
    """过滤验证节点"""
    node_type: ASTNodeType = ASTNodeType.FILTER_VALIDATION
    filter_reference: str
    result_field: str

@dataclass
class LogicalAndNode(ASTNode):
    """逻辑与节点"""
    node_type: ASTNodeType = ASTNodeType.LOGICAL_AND
    operands: List[ASTNode]

@dataclass
class LogicalOrNode(ASTNode):
    """逻辑或节点"""
    node_type: ASTNodeType = ASTNodeType.LOGICAL_OR
    operands: List[ASTNode]

@dataclass
class LogicalNotNode(ASTNode):
    """逻辑非节点"""
    node_type: ASTNodeType = ASTNodeType.LOGICAL_NOT
    operand: ASTNode

@dataclass
class Precondition:
    """前置条件"""
    name: str
    condition: str  # 可转换为 AST

@dataclass
class TriggerCondition:
    """Oracle 触发条件"""
    required_operations: List[str]
    required_slots: Dict[str, Any]
    preconditions: List[Precondition]
    exclude_conditions: List[ASTNode]

@dataclass
class ValidationLogic:
    """验证逻辑"""
    root: ASTNode

@dataclass
class OracleDefinition:
    """Oracle 定义"""
    oracle_id: str
    name: str
    category: OracleCategory
    description: str
    trigger_condition: TriggerCondition
    validation_logic: ValidationLogic
    severity: Severity
    evidence_required: bool
```

---

## 四、Adapter 层数据模型

```python
# ================================================================
# Adapter 层数据模型
# ================================================================

@dataclass
class Capabilities:
    """数据库能力声明"""
    supported_operations: List[str]
    supported_vector_types: List[str]
    supported_index_types: List[str]
    concurrent_operations: bool
    max_concurrent_requests: Optional[int]
    transaction_support: bool
    distributed: bool
```

---

## 五、RuleEngine 层数据模型

```python
# ================================================================
# RuleEngine 层数据模型
# ================================================================

@dataclass
class EvaluationRecord:
    """评估记录"""
    value: Any
    passed: Optional[bool]
    timestamp: datetime

@dataclass
class CoverageReport:
    """覆盖统计报告"""
    session_id: str
    created_at: datetime
    slot_coverage: Dict[str, float]
    boundary_coverage: float
    total_evaluations: int
    unique_values_tested: Dict[str, int]

@dataclass
class ThreeValuedEvaluationTrace:
    """三值逻辑评估追踪"""
    final_result: Optional[bool]
    false_sources: List[str]
    none_sources: List[str]
    evaluation_path: str

@dataclass
class SingleRuleResult:
    """单条规则评估结果"""
    rule_id: str
    passed: Optional[bool]
    reason: Optional[str]
    violated_slot: Optional[str]

@dataclass
class SlotRuleResult:
    """槽规则评估结果"""
    slot_name: str
    results: List[SingleRuleResult]
    passed: Optional[bool]

@dataclass
class RuleEvaluationResult:
    """规则评估结果"""
    results: List[SlotRuleResult]
    overall_passed: Optional[bool]
    coverage_report: CoverageReport
    trace: ThreeValuedEvaluationTrace
```

---

## 六、StateModel 层数据模型

```python
# ================================================================
# StateModel 层数据模型
# ================================================================

@dataclass
class StateIdentifier:
    """状态标识符"""
    scope: SlotScope
    name: str

    def __hash__(self):
        return hash((self.scope.value, self.name))

@dataclass
class StabilityConfig:
    """状态稳定配置"""
    poll_interval: float = 0.5
    max_wait_time: float = 30.0
    stable_duration: float = 2.0
    stable_states: Set[str] = field(default_factory=lambda: {
        "ready", "empty", "has_data", "active", "in_sync", "not_exist"
    })
    stable_predicate: Optional[Callable[[str], bool]] = None

@dataclass
class StateStabilityResult:
    """状态稳定结果"""
    stable_state: str
    elapsed_seconds: float
    is_timeout: bool
    history: List[tuple[datetime, str]]
    timeout_reason: Optional[str] = None

@dataclass
class TransitionLegalityResult:
    """状态转移合法性结果"""
    is_legal: Optional[bool]
    from_state: str
    to_state: str
    reason: str
    note: Optional[str] = None
```

---

## 七、Bug Type Engine 数据模型

```python
# ================================================================
# Bug Type Engine 数据模型
# ================================================================

@dataclass
class ConfidenceFactors:
    """置信度影响因子"""
    base_confidence: float = 1.0
    environment_stability_score: Optional[float] = None
    infra_suspect_weight: Optional[float] = None
    concurrent_load_factor: Optional[float] = None
    retry_consistency: Optional[float] = None

    def compute_final_confidence(self) -> float:
        return self.base_confidence

@dataclass
class BugTypeDerivation:
    """Bug 类型推导结果"""
    bug_type: Optional[BugType]
    reason: str
    confidence: float
    decision_path: str
    violated_rules: Optional[List[str]] = None
    confidence_factors: Optional[ConfidenceFactors] = None
    derivation_metadata: Optional[Dict[str, Any]] = None
```

---

## 八、执行层数据模型

```python
# ================================================================
# 执行层数据模型
# ================================================================

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
    """门禁结果"""
    passed: bool
    reason: str
    coverage_report: Optional[CoverageReport] = None

@dataclass
class ExecutionContext:
    """执行上下文"""
    adapter: 'BaseAdapter'
    profile: Optional['BaseProfilePlugin']
    state_model: 'StateModel'
    test_case: TestCase

@dataclass
class TestExecutionResult:
    """测试执行结果"""
    status: ExecutionStatus
    error: Optional[Exception]
    result_data: Optional[Any]
    elapsed_seconds: float
    gate_result: GateResult
    rule_evaluation_result: Optional[RuleEvaluationResult]
    bug_type_derivation: Optional[BugTypeDerivation]
```
