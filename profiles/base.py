"""
Profile Plugin Base Class

定义 Profile Plugin 抽象基类，提供数据库特化逻辑的接口规范。
"""

from abc import ABC, abstractmethod
from typing import Optional, Any

from oracle.base import TestCase


# ================================================================
# Base Profile Plugin
# ================================================================

class BaseProfilePlugin(ABC):
    """数据库特化逻辑基类

    职责：
    - 提供 skip 逻辑 (过滤不支持的测试)
    - 提供结果后处理 (标准化结果格式)

    不允许：
    - 声明能力 (由 Adapter 提供)
    - 定义 Constraint (由 Contract 提供)

    设计原则：
    1. 保持简单 - 只关注数据库特化逻辑
    2. 可组合 - 多个 Profile 可以组合使用
    3. 可测试 - 每个方法都可以独立测试

    Example:
        >>> class SeekDBProfilePlugin(BaseProfilePlugin):
        ...     def should_skip_test(self, test_case: TestCase) -> Optional[str]:
        ...         # SeekDB: COSINE + HNSW 暂不支持
        ...         if (test_case.slot_values.get('metric_type') == 'COSINE' and
        ...             test_case.slot_values.get('index_type') == 'HNSW'):
        ...             return "COSINE + HNSW 暂不支持"
        ...         return None
        ...
        ...     def post_process_result(self, result: Any) -> Any:
        ...         # 统一结果格式
        ...         if isinstance(result, dict):
        ...             return SearchResult(
        ...                 ids=result.get('ids', []),
        ...                 scores=result.get('scores', []),
        ...                 total=result.get('total', 0)
        ...             )
        ...         return result
    """

    def __init__(self, name: Optional[str] = None):
        """初始化 Profile Plugin

        Args:
            name: Plugin 名称（可选，默认使用类名）
        """
        self._name = name or self.__class__.__name__

    def get_name(self) -> str:
        """获取 Plugin 名称

        Returns:
            str: Plugin 名称
        """
        return self._name

    # ================================================================
    # Abstract Methods (必须实现)
    # ================================================================

    @abstractmethod
    def should_skip_test(self, test_case: TestCase) -> Optional[str]:
        """判断是否跳过某个测试

        此方法用于过滤不支持的测试场景。当测试条件不符合数据库特性时，
        返回跳过原因，测试将被标记为 PRECONDITION_FAILED。

        Args:
            test_case: 测试用例

        Returns:
            Optional[str]: 跳过原因，None 表示不跳过

        Example:
            >>> def should_skip_test(self, test_case: TestCase) -> Optional[str]:
            ...     # 检查维度范围
            ...     dimension = test_case.slot_values.get('dimension')
            ...     if dimension is not None and dimension > 32768:
            ...         return f"Dimension {dimension} exceeds maximum 32768"
            ...
            ...     # 检查索引类型组合
            ...     metric = test_case.slot_values.get('metric_type')
            ...     index = test_case.slot_values.get('index_type')
            ...     if metric == 'COSINE' and index == 'HNSW':
            ...         return "COSINE + HNSW not supported"
            ...
            ...     return None  # 不跳过

        Note:
            - 返回 None 表示测试应该继续执行
            - 返回字符串表示测试应该被跳过
            - 跳过原因应清晰、具体，便于调试
        """
        pass

    @abstractmethod
    def post_process_result(self, result: Any) -> Any:
        """结果后处理

        此方法用于标准化或转换测试结果，使不同数据库返回的结果格式一致。

        Args:
            result: 原始结果 (来自 Adapter.execute_test)

        Returns:
            Any: 处理后的结果

        Example:
            >>> def post_process_result(self, result: Any) -> Any:
            ...     # 处理字典结果
            ...     if isinstance(result, dict):
            ...         # 提取必要字段
            ...         return SearchResult(
            ...             ids=result.get('ids', []),
            ...             scores=result.get('scores', []),
            ...             total=result.get('total', 0)
            ...         )
            ...
            ...     # 处理其他类型
            ...     return result

        Note:
            - 应该处理所有可能的输入类型
            - 如果无法处理，考虑记录日志并返回原始结果
            - 不应该抛出异常（除非是严重的数据格式错误）
        """
        pass

    # ================================================================
    # Optional Methods (可选实现)
    # ================================================================

    def validate_test_case(self, test_case: TestCase) -> Optional[str]:
        """验证测试用例的合法性

        此方法是可选的，用于在跳过测试之前进行更深层次的验证。
        默认实现返回 None（不验证）。

        Args:
            test_case: 测试用例

        Returns:
            Optional[str]: 验证失败原因，None 表示通过

        Example:
            >>> def validate_test_case(self, test_case: TestCase) -> Optional[str]:
            ...     # 验证必需参数
            ...     required = ['dimension', 'metric_type']
            ...     for param in required:
            ...         if param not in test_case.slot_values:
            ...             return f"Missing required parameter: {param}"
            ...     return None
        """
        return None

    def get_supported_operations(self) -> list:
        """获取支持的操作列表

        此方法是可选的，用于声明此 Profile 支持的操作。
        默认实现返回空列表（支持所有操作）。

        Returns:
            list: 支持的操作列表，如 ['search', 'insert', 'delete']

        Example:
            >>> def get_supported_operations(self) -> list:
            ...     return ['search', 'insert', 'update', 'delete']
        """
        return []

    def get_description(self) -> str:
        """获取 Plugin 描述

        此方法用于提供关于此 Plugin 的详细信息。

        Returns:
            str: Plugin 描述
        """
        return f"{self._name} - Profile Plugin for database-specific logic"

    def __repr__(self) -> str:
        """字符串表示"""
        return f"{self.__class__.__name__}(name='{self._name}')"


# ================================================================
# Helper Classes
# ================================================================

class SkipDecision:
    """跳过决策结果

    用于封装 should_skip_test 的返回值，提供更多信息。

    Attributes:
        should_skip: 是否跳过
        reason: 跳过原因
        category: 跳过类别
    """

    NOT_SUPPORTED = "not_supported"
    CONFIG_LIMITATION = "config_limitation"
    VERSION_MISMATCH = "version_mismatch"
    TEMPORARY_DISABLE = "temporary_disable"
    OTHER = "other"

    def __init__(
        self,
        should_skip: bool,
        reason: Optional[str] = None,
        category: str = OTHER
    ):
        """初始化跳过决策

        Args:
            should_skip: 是否跳过
            reason: 跳过原因
            category: 跳过类别
        """
        self.should_skip = should_skip
        self.reason = reason
        self.category = category

    @classmethod
    def do_not_skip(cls) -> 'SkipDecision':
        """创建不跳过的决策"""
        return cls(should_skip=False)

    @classmethod
    def skip_with_reason(cls, reason: str, category: str = OTHER) -> 'SkipDecision':
        """创建跳过的决策"""
        return cls(should_skip=True, reason=reason, category=category)

    def to_skip_reason(self) -> Optional[str]:
        """转换为 skip_reason 字符串"""
        if not self.should_skip:
            return None
        prefix = f"[{self.category}] " if self.category != self.OTHER else ""
        return f"{prefix}{self.reason}"


__all__ = [
    "BaseProfilePlugin",
    "SkipDecision",
]
