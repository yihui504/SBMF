# tests/test_execution_pipeline.py
import pytest
from core.execution_pipeline import ExecutionPipeline
from core.models import *
from core.rule_engine import RuleEngine
from core.precondition_gate import PreconditionGate
from adapters.seekdb import SeekDBAdapter

def test_execution_pipeline_precondition_failed():
    """Test execution pipeline when precondition fails"""
    contract = Contract(
        database_name="test_db",
        version="1.0",
        core_slots=[]
    )

    rule_engine = RuleEngine(contract)
    precondition_gate = PreconditionGate(rule_engine=rule_engine)

    pipeline = ExecutionPipeline(rule_engine=rule_engine, precondition_gate=precondition_gate)

    test_case = TestCase(
        test_id="test_1",
        operation="search",
        slot_values={},
        raw_parameters={},
        is_legal=False,
        scope=SlotScope.COLLECTION
    )

    # Use SeekDB adapter instead of mock
    adapter = SeekDBAdapter()

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter,
        profile=None,
        state_model=None
    )

    assert result.status == ExecutionStatus.SUCCESS  # No rules, so precondition passes
    assert result.gate_result is not None

def test_execution_pipeline_full_flow():
    """Test execution pipeline full flow"""
    contract = Contract(
        database_name="test_db",
        version="1.0",
        core_slots=[]
    )

    rule_engine = RuleEngine(contract)
    precondition_gate = PreconditionGate(rule_engine=rule_engine)

    pipeline = ExecutionPipeline(rule_engine=rule_engine, precondition_gate=precondition_gate)

    test_case = TestCase(
        test_id="test_2",
        operation="search",
        slot_values={"top_k": 10},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    # Use SeekDB adapter (simplified, no actual DB)
    adapter = SeekDBAdapter()

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter,
        profile=None,
        state_model=None
    )

    assert result.status == ExecutionStatus.SUCCESS
    assert result.gate_result is not None
    assert result.rule_evaluation_result is not None
    assert result.bug_type_derivation is not None
    assert result.elapsed_seconds >= 0

def test_execution_pipeline_bug_type_derivation():
    """Test bug type derivation in pipeline"""
    contract = Contract(
        database_name="test_db",
        version="1.0",
        core_slots=[]
    )

    rule_engine = RuleEngine(contract)
    precondition_gate = PreconditionGate(rule_engine=rule_engine)

    pipeline = ExecutionPipeline(rule_engine=rule_engine, precondition_gate=precondition_gate)

    # Illegal test that succeeds (TYPE_1)
    test_case = TestCase(
        test_id="test_3",
        operation="search",
        slot_values={"top_k": 10},  # Valid value but test is illegal
        raw_parameters={},
        is_legal=False,
        scope=SlotScope.COLLECTION
    )

    adapter = SeekDBAdapter()

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter,
        profile=None,
        state_model=None
    )

    # Should succeed (simplified adapter)
    assert result.status == ExecutionStatus.SUCCESS
    # BugTypeEngine should derive TYPE_1 (illegal success)
    assert result.bug_type_derivation is not None
    assert result.bug_type_derivation.bug_type == BugType.TYPE_1
