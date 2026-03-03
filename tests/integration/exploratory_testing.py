# -*- coding: utf-8 -*-
"""
Exploratory Testing Framework for SeekDB Product-Level Bugs

探索性测试框架：
1. 深度产品功能测试
2. 隐蔽边界条件挖掘
3. 真实并发和竞态条件
4. 资源管理和内存泄漏
5. 数据一致性验证
6. API 合同违规检测
"""
import sys
import time
import json
import threading
import multiprocessing
import gc
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

from agent.runtime import AgentRuntime, AgentConfig
from agent.memory import AgentMemory, MemoryType
from detectors import AnomalyDetectionAdapter
from adapters import SeekDBAdapter
from core.models import SemanticCase, SlotScope, ErrorCategory


class BugSeverity(Enum):
    """Bug 严重程度"""
    CRITICAL = "critical"  # 崩溃、数据丢失
    HIGH = "high"         # 功能异常、性能严重下降
    MEDIUM = "medium"     # 边界情况问题、性能轻微下降
    LOW = "low"         # 文档问题、UI 问题


@dataclass
class ExploratoryBug:
    """探索发现的 Bug"""
    bug_id: str
    title: str
    description: str
    severity: BugSeverity
    category: str
    reproduction_steps: List[str]
    evidence: Dict[str, Any]
    discovered_by: str
    timestamp: float
    confirmed: bool = False


@dataclass
class TestResult:
    """测试结果"""
    test_name: str
    passed: bool
    duration: float
    error: Optional[str] = None
    crash: bool = False
    timeout: bool = False
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    bugs: List[ExploratoryBug] = field(default_factory=list)


class ExploratoryTester:
    """
    探索性测试器

    专注于发现产品级别的潜在问题
    """

    def __init__(self, host: str = "localhost", port: int = 2881):
        self.host = host
        self.port = port
        self.adapter = SeekDBAdapter(host=host, port=port)

        # Agent 组件
        agent_config = AgentConfig(
            agent_id="exploratory_tester",
            enable_monitoring=True,
            enable_memory=True
        )
        self.runtime = AgentRuntime(config=agent_config)
        self.memory = AgentMemory(agent_id="exploratory_tester")
        self.anomaly_detector = AnomalyDetectionAdapter(method="z_score", threshold=2.5)

        # 存储发现的 bug
        self.discovered_bugs: List[ExploratoryBug] = []
        self.test_results: List[TestResult] = []

        # 探索性测试策略
        self.strategies = [
            self.explore_dimension_boundaries,
            self.explore_parameter_interactions,
            self.explore_concurrency_races,
            self.explore_resource_limits,
            self.explore_data_consistency,
            self.explore_api_contract_violations
        ]

    def setup(self) -> bool:
        """设置测试环境"""
        print(f"\n[*] Setting up exploratory testing environment...")
        print(f"    Target: {self.host}:{self.port}")

        if not self.adapter.connect():
            print(f"[!] Cannot connect to SeekDB, using simulation mode")
            self.adapter._connected = True

        self.runtime.start()
        print(f"[+] Ready for exploratory testing")
        return True

    def run_all_explorations(self) -> Dict[str, Any]:
        """运行所有探索性测试"""
        print("\n" + "="*70)
        print("Exploratory Testing: Product-Level Bug Discovery")
        print("="*70)

        summary = {
            "total_tests": 0,
            "bugs_found": 0,
            "critical_bugs": 0,
            "categories": {}
        }

        for strategy in self.strategies:
            strategy_name = strategy.__name__
            print(f"\n[*] Running: {strategy_name}")

            try:
                result = strategy()
                self.test_results.append(result)

                # 统计
                summary["total_tests"] += getattr(result, "test_count", 0)

                for bug in result.bugs:
                    self.discovered_bugs.append(bug)
                    summary["bugs_found"] += 1

                    if bug.severity == BugSeverity.CRITICAL:
                        summary["critical_bugs"] += 1

                    category = bug.category
                    summary["categories"][category] = summary["categories"].get(category, 0) + 1

                # 打印结果摘要
                print(f"    Tests: {getattr(result, 'test_count', 0)}")
                print(f"    Bugs: {len(result.bugs)}")
                if result.bugs:
                    for bug in result.bugs[:3]:  # 只显示前3个
                        print(f"      - [{bug.severity.value.upper()}] {bug.title}")

            except Exception as e:
                print(f"    [!] Strategy failed: {e}")
                traceback.print_exc()

        return summary

    def explore_dimension_boundaries(self) -> TestResult:
        """
        探索维度边界条件

        挖掘维度参数的隐蔽边界问题
        """
        result = TestResult(test_name="dimension_boundaries", passed=False, duration=0.0)
        start_time = time.time()

        # 1. 2的幂次方边界
        power_of_2_dims = [2**i for i in range(1, 17)]  # 2, 4, 8, ..., 65536

        # 2. 素邻边界的值
        boundary_adjacent = []
        for i in range(1, 16):
            power = 2**i
            boundary_adjacent.extend([power - 1, power + 1])

        # 3. 负数和零
        negative_tests = [0, -1, -100, -1000]

        all_dims = power_of_2_dims + boundary_adjacent + negative_tests
        unique_dims = sorted(set(all_dims))

        print(f"    Testing {len(unique_dims)} dimension values")

        for dim in unique_dims:
            try:
                test_case = SemanticCase(
                    test_id=f"explore_dim_{dim}",
                    operation="search",
                    slot_values={"dimension": dim, "top_k": 10},
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.DATABASE
                )

                response = self.adapter.execute_test(test_case)

                # 检查是否有错误
                if response.status.value not in ["SUCCESS", "success"]:
                    error_str = str(response.error) if response.error else response.status.value

                    # 分析错误类型
                    if "dimension" in error_str.lower():
                        # 可能是产品 bug
                        if dim < 0:
                            # 负维度应该被拒绝，但没有
                            if "negative" not in error_str.lower():
                                result.bugs.append(ExploratoryBug(
                                    bug_id=f"dim_negative_{dim}",
                                    title=f"Negative dimension not properly validated",
                                    description=f"Dimension={dim} should be rejected but was accepted or caused unclear error",
                                    severity=BugSeverity.HIGH,
                                    category="validation",
                                    reproduction_steps=[
                                        f"Create collection with dimension={dim}",
                                        f"Execute search with top_k=10"
                                    ],
                                    evidence={"dimension": dim, "error": error_str},
                                    discovered_by="dimension_boundaries",
                                    timestamp=time.time()
                                ))
                        elif dim == 0:
                            result.bugs.append(ExploratoryBug(
                                bug_id=f"dim_zero",
                                title=f"Zero dimension handling unclear",
                                description=f"Dimension=0 behavior is undefined",
                                severity=BugSeverity.MEDIUM,
                                category="edge_case",
                                reproduction_steps=[
                                    f"Use dimension=0 in search"
                                ],
                                evidence={"dimension": dim, "error": error_str},
                                discovered_by="dimension_boundaries",
                                timestamp=time.time()
                            ))
                        else:
                            # 检查是否有特定的边界值问题
                            for bug in self._detect_dimension_boundary_bug(dim, error_str):
                                result.bugs.append(bug)

            except Exception as e:
                result.bugs.append(ExploratoryBug(
                    bug_id=f"dim_exception_{dim}",
                    title=f"Exception on dimension={dim}",
                    description=str(e),
                    severity=BugSeverity.MEDIUM,
                    category="exception_handling",
                    reproduction_steps=[f"Use dimension={dim}"],
                    evidence={"dimension": dim, "exception": str(e)},
                    discovered_by="dimension_boundaries",
                    timestamp=time.time()
                ))

        result.test_count = len(unique_dims)
        result.duration = time.time() - start_time
        result.passed = len(result.bugs) == 0

        return result

    def _detect_dimension_boundary_bug(self, dim: int, error: str) -> Optional[ExploratoryBug]:
        """检测维度边界特有的 bug"""
        bugs = []

        # 检查 2^n 边界
        if dim in [32768, 65536]:
            if "overflow" in error.lower() or "too large" in error.lower():
                bugs.append(ExploratoryBug(
                    bug_id=f"dim_overflow_{dim}",
                    title=f"Dimension overflow at 2^n boundary",
                    description=f"Dimension={dim} (2^15 or 2^16) causes overflow",
                    severity=BugSeverity.HIGH,
                    category="overflow",
                    reproduction_steps=[f"Use dimension={dim}"],
                    evidence={"dimension": dim, "error": error},
                    discovered_by="dimension_boundaries",
                    timestamp=time.time()
                ))

        return bugs

    def explore_parameter_interactions(self) -> TestResult:
        """
        探索参数交互作用

        挖掘参数组合产生的隐蔽问题
        """
        result = TestResult(test_name="parameter_interactions", passed=False, duration=0.0)
        start_time = time.time()

        # 定义参数空间
        dimensions = [64, 128, 256, 512, 1024, 2048, 4096]
        top_ks = [1, 5, 10, 50, 100, 500, 1000]
        metrics = ["L2", "IP", "COSINE"]

        print(f"    Testing parameter interactions...")
        print(f"      Dimensions: {len(dimensions)}")
        print(f"      Top-K values: {len(top_ks)}")
        print(f"      Metrics: {len(metrics)}")

        # 深度组合测试
        test_count = 0

        # 层级交互：先测单参数，再测组合
        # 第一层：单参数变化
        for dim in dimensions:
            for metric in metrics:
                test_case = SemanticCase(
                    test_id=f"interact_1_dim{dim}_{metric}",
                    operation="search",
                    slot_values={"dimension": dim, "metric_type": metric, "top_k": 10},
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.DATABASE
                )

                response = self.adapter.execute_test(test_case)
                test_count += 1

                if response.status.value not in ["SUCCESS", "success"]:
                    error_str = str(response.error) if response.error else response.status.value

                    # 检查是否有特殊的交互问题
                    if dim == 64 and "metric" in error_str.lower():
                        result.bugs.append(ExploratoryBug(
                            bug_id=f"interact_small_dim_{metric}",
                            title=f"Small dimension incompatible with {metric}",
                            description=f"Dimension=64 has issues with metric_type={metric}",
                            severity=BugSeverity.MEDIUM,
                            category="compatibility",
                            reproduction_steps=[
                                f"Use dimension=64, metric_type={metric}"
                            ],
                            evidence={"dimension": dim, "metric": metric, "error": error_str},
                            discovered_by="parameter_interactions",
                            timestamp=time.time()
                        ))

        # 第二层：深层次组合
        high_value_dims = [128, 256, 512, 1024]
        high_value_ks = [100, 500, 1000]

        for dim in high_value_dims:
            for top_k in high_value_ks:
                for metric in metrics:
                    # 特定交互：小维度 + 大 top_k
                    if dim < top_k:
                        test_case = SemanticCase(
                            test_id=f"interact_2_dim{dim}_k{top_k}_{metric}",
                            operation="search",
                            slot_values={
                                "dimension": dim,
                                "top_k": top_k,
                                "metric_type": metric
                            },
                            raw_parameters={},
                            is_legal=True,
                            scope=SlotScope.DATABASE
                        )

                        response = self.adapter.execute_test(test_case)
                        test_count += 1

                        # 检查是否有特殊的交互问题
                        if response.status.value not in ["SUCCESS", "success"]:
                            error_str = str(response.error) if response.error else response.status.value

                            # 检查是否有比 top_k 还小的向量空间问题
                            if "insufficient" in error_str.lower() or "empty" in error_str.lower():
                                result.bugs.append(ExploratoryBug(
                                    bug_id=f"interact_vector_space_dim{dim}_k{top_k}",
                                    title=f"Vector space too small for top_k={top_k}",
                                    description=f"Dimension={dim} produces < {top_k} possible vectors, but API doesn't prevent this",
                                    severity=BugSeverity.MEDIUM,
                                    category="validation",
                                    reproduction_steps=[
                                        f"Use dimension={dim} (produces {dim//2 if dim < 512 else dim} vectors max)",
                                        f"Request top_k={top_k} results"
                                    ],
                                    evidence={"dimension": dim, "top_k": top_k, "metric": metric, "error": error_str},
                                    discovered_by="parameter_interactions",
                                    timestamp=time.time()
                                ))

        result.test_count = test_count
        result.duration = time.time() - start_time
        result.passed = len(result.bugs) == 0

        return result

    def explore_concurrency_races(self) -> TestResult:
        """
        探索并发竞态条件

        挖掘真实并发场景下的竞态条件
        """
        result = TestResult(test_name="concurrency_races", passed=False, duration=0.0)
        start_time = time.time()

        # 真实并发场景测试
        scenarios = [
            {
                "name": "concurrent_insert_same_collection",
                "threads": 10,
                "operations": 100,
                "test_func": self._concurrent_insert_test
            },
            {
                "name": "concurrent_search_same_collection",
                "threads": 20,
                "operations": 200,
                "test_func": self._concurrent_search_test
            },
            {
                "name": "mixed_concurrent_operations",
                "threads": 15,
                "operations": 150,
                "test_func": self._concurrent_mixed_test
            }
        ]

        for scenario in scenarios:
            print(f"\n    Scenario: {scenario['name']}")
            print(f"      Threads: {scenario['threads']}")
            print(f"      Operations: {scenario['operations']}")

            try:
                bug_count = scenario["test_func"](scenario["threads"], scenario["operations"])

                if bug_count > 0:
                    result.bugs.append(ExploratoryBug(
                        bug_id=f"race_{scenario['name']}",
                        title=f"Concurrency issue in {scenario['name']}",
                        description=f"Found {bug_count} potential race conditions",
                        severity=BugSeverity.HIGH,
                        category="concurrency",
                        reproduction_steps=[
                            f"Run {scenario['name']} with {scenario['threads']} threads",
                            f"Execute {scenario['operations']} operations"
                        ],
                        evidence={"threads": scenario["threads"], "operations": scenario["operations"]},
                        discovered_by="concurrency_races",
                        timestamp=time.time()
                    ))

            except Exception as e:
                print(f"      [!] Scenario failed: {e}")

        result.test_count = len(scenarios)
        result.duration = time.time() - start_time
        result.passed = len(result.bugs) == 0

        return result

    def _concurrent_insert_test(self, num_threads: int, num_ops: int) -> int:
        """并发插入测试"""
        bugs_found = 0
        errors = []

        def insert_worker(worker_id: int) -> List[str]:
            worker_errors = []

            for i in range(num_ops // num_threads):
                try:
                    test_case = SemanticCase(
                        test_id=f"concurrent_insert_t{worker_id}_op{i}",
                        operation="insert",
                        slot_values={"dimension": 128},
                        raw_parameters={},
                        is_legal=True,
                        scope=SlotScope.DATABASE
                    )

                    response = self.adapter.execute_test(test_case)

                    if response.status.value not in ["SUCCESS", "success"]:
                        worker_errors.append(str(response.error))

                        # 检查并发特有的错误
                        error_str = str(response.error) if response.error else ""
                        if "lock" in error_str.lower() or "deadlock" in error_str.lower():
                            bugs_found += 1

                except Exception as e:
                    worker_errors.append(str(e))

            return worker_errors

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(insert_worker, i) for i in range(num_threads)]
            all_errors = []
            for future in as_completed(futures):
                all_errors.extend(future.result())

        return bugs_found

    def _concurrent_search_test(self, num_threads: int, num_ops: int) -> int:
        """并发搜索测试"""
        bugs_found = 0

        def search_worker(worker_id: int) -> int:
            worker_bugs = 0

            for i in range(num_ops // num_threads):
                try:
                    test_case = SemanticCase(
                        test_id=f"concurrent_search_t{worker_id}_op{i}",
                        operation="search",
                        slot_values={"dimension": 512, "top_k": 10},
                        raw_parameters={},
                        is_legal=True,
                        scope=SlotScope.DATABASE
                    )

                    response = self.adapter.execute_test(test_case)

                    if response.status.value not in ["SUCCESS", "success"]:
                        error_str = str(response.error) if response.error else ""

                        # 检查数据一致性问题
                        if "inconsistent" in error_str.lower() or "mismatch" in error_str.lower():
                            bugs_found += 1

                except Exception as e:
                    if "race" in str(e).lower():
                        bugs_found += 1

            return worker_bugs

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(search_worker, i) for i in range(num_threads)]
            for future in as_completed(futures):
                future.result()

        return bugs_found

    def _concurrent_mixed_test(self, num_threads: int, num_ops: int) -> int:
        """混合并发测试"""
        # 30% insert, 70% search
        bugs_found = 0

        def mixed_worker(worker_id: int) -> int:
            worker_bugs = 0

            for i in range(num_ops // num_threads):
                try:
                    # 混合操作
                    if i % 10 < 3:
                        # Insert
                        test_case = SemanticCase(
                            test_id=f"mixed_t{worker_id}_insert_{i}",
                            operation="insert",
                            slot_values={"dimension": 256},
                            raw_parameters={},
                            is_legal=True,
                            scope=SlotScope.DATABASE
                        )
                    else:
                        # Search
                        test_case = SemanticCase(
                            test_id=f"mixed_t{worker_id}_search_{i}",
                            operation="search",
                            slot_values={"dimension": 256, "top_k": 20},
                            raw_parameters={},
                            is_legal=True,
                            scope=SlotScope.DATABASE
                        )

                    response = self.adapter.execute_test(test_case)

                    if response.status.value not in ["SUCCESS", "success"]:
                        # 检查数据一致性问题
                        error_str = str(response.error) if response.error else ""
                        if "corruption" in error_str.lower() or "inconsistent" in error_str.lower():
                            bugs_found += 1

                except Exception as e:
                    if "race" in str(e).lower() or "concurrency" in str(e).lower():
                        bugs_found += 1

            return worker_bugs

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(mixed_worker, i) for i in range(num_threads)]
            for future in as_completed(futures):
                future.result()

        return bugs_found

    def explore_resource_limits(self) -> TestResult:
        """
        探索资源限制

        挖掘内存、连接、文件句柄等资源限制问题
        """
        result = TestResult(test_name="resource_limits", passed=False, duration=0.0)
        start_time = time.time()

        # 内存限制测试
        print(f"\n    Testing memory limits...")

        # 测试大量数据
        large_dimensions = [16384, 32768, 65536, 131072]

        for dim in large_dimensions:
            try:
                test_case = SemanticCase(
                    test_id=f"resource_mem_{dim}",
                    operation="search",
                    slot_values={"dimension": dim, "top_k": 1000},
                    raw_parameters={},
                    is_legal=(dim <= 65536),
                    scope=SlotScope.DATABASE
                )

                response = self.adapter.execute_test(test_case)

                if response.status.value not in ["SUCCESS", "success"]:
                    error_str = str(response.error) if response.error else ""

                    # 检查内存相关错误
                    if any(kw in error_str.lower() for kw in ["memory", "oom", "allocation", "buffer"]):
                        result.bugs.append(ExploratoryBug(
                            bug_id=f"resource_memory_{dim}",
                            title=f"Memory issue with dimension={dim}",
                            description=f"Large dimension={dim} causes memory problems",
                            severity=BugSeverity.HIGH,
                            category="memory",
                            reproduction_steps=[f"Use dimension={dim}, top_k=1000"],
                            evidence={"dimension": dim, "error": error_str},
                            discovered_by="resource_limits",
                            timestamp=time.time()
                        ))

            except Exception as e:
                if "memory" in str(e).lower():
                    result.bugs.append(ExploratoryBug(
                        bug_id="resource_memory_exception",
                        title="Memory exception on large data",
                        description=str(e),
                        severity=BugSeverity.HIGH,
                        category="memory",
                        reproduction_steps=["Use large dimension values"],
                        evidence={"exception": str(e)},
                        discovered_by="resource_limits",
                        timestamp=time.time()
                    ))

        # 连接限制测试
        print(f"\n    Testing connection limits...")

        try:
            # 尝试创建大量"连接"
            test_cases = []
            for i in range(100):
                test_cases.append(SemanticCase(
                    test_id=f"resource_conn_{i}",
                    operation="search",
                    slot_values={"dimension": 128, "top_k": 10},
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.DATABASE
                ))

            # 快速执行
            for test_case in test_cases[:50]:  # 限制数量
                self.adapter.execute_test(test_case)

        except Exception as e:
            if "connection" in str(e).lower() or "too many" in str(e).lower():
                result.bugs.append(ExploratoryBug(
                    bug_id="resource_connection_limit",
                    title="Connection limit not enforced",
                    description="System allows excessive connections without proper limit",
                    severity=BugSeverity.MEDIUM,
                    category="resource_management",
                    reproduction_steps=["Create many concurrent connections"],
                    evidence={"exception": str(e)},
                    discovered_by="resource_limits",
                    timestamp=time.time()
                ))

        result.test_count = len(large_dimensions) + 1
        result.duration = time.time() - start_time
        result.passed = len(result.bugs) == 0

        return result

    def explore_data_consistency(self) -> TestResult:
        """
        探索数据一致性

        挖掘读写一致性、事务隔离性问题
        """
        result = TestResult(test_name="data_consistency", passed=False, duration=0.0)
        start_time = time.time()

        print(f"\n    Testing data consistency...")

        # 1. 读写一致性测试
        # 插入相同数据多次，检查一致性
        test_vector = {"dimension": 128, "data": [1.0] * 128}

        for i in range(10):
            try:
                test_case = SemanticCase(
                    test_id=f"consistency_insert_{i}",
                    operation="insert",
                    slot_values={"dimension": 128, "data": test_vector},
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.DATABASE
                )

                response1 = self.adapter.execute_test(test_case)
                response2 = self.adapter.execute_test(test_case)

                # 检查响应一致性
                if response1.status.value != response2.status.value:
                    result.bugs.append(ExploratoryBug(
                        bug_id="consistency_insert_response",
                        title="Inconsistent response for identical insert",
                        description="Same insert operation returns different results",
                        severity=BugSeverity.HIGH,
                        category="consistency",
                        reproduction_steps=[
                            "Insert same data twice",
                            "Compare responses"
                        ],
                        evidence={"response1": response1.status.value, "response2": response2.status.value},
                        discovered_by="data_consistency",
                        timestamp=time.time()
                    ))

            except Exception as e:
                pass

        # 2. 搜索结果一致性
        # 多次搜索相同查询，检查结果一致性
        for i in range(5):
            try:
                test_case = SemanticCase(
                    test_id=f"consistency_search_{i}",
                    operation="search",
                    slot_values={"dimension": 256, "top_k": 10},
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.DATABASE
                )

                results = []
                for j in range(3):
                    response = self.adapter.execute_test(test_case)
                    if response.status.value == "SUCCESS":
                        results.append(response.result_data)

                # 检查结果一致性
                if len(results) > 1:
                    # 简化检查：比较结果数量
                    counts = [r.get("total", 0) if isinstance(r, dict) else 0 for r in results]
                    if len(set(counts)) > 1:
                        result.bugs.append(ExploratoryBug(
                            bug_id="consistency_search_result",
                            title="Inconsistent search results",
                            description="Same search returns different result counts",
                            severity=BugSeverity.HIGH,
                            category="consistency",
                            reproduction_steps=[
                                "Execute same search query 3 times",
                                "Compare result counts"
                            ],
                            evidence={"result_counts": counts},
                            discovered_by="data_consistency",
                            timestamp=time.time()
                        ))

            except Exception as e:
                pass

        result.test_count = 15
        result.duration = time.time() - start_time
        result.passed = len(result.bugs) == 0

        return result

    def explore_api_contract_violations(self) -> TestResult:
        """
        探索 API 合同违规

        检测违反 API 规范的输入被错误处理的情况
        """
        result = TestResult(test_name="api_contract_violations", passed=False, duration=0.0)
        start_time = time.time()

        # 定义应该被拒绝的无效输入
        invalid_inputs = [
            # 应该被明确拒绝的无效值
            {"test_id": "contract_neg_dim", "operation": "search", "params": {"dimension": -1, "top_k": 10}, "should_reject": True},
            {"test_id": "contract_zero_k", "operation": "search", "params": {"dimension": 128, "top_k": 0}, "should_reject": True},
            {"test_id": "contract_invalid_metric", "operation": "search", "params": {"dimension": 128, "top_k": 10, "metric_type": "INVALID"}, "should_reject": True},

            # 边界值：可能接受也可能拒绝
            {"test_id": "contract_max_dim", "operation": "search", "params": {"dimension": 65537, "top_k": 10}, "should_reject": True},
            {"test_id": "contract_max_k", "operation": "search", "params": {"dimension": 128, "top_k": 10001}, "should_reject": True},

            # 参数缺失（如果没有默认值）
            {"test_id": "contract_no_dim", "operation": "search", "params": {"top_k": 10}, "should_reject": True},
        ]

        print(f"    Testing {len(invalid_inputs)} API contract scenarios")

        for test_input in invalid_inputs:
            try:
                test_case = SemanticCase(
                    test_id=test_input["test_id"],
                    operation=test_input["operation"],
                    slot_values=test_input["params"],
                    raw_parameters={},
                    is_legal=False,  # 标记为非法
                    scope=SlotScope.DATABASE
                )

                response = self.adapter.execute_test(test_case)

                # 检查是否正确拒绝
                if test_input["should_reject"]:
                    if response.status.value in ["SUCCESS", "success"]:
                        # 应该拒绝但成功了 - 这是一个 bug
                        result.bugs.append(ExploratoryBug(
                            bug_id=f"contract_{test_input['test_id']}_not_rejected",
                            title=f"Invalid input not rejected: {test_input['test_id']}",
                            description=f"Input {test_input['params']} should be rejected but was accepted",
                            severity=BugSeverity.HIGH,
                            category="validation",
                            reproduction_steps=[
                                f"Use parameters: {test_input['params']}"
                            ],
                            evidence={"params": test_input["params"], "response": response.status.value},
                            discovered_by="api_contract_violations",
                            timestamp=time.time()
                        ))

                    elif response.status.value in ["FAILURE", "error"]:
                        # 检查错误信息是否清晰
                        error_str = str(response.error) if response.error else ""

                        # 错误信息含糊不清
                        if "error" in error_str.lower() and "invalid" not in error_str.lower():
                            result.bugs.append(ExploratoryBug(
                                bug_id=f"contract_{test_input['test_id']}_unclear_error",
                                title=f"Unclear error message for {test_input['test_id']}",
                                description=f"Invalid input rejected but error message is unclear: {error_str}",
                                severity=BugSeverity.LOW,
                                category="documentation",
                                reproduction_steps=[
                                    f"Use invalid parameters: {test_input['params']}"
                                ],
                                evidence={"params": test_input["params"], "error": error_str},
                                discovered_by="api_contract_violations",
                                timestamp=time.time()
                            ))

            except Exception as e:
                # 异常也是可以接受的（如果是有意义的异常）
                error_str = str(e)
                if "invalid" in error_str.lower() or "reject" in error_str.lower():
                    # 这是正确的行为
                    pass
                else:
                    # 异常处理不当
                    result.bugs.append(ExploratoryBug(
                        bug_id=f"contract_{test_input['test_id']}_exception",
                        title=f"Poor exception handling for {test_input['test_id']}",
                        description=f"Exception thrown instead of proper error: {error_str}",
                        severity=BugSeverity.MEDIUM,
                        category="error_handling",
                        reproduction_steps=[
                            f"Use invalid parameters: {test_input['params']}"
                        ],
                        evidence={"params": test_input["params"], "exception": error_str},
                        discovered_by="api_contract_violations",
                        timestamp=time.time()
                    ))

        result.test_count = len(invalid_inputs)
        result.duration = time.time() - start_time
        result.passed = len(result.bugs) == 0

        return result

    def analyze_findings(self) -> str:
        """分析发现结果"""
        print("\n" + "="*70)
        print("[*] Exploratory Testing Analysis")
        print("="*70)

        # 按严重程度分组
        bugs_by_severity = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }

        for bug in self.discovered_bugs:
            bugs_by_severity[bug.severity.value].append(bug)

        print(f"\n[*] Total Bugs Found: {len(self.discovered_bugs)}")

        for severity in ["critical", "high", "medium", "low"]:
            bugs = bugs_by_severity[severity]
            if bugs:
                print(f"\n{severity.upper()} ({len(bugs)}):")
                for bug in bugs:
                    print(f"  - {bug.title}")
                    print(f"      Category: {bug.category}")
                    print(f"      Discovered by: {bug.discovered_by}")

        # 按类别分组
        bugs_by_category = {}
        for bug in self.discovered_bugs:
            bugs_by_category[bug.category] = bugs_by_category.get(bug.category, 0) + 1

        print(f"\n[*] By Category:")
        for category, count in sorted(bugs_by_category.items(), key=lambda x: -x[1]):
            print(f"  {category}: {count}")

        # 优先级建议
        print(f"\n[*] Priority Recommendations:")

        if bugs_by_severity["critical"]:
            print("\n  [CRITICAL] Fix immediately:")
            for bug in bugs_by_severity["critical"]:
                print(f"    - {bug.title}")

        if bugs_by_severity["high"]:
            print("\n  [HIGH] Fix soon:")
            for bug in bugs_by_severity["high"]:
                print(f"    - {bug.title}")

        return f"Found {len(self.discovered_bugs)} potential product-level bugs"

    def save_exploratory_report(self) -> None:
        """保存探索性测试报告"""
        output = Path("reports/exploratory_testing.json")
        output.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "timestamp": time.time(),
            "bugs": [
                {
                    "bug_id": bug.bug_id,
                    "title": bug.title,
                    "description": bug.description,
                    "severity": bug.severity.value,
                    "category": bug.category,
                    "evidence": bug.evidence,
                    "discovered_by": bug.discovered_by,
                    "timestamp": bug.timestamp
                }
                for bug in self.discovered_bugs
            ],
            "total_bugs": len(self.discovered_bugs),
            "by_severity": {
                "critical": len([b for b in self.discovered_bugs if b.severity == BugSeverity.CRITICAL]),
                "high": len([b for b in self.discovered_bugs if b.severity == BugSeverity.HIGH]),
                "medium": len([b for b in self.discovered_bugs if b.severity == BugSeverity.MEDIUM]),
                "low": len([b for b in self.discovered_bugs if b.severity == BugSeverity.LOW]),
            },
            "by_category": {}
        }

        # 按类别统计
        for bug in self.discovered_bugs:
            report["by_category"][bug.category] = report["by_category"].get(bug.category, 0) + 1

        with open(output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n[+] Exploratory testing report saved to: {output}")

    def run_exploratory_testing(self):
        """运行探索性测试"""
        print("\n" + "="*70)
        print("Exploratory Testing: Product-Level Bug Discovery")
        print("="*70)

        self.setup()

        try:
            # 运行所有探索性测试
            summary = self.run_all_explorations()

            # 分析发现
            self.analyze_findings()

            # 保存报告
            self.save_exploratory_report()

            # 总结
            print("\n" + "="*70)
            print("[*] Exploratory Testing Summary")
            print("="*70)
            print(f"\n[*] Tests Executed: {summary['total_tests']}")
            print(f"[*] Bugs Found: {summary['bugs_found']}")
            print(f"[*] Critical Bugs: {summary['critical_bugs']}")
            print(f"[*] Categories: {len(summary['categories'])}")

            if summary['bugs_found'] > 0:
                print(f"\n[+] SUCCESS: Found {summary['bugs_found']} potential product-level bugs!")
            else:
                print(f"\n[*] No product-level bugs found in this run")

        finally:
            self.adapter.disconnect()
            self.runtime.stop()


def main():
    """主函数"""
    tester = ExploratoryTester()
    tester.run_exploratory_testing()


if __name__ == "__main__":
    main()
