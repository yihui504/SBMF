# tests/test_rule_engine.py
import pytest
from core.rule_engine import RuleEngine, RuleEvaluationResult, ExecutionContext, CoverageReport
from core.models import *

def test_rule_engine_evaluate_all_passed():
    """Test evaluating rules with no rules (empty contract)"""
    contract = Contract(
        database_name="test_db",
        version="1.0",
        core_slots=[]
    )

    engine = RuleEngine(contract)

    test_case = TestCase(
        test_id="test_1",
        operation="search",
        slot_values={"top_k": 10},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    execution_context = ExecutionContext(
        adapter=None,
        profile=None,
        state_model=None,
        test_case=test_case
    )

    result = engine.evaluate_rules(test_case, execution_context)

    # Empty results list should return None, but get_report() returns CoverageReport
    assert result.overall_passed is None
    assert isinstance(result.coverage_report, CoverageReport)
    assert result.trace is not None

def test_rule_engine_trace():
    """Test explainability output (trace)"""
    contract = Contract(
        database_name="test_db",
        version="1.0",
        core_slots=[]
    )

    engine = RuleEngine(contract)

    test_case = TestCase(
        test_id="test",
        operation="search",
        slot_values={},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    execution_context = ExecutionContext(
        adapter=None,
        profile=None,
        state_model=None,
        test_case=test_case
    )

    result = engine.evaluate_rules(test_case, execution_context)

    assert hasattr(result, 'trace')
    assert hasattr(result.trace, 'false_sources')
    assert hasattr(result.trace, 'none_sources')
    assert hasattr(result.trace, 'final_result')
    assert hasattr(result.trace, 'evaluation_path')

def test_rule_coverage_tracker():
    """Test coverage tracking"""
    from core.rule_engine import RuleCoverageTracker

    tracker = RuleCoverageTracker(session_id="test_session")

    # Record some evaluations
    tracker.record_evaluation("top_k", 10, True)
    tracker.record_evaluation("top_k", 100, False)
    tracker.record_evaluation("dimension", 128, True)

    report = tracker.get_report()

    assert report.session_id == "test_session"
    assert report.total_evaluations == 3
    assert report.unique_values_tested["top_k"] == 2  # 10 and 100
    assert report.unique_values_tested["dimension"] == 1  # 128

def test_rule_coverage_tracker_auto_session_id():
    """Test auto-generated session ID"""
    from core.rule_engine import RuleCoverageTracker

    tracker = RuleCoverageTracker()

    assert tracker.session_id is not None
    assert tracker.session_id.startswith("session_")

def test_rule_engine_session_isolation():
    """Test RuleEngine maintains session isolation"""
    contract = Contract(
        database_name="test_db",
        version="1.0",
        core_slots=[]
    )

    engine = RuleEngine(contract, session_id="my_session")

    assert engine.session_id == "my_session"
    assert engine.coverage_tracker.session_id == "my_session"
