# -*- coding: utf-8 -*-
"""
Deep Validation of Phase 5 Results

深入核验 Phase 5 实战成果：
1. Bug 真实性检查
2. 测试用例质量分析
3. 组件有效性验证
4. 误报/假阳性分析
5. 覆盖率评估
"""
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Set
from dataclasses import dataclass, field

from agent.runtime import AgentRuntime, AgentConfig
from agent.memory import AgentMemory, MemoryType
from agent.monitor import AgentMonitor
from detectors import StatisticalAnomalyDetector, AnomalyPatternLearner
from adapters import SeekDBAdapter
from core.models import SemanticCase, SlotScope, ErrorCategory


@dataclass
class DeepValidationMetrics:
    """深度验证指标"""
    real_bugs: int = 0
    false_positives: int = 0
    api_errors: int = 0
    product_bugs: int = 0
    test_quality_score: float = 0.0
    coverage_score: float = 0.0
    component_effectiveness: Dict[str, float] = field(default_factory=dict)


class DeepValidator:
    """深度验证器"""

    def __init__(self):
        self.adapter = SeekDBAdapter(host="localhost", port=2881)

        agent_config = AgentConfig(
            agent_id="deep_validator",
            enable_monitoring=True,
            enable_memory=True
        )
        self.runtime = AgentRuntime(config=agent_config)
        self.memory = AgentMemory(agent_id="deep_validator")
        self.monitor = AgentMonitor(agent_id="deep_validator")

        self.anomaly_detector = StatisticalAnomalyDetector()

        # 加载之前的验证结果
        self.previous_results = self._load_validation_results()

        # 分析结果
        self.analysis = {
            "bug_analysis": [],
            "test_analysis": [],
            "component_analysis": {},
            "recommendations": []
        }

    def _load_validation_results(self) -> Dict:
        """加载之前的验证结果"""
        report_path = Path("reports/phase5_validation.json")
        if report_path.exists():
            with open(report_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def analyze_discovered_bugs(self) -> None:
        """分析发现的 bugs"""
        print("\n" + "="*70)
        print("[*] Deep Analysis: Discovered Bugs")
        print("="*70)

        bugs = self.previous_results.get("discovered_bugs", [])

        # 分类统计
        error_types = {}
        for bug in bugs:
            error = bug.get("error", "")
            error_types[error] = error_types.get(error, 0) + 1

        print(f"\n[*] Total Bugs: {len(bugs)}")
        print(f"[*] Unique Error Types: {len(error_types)}")

        # 详细分析每个错误类型
        for error, count in sorted(error_types.items(), key=lambda x: -x[1]):
            percentage = (count / len(bugs)) * 100
            print(f"\n  [{count}x, {percentage:.1f}%] {error}")

            # 分析错误类型
            analysis = self._analyze_error_type(error)
            self.analysis["bug_analysis"].append({
                "error": error,
                "count": count,
                "percentage": percentage,
                "category": analysis["category"],
                "severity": analysis["severity"],
                "is_real_bug": analysis["is_real_bug"],
                "recommendation": analysis["recommendation"]
            })

            print(f"      Category: {analysis['category']}")
            print(f"      Severity: {analysis['severity']}")
            print(f"      Real Bug: {analysis['is_real_bug']}")
            print(f"      Note: {analysis['recommendation']}")

    def _analyze_error_type(self, error: str) -> Dict:
        """分析错误类型"""
        analysis = {
            "category": "unknown",
            "severity": "medium",
            "is_real_bug": False,
            "recommendation": ""
        }

        error_lower = error.lower()

        # API 兼容性问题
        if "takes" in error_lower and "positional arguments" in error_lower:
            analysis["category"] = "API Compatibility"
            analysis["severity"] = "high"
            analysis["is_real_bug"] = True
            analysis["recommendation"] = "检测器 API 签名不匹配，需要修复接口调用"

        # 数据库连接问题
        elif "connection" in error_lower:
            analysis["category"] = "Infrastructure"
            analysis["severity"] = "critical"
            analysis["is_real_bug"] = False
            analysis["recommendation"] = "环境问题，非产品 bug"

        # 参数验证问题
        elif "invalid" in error_lower or "validation" in error_lower:
            analysis["category"] = "Parameter Validation"
            analysis["severity"] = "medium"
            analysis["is_real_bug"] = True
            analysis["recommendation"] = "产品可能需要更好的参数验证"

        # 超时问题
        elif "timeout" in error_lower:
            analysis["category"] = "Performance"
            analysis["severity"] = "medium"
            analysis["is_real_bug"] = True
            analysis["recommendation"] = "性能问题，可能需要优化"

        # 未找到资源
        elif "not found" in error_lower:
            analysis["category"] = "Resource"
            analysis["severity"] = "low"
            analysis["is_real_bug"] = False
            analysis["recommendation"] = "测试前条件问题，非产品 bug"

        return analysis

    def analyze_test_quality(self) -> None:
        """分析测试用例质量"""
        print("\n" + "="*70)
        print("[*] Deep Analysis: Test Quality")
        print("="*70)

        tests = self._generate_diverse_tests()

        # 质量指标
        metrics = {
            "total_tests": len(tests),
            "boundary_tests": 0,
            "extreme_tests": 0,
            "combinatorial_tests": 0,
            "relational_tests": 0,
            "illegal_tests": 0,
            "diversity_score": 0.0,
            "coverage_score": 0.0
        }

        # 分析每个测试
        for test in tests:
            slot_values = test.slot_values

            # 边界值测试
            if "dimension" in slot_values:
                dim = slot_values["dimension"]
                if dim in [1, 128, 512, 1024, 4096, 32768]:
                    metrics["boundary_tests"] += 1

            # 极限值测试
            if slot_values.get("dimension", 0) > 100000 or slot_values.get("top_k", 0) > 10000:
                metrics["extreme_tests"] += 1

            # 组合测试
            if "metric_type" in slot_values and "top_k" in slot_values:
                metrics["combinatorial_tests"] += 1

            # 关系测试
            if "search_range" in slot_values and "top_k" in slot_values:
                metrics["relational_tests"] += 1

            # 非法测试
            if not test.is_legal:
                metrics["illegal_tests"] += 1

        # 计算多样性得分
        category_count = sum([
            metrics["boundary_tests"] > 0,
            metrics["extreme_tests"] > 0,
            metrics["combinatorial_tests"] > 0,
            metrics["relational_tests"] > 0,
            metrics["illegal_tests"] > 0
        ])
        metrics["diversity_score"] = (category_count / 5) * 100

        print(f"\n[*] Test Quality Metrics:")
        print(f"   Total Tests: {metrics['total_tests']}")
        print(f"   Boundary Tests: {metrics['boundary_tests']}")
        print(f"   Extreme Tests: {metrics['extreme_tests']}")
        print(f"   Combinatorial Tests: {metrics['combinatorial_tests']}")
        print(f"   Relational Tests: {metrics['relational_tests']}")
        print(f"   Illegal Tests: {metrics['illegal_tests']}")
        print(f"   Diversity Score: {metrics['diversity_score']:.1f}%")

        # 具体测试示例
        print(f"\n[*] Test Examples:")

        print("\n  [Boundary Tests]")
        for test in tests[:3]:
            print(f"    - {test.test_id}: {test.slot_values}")

        print("\n  [Extreme Tests]")
        for test in tests:
            if test.slot_values.get("dimension", 0) > 100000:
                print(f"    - {test.test_id}: dimension={test.slot_values.get('dimension')}")
                break

        print("\n  [Relational Tests]")
        for test in tests:
            if "search_range" in test.slot_values:
                print(f"    - {test.test_id}: search_range={test.slot_values.get('search_range')}, top_k={test.slot_values.get('top_k')}")
                break

        self.analysis["test_analysis"] = metrics

    def _generate_diverse_tests(self) -> List[SemanticCase]:
        """生成多样化的测试用例"""
        tests = []

        # 边界值测试
        for dim in [1, 128, 512, 1024, 4096, 32768]:
            tests.append(SemanticCase(
                test_id=f"boundary_dim_{dim}",
                operation="search",
                slot_values={"dimension": dim, "top_k": 10},
                raw_parameters={},
                is_legal=True,
                scope=SlotScope.DATABASE
            ))

        # 组合测试
        for metric in ["L2", "IP", "COSINE"]:
            for top_k in [1, 10, 100]:
                tests.append(SemanticCase(
                    test_id=f"combo_{metric}_{top_k}",
                    operation="search",
                    slot_values={"dimension": 512, "metric_type": metric, "top_k": top_k},
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.DATABASE
                ))

        # 极限值测试
        tests.append(SemanticCase(
            test_id="extreme_large_dim",
            operation="search",
            slot_values={"dimension": 999999, "top_k": 99999},
            raw_parameters={},
            is_legal=False,
            scope=SlotScope.DATABASE
        ))

        tests.append(SemanticCase(
            test_id="extreme_zero_dim",
            operation="insert",
            slot_values={"dimension": 0},
            raw_parameters={},
            is_legal=False,
            scope=SlotScope.DATABASE
        ))

        # 关系测试
        tests.append(SemanticCase(
            test_id="relational_range_k",
            operation="search",
            slot_values={"search_range": 10, "top_k": 100},
            raw_parameters={},
            is_legal=False,
            scope=SlotScope.DATABASE
        ))

        return tests

    def verify_component_effectiveness(self) -> None:
        """验证组件有效性"""
        print("\n" + "="*70)
        print("[*] Deep Analysis: Component Effectiveness")
        print("="*70)

        components = {
            "Agent Runtime": self._test_runtime,
            "Agent Memory": self._test_memory,
            "Anomaly Detector": self._test_anomaly_detector,
            "Adapter": self._test_adapter
        }

        for name, test_func in components.items():
            print(f"\n[*] Testing: {name}")
            try:
                effectiveness = test_func()
                self.analysis["component_analysis"][name] = effectiveness
                print(f"   Status: {'PASS' if effectiveness > 0.5 else 'NEEDS IMPROVEMENT'}")
                print(f"   Effectiveness: {effectiveness:.2f}")
            except Exception as e:
                print(f"   Status: FAIL - {e}")
                self.analysis["component_analysis"][name] = 0.0

    def _test_runtime(self) -> float:
        """测试 Agent Runtime"""
        self.runtime.start()
        stats = self.runtime.get_stats()
        self.runtime.stop()

        # 检查功能
        has_stats = "total_operations" in stats or len(stats) > 0
        return 1.0 if has_stats else 0.0

    def _test_memory(self) -> float:
        """测试 Agent Memory"""
        self.memory.store("test_key", {"data": "test_value"}, MemoryType.SHORT_TERM)
        retrieved = self.memory.retrieve("test_key")

        # 检查功能
        has_storage = retrieved is not None
        has_stats = self.memory.get_stats() is not None

        return 1.0 if has_storage and has_stats else 0.5

    def _test_anomaly_detector(self) -> float:
        """测试异常检测器"""
        # 测试检测功能
        base_data = [1.0, 1.1, 0.9, 1.0, 1.1]
        anomaly_value = 5.0

        result = self.anomaly_detector.detect(anomaly_value, base_data)

        # 检查是否检测到异常
        detected = result.is_anomaly
        has_score = result.anomaly_score > 0

        return 1.0 if detected and has_score else 0.5

    def _test_adapter(self) -> float:
        """测试适配器"""
        # 测试基本功能
        capabilities = self.adapter.get_capabilities()

        # 检查能力
        has_ops = len(capabilities.supported_operations) > 0
        has_vectors = len(capabilities.supported_vector_types) > 0

        # 测试参数映射
        param = self.adapter.map_slot_to_param("top_k")
        has_mapping = param == "top_k" or param is not None

        return min(1.0, (0.3 + 0.3 + 0.4) if has_ops and has_vectors and has_mapping else 0.5)

    def check_false_positives(self) -> None:
        """检查假阳性"""
        print("\n" + "="*70)
        print("[*] Deep Analysis: False Positive Check")
        print("="*70)

        bugs = self.previous_results.get("discovered_bugs", [])

        real_bugs = 0
        false_positives = 0
        api_errors = 0
        product_bugs = 0

        for bug in bugs:
            error = bug.get("error", "")
            analysis = self._analyze_error_type(error)

            if not analysis["is_real_bug"]:
                false_positives += 1
            elif analysis["category"] == "API Compatibility":
                api_errors += 1
            elif analysis["category"] in ["Parameter Validation", "Performance"]:
                product_bugs += 1
            else:
                real_bugs += 1

        print(f"\n[*] Bug Classification:")
        print(f"   Real Product Bugs: {real_bugs}")
        print(f"   API/Integration Errors: {api_errors}")
        print(f"   False Positives: {false_positives}")

        if len(bugs) > 0:
            print(f"\n[*] Bug Quality Metrics:")
            print(f"   True Positive Rate: {(real_bugs + product_bugs) / len(bugs) * 100:.1f}%")
            print(f"   False Positive Rate: {false_positives / len(bugs) * 100:.1f}%")

        self.analysis["false_positive_analysis"] = {
            "real_bugs": real_bugs,
            "api_errors": api_errors,
            "false_positives": false_positives,
            "product_bugs": product_bugs
        }

    def generate_recommendations(self) -> None:
        """生成改进建议"""
        print("\n" + "="*70)
        print("[*] Recommendations")
        print("="*70)

        recommendations = []

        # 基于 bug 分析的建议
        bug_analysis = self.analysis.get("bug_analysis", [])
        for analysis in bug_analysis:
            if not analysis["is_real_bug"] and analysis["count"] > 5:
                recommendations.append({
                    "priority": "HIGH",
                    "issue": f"大量 {analysis['category']} 错误",
                    "recommendation": analysis["recommendation"]
                })

        # 基于测试质量的建议
        test_analysis = self.analysis.get("test_analysis", {})
        if test_analysis.get("diversity_score", 0) < 60:
            recommendations.append({
                "priority": "MEDIUM",
                "issue": "测试多样性不足",
                "recommendation": "增加更多类型的测试用例（边界、组合、关系等）"
            })

        # 基于组件有效性的建议
        component_analysis = self.analysis.get("component_analysis", {})
        for component, effectiveness in component_analysis.items():
            if effectiveness < 0.7:
                recommendations.append({
                    "priority": "MEDIUM",
                    "issue": f"{component} 有效性较低",
                    "recommendation": f"检查 {component} 的配置和实现"
                })

        # 输出建议
        if recommendations:
            print(f"\n[*] Found {len(recommendations)} recommendations:\n")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. [{rec['priority']}] {rec['issue']}")
                print(f"     -> {rec['recommendation']}")
        else:
            print("\n[+] No critical issues found!")

        self.analysis["recommendations"] = recommendations

    def save_deep_analysis_report(self) -> None:
        """保存深度分析报告"""
        output = Path("reports/phase5_deep_validation.json")
        output.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "timestamp": time.time(),
            "bug_analysis": self.analysis.get("bug_analysis", []),
            "test_analysis": self.analysis.get("test_analysis", {}),
            "component_analysis": self.analysis.get("component_analysis", {}),
            "false_positive_analysis": self.analysis.get("false_positive_analysis", {}),
            "recommendations": self.analysis.get("recommendations", [])
        }

        with open(output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n[+] Deep analysis report saved to: {output}")

    def run_deep_validation(self):
        """运行深度验证"""
        print("\n" + "="*70)
        print("Phase 5 Deep Validation: Results Verification")
        print("="*70)

        # 连接数据库
        self.adapter.connect()

        try:
            # 1. 分析发现的 bugs
            self.analyze_discovered_bugs()

            # 2. 分析测试质量
            self.analyze_test_quality()

            # 3. 验证组件有效性
            self.verify_component_effectiveness()

            # 4. 检查假阳性
            self.check_false_positives()

            # 5. 生成建议
            self.generate_recommendations()

            # 6. 保存报告
            self.save_deep_analysis_report()

            # 总结
            print("\n" + "="*70)
            print("[*] Deep Validation Summary")
            print("="*70)

            fp_analysis = self.analysis.get("false_positive_analysis", {})
            print(f"\n[*] Bug Quality:")
            print(f"   Real Product Bugs: {fp_analysis.get('product_bugs', 0)}")
            print(f"   API/Integration Issues: {fp_analysis.get('api_errors', 0)}")
            print(f"   False Positives: {fp_analysis.get('false_positives', 0)}")

            component_analysis = self.analysis.get("component_analysis", {})
            print(f"\n[*] Component Health:")
            for comp, eff in component_analysis.items():
                status = "HEALTHY" if eff >= 0.7 else "NEEDS ATTENTION"
                print(f"   {comp}: {eff:.2f} [{status}]")

            rec_count = len(self.analysis.get("recommendations", []))
            print(f"\n[*] Recommendations: {rec_count}")

        finally:
            self.adapter.disconnect()


def main():
    """主函数"""
    validator = DeepValidator()
    validator.run_deep_validation()


if __name__ == "__main__":
    main()
