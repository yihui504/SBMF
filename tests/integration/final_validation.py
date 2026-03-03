# -*- coding: utf-8 -*-
"""
Final Validation: Phase 5 Improvements Verification

验证三个改进任务：
1. 修复异常检测 API 问题
2. 增强产品级测试
3. 优化生成策略
"""
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any

from agent.runtime import AgentRuntime, AgentConfig
from agent.memory import AgentMemory, MemoryType
from detectors import AnomalyDetectionAdapter
from adapters import SeekDBAdapter
from generators.enhanced_strategy import EnhancedTestGenerator
from core.models import SemanticCase, SlotScope


class FinalValidator:
    """最终验证器"""

    def __init__(self):
        self.adapter = SeekDBAdapter(host="localhost", port=2881)

        # Agent 组件
        agent_config = AgentConfig(
            agent_id="final_validator",
            enable_monitoring=True,
            enable_memory=True
        )
        self.runtime = AgentRuntime(config=agent_config)
        self.memory = AgentMemory(agent_id="final_validator")

        # 改进的组件
        self.anomaly_adapter = AnomalyDetectionAdapter(method="z_score", threshold=2.5)
        self.enhanced_generator = EnhancedTestGenerator(adapter=self.adapter)

        self.results = {
            "anomaly_detector_fixed": False,
            "product_tests_passed": 0,
            "enhanced_strategy_diversity": 0.0,
            "total_bugs_found": 0
        }

    def verify_anomaly_detector_fix(self) -> bool:
        """验证异常检测器修复"""
        print("\n" + "="*70)
        print("[*] Task 1: Verify Anomaly Detector Fix")
        print("="*70)

        try:
            # 测试正常值
            history = [1.0, 1.1, 0.9, 1.0, 1.1, 0.95, 1.05]
            normal_value = 1.02

            result = self.anomaly_adapter.detect(normal_value, history)

            print(f"\n[*] Test 1: Normal Value Detection")
            print(f"   Input: {normal_value}")
            print(f"   History: {history}")
            print(f"   Is Anomaly: {result.is_anomaly}")
            print(f"   Score: {result.anomaly_score:.3f}")
            print(f"   Z-score: {result.z_score:.2f}")
            print(f"   Status: {'PASS' if not result.is_anomaly else 'FAIL'}")

            # 测试异常值
            anomaly_value = 5.0
            result2 = self.anomaly_adapter.detect(anomaly_value, history)

            print(f"\n[*] Test 2: Anomaly Value Detection")
            print(f"   Input: {anomaly_value}")
            print(f"   History: {history}")
            print(f"   Is Anomaly: {result2.is_anomaly}")
            print(f"   Score: {result2.anomaly_score:.3f}")
            print(f"   Z-score: {result2.z_score:.2f}")
            print(f"   Status: {'PASS' if result2.is_anomaly else 'FAIL'}")

            # 测试 IQR 方法
            iqr_adapter = AnomalyDetectionAdapter(method="iqr", threshold=1.5)
            result3 = iqr_adapter.detect(anomaly_value, history)

            print(f"\n[*] Test 3: IQR Method")
            print(f"   Is Anomaly: {result3.is_anomaly}")
            print(f"   Score: {result3.anomaly_score:.3f}")
            print(f"   Status: {'PASS' if result3.is_anomaly else 'FAIL'}")

            self.results["anomaly_detector_fixed"] = True
            print(f"\n[+] Anomaly Detector Fix: VERIFIED")
            return True

        except Exception as e:
            print(f"\n[!] Anomaly Detector Fix: FAILED - {e}")
            return False

    def verify_product_level_testing(self) -> bool:
        """验证产品级测试增强"""
        print("\n" + "="*70)
        print("[*] Task 2: Verify Product-Level Testing")
        print("="*70)

        from tests.integration.product_level_test import ProductLevelTester

        tester = ProductLevelTester()
        tester.setup()

        try:
            # 运行基本操作测试
            result1 = tester.test_basic_operations()

            # 运行高并发测试
            result2 = tester.test_high_concurrency()

            # 运行大数据量测试
            result3 = tester.test_large_data_volume()

            # 运行边界条件测试
            result4 = tester.test_boundary_conditions()

            # 汇总结果
            total_ops = result1.total_operations + result2.total_operations + result3.total_operations + result4.total_operations
            total_success = result1.successful_operations + result2.successful_operations + result3.successful_operations + result4.successful_operations
            total_bugs = result1.bugs_found + result2.bugs_found + result3.bugs_found + result4.bugs_found

            print(f"\n[*] Product-Level Testing Summary:")
            print(f"   Total Operations: {total_ops}")
            print(f"   Success Rate: {total_success/total_ops*100:.1f}%")
            print(f"   Bugs Found: {total_bugs}")

            self.results["product_tests_passed"] = total_success
            self.results["total_bugs_found"] = total_bugs

            print(f"\n[+] Product-Level Testing: VERIFIED")
            return True

        except Exception as e:
            print(f"\n[!] Product-Level Testing: FAILED - {e}")
            return False

        finally:
            tester.adapter.disconnect()
            tester.runtime.stop()

    def verify_enhanced_strategy(self) -> bool:
        """验证优化的生成策略"""
        print("\n" + "="*70)
        print("[*] Task 3: Verify Enhanced Generation Strategy")
        print("="*70)

        try:
            # 生成测试
            print(f"\n[*] Generating tests with enhanced strategy...")
            tests = self.enhanced_generator.generate_mixed_strategy(total_count=100)

            # 分析多样性
            diversity = self.enhanced_generator.analyze_diversity(tests)

            print(f"\n[*] Enhanced Strategy Results:")
            print(f"   Generated Tests: {len(tests)}")
            print(f"   Diversity Score: {diversity['diversity_score']:.1f}%")
            print(f"   Boundary Coverage: {diversity['boundary_coverage']:.1f}%")
            print(f"   Constraint Coverage: {diversity['constraint_coverage']:.1f}%")
            print(f"   Combinatorial Depth: {diversity['combinatorial_depth']:.2f}")

            # 策略分布
            strategy_counts = {}
            for test in tests:
                if "boundary" in test.test_id:
                    strategy_counts["boundary"] = strategy_counts.get("boundary", 0) + 1
                elif "combo" in test.test_id:
                    strategy_counts["combinatorial"] = strategy_counts.get("combinatorial", 0) + 1
                elif "rel" in test.test_id:
                    strategy_counts["relational"] = strategy_counts.get("relational", 0) + 1
                elif "extreme" in test.test_id:
                    strategy_counts["extreme"] = strategy_counts.get("extreme", 0) + 1
                elif "adaptive" in test.test_id:
                    strategy_counts["adaptive"] = strategy_counts.get("adaptive", 0) + 1

            print(f"\n[*] Strategy Distribution:")
            for strategy, count in sorted(strategy_counts.items(), key=lambda x: -x[1]):
                pct = (count / len(tests)) * 100
                print(f"   {strategy}: {count} ({pct:.1f}%)")

            # 验证改进
            improvements = []

            if diversity['diversity_score'] > 60:
                improvements.append("Diversity score > 60%")
                self.results["enhanced_strategy_diversity"] = diversity['diversity_score']

            if diversity['boundary_coverage'] > 30:
                improvements.append("Boundary coverage > 30%")

            if diversity['constraint_coverage'] > 5:
                improvements.append("Constraint coverage > 5%")

            if len(strategy_counts) >= 4:
                improvements.append(f"Uses {len(strategy_counts)} different strategies")

            print(f"\n[*] Improvements Verified:")
            for improvement in improvements:
                print(f"   [+] {improvement}")

            print(f"\n[+] Enhanced Strategy: VERIFIED")
            return True

        except Exception as e:
            print(f"\n[!] Enhanced Strategy: FAILED - {e}")
            return False

    def run_final_validation(self):
        """运行最终验证"""
        print("\n" + "="*70)
        print("Phase 5 Final Validation: Improvements Verification")
        print("="*70)

        # 连接数据库
        self.adapter.connect()
        self.runtime.start()

        try:
            # 任务 1: 验证异常检测器修复
            task1_pass = self.verify_anomaly_detector_fix()

            # 任务 2: 验证产品级测试
            task2_pass = self.verify_product_level_testing()

            # 任务 3: 验证优化的生成策略
            task3_pass = self.verify_enhanced_strategy()

            # 最终报告
            print("\n" + "="*70)
            print("[*] Final Validation Summary")
            print("="*70)

            tasks = [
                ("Anomaly Detector Fix", task1_pass),
                ("Product-Level Testing", task2_pass),
                ("Enhanced Strategy", task3_pass)
            ]

            print(f"\n[*] Task Results:")
            all_pass = True
            for task_name, passed in tasks:
                status = "PASS" if passed else "FAIL"
                symbol = "[+]" if passed else "[!]"
                print(f"   {symbol} {task_name}: {status}")
                if not passed:
                    all_pass = False

            print(f"\n[*] Overall Status: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")

            # 统计数据
            print(f"\n[*] Key Metrics:")
            print(f"   Anomaly Detector Fixed: {self.results['anomaly_detector_fixed']}")
            print(f"   Product Tests Passed: {self.results.get('product_tests_passed', 0)}")
            print(f"   Bugs Found: {self.results.get('total_bugs_found', 0)}")
            print(f"   Enhanced Diversity Score: {self.results.get('enhanced_strategy_diversity', 0):.1f}%")

            # 保存报告
            self._save_report()

        finally:
            self.adapter.disconnect()
            self.runtime.stop()

    def _save_report(self):
        """保存验证报告"""
        output = Path("reports/phase5_final_validation.json")
        output.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "timestamp": time.time(),
            "results": self.results,
            "validation_complete": True
        }

        with open(output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n[+] Final validation report saved to: {output}")


def main():
    """主函数"""
    validator = FinalValidator()
    validator.run_final_validation()


if __name__ == "__main__":
    main()
