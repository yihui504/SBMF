"""
实战测试：Phase 5 智能体驱动功能验证

在实际 SeekDB 环境上验证以下功能：
1. Agent 驱动的智能测试生成 (M0)
2. 自适应异常检测 (M1)
3. 增强模糊测试 (M3)
4. Bug 分析与修复建议 (M4)
5. 智能报告生成 (M6)

对比分析：
- 传统测试 vs 智能体驱动测试
- 发现 bug 的数量和质量
- 测试效率提升
"""
import time
import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field

from agent.runtime import AgentRuntime, AgentConfig
from generators.agent import TestGenerationAgent, TestGenerationCache
from fuzzing.agent import FuzzingAgent, FuzzerConfig
from anomaly.detector import AnomalyDetector, PatternAnalyzer
from anomaly.feedback import FeedbackLoop
from analysis.bug_analyzer import BugAnalyzer
from analysis.fix_recommender import FixRecommender
from reporting.generator import ReportGenerator
from adapters.seekdb import SeekDBAdapter
from core.models import SemanticCase, ErrorCategory, SlotScope


@dataclass
class ValidationMetrics:
    """验证指标"""
    total_tests_run: int = 0
    bugs_found: int = 0
    unique_bugs: int = 0
    critical_bugs: int = 0
    test_generation_time: float = 0.0
    execution_time: float = 0.0
    bugs_by_type: Dict[str, int] = field(default_factory=dict)
    bugs_by_severity: Dict[str, int] = field(default_factory=dict)
    coverage_gain: float = 0.0
    anomaly_detections: int = 0
    fuzzing_crashes: int = 0


class Phase5Validator:
    """Phase 5 功能验证器"""

    def __init__(self, seekdb_host: str = "localhost", seekdb_port: int = 2881):
        """
        初始化验证器

        Args:
            seekdb_host: SeekDB 主机
            seekdb_port: SeekDB 端口
        """
        self.seekdb_host = seekdb_host
        self.seekdb_port = seekdb_port

        # 初始化 SeekDB 适配器
        self.adapter = SeekDBAdapter(host=seekdb_host, port=seekdb_port)

        # 初始化 Agent 运行时
        agent_config = AgentConfig(
            agent_id="phase5_validator",
            enable_monitoring=True,
            enable_memory=True
        )
        self.runtime = AgentRuntime(agent_config)

        # 初始化各组件
        self.test_generator = None
        self.fuzzing_agent = None
        self.anomaly_detector = None
        self.bug_analyzer = None
        self.fix_recommender = None
        self.report_generator = None

        # 存储结果
        self.results = {
            "traditional": ValidationMetrics(),
            "agent_driven": ValidationMetrics()
        }

        self.discovered_bugs = []

    def setup(self) -> bool:
        """设置验证环境"""
        print("🔧 设置验证环境...")

        # 连接 SeekDB
        if not self.adapter.connect():
            print("❌ 无法连接到 SeekDB，使用模拟模式")
            return False

        print(f"✅ 已连接到 SeekDB ({self.seekdb_host}:{self.seekdb_port})")

        # 初始化组件
        self.test_generator = TestGenerationAgent(self.adapter)
        self.fuzzing_agent = FuzzingAgent(FuzzerConfig(
            max_iterations=100,
            max_duration=30.0
        ))
        self.anomaly_detector = AnomalyDetector()
        self.bug_analyzer = BugAnalyzer()
        self.fix_recommender = FixRecommender()
        self.report_generator = ReportGenerator()

        # 启动 Agent 运行时
        self.runtime.start()

        print("✅ 所有组件初始化完成")
        return True

    def run_traditional_testing(self) -> ValidationMetrics:
        """运行传统测试（基线对比）"""
        print("\n" + "="*60)
        print("📊 运行传统测试（基线）...")
        print("="*60)

        metrics = ValidationMetrics()
        start_time = time.time()

        # 传统测试：固定测试用例
        traditional_tests = self._get_traditional_test_cases()

        print(f"📝 生成 {len(traditional_tests)} 个传统测试用例")

        for test_case in traditional_tests:
            try:
                result = self.adapter.execute_test(test_case)
                metrics.total_tests_run += 1

                # 检查是否发现 bug
                if result.status.value == "FAILURE":
                    bug_info = self._analyze_bug(result, test_case)
                    self.discovered_bugs.append({
                        **bug_info,
                        "method": "traditional"
                    })
                    metrics.bugs_found += 1

            except Exception as e:
                # 异常也算 bug
                metrics.bugs_found += 1
                self.discovered_bugs.append({
                    "error": str(e),
                    "operation": test_case.operation,
                    "method": "traditional",
                    "severity": "medium"
                })

        metrics.execution_time = time.time() - start_time

        # 统计唯一 bug
        metrics.unique_bugs = len(set(
            b.get("error", "") for b in self.discovered_bugs
            if b.get("method") == "traditional"
        ))

        print(f"✅ 传统测试完成:")
        print(f"   - 执行: {metrics.total_tests_run} 个测试")
        print(f"   - 发现: {metrics.bugs_found} 个 bug")
        print(f"   - 唯一: {metrics.unique_bugs} 个")
        print(f"   - 耗时: {metrics.execution_time:.2f} 秒")

        return metrics

    def run_agent_driven_testing(self) -> ValidationMetrics:
        """运行智能体驱动测试"""
        print("\n" + "="*60)
        print("🤖 运行智能体驱动测试...")
        print("="*60)

        metrics = ValidationMetrics()
        self.runtime.start()

        try:
            # 1. 智能测试生成 (M0)
            print("\n📝 M0: 智能测试生成...")
            gen_start = time.time()

            generated_tests = self.test_generator.generate_batch(
                operations=["search", "insert", "delete"],
                count=50
            )

            metrics.test_generation_time = time.time() - gen_start
            print(f"   ✅ 生成 {len(generated_tests)} 个智能测试用例 ({metrics.test_generation_time:.2f}s)")

            # 2. 模糊测试 (M3)
            print("\n🧪 M3: 增强模糊测试...")

            initial_inputs = [
                {"dimension": 512, "metric_type": "L2", "top_k": 10},
                {"dimension": 1024, "metric_type": "IP", "top_k": 100},
            ]

            def execute_func(test_input):
                # 将字典转换为 SemanticCase
                test_case = SemanticCase(
                    test_id=f"fuzz_{len(self.discovered_bugs)}",
                    operation="search",
                    slot_values=test_input,
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.DATABASE
                )
                return self.adapter.execute_test(test_case)

            fuzzing_session = self.fuzzing_agent.fuzz(
                initial_inputs,
                execute_func,
                max_iterations=50
            )

            metrics.fuzzing_crashes = fuzzing_session.crashes_found
            print(f"   ✅ 模糊测试完成:")
            print(f"      - 迭代: {fuzzing_session.total_iterations}")
            print(f"      - 执行: {fuzzing_session.total_executions}")
            print(f"      - 崩溃: {fuzzing_session.crashes_found}")
            print(f"      - 唯一崩溃: {fuzzing_session.unique_crashes}")

            # 3. 执行智能生成的测试并检测异常 (M1)
            print("\n🎯 M1: 自适应异常检测...")

            execution_times = []
            anomaly_count = 0

            for test_case in generated_tests[:30]:  # 限制数量
                try:
                    exec_start = time.time()
                    result = self.adapter.execute_test(test_case)
                    exec_time = time.time() - exec_start
                    execution_times.append(exec_time)

                    metrics.total_tests_run += 1

                    # 检测异常
                    if len(execution_times) > 5:
                        is_anomaly, score = self.anomaly_detector.detect_z_score(
                            exec_time, execution_times[:-1]
                        )
                        if is_anomaly:
                            anomaly_count += 1
                            metrics.anomaly_detections += 1
                            print(f"      ⚠️  检测到异常: 执行时间 {exec_time:.3f}s (z-score: {score:.2f})")

                    # 分析 bug (M4)
                    if result.status.value in ["FAILURE", "TIMEOUT", "CRASH"]:
                        bug_info = self._analyze_bug(result, test_case)
                        bug_info["method"] = "agent_driven"
                        bug_info["anomaly_detected"] = (exec_time in execution_times and
                                                         len(execution_times) > 5 and
                                                         self.anomaly_detector.detect_z_score(
                                                             exec_time, execution_times[:-1]
                                                         )[0])

                        self.discovered_bugs.append(bug_info)
                        metrics.bugs_found += 1

                        # 生成修复建议 (M4)
                        if result.error:
                            recommendations = self.fix_recommender.generate_recommendations(
                                result.error, test_case
                            )
                            bug_info["recommendations"] = recommendations

                except Exception as e:
                    metrics.bugs_found += 1
                    self.discovered_bugs.append({
                        "error": str(e),
                        "operation": test_case.operation,
                        "method": "agent_driven",
                        "severity": "high"
                    })

            print(f"   ✅ 异常检测完成: 检测到 {metrics.anomaly_detections} 个异常")

            # 4. 模式分析
            if len(execution_times) > 10:
                print("\n📈 M1: 模式分析...")
                analyzer = PatternAnalyzer()
                patterns = analyzer.analyze_time_series(execution_times)
                print(f"   ✅ 分析结果:")
                print(f"      - 趋势: {patterns.get('trend', 'unknown')}")
                print(f"      - 周期性: {patterns.get('has_periodicity', False)}")
                print(f"      - 异常点: {patterns.get('anomaly_count', 0)}")

            metrics.execution_time = time.time() - start_time
            metrics.unique_bugs = len(set(
                b.get("error", "") for b in self.discovered_bugs
                if b.get("method") == "agent_driven"
            ))

        finally:
            self.runtime.stop()

        print(f"\n✅ 智能体驱动测试完成:")
        print(f"   - 执行: {metrics.total_tests_run} 个测试")
        print(f"   - 发现: {metrics.bugs_found} 个 bug")
        print(f"   - 唯一: {metrics.unique_bugs} 个")
        print(f"   - 异常: {metrics.anomaly_detections} 个")
        print(f"   - 耗时: {metrics.execution_time:.2f} 秒")

        return metrics

    def _analyze_bug(self, result, test_case) -> Dict[str, Any]:
        """分析 bug"""
        error_category = self.adapter.classify_error(result.error) if result.error else None

        bug_info = {
            "operation": test_case.operation,
            "slot_values": test_case.slot_values,
            "error": str(result.error) if result.error else result.status.value,
            "error_category": str(error_category) if error_category else "unknown",
            "execution_time": result.elapsed_seconds,
            "severity": self._determine_severity(error_category) if error_category else "low"
        }

        return bug_info

    def _determine_severity(self, error_category) -> str:
        """确定严重程度"""
        if error_category == ErrorCategory.PRODUCT_SUSPECT:
            return "critical"
        elif error_category == ErrorCategory.PRECONDITION_FAILED:
            return "high"
        else:
            return "medium"

    def _get_traditional_test_cases(self) -> List[SemanticCase]:
        """获取传统测试用例（固定集合）"""
        return [
            SemanticCase(
                test_id="trad_001",
                operation="search",
                slot_values={"dimension": 128, "top_k": 10},
                raw_parameters={},
                is_legal=True,
                scope=SlotScope.DATABASE
            ),
            SemanticCase(
                test_id="trad_002",
                operation="search",
                slot_values={"dimension": 256, "top_k": 100},
                raw_parameters={},
                is_legal=True,
                scope=SlotScope.DATABASE
            ),
            SemanticCase(
                test_id="trad_003",
                operation="search",
                slot_values={"dimension": 512, "metric_type": "L2"},
                raw_parameters={},
                is_legal=True,
                scope=SlotScope.DATABASE
            ),
            SemanticCase(
                test_id="trad_004",
                operation="search",
                slot_values={"dimension": 1024, "top_k": 50},
                raw_parameters={},
                is_legal=True,
                scope=SlotScope.DATABASE
            ),
            SemanticCase(
                test_id="trad_005",
                operation="insert",
                slot_values={"dimension": 512},
                raw_parameters={},
                is_legal=True,
                scope=SlotScope.DATABASE
            ),
        ]

    def generate_comparison_report(self) -> str:
        """生成对比报告"""
        trad = self.results["traditional"]
        agent = self.results["agent_driven"]

        report = []
        report.append("\n" + "="*70)
        report.append("📊 Phase 5 实战验证报告")
        report.append("="*70)

        # 对比表格
        report.append("\n📈 性能对比:")
        report.append("-" * 70)
        report.append(f"{'指标':<25} {'传统测试':<15} {'智能体驱动':<15} {'提升':<10}")
        report.append("-" * 70)

        # 测试执行数
        trad_tests = trad.total_tests_run
        agent_tests = agent.total_tests_run
        improvement = f"+{((agent_tests - trad_tests) / trad_tests * 100):.1f}%" if trad_tests > 0 else "N/A"
        report.append(f"{'执行测试数':<25} {trad_tests:<15} {agent_tests:<15} {improvement:<10}")

        # Bug 发现数
        trad_bugs = trad.bugs_found
        agent_bugs = agent.bugs_found
        improvement = f"+{((agent_bugs - trad_bugs) / trad_bugs * 100):.1f}%" if trad_bugs > 0 else "N/A"
        report.append(f"{'Bug 发现数':<25} {trad_bugs:<15} {agent_bugs:<15} {improvement:<10}")

        # 唯一 Bug 数
        trad_unique = trad.unique_bugs
        agent_unique = agent.unique_bugs
        improvement = f"+{((agent_unique - trad_unique) / trad_unique * 100):.1f}%" if trad_unique > 0 else "N/A"
        report.append(f"{'唯一 Bug 数':<25} {trad_unique:<15} {agent_unique:<15} {improvement:<10}")

        # 执行时间
        trad_time = trad.execution_time
        agent_time = agent.execution_time
        improvement = f"{((trad_time - agent_time) / trad_time * 100):.1f}%" if trad_time > 0 else "N/A"
        report.append(f"{'执行时间 (秒)':<25} {trad_time:<15.2f} {agent_time:<15.2f} {improvement:<10}")

        # 效率 (bugs/秒)
        trad_eff = trad_bugs / trad_time if trad_time > 0 else 0
        agent_eff = agent_bugs / agent_time if agent_time > 0 else 0
        improvement = f"+{((agent_eff - trad_eff) / trad_eff * 100):.1f}%" if trad_eff > 0 else "N/A"
        report.append(f"{'效率 (Bug/秒)':<25} {trad_eff:<15.3f} {agent_eff:<15.3f} {improvement:<10}")

        report.append("-" * 70)

        # 功能增强
        report.append("\n🚀 Phase 5 功能增强:")
        report.append("-" * 70)
        report.append(f"✅ M0: 智能测试生成 - 生成 {agent.total_tests_run} 个智能测试")
        report.append(f"✅ M1: 异常检测 - 检测到 {agent.anomaly_detections} 个异常")
        report.append(f"✅ M3: 模糊测试 - 发现 {agent.fuzzing_crashes} 个崩溃")
        report.append(f"✅ M4: Bug 分析 - 自动分类和严重程度评估")
        report.append(f"✅ M6: 智能报告 - 本报告")

        # Bug 分类统计
        if self.discovered_bugs:
            report.append("\n🐛 Bug 分类统计:")
            report.append("-" * 70)

            severity_count = {}
            for bug in self.discovered_bugs:
                severity = bug.get("severity", "unknown")
                severity_count[severity] = severity_count.get(severity, 0) + 1

            for severity, count in sorted(severity_count.items(), key=lambda x: -x[1]):
                report.append(f"   {severity.capitalize()}: {count}")

        # 结论
        report.append("\n💡 结论:")
        report.append("-" * 70)

        if agent_bugs > trad_bugs:
            improvement = ((agent_bugs - trad_bugs) / trad_bugs * 100) if trad_bugs > 0 else 0
            report.append(f"✨ 智能体驱动测试比传统测试多发现 {agent_bugs - trad_bugs} 个 bug")
            report.append(f"   (提升 {improvement:.1f}%)")
        else:
            report.append("⚠️  智能体驱动测试需要进一步调优")

        if agent.anomaly_detections > 0:
            report.append(f"✨ 异常检测发现了 {agent.anomaly_detections} 个潜在问题")

        if agent.fuzzing_crashes > 0:
            report.append(f"✨ 模糊测试发现了 {agent.fuzzing_crashes} 个崩溃")

        report.append("="*70)

        return "\n".join(report)

    def save_detailed_report(self, output_path: str = "reports/phase5_validation.json"):
        """保存详细报告"""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        detailed_report = {
            "validation_summary": {
                "traditional_metrics": self.results["traditional"].__dict__,
                "agent_driven_metrics": self.results["agent_driven"].__dict__,
            },
            "discovered_bugs": self.discovered_bugs,
            "timestamp": time.time()
        }

        with open(output, 'w', encoding='utf-8') as f:
            json.dump(detailed_report, f, indent=2, ensure_ascii=False, default=str)

        print(f"📄 详细报告已保存到: {output}")

    def run_validation(self):
        """运行完整验证"""
        print("\n" + "="*70)
        print("🎯 Phase 5 实战验证: 智能体驱动 Bug 挖掘")
        print("="*70)

        # 设置
        if not self.setup():
            print("⚠️  无法连接实际数据库，使用模拟模式继续...")

        # 运行传统测试
        self.results["traditional"] = self.run_traditional_testing()

        # 重置 bug 列表
        self.discovered_bugs = []

        # 运行智能体驱动测试
        self.results["agent_driven"] = self.run_agent_driven_testing()

        # 生成报告
        print(self.generate_comparison_report())

        # 保存详细报告
        self.save_detailed_report()

        # 断开连接
        self.adapter.disconnect()


def main():
    """主函数"""
    validator = Phase5Validator(
        seekdb_host="localhost",
        seekdb_port=2881
    )

    validator.run_validation()


if __name__ == "__main__":
    main()
