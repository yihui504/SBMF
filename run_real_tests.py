#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Real-World SeekDB实战测试执行器

执行真实数据库环境的完整测试流程，包括：
- 连接真实 SeekDB 或回退到模拟模式
- 运行所有测试场景
- 生成详细测试报告
"""
import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

from contract import load_contract
from profiles import SeekDBProfilePlugin
from core import (
    ExecutionPipeline,
    OracleReporter,
    RuleEngine,
    PreconditionGate,
    ReportFormat,
)
from core.models import SemanticCase, SlotScope, ExecutionStatus
from oracle import (
    RangeConstraintOracle,
    EnumConstraintOracle,
    RelationalConstraintOracle,
    StatusValidationOracle,
    OracleResult,
    ComparisonOperator,
)

# Import both adapters
from adapters.seekdb import SeekDBAdapter as MockSeekDBAdapter
from adapters.real_seekdb import create_seekdb_adapter, RealSeekDBAdapter


# ================================================================
# Configuration
# ================================================================

class TestConfig:
    """测试配置"""
    def __init__(self):
        # Load from environment or use defaults
        if DOTENV_AVAILABLE:
            load_dotenv()

        self.seekdb_host = os.getenv("SEEKDB_HOST", "localhost")
        self.seekdb_port = int(os.getenv("SEEKDB_PORT", "2881"))
        self.use_real_adapter = os.getenv("USE_REAL_ADAPTER", "true").lower() == "true"
        self.test_collection = os.getenv("TEST_COLLECTION", "test_framework")
        self.verbose = os.getenv("VERBOSE_TESTS", "false").lower() == "true"


# ================================================================
# Test Scenario Runner
# ================================================================

class RealWorldTestRunner:
    """真实世界测试运行器"""

    def __init__(self, config: TestConfig):
        self.config = config
        self.adapter = None
        self.test_results = []
        self.oracle_results_by_test = []
        self.start_time = None

    def setup(self):
        """设置测试环境"""
        print("=" * 70)
        print("Semantic Bug Mining Framework - Real-World Test Runner")
        print("=" * 70)
        print()
        print(f"Configuration:")
        print(f"  SeekDB: {self.config.seekdb_host}:{self.config.seekdb_port}")
        print(f"  Use Real Adapter: {self.config.use_real_adapter}")
        print()

        # Create adapter
        print("Initializing SeekDB adapter...")
        self.adapter = create_seekdb_adapter(
            host=self.config.seekdb_host,
            port=self.config.seekdb_port,
            use_real_adapter=self.config.use_real_adapter
        )

        # Check adapter type
        if hasattr(self.adapter, '_is_mock'):
            print("  Status: MOCK MODE (simulated responses)")
        else:
            print("  Status: REAL MODE (connected to database)")

        print()

        # Load Contract
        print("Loading Contract...")
        self.contract = load_contract("tests/fixtures/integration/seekdb_contract.yaml")
        print(f"  Loaded Contract: {self.contract.database_name} v{self.contract.version}")
        print(f"  Slots: {len(self.contract.core_slots)} semantic slots defined")
        print()

        # Create Profile
        self.profile = SeekDBProfilePlugin(enable_logging=True)

        # Create Oracle checkers
        self.oracles = [
            RangeConstraintOracle("dimension", min_value=1, max_value=32768),
            EnumConstraintOracle("metric_type", allowed_values=["L2", "IP", "COSINE"]),
            RelationalConstraintOracle("search_range", ComparisonOperator.GE, "top_k"),
            StatusValidationOracle(expected_status="SUCCESS"),
        ]

        # Create pipeline
        rule_engine = RuleEngine(self.contract)
        precondition_gate = PreconditionGate(rule_engine)

        self.pipeline = ExecutionPipeline(
            rule_engine=rule_engine,
            precondition_gate=precondition_gate,
            oracles=self.oracles
        )

        print("Test environment ready.")
        print()

    def run_test_scenarios(self) -> Dict[str, Any]:
        """运行所有测试场景"""
        scenarios = [
            {
                "id": "S001",
                "name": "Normal Search",
                "test_case": SemanticCase(
                    test_id="S001_Normal_Search",
                    operation="search",
                    slot_values={
                        "dimension": 512,
                        "metric_type": "L2",
                        "top_k": 10,
                        "search_range": 100,
                        "collection_name": self.config.test_collection,
                    },
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.COLLECTION
                ),
                "expected_status": "SUCCESS",
                "description": "Normal search with all valid parameters"
            },
            {
                "id": "S002",
                "name": "Dimension Exceeds Maximum",
                "test_case": SemanticCase(
                    test_id="S002_Dimension_Exceeds_Max",
                    operation="search",
                    slot_values={
                        "dimension": 99999,
                        "metric_type": "L2",
                        "top_k": 10,
                    },
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.COLLECTION
                ),
                "expected_status": "PRECONDITION_FAILED",
                "description": "Dimension exceeds maximum - should be skipped by Profile"
            },
            {
                "id": "S003",
                "name": "Unsupported Metric Type",
                "test_case": SemanticCase(
                    test_id="S003_Unsupported_Metric",
                    operation="search",
                    slot_values={
                        "dimension": 512,
                        "metric_type": "HAMMING",
                        "top_k": 10,
                    },
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.COLLECTION
                ),
                "expected_status": "PRECONDITION_FAILED",
                "description": "HAMMING metric not supported - should be skipped"
            },
            {
                "id": "S004",
                "name": "Boundary Test - Minimum Dimension",
                "test_case": SemanticCase(
                    test_id="S004_Dimension_Min",
                    operation="search",
                    slot_values={
                        "dimension": 1,
                        "metric_type": "L2",
                        "top_k": 1,
                    },
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.COLLECTION
                ),
                "expected_status": "SUCCESS",
                "description": "Minimum valid dimension"
            },
            {
                "id": "S005",
                "name": "Boundary Test - Maximum Dimension",
                "test_case": SemanticCase(
                    test_id="S005_Dimension_Max",
                    operation="search",
                    slot_values={
                        "dimension": 32768,
                        "metric_type": "L2",
                        "top_k": 1,
                    },
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.COLLECTION
                ),
                "expected_status": "SUCCESS",
                "description": "Maximum valid dimension"
            },
            {
                "id": "S006",
                "name": "COSINE + HNSW Not Supported",
                "test_case": SemanticCase(
                    test_id="S006_COSINE_HNSW",
                    operation="search",
                    slot_values={
                        "dimension": 512,
                        "metric_type": "COSINE",
                        "index_type": "HNSW",
                        "top_k": 10,
                    },
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.COLLECTION
                ),
                "expected_status": "PRECONDITION_FAILED",
                "description": "COSINE + HNSW combination not supported"
            },
            {
                "id": "S007",
                "name": "Large Top K",
                "test_case": SemanticCase(
                    test_id="S007_Large_TopK",
                    operation="search",
                    slot_values={
                        "dimension": 512,
                        "metric_type": "L2",
                        "top_k": 5000,
                        "search_range": 5000,
                    },
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.COLLECTION
                ),
                "expected_status": "SUCCESS",
                "description": "Large top_k test"
            },
        ]

        results = {
            "total": len(scenarios),
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "scenarios": []
        }

        print(f"Running {len(scenarios)} test scenarios...")
        print("-" * 70)
        print()

        for scenario in scenarios:
            result = self._run_single_test(scenario)
            results["scenarios"].append(result)

            if result["status"] == "PASS":
                results["passed"] += 1
            elif result["status"] == "FAIL":
                results["failed"] += 1
            elif result["status"] == "SKIP":
                results["skipped"] += 1

            # Store Oracle results for report generation
            if result["execution_result"]:
                self.oracle_results_by_test.append(result["execution_result"].oracle_results)

            print()

        return results

    def _run_single_test(self, scenario: Dict) -> Dict[str, Any]:
        """运行单个测试场景"""
        scenario_id = scenario["id"]
        test_case = scenario["test_case"]

        print(f"[{scenario_id}] {scenario['name']}")
        print(f"  Description: {scenario['description']}")

        start_time = time.time()

        try:
            execution_result = self.pipeline.execute_test_case(
                test_case=test_case,
                contract=self.contract,
                adapter=self.adapter,
                profile=self.profile
            )

            elapsed = time.time() - start_time

            # Check result
            expected_status = scenario["expected_status"]
            actual_status = execution_result.status.value

            # Determine test outcome
            if actual_status == expected_status:
                status = "PASS"
                symbol = "[PASS]"
            else:
                status = "FAIL"
                symbol = "[FAIL]"

            print(f"  Status: {actual_status} (expected: {expected_status})")
            print(f"  Time: {elapsed:.3f}s")

            # Show Oracle results
            if execution_result.oracle_results:
                passed_oracles = sum(1 for r in execution_result.oracle_results if r.passed)
                total_oracles = len(execution_result.oracle_results)
                print(f"  Oracle: {passed_oracles}/{total_oracles} passed")

            print(f"  Result: {symbol} {status}")

            return {
                "id": scenario_id,
                "name": scenario["name"],
                "status": status,
                "expected_status": expected_status,
                "actual_status": actual_status,
                "elapsed_seconds": elapsed,
                "execution_result": execution_result,
            }

        except Exception as e:
            print(f"  [ERROR] Exception: {type(e).__name__}: {e}")
            return {
                "id": scenario_id,
                "name": scenario["name"],
                "status": "ERROR",
                "error": str(e),
                "execution_result": None,
            }

    def generate_reports(self) -> str:
        """生成测试报告"""
        print()
        print("=" * 70)
        print("Generating Test Reports...")
        print("=" * 70)
        print()

        # Flatten Oracle results for report
        all_oracle_results = []
        for test_oracle_list in self.oracle_results_by_test:
            all_oracle_results.extend(test_oracle_list)

        # Create reporter
        reporter = OracleReporter()

        # Generate report
        report = reporter.generate_report(all_oracle_results)

        # Create reports directory
        reports_dir = Path("reports/real_world")
        reports_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save reports
        json_path = reports_dir / f"test_report_{timestamp}.json"
        html_path = reports_dir / f"test_report_{timestamp}.html"
        txt_path = reports_dir / f"test_report_{timestamp}.txt"

        reporter.save_report(report, str(json_path), ReportFormat.JSON)
        reporter.save_report(report, str(html_path), ReportFormat.HTML)
        reporter.save_report(report, str(txt_path), ReportFormat.TEXT)

        print(f"Reports saved:")
        print(f"  JSON: {json_path}")
        print(f"  HTML: {html_path}")
        print(f"  Text: {txt_path}")

        # Print summary
        print()
        print("Test Summary:")
        print(f"  Total scenarios: {self.test_results['total']}")
        print(f"  Passed: {self.test_results['passed']}")
        print(f"  Failed: {self.test_results['failed']}")
        print(f"  Skipped: {self.test_results['skipped']}")
        print()
        print("Oracle Summary:")
        print(f"  Total checks: {report.total_oracles}")
        print(f"  Passed: {report.passed_count}")
        print(f"  Failed: {report.failed_count}")
        print(f"  Pass rate: {report.pass_rate * 100:.1f}%")
        print()

        # Try to open HTML report
        try:
            os.startfile(str(html_path.absolute()))
            print(f"[OK] HTML report opened in browser")
        except:
            print(f"  [INFO] Open manually: {html_path.absolute()}")

        return str(html_path.absolute())

    def run(self):
        """运行完整的测试流程"""
        self.start_time = time.time()

        try:
            # Setup
            self.setup()

            # Run tests
            print()
            self.test_results = self.run_test_scenarios()

            # Generate reports
            report_path = self.generate_reports()

            # Final summary
            total_time = time.time() - self.start_time

            print("=" * 70)
            print("TEST EXECUTION COMPLETE")
            print("=" * 70)
            print()
            print(f"Total time: {total_time:.2f}s")
            print(f"Report: {report_path}")
            print()

            # Return exit code
            if self.test_results['failed'] == 0:
                print("[OK] All tests executed successfully!")
                return 0
            else:
                print(f"[WARNING] {self.test_results['failed']} tests had unexpected results")
                return 1

        except Exception as e:
            print()
            print("=" * 70)
            print("TEST EXECUTION FAILED")
            print("=" * 70)
            print()
            print(f"Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return 1


# ================================================================
# Main Entry Point
# ================================================================

def main():
    """主函数"""
    config = TestConfig()
    runner = RealWorldTestRunner(config)

    return runner.run()


if __name__ == "__main__":
    sys.exit(main())
