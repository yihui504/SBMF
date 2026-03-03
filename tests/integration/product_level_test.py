# -*- coding: utf-8 -*-
"""
Enhanced Product-Level Testing for SeekDB

增强产品级测试：
1. 真实 SeekDB 数据库操作
2. 高并发场景测试
3. 大数据量场景测试
4. 压力测试和稳定性测试
"""
import sys
import time
import threading
import multiprocessing
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

from agent.runtime import AgentRuntime, AgentConfig
from agent.memory import AgentMemory, MemoryType
from adapters import SeekDBAdapter
from detectors import AnomalyDetectionAdapter
from core.models import SemanticCase, SlotScope, ErrorCategory


@dataclass
class ProductTestResult:
    """产品测试结果"""
    test_name: str
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    bugs_found: int = 0
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    errors: List[Dict] = field(default_factory=list)
    duration: float = 0.0


class ProductLevelTester:
    """产品级测试器"""

    def __init__(self, host: str = "localhost", port: int = 2881):
        self.host = host
        self.port = port
        self.adapter = SeekDBAdapter(host=host, port=port)

        # Agent 组件
        agent_config = AgentConfig(
            agent_id="product_tester",
            enable_monitoring=True,
            enable_memory=True
        )
        self.runtime = AgentRuntime(config=agent_config)
        self.memory = AgentMemory(agent_id="product_tester")
        self.anomaly_detector = AnomalyDetectionAdapter(method="z_score", threshold=2.5)

        # 测试结果
        self.results = []

    def setup(self) -> bool:
        """设置测试环境"""
        print(f"\n[*] Setting up product-level test environment...")
        print(f"    Target: {self.host}:{self.port}")

        if not self.adapter.connect():
            print(f"[!] Cannot connect to SeekDB, using simulation mode")
            self.adapter._connected = True

        self.runtime.start()
        print(f"[+] Environment ready")
        return True

    def test_basic_operations(self) -> ProductTestResult:
        """测试基本操作"""
        print("\n" + "="*70)
        print("[*] Test 1: Basic Operations")
        print("="*70)

        result = ProductTestResult(test_name="basic_operations")
        start_time = time.time()

        # 测试场景：各种基本操作
        operations = [
            {"operation": "search", "dimension": 128, "top_k": 10, "metric_type": "L2"},
            {"operation": "search", "dimension": 256, "top_k": 50, "metric_type": "IP"},
            {"operation": "search", "dimension": 512, "top_k": 100, "metric_type": "COSINE"},
            {"operation": "insert", "dimension": 128},
            {"operation": "insert", "dimension": 256},
            {"operation": "insert", "dimension": 512},
        ]

        exec_times = []

        for op in operations:
            try:
                exec_start = time.time()

                test_case = SemanticCase(
                    test_id=f"basic_{op['operation']}_{op.get('dimension', 0)}",
                    operation=op["operation"],
                    slot_values={k: v for k, v in op.items() if k != "operation"},
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.DATABASE
                )

                response = self.adapter.execute_test(test_case)
                exec_time = time.time() - exec_start

                exec_times.append(exec_time)
                result.total_operations += 1

                if response.status.value in ["SUCCESS", "success"]:
                    result.successful_operations += 1
                else:
                    result.failed_operations += 1
                    result.errors.append({
                        "operation": op,
                        "error": str(response.error) if response.error else response.status.value,
                        "exec_time": exec_time
                    })

            except Exception as e:
                result.failed_operations += 1
                result.total_operations += 1
                result.errors.append({
                    "operation": op,
                    "error": str(e),
                    "exec_time": 0.0
                })

        result.duration = time.time() - start_time

        # 计算性能指标
        if exec_times:
            result.performance_metrics = {
                "avg_time": sum(exec_times) / len(exec_times),
                "min_time": min(exec_times),
                "max_time": max(exec_times),
                "total_time": sum(exec_times)
            }

        self._print_result(result)
        self.results.append(result)
        return result

    def test_high_concurrency(self) -> ProductTestResult:
        """测试高并发场景"""
        print("\n" + "="*70)
        print("[*] Test 2: High Concurrency")
        print("="*70)

        result = ProductTestResult(test_name="high_concurrency")
        start_time = time.time()

        # 并发配置
        num_threads = 10
        operations_per_thread = 5

        print(f"    Threads: {num_threads}")
        print(f"    Operations per thread: {operations_per_thread}")
        print(f"    Total operations: {num_threads * operations_per_thread}")

        def worker(thread_id: int) -> Dict:
            """工作线程"""
            thread_results = {
                "thread_id": thread_id,
                "total": 0,
                "success": 0,
                "failed": 0,
                "errors": []
            }

            for i in range(operations_per_thread):
                try:
                    test_case = SemanticCase(
                        test_id=f"concurrent_t{thread_id}_op{i}",
                        operation="search",
                        slot_values={
                            "dimension": 128 + (thread_id * 10),
                            "top_k": 10 + i
                        },
                        raw_parameters={},
                        is_legal=True,
                        scope=SlotScope.DATABASE
                    )

                    response = self.adapter.execute_test(test_case)
                    thread_results["total"] += 1

                    if response.status.value in ["SUCCESS", "success"]:
                        thread_results["success"] += 1
                    else:
                        thread_results["failed"] += 1
                        thread_results["errors"].append(str(response.error))

                except Exception as e:
                    thread_results["total"] += 1
                    thread_results["failed"] += 1
                    thread_results["errors"].append(str(e))

            return thread_results

        # 使用线程池执行并发测试
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            thread_results = [f.result() for f in as_completed(futures)]

        # 汇总结果
        for tr in thread_results:
            result.total_operations += tr["total"]
            result.successful_operations += tr["success"]
            result.failed_operations += tr["failed"]
            for err in tr["errors"]:
                result.errors.append({"thread": tr["thread_id"], "error": err})

        result.duration = time.time() - start_time
        result.performance_metrics = {
            "throughput": result.total_operations / result.duration,
            "concurrency_level": num_threads
        }

        self._print_result(result)
        self.results.append(result)
        return result

    def test_large_data_volume(self) -> ProductTestResult:
        """测试大数据量场景"""
        print("\n" + "="*70)
        print("[*] Test 3: Large Data Volume")
        print("="*70)

        result = ProductTestResult(test_name="large_data_volume")
        start_time = time.time()

        # 大维度测试
        large_dimensions = [1024, 2048, 4096, 8192, 16384, 32768, 65536]

        print(f"    Testing dimensions: {large_dimensions}")

        for dim in large_dimensions:
            try:
                exec_start = time.time()

                test_case = SemanticCase(
                    test_id=f"large_dim_{dim}",
                    operation="search",
                    slot_values={"dimension": dim, "top_k": 100},
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.DATABASE
                )

                response = self.adapter.execute_test(test_case)
                exec_time = time.time() - exec_start

                result.total_operations += 1

                if response.status.value in ["SUCCESS", "success"]:
                    result.successful_operations += 1
                else:
                    result.failed_operations += 1
                    result.errors.append({
                        "dimension": dim,
                        "error": str(response.error) if response.error else response.status.value,
                        "exec_time": exec_time
                    })

                # 检测执行时间异常
                if result.total_operations > 1:
                    history = result.performance_metrics.get("exec_times", [])
                    anomaly = self.anomaly_detector.detect(exec_time, history)
                    if anomaly.is_anomaly:
                        print(f"      [!] Anomaly detected: dim={dim}, time={exec_time:.3f}s (score={anomaly.anomaly_score:.2f})")

                result.performance_metrics.setdefault("exec_times", []).append(exec_time)

            except Exception as e:
                result.failed_operations += 1
                result.total_operations += 1
                result.errors.append({
                    "dimension": dim,
                    "error": str(e)
                })

        result.duration = time.time() - start_time

        self._print_result(result)
        self.results.append(result)
        return result

    def test_stress_load(self) -> ProductTestResult:
        """压力测试"""
        print("\n" + "="*70)
        print("[*] Test 4: Stress Load")
        print("="*70)

        result = ProductTestResult(test_name="stress_load")
        start_time = time.time()

        # 快速连续执行大量操作
        num_operations = 100
        print(f"    Operations: {num_operations}")

        exec_times = []
        error_count = 0

        for i in range(num_operations):
            try:
                exec_start = time.time()

                # 混合不同类型的操作
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
                    # 极限测试
                    test_case = SemanticCase(
                        test_id=f"stress_extreme_{i}",
                        operation="search",
                        slot_values={"dimension": 128 + i * 100, "top_k": 1000},
                        raw_parameters={},
                        is_legal=(i % 2 == 0),
                        scope=SlotScope.DATABASE
                    )

                response = self.adapter.execute_test(test_case)
                exec_time = time.time() - exec_start

                exec_times.append(exec_time)
                result.total_operations += 1

                if response.status.value in ["SUCCESS", "success"]:
                    result.successful_operations += 1
                else:
                    result.failed_operations += 1
                    error_count += 1

                # 每 20 个操作报告一次进度
                if (i + 1) % 20 == 0:
                    progress = (i + 1) / num_operations * 100
                    print(f"    Progress: {progress:.0f}% ({i+1}/{num_operations})")

            except Exception as e:
                result.failed_operations += 1
                result.total_operations += 1
                error_count += 1

        result.duration = time.time() - start_time
        result.bugs_found = error_count

        if exec_times:
            result.performance_metrics = {
                "avg_time": sum(exec_times) / len(exec_times),
                "min_time": min(exec_times),
                "max_time": max(exec_times),
                "ops_per_second": len(exec_times) / max(result.duration, 0.001)  # 避免除零
            }

        self._print_result(result)
        self.results.append(result)
        return result

    def test_boundary_conditions(self) -> ProductTestResult:
        """边界条件测试"""
        print("\n" + "="*70)
        print("[*] Test 5: Boundary Conditions")
        print("="*70)

        result = ProductTestResult(test_name="boundary_conditions")
        start_time = time.time()

        # 各种边界条件
        boundary_tests = [
            # 维度边界
            {"name": "min_dimension", "operation": "search", "dimension": 1, "top_k": 1},
            {"name": "max_dimension", "operation": "search", "dimension": 65536, "top_k": 10},
            {"name": "zero_dimension", "operation": "insert", "dimension": 0},

            # top_k 边界
            {"name": "min_top_k", "operation": "search", "dimension": 128, "top_k": 1},
            {"name": "max_top_k", "operation": "search", "dimension": 128, "top_k": 10000},

            # 参数组合边界
            {"name": "small_dim_large_k", "operation": "search", "dimension": 8, "top_k": 1000},
            {"name": "large_dim_small_k", "operation": "search", "dimension": 10000, "top_k": 1},
        ]

        for test in boundary_tests:
            try:
                test_case = SemanticCase(
                    test_id=f"boundary_{test['name']}",
                    operation=test["operation"],
                    slot_values={k: v for k, v in test.items() if k not in ["name", "operation"]},
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.DATABASE
                )

                response = self.adapter.execute_test(test_case)
                result.total_operations += 1

                if response.status.value in ["SUCCESS", "success"]:
                    result.successful_operations += 1
                else:
                    result.failed_operations += 1
                    result.errors.append({
                        "test": test["name"],
                        "error": str(response.error) if response.error else response.status.value
                    })

                    # 检查是否是产品 bug
                    if response.error:
                        error_str = str(response.error).lower()
                        if "dimension" in error_str or "out of range" in error_str:
                            result.bugs_found += 1

            except Exception as e:
                result.failed_operations += 1
                result.total_operations += 1
                result.errors.append({
                    "test": test["name"],
                    "error": str(e)
                })

        result.duration = time.time() - start_time

        self._print_result(result)
        self.results.append(result)
        return result

    def _print_result(self, result: ProductTestResult) -> None:
        """打印测试结果"""
        print(f"\n[*] Results: {result.test_name}")
        print(f"   Total Operations: {result.total_operations}")
        print(f"   Successful: {result.successful_operations}")
        print(f"   Failed: {result.failed_operations}")
        print(f"   Bugs Found: {result.bugs_found}")
        print(f"   Duration: {result.duration:.2f}s")

        if result.performance_metrics:
            print(f"   Performance Metrics:")
            for k, v in result.performance_metrics.items():
                if isinstance(v, float):
                    print(f"      {k}: {v:.4f}")
                else:
                    print(f"      {k}: {v}")

        if result.errors:
            print(f"   Errors: {len(result.errors)}")
            for err in result.errors[:5]:  # 只显示前 5 个
                print(f"      - {err}")

    def generate_report(self) -> str:
        """生成测试报告"""
        report = []
        report.append("\n" + "="*70)
        report.append("Product-Level Testing Report")
        report.append("="*70)

        # 汇总统计
        total_ops = sum(r.total_operations for r in self.results)
        total_success = sum(r.successful_operations for r in self.results)
        total_failed = sum(r.failed_operations for r in self.results)
        total_bugs = sum(r.bugs_found for r in self.results)
        total_duration = sum(r.duration for r in self.results)

        report.append(f"\n[*] Summary:")
        report.append(f"   Total Operations: {total_ops}")
        report.append(f"   Successful: {total_success} ({total_success/total_ops*100:.1f}%)")
        report.append(f"   Failed: {total_failed} ({total_failed/total_ops*100:.1f}%)")
        report.append(f"   Bugs Found: {total_bugs}")
        report.append(f"   Total Duration: {total_duration:.2f}s")

        # 各测试详情
        report.append(f"\n[*] Test Details:")
        for result in self.results:
            report.append(f"\n  {result.test_name}:")
            report.append(f"    Operations: {result.total_operations}")
            report.append(f"    Success Rate: {result.successful_operations/result.total_operations*100:.1f}%" if result.total_operations > 0 else "    Success Rate: N/A")
            report.append(f"    Duration: {result.duration:.2f}s")
            if result.bugs_found > 0:
                report.append(f"    Bugs: {result.bugs_found}")

        # 建议
        report.append(f"\n[*] Recommendations:")
        if total_bugs > 0:
            report.append(f"  [!] Found {total_bugs} potential bugs - investigate priority order")
        if total_failed / total_ops > 0.1:
            report.append(f"  [!] High failure rate ({total_failed/total_ops*100:.1f}%) - review test environment")
        else:
            report.append(f"  [+] Failure rate acceptable ({total_failed/total_ops*100:.1f}%)")

        report.append("="*70)
        return "\n".join(report)

    def run_all_tests(self):
        """运行所有产品级测试"""
        print("\n" + "="*70)
        print("Product-Level Testing Suite")
        print("="*70)

        self.setup()

        try:
            # 1. 基本操作测试
            self.test_basic_operations()

            # 2. 高并发测试
            self.test_high_concurrency()

            # 3. 大数据量测试
            self.test_large_data_volume()

            # 4. 压力测试
            self.test_stress_load()

            # 5. 边界条件测试
            self.test_boundary_conditions()

            # 生成报告
            print(self.generate_report())

        finally:
            self.adapter.disconnect()
            self.runtime.stop()


def main():
    """主函数"""
    tester = ProductLevelTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
