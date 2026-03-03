# core/precondition_gate.py
from typing import Optional
from core.models import *
from core.rule_engine import RuleEngine, ExecutionContext


class PreconditionGate:
    """预条件门禁

    职责：
    - 消费 RuleEngine 评估结果
    - 检查 Profile skip 逻辑
    - 检查 StateModel 状态机合法性

    执行顺序（STRICT）：
    1. RuleEngine 规则评估
    2. Profile skip 逻辑
    3. StateModel 状态机合法性（Phase 1.5 部分实现）
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
              test_case: SemanticCase,
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

        # 3. StateModel 状态机合法性检查
        if self.state_model:
            state_result = self._check_state_machine_legality(test_case, adapter)
            if not state_result.passed:
                return GateResult(
                    passed=False,
                    reason=state_result.reason,
                    coverage_report=rule_result.coverage_report
                )

        # 所有检查通过
        return GateResult(
            passed=True,
            reason="all_checks_passed",
            coverage_report=rule_result.coverage_report
        )

    def _check_state_machine_legality(self,
                                      test_case: SemanticCase,
                                      adapter: Optional['BaseAdapter']) -> 'GateResult':
        """检查状态机合法性

        Phase 1.5 实现说明：
        - 尝试调用 StateModel.get_current_state()
        - 如果 NotImplementedError（Phase 1），跳过状态检查
        - Phase 2 将实现完整的状态机合法性检查

        Args:
            test_case: 测试用例
            adapter: 数据库适配器

        Returns:
            GateResult: 状态机检查结果
        """
        from dataclasses import dataclass

        @dataclass
        class StateCheckResult:
            passed: bool
            reason: str

        try:
            # 尝试获取当前状态
            current_state = self.state_model.get_current_state(
                scope=test_case.scope,
                name=self._extract_resource_name(test_case),
                adapter=adapter
            )

            # Phase 2: 这里将实现实际的状态转移合法性检查
            # Phase 1: get_current_state 抛出 NotImplementedError，所以不会到达这里
            return StateCheckResult(
                passed=True,
                reason="state_check_not_implemented"
            )

        except NotImplementedError as e:
            # Phase 1: StateModel 未实现，跳过检查
            return StateCheckResult(
                passed=True,
                reason="state_check_skipped_not_implemented"
            )

    def _extract_resource_name(self, test_case: SemanticCase) -> str:
        """从测试用例中提取资源名称

        Args:
            test_case: 测试用例

        Returns:
            str: 资源名称（例如：集合名）
        """
        # 简化实现：从 raw_parameters 中提取
        # 实际实现可能需要更复杂的逻辑
        return test_case.raw_parameters.get("collection_name", "unknown")
