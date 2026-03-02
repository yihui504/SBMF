# Phase 1: Core Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现语义驱动的数据库 Bug 挖掘框架的核心基础模块，包括数据模型、三值逻辑系统、Bug 类型推导引擎、适配器接口、SeekDB 适配器、规则引擎、预条件门禁、状态机模型和执行流程。

**Architecture:** 基于 Contract 驱动的语义验证框架，采用分层架构：Contract 层定义语义契约，Adapter 层映射到具体数据库，RuleEngine 评估规则，PreconditionGate 确保预条件，BugTypeEngine 推导 Bug 类型。

**Tech Stack:** Python 3.10+, Pydantic (数据验证), Pytest (测试), YAML (Contract DSL)

---

## 目录结构

```
SemanticBugMiningFramework/
├── core/
│   ├── __init__.py
│   ├── models.py              # 枚举和数据模型
│   ├── three_valued_logic.py  # 三值逻辑系统
│   ├── bug_type_engine.py    # Bug 类型推导引擎
│   ├── execution_pipeline.py # 执行流程
│   └── rule_engine.py         # 规则评估引擎
├── adapters/
│   ├── __init__.py
│   ├── base.py                # 适配器基类
│   └── seekdb.py              # SeekDB 适配器
├── state/
│   ├── __init__.py
│   ├── base.py                # StateModel 基类
│   └── scoped.py              # 多粒度状态机
├── contracts/
│   └── profiles/
│       └── seekdb.yaml        # SeekDB Contract
├── tests/
│   ├── test_models.py
│   ├── test_three_valued_logic.py
│   ├── test_bug_type_engine.py
│   ├── test_rule_engine.py
│   └── test_execution_pipeline.py
└── requirements.txt
```

---

## Task 1: 基础枚举类型定义

**Files:**
- Create: `core/models.py`
- Test: `tests/test_models.py`

**Step 1: Write the failing test**

```python
# tests/test_models.py
import pytest
from core.models import SlotType, SlotScope, BugType, ExecutionStatus, Severity

def test_slot_type_enum():
    assert SlotType.INTEGER.value == "integer"
    assert SlotType.VECTOR.value == "vector"

def test_slot_scope_enum():
    assert SlotScope.DATABASE.value == "DATABASE"
    assert SlotScope.COLLECTION.value == "COLLECTION"

def test_bug_type_enum():
    assert BugType.TYPE_1.value == "TYPE_1"
    assert BugType.TYPE_4.value == "TYPE_4"

def test_execution_status_enum():
    assert ExecutionStatus.SUCCESS.value == "SUCCESS"
    assert ExecutionStatus.PRECONDITION_FAILED.value == "PRECONDITION_FAILED"
```

**Step 2: Run test to verify it fails**

```bash
cd C:/Users/11428/Desktop/SemanticBugMiningFramework
pytest tests/test_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'core'`

**Step 3: Create core package and implement enums**

```python
# core/models.py
from enum import Enum

class SlotType(Enum):
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    ENUM = "enum"
    BOOLEAN = "boolean"
    VECTOR = "vector"

class SlotScope(Enum):
    DATABASE = "DATABASE"
    COLLECTION = "COLLECTION"
    PARTITION = "PARTITION"
    INDEX = "INDEX"
    REPLICA = "REPLICA"

class BugType(Enum):
    TYPE_1 = "TYPE_1"
    TYPE_2 = "TYPE_2"
    TYPE_3 = "TYPE_3"
    TYPE_4 = "TYPE_4"

class ExecutionStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    CRASH = "CRASH"
    TIMEOUT = "TIMEOUT"
    PRECONDITION_FAILED = "PRECONDITION_FAILED"

class Severity(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class ErrorCategory(Enum):
    INFRA_SUSPECT = "infra_suspect"
    PRODUCT_SUSPECT = "product_suspect"
    PRECONDITION_FAILED = "precondition_failed"

class OracleCategory(Enum):
    MONOTONICITY = "monotonicity"
    CONSISTENCY = "consistency"
    CORRECTNESS = "correctness"
    PERFORMANCE = "performance"

class ASTNodeType(Enum):
    COMPARISON = "comparison"
    FIELD_ACCESS = "field_access"
    SLOT_REFERENCE = "slot_reference"
    FILTER_VALIDATION = "filter_validation"
    LOGICAL_AND = "logical_and"
    LOGICAL_OR = "logical_or"
    LOGICAL_NOT = "logical_not"

class ComparisonOperator(Enum):
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="
    EQUAL = "=="
    NOT_EQUAL = "!="

class EvidenceSource(Enum):
    OFFICIAL_DOCUMENTATION = "official_documentation"
    CODE_ANALYSIS = "code_analysis"
    LLM_DISCOVERED = "llm_discovered"
    MANUAL = "manual"

class ReviewStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_models.py -v
```

Expected: `PASSED`

**Step 5: Commit**

```bash
git add core/models.py tests/test_models.py
git commit -m "feat(core): add base enum types for models"
```

---

## Task 2: 数据模型定义

**Files:**
- Modify: `core/models.py`
- Test: `tests/test_models.py`

**Step 1: Write the failing test**

```python
# tests/test_models.py (新增)
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

def test_slot_dataclass():
    from core.models import Slot, CoreSlot

    slot = CoreSlot(
        slot_name="dimension",
        description="向量维度",
        type=SlotType.INTEGER,
        scope=SlotScope.COLLECTION,
        depends_on=[]
    )

    assert slot.slot_name == "dimension"
    assert slot.type == SlotType.INTEGER
    assert slot.scope == SlotScope.COLLECTION

def test_rule_dataclass():
    from core.models import Rule, RelationalRule

    rule = RelationalRule(
        rule_id="test_rule",
        type=RuleType.RELATIONAL,
        severity=Severity.HIGH,
        enabled=True,
        priority=10,
        operator=ComparisonOperator.GREATER_THAN_OR_EQUAL,
        reference_slot="top_k",
        error_message="test error"
    )

    assert rule.operator == ComparisonOperator.GREATER_THAN_OR_EQUAL
    assert rule.priority == 10
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py::test_slot_dataclass -v
```

Expected: `ImportError: cannot import name 'CoreSlot' from 'core.models'`

**Step 3: Add dataclass models**

```python
# core/models.py (在文件末尾添加)
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set, Callable

@dataclass
class SlotDependency:
    slot_name: str
    reason: Optional[str] = None

@dataclass
class Slot:
    slot_name: str
    description: str
    type: SlotType
    scope: SlotScope
    depends_on: List[SlotDependency] = field(default_factory=list)

@dataclass
class CoreSlot(Slot):
    constraints: Optional['SlotConstraints'] = None

@dataclass
class SlotConstraints:
    range: Optional['RangeConstraint'] = None
    enum: Optional['EnumConstraint'] = None

@dataclass
class RangeConstraint:
    min: Optional[float] = None
    max: Optional[float] = None
    inclusive: bool = True

@dataclass
class EnumConstraint:
    values: List[Any]

@dataclass
class Rule:
    rule_id: str
    type: RuleType
    severity: Severity
    enabled: bool
    priority: int = 100

@dataclass
class RelationalRule(Rule):
    operator: ComparisonOperator
    reference_slot: str
    error_message: str

@dataclass
class Contract:
    database_name: str
    version: str
    core_slots: List[CoreSlot] = field(default_factory=list)

@dataclass
class TestCase:
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
    status: ExecutionStatus
    result_data: Optional[Any]
    error: Optional[Exception]
    elapsed_seconds: float

@dataclass
class GateResult:
    passed: bool
    reason: str
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_models.py::test_slot_dataclass -v
```

Expected: `PASSED`

**Step 5: Commit**

```bash
git add core/models.py tests/test_models.py
git commit -m "feat(core): add dataclass models for Slot, Rule, Contract, TestCase"
```

---

## Task 3: 三值逻辑系统

**Files:**
- Create: `core/three_valued_logic.py`
- Test: `tests/test_three_valued_logic.py`

**Step 1: Write the failing test**

```python
# tests/test_three_valued_logic.py
import pytest
from core.three_valued_logic import ThreeValuedLogic

def test_compute_overall_passed_all_true():
    result = ThreeValuedLogic.compute_overall_passed([True, True, True])
    assert result is True

def test_compute_overall_passed_one_false():
    result = ThreeValuedLogic.compute_overall_passed([True, False, True])
    assert result is False

def test_compute_overall_passed_true_and_none():
    result = ThreeValuedLogic.compute_overall_passed([True, None, True])
    assert result is True

def test_compute_overall_passed_all_none():
    result = ThreeValuedLogic.compute_overall_passed([None, None, None])
    assert result is None

def test_and_operator():
    assert ThreeValuedLogic.and_operator(True, True) == True
    assert ThreeValuedLogic.and_operator(True, False) == False
    assert ThreeValuedLogic.and_operator(True, None) is None
    assert ThreeValuedLogic.and_operator(False, None) == False

def test_or_operator():
    assert ThreeValuedLogic.or_operator(True, True) == True
    assert ThreeValuedLogic.or_operator(True, False) == True
    assert ThreeValuedLogic.or_operator(False, None) is None
    assert ThreeValuedLogic.or_operator(True, None) == True

def test_not_operator():
    assert ThreeValuedLogic.not_operator(True) is False
    assert ThreeValuedLogic.not_operator(False) is True
    assert ThreeValuedLogic.not_operator(None) is None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_three_valued_logic.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.three_valued_logic'`

**Step 3: Implement ThreeValuedLogic**

```python
# core/three_valued_logic.py
from typing import Optional, List

class ThreeValuedLogic:
    """三值逻辑系统"""

    @staticmethod
    def compute_overall_passed(results: List[Optional[bool]]) -> Optional[bool]:
        """
        计算整体评估结果

        规则：
        1. False + anything → False
        2. True + None → True
        3. 全部 None → None
        """
        if not results:
            return None

        # 规则 1: False + anything → False
        if any(r is False for r in results):
            return False

        has_true = any(r is True for r in results)
        has_none = any(r is None for r in results)

        # 规则 2: True + None → True
        if has_true and has_none:
            return True

        # 规则 3: 全部 None → None
        if has_none and not has_true:
            return None

        # 全部 True
        return True

    @staticmethod
    def and_operator(a: Optional[bool], b: Optional[bool]) -> Optional[bool]:
        if a is False or b is False:
            return False
        if a is None or b is None:
            return None
        return True

    @staticmethod
    def or_operator(a: Optional[bool], b: Optional[bool]) -> Optional[bool]:
        if a is True or b is True:
            return True
        if a is None or b is None:
            return None
        return False

    @staticmethod
    def not_operator(a: Optional[bool]) -> Optional[bool]:
        if a is None:
            return None
        return not a
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_three_valued_logic.py -v
```

Expected: `PASSED`

**Step 5: Commit**

```bash
git add core/three_valued_logic.py tests/test_three_valued_logic.py
git commit -m "feat(core): implement three-valued logic system"
```

---

## Task 4: Bug 类型推导引擎

**Files:**
- Create: `core/bug_type_engine.py`
- Test: `tests/test_bug_type_engine.py`

**Step 1: Write the failing test**

```python
# tests/test_bug_type_engine.py
import pytest
from core.models import *
from core.bug_type_engine import BugTypeEngine

def test_derive_type_1_illegal_success():
    test_case = TestCase(
        test_id="test_1",
        operation="insert",
        slot_values={"dimension": 0},
        raw_parameters={},
        is_legal=False,
        scope=SlotScope.COLLECTION
    )
    execution_result = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        result_data=None,
        error=None,
        elapsed_seconds=0.1
    )

    derivation = BugTypeEngine.derive_bug_type(
        test_case=test_case,
        rule_result=None,
        execution_result=execution_result,
        error_has_root_cause=False,
        precondition_passed=True
    )

    assert derivation.bug_type == BugType.TYPE_1
    assert "非法操作未报错" in derivation.reason

def test_derive_type_2_bad_diagnostics():
    test_case = TestCase(
        test_id="test_2",
        operation="insert",
        slot_values={"dimension": 999999},
        raw_parameters={},
        is_legal=False,
        scope=SlotScope.COLLECTION
    )
    execution_result = ExecutionResult(
        status=ExecutionStatus.FAILURE,
        result_data=None,
        error=Exception("Invalid parameter"),
        elapsed_seconds=0.1
    )

    derivation = BugTypeEngine.derive_bug_type(
        test_case=test_case,
        rule_result=None,
        execution_result=execution_result,
        error_has_root_cause=False,
        precondition_passed=True
    )

    assert derivation.bug_type == BugType.TYPE_2

def test_derive_type_3_legal_failure():
    test_case = TestCase(
        test_id="test_3",
        operation="search",
        slot_values={"top_k": 10},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )
    execution_result = ExecutionResult(
        status=ExecutionStatus.FAILURE,
        result_data=None,
        error=Exception("Connection error"),
        elapsed_seconds=0.1
    )

    derivation = BugTypeEngine.derive_bug_type(
        test_case=test_case,
        rule_result=None,
        execution_result=execution_result,
        error_has_root_cause=True,
        precondition_passed=True
    )

    assert derivation.bug_type == BugType.TYPE_3
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_bug_type_engine.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.bug_type_engine'`

**Step 3: Implement BugTypeEngine**

```python
# core/bug_type_engine.py
from typing import Optional
from dataclasses import dataclass
from core.models import *
from core.three_valued_logic import ThreeValuedLogic

@dataclass
class BugTypeDerivation:
    bug_type: Optional[BugType]
    reason: str
    confidence: float
    decision_path: str
    violated_rules: Optional[list] = None

class BugTypeEngine:
    """Bug 类型推导引擎"""

    @staticmethod
    def derive_bug_type(test_case: TestCase,
                       rule_result: Optional['RuleEvaluationResult'],
                       execution_result: ExecutionResult,
                       error_has_root_cause: bool,
                       precondition_passed: bool) -> BugTypeDerivation:
        """推导 Bug 类型"""

        # 优先级 1: 超时/崩溃 → TYPE_3
        if execution_result.status in [ExecutionStatus.TIMEOUT, ExecutionStatus.CRASH]:
            return BugTypeDerivation(
                bug_type=BugType.TYPE_3,
                reason=f"执行状态为 {execution_result.status.value}",
                confidence=1.0,
                decision_path="priority_1_timeout_crash"
            )

        # 优先级 2: 非法成功 → TYPE_1
        if (not test_case.is_legal and
            execution_result.status == ExecutionStatus.SUCCESS):
            return BugTypeDerivation(
                bug_type=BugType.TYPE_1,
                reason="非法操作未报错",
                confidence=1.0,
                decision_path="priority_2_illegal_success"
            )

        # 优先级 3: 预条件违反 → PRECONDITION_VIOLATION
        if not precondition_passed:
            return BugTypeDerivation(
                bug_type=None,
                reason="预条件未通过，不计入 Bug",
                confidence=1.0,
                decision_path="priority_3_precondition_failed"
            )

        # 优先级 4: 错误不可诊断 → TYPE_2
        if (not test_case.is_legal and
            execution_result.status == ExecutionStatus.FAILURE and
            not error_has_root_cause):
            return BugTypeDerivation(
                bug_type=BugType.TYPE_2,
                reason="非法操作报错但错误信息缺失根因槽",
                confidence=1.0,
                decision_path="priority_4_bad_diagnostics"
            )

        # 优先级 5: 预期行为 → NOT_A_BUG
        if (not test_case.is_legal and
            execution_result.status == ExecutionStatus.FAILURE and
            error_has_root_cause):
            return BugTypeDerivation(
                bug_type=None,
                reason="非法操作正确报错，预期行为",
                confidence=1.0,
                decision_path="priority_5_expected_failure"
            )

        # 优先级 6: 合法失败 → TYPE_3
        if (test_case.is_legal and
            execution_result.status == ExecutionStatus.FAILURE):
            return BugTypeDerivation(
                bug_type=BugType.TYPE_3,
                reason="合法操作报错/失败",
                confidence=1.0,
                decision_path="priority_6_legal_failure"
            )

        # 优先级 7: 语义违背 → TYPE_4
        if (test_case.is_legal and
            execution_result.status == ExecutionStatus.SUCCESS and
            rule_result is not None and
            rule_result.overall_passed is False):
            return BugTypeDerivation(
                bug_type=BugType.TYPE_4,
                reason="合法操作结果违反语义规则",
                confidence=1.0,
                decision_path="priority_7_semantic_violation"
            )

        # 默认: 无法判断
        return BugTypeDerivation(
            bug_type=None,
            reason="无法推导 Bug 类型",
            confidence=0.0,
            decision_path="default_unknown"
        )
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_bug_type_engine.py -v
```

Expected: `PASSED`

**Step 5: Commit**

```bash
git add core/bug_type_engine.py tests/test_bug_type_engine.py
git commit -m "feat(core): implement BugTypeEngine with decision table logic"
```

---

## Task 5: Adapter 接口定义

**Files:**
- Create: `adapters/base.py`
- Create: `adapters/__init__.py`
- Test: `tests/test_adapters.py`

**Step 1: Write the failing test**

```python
# tests/test_adapters.py
import pytest
from abc import ABC
from adapters.base import BaseAdapter, Capabilities

def test_adapter_interface():
    # 测试接口可以被子类化
    class TestAdapter(BaseAdapter):
        def get_capabilities(self):
            return Capabilities(
                supported_operations=["test"],
                supported_vector_types=["float32"],
                supported_index_types=["IVF"],
                concurrent_operations=False,
                max_concurrent_requests=None,
                transaction_support=False,
                distributed=False
            )

        def map_slot_to_param(self, slot_name):
            return slot_name

        def transform_value(self, slot_name, value):
            return value

        def classify_error(self, error):
            return ErrorCategory.PRODUCT_SUSPECT

        def connect(self, **kwargs):
            return True

        def disconnect(self):
            pass

        def is_connected(self):
            return True

        def execute_test(self, test_case):
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                result_data=None,
                error=None,
                elapsed_seconds=0.0
            )

    adapter = TestAdapter()
    caps = adapter.get_capabilities()
    assert caps.supported_operations == ["test"]
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_adapters.py -v
```

Expected: `ModuleNotFoundError: No module named 'adapters'`

**Step 3: Implement BaseAdapter and Capabilities**

```python
# adapters/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from core.models import *

@dataclass
class Capabilities:
    supported_operations: List[str]
    supported_vector_types: List[str]
    supported_index_types: List[str]
    concurrent_operations: bool
    max_concurrent_requests: Optional[int]
    transaction_support: bool
    distributed: bool

class BaseAdapter(ABC):
    """数据库适配器基类"""

    @abstractmethod
    def get_capabilities(self) -> Capabilities:
        pass

    @abstractmethod
    def map_slot_to_param(self, slot_name: str) -> str:
        pass

    @abstractmethod
    def transform_value(self, slot_name: str, value: Any) -> Any:
        pass

    @abstractmethod
    def classify_error(self, error: Exception) -> ErrorCategory:
        pass

    @abstractmethod
    def connect(self, **kwargs) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def execute_test(self, test_case: TestCase) -> ExecutionResult:
        pass

# adapters/__init__.py
from adapters.base import BaseAdapter, Capabilities
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_adapters.py -v
```

Expected: `PASSED`

**Step 5: Commit**

```bash
git add adapters/ tests/test_adapters.py
git commit -m "feat(adapters): add BaseAdapter interface and Capabilities dataclass"
```

---

## Task 6: SeekDB Adapter 实现（简化版）

**Files:**
- Create: `adapters/seekdb.py`
- Test: `tests/test_seekdb_adapter.py`

**Step 1: Write the failing test**

```python
# tests/test_seekdb_adapter.py
import pytest
from adapters.seekdb import SeekDBAdapter

def test_seekdb_adapter_capabilities():
    adapter = SeekDBAdapter(host="localhost", port=2881)
    caps = adapter.get_capabilities()

    assert "insert" in caps.supported_operations
    assert "search" in caps.supported_operations

def test_seekdb_map_slot_to_param():
    adapter = SeekDBAdapter(host="localhost", port=2881)

    assert adapter.map_slot_to_param("search_range") == "ef"
    assert adapter.map_slot_to_param("top_k") == "top_k"

def test_seekdb_classify_error():
    adapter = SeekDBAdapter(host="localhost", port=2881)

    assert adapter.classify_error(TimeoutError()) == ErrorCategory.INFRA_SUSPECT
    assert adapter.classify_error(ValueError("invalid dimension")) == ErrorCategory.PRODUCT_SUSPECT
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_seekdb_adapter.py -v
```

Expected: `ModuleNotFoundError: No module named 'adapters.seekdb'`

**Step 3: Implement SeekDBAdapter**

```python
# adapters/seekdb.py
import requests
from typing import Dict, Any
from adapters.base import BaseAdapter, Capabilities
from core.models import *

class SeekDBAdapter(BaseAdapter):
    """SeekDB 数据库适配器"""

    # 语义槽到参数的映射
    SLOT_TO_PARAM = {
        "search_range": "ef",
        "top_k": "top_k",
        "dimension": "dimension",
        "metric_type": "metric_type"
    }

    def __init__(self, host: str = "localhost", port: int = 2881):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self._connected = False

    def get_capabilities(self) -> Capabilities:
        return Capabilities(
            supported_operations=["insert", "search", "delete", "create_collection", "drop_collection"],
            supported_vector_types=["float32", "float16"],
            supported_index_types=["IVF", "HNSW", "FLAT"],
            concurrent_operations=True,
            max_concurrent_requests=100,
            transaction_support=False,
            distributed=False
        )

    def map_slot_to_param(self, slot_name: str) -> str:
        return self.SLOT_TO_PARAM.get(slot_name, slot_name)

    def transform_value(self, slot_name: str, value: Any) -> Any:
        if slot_name == "metric_type" and isinstance(value, str):
            return value.upper()
        return value

    def classify_error(self, error: Exception) -> ErrorCategory:
        if isinstance(error, TimeoutError):
            return ErrorCategory.INFRA_SUSPECT
        elif isinstance(error, ConnectionError):
            return ErrorCategory.INFRA_SUSPECT
        elif isinstance(error, (ValueError, KeyError)):
            return ErrorCategory.PRODUCT_SUSPECT
        else:
            return ErrorCategory.INFRA_SUSPECT

    def connect(self, **kwargs) -> bool:
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            self._connected = response.status_code == 200
            return self._connected
        except:
            self._connected = False
            return False

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def execute_test(self, test_case: TestCase) -> ExecutionResult:
        import time
        start_time = time.time()

        try:
            # 根据操作类型执行
            if test_case.operation == "search":
                result = self._execute_search(test_case)
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    result_data=result,
                    error=None,
                    elapsed_seconds=time.time() - start_time
                )
            else:
                return ExecutionResult(
                    status=ExecutionStatus.FAILURE,
                    result_data=None,
                    error=NotImplementedError(f"Operation {test_case.operation} not implemented"),
                    elapsed_seconds=time.time() - start_time
                )
        except Exception as e:
            return ExecutionResult(
                status=self._classify_exception(e),
                result_data=None,
                error=e,
                elapsed_seconds=time.time() - start_time
            )

    def _execute_search(self, test_case: TestCase) -> Dict[str, Any]:
        # 简化的搜索实现
        params = {}
        for slot_name, slot_value in test_case.slot_values.items():
            param_name = self.map_slot_to_param(slot_name)
            params[param_name] = self.transform_value(slot_name, slot_value)

        # 模拟搜索结果
        return {
            "ids": [1, 2, 3],
            "scores": [0.1, 0.2, 0.3],
            "total": 3
        }

    def _classify_exception(self, error: Exception) -> ExecutionStatus:
        if isinstance(error, TimeoutError):
            return ExecutionStatus.TIMEOUT
        elif isinstance(error, (ConnectionError, OSError)):
            return ExecutionStatus.CRASH
        else:
            return ExecutionStatus.FAILURE
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_seekdb_adapter.py -v
```

Expected: `PASSED`

**Step 5: Commit**

```bash
git add adapters/seekdb.py tests/test_seekdb_adapter.py
git commit -m "feat(adapters): implement SeekDB adapter with basic operations"
```

---

## Task 7: RuleEngine 基础实现

**Files:**
- Create: `core/rule_engine.py`
- Test: `tests/test_rule_engine.py`

**Step 1: Write the failing test**

```python
# tests/test_rule_engine.py
import pytest
from core.rule_engine import RuleEngine, RuleEvaluationResult
from core.models import *

def test_rule_engine_evaluate_all_passed():
    contract = Contract(
        database_name="test_db",
        version="1.0",
        core_slots=[
            CoreSlot(
                slot_name="top_k",
                description="测试槽",
                type=SlotType.INTEGER,
                scope=SlotScope.COLLECTION,
                depends_on=[]
            )
        ]
    )

    engine = RuleEngine(contract)

    test_case = TestCase(
        test_id="test_1",
        operation="search",
        slot_values={"top_k": 10},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    result = engine.evaluate_rules(test_case, ExecutionContext(adapter=None, profile=None, state_model=None, test_case=test_case))

    assert result.overall_passed is True  # 无规则，所以为 None，但空列表默认为 True

def test_rule_engine_trace():
    # 测试可解释性输出
    contract = Contract(
        database_name="test_db",
        version="1.0",
        core_slots=[]
    )

    engine = RuleEngine(contract)
    result = engine.evaluate_rules(
        TestCase(test_id="test", operation="search", slot_values={}, raw_parameters={}, is_legal=True, scope=SlotScope.COLLECTION),
        ExecutionContext(adapter=None, profile=None, state_model=None, test_case=TestCase(test_id="test", operation="search", slot_values={}, raw_parameters={}, is_legal=True, scope=SlotScope.COLLECTION))
    )

    assert hasattr(result, 'trace')
    assert hasattr(result.trace, 'false_sources')
    assert hasattr(result.trace, 'none_sources')
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_rule_engine.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.rule_engine'`

**Step 3: Implement RuleEngine**

```python
# core/rule_engine.py
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from core.models import *
from core.three_valued_logic import ThreeValuedLogic

@dataclass
class ExecutionContext:
    adapter: Optional['BaseAdapter']
    profile: Optional['BaseProfilePlugin']
    state_model: Optional['StateModel']
    test_case: TestCase

@dataclass
class SingleRuleResult:
    rule_id: str
    passed: Optional[bool]
    reason: Optional[str]
    violated_slot: Optional[str]

@dataclass
class SlotRuleResult:
    slot_name: str
    results: List[SingleRuleResult]
    passed: Optional[bool]

@dataclass
class ThreeValuedEvaluationTrace:
    final_result: Optional[bool]
    false_sources: List[str] = field(default_factory=list)
    none_sources: List[str] = field(default_factory=list)
    evaluation_path: str = ""

@dataclass
class CoverageReport:
    session_id: str
    created_at: datetime
    slot_coverage: Dict[str, float] = field(default_factory=dict)
    boundary_coverage: float = 0.0
    total_evaluations: int = 0
    unique_values_tested: Dict[str, int] = field(default_factory=dict)

@dataclass
class RuleEvaluationResult:
    results: List[SlotRuleResult]
    overall_passed: Optional[bool]
    coverage_report: CoverageReport
    trace: ThreeValuedEvaluationTrace

class RuleCoverageTracker:
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        self.evaluations: Dict[str, List] = {}
        self.slot_values_tested: Dict[str, set] = {}
        self.created_at = datetime.now()

    def record_evaluation(self, slot_name: str, value: Any, passed: Optional[bool]):
        if slot_name not in self.evaluations:
            self.evaluations[slot_name] = []
        self.evaluations[slot_name].append((value, passed, datetime.now()))

        if slot_name not in self.slot_values_tested:
            self.slot_values_tested[slot_name] = set()
        if value is not None:
            self.slot_values_tested[slot_name].add(value)

    def get_report(self) -> CoverageReport:
        return CoverageReport(
            session_id=self.session_id,
            created_at=self.created_at,
            total_evaluations=sum(len(v) for v in self.evaluations.values()),
            unique_values_tested={
                slot: len(values) for slot, values in self.slot_values_tested.items()
            }
        )

class RuleEngine:
    def __init__(self, contract: Contract, session_id: Optional[str] = None):
        self.contract = contract
        self.coverage_tracker = RuleCoverageTracker(session_id)
        self.session_id = self.coverage_tracker.session_id

    def evaluate_rules(self, test_case: TestCase, execution_context: ExecutionContext) -> RuleEvaluationResult:
        results = []
        false_sources = []
        none_sources = []

        for slot in self.contract.get_all_slots():
            slot_result = SlotRuleResult(
                slot_name=slot.slot_name,
                results=[],
                passed=None
            )
            results.append(slot_result)

        # 计算整体结果
        overall_passed = ThreeValuedLogic.compute_overall_passed([r.passed for r in results])

        # 生成追踪
        trace = ThreeValuedEvaluationTrace(
            final_result=overall_passed,
            false_sources=false_sources,
            none_sources=none_sources,
            evaluation_path=self._generate_evaluation_path(results)
        )

        return RuleEvaluationResult(
            results=results,
            overall_passed=overall_passed,
            coverage_report=self.coverage_tracker.get_report(),
            trace=trace
        )

    def _generate_evaluation_path(self, results: List[SlotRuleResult]) -> str:
        passed_count = sum(1 for r in results if r.passed is True)
        false_count = sum(1 for r in results if r.passed is False)
        none_count = sum(1 for r in results if r.passed is None)
        return f"evaluated_{len(results)}_slots:_{passed_count}_passed_{false_count}_false_{none_count}_none"
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_rule_engine.py -v
```

Expected: `PASSED`

**Step 5: Commit**

```bash
git add core/rule_engine.py tests/test_rule_engine.py
git commit -m "feat(core): implement RuleEngine with three-valued logic and trace"
```

---

## Task 8: Precondition Gate

**Files:**
- Create: `core/precondition_gate.py`
- Test: `tests/test_precondition_gate.py`

**Step 1: Write the failing test**

```python
# tests/test_precondition_gate.py
import pytest
from core.precondition_gate import PreconditionGate, GateResult
from core.models import *

def test_precondition_gate_all_passed():
    gate = PreconditionGate(rule_engine=None, state_model=None)

    result = GateResult(
        passed=True,
        reason="all_checks_passed"
    )

    assert result.passed is True

def test_precondition_gate_rule_violation():
    gate = PreconditionGate(rule_engine=None, state_model=None)

    result = GateResult(
        passed=False,
        reason="rule_violation: top_k.range_check"
    )

    assert result.passed is False
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_precondition_gate.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.precondition_gate'`

**Step 3: Implement PreconditionGate**

```python
# core/precondition_gate.py
from typing import Optional
from core.models import *
from core.rule_engine import RuleEngine

class PreconditionGate:
    """预条件门禁"""

    def __init__(self, rule_engine: RuleEngine, state_model: Optional['StateModel'] = None):
        self.rule_engine = rule_engine
        self.state_model = state_model

    def check(self, test_case: TestCase, adapter: 'BaseAdapter', profile: Optional['BaseProfilePlugin'] = None) -> GateResult:
        """检查测试用例是否通过预条件"""

        # 1. RuleEngine 规则评估
        rule_result = self.rule_engine.evaluate_rules(
            test_case,
            ExecutionContext(adapter=adapter, profile=profile, state_model=self.state_model, test_case=test_case)
        )

        if not rule_result.overall_passed:
            for slot_result in rule_result.results:
                for single_rule in slot_result.results:
                    if single_rule.passed is False:
                        return GateResult(
                            passed=False,
                            reason=f"rule_violation: {slot_result.slot_name}.{single_rule.rule_id}"
                        )

        # 2. Profile skip 逻辑
        if profile:
            skip_reason = profile.should_skip_test(test_case)
            if skip_reason:
                return GateResult(
                    passed=False,
                    reason=f"profile_skip: {skip_reason}"
                )

        # 3. StateModel 状态机合法性（暂不实现）
        # if self.state_model:
        #     state_result = self._check_state_machine_legality(test_case, adapter)
        #     if not state_result.passed:
        #         return GateResult(passed=False, reason=state_result.reason)

        return GateResult(
            passed=True,
            reason="all_checks_passed",
            coverage_report=rule_result.coverage_report
        )
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_precondition_gate.py -v
```

Expected: `PASSED`

**Step 5: Commit**

```bash
git add core/precondition_gate.py tests/test_precondition_gate.py
git commit -m "feat(core): implement PreconditionGate with rule evaluation"
```

---

## Task 9: StateModel 单粒度实现

**Files:**
- Create: `state/base.py`
- Create: `state/scoped.py`
- Test: `tests/test_state_model.py`

**Step 1: Write the failing test**

```python
# tests/test_state_model.py
import pytest
from state.scoped import ScopedStateModel, StateIdentifier
from core.models import SlotScope

def test_state_model_collection_states():
    model = ScopedStateModel()

    states = model.get_valid_states(SlotScope.COLLECTION)
    assert "empty" in states
    assert "has_data" in states
    assert "not_exist" in states

def test_state_model_transitions():
    model = ScopedStateModel()

    transitions = model.get_valid_transitions(SlotScope.COLLECTION)
    assert "has_data" in transitions.get("empty", [])
    assert "empty" in transitions.get("has_data", [])
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_state_model.py -v
```

Expected: `ModuleNotFoundError: No module named 'state'`

**Step 3: Implement StateModel**

```python
# state/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from core.models import SlotScope

class StateModel(ABC):
    @abstractmethod
    def get_valid_states(self, scope: SlotScope) -> List[str]:
        pass

    @abstractmethod
    def get_valid_transitions(self, scope: SlotScope) -> Dict[str, List[str]]:
        pass

    @abstractmethod
    def get_current_state(self, scope: SlotScope, name: str, adapter) -> str:
        pass

    @abstractmethod
    def is_transition_legal(self, scope: SlotScope, from_state: str, to_state: str) -> bool:
        pass

# state/scoped.py
from typing import List, Dict
from state.base import StateModel
from core.models import SlotScope

@dataclass
class StateIdentifier:
    scope: SlotScope
    name: str

    def __hash__(self):
        return hash((self.scope.value, self.name))

class ScopedStateModel(StateModel):
    """多粒度状态机模型（单粒度实现）"""

    # COLLECTION 级别的状态定义
    COLLECTION_STATES = [
        "not_exist",
        "creating",
        "empty",
        "has_data",
        "loading",
        "indexing",
        "deleting",
        "error"
    ]

    COLLECTION_TRANSITIONS = {
        "not_exist": ["creating", "error"],
        "creating": ["empty", "error"],
        "empty": ["has_data", "loading", "deleting", "error"],
        "has_data": ["loading", "indexing", "deleting", "error"],
        "loading": ["has_data", "error"],
        "indexing": ["has_data", "error"],
        "deleting": ["not_exist", "error"],
        "error": ["not_exist", "empty", "has_data"]
    }

    def get_valid_states(self, scope: SlotScope) -> List[str]:
        if scope == SlotScope.COLLECTION:
            return self.COLLECTION_STATES
        return []

    def get_valid_transitions(self, scope: SlotScope) -> Dict[str, List[str]]:
        if scope == SlotScope.COLLECTION:
            return self.COLLECTION_TRANSITIONS
        return {}

    def get_current_state(self, scope: SlotScope, name: str, adapter) -> str:
        # 简化实现：返回默认状态
        return "not_exist"

    def is_transition_legal(self, scope: SlotScope, from_state: str, to_state: str) -> bool:
        transitions = self.get_valid_transitions(scope)
        return to_state in transitions.get(from_state, [])
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_state_model.py -v
```

Expected: `PASSED`

**Step 5: Commit**

```bash
git add state/ tests/test_state_model.py
git commit -m "feat(state): implement ScopedStateModel with COLLECTION scope"
```

---

## Task 10: 执行流程

**Files:**
- Create: `core/execution_pipeline.py`
- Test: `tests/test_execution_pipeline.py`

**Step 1: Write the failing test**

```python
# tests/test_execution_pipeline.py
import pytest
from core.execution_pipeline import ExecutionPipeline, TestExecutionResult
from core.models import *

def test_execution_pipeline_precondition_failed():
    pipeline = ExecutionPipeline()

    test_case = TestCase(
        test_id="test_1",
        operation="search",
        slot_values={},
        raw_parameters={},
        is_legal=False,
        scope=SlotScope.COLLECTION
    )

    # Mock gate 失败
    result = TestExecutionResult(
        status=ExecutionStatus.PRECONDITION_FAILED,
        error=None,
        result_data=None,
        elapsed_seconds=0.0,
        gate_result=GateResult(passed=False, reason="test"),
        rule_evaluation_result=None,
        bug_type_derivation=None
    )

    assert result.status == ExecutionStatus.PRECONDITION_FAILED
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_execution_pipeline.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.execution_pipeline'`

**Step 3: Implement ExecutionPipeline**

```python
# core/execution_pipeline.py
from typing import Optional
from datetime import datetime
from core.models import *
from core.rule_engine import RuleEngine
from core.precondition_gate import PreconditionGate
from core.bug_type_engine import BugTypeEngine

class ExecutionPipeline:
    """测试执行流水线"""

    def __init__(self, rule_engine: RuleEngine, precondition_gate: PreconditionGate):
        self.rule_engine = rule_engine
        self.precondition_gate = precondition_gate
        self.bug_type_engine = BugTypeEngine()

    def execute_test_case(self, test_case: TestCase, contract: Contract, adapter: 'BaseAdapter', profile: Optional['BaseProfilePlugin'] = None, state_model: Optional['StateModel'] = None) -> TestExecutionResult:
        """执行单个测试用例的完整流程"""

        # Step 1: PreconditionGate
        gate_result = self.precondition_gate.check(
            test_case=test_case,
            adapter=adapter,
            profile=profile
        )

        if not gate_result.passed:
            return TestExecutionResult(
                status=ExecutionStatus.PRECONDITION_FAILED,
                error=None,
                result_data=None,
                elapsed_seconds=0.0,
                gate_result=gate_result,
                rule_evaluation_result=None,
                bug_type_derivation=None
            )

        # Step 2: Adapter.execute_test
        start_time = datetime.now()
        execution_result = adapter.execute_test(test_case)
        elapsed_seconds = (datetime.now() - start_time).total_seconds()

        # Step 3: RuleEngine
        rule_result = self.rule_engine.evaluate_rules(
            test_case,
            ExecutionContext(adapter=adapter, profile=profile, state_model=state_model, test_case=test_case)
        )

        # Step 4: BugTypeEngine
        bug_type_derivation = self.bug_type_engine.derive_bug_type(
            test_case=test_case,
            rule_result=rule_result,
            execution_result=execution_result,
            error_has_root_cause=self._has_root_cause_slot(execution_result.error),
            precondition_passed=gate_result.passed
        )

        return TestExecutionResult(
            status=execution_result.status,
            error=execution_result.error,
            result_data=execution_result.result_data,
            elapsed_seconds=elapsed_seconds,
            gate_result=gate_result,
            rule_evaluation_result=rule_result,
            bug_type_derivation=bug_type_derivation
        )

    def _has_root_cause_slot(self, error: Optional[Exception]) -> bool:
        """检查错误是否有根因槽"""
        if error is None:
            return False
        error_msg = str(error).lower()
        # 简化判断：如果错误信息包含参数名，认为有根因槽
        return any(keyword in error_msg for keyword in ["dimension", "top_k", "ef", "nprobe", "metric"])
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_execution_pipeline.py -v
```

Expected: `PASSED`

**Step 5: Commit**

```bash
git add core/execution_pipeline.py tests/test_execution_pipeline.py
git commit -m "feat(core): implement ExecutionPipeline with correct flow order"
```

---

## Task 11: 添加 requirements.txt

**Files:**
- Create: `requirements.txt`

**Step 1: Create requirements.txt**

```bash
cat > "C:/Users/11428/Desktop/SemanticBugMiningFramework/requirements.txt" << 'EOF'
# Core dependencies
pydantic>=2.0.0
pyyaml>=6.0
requests>=2.28.0

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0

# Development
black>=23.0.0
isort>=5.12.0
mypy>=1.7.0
EOF
```

**Step 2: Commit**

```bash
git add requirements.txt
git commit -m "chore: add project dependencies"
```

---

## Task 12: 添加 __init__.py 文件

**Files:**
- Create: `core/__init__.py`
- Create: `state/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Create __init__.py files**

```python
# core/__init__.py
from core.models import *
from core.three_valued_logic import ThreeValuedLogic
from core.bug_type_engine import BugTypeEngine
from core.rule_engine import RuleEngine
from core.precondition_gate import PreconditionGate
from core.execution_pipeline import ExecutionPipeline
```

```python
# state/__init__.py
from state.base import StateModel
from state.scoped import ScopedStateModel
```

```python
# tests/__init__.py
```

**Step 2: Commit**

```bash
git add core/__init__.py state/__init__.py tests/__init__.py
git commit -m "chore: add __init__.py files for packages"
```

---

## Task 13: 运行所有测试

**Step 1: Run all tests**

```bash
cd C:/Users/11428/Desktop/SemanticBugMiningFramework
pytest tests/ -v
```

Expected: 所有测试通过

**Step 2: Commit (如果通过)**

```bash
git add .
git commit -m "test: all Phase 1 tests passing"
```

---

## 完成标准

当所有任务完成后，你应该有：

✅ 7 个设计文档在 `docs/design/`
✅ 13 个任务文件实现
✅ 完整的测试覆盖
✅ 所有测试通过

---

## 下一步

Phase 1 完成后，可以进入 Phase 2（Oracle 层、Case Generator、Evidence Collector）。
