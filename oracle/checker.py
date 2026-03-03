"""
Oracle Checker Base Class

定义 Oracle 检查器的抽象基类。
"""

from abc import ABC, abstractmethod
from typing import Optional

from oracle.base import (
    OracleDefinition,
    OracleResult,
    OracleCategory,
    TestCase,
    ExecutionResult,
    TriggerCondition,
)


class OracleChecker(ABC):
    """Oracle 检查器基类

    职责：
    - 定义 Oracle
    - 检查是否可检查
    - 执行检查

    所有 Oracle 检查器都必须继承此类并实现抽象方法。
    """

    def __init__(self):
        """初始化 Oracle 检查器"""
        self._definition: Optional[OracleDefinition] = None

    @abstractmethod
    def get_definition(self) -> OracleDefinition:
        """获取 Oracle 定义

        Returns:
            OracleDefinition: Oracle 定义

        Example:
            >>> def get_definition(self) -> OracleDefinition:
            ...     return OracleDefinition(
            ...         oracle_id="dimension_positive",
            ...         name="Dimension Must Be Positive",
            ...         category=OracleCategory.CORRECTNESS,
            ...         description="Dimension must be positive",
            ...         trigger_condition=TriggerCondition(
            ...             required_slots={"dimension": None}
            ...         ),
            ...         validation_logic=ValidationLogic(...),
            ...         severity=Severity.HIGH,
            ...         evidence_required=False
            ...     )
        """
        pass

    def can_check(self, test_case: TestCase) -> bool:
        """判断是否可检查

        默认实现：检查触发条件是否满足

        Args:
            test_case: 测试用例

        Returns:
            bool: 是否可检查

        Example:
            >>> def can_check(self, test_case: TestCase) -> bool:
            ...     # 检查必需的槽是否存在
            ...     required_slot = "dimension"
            ...     return required_slot in test_case.slot_values
        """
        definition = self.get_definition()
        trigger = definition.trigger_condition

        # 检查 required_operations
        if trigger.required_operations:
            if test_case.operation not in trigger.required_operations:
                return False

        # 检查 required_slots
        if trigger.required_slots:
            for slot_name in trigger.required_slots:
                if slot_name not in test_case.slot_values:
                    return False

        # 检查 exclude_conditions
        # TODO: Phase 4 实现 AST 评估

        return True

    @abstractmethod
    def check(self, test_case: TestCase, result: ExecutionResult) -> OracleResult:
        """执行 Oracle 检查

        Args:
            test_case: 测试用例
            result: 执行结果

        Returns:
            OracleResult: 检查结果

        Example:
            >>> def check(self, test_case: TestCase, result: ExecutionResult) -> OracleResult:
            ...     dimension = test_case.slot_values.get("dimension")
            ...     passed = dimension > 0
            ...     return OracleResult(
            ...         oracle_id=self.get_definition().oracle_id,
            ...         passed=passed,
            ...         details=f"Dimension is {dimension}, {'positive' if passed else 'negative'}",
            ...         violated_slots=["dimension"] if not passed else None
            ...     )
        """
        pass

    def get_id(self) -> str:
        """获取 Oracle ID

        Returns:
            str: Oracle ID
        """
        return self.get_definition().oracle_id

    def get_category(self) -> OracleCategory:
        """获取 Oracle 类别

        Returns:
            OracleCategory: Oracle 类别
        """
        return self.get_definition().category

    def get_severity(self) -> str:
        """获取严重性级别

        Returns:
            str: 严重性级别 (HIGH/MEDIUM/LOW)
        """
        return self.get_definition().severity.value


# ================================================================
# Oracle Checker Registry
# ================================================================

class OracleCheckerRegistry:
    """Oracle 检查器注册表

    管理所有可用的 Oracle 检查器
    """

    def __init__(self):
        """初始化注册表"""
        self._checkers: Dict[str, OracleChecker] = {}

    def register(self, checker: OracleChecker) -> None:
        """注册 Oracle 检查器

        Args:
            checker: Oracle 检查器实例

        Raises:
            ValueError: 如果 Oracle ID 已存在
        """
        oracle_id = checker.get_id()
        if oracle_id in self._checkers:
            raise ValueError(f"Oracle ID '{oracle_id}' already registered")

        self._checkers[oracle_id] = checker

    def get(self, oracle_id: str) -> Optional[OracleChecker]:
        """获取 Oracle 检查器

        Args:
            oracle_id: Oracle ID

        Returns:
            Optional[OracleChecker]: Oracle 检查器，如果不存在则返回 None
        """
        return self._checkers.get(oracle_id)

    def get_all(self) -> list:
        """获取所有已注册的 Oracle 检查器

        Returns:
            list: Oracle 检查器列表
        """
        return list(self._checkers.values())

    def get_by_category(self, category: OracleCategory) -> list:
        """按类别获取 Oracle 检查器

        Args:
            category: Oracle 类别

        Returns:
            list: 该类别的 Oracle 检查器列表
        """
        return [
            checker for checker in self._checkers.values()
            if checker.get_category() == category
        ]

    def clear(self) -> None:
        """清空注册表"""
        self._checkers.clear()


# 全局注册表实例
_global_registry = OracleCheckerRegistry()


def register_oracle(checker: OracleChecker) -> None:
    """注册 Oracle 检查器到全局注册表

    Args:
        checker: Oracle 检查器实例
    """
    _global_registry.register(checker)


def get_oracle(oracle_id: str) -> Optional[OracleChecker]:
    """从全局注册表获取 Oracle 检查器

    Args:
        oracle_id: Oracle ID

    Returns:
        Optional[OracleChecker]: Oracle 检查器，如果不存在则返回 None
    """
    return _global_registry.get(oracle_id)


def get_all_oracles() -> list:
    """获取全局注册表中的所有 Oracle 检查器

    Returns:
        list: Oracle 检查器列表
    """
    return _global_registry.get_all()


def get_oracles_by_category(category: OracleCategory) -> list:
    """按类别从全局注册表获取 Oracle 检查器

    Args:
        category: Oracle 类别

    Returns:
        list: 该类别的 Oracle 检查器列表
    """
    return _global_registry.get_by_category(category)


__all__ = [
    # Base Class
    "OracleChecker",
    # Registry
    "OracleCheckerRegistry",
    # Global Registry Functions
    "register_oracle",
    "get_oracle",
    "get_all_oracles",
    "get_oracles_by_category",
    # Global Registry
    "_global_registry",
]
