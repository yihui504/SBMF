# core/rule_engine.py
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from core.models import *
from core.three_valued_logic import ThreeValuedLogic


@dataclass
class ExecutionContext:
    """执行上下文"""
    adapter: Optional['BaseAdapter']
    profile: Optional['BaseProfilePlugin']
    state_model: Optional['StateModel']
    test_case: TestCase


@dataclass
class SingleRuleResult:
    """单个规则评估结果"""
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
class ThreeValuedEvaluationTrace:
    """三值逻辑评估追踪"""
    final_result: Optional[bool]
    false_sources: List[str] = field(default_factory=list)
    none_sources: List[str] = field(default_factory=list)
    evaluation_path: str = ""


@dataclass
class CoverageReport:
    """覆盖统计报告"""
    session_id: str
    created_at: datetime
    slot_coverage: Dict[str, float] = field(default_factory=dict)
    boundary_coverage: float = 0.0
    total_evaluations: int = 0
    unique_values_tested: Dict[str, int] = field(default_factory=dict)


@dataclass
class RuleEvaluationResult:
    """规则评估结果"""
    results: List[SlotRuleResult]
    overall_passed: Optional[bool]
    coverage_report: CoverageReport
    trace: ThreeValuedEvaluationTrace


class RuleCoverageTracker:
    """规则覆盖追踪器

    职责：
    - 追踪每个槽的评估次数
    - 追踪测试过的唯一值
    - Session 级隔离
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        self.evaluations: Dict[str, List] = {}
        self.slot_values_tested: Dict[str, set] = {}
        self.created_at = datetime.now()

    def record_evaluation(self, slot_name: str, value: Any, passed: Optional[bool]):
        """记录一次评估"""
        if slot_name not in self.evaluations:
            self.evaluations[slot_name] = []
        self.evaluations[slot_name].append((value, passed, datetime.now()))

        if slot_name not in self.slot_values_tested:
            self.slot_values_tested[slot_name] = set()
        if value is not None:
            self.slot_values_tested[slot_name].add(value)

    def get_report(self) -> CoverageReport:
        """获取覆盖报告

        Returns:
            CoverageReport: 包含 slot_coverage 和 boundary_coverage 的完整报告
            - slot_coverage: 每个槽的覆盖百分比（基于唯一值数量）
            - boundary_coverage: 边界测试覆盖度（Phase 1 暂时为 0.0）
        """
        # 计算 slot_coverage：每个槽的覆盖百分比
        # 简化实现：基于评估次数和唯一值数量的启发式计算
        slot_coverage = {}
        for slot_name, evaluations in self.evaluations.items():
            unique_count = len(self.slot_values_tested.get(slot_name, set()))
            total_count = len(evaluations)
            if total_count > 0:
                # 覆盖度 = 唯一值数量 / 总评估次数（简化计算）
                coverage = min(1.0, unique_count / max(1, total_count))
            else:
                coverage = 0.0
            slot_coverage[slot_name] = coverage

        # boundary_coverage: 边界测试覆盖度
        # Phase 1 暂时返回 0.0，待后续实现边界值测试后计算
        boundary_coverage = 0.0

        return CoverageReport(
            session_id=self.session_id,
            created_at=self.created_at,
            total_evaluations=sum(len(v) for v in self.evaluations.values()),
            unique_values_tested={
                slot: len(values) for slot, values in self.slot_values_tested.items()
            },
            slot_coverage=slot_coverage,
            boundary_coverage=boundary_coverage
        )


class RuleEngine:
    """规则评估引擎

    职责：
    - 评估 Contract 规则
    - 生成覆盖统计
    - Session 级隔离

    Phase 1 实现说明：
    - 当前版本提供框架结构和数据流
    - 实际规则解析和评估将在后续阶段实现（待 Contract DSL 解析完成后）
    - 对于没有规则的槽，返回 passed=None（表示未评估）
    - 对于空 Contract，overall_passed 返回 None（三值逻辑）
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

        Phase 1 实现：
        - 遍历 Contract 中的所有槽
        - 对于每个槽，如果没有规则定义，返回 passed=None
        - 记录评估到 coverage_tracker
        - 生成包含 false_sources 和 none_sources 的追踪信息

        Args:
            test_case: 测试用例
            execution_context: 执行上下文

        Returns:
            RuleEvaluationResult: 评估结果，包含 trace 和 coverage_report
        """
        results = []
        false_sources = []  # 追踪导致 False 结果的规则来源
        none_sources = []   # 追踪导致 None 结果的规则来源

        # 遍历所有槽
        for slot in self.contract.core_slots:
            # Phase 1: 槽没有规则时，passed=None（表示未评估/无规则）
            # 后续阶段将解析 slot.rules 并进行实际规则评估
            slot_result = SlotRuleResult(
                slot_name=slot.slot_name,
                results=[],  # Phase 1: 空，后续填充 SingleRuleResult
                passed=None  # 无规则时为 None
            )
            results.append(slot_result)

            # 记录到覆盖追踪器
            slot_value = test_case.slot_values.get(slot.slot_name)
            self.coverage_tracker.record_evaluation(slot.slot_name, slot_value, None)

            # 追踪 None 来源
            none_sources.append(f"slot:{slot.slot_name}")

        # 计算整体结果（三值逻辑）
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

    def get_coverage_report(self) -> CoverageReport:
        """获取当前 Session 的覆盖统计"""
        return self.coverage_tracker.get_report()

    def reset_session(self) -> None:
        """重置当前 Session（保留 session_id）"""
        self.coverage_tracker = RuleCoverageTracker(self.session_id)

    def close_session(self) -> CoverageReport:
        """关闭当前 Session 并返回最终报告"""
        return self.coverage_tracker.get_report()

    def export_snapshot(self) -> dict:
        """导出当前统计快照"""
        return {
            "session_id": self.session_id,
            "evaluations": self.coverage_tracker.evaluations,
            "slot_values_tested": {
                k: list(v) for k, v in self.coverage_tracker.slot_values_tested.items()
            }
        }

    def _generate_evaluation_path(self, results: List[SlotRuleResult]) -> str:
        """生成评估路径描述"""
        passed_count = sum(1 for r in results if r.passed is True)
        false_count = sum(1 for r in results if r.passed is False)
        none_count = sum(1 for r in results if r.passed is None)
        return f"evaluated_{len(results)}_slots:_{passed_count}_passed_{false_count}_false_{none_count}_none"
