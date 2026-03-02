# 接口规范定义

**版本**: v1.1
**状态**: 冻结
**日期**: 2026-03-02

---

## 一、Adapter 接口规范

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseAdapter(ABC):
    """数据库适配器基类

    职责：
    - 声明数据库能力
    - 语义槽到参数名的映射
    - 参数值转换
    - 错误分类
    - 执行测试
    """

    # ================================================================
    # 必须实现的方法
    # ================================================================

    @abstractmethod
    def get_capabilities(self) -> Capabilities:
        """返回数据库能力声明（唯一能力来源）

        Returns:
            Capabilities: 数据库能力声明
        """
        pass

    @abstractmethod
    def map_slot_to_param(self, slot_name: str) -> str:
        """语义槽 → 参数名映射

        Args:
            slot_name: 语义槽名称

        Returns:
            str: 数据库特定参数名

        Example:
            adapter.map_slot_to_param("search_range") → "ef"  # SeekDB
            adapter.map_slot_to_param("search_range") → "nprobe"  # Milvus
        """
        pass

    @abstractmethod
    def transform_value(self, slot_name: str, value: Any) -> Any:
        """参数值转换

        Args:
            slot_name: 语义槽名称
            value: 原始值

        Returns:
            Any: 转换后的值

        Example:
            adapter.transform_value("metric_type", "l2") → "L2"
        """
        pass

    @abstractmethod
    def classify_error(self, error: Exception) -> ErrorCategory:
        """错误归类

        Args:
            error: 异常对象

        Returns:
            ErrorCategory: infra_suspect / product_suspect / precondition_failed

        规则:
        - TimeoutError → infra_suspect
        - ConnectionError → infra_suspect
        - 参数相关错误 → product_suspect
        - 前条件错误 → precondition_failed
        """
        pass

    @abstractmethod
    def connect(self, **kwargs) -> bool:
        """连接数据库

        Args:
            **kwargs: 连接参数 (host, port, user, password, ...)

        Returns:
            bool: 连接是否成功
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """断开数据库连接"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """检查连接状态

        Returns:
            bool: 是否已连接
        """
        pass

    @abstractmethod
    def execute_test(self, test_case: TestCase) -> ExecutionResult:
        """执行测试用例

        Args:
            test_case: 测试用例

        Returns:
            ExecutionResult: 执行结果

        Raises:
            Exception: 执行过程中的异常（由调用方分类）
        """
        pass
```

---

## 二、Profile Plugin 接口规范

```python
class BaseProfilePlugin(ABC):
    """数据库特化逻辑基类

    职责：
    - 提供 skip 逻辑
    - 提供结果后处理

    不允许：
    - 声明能力（由 Adapter 提供）
    - 定义 Constraint（由 Contract 提供）
    """

    # ================================================================
    # 必须实现的方法
    # ================================================================

    @abstractmethod
    def should_skip_test(self, test_case: TestCase) -> Optional[str]:
        """判断是否跳过某个测试

        Args:
            test_case: 测试用例

        Returns:
            Optional[str]: 跳过原因，None 表示不跳过

        Example:
            # SeekDB: COSINE + HNSW 暂不支持
            if test_case.get('metric_type') == 'COSINE' and test_case.get('index_type') == 'HNSW':
                return "COSINE + HNSW 暂不支持"
            return None
        """
        pass

    @abstractmethod
    def post_process_result(self, result: Any) -> Any:
        """结果后处理

        Args:
            result: 原始结果

        Returns:
            Any: 处理后的结果

        Example:
            # 统一结果格式
            if isinstance(result, dict):
                return SearchResult(
                    ids=result.get('ids', []),
                    scores=result.get('scores', []),
                    total=result.get('total', 0)
                )
            return result
        """
        pass
```

---

## 三、RuleEngine 接口规范

```python
class RuleEngine:
    """规则评估引擎

    职责：
    - 评估 Contract 规则
    - 生成覆盖统计
    - Session 级隔离
    """

    def __init__(self, contract: Contract, session_id: Optional[str] = None):
        """初始化 RuleEngine

        Args:
            contract: Contract 对象
            session_id: Session ID（可选，自动生成）
        """
        self.contract = contract
        self.coverage_tracker = RuleCoverageTracker(session_id)
        self.session_id = self.coverage_tracker.session_id

    def evaluate_rules(self,
                       test_case: TestCase,
                       execution_context: ExecutionContext) -> RuleEvaluationResult:
        """评估所有规则

        Args:
            test_case: 测试用例
            execution_context: 执行上下文

        Returns:
            RuleEvaluationResult: 评估结果，包含 trace
        """
        pass

    def get_coverage_report(self) -> CoverageReport:
        """获取当前 Session 的覆盖统计

        Returns:
            CoverageReport: 覆盖统计报告
        """
        return self.coverage_tracker.get_report()

    def reset_session(self) -> None:
        """重置当前 Session（保留 session_id）"""
        self.coverage_tracker.reset()

    def close_session(self) -> CoverageReport:
        """关闭当前 Session 并返回最终报告

        Returns:
            CoverageReport: 最终覆盖统计报告
        """
        return self.coverage_tracker.close()

    def export_snapshot(self) -> dict:
        """导出当前统计快照

        Returns:
            dict: 快照数据
        """
        return self.coverage_tracker.snapshot()
```

---

## 四、StateModel 接口规范

```python
class StateModel(ABC):
    """状态机抽象基类

    职责：
    - 定义有效状态和转移
    - 检查转移合法性
    """

    @abstractmethod
    def get_valid_states(self, scope: SlotScope) -> List[str]:
        """返回指定粒度的所有有效状态

        Args:
            scope: 状态粒度

        Returns:
            List[str]: 有效状态列表
        """
        pass

    @abstractmethod
    def get_valid_transitions(self, scope: SlotScope) -> Dict[str, List[str]]:
        """返回指定粒度的有效状态转移

        Args:
            scope: 状态粒度

        Returns:
            Dict[str, List[str]]: {from_state: [to_states]}
        """
        pass

    @abstractmethod
    def get_current_state(self,
                         scope: SlotScope,
                         name: str,
                         adapter: BaseAdapter) -> str:
        """获取指定粒度的当前状态

        Args:
            scope: 状态粒度
            name: 资源名称
            adapter: 数据库适配器

        Returns:
            str: 当前状态
        """
        pass

    @abstractmethod
    def is_transition_legal(self,
                           scope: SlotScope,
                           from_state: str,
                           to_state: str) -> bool:
        """判断状态转移是否合法

        Args:
            scope: 状态粒度
            from_state: 起始状态
            to_state: 目标状态

        Returns:
            bool: 是否合法
        """
        pass


class AsyncStateModel(StateModel):
    """支持异步状态稳定的状态机模型"""

    def __init__(self, stability_config: StabilityConfig = None):
        super().__init__()
        self.stability_config = stability_config or StabilityConfig()

    async def wait_until_stable(self,
                               scope: SlotScope,
                               name: str,
                               adapter: BaseAdapter,
                               timeout: Optional[float] = None) -> StateStabilityResult:
        """等待状态稳定

        Args:
            scope: 状态粒度
            name: 资源名称
            adapter: 数据库适配器
            timeout: 超时时间（秒）

        Returns:
            StateStabilityResult: 稳定性结果
        """
        pass
```

---

## 五、BugTypeEngine 接口规范

```python
class BugTypeEngine:
    """Bug 类型推导引擎

    职责：
    - 根据上下文推导 Bug 类型
    - 生成决策路径
    - 支持置信度扩展
    """

    @staticmethod
    def derive_bug_type(test_case: TestCase,
                       rule_result: Optional[RuleEvaluationResult],
                       execution_result: ExecutionResult,
                       error_has_root_cause: bool,
                       precondition_passed: bool,
                       confidence_factors: Optional[ConfidenceFactors] = None
                       ) -> BugTypeDerivation:
        """推导 Bug 类型

        Args:
            test_case: 测试用例
            rule_result: 规则评估结果
            execution_result: 执行结果
            error_has_root_cause: 错误是否有根因槽
            precondition_passed: 预条件是否通过
            confidence_factors: 置信度因子（可选）

        Returns:
            BugTypeDerivation: 推导结果
        """
        pass

    @staticmethod
    def _has_root_cause_slot(error: Optional[Exception]) -> bool:
        """检查错误是否有根因槽

        Args:
            error: 异常对象

        Returns:
            bool: 是否有根因槽
        """
        pass
```

---

## 六、PreconditionGate 接口规范

```python
class PreconditionGate:
    """预条件门禁

    职责：
    - 消费 RuleEngine 评估结果
    - 检查 Profile skip 逻辑
    - 检查 StateModel 状态机合法性
    """

    def __init__(self, rule_engine: RuleEngine, state_model: StateModel):
        """初始化 PreconditionGate

        Args:
            rule_engine: 规则评估引擎
            state_model: 状态机模型
        """
        self.rule_engine = rule_engine
        self.state_model = state_model

    def check(self,
              test_case: TestCase,
              adapter: BaseAdapter,
              profile: Optional[BaseProfilePlugin]) -> GateResult:
        """检查测试用例是否通过预条件

        Args:
            test_case: 测试用例
            adapter: 数据库适配器
            profile: Profile Plugin（可选）

        Returns:
            GateResult: 门禁结果，附带覆盖报告
        """
        pass
```

---

## 七、Oracle 接口规范

```python
class OracleChecker(ABC):
    """Oracle 检查器基类

    职责：
    - 定义 Oracle
    - 检查是否可检查
    - 执行检查
    """

    @abstractmethod
    def get_definition(self) -> OracleDefinition:
        """获取 Oracle 定义

        Returns:
            OracleDefinition: Oracle 定义
        """
        pass

    @abstractmethod
    def can_check(self, test_case: TestCase) -> bool:
        """判断是否可检查

        Args:
            test_case: 测试用例

        Returns:
            bool: 是否可检查
        """
        pass

    @abstractmethod
    def check(self, test_case: TestCase, result: ExecutionResult) -> OracleResult:
        """执行 Oracle 检查

        Args:
            test_case: 测试用例
            result: 执行结果

        Returns:
            OracleResult: 检查结果
        """
        pass


@dataclass
class OracleResult:
    """Oracle 检查结果"""
    oracle_id: str
    passed: bool
    details: str
    violated_slots: Optional[List[str]] = None
    evidence: Optional[Dict[str, Any]] = None
```

---

## 八、依赖注入规范

```python
@dataclass
class FrameworkConfig:
    """框架配置

    用于依赖注入和模块组装
    """
    # Contract
    contract: Contract

    # Adapter
    adapter: BaseAdapter

    # Profile Plugin（可选）
    profile: Optional[BaseProfilePlugin] = None

    # StateModel
    state_model: Optional[StateModel] = None

    # RuleEngine（自动创建）
    rule_engine: Optional[RuleEngine] = None

    # PreconditionGate（自动创建）
    precondition_gate: Optional[PreconditionGate] = None

    # Oracle 列表
    oracles: List[OracleChecker] = field(default_factory=list)

    def __post_init__(self):
        """自动组装依赖"""
        if self.rule_engine is None:
            self.rule_engine = RuleEngine(self.contract)

        if self.precondition_gate is None and self.state_model is not None:
            self.precondition_gate = PreconditionGate(
                self.rule_engine,
                self.state_model
            )
```
