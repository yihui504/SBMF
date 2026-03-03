# -*- coding: utf-8 -*-
"""
Simplified Anomaly Detection Adapter

提供简化的异常检测 API，解决 StatisticalAnomalyDetector 的兼容性问题。
"""
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from detectors import StatisticalAnomalyDetector, AnomalyResult, AnomalyType
from detectors.base import MetricData


@dataclass
class SimpleAnomalyResult:
    """简化的异常检测结果"""
    is_anomaly: bool
    anomaly_score: float
    anomaly_type: str
    threshold: float
    value: float
    z_score: Optional[float] = None
    message: str = ""


class AnomalyDetectionAdapter:
    """
    异常检测适配器

    提供简化的 API 来使用 StatisticalAnomalyDetector，
    解决原 API 复杂性问题。
    """

    def __init__(self, method: str = "z_score", threshold: float = 3.0):
        """
        初始化适配器

        Args:
            method: 检测方法 (z_score, iqr)
            threshold: 异常阈值
        """
        self.method = method
        self.threshold = threshold
        self.detector = StatisticalAnomalyDetector()
        self.history: List[float] = []

    def detect(self, value: float, history: Optional[List[float]] = None) -> SimpleAnomalyResult:
        """
        检测单个值是否异常

        Args:
            value: 要检测的值
            history: 历史数据列表，如果为 None 则使用内部历史

        Returns:
            SimpleAnomalyResult: 检测结果
        """
        # 使用提供的历史或内部历史
        data_points = history if history is not None else self.history

        # 更新内部历史
        if history is None:
            self.history.append(value)
        else:
            self.history = history + [value]

        # 如果数据点不足，返回正常
        if len(data_points) < 3:
            return SimpleAnomalyResult(
                is_anomaly=False,
                anomaly_score=0.0,
                anomaly_type="insufficient_data",
                threshold=self.threshold,
                value=value,
                message="Insufficient data for anomaly detection"
            )

        # 使用 Z-score 方法
        if self.method == "z_score":
            return self._detect_z_score(value, data_points)

        # 使用 IQR 方法
        elif self.method == "iqr":
            return self._detect_iqr(value, data_points)

        else:
            raise ValueError(f"Unknown method: {self.method}")

    def _detect_z_score(self, value: float, history: List[float]) -> SimpleAnomalyResult:
        """使用 Z-score 方法检测"""
        import statistics

        try:
            mean = statistics.mean(history)
            stdev = statistics.stdev(history) if len(history) > 1 else 0.0

            if stdev == 0:
                return SimpleAnomalyResult(
                    is_anomaly=False,
                    anomaly_score=0.0,
                    anomaly_type="stable",
                    threshold=self.threshold,
                    value=value,
                    z_score=0.0,
                    message="All values are identical"
                )

            z_score = abs((value - mean) / stdev)
            is_anomaly = z_score > self.threshold

            return SimpleAnomalyResult(
                is_anomaly=is_anomaly,
                anomaly_score=min(z_score / self.threshold, 1.0),
                anomaly_type="statistical",
                threshold=self.threshold,
                value=value,
                z_score=z_score,
                message=f"Z-score: {z_score:.2f} (threshold: {self.threshold})"
            )

        except Exception as e:
            return SimpleAnomalyResult(
                is_anomaly=False,
                anomaly_score=0.0,
                anomaly_type="error",
                threshold=self.threshold,
                value=value,
                message=f"Detection error: {e}"
            )

    def _detect_iqr(self, value: float, history: List[float]) -> SimpleAnomalyResult:
        """使用 IQR 方法检测"""
        import statistics

        try:
            sorted_data = sorted(history)
            n = len(sorted_data)

            q1_idx = n // 4
            q3_idx = 3 * n // 4
            q1 = sorted_data[q1_idx]
            q3 = sorted_data[q3_idx]
            iqr = q3 - q1

            if iqr == 0:
                return SimpleAnomalyResult(
                    is_anomaly=False,
                    anomaly_score=0.0,
                    anomaly_type="stable",
                    threshold=self.threshold,
                    value=value,
                    message="All values are identical"
                )

            # 定义异常边界
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            is_anomaly = value < lower_bound or value > upper_bound

            # 计算异常分数
            if value < lower_bound:
                distance = abs(value - lower_bound)
                score = min(distance / iqr, 1.0)
            elif value > upper_bound:
                distance = abs(value - upper_bound)
                score = min(distance / iqr, 1.0)
            else:
                score = 0.0

            return SimpleAnomalyResult(
                is_anomaly=is_anomaly,
                anomaly_score=score,
                anomaly_type="outlier",
                threshold=self.threshold,
                value=value,
                message=f"IQR bounds: [{lower_bound:.2f}, {upper_bound:.2f}]"
            )

        except Exception as e:
            return SimpleAnomalyResult(
                is_anomaly=False,
                anomaly_score=0.0,
                anomaly_type="error",
                threshold=self.threshold,
                value=value,
                message=f"Detection error: {e}"
            )

    def detect_batch(self, values: List[float]) -> List[SimpleAnomalyResult]:
        """
        批量检测多个值

        Args:
            values: 值列表

        Returns:
            List[SimpleAnomalyResult]: 检测结果列表
        """
        results = []

        for i, value in enumerate(values):
            history = values[:i] if i > 0 else []
            result = self.detect(value, history)
            results.append(result)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "method": self.method,
            "threshold": self.threshold,
            "history_size": len(self.history),
            "detection_count": len([v for v in self.history if len(self.history) > 3])
        }

    def clear_history(self) -> None:
        """清除历史数据"""
        self.history.clear()


# 兼容性包装器：保持与原有代码的兼容性
class AnomalyDetectorCompatibility:
    """
    兼容性包装器，提供与原验证脚本兼容的 API
    """

    def __init__(self, method: str = "z_score", threshold: float = 3.0):
        self.adapter = AnomalyDetectionAdapter(method=method, threshold=threshold)

    def detect(self, value: float, history: List[float]) -> SimpleAnomalyResult:
        """兼容接口：detect(value, history)"""
        return self.adapter.detect(value, history)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.adapter.get_stats()


__all__ = [
    "AnomalyDetectionAdapter",
    "SimpleAnomalyResult",
    "AnomalyDetectorCompatibility"
]
