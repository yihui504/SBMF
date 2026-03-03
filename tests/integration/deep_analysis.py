# -*- coding: utf-8 -*-
"""
Deep Analysis of Product-Level Bugs
深度分析产品级Bug
"""
import sys
import time
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

from agent.runtime import AgentRuntime, AgentConfig
from agent.memory import AgentMemory, MemoryType
from adapters import SeekDBAdapter
from detectors import AnomalyDetectionAdapter
from core.models import SemanticCase, SlotScope, ErrorCategory


class BugSeverity(Enum):
    """Bug严重程度"""
    CRITICAL = "critical"      # 崩溃、数据丢失
    HIGH = "high"             # 功能错误
    MEDIUM = "medium"         # 边界问题
    LOW = "low"               # 轻微问题


class BugCategory(Enum):
    """Bug类别"""
    PRODUCT_BUG = "product_bug"           # SeekDB产品bug
    FRAMEWORK_ISSUE = "framework_issue"   # 框架问题
    CONFIG_ERROR = "config_error"         # 配置错误
    EXPECTED_FAILURE = "expected_failure" # 预期失败（如非法参数）


@dataclass
class ProductBug:
    """产品Bug定义"""
    bug_id: str
    severity: BugSeverity
    category: BugCategory
    title: str
    description: str
    reproduction: Dict[str, Any]
    evidence: str
    impact: str
    recommendation: str


class DeepBugAnalyzer:
    """深度Bug分析器"""

    def __init__(self, host: str = "localhost", port: int = 2881):
        self.host = host
        self.port = port
        self.adapter = SeekDBAdapter(host=host, port=port)

        # Agent 组件
        agent_config = AgentConfig(
            agent_id="deep_analyzer",
            enable_monitoring=True,
            enable_memory=True
        )
        self.runtime = AgentRuntime(config=agent_config)
        self.memory = AgentMemory(agent_id="deep_analyzer")

        self.bugs: List[ProductBug] = []

    def analyze_stress_failures(self) -> List[ProductBug]:
        """分析压力测试中的失败"""
        print("\n" + "="*70)
        print("[*] Analyzing Stress Test Failures")
        print("="*70)

        found_bugs = []

        # 重新运行压力测试并详细记录每个失败
        for i in range(100):
            op_type = i % 3

            if op_type == 0:
                test_case = SemanticCase(
                    test_id=f"stress_search_{i}",
                    operation="search",
                    slot_values={"dimension": 128 + (i % 10) * 64, "top_k": 10 + (i % 5) * 10},
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.DATABASE
                )
            elif op_type == 1:
                test_case = SemanticCase(
                    test_id=f"stress_insert_{i}",
                    operation="insert",
                    slot_values={"dimension": 128 + (i % 5) * 64},
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.DATABASE
                )
            else:
                is_legal = (i % 2 == 0)
                test_case = SemanticCase(
                    test_id=f"stress_extreme_{i}",
                    operation="search",
                    slot_values={"dimension": 128 + i * 100, "top_k": 1000},
                    raw_parameters={},
                    is_legal=is_legal,
                    scope=SlotScope.DATABASE
                )

            response = self.adapter.execute_test(test_case)

            if response.status.value not in ["SUCCESS", "success"]:
                # 分析这个失败
                bug = self._classify_failure(test_case, response, i)
                if bug:
                    found_bugs.append(bug)
                    self._print_bug(bug)

        return found_bugs

    def _classify_failure(self, test_case: SemanticCase, response, index: int) -> ProductBug:
        """分类失败的类型"""

        error_str = str(response.error) if response.error else response.status.value
        test_id = test_case.test_id

        # 检查是否是框架问题
        if "not implemented" in error_str.lower():
            return ProductBug(
                bug_id=f"BUG_{index:03d}",
                severity=BugSeverity.LOW,
                category=BugCategory.FRAMEWORK_ISSUE,
                title="Framework: Operation Not Implemented",
                description=f"The operation '{test_case.operation}' is not implemented in the test adapter",
                reproduction={
                    "operation": test_case.operation,
                    "slot_values": test_case.slot_values
                },
                evidence=error_str,
                impact="Testing only - not a product bug",
                recommendation="Implement adapter operation or skip in tests"
            )

        # 检查是否是非法参数被正确拒绝
        if not test_case.is_legal:
            if any(x in error_str.lower() for x in ["invalid", "out of range", "not allowed"]):
                return ProductBug(
                    bug_id=f"BUG_{index:03d}",
                    severity=BugSeverity.LOW,
                    category=BugCategory.EXPECTED_FAILURE,
                    title="Expected: Invalid Parameter Rejected",
                    description=f"System correctly rejected invalid parameter: {test_case.slot_values}",
                    reproduction={
                        "operation": test_case.operation,
                        "invalid_params": test_case.slot_values
                    },
                    evidence=error_str,
                    impact="Positive - system validates inputs correctly",
                    recommendation="No action needed"
                )

        # 检查是否是产品Bug
        # 维度相关问题
        if "dimension" in error_str.lower():
            dim = test_case.slot_values.get("dimension", 0)

            # 检查是否是合理的维度被错误拒绝
            if test_case.is_legal and 1 <= dim <= 65536:
                severity = BugSeverity.HIGH if dim <= 10000 else BugSeverity.MEDIUM
                return ProductBug(
                    bug_id=f"BUG_{index:03d}",
                    severity=severity,
                    category=BugCategory.PRODUCT_BUG,
                    title=f"Product: Dimension Validation Error at {dim}",
                    description=f"Valid dimension {dim} was rejected with error",
                    reproduction={
                        "operation": test_case.operation,
                        "dimension": dim,
                        "other_params": {k: v for k, v in test_case.slot_values.items() if k != "dimension"}
                    },
                    evidence=error_str,
                    impact=f"Cannot perform operations with dimension={dim}",
                    recommendation="Review dimension validation logic in SeekDB"
                )

        # top_k 相关问题
        if "top_k" in error_str.lower():
            top_k = test_case.slot_values.get("top_k", 0)

            if test_case.is_legal and 1 <= top_k <= 10000:
                return ProductBug(
                    bug_id=f"BUG_{index:03d}",
                    severity=BugSeverity.HIGH,
                    category=BugCategory.PRODUCT_BUG,
                    title=f"Product: TopK Validation Error at {top_k}",
                    description=f"Valid top_k={top_k} was rejected",
                    reproduction={
                        "operation": test_case.operation,
                        "top_k": top_k,
                        "dimension": test_case.slot_values.get("dimension", 0)
                    },
                    evidence=error_str,
                    impact=f"Cannot search with top_k={top_k}",
                    recommendation="Review top_k parameter validation"
                )

        # 通用产品bug
        if test_case.is_legal:
            return ProductBug(
                bug_id=f"BUG_{index:03d}",
                severity=BugSeverity.MEDIUM,
                category=BugCategory.PRODUCT_BUG,
                title=f"Product: Unexpected Error on Legal Input",
                description=f"Legal test case failed with unexpected error",
                reproduction={
                    "operation": test_case.operation,
                    "slot_values": test_case.slot_values
                },
                evidence=error_str,
                impact="Operation failed unexpectedly",
                recommendation="Investigate error handling logic"
            )

        return None

    def _print_bug(self, bug: ProductBug):
        """打印Bug信息"""
        print(f"\n[*] Bug ID: {bug.bug_id}")
        print(f"    Category: {bug.category.value.upper()}")
        print(f"    Severity: {bug.severity.value.upper()}")
        print(f"    Title: {bug.title}")
        print(f"    Description: {bug.description}")
        print(f"    Evidence: {bug.evidence}")
        print(f"    Impact: {bug.impact}")
        print(f"    Recommendation: {bug.recommendation}")
        print(f"    Reproduction: {bug.reproduction}")

    def analyze_edge_cases(self) -> List[ProductBug]:
        """分析边缘情况"""
        print("\n" + "="*70)
        print("[*] Analyzing Edge Cases")
        print("="*70)

        found_bugs = []

        # 测试2的幂次方边界
        edge_cases = [
            # (dimension, top_k, should_succeed, description)
            (0, 10, False, "Zero dimension"),
            (1, 1, True, "Minimum dimension and top_k"),
            (2, 10, True, "Power of 2 (small)"),
            (128, 10, True, "Common dimension"),
            (256, 100, True, "Power of 2 (medium)"),
            (512, 1000, True, "Power of 2 (large)"),
            (1024, 10000, True, "Large dimension with large top_k"),
            (65536, 10, True, "Maximum dimension"),
            (65537, 10, False, "Beyond maximum dimension"),
            (100, 0, False, "Zero top_k"),
            (100, 10001, False, "Beyond maximum top_k"),
            (8, 1000, True, "Small dimension large top_k"),
            (10000, 1, True, "Large dimension small top_k"),
        ]

        for dim, top_k, should_succeed, desc in edge_cases:
            test_case = SemanticCase(
                test_id=f"edge_{dim}_{top_k}",
                operation="search",
                slot_values={"dimension": dim, "top_k": top_k},
                raw_parameters={},
                is_legal=should_succeed,
                scope=SlotScope.DATABASE
            )

            response = self.adapter.execute_test(test_case)

            actual_success = response.status.value in ["SUCCESS", "success"]

            # 检查行为是否符合预期
            if should_succeed and not actual_success:
                # 应该成功但失败了 - 可能是bug
                error_str = str(response.error) if response.error else response.status.value

                if "not implemented" not in error_str.lower():
                    bug = ProductBug(
                        bug_id=f"EDGE_{dim}_{top_k}",
                        severity=BugSeverity.MEDIUM,
                        category=BugCategory.PRODUCT_BUG,
                        title=f"Product: Edge Case Failed - {desc}",
                        description=f"Expected success but failed for dimension={dim}, top_k={top_k}",
                        reproduction={"dimension": dim, "top_k": top_k},
                        evidence=error_str,
                        impact=f"Cannot use configuration: {desc}",
                        recommendation="Review edge case handling"
                    )
                    found_bugs.append(bug)
                    self._print_bug(bug)

            elif not should_succeed and actual_success:
                # 应该失败但成功了 - 参数验证问题
                bug = ProductBug(
                    bug_id=f"EDGE_{dim}_{top_k}",
                    severity=BugSeverity.HIGH,
                    category=BugCategory.PRODUCT_BUG,
                    title=f"Product: Invalid Parameter Accepted - {desc}",
                    description=f"Expected failure but succeeded for dimension={dim}, top_k={top_k}",
                    reproduction={"dimension": dim, "top_k": top_k},
                    evidence="Operation succeeded when it should have been rejected",
                    impact="System accepts invalid parameters",
                    recommendation="Add input validation"
                )
                found_bugs.append(bug)
                self._print_bug(bug)

        return found_bugs

    def run_deep_analysis(self):
        """运行深度分析"""
        print("\n" + "="*70)
        print("Deep Bug Analysis: Product-Level Issues")
        print("="*70)
        print(f"[*] Target: {self.host}:{self.port}")

        self.adapter.connect()
        self.runtime.start()

        try:
            # 分析压力测试失败
            stress_bugs = self.analyze_stress_failures()

            # 分析边缘情况
            edge_bugs = self.analyze_edge_cases()

            self.bugs = stress_bugs + edge_bugs

            # 汇总报告
            self._generate_report()

        finally:
            self.adapter.disconnect()
            self.runtime.stop()

    def _generate_report(self):
        """生成分析报告"""
        print("\n" + "="*70)
        print("[*] Deep Analysis Summary")
        print("="*70)

        # 按类别统计
        by_category = {}
        for bug in self.bugs:
            by_category[bug.category] = by_category.get(bug.category, 0) + 1

        print(f"\n[*] Bugs by Category:")
        for category, count in sorted(by_category.items(), key=lambda x: -x[1]):
            print(f"    {category.value}: {count}")

        # 按严重程度统计
        by_severity = {}
        for bug in self.bugs:
            by_severity[bug.severity] = by_severity.get(bug.severity, 0) + 1

        print(f"\n[*] Bugs by Severity:")
        for severity, count in sorted(by_severity.items(), key=lambda x: x[0].value):
            print(f"    {severity.value}: {count}")

        # 产品bug列表
        product_bugs = [b for b in self.bugs if b.category == BugCategory.PRODUCT_BUG]

        print(f"\n[*] Product Bugs Found: {len(product_bugs)}")

        if product_bugs:
            print(f"\n[*] Product Bug Details:")
            for bug in product_bugs:
                print(f"\n    [{bug.bug_id}] {bug.title}")
                print(f"        Severity: {bug.severity.value}")
                print(f"        Description: {bug.description}")
                print(f"        Reproduction: {bug.reproduction}")
        else:
            print(f"\n[+] No product-level bugs found in current tests")
            print(f"[*] All failures are framework issues or expected rejections")

        # 建议
        print(f"\n[*] Recommendations:")
        if len(product_bugs) == 0:
            print(f"    [+] SeekDB handles all test cases correctly")
            print(f"    [+] Input validation works as expected")
            print(f"    [+] Framework needs adapter implementation for insert operations")
        else:
            critical_bugs = [b for b in product_bugs if b.severity == BugSeverity.CRITICAL]
            high_bugs = [b for b in product_bugs if b.severity == BugSeverity.HIGH]

            if critical_bugs:
                print(f"    [!] {len(critical_bugs)} CRITICAL bugs require immediate attention")
            if high_bugs:
                print(f"    [!] {len(high_bugs)} HIGH priority bugs should be addressed soon")

            print(f"    [*] Total product bugs: {len(product_bugs)}")


def main():
    """主函数"""
    analyzer = DeepBugAnalyzer()
    analyzer.run_deep_analysis()


if __name__ == "__main__":
    main()
