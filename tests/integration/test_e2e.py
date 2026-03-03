"""
End-to-End Integration Tests

Tests complete framework workflow: Contract → Profile → Oracle → Pipeline
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from contract import load_contract
from profiles import SeekDBProfilePlugin
from core import ExecutionPipeline, OracleReporter, RuleEngine, PreconditionGate, ReportFormat
from core.models import SemanticCase, SlotScope, ExecutionStatus
from oracle import (
    RangeConstraintOracle,
    EnumConstraintOracle,
    RelationalConstraintOracle,
    StatusValidationOracle,
    OracleResult,
    ComparisonOperator,
)
from adapters.seekdb import SeekDBAdapter


# ================================================================
# Fixtures
# ================================================================

@pytest.fixture(scope="module")
def contract():
    return load_contract("tests/fixtures/integration/seekdb_contract.yaml")


@pytest.fixture(scope="module")
def adapter():
    return SeekDBAdapter()


@pytest.fixture(scope="module")
def profile():
    return SeekDBProfilePlugin(enable_logging=False)


@pytest.fixture
def pipeline_with_oracles(contract):
    oracles = [
        RangeConstraintOracle("dimension", min_value=1, max_value=32768),
        EnumConstraintOracle("metric_type", allowed_values=["L2", "IP", "COSINE"]),
        RelationalConstraintOracle("search_range", ComparisonOperator.GE, "top_k"),
    ]
    rule_engine = RuleEngine(contract)
    precondition_gate = PreconditionGate(rule_engine)
    return ExecutionPipeline(
        rule_engine=rule_engine,
        precondition_gate=precondition_gate,
        oracles=oracles
    )


# ================================================================
# Test Scenarios
# ================================================================

def test_scenario1_normal_search_all_passed(pipeline_with_oracles, contract, adapter, profile):
    """S001: Normal search - all checks should pass"""
    test_case = SemanticCase(
        test_id="S001_Normal_Search",
        operation="search",
        slot_values={
            "dimension": 512,
            "metric_type": "L2",
            "top_k": 10,
            "search_range": 100,
        },
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    result = pipeline_with_oracles.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter,
        profile=profile
    )

    # Verify execution succeeded
    assert result.status == ExecutionStatus.SUCCESS

    # Verify all Oracle checks passed
    oracle_ids = [r.oracle_id for r in result.oracle_results]
    assert len(oracle_ids) == 3
    assert "range_dimension" in oracle_ids
    assert "enum_metric_type" in oracle_ids
    assert "relational_search_range_top_k" in oracle_ids

    # Check results - use explicit iteration instead of all()
    passed_count = sum(1 for r in result.oracle_results if r.passed)
    results_dict = {r.oracle_id: r.passed for r in result.oracle_results}
    assert passed_count == 3, f"Expected 3 passed, got {passed_count}. Results: {results_dict}"

    print(f"S001: PASSED - {len(result.oracle_results)} oracles checked")


def test_scenario2_dimension_exceeds_maximum(pipeline_with_oracles, contract, adapter, profile):
    """S002: Dimension exceeds maximum - should be skipped by Profile"""
    test_case = SemanticCase(
        test_id="S002_Dimension_Exceeds_Max",
        operation="search",
        slot_values={
            "dimension": 99999,  # Exceeds 32768
            "metric_type": "L2",
            "top_k": 10,
        },
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    result = pipeline_with_oracles.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter,
        profile=profile
    )

    assert result.status == ExecutionStatus.PRECONDITION_FAILED
    assert "exceeds maximum" in result.gate_result.reason.lower()

    print(f"S002: PASSED - Correctly skipped: {result.gate_result.reason}")


def test_scenario3_unsupported_metric_type(pipeline_with_oracles, contract, adapter, profile):
    """S003: Unsupported metric type - should be skipped"""
    test_case = SemanticCase(
        test_id="S003_Unsupported_Metric",
        operation="search",
        slot_values={
            "dimension": 512,
            "metric_type": "HAMMING",  # Not supported
            "top_k": 10,
        },
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    result = pipeline_with_oracles.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter,
        profile=profile
    )

    assert result.status == ExecutionStatus.PRECONDITION_FAILED
    assert "not supported" in result.gate_result.reason.lower()

    print(f"S003: PASSED - Correctly skipped: {result.gate_result.reason}")


def test_scenario4_relational_constraint_violation(contract, adapter, profile):
    """S004: Relational constraint violation - Oracle should fail"""
    # Use only relational oracle
    oracles = [
        RelationalConstraintOracle("search_range", ComparisonOperator.GE, "top_k"),
    ]

    rule_engine = RuleEngine(contract)
    precondition_gate = PreconditionGate(rule_engine)
    pipeline = ExecutionPipeline(
        rule_engine=rule_engine,
        precondition_gate=precondition_gate,
        oracles=oracles
    )

    test_case = SemanticCase(
        test_id="S004_Relational_Violation",
        operation="search",
        slot_values={
            "dimension": 512,
            "metric_type": "L2",
            "top_k": 100,
            "search_range": 50,  # < top_k, violates constraint
        },
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter,
        profile=profile
    )

    assert result.status == ExecutionStatus.SUCCESS
    assert len(result.oracle_results) == 1
    assert not result.oracle_results[0].passed
    assert "search_range" in result.oracle_results[0].violated_slots

    print(f"S004: PASSED - Oracle detected violation: {result.oracle_results[0].details}")


def test_scenario5_boundary_values(pipeline_with_oracles, contract, adapter, profile):
    """S005: Boundary value tests"""
    # Create oracles that don't require search_range
    boundary_oracles = [
        RangeConstraintOracle("dimension", min_value=1, max_value=32768),
        EnumConstraintOracle("metric_type", allowed_values=["L2", "IP", "COSINE"]),
    ]

    rule_engine = RuleEngine(contract)
    precondition_gate = PreconditionGate(rule_engine)
    pipeline = ExecutionPipeline(
        rule_engine=rule_engine,
        precondition_gate=precondition_gate,
        oracles=boundary_oracles
    )

    test_cases = [
        SemanticCase(
            test_id="B001_Dimension_Min",
            operation="search",
            slot_values={"dimension": 1, "metric_type": "L2", "top_k": 1},
            raw_parameters={},
            is_legal=True,
            scope=SlotScope.COLLECTION
        ),
        SemanticCase(
            test_id="B002_Dimension_Max",
            operation="search",
            slot_values={"dimension": 32768, "metric_type": "L2", "top_k": 1},
            raw_parameters={},
            is_legal=True,
            scope=SlotScope.COLLECTION
        ),
    ]

    for test_case in test_cases:
        result = pipeline.execute_test_case(
            test_case=test_case,
            contract=contract,
            adapter=adapter,
            profile=profile
        )

        assert result.status == ExecutionStatus.SUCCESS
        passed_count = sum(1 for r in result.oracle_results if r.passed)
        assert passed_count == 2  # Only 2 oracles without relational

        print(f"{test_case.test_id}: PASSED")


def test_scenario6_cosine_hnsw_not_supported(pipeline_with_oracles, contract, adapter, profile):
    """S006: COSINE + HNSW combination not supported"""
    test_case = SemanticCase(
        test_id="B004_COSINE_HNSW",
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
    )

    result = pipeline_with_oracles.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter,
        profile=profile
    )

    assert result.status == ExecutionStatus.PRECONDITION_FAILED
    assert "COSINE" in result.gate_result.reason and "HNSW" in result.gate_result.reason

    print(f"B004: PASSED - Correctly skipped: {result.gate_result.reason}")


def test_scenario7_generate_reports():
    """Generate test reports in multiple formats"""
    from datetime import datetime

    # Simulate Oracle results from multiple test runs
    all_results = [
        # Test 1: All passed
        [
            OracleResult(oracle_id="dimension", passed=True, details="Dimension 512 OK"),
            OracleResult(oracle_id="metric_type", passed=True, details="Metric L2 OK"),
            OracleResult(oracle_id="relational", passed=True, details="100 >= 10 OK"),
        ],
        # Test 2: Relational violation
        [
            OracleResult(oracle_id="dimension", passed=True, details="Dimension 512 OK"),
            OracleResult(
                oracle_id="relational",
                passed=False,
                details="search_range (50) < top_k (100)",
                violated_slots=["search_range"]
            ),
        ],
        # Test 3: All passed
        [
            OracleResult(oracle_id="dimension", passed=True, details="Dimension 1024 OK"),
            OracleResult(oracle_id="metric_type", passed=True, details="Metric IP OK"),
        ],
    ]

    reporter = OracleReporter()
    aggregated_report = reporter.aggregate_results(all_results)

    # Create reports directory
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    # Save reports in multiple formats
    reporter.save_report(
        aggregated_report,
        reports_dir / "integration_test_report.json",
        ReportFormat.JSON
    )
    reporter.save_report(
        aggregated_report,
        reports_dir / "integration_test_report.html",
        ReportFormat.HTML
    )
    reporter.save_report(
        aggregated_report,
        reports_dir / "integration_test_report.txt",
        ReportFormat.TEXT
    )

    print(f"Test Report Summary:")
    print(f"  Total Oracle checks: {aggregated_report.total_oracles}")
    print(f"  Passed: {aggregated_report.passed_count}")
    print(f"  Failed: {aggregated_report.failed_count}")
    print(f"  Pass rate: {aggregated_report.pass_rate * 100:.1f}%")
    print(f"Reports saved to: {reports_dir.absolute()}")

    # Verify expectations (7 results total, not 8)
    assert aggregated_report.total_oracles == 7
    assert aggregated_report.passed_count == 6
    assert aggregated_report.failed_count == 1


def test_main_summary():
    """Print summary of integration test results"""
    print()
    print("=" * 70)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 70)
    print()
    print("Test Scenarios:")
    print("  S001: Normal search with valid parameters")
    print("  S002: Dimension exceeds maximum (skipped by Profile)")
    print("  S003: Unsupported metric type (skipped by Profile)")
    print("  S004: Relational constraint violation (Oracle fail)")
    print("  S005: Boundary value tests (min/max)")
    print("  S006: COSINE + HNSW not supported (skipped)")
    print("  S007: Report generation")
    print()
    print("Framework Components Validated:")
    print("  [OK] Contract DSL loading and validation")
    print("  [OK] Profile Plugin (SeekDB)")
    print("  [OK] Oracle Checkers (Range, Enum, Relational)")
    print("  [OK] ExecutionPipeline integration")
    print("  [OK] Report generation (JSON, HTML, TEXT)")
    print()
    print("=" * 70)
