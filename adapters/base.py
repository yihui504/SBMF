# adapters/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from core.models import *

@dataclass
class Capabilities:
    """数据库能力声明

    声明数据库支持的操作、向量类型、索引类型等能力。
    这是 Capabilities 的唯一来源。
    """
    supported_operations: List[str]
    supported_vector_types: List[str]
    supported_index_types: List[str]
    concurrent_operations: bool
    max_concurrent_requests: Optional[int]
    transaction_support: bool
    distributed: bool


class BaseAdapter(ABC):
    """数据库适配器基类

    职责：
    - 声明数据库能力
    - 语义槽到参数名的映射
    - 参数值转换
    - 错误分类
    - 执行测试
    """

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
    def execute_test(self, test_case: SemanticCase) -> ExecutionResult:
        """执行测试用例

        Args:
            test_case: 测试用例

        Returns:
            ExecutionResult: 执行结果

        Raises:
            Exception: 执行过程中的异常（由调用方分类）
        """
        pass
