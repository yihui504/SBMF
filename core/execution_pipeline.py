# core/execution_pipeline.py
from typing import Optional, List
from datetime import datetime
from core.models import *
from core.rule_engine import RuleEngine, ExecutionContext
from core.precondition_gate import PreconditionGate
from core.bug_type_engine import BugTypeEngine
from oracle.checker import OracleChecker


class ExecutionPipeline:
    """测试执行流水线

    完整的测试执行流程：
    1. PreconditionGate 预条件检查
    2. Adapter.execute_test 执行测试
    3. RuleEngine 评估规则
    4. Oracle 检查器验证结果
    5. BugTypeEngine 推导 Bug 类型

    执行顺序必须严格遵守！
    """

    def __init__(
        self,
        rule_engine: RuleEngine,
        precondition_gate: PreconditionGate,
        oracles: Optional[List[OracleChecker]] = None
    ):
        """初始化 ExecutionPipeline

        Args:
            rule_engine: 规则评估引擎
            precondition_gate: 预条件门禁
            oracles: Oracle 检查器列表（可选）
        """
        self.rule_engine = rule_engine
        self.precondition_gate = precondition_gate
        self.bug_type_engine = BugTypeEngine()
        self.oracles = oracles or []

    def execute_test_case(self,
                         test_case: SemanticCase,
                         contract: Contract,
                         adapter: 'BaseAdapter',
                         profile: Optional['BaseProfilePlugin'] = None,
                         state_model: Optional['StateModel'] = None) -> FullExecutionResult:
        """执行单个测试用例的完整流程

        Args:
            test_case: 测试用例
            contract: Contract 对象
            adapter: 数据库适配器
            profile: Profile Plugin（可选）
            state_model: 状态机模型（可选）

        Returns:
            FullExecutionResult: 完整的执行结果
        """
        # Step 1: PreconditionGate 预条件检查
        gate_result = self.precondition_gate.check(
            test_case=test_case,
            adapter=adapter,
            profile=profile
        )

        # 如果预条件未通过，直接返回
        if not gate_result.passed:
            return FullExecutionResult(
                status=ExecutionStatus.PRECONDITION_FAILED,
                error=None,
                result_data=None,
                elapsed_seconds=0.0,
                gate_result=gate_result,
                rule_evaluation_result=None,
                bug_type_derivation=None,
                oracle_results=[]
            )

        # Step 2: Adapter.execute_test 执行测试
        start_time = datetime.now()
        execution_result = adapter.execute_test(test_case)
        elapsed_seconds = (datetime.now() - start_time).total_seconds()

        # Step 3: RuleEngine 评估规则
        execution_context = ExecutionContext(
            adapter=adapter,
            profile=profile,
            state_model=state_model,
            test_case=test_case
        )
        rule_result = self.rule_engine.evaluate_rules(test_case, execution_context)

        # Step 4: Oracle 检查器验证结果（Phase 4 新增）
        oracle_results = self._run_oracle_checks(test_case, execution_result)

        # Step 5: BugTypeEngine 推导 Bug 类型
        bug_type_derivation = self.bug_type_engine.derive_bug_type(
            test_case=test_case,
            rule_result=rule_result,
            execution_result=execution_result,
            error_has_root_cause=self._has_root_cause_slot(execution_result.error),
            precondition_passed=gate_result.passed
        )

        return FullExecutionResult(
            status=execution_result.status,
            error=execution_result.error,
            result_data=execution_result.result_data,
            elapsed_seconds=elapsed_seconds,
            gate_result=gate_result,
            rule_evaluation_result=rule_result,
            bug_type_derivation=bug_type_derivation,
            oracle_results=oracle_results
        )

    def _run_oracle_checks(
        self,
        test_case: SemanticCase,
        execution_result: ExecutionResult
    ) -> List['OracleResult']:
        """运行 Oracle 检查器

        Args:
            test_case: 测试用例
            execution_result: 执行结果

        Returns:
            List[OracleResult]: Oracle 检查结果列表
        """
        # Import here to avoid circular dependency
        from oracle.base import OracleResult

        results = []

        for oracle in self.oracles:
            # 检查 Oracle 是否可以检查此测试用例
            if oracle.can_check(test_case):
                try:
                    result = oracle.check(test_case, execution_result)
                    results.append(result)
                except Exception as e:
                    # 记录 Oracle 检查失败，但不中断流程
                    results.append(OracleResult(
                        oracle_id=oracle.get_id(),
                        passed=False,
                        details=f"Oracle check failed with exception: {str(e)}"
                    ))

        return results

    def _has_root_cause_slot(self, error: Optional[Exception]) -> bool:
        """检查错误是否有根因槽

        Args:
            error: 异常对象

        Returns:
            bool: 是否有根因槽
        """
        if error is None:
            return False
        error_msg = str(error).lower()
        # 简化判断：如果错误信息包含参数名，认为有根因槽
        return any(keyword in error_msg for keyword in ["dimension", "top_k", "ef", "nprobe", "metric"])
