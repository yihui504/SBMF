"""
Tests for Oracle Integration with ExecutionPipeline.

Tests that Oracle checkers are properly integrated into the execution pipeline.
"""

import pytest
from typing import Optional, List
from core.execution_pipeline import ExecutionPipeline
from core.models import (
    SemanticCase, ExecutionStatus, ExecutionResult,
    Contract, CoreSlot, Slot, SlotScope, SlotType
)
from oracle import (
    OracleChecker,
    OracleDefinition,
    OracleResult,
    OracleCategory,
    Severity,
    TriggerCondition,
    ValidationLogic,
    TestCase,
    ExecutionResult as OracleExecutionResult,
    RangeConstraintOracle,
    EnumConstraintOracle,
    StatusValidationOracle,
)
from oracle.ast_nodes import literal


# ================================================================
# Mock Components
# ================================================================

class MockAdapter:
    """Mock adapter for testing

    Note: Oracle checkers expect status as string value (e.g., "SUCCESS")
    not as ExecutionStatus enum. This mock returns an ExecutionResult
    with the status set to the string value.
    """

    def __init__(self, status: ExecutionStatus = ExecutionStatus.SUCCESS):
        self.status = status
        self.last_test_case = None

    def execute_test(self, test_case: SemanticCase) -> ExecutionResult:
        self.last_test_case = test_case
        # Create result with string status value (not enum)
        return ExecutionResult(
            status=self.status.value,  # Use string value for Oracle compatibility
            result_data={"count": 10},
            error=None,
            elapsed_seconds=0.1
        )


class MockRuleEngine:
    """Mock rule engine for testing"""

    def evaluate_rules(self, test_case, execution_context):
        from core.rule_engine import RuleEvaluationResult, ThreeValuedEvaluationTrace, CoverageReport
        from datetime import datetime
        return RuleEvaluationResult(
            overall_passed=True,
            results=[],
            coverage_report=CoverageReport(
                session_id="test_session",
                created_at=datetime.now()
            ),
            trace=ThreeValuedEvaluationTrace(
                final_result=True
            )
        )


class MockPreconditionGate:
    """Mock precondition gate for testing"""

    def check(self, test_case, adapter, profile=None):
        from core.models import GateResult
        return GateResult(
            passed=True,
            reason="All checks passed"
        )


class MockOracle(OracleChecker):
    """Mock Oracle checker for testing"""

    def __init__(self, oracle_id: str, should_pass: bool = True, can_check_result: bool = True):
        super().__init__()
        self.oracle_id = oracle_id
        self.should_pass = should_pass
        self.can_check_result = can_check_result
        self.check_count = 0
        self.last_test_case = None
        self.last_result = None

    def get_definition(self) -> OracleDefinition:
        return OracleDefinition(
            oracle_id=self.oracle_id,
            name=f"Mock {self.oracle_id}",
            category=OracleCategory.CUSTOM,
            description="Mock oracle for testing",
            trigger_condition=TriggerCondition(),
            validation_logic=ValidationLogic(root=literal(True)),
            severity=Severity.LOW
        )

    def can_check(self, test_case: TestCase) -> bool:
        return self.can_check_result

    def check(self, test_case: TestCase, result: OracleExecutionResult) -> OracleResult:
        self.check_count += 1
        self.last_test_case = test_case
        self.last_result = result

        return OracleResult(
            oracle_id=self.oracle_id,
            passed=self.should_pass,
            details=f"Mock check result: {'passed' if self.should_pass else 'failed'}"
        )


class FailingMockOracle(MockOracle):
    """Mock Oracle that raises exception during check"""

    def check(self, test_case: TestCase, result: OracleExecutionResult) -> OracleResult:
        raise RuntimeError("Intentional failure for testing")


# ================================================================
# Basic Integration Tests
# ================================================================

def test_execution_pipeline_with_no_oracles():
    """Test ExecutionPipeline with no oracles (backward compatibility)"""
    pipeline = ExecutionPipeline(
        rule_engine=MockRuleEngine(),
        precondition_gate=MockPreconditionGate(),
        oracles=None
    )

    test_case = SemanticCase(
        test_id="test_001",
        operation="search",
        slot_values={"dimension": 512},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    contract = Contract(database_name="test_db", version="1.0")
    adapter = MockAdapter()

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter
    )

    assert result.oracle_results == []
    assert len(result.oracle_results) == 0


def test_execution_pipeline_with_empty_oracles_list():
    """Test ExecutionPipeline with empty oracles list"""
    pipeline = ExecutionPipeline(
        rule_engine=MockRuleEngine(),
        precondition_gate=MockPreconditionGate(),
        oracles=[]
    )

    test_case = SemanticCase(
        test_id="test_001",
        operation="search",
        slot_values={"dimension": 512},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    contract = Contract(database_name="test_db", version="1.0")
    adapter = MockAdapter()

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter
    )

    assert result.oracle_results == []


def test_execution_pipeline_with_single_oracle():
    """Test ExecutionPipeline with single Oracle"""
    oracle = MockOracle("test_oracle", should_pass=True)
    pipeline = ExecutionPipeline(
        rule_engine=MockRuleEngine(),
        precondition_gate=MockPreconditionGate(),
        oracles=[oracle]
    )

    test_case = SemanticCase(
        test_id="test_001",
        operation="search",
        slot_values={"dimension": 512},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    contract = Contract(database_name="test_db", version="1.0")
    adapter = MockAdapter()

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter
    )

    assert len(result.oracle_results) == 1
    assert result.oracle_results[0].oracle_id == "test_oracle"
    assert result.oracle_results[0].passed is True
    assert oracle.check_count == 1


def test_execution_pipeline_with_multiple_oracles():
    """Test ExecutionPipeline with multiple Oracles"""
    oracles = [
        MockOracle("oracle_1", should_pass=True),
        MockOracle("oracle_2", should_pass=False),
        MockOracle("oracle_3", should_pass=True)
    ]

    pipeline = ExecutionPipeline(
        rule_engine=MockRuleEngine(),
        precondition_gate=MockPreconditionGate(),
        oracles=oracles
    )

    test_case = SemanticCase(
        test_id="test_001",
        operation="search",
        slot_values={"dimension": 512},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    contract = Contract(database_name="test_db", version="1.0")
    adapter = MockAdapter()

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter
    )

    assert len(result.oracle_results) == 3
    assert result.oracle_results[0].passed is True
    assert result.oracle_results[1].passed is False
    assert result.oracle_results[2].passed is True

    # Verify all oracles were called
    for oracle in oracles:
        assert oracle.check_count == 1


# ================================================================
# Oracle Filtering Tests
# ================================================================

def test_oracle_that_cannot_check_is_skipped():
    """Test that Oracle that can't check is skipped"""
    oracle_can = MockOracle("can_check", can_check_result=True)
    oracle_cannot = MockOracle("cannot_check", can_check_result=False)

    pipeline = ExecutionPipeline(
        rule_engine=MockRuleEngine(),
        precondition_gate=MockPreconditionGate(),
        oracles=[oracle_can, oracle_cannot]
    )

    test_case = SemanticCase(
        test_id="test_001",
        operation="search",
        slot_values={"dimension": 512},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    contract = Contract(database_name="test_db", version="1.0")
    adapter = MockAdapter()

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter
    )

    # Only the oracle that can check should be called
    assert len(result.oracle_results) == 1
    assert result.oracle_results[0].oracle_id == "can_check"
    assert oracle_can.check_count == 1
    assert oracle_cannot.check_count == 0


# ================================================================
# Built-in Oracle Tests
# ================================================================

def test_with_range_constraint_oracle_passing():
    """Test with RangeConstraintOracle that passes"""
    # Create oracle that checks dimension in range
    oracle = RangeConstraintOracle(
        slot_name="dimension",
        min_value=1,
        max_value=1024
    )

    pipeline = ExecutionPipeline(
        rule_engine=MockRuleEngine(),
        precondition_gate=MockPreconditionGate(),
        oracles=[oracle]
    )

    test_case = SemanticCase(
        test_id="test_001",
        operation="search",
        slot_values={"dimension": 512},  # Within range
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    contract = Contract(database_name="test_db", version="1.0")
    adapter = MockAdapter()

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter
    )

    assert len(result.oracle_results) == 1
    assert result.oracle_results[0].passed is True


def test_with_range_constraint_oracle_failing():
    """Test with RangeConstraintOracle that fails"""
    oracle = RangeConstraintOracle(
        slot_name="dimension",
        min_value=1,
        max_value=1024
    )

    pipeline = ExecutionPipeline(
        rule_engine=MockRuleEngine(),
        precondition_gate=MockPreconditionGate(),
        oracles=[oracle]
    )

    test_case = SemanticCase(
        test_id="test_001",
        operation="search",
        slot_values={"dimension": 2048},  # Exceeds max
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    contract = Contract(database_name="test_db", version="1.0")
    adapter = MockAdapter()

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter
    )

    assert len(result.oracle_results) == 1
    assert result.oracle_results[0].passed is False
    assert "dimension" in result.oracle_results[0].violated_slots


def test_with_status_validation_oracle():
    """Test with StatusValidationOracle"""
    oracle = StatusValidationOracle(expected_status="SUCCESS")

    pipeline = ExecutionPipeline(
        rule_engine=MockRuleEngine(),
        precondition_gate=MockPreconditionGate(),
        oracles=[oracle]
    )

    test_case = SemanticCase(
        test_id="test_001",
        operation="search",
        slot_values={},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    contract = Contract(database_name="test_db", version="1.0")
    adapter = MockAdapter(status=ExecutionStatus.SUCCESS)

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter
    )

    assert len(result.oracle_results) == 1
    assert result.oracle_results[0].passed is True


# ================================================================
# Error Handling Tests
# ================================================================

def test_oracle_exception_handling():
    """Test that Oracle exceptions are handled gracefully"""
    failing_oracle = FailingMockOracle("failing_oracle")
    working_oracle = MockOracle("working_oracle", should_pass=True)

    pipeline = ExecutionPipeline(
        rule_engine=MockRuleEngine(),
        precondition_gate=MockPreconditionGate(),
        oracles=[failing_oracle, working_oracle]
    )

    test_case = SemanticCase(
        test_id="test_001",
        operation="search",
        slot_values={"dimension": 512},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    contract = Contract(database_name="test_db", version="1.0")
    adapter = MockAdapter()

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter
    )

    # Both oracles should produce results (one failed, one passed)
    assert len(result.oracle_results) == 2

    # Failing oracle should have error result
    failing_result = next(r for r in result.oracle_results if r.oracle_id == "failing_oracle")
    assert failing_result.passed is False
    assert "exception" in failing_result.details.lower()

    # Working oracle should have normal result
    working_result = next(r for r in result.oracle_results if r.oracle_id == "working_oracle")
    assert working_result.passed is True


# ================================================================
# Precondition Failed Tests
# ================================================================

def test_oracles_not_run_when_precondition_fails():
    """Test that oracles are not run when precondition fails"""
    class FailingPreconditionGate:
        def check(self, test_case, adapter, profile=None):
            from core.models import GateResult
            return GateResult(
                passed=False,
                reason="Precondition failed"
            )

    oracle = MockOracle("test_oracle")
    pipeline = ExecutionPipeline(
        rule_engine=MockRuleEngine(),
        precondition_gate=FailingPreconditionGate(),
        oracles=[oracle]
    )

    test_case = SemanticCase(
        test_id="test_001",
        operation="search",
        slot_values={"dimension": 512},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    contract = Contract(database_name="test_db", version="1.0")
    adapter = MockAdapter()

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter
    )

    # Should return PRECONDITION_FAILED
    assert result.status == ExecutionStatus.PRECONDITION_FAILED
    assert result.oracle_results == []
    assert oracle.check_count == 0  # Oracle should not be called
