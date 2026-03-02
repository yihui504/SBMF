# core/precondition_gate.py
from typing import Optional
from core.models import *
from core.rule_engine import RuleEngine, ExecutionContext


class PreconditionGate:
    """预条件门禁

    职责：
    - 消费 RuleEngine 评估结果
    - 检查 Profile skip 逻辑
    - 检查 StateModel 状态机合法性（Phase 1 暂不实现）

    执行顺序：
    1. RuleEngine 规则评估
    2. Profile skip 逻辑
    3. StateModel 状态机合法性（Phase 1 暂不实现）
    """

    def __init__(self, rule_engine: RuleEngine, state_model: Optional['StateModel'] = None):
        """初始化 PreconditionGate

        Args:
            rule_engine: 规则评估引擎
            state_model: 状态机模型（可选）
        """
        self.rule_engine = rule_engine
        self.state_model = state_model

    def check(self,
              test_case: TestCase,
              adapter: Optional['BaseAdapter'],
              profile: Optional['BaseProfilePlugin'] = None) -> GateResult:
        """检查测试用例是否通过预条件

        Args:
            test_case: 测试用例
            adapter: 数据库适配器
            profile: Profile Plugin（可选）

        Returns:
            GateResult: 门禁结果，附带覆盖报告
        """
        # 1. RuleEngine 规则评估
        execution_context = ExecutionContext(
            adapter=adapter,
            profile=profile,
            state_model=self.state_model,
            test_case=test_case
        )
        rule_result = self.rule_engine.evaluate_rules(test_case, execution_context)

        # 检查规则是否违反（False 表示明确违反）
        if rule_result.overall_passed is False:
            for slot_result in rule_result.results:
                for single_rule in slot_result.results:
                    if single_rule.passed is False:
                        return GateResult(
                            passed=False,
                            reason=f"rule_violation: {slot_result.slot_name}.{single_rule.rule_id}",
                            coverage_report=rule_result.coverage_report
                        )

        # 2. Profile skip 逻辑
        if profile:
            skip_reason = profile.should_skip_test(test_case)
            if skip_reason:
                return GateResult(
                    passed=False,
                    reason=f"profile_skip: {skip_reason}",
                    coverage_report=rule_result.coverage_report
                )

        # 3. StateModel 状态机合法性（Phase 1 暂不实现）
        # TODO: Phase 2 实现 StateModel 集成
        # if self.state_model:
        #     state_result = self._check_state_machine_legality(test_case, adapter)
        #     if not state_result.passed:
        #         return GateResult(passed=False, reason=state_result.reason)

        # 所有检查通过
        return GateResult(
            passed=True,
            reason="all_checks_passed",
            coverage_report=rule_result.coverage_report
        )
