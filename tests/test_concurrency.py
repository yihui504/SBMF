"""
Tests for M2: Concurrency & Security Testing
"""
import pytest
import tempfile
import time
from pathlib import Path

from concurrency.scenario_generator import (
    ConcurrentScenarioGenerator, ConcurrentScenario, ConcurrentOperation,
    OperationType, ConflictType
)
from concurrency.race_detector import (
    RaceConditionDetector, RaceCondition, RaceType, ExecutionTrace
)
from concurrency.security_tester import (
    SecurityTester, SecurityTest, SecurityTestResult, VulnerabilityType
)
from concurrency.agent import ConcurrencyTestingAgent, ConcurrencyTestResult


# ================================================================
# Scenario Generator Tests
# ================================================================

class TestConcurrentScenarioGenerator:
    """Test concurrent scenario generator"""

    def test_initialization(self):
        """Test generator initialization"""
        resources = ["collection1", "collection2"]
        generator = ConcurrentScenarioGenerator(resources)

        stats = generator.get_stats()
        assert stats["resources"] == 2

    def test_generate_write_write_conflict(self):
        """Test write-write conflict scenario generation"""
        resources = ["test_collection"]
        generator = ConcurrentScenarioGenerator(resources)

        scenarios = generator.generate_write_write_conflict(count=3)

        assert len(scenarios) == 3
        assert all(s.conflict_type == ConflictType.WRITE_WRITE for s in scenarios)

    def test_generate_read_write_conflict(self):
        """Test read-write conflict scenario generation"""
        resources = ["test_collection"]
        generator = ConcurrentScenarioGenerator(resources)

        scenarios = generator.generate_read_write_conflict(count=3)

        assert len(scenarios) == 3
        assert all(s.conflict_type == ConflictType.READ_WRITE for s in scenarios)

    def test_generate_delete_during_read(self):
        """Test delete-during-read scenario generation"""
        resources = ["test_collection"]
        generator = ConcurrentScenarioGenerator(resources)

        scenarios = generator.generate_delete_during_read(count=2)

        assert len(scenarios) == 2
        assert all(s.conflict_type == ConflictType.DELETE_READ for s in scenarios)

    def test_generate_resource_exhaustion(self):
        """Test resource exhaustion scenario generation"""
        resources = ["test_collection"]
        config = {"max_concurrent": 5}
        generator = ConcurrentScenarioGenerator(resources, config)

        scenarios = generator.generate_resource_exhaustion(count=2)

        assert len(scenarios) == 2
        # Should have more operations than max_concurrent
        assert all(len(s.operations) > 5 for s in scenarios)

    def test_generate_all_scenarios(self):
        """Test generating all scenario types"""
        resources = ["collection1", "collection2"]
        generator = ConcurrentScenarioGenerator(resources)

        scenarios = generator.generate_all_scenarios()

        assert len(scenarios) > 0

        # Check different conflict types are represented
        conflict_types = {s.conflict_type for s in scenarios}
        assert ConflictType.WRITE_WRITE in conflict_types
        assert ConflictType.READ_WRITE in conflict_types


# ================================================================
# Race Condition Detector Tests
# ================================================================

class TestRaceConditionDetector:
    """Test race condition detector"""

    def test_initialization(self):
        """Test detector initialization"""
        detector = RaceConditionDetector()

        stats = detector.get_stats()
        assert stats["total_races_detected"] == 0

    def test_detect_write_write_races(self):
        """Test write-write race detection"""
        detector = RaceConditionDetector()

        # Create overlapping write traces
        traces = [
            ExecutionTrace(
                op_id="write1", operation_type=OperationType.INSERT,
                resource_id="collection1", start_time=0.0, end_time=2.0,
                thread_id=1, success=True, access_pattern="write"
            ),
            ExecutionTrace(
                op_id="write2", operation_type=OperationType.INSERT,
                resource_id="collection1", start_time=1.0, end_time=3.0,
                thread_id=2, success=True, access_pattern="write"
            ),
        ]

        for trace in traces:
            detector.record_execution(trace)

        # Analyze - create scenario with matching operations
        scenario = ConcurrentScenario(
            scenario_id="test",
            name="Test",
            description="Test",
            operations=[
                ConcurrentOperation(
                    op_id="write1", operation_type=OperationType.INSERT,
                    resource_id="collection1"
                ),
                ConcurrentOperation(
                    op_id="write2", operation_type=OperationType.INSERT,
                    resource_id="collection1"
                ),
            ],
        )

        results = [
            {"start_time": t.start_time, "end_time": t.end_time,
             "thread_id": t.thread_id, "success": t.success}
            for t in traces
        ]

        races = detector.analyze_scenario(scenario, results)

        assert len(races) > 0
        assert races[0].race_type == RaceType.DATA_RACE

    def test_detect_read_write_races(self):
        """Test read-write race detection"""
        detector = RaceConditionDetector()

        traces = [
            ExecutionTrace(
                op_id="read1", operation_type=OperationType.SEARCH,
                resource_id="collection1", start_time=0.0, end_time=2.0,
                thread_id=1, success=True, access_pattern="read"
            ),
            ExecutionTrace(
                op_id="write1", operation_type=OperationType.INSERT,
                resource_id="collection1", start_time=1.0, end_time=2.5,
                thread_id=2, success=True, access_pattern="write"
            ),
        ]

        for trace in traces:
            detector.record_execution(trace)

        scenario = ConcurrentScenario(
            scenario_id="test", name="Test", description="Test",
            operations=[
                ConcurrentOperation(
                    op_id="read1", operation_type=OperationType.SEARCH,
                    resource_id="collection1"
                ),
                ConcurrentOperation(
                    op_id="write1", operation_type=OperationType.INSERT,
                    resource_id="collection1"
                ),
            ],
        )

        results = [
            {"start_time": t.start_time, "end_time": t.end_time,
             "thread_id": t.thread_id, "success": t.success}
            for t in traces
        ]

        races = detector.analyze_scenario(scenario, results)

        # Should detect read-write race
        assert len(races) > 0

    def test_detect_potential_deadlocks(self):
        """Test potential deadlock detection"""
        detector = RaceConditionDetector()

        # Create a very slow operation (potential deadlock)
        traces = [
            ExecutionTrace(
                op_id="slow1", operation_type=OperationType.INSERT,
                resource_id="collection1", start_time=time.time() - 40.0,
                end_time=time.time(), thread_id=1, success=True, access_pattern="write"
            ),
        ]

        for trace in traces:
            detector.record_execution(trace)

        scenario = ConcurrentScenario(
            scenario_id="test", name="Test", description="Test",
            operations=[
                ConcurrentOperation(
                    op_id="slow1", operation_type=OperationType.INSERT,
                    resource_id="collection1"
                ),
            ],
        )

        results = [
            {"start_time": t.start_time, "end_time": t.end_time,
             "thread_id": t.thread_id, "success": t.success}
            for t in traces
        ]

        races = detector.analyze_scenario(scenario, results)

        # Should detect potential deadlock due to long duration
        deadlock_races = [r for r in races if r.race_type in [RaceType.DEADLOCK, RaceType.LIVELock]]
        assert len(deadlock_races) > 0

    def test_get_races_by_severity(self):
        """Test filtering races by severity"""
        detector = RaceConditionDetector()

        # Create a race (through scenario analysis)
        traces = [
            ExecutionTrace(
                op_id="write1", operation_type=OperationType.INSERT,
                resource_id="collection1", start_time=0.0, end_time=2.0,
                thread_id=1, success=True, access_pattern="write"
            ),
            ExecutionTrace(
                op_id="write2", operation_type=OperationType.INSERT,
                resource_id="collection1", start_time=1.0, end_time=3.0,
                thread_id=2, success=True, access_pattern="write"
            ),
        ]

        for trace in traces:
            detector.record_execution(trace)

        scenario = ConcurrentScenario(
            scenario_id="test", name="Test", description="Test",
            operations=[
                ConcurrentOperation(
                    op_id="write1", operation_type=OperationType.INSERT,
                    resource_id="collection1"
                ),
                ConcurrentOperation(
                    op_id="write2", operation_type=OperationType.INSERT,
                    resource_id="collection1"
                ),
            ],
        )

        results = [
            {"start_time": t.start_time, "end_time": t.end_time,
             "thread_id": t.thread_id, "success": t.success}
            for t in traces
        ]

        detector.analyze_scenario(scenario, results)

        # Get races by severity
        medium_races = detector.get_races_by_severity("medium")
        assert len(medium_races) > 0


# ================================================================
# Security Tester Tests
# ================================================================

class TestSecurityTester:
    """Test security tester"""

    def test_initialization(self):
        """Test tester initialization"""
        tester = SecurityTester()

        stats = tester.get_stats()
        assert stats["total_tests_generated"] == 0

    def test_generate_injection_tests(self):
        """Test injection test generation"""
        tester = SecurityTester()

        tests = tester.generate_injection_tests("insert", ["dimension", "collection"])

        assert len(tests) > 0

        # Check for SQL injection tests
        sql_tests = [t for t in tests if t.vulnerability_type == VulnerabilityType.SQL_INJECTION]
        assert len(sql_tests) > 0

    def test_generate_input_validation_tests(self):
        """Test input validation test generation"""
        tester = SecurityTester()

        tests = tester.generate_input_validation_tests("search", ["dimension", "top_k"])

        assert len(tests) > 0

        # Check for overflow tests
        overflow_tests = [t for t in tests if "overflow" in t.name.lower()]
        assert len(overflow_tests) > 0

    def test_generate_dos_tests(self):
        """Test DoS test generation"""
        tester = SecurityTester()

        tests = tester.generate_dos_tests("search", ["top_k", "dimension"])

        assert len(tests) > 0

        # Check for DoS tests
        dos_tests = [t for t in tests if t.vulnerability_type == VulnerabilityType.DENIAL_OF_SERVICE]
        assert len(dos_tests) > 0

    def test_generate_authorization_tests(self):
        """Test authorization test generation"""
        tester = SecurityTester()

        tests = tester.generate_authorization_tests("delete", ["collection1", "collection2"])

        assert len(tests) > 0

        # Check for auth bypass tests
        auth_tests = [t for t in tests if t.vulnerability_type == VulnerabilityType.AUTHORIZATION_BYPASS]
        assert len(auth_tests) > 0

    def test_analyze_response_for_vulnerabilities(self):
        """Test response analysis"""
        tester = SecurityTester()

        test = SecurityTest(
            test_id="test1",
            name="SQL Injection Test",
            vulnerability_type=VulnerabilityType.SQL_INJECTION,
            description="Test SQL injection",
            input_data={"dimension": "' OR '1'='1"},
            expected_behavior="blocked",
            severity="critical"
        )

        # Test with blocked response
        response_blocked = {"status": "error", "error": "Invalid input"}
        result = tester.analyze_response_for_vulnerabilities(test, response_blocked)

        assert not result.vulnerable
        assert "blocked" in result.actual_behavior.lower()

        # Test with allowed response (should be vulnerable)
        response_allowed = {"status": "success", "data": {}}
        result = tester.analyze_response_for_vulnerabilities(test, response_allowed)

        assert result.vulnerable
        assert result.severity == "critical"


# ================================================================
# Concurrency Testing Agent Tests
# ================================================================

class TestConcurrencyTestingAgent:
    """Test concurrency testing agent"""

    def test_initialization(self):
        """Test agent initialization"""
        resources = ["collection1"]
        input_fields = ["dimension", "top_k"]

        agent = ConcurrencyTestingAgent(resources, input_fields)

        assert agent.runtime is not None
        assert agent.scenario_generator is not None

    def test_test_scenario_simulation(self):
        """Test scenario execution with simulation"""
        resources = ["collection1"]
        input_fields = ["dimension", "top_k"]

        agent = ConcurrencyTestingAgent(resources, input_fields)

        # Create a scenario
        scenario = ConcurrentScenario(
            scenario_id="test_scenario",
            name="Test Scenario",
            description="Test scenario",
            operations=[
                ConcurrentOperation(
                    op_id="op1", operation_type=OperationType.INSERT,
                    resource_id="collection1", parameters={}
                ),
                ConcurrentOperation(
                    op_id="op2", operation_type=OperationType.SEARCH,
                    resource_id="collection1", parameters={}
                ),
            ],
            conflict_type=ConflictType.READ_WRITE
        )

        result = agent.test_scenario(scenario, execute_func=None)

        assert result is not None
        assert result.scenario_id == "test_scenario"
        assert result.operations_total == 2

    def test_test_all_scenarios(self):
        """Test running all scenarios"""
        resources = ["collection1"]
        input_fields = ["dimension", "top_k"]

        agent = ConcurrencyTestingAgent(resources, input_fields)

        results = agent.test_all_scenarios()

        assert len(results) > 0

    def test_get_test_summary(self):
        """Test getting test summary"""
        resources = ["collection1"]
        input_fields = ["dimension", "top_k"]

        agent = ConcurrencyTestingAgent(resources, input_fields)

        # Run some tests
        agent.test_all_scenarios()

        summary = agent.get_test_summary()

        assert summary["total_tests"] > 0
        assert "race_conditions_found" in summary
        assert "vulnerabilities_found" in summary

    def test_get_detected_races(self):
        """Test getting detected races"""
        resources = ["collection1"]
        input_fields = ["dimension"]

        agent = ConcurrencyTestingAgent(resources, input_fields)

        # Run tests
        agent.test_all_scenarios()

        races = agent.get_detected_races()

        # Returns list (may be empty)
        assert isinstance(races, list)

    def test_get_vulnerabilities(self):
        """Test getting vulnerabilities"""
        resources = ["collection1"]
        input_fields = ["dimension", "collection"]

        agent = ConcurrencyTestingAgent(resources, input_fields)

        # Run tests
        agent.test_all_scenarios()

        vulnerabilities = agent.get_vulnerabilities()

        # Returns list
        assert isinstance(vulnerabilities, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
