"""
Concurrency Testing Agent

Agent for coordinating concurrent and security testing.
"""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
import threading
import queue
import time

from agent.runtime import AgentRuntime, AgentConfig
from concurrency.scenario_generator import (
    ConcurrentScenarioGenerator, ConcurrentScenario, OperationType
)
from concurrency.race_detector import RaceConditionDetector, RaceCondition, ExecutionTrace
from concurrency.security_tester import SecurityTester, SecurityTest, SecurityTestResult


@dataclass
class ConcurrencyTestResult:
    """
    Result of concurrency testing
    """
    scenario_id: str
    scenario_name: str
    success: bool
    execution_time: float
    operations_completed: int
    operations_total: int
    race_conditions: List[RaceCondition] = None
    security_results: List[SecurityTestResult] = None
    errors: List[str] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.race_conditions is None:
            self.race_conditions = []
        if self.security_results is None:
            self.security_results = []
        if self.errors is None:
            self.errors = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "success": self.success,
            "execution_time": self.execution_time,
            "operations_completed": self.operations_completed,
            "operations_total": self.operations_total,
            "race_conditions": [r.to_dict() for r in self.race_conditions],
            "security_results": [r.to_dict() for r in self.security_results],
            "errors": self.errors,
            "metadata": self.metadata,
        }


class ConcurrencyTestingAgent:
    """
    Concurrency Testing Agent

    Coordinates concurrent and security testing using:
    - Scenario generation
    - Race condition detection
    - Security vulnerability testing
    """

    def __init__(self, resources: List[str],
                 input_fields: List[str],
                 config: Optional[Dict] = None):
        """
        Initialize concurrency testing agent

        Args:
            resources: List of resource names to test
            input_fields: List of input field names for security testing
            config: Configuration options
        """
        self.resources = resources
        self.input_fields = input_fields
        self.config = config or {}

        # Initialize agent runtime
        agent_config = AgentConfig(
            agent_id="concurrency_test_agent",
            enable_monitoring=True,
            enable_memory=True
        )
        self.runtime = AgentRuntime(agent_config)

        # Initialize components
        self.scenario_generator = ConcurrentScenarioGenerator(
            resources, config
        )
        self.race_detector = RaceConditionDetector(config)
        self.security_tester = SecurityTester(config)

        # Test history
        self._test_history: List[ConcurrencyTestResult] = []

    def test_scenario(self, scenario: ConcurrentScenario,
                      execute_func: Optional[Callable] = None) -> ConcurrencyTestResult:
        """
        Test a concurrent scenario

        Args:
            scenario: Scenario to test
            execute_func: Function to execute operations (optional, for simulation)

        Returns:
            ConcurrencyTestResult
        """
        self.runtime.start()

        try:
            start_time = time.time()

            # Execute operations concurrently
            execution_results = []
            errors = []

            if execute_func:
                # Use provided execution function
                execution_results = self._execute_with_func(
                    scenario, execute_func
                )
            else:
                # Simulate execution
                execution_results = self._simulate_execution(scenario)

            # Detect race conditions
            races = self.race_detector.analyze_scenario(
                scenario, execution_results
            )

            # Run security tests
            security_results = self._run_security_tests(scenario)

            execution_time = time.time() - start_time

            # Check for errors in execution
            for result in execution_results:
                if not result.get("success", True):
                    errors.append(result.get("error", "Unknown error"))

            result = ConcurrencyTestResult(
                scenario_id=scenario.scenario_id,
                scenario_name=scenario.name,
                success=len(errors) == 0,
                execution_time=execution_time,
                operations_completed=len([r for r in execution_results if r.get("success", True)]),
                operations_total=len(scenario.operations),
                race_conditions=races,
                security_results=security_results,
                errors=errors,
                metadata={
                    "conflict_type": scenario.conflict_type.value if scenario.conflict_type else None,
                }
            )

            self._test_history.append(result)

            return result

        finally:
            self.runtime.stop()

    def _execute_with_func(self, scenario: ConcurrentScenario,
                            execute_func: Callable) -> List[Dict]:
        """Execute scenario using provided function"""
        results = []
        threads = []
        result_queue = queue.Queue()

        def worker(op):
            try:
                start = time.time()
                success, data = execute_func(op)
                end = time.time()

                result_queue.put({
                    "op_id": op.op_id,
                    "success": success,
                    "data": data,
                    "start_time": start,
                    "end_time": end,
                    "thread_id": threading.get_ident(),
                    "error": "" if success else "Execution failed",
                })
            except Exception as e:
                result_queue.put({
                    "op_id": op.op_id,
                    "success": False,
                    "data": None,
                    "start_time": time.time(),
                    "end_time": time.time(),
                    "thread_id": threading.get_ident(),
                    "error": str(e),
                })

        # Start threads
        for op in scenario.operations:
            thread = threading.Thread(target=worker, args=(op,))
            threads.append(thread)
            thread.start()

            # Add small delay for realistic concurrency
            if op.delay_ms > 0:
                time.sleep(op.delay_ms / 1000.0)

        # Wait for completion
        for thread in threads:
            thread.join(timeout=30.0)  # 30 second timeout

        # Collect results
        while not result_queue.empty():
            results.append(result_queue.get())

        return results

    def _simulate_execution(self, scenario: ConcurrentScenario) -> List[Dict]:
        """Simulate scenario execution (for testing without real DB)"""
        results = []
        current_time = time.time()

        for op in scenario.operations:
            # Simulate execution time
            duration = 0.01 + (op.delay_ms / 1000.0)

            results.append({
                "op_id": op.op_id,
                "success": True,
                "data": {"simulated": True},
                "start_time": current_time,
                "end_time": current_time + duration,
                "thread_id": hash(op.op_id) % 10,
                "error": "",
            })

            current_time += duration

        return results

    def _run_security_tests(self, scenario: ConcurrentScenario) -> List[SecurityTestResult]:
        """Run security tests on scenario"""
        results = []

        # Generate security tests for the scenario
        security_tests = self.security_tester.generate_all_tests(
            operation=scenario.operations[0].operation_type.value if scenario.operations else "search",
            input_fields=self.input_fields,
            resources=self.resources
        )

        # Run a subset of tests (to avoid too many tests)
        for test in security_tests[:10]:  # Limit to 10 tests per scenario
            # Simulate response
            response = {"status": "success", "data": {}}

            # Analyze for vulnerabilities
            result = self.security_tester.analyze_response_for_vulnerabilities(
                test, response
            )
            results.append(result)

        return results

    def test_all_scenarios(self,
                           execute_func: Optional[Callable] = None) -> List[ConcurrencyTestResult]:
        """
        Test all generated scenarios

        Args:
            execute_func: Function to execute operations (optional)

        Returns:
            List of test results
        """
        scenarios = self.scenario_generator.generate_all_scenarios()
        results = []

        for scenario in scenarios:
            result = self.test_scenario(scenario, execute_func)
            results.append(result)

        return results

    def get_test_summary(self) -> Dict:
        """
        Get summary of all tests

        Returns:
            Test summary statistics
        """
        if not self._test_history:
            return {"total_tests": 0}

        total_tests = len(self._test_history)
        successful_tests = len([t for t in self._test_history if t.success])
        failed_tests = total_tests - successful_tests

        total_races = sum(len(t.race_conditions) for t in self._test_history)
        total_vulnerabilities = sum(
            len([r for r in t.security_results if r.vulnerable])
            for t in self._test_history
        )

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        for test in self._test_history:
            for race in test.race_conditions:
                severity_counts[race.severity] += 1
            for sec_result in test.security_results:
                if sec_result.vulnerable:
                    severity_counts[sec_result.severity] += 1

        return {
            "total_tests": total_tests,
            "successful": successful_tests,
            "failed": failed_tests,
            "race_conditions_found": total_races,
            "vulnerabilities_found": total_vulnerabilities,
            "by_severity": severity_counts,
            "race_detector_stats": self.race_detector.get_stats(),
            "security_tester_stats": self.security_tester.get_stats(),
        }

    def get_detected_races(self) -> List[RaceCondition]:
        """Get all detected race conditions"""
        return self.race_detector.get_detected_races()

    def get_vulnerabilities(self) -> List[SecurityTestResult]:
        """Get all detected vulnerabilities"""
        vulnerabilities = []

        for test in self._test_history:
            for result in test.security_results:
                if result.vulnerable:
                    vulnerabilities.append(result)

        return vulnerabilities

    def clear_history(self) -> None:
        """Clear test history"""
        self._test_history.clear()
        self.race_detector.clear()


__all__ = [
    "ConcurrencyTestResult",
    "ConcurrencyTestingAgent",
]
