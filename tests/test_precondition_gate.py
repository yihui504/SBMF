# tests/test_precondition_gate.py
import pytest
from core.precondition_gate import PreconditionGate
from core.models import *
from core.rule_engine import RuleEngine, ExecutionContext

def test_precondition_gate_all_passed():
    """Test precondition gate passes when all checks pass"""
    contract = Contract(
        database_name="test_db",
        version="1.0",
        core_slots=[]
    )

    rule_engine = RuleEngine(contract)
    gate = PreconditionGate(rule_engine=rule_engine, state_model=None)

    test_case = TestCase(
        test_id="test_1",
        operation="search",
        slot_values={"top_k": 10},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    result = gate.check(test_case=test_case, adapter=None, profile=None)

    assert result.passed is True
    assert "all_checks_passed" in result.reason

def test_precondition_gate_with_profile_skip():
    """Test precondition gate respects profile skip logic"""
    from unittest.mock import Mock

    contract = Contract(
        database_name="test_db",
        version="1.0",
        core_slots=[]
    )

    rule_engine = RuleEngine(contract)
    gate = PreconditionGate(rule_engine=rule_engine, state_model=None)

    test_case = TestCase(
        test_id="test_2",
        operation="search",
        slot_values={"top_k": 10},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    # Mock profile that wants to skip
    mock_profile = Mock()
    mock_profile.should_skip_test.return_value = "COSINE + HNSW not supported"

    result = gate.check(test_case=test_case, adapter=None, profile=mock_profile)

    assert result.passed is False
    assert "profile_skip" in result.reason
    assert "COSINE + HNSW not supported" in result.reason

def test_precondition_gate_no_profile():
    """Test precondition gate works without profile"""
    contract = Contract(
        database_name="test_db",
        version="1.0",
        core_slots=[]
    )

    rule_engine = RuleEngine(contract)
    gate = PreconditionGate(rule_engine=rule_engine, state_model=None)

    test_case = TestCase(
        test_id="test_3",
        operation="search",
        slot_values={"top_k": 10},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    result = gate.check(test_case=test_case, adapter=None, profile=None)

    # Should pass since no rules to check and no profile
    assert result.passed is True

def test_precondition_gate_with_coverage_report():
    """Test that coverage report is included in result"""
    contract = Contract(
        database_name="test_db",
        version="1.0",
        core_slots=[]
    )

    rule_engine = RuleEngine(contract)
    gate = PreconditionGate(rule_engine=rule_engine, state_model=None)

    test_case = TestCase(
        test_id="test_4",
        operation="search",
        slot_values={},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    result = gate.check(test_case=test_case, adapter=None, profile=None)

    assert result.passed is True
    assert hasattr(result, 'coverage_report')
    assert result.coverage_report is not None
