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

    test_case = SemanticCase(
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

    test_case = SemanticCase(
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
    # Verify slot_coverage is populated
    assert "slot_coverage" in report.__dataclass_fields__
    assert isinstance(report.slot_coverage, dict)
    # Verify boundary_coverage is populated (even if 0.0 for Phase 1)
    assert hasattr(report, 'boundary_coverage')
    assert report.boundary_coverage == 0.0

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

def test_rule_coverage_with_slots():
    """Test coverage calculation when contract has slots"""
    from core.models import Slot, SlotType, SlotScope

    contract = Contract(
        database_name="test_db",
        version="1.0",
        core_slots=[
            Slot(
                slot_name="top_k",
                description="top k parameter",
                type=SlotType.INTEGER,
                scope=SlotScope.COLLECTION,
                depends_on=[]
            )
        ]
    )

    engine = RuleEngine(contract)

    test_case = SemanticCase(
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

    # Verify coverage report has all fields populated
    assert result.coverage_report.slot_coverage is not None
    assert isinstance(result.coverage_report.slot_coverage, dict)
    # top_k slot should be in slot_coverage
    assert "top_k" in result.coverage_report.slot_coverage
    # boundary_coverage should be 0.0 for Phase 1
    assert result.coverage_report.boundary_coverage == 0.0
    # Verify none_sources is populated (slots without rules contribute to None)
    assert len(result.trace.none_sources) > 0
    assert "slot:top_k" in result.trace.none_sources

def test_rule_engine_empty_contract():
    """Test RuleEngine with empty contract (no slots)"""
    contract = Contract(
        database_name="test_db",
        version="1.0",
        core_slots=[]
    )

    engine = RuleEngine(contract)

    test_case = SemanticCase(
        test_id="test_1",
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

    # Empty contract: no slots, no rules
    assert result.overall_passed is None  # Three-valued logic: empty list -> None
    assert len(result.results) == 0
    # Coverage report should still be complete
    assert result.coverage_report.slot_coverage == {}
    assert result.coverage_report.boundary_coverage == 0.0
    assert result.coverage_report.total_evaluations == 0
