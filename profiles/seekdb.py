"""
SeekDB Profile Plugin

SeekDB 特定的 Profile Plugin 实现，包含数据库特定的测试过滤和结果后处理逻辑。
"""

import logging
from typing import Optional, Any, Dict, List

from profiles.base import BaseProfilePlugin
from oracle.base import TestCase


# ================================================================
# SeekDB Constants
# ================================================================

class SeekDBConstants:
    """SeekDB 常量定义"""

    # 支持的度量类型
    SUPPORTED_METRIC_TYPES = ["L2", "IP", "COSINE"]

    # 支持的索引类型
    SUPPORTED_INDEX_TYPES = ["IVF", "HNSW", "FLAT", "IVF_PQ"]

    # 不支持的组合
    UNSUPPORTED_COMBINATIONS = [
        ("COSINE", "HNSW"),  # COSINE + HNSW 暂不支持
    ]

    # 维度限制
    MIN_DIMENSION = 1
    MAX_DIMENSION = 32768

    # ef_construction 限制
    MAX_EF_CONSTRUCTION = 500

    # top_k 限制
    MAX_TOP_K = 10000

    # search_range 限制
    MAX_SEARCH_RANGE = 65535


# ================================================================
# SeekDB Profile Plugin
# ================================================================

class SeekDBProfilePlugin(BaseProfilePlugin):
    """SeekDB 特化 Profile Plugin

    职责：
    - 过滤 SeekDB 不支持的测试场景
    - 标准化 SeekDB 测试结果

    Skip 逻辑：
    - COSINE + HNSW 组合不支持
    - 维度超出 [1, 32768] 范围
    - ef_construction > 500
    - 其他已知限制

    后处理逻辑：
    - 统一搜索结果格式
    - 处理分页信息
    - 提取元数据
    """

    def __init__(self, enable_logging: bool = True):
        """初始化 SeekDB Profile Plugin

        Args:
            enable_logging: 是否启用日志记录（默认启用）
        """
        super().__init__(name="SeekDBProfilePlugin")
        self.enable_logging = enable_logging

        # 配置日志
        self._setup_logging()

    def _setup_logging(self):
        """配置日志记录器"""
        if self.enable_logging:
            self.logger = logging.getLogger(f"{self.__class__.__name__}")
            self.logger.setLevel(logging.DEBUG)

            # 避免重复添加 handler
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                handler.setLevel(logging.DEBUG)
                formatter = logging.Formatter(
                    '[%(name)s] %(levelname)s: %(message)s'
                )
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
        else:
            self.logger = None

    def _log_skip(self, test_case: TestCase, reason: str):
        """记录跳过日志"""
        if self.logger:
            self.logger.info(
                f"Skipping test '{test_case.test_id}': {reason}"
            )

    def _log_debug(self, message: str):
        """记录调试日志"""
        if self.logger:
            self.logger.debug(message)

    # ================================================================
    # Skip Logic
    # ================================================================

    def should_skip_test(self, test_case: TestCase) -> Optional[str]:
        """判断是否跳过某个测试

        Args:
            test_case: 测试用例

        Returns:
            Optional[str]: 跳过原因，None 表示不跳过
        """
        slot_values = test_case.slot_values

        # 1. 检查不支持的索引类型 + 度量类型组合
        combination_skip = self._check_unsupported_combination(slot_values)
        if combination_skip:
            self._log_skip(test_case, combination_skip)
            return combination_skip

        # 2. 检查维度范围
        dimension_skip = self._check_dimension_range(slot_values)
        if dimension_skip:
            self._log_skip(test_case, dimension_skip)
            return dimension_skip

        # 3. 检查 ef_construction
        ef_skip = self._check_ef_construction(slot_values)
        if ef_skip:
            self._log_skip(test_case, ef_skip)
            return ef_skip

        # 4. 检查 top_k
        top_k_skip = self._check_top_k(slot_values)
        if top_k_skip:
            self._log_skip(test_case, top_k_skip)
            return top_k_skip

        # 5. 检查 search_range
        search_range_skip = self._check_search_range(slot_values)
        if search_range_skip:
            self._log_skip(test_case, search_range_skip)
            return search_range_skip

        # 6. 检查度量类型是否支持
        metric_skip = self._check_metric_type(slot_values)
        if metric_skip:
            self._log_skip(test_case, metric_skip)
            return metric_skip

        # 7. 检查索引类型是否支持
        index_skip = self._check_index_type(slot_values)
        if index_skip:
            self._log_skip(test_case, index_skip)
            return index_skip

        # 通过所有检查
        self._log_debug(f"Test '{test_case.test_id}' passed all skip checks")
        return None

    def _check_unsupported_combination(self, slot_values: Dict[str, Any]) -> Optional[str]:
        """检查不支持的组合"""
        metric_type = slot_values.get('metric_type')
        index_type = slot_values.get('index_type')

        if not metric_type or not index_type:
            return None

        for (metric, index) in SeekDBConstants.UNSUPPORTED_COMBINATIONS:
            if metric_type == metric and index_type == index:
                return f"{metric_type} + {index_type} is not supported by SeekDB"

        return None

    def _check_dimension_range(self, slot_values: Dict[str, Any]) -> Optional[str]:
        """检查维度范围"""
        dimension = slot_values.get('dimension')

        if dimension is None:
            return None

        if not isinstance(dimension, (int, float)):
            return f"Dimension must be a number, got {type(dimension).__name__}"

        if dimension < SeekDBConstants.MIN_DIMENSION:
            return f"Dimension {dimension} is below minimum {SeekDBConstants.MIN_DIMENSION}"

        if dimension > SeekDBConstants.MAX_DIMENSION:
            return f"Dimension {dimension} exceeds maximum {SeekDBConstants.MAX_DIMENSION}"

        return None

    def _check_ef_construction(self, slot_values: Dict[str, Any]) -> Optional[str]:
        """检查 ef_construction 参数"""
        ef_construction = slot_values.get('ef_construction')

        if ef_construction is None:
            return None

        if not isinstance(ef_construction, int):
            return f"ef_construction must be an integer, got {type(ef_construction).__name__}"

        if ef_construction > SeekDBConstants.MAX_EF_CONSTRUCTION:
            return f"ef_construction {ef_construction} exceeds maximum {SeekDBConstants.MAX_EF_CONSTRUCTION}"

        return None

    def _check_top_k(self, slot_values: Dict[str, Any]) -> Optional[str]:
        """检查 top_k 参数"""
        top_k = slot_values.get('top_k')

        if top_k is None:
            return None

        if not isinstance(top_k, int):
            return f"top_k must be an integer, got {type(top_k).__name__}"

        if top_k < 1:
            return f"top_k must be at least 1, got {top_k}"

        if top_k > SeekDBConstants.MAX_TOP_K:
            return f"top_k {top_k} exceeds maximum {SeekDBConstants.MAX_TOP_K}"

        return None

    def _check_search_range(self, slot_values: Dict[str, Any]) -> Optional[str]:
        """检查 search_range 参数"""
        search_range = slot_values.get('search_range')

        if search_range is None:
            return None

        if not isinstance(search_range, int):
            return f"search_range must be an integer, got {type(search_range).__name__}"

        if search_range < 1:
            return f"search_range must be at least 1, got {search_range}"

        if search_range > SeekDBConstants.MAX_SEARCH_RANGE:
            return f"search_range {search_range} exceeds maximum {SeekDBConstants.MAX_SEARCH_RANGE}"

        return None

    def _check_metric_type(self, slot_values: Dict[str, Any]) -> Optional[str]:
        """检查度量类型是否支持"""
        metric_type = slot_values.get('metric_type')

        if metric_type is None:
            return None

        if metric_type not in SeekDBConstants.SUPPORTED_METRIC_TYPES:
            return f"Metric type '{metric_type}' is not supported. Supported: {SeekDBConstants.SUPPORTED_METRIC_TYPES}"

        return None

    def _check_index_type(self, slot_values: Dict[str, Any]) -> Optional[str]:
        """检查索引类型是否支持"""
        index_type = slot_values.get('index_type')

        if index_type is None:
            return None

        if index_type not in SeekDBConstants.SUPPORTED_INDEX_TYPES:
            return f"Index type '{index_type}' is not supported. Supported: {SeekDBConstants.SUPPORTED_INDEX_TYPES}"

        return None

    # ================================================================
    # Post-Process Logic
    # ================================================================

    def post_process_result(self, result: Any) -> Any:
        """结果后处理

        标准化 SeekDB 测试结果格式。

        Args:
            result: 原始结果

        Returns:
            Any: 处理后的结果
        """
        self._log_debug(f"Post-processing result of type: {type(result).__name__}")

        # 处理字典结果
        if isinstance(result, dict):
            return self._process_dict_result(result)

        # 处理列表结果
        if isinstance(result, list):
            return self._process_list_result(result)

        # 其他类型直接返回
        return result

    def _process_dict_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """处理字典类型结果"""
        processed = result.copy()

        # 标记为已处理
        processed['_processed_by'] = self.get_name()

        # 确保有 ids 字段
        if 'ids' not in processed:
            processed['ids'] = []

        # 标准化分数字段 (score -> scores) - 必须在设置默认 scores 之前
        if 'score' in processed:
            # 单个 score 转换为 scores 列表
            if isinstance(processed['score'], list):
                processed['scores'] = processed['score']
            else:
                processed['scores'] = [processed['score']]
            del processed['score']

        # 确保有 scores 字段 (如果还没有设置)
        if 'scores' not in processed:
            processed['scores'] = []

        # 确保 total 字段存在
        if 'total' not in processed:
            # 如果有 ids，用 ids 长度作为 total
            if 'ids' in processed and isinstance(processed['ids'], list):
                processed['total'] = len(processed['ids'])
            else:
                processed['total'] = 0

        self._log_debug(f"Processed dict result: {len(processed.get('ids', []))} items")
        return processed

    def _process_list_result(self, result: List[Any]) -> Dict[str, Any]:
        """处理列表类型结果"""
        # 如果是整数列表，假设是 ids
        if all(isinstance(x, int) for x in result):
            return {
                'ids': result,
                'scores': [],
                'total': len(result),
                '_processed_by': self.get_name()
            }

        # 如果是字典列表，提取 ids 和 scores
        if all(isinstance(x, dict) for x in result):
            ids = []
            scores = []
            for item in result:
                if 'id' in item:
                    ids.append(item['id'])
                if 'score' in item or 'distance' in item:
                    scores.append(item.get('score', item.get('distance')))

            return {
                'ids': ids,
                'scores': scores,
                'total': len(result),
                '_processed_by': self.get_name()
            }

        # 其他列表类型，包装为字典
        return {
            'data': result,
            'total': len(result),
            '_processed_by': self.get_name()
        }

    # ================================================================
    # Optional Methods
    # ================================================================

    def get_supported_operations(self) -> List[str]:
        """获取支持的操作列表"""
        return [
            'create_collection',
            'drop_collection',
            'create_index',
            'drop_index',
            'insert',
            'delete',
            'search',
            'get',
            'count',
        ]

    def get_description(self) -> str:
        """获取 Plugin 描述"""
        return (
            f"{self.get_name()} - SeekDB specific profile plugin. "
            f"Handles SeekDB-specific skip logic and result post-processing. "
            f"Supports metric types: {SeekDBConstants.SUPPORTED_METRIC_TYPES}"
        )


__all__ = [
    "SeekDBProfilePlugin",
    "SeekDBConstants",
]
