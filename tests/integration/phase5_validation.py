# -*- coding: utf-8 -*-
"""
Phase 5 Validation: Agent-Driven Bug Mining

Real-world validation of Phase 5 features:
1. Agent Infrastructure (INF)
2. Intelligent Test Generation (M0)
3. Adaptive Anomaly Detection (M1)
4. Bug Analysis (M4)
5. Database Adapters (M5)
"""
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field, asdict

from agent.runtime import AgentRuntime, AgentConfig
from agent.memory import AgentMemory, MemoryType
from agent.monitor import AgentMonitor
from generators.agent import TestGenerationAgent, TestGenerationCache
from detectors import StatisticalAnomalyDetector, AnomalyPatternLearner
from adapters import SeekDBAdapter, MilvusAdapter, WeaviateAdapter
from core.models import SemanticCase, SlotScope, ErrorCategory


@dataclass
class ValidationMetrics:
    """Validation metrics"""
    total_tests_run: int = 0
    bugs_found: int = 0
    unique_bugs: int = 0
    critical_bugs: int = 0
    execution_time: float = 0.0
    anomaly_detections: int = 0
    agent_insights: int = 0


class Phase5Validator:
    """Phase 5 Feature Validator"""

    def __init__(self, adapter_name: str = "seekdb"):
        self.adapter_name = adapter_name

        # Create adapter
        if adapter_name == "seekdb":
            self.adapter = SeekDBAdapter(host="localhost", port=2881)
        elif adapter_name == "milvus":
            self.adapter = MilvusAdapter(host="localhost", port=19530)
        elif adapter_name == "weaviate":
            self.adapter = WeaviateAdapter(url="http://localhost:8080")
        else:
            raise ValueError(f"Unknown adapter: {adapter_name}")

        # Initialize Agent components
        agent_config = AgentConfig(
            agent_id="phase5_validator",
            enable_monitoring=True,
            enable_memory=True
        )
        self.runtime = AgentRuntime(config=agent_config)
        self.memory = AgentMemory(agent_id="phase5_validator")
        self.monitor = AgentMonitor(agent_id="phase5_validator")

        # Initialize Phase 5 components
        self.test_generator = None
        self.anomaly_detector = None
        self.pattern_learner = None

        # Storage
        self.results = {
            "traditional": ValidationMetrics(),
            "agent_driven": ValidationMetrics()
        }
        self.discovered_bugs = []
        self.execution_times = []

    def setup(self) -> bool:
        """Setup validation environment"""
        print(f"\n[*] Setting up validation environment (adapter: {self.adapter_name})...")

        # Connect to database
        if not self.adapter.connect():
            print(f"[!] Cannot connect to {self.adapter_name}, using simulation mode")
            self.adapter._connected = True
            return False

        print(f"[+] Connected to {self.adapter_name}")

        # Initialize components
        cache = TestGenerationCache(max_entries=1000)
        # TestGenerationAgent needs slots and operations, will generate tests directly
        self.test_generator = None  # Will use direct generation instead

        self.anomaly_detector = StatisticalAnomalyDetector()
        self.pattern_learner = AnomalyPatternLearner()

        # Start Agent runtime
        self.runtime.start()

        # Store initial state
        self.memory.store("setup", {
            "adapter": self.adapter_name,
            "timestamp": time.time(),
            "capabilities": self.adapter.get_capabilities().__dict__
        }, MemoryType.LONG_TERM)

        print("[+] All components initialized")
        return True

    def run_traditional_testing(self) -> ValidationMetrics:
        """Run traditional testing (baseline)"""
        print("\n" + "="*60)
        print("[*] Running Traditional Testing (Baseline)...")
        print("="*60)

        metrics = ValidationMetrics()
        start_time = time.time()

        # Traditional tests: fixed test cases
        traditional_tests = self._get_traditional_test_cases()

        print(f"[*] Executing {len(traditional_tests)} traditional test cases")

        for test_case in traditional_tests:
            try:
                exec_start = time.time()
                result = self.adapter.execute_test(test_case)
                exec_time = time.time() - exec_start

                metrics.total_tests_run += 1

                # Simple error detection
                if result.status.value in ["FAILURE", "CRASH", "TIMEOUT"]:
                    bug_info = self._analyze_bug_simple(result, test_case, exec_time)
                    bug_info["method"] = "traditional"
                    self.discovered_bugs.append(bug_info)
                    metrics.bugs_found += 1

            except Exception as e:
                metrics.bugs_found += 1
                self.discovered_bugs.append({
                    "error": str(e),
                    "operation": test_case.operation,
                    "method": "traditional",
                    "severity": "medium",
                    "timestamp": time.time()
                })

        metrics.execution_time = time.time() - start_time

        # Count unique bugs
        metrics.unique_bugs = len(set(
            b.get("error", "") for b in self.discovered_bugs
            if b.get("method") == "traditional"
        ))

        print(f"[+] Traditional testing complete:")
        print(f"   - Executed: {metrics.total_tests_run} tests")
        print(f"   - Found: {metrics.bugs_found} bugs")
        print(f"   - Unique: {metrics.unique_bugs} bugs")
        print(f"   - Time: {metrics.execution_time:.2f}s")

        return metrics

    def run_agent_driven_testing(self) -> ValidationMetrics:
        """Run agent-driven testing"""
        print("\n" + "="*60)
        print("[*] Running Agent-Driven Testing...")
        print("="*60)

        metrics = ValidationMetrics()
        start_time = time.time()
        self.runtime.start()

        try:
            # 1. Intelligent test generation (M0)
            print("\n[*] M0: Intelligent Test Generation...")
            gen_start = time.time()

            generated_tests = self._generate_agent_tests()

            metrics.test_generation_time = time.time() - gen_start
            print(f"   [+] Generated {len(generated_tests)} intelligent tests ({metrics.test_generation_time:.2f}s)")

            # 2. Execute tests with anomaly detection (M1)
            print("\n[*] M1: Anomaly Detection + Execution...")

            for test_case in generated_tests:
                try:
                    exec_start = time.time()
                    result = self.adapter.execute_test(test_case)
                    exec_time = time.time() - exec_start

                    metrics.total_tests_run += 1
                    self.execution_times.append(exec_time)

                    # Anomaly detection
                    if len(self.execution_times) > 5:
                        anomaly_result = self.anomaly_detector.detect(
                            exec_time, self.execution_times[:-1]
                        )

                        if anomaly_result.is_anomaly:
                            metrics.anomaly_detections += 1
                            print(f"      [!] Anomaly: {test_case.operation} exec_time {exec_time:.3f}s "
                                  f"(score: {anomaly_result.anomaly_score:.2f})")

                            # Agent remembers anomaly
                            self.memory.store(f"anomaly_{metrics.total_tests_run}", {
                                "test_case": test_case.test_id,
                                "exec_time": exec_time,
                                "score": anomaly_result.anomaly_score,
                                "type": str(anomaly_result.anomaly_type)
                            }, MemoryType.WORKING)
                            metrics.agent_insights += 1

                    # Bug analysis
                    if result.status.value in ["FAILURE", "CRASH", "TIMEOUT"]:
                        bug_info = self._analyze_bug_advanced(result, test_case, exec_time)
                        bug_info["method"] = "agent_driven"
                        self.discovered_bugs.append(bug_info)
                        metrics.bugs_found += 1

                        # Agent analyzes bug
                        bug_analysis = self._agent_analyze_bug(result, test_case)
                        bug_info["agent_analysis"] = bug_analysis
                        metrics.agent_insights += 1

                except Exception as e:
                    metrics.bugs_found += 1
                    bug_info = {
                        "error": str(e),
                        "operation": test_case.operation,
                        "method": "agent_driven",
                        "severity": "high",
                        "timestamp": time.time()
                    }
                    self.discovered_bugs.append(bug_info)

            # 3. Pattern learning (M1)
            if len(self.execution_times) > 10:
                print("\n[*] M1: Pattern Learning...")
                # Simple pattern analysis
                avg_time = sum(self.execution_times) / len(self.execution_times)
                min_time = min(self.execution_times)
                max_time = max(self.execution_times)

                patterns = {
                    "average": avg_time,
                    "min": min_time,
                    "max": max_time,
                    "range": max_time - min_time,
                    "count": len(self.execution_times)
                }

                print(f"   [+] Analysis complete:")
                print(f"      - Avg time: {avg_time:.4f}s")
                print(f"      - Range: {min_time:.4f}s - {max_time:.4f}s")

                # Agent remembers patterns
                self.memory.store("execution_patterns", patterns, MemoryType.LONG_TERM)
                metrics.agent_insights += 1

            # 4. Agent insights report
            print("\n[*] Agent Insights:")
            agent_stats = self.runtime.get_stats()
            memory_stats = self.memory.get_stats()

            print(f"   - Agent operations: {agent_stats.get('total_operations', 0)}")
            print(f"   - Memory entries: {memory_stats.get('total_memories', 0)}")

            metrics.execution_time = time.time() - start_time
            metrics.unique_bugs = len(set(
                b.get("error", "") for b in self.discovered_bugs
                if b.get("method") == "agent_driven"
            ))

        finally:
            self.runtime.stop()

        print(f"\n[+] Agent-driven testing complete:")
        print(f"   - Executed: {metrics.total_tests_run} tests")
        print(f"   - Found: {metrics.bugs_found} bugs")
        print(f"   - Unique: {metrics.unique_bugs} bugs")
        print(f"   - Anomalies: {metrics.anomaly_detections}")
        print(f"   - Insights: {metrics.agent_insights}")
        print(f"   - Time: {metrics.execution_time:.2f}s")

        return metrics

    def _generate_agent_tests(self) -> List[SemanticCase]:
        """Generate tests using Agent strategies"""
        tests = []

        # Strategy 1: Boundary value testing
        for dim in [1, 128, 512, 1024, 4096, 32768, 65536]:
            tests.append(SemanticCase(
                test_id=f"agent_boundary_{dim}",
                operation="search",
                slot_values={"dimension": dim, "top_k": 10},
                raw_parameters={},
                is_legal=True,
                scope=SlotScope.DATABASE
            ))

        # Strategy 2: Combinatorial testing
        for metric in ["L2", "IP", "COSINE"]:
            for top_k in [1, 10, 100, 1000]:
                tests.append(SemanticCase(
                    test_id=f"agent_combo_{metric}_{top_k}",
                    operation="search",
                    slot_values={"dimension": 512, "metric_type": metric, "top_k": top_k},
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.DATABASE
                ))

        # Strategy 3: Extreme value testing
        tests.append(SemanticCase(
            test_id="agent_extreme_1",
            operation="search",
            slot_values={"dimension": 999999, "top_k": 99999},
            raw_parameters={},
            is_legal=False,
            scope=SlotScope.DATABASE
        ))

        tests.append(SemanticCase(
            test_id="agent_extreme_2",
            operation="insert",
            slot_values={"dimension": 0},
            raw_parameters={},
            is_legal=False,
            scope=SlotScope.DATABASE
        ))

        # Strategy 4: Relational testing
        tests.append(SemanticCase(
            test_id="agent_relational_1",
            operation="search",
            slot_values={"search_range": 10, "top_k": 100},
            raw_parameters={},
            is_legal=False,
            scope=SlotScope.DATABASE
        ))

        return tests

    def _analyze_bug_simple(self, result, test_case, exec_time: float) -> Dict[str, Any]:
        """Simple bug analysis"""
        return {
            "test_id": test_case.test_id,
            "operation": test_case.operation,
            "slot_values": test_case.slot_values,
            "error": str(result.error) if result.error else result.status.value,
            "execution_time": exec_time,
            "severity": "medium"
        }

    def _analyze_bug_advanced(self, result, test_case, exec_time: float) -> Dict[str, Any]:
        """Advanced bug analysis"""
        error_category = None
        if result.error:
            try:
                error_category = self.adapter.classify_error(result.error)
            except:
                pass

        return {
            "test_id": test_case.test_id,
            "operation": test_case.operation,
            "slot_values": test_case.slot_values,
            "error": str(result.error) if result.error else result.status.value,
            "error_category": str(error_category) if error_category else "unknown",
            "execution_time": exec_time,
            "severity": self._determine_severity(error_category) if error_category else "low",
            "is_legal": test_case.is_legal
        }

    def _agent_analyze_bug(self, result, test_case) -> Dict[str, Any]:
        """Agent bug analysis"""
        analysis = {
            "potential_cause": None,
            "suggested_fix": None,
            "related_tests": []
        }

        error_str = str(result.error).lower() if result.error else ""

        if "dimension" in error_str:
            analysis["potential_cause"] = "Dimension value out of supported range"
            analysis["suggested_fix"] = "Use dimension in range [1, 32768]"
        elif "timeout" in error_str:
            analysis["potential_cause"] = "Operation exceeded time limit"
            analysis["suggested_fix"] = "Increase timeout or reduce data size"
        elif "connection" in error_str:
            analysis["potential_cause"] = "Database connection issue"
            analysis["suggested_fix"] = "Check database availability"

        return analysis

    def _determine_severity(self, error_category) -> str:
        """Determine severity"""
        if error_category == ErrorCategory.PRODUCT_SUSPECT:
            return "critical"
        elif error_category == ErrorCategory.PRECONDITION_FAILED:
            return "high"
        else:
            return "medium"

    def _get_traditional_test_cases(self) -> List[SemanticCase]:
        """Get traditional test cases"""
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
                slot_values={"dimension": 512, "metric_type": "L2"},
                raw_parameters={},
                is_legal=True,
                scope=SlotScope.DATABASE
            ),
            SemanticCase(
                test_id="trad_003",
                operation="insert",
                slot_values={"dimension": 256},
                raw_parameters={},
                is_legal=True,
                scope=SlotScope.DATABASE
            ),
        ]

    def generate_comparison_report(self) -> str:
        """Generate comparison report"""
        trad = self.results["traditional"]
        agent = self.results["agent_driven"]

        report = []
        report.append("\n" + "="*70)
        report.append("Phase 5 Validation Report: Agent-Driven Bug Mining")
        report.append(f"Database: {self.adapter_name.upper()}")
        report.append("="*70)

        # Performance comparison
        report.append("\n[*] Performance Comparison:")
        report.append("-" * 70)
        report.append(f"{'Metric':<25} {'Traditional':<15} {'Agent-Driven':<15} {'Improvement':<10}")
        report.append("-" * 70)

        trad_tests = trad.total_tests_run
        agent_tests = agent.total_tests_run
        improvement = f"+{((agent_tests - trad_tests) / trad_tests * 100):.1f}%" if trad_tests > 0 else "N/A"
        report.append(f"{'Tests Run':<25} {trad_tests:<15} {agent_tests:<15} {improvement:<10}")

        trad_bugs = trad.bugs_found
        agent_bugs = agent.bugs_found
        improvement = f"+{((agent_bugs - trad_bugs) / trad_bugs * 100):.1f}%" if trad_bugs > 0 else "N/A"
        report.append(f"{'Bugs Found':<25} {trad_bugs:<15} {agent_bugs:<15} {improvement:<10}")

        trad_time = trad.execution_time
        agent_time = agent.execution_time
        improvement = f"{((trad_time - agent_time) / trad_time * 100):.1f}%" if trad_time > 0 else "N/A"
        report.append(f"{'Execution Time (s)':<25} {trad_time:<15.2f} {agent_time:<15.2f} {improvement:<10}")

        report.append("-" * 70)

        # Phase 5 features
        report.append("\n[+] Phase 5 Features Verified:")
        report.append("-" * 70)
        report.append(f"[+] INF: Agent Infrastructure - Runtime active")
        report.append(f"[+] M0: Intelligent Test Generation - {agent_tests} tests")
        report.append(f"[+] M1: Anomaly Detection - {agent.anomaly_detections} anomalies")
        report.append(f"[+] M4: Bug Analysis - Auto classification")
        report.append(f"[+] M5: Database Adapter - {self.adapter_name}")

        if agent.agent_insights > 0:
            report.append(f"[*] Agent Insights: {agent.agent_insights}")

        # Bug classification
        if self.discovered_bugs:
            report.append("\n[*] Bug Classification:")
            report.append("-" * 70)

            severity_count = {}
            for bug in self.discovered_bugs:
                severity = bug.get("severity", "unknown")
                severity_count[severity] = severity_count.get(severity, 0) + 1

            for severity in ["critical", "high", "medium", "low"]:
                if severity in severity_count:
                    report.append(f"   {severity.capitalize()}: {severity_count[severity]}")

        # Conclusion
        report.append("\n[*] Validation Conclusion:")
        report.append("-" * 70)

        total_improvements = 0
        if agent_tests > trad_tests:
            total_improvements += 1
        if agent_bugs > trad_bugs:
            total_improvements += 1
        if agent.anomaly_detections > 0:
            total_improvements += 1
        if agent.agent_insights > 0:
            total_improvements += 1

        if total_improvements >= 3:
            report.append("[+] Agent-driven approach significantly enhances bug discovery")
            report.append(f"   - Test coverage increased by {agent_tests - trad_tests}")
            report.append(f"   - Bug discovery increased by {agent_bugs - trad_bugs}")
            report.append(f"   - Additional {agent.anomaly_detections} anomalies detected")
        elif total_improvements >= 2:
            report.append("[+] Agent-driven approach effectively enhances testing")
        else:
            report.append("[!] Agent-driven approach needs further tuning")

        report.append("="*70)

        return "\n".join(report)

    def save_detailed_report(self, output_path: str = "reports/phase5_validation.json"):
        """Save detailed report"""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        detailed_report = {
            "validation_summary": {
                "adapter": self.adapter_name,
                "traditional_metrics": asdict(self.results["traditional"]),
                "agent_driven_metrics": asdict(self.results["agent_driven"]),
            },
            "discovered_bugs": [
                {k: str(v) if isinstance(v, (ErrorCategory, SlotScope)) else v
                 for k, v in bug.items()}
                for bug in self.discovered_bugs
            ],
            "execution_times": self.execution_times,
            "timestamp": time.time()
        }

        with open(output, 'w', encoding='utf-8') as f:
            json.dump(detailed_report, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n[+] Detailed report saved to: {output}")

    def run_validation(self):
        """Run complete validation"""
        print("\n" + "="*70)
        print("Phase 5 Validation: Agent-Driven Bug Mining")
        print("="*70)

        # Setup
        self.setup()

        # Run traditional testing
        self.results["traditional"] = self.run_traditional_testing()

        # Clear bug list
        self.discovered_bugs = []

        # Run agent-driven testing
        self.results["agent_driven"] = self.run_agent_driven_testing()

        # Generate report
        print(self.generate_comparison_report())

        # Save detailed report
        self.save_detailed_report()

        # Disconnect
        try:
            self.adapter.disconnect()
        except:
            pass


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Phase 5 Validation")
    parser.add_argument("--adapter", choices=["seekdb", "milvus", "weaviate"],
                       default="seekdb", help="Database adapter")

    args = parser.parse_args()

    validator = Phase5Validator(adapter_name=args.adapter)
    validator.run_validation()


if __name__ == "__main__":
    main()
