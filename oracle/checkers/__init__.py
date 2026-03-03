"""
Built-in Oracle Checkers

提供常用的内置 Oracle 检查器实现。
"""

from typing import List, Dict, Any

from oracle import (
    OracleChecker,
    OracleDefinition,
    OracleResult,
    OracleCategory,
    Severity,
    TriggerCondition,
    ValidationLogic,
    TestCase,
    ExecutionResult,
)
from oracle.ast_nodes import (
    ComparisonOperator,
    SlotReferenceNode,
    LiteralNode,
    ComparisonNode,
    ASTNodeType,
)


# ================================================================
# Range Constraint Oracle
# ================================================================

class RangeConstraintOracle(OracleChecker):
    """范围约束 Oracle

    检查某个 slot 的值是否在指定范围内

    Example:
        dimension >= 1 AND dimension <= 2048
    """

    def __init__(
        self,
        slot_name: str,
        min_value: float = None,
        max_value: float = None,
        inclusive_min: bool = True,
        inclusive_max: bool = True,
        severity: Severity = Severity.HIGH
    ):
        """初始化范围约束 Oracle

        Args:
            slot_name: 要检查的槽名称
            min_value: 最小值（None 表示无限制）
            max_value: 最大值（None 表示无限制）
            inclusive_min: 是否包含最小值
            inclusive_max: 是否包含最大值
            severity: 严重性级别
        """
        super().__init__()
        self.slot_name = slot_name
        self.min_value = min_value
        self.max_value = max_value
        self.inclusive_min = inclusive_min
        self.inclusive_max = inclusive_max
        self._severity = severity

    def get_definition(self) -> OracleDefinition:
        """获取 Oracle 定义"""
        return OracleDefinition(
            oracle_id=f"range_{self.slot_name}",
            name=f"{self.slot_name} Range Constraint",
            category=OracleCategory.CONSISTENCY,
            description=f"{self.slot_name} must be in range [{self.min_value}, {self.max_value}]",
            trigger_condition=TriggerCondition(
                required_slots={self.slot_name: None}
            ),
            validation_logic=ValidationLogic(root=None),  # TODO: 构建 AST
            severity=self._severity,
            evidence_required=False
        )

    def check(self, test_case: TestCase, result: ExecutionResult) -> OracleResult:
        """执行范围检查"""
        value = test_case.slot_values.get(self.slot_name)

        # 如果值不存在，视为通过（这个 Oracle 不适用）
        if value is None:
            return OracleResult(
                oracle_id=self.get_id(),
                passed=True,
                details=f"Slot '{self.slot_name}' not provided, skipping check"
            )

        # 检查最小值
        if self.min_value is not None:
            if self.inclusive_min:
                if value < self.min_value:
                    return OracleResult(
                        oracle_id=self.get_id(),
                        passed=False,
                        details=f"{self.slot_name}={value} is less than minimum {self.min_value}",
                        violated_slots=[self.slot_name],
                        evidence={"value": value, "min": self.min_value, "inclusive": True}
                    )
            else:
                if value <= self.min_value:
                    return OracleResult(
                        oracle_id=self.get_id(),
                        passed=False,
                        details=f"{self.slot_name}={value} is less than or equal to minimum {self.min_value}",
                        violated_slots=[self.slot_name],
                        evidence={"value": value, "min": self.min_value, "inclusive": False}
                    )

        # 检查最大值
        if self.max_value is not None:
            if self.inclusive_max:
                if value > self.max_value:
                    return OracleResult(
                        oracle_id=self.get_id(),
                        passed=False,
                        details=f"{self.slot_name}={value} is greater than maximum {self.max_value}",
                        violated_slots=[self.slot_name],
                        evidence={"value": value, "max": self.max_value, "inclusive": True}
                    )
            else:
                if value >= self.max_value:
                    return OracleResult(
                        oracle_id=self.get_id(),
                        passed=False,
                        details=f"{self.slot_name}={value} is greater than or equal to maximum {self.max_value}",
                        violated_slots=[self.slot_name],
                        evidence={"value": value, "max": self.max_value, "inclusive": False}
                    )

        # 通过检查
        return OracleResult(
            oracle_id=self.get_id(),
            passed=True,
            details=f"{self.slot_name}={value} is within range [{self.min_value}, {self.max_value}]"
        )


# ================================================================
# Enum Constraint Oracle
# ================================================================

class EnumConstraintOracle(OracleChecker):
    """枚举约束 Oracle

    检查某个 slot 的值是否在允许的枚举列表中

    Example:
        metric_type in ["L2", "IP", "COSINE"]
    """

    def __init__(
        self,
        slot_name: str,
        allowed_values: List[Any],
        strict: bool = True,
        severity: Severity = Severity.HIGH
    ):
        """初始化枚举约束 Oracle

        Args:
            slot_name: 要检查的槽名称
            allowed_values: 允许的值列表
            strict: 是否严格匹配（False 时允许其他值，仅警告）
            severity: 严重性级别
        """
        super().__init__()
        self.slot_name = slot_name
        self.allowed_values = allowed_values
        self.strict = strict
        self._severity = severity

    def get_definition(self) -> OracleDefinition:
        """获取 Oracle 定义"""
        return OracleDefinition(
            oracle_id=f"enum_{self.slot_name}",
            name=f"{self.slot_name} Enum Constraint",
            category=OracleCategory.CONSISTENCY,
            description=f"{self.slot_name} must be one of {self.allowed_values}",
            trigger_condition=TriggerCondition(
                required_slots={self.slot_name: None}
            ),
            validation_logic=ValidationLogic(root=None),
            severity=self._severity,
            evidence_required=False
        )

    def check(self, test_case: TestCase, result: ExecutionResult) -> OracleResult:
        """执行枚举检查"""
        value = test_case.slot_values.get(self.slot_name)

        if value is None:
            return OracleResult(
                oracle_id=self.get_id(),
                passed=True,
                details=f"Slot '{self.slot_name}' not provided, skipping check"
            )

        passed = value in self.allowed_values

        return OracleResult(
            oracle_id=self.get_id(),
            passed=passed,
            details=f"{self.slot_name}={value} is {'allowed' if passed else 'not allowed'} (expected: {self.allowed_values})",
            violated_slots=[self.slot_name] if not passed else None,
            evidence={"value": value, "allowed_values": self.allowed_values}
        )


# ================================================================
# Relational Constraint Oracle
# ================================================================

class RelationalConstraintOracle(OracleChecker):
    """关系约束 Oracle

    检查两个 slot 之间的关系是否满足

    Example:
        search_range >= top_k
    """

    def __init__(
        self,
        left_slot: str,
        operator: ComparisonOperator,
        right_slot: str,
        severity: Severity = Severity.HIGH
    ):
        """初始化关系约束 Oracle

        Args:
            left_slot: 左侧槽名称
            operator: 比较操作符
            right_slot: 右侧槽名称
            severity: 严重性级别
        """
        super().__init__()
        self.left_slot = left_slot
        self.operator = operator
        self.right_slot = right_slot
        self._severity = severity

    def get_definition(self) -> OracleDefinition:
        """获取 Oracle 定义"""
        return OracleDefinition(
            oracle_id=f"relational_{self.left_slot}_{self.right_slot}",
            name=f"{self.left_slot} {self.operator.value} {self.right_slot}",
            category=OracleCategory.CONSISTENCY,
            description=f"{self.left_slot} must be {self.operator.value} {self.right_slot}",
            trigger_condition=TriggerCondition(
                required_slots={self.left_slot: None, self.right_slot: None}
            ),
            validation_logic=ValidationLogic(root=None),
            severity=self._severity,
            evidence_required=False
        )

    def check(self, test_case: TestCase, result: ExecutionResult) -> OracleResult:
        """执行关系检查"""
        left_value = test_case.slot_values.get(self.left_slot)
        right_value = test_case.slot_values.get(self.right_slot)

        # 如果任一值不存在，跳过检查
        if left_value is None or right_value is None:
            return OracleResult(
                oracle_id=self.get_id(),
                passed=True,
                details=f"Skipping check: {self.left_slot}={left_value}, {self.right_slot}={right_value}"
            )

        # 执行比较
        passed = False
        if self.operator == ComparisonOperator.EQ:
            passed = left_value == right_value
        elif self.operator == ComparisonOperator.NE:
            passed = left_value != right_value
        elif self.operator == ComparisonOperator.GT:
            passed = left_value > right_value
        elif self.operator == ComparisonOperator.GE:
            passed = left_value >= right_value
        elif self.operator == ComparisonOperator.LT:
            passed = left_value < right_value
        elif self.operator == ComparisonOperator.LE:
            passed = left_value <= right_value
        else:
            return OracleResult(
                oracle_id=self.get_id(),
                passed=True,
                details=f"Unsupported operator: {self.operator}"
            )

        return OracleResult(
            oracle_id=self.get_id(),
            passed=passed,
            details=f"{self.left_slot}={left_value} {self.operator.value} {self.right_slot}={right_value}: {'passed' if passed else 'failed'}",
            violated_slots=[self.left_slot] if not passed else None,
            evidence={
                "left_value": left_value,
                "operator": self.operator.value,
                "right_value": right_value
            }
        )


# ================================================================
# Status Validation Oracle
# ================================================================

class StatusValidationOracle(OracleChecker):
    """状态验证 Oracle

    检查操作结果状态是否符合预期
    """

    def __init__(
        self,
        expected_status: str = "SUCCESS",
        severity: Severity = Severity.HIGH
    ):
        """初始化状态验证 Oracle

        Args:
            expected_status: 期望的状态（SUCCESS 或 FAILURE）
            severity: 严重性级别
        """
        super().__init__()
        self.expected_status = expected_status
        self._severity = severity

    def get_definition(self) -> OracleDefinition:
        """获取 Oracle 定义"""
        return OracleDefinition(
            oracle_id="status_validation",
            name="Status Validation",
            category=OracleCategory.CORRECTNESS,
            description=f"Operation status must be {self.expected_status}",
            trigger_condition=TriggerCondition(),
            validation_logic=ValidationLogic(root=None),
            severity=self._severity,
            evidence_required=False
        )

    def can_check(self, test_case: TestCase) -> bool:
        """总是可以检查"""
        return True

    def check(self, test_case: TestCase, result: ExecutionResult) -> OracleResult:
        """执行状态检查"""
        # Convert status to string for comparison and JSON serialization
        actual_status = result.status.value if hasattr(result.status, 'value') else str(result.status)

        passed = actual_status == self.expected_status

        return OracleResult(
            oracle_id=self.get_id(),
            passed=passed,
            details=f"Status is {actual_status}, expected {self.expected_status}: {'passed' if passed else 'failed'}",
            evidence={"actual_status": actual_status, "expected_status": self.expected_status}
        )


__all__ = [
    "RangeConstraintOracle",
    "EnumConstraintOracle",
    "RelationalConstraintOracle",
    "StatusValidationOracle",
]
