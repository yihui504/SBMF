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
        """推导 Bug 类型

        Based on decision table in docs/design/006-bug-type-decision-table.md
        Priority order:
        1. TIMEOUT/CRASH → TYPE_3
        2. Illegal + SUCCESS → TYPE_1
        3. Precondition failed → None (PRECONDITION_VIOLATION)
        4. Illegal + FAILURE + no root cause → TYPE_2
        5. Illegal + FAILURE + has root cause → None (NOT_A_BUG)
        6. Legal + FAILURE → TYPE_3
        7. Legal + SUCCESS + rule violated → TYPE_4
        """

        # Priority 1: Timeout/Crash → TYPE_3
        if execution_result.status in [ExecutionStatus.TIMEOUT, ExecutionStatus.CRASH]:
            return BugTypeDerivation(
                bug_type=BugType.TYPE_3,
                reason=f"执行状态为 {execution_result.status.value}",
                confidence=1.0,
                decision_path="priority_1_timeout_crash"
            )

        # Priority 2: Illegal success → TYPE_1
        if (not test_case.is_legal and
            execution_result.status == ExecutionStatus.SUCCESS):
            return BugTypeDerivation(
                bug_type=BugType.TYPE_1,
                reason="非法操作未报错",
                confidence=1.0,
                decision_path="priority_2_illegal_success"
            )

        # Priority 3: Precondition failed → None
        if not precondition_passed:
            return BugTypeDerivation(
                bug_type=None,
                reason="预条件未通过，不计入 Bug",
                confidence=1.0,
                decision_path="priority_3_precondition_failed"
            )

        # Priority 4: Bad diagnostics → TYPE_2
        if (not test_case.is_legal and
            execution_result.status == ExecutionStatus.FAILURE and
            not error_has_root_cause):
            return BugTypeDerivation(
                bug_type=BugType.TYPE_2,
                reason="非法操作报错但错误信息缺失根因槽",
                confidence=1.0,
                decision_path="priority_4_bad_diagnostics"
            )

        # Priority 5: Expected failure → None (NOT_A_BUG)
        if (not test_case.is_legal and
            execution_result.status == ExecutionStatus.FAILURE and
            error_has_root_cause):
            return BugTypeDerivation(
                bug_type=None,
                reason="非法操作正确报错，预期行为",
                confidence=1.0,
                decision_path="priority_5_expected_failure"
            )

        # Priority 6: Legal failure → TYPE_3
        if (test_case.is_legal and
            execution_result.status == ExecutionStatus.FAILURE):
            return BugTypeDerivation(
                bug_type=BugType.TYPE_3,
                reason="合法操作报错/失败",
                confidence=1.0,
                decision_path="priority_6_legal_failure"
            )

        # Priority 7: Semantic violation → TYPE_4
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

        # Default: Unknown
        return BugTypeDerivation(
            bug_type=None,
            reason="无法推导 Bug 类型",
            confidence=0.0,
            decision_path="default_unknown"
        )
