"""
Tests for Oracle Reporter.

Tests OracleReport and OracleReporter classes.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime
from core.oracle_reporter import (
    ReportFormat,
    OracleReport,
    OracleReporter,
)
from oracle.base import OracleResult


# ================================================================
# Fixtures
# ================================================================

@pytest.fixture
def sample_oracle_results():
    """Provide sample Oracle results for testing"""
    return [
        OracleResult(
            oracle_id="range_dimension",
            passed=True,
            details="Dimension 512 is within range [1, 32768]"
        ),
        OracleResult(
            oracle_id="enum_metric_type",
            passed=True,
            details="Metric type L2 is allowed"
        ),
        OracleResult(
            oracle_id="relational_range_topk",
            passed=False,
            details="search_range=50 < top_k=100",
            violated_slots=["search_range"],
            evidence={"search_range": 50, "top_k": 100, "operator": ">="}
        ),
        OracleResult(
            oracle_id="status_validation",
            passed=True,
            details="Status is SUCCESS, expected SUCCESS: passed"
        ),
    ]


@pytest.fixture
def all_passed_results():
    """Provide all-passed results"""
    return [
        OracleResult(oracle_id="oracle1", passed=True, details="Passed"),
        OracleResult(oracle_id="oracle2", passed=True, details="Passed"),
        OracleResult(oracle_id="oracle3", passed=True, details="Passed"),
    ]


@pytest.fixture
def all_failed_results():
    """Provide all-failed results"""
    return [
        OracleResult(oracle_id="oracle1", passed=False, details="Failed 1"),
        OracleResult(oracle_id="oracle2", passed=False, details="Failed 2"),
    ]


# ================================================================
# OracleReport Tests
# ================================================================

def test_oracle_report_creation(sample_oracle_results):
    """Test creating OracleReport"""
    report = OracleReport(
        total_oracles=4,
        passed_count=3,
        failed_count=1,
        skipped_count=0,
        results=sample_oracle_results,
        summary="3/4 Oracle checks passed, 1 failed (Failed: relational_range_topk)"
    )

    assert report.total_oracles == 4
    assert report.passed_count == 3
    assert report.failed_count == 1
    assert len(report.results) == 4


def test_oracle_report_pass_rate(sample_oracle_results):
    """Test pass_rate property"""
    report = OracleReport(
        total_oracles=4,
        passed_count=3,
        failed_count=1,
        skipped_count=0,
        results=sample_oracle_results,
        summary="Test"
    )

    assert report.pass_rate == 0.75


def test_oracle_report_pass_rate_all_passed(all_passed_results):
    """Test pass_rate when all passed"""
    report = OracleReport(
        total_oracles=3,
        passed_count=3,
        failed_count=0,
        skipped_count=0,
        results=all_passed_results,
        summary="All passed"
    )

    assert report.pass_rate == 1.0


def test_oracle_report_pass_rate_empty():
    """Test pass_rate when empty"""
    report = OracleReport(
        total_oracles=0,
        passed_count=0,
        failed_count=0,
        skipped_count=0,
        results=[],
        summary="Empty"
    )

    assert report.pass_rate == 1.0


def test_oracle_report_has_failures(sample_oracle_results):
    """Test has_failures property"""
    report_with_failures = OracleReport(
        total_oracles=4,
        passed_count=3,
        failed_count=1,
        skipped_count=0,
        results=sample_oracle_results,
        summary="Test"
    )

    assert report_with_failures.has_failures is True

    # Create all passed results inline
    all_passed = [
        OracleResult(oracle_id="oracle1", passed=True, details="Passed"),
        OracleResult(oracle_id="oracle2", passed=True, details="Passed"),
        OracleResult(oracle_id="oracle3", passed=True, details="Passed"),
    ]
    report_without_failures = OracleReport(
        total_oracles=3,
        passed_count=3,
        failed_count=0,
        skipped_count=0,
        results=all_passed,
        summary="All passed"
    )

    assert report_without_failures.has_failures is False


def test_oracle_report_failed_oracles(sample_oracle_results):
    """Test failed_oracles property"""
    report = OracleReport(
        total_oracles=4,
        passed_count=3,
        failed_count=1,
        skipped_count=0,
        results=sample_oracle_results,
        summary="Test"
    )

    failed = report.failed_oracles
    assert len(failed) == 1
    assert failed[0].oracle_id == "relational_range_topk"
    assert failed[0].passed is False


def test_oracle_report_passed_oracles(sample_oracle_results):
    """Test passed_oracles property"""
    report = OracleReport(
        total_oracles=4,
        passed_count=3,
        failed_count=1,
        skipped_count=0,
        results=sample_oracle_results,
        summary="Test"
    )

    passed = report.passed_oracles
    assert len(passed) == 3
    assert all(r.passed for r in passed)


def test_oracle_report_to_dict(sample_oracle_results):
    """Test to_dict method"""
    report = OracleReport(
        total_oracles=4,
        passed_count=3,
        failed_count=1,
        skipped_count=0,
        results=sample_oracle_results,
        summary="Test"
    )

    result_dict = report.to_dict()

    assert "summary" in result_dict
    assert result_dict["summary"]["total_oracles"] == 4
    assert result_dict["summary"]["passed_count"] == 3
    assert result_dict["summary"]["failed_count"] == 1
    assert result_dict["summary"]["pass_rate"] == 75.0
    assert result_dict["summary"]["has_failures"] is True
    assert "results" in result_dict
    assert len(result_dict["results"]) == 4


# ================================================================
# OracleReporter Tests
# ================================================================

def test_reporter_initialization():
    """Test OracleReporter initialization"""
    reporter = OracleReporter()

    assert reporter.oracles == []
    assert reporter._start_time is None


def test_reporter_with_oracles():
    """Test OracleReporter with oracles list"""
    oracles = ["oracle1", "oracle2"]  # Mock oracles
    reporter = OracleReporter(oracles)

    assert reporter.oracles == oracles


def test_generate_report(sample_oracle_results):
    """Test generate_report method"""
    reporter = OracleReporter()

    report = reporter.generate_report(sample_oracle_results)

    assert isinstance(report, OracleReport)
    assert report.total_oracles == 4
    assert report.passed_count == 3
    assert report.failed_count == 1
    assert "3/4" in report.summary


def test_generate_report_all_passed(all_passed_results):
    """Test generate_report with all passed results"""
    reporter = OracleReporter()

    report = reporter.generate_report(all_passed_results)

    assert report.passed_count == 3
    assert report.failed_count == 0
    assert report.has_failures is False
    assert "All 3" in report.summary


def test_generate_report_all_failed(all_failed_results):
    """Test generate_report with all failed results"""
    reporter = OracleReporter()

    report = reporter.generate_report(all_failed_results)

    assert report.passed_count == 0
    assert report.failed_count == 2
    assert report.has_failures is True


def test_generate_report_empty():
    """Test generate_report with empty results"""
    reporter = OracleReporter()

    report = reporter.generate_report([])

    assert report.total_oracles == 0
    assert report.passed_count == 0
    assert report.failed_count == 0
    assert report.summary == "No Oracle checks performed"


def test_aggregate_results():
    """Test aggregate_results method"""
    reporter = OracleReporter()

    # Simulate 3 test runs
    test1_results = [
        OracleResult(oracle_id="o1", passed=True, details=""),
        OracleResult(oracle_id="o2", passed=False, details=""),
    ]
    test2_results = [
        OracleResult(oracle_id="o1", passed=True, details=""),
        OracleResult(oracle_id="o2", passed=True, details=""),
    ]
    test3_results = [
        OracleResult(oracle_id="o1", passed=False, details=""),
    ]

    report = reporter.aggregate_results([test1_results, test2_results, test3_results])

    # Total: 5 results (2 + 2 + 1)
    assert report.total_oracles == 5
    # Passed: o1(t1) + o1(t2) + o2(t2) = 3
    assert report.passed_count == 3
    # Failed: o2(t1) + o1(t3) = 2
    assert report.failed_count == 2


def test_timer_functionality():
    """Test timer functionality"""
    reporter = OracleReporter()
    import time

    reporter.start_timer()
    time.sleep(0.01)  # Small delay
    duration = reporter.stop_timer()

    assert duration >= 0.01
    assert duration < 1.0  # Should be fast


# ================================================================
# JSON Output Tests
# ================================================================

def test_to_json(sample_oracle_results):
    """Test to_json method"""
    reporter = OracleReporter()
    report = reporter.generate_report(sample_oracle_results)

    json_str = reporter.to_json(report)

    # Verify it's valid JSON
    parsed = json.loads(json_str)
    assert parsed["summary"]["total_oracles"] == 4
    assert parsed["summary"]["pass_rate"] == 75.0


def test_to_json_indent(sample_oracle_results):
    """Test to_json with custom indent"""
    reporter = OracleReporter()
    report = reporter.generate_report(sample_oracle_results)

    json_no_indent = reporter.to_json(report, indent=None)
    json_with_indent = reporter.to_json(report, indent=4)

    # Indented version should be longer
    assert len(json_with_indent) > len(json_no_indent)


# ================================================================
# HTML Output Tests
# ================================================================

def test_to_html_contains_summary(sample_oracle_results):
    """Test to_html contains summary"""
    reporter = OracleReporter()
    report = reporter.generate_report(sample_oracle_results)

    html = reporter.to_html(report)

    assert "<!DOCTYPE html>" in html
    assert report.summary in html
    assert "Total Checks" in html
    assert "Passed" in html
    assert "Failed" in html


def test_to_html_contains_results(sample_oracle_results):
    """Test to_html contains individual results"""
    reporter = OracleReporter()
    report = reporter.generate_report(sample_oracle_results)

    html = reporter.to_html(report)

    # Check for oracle IDs
    assert "range_dimension" in html
    assert "enum_metric_type" in html
    assert "relational_range_topk" in html
    assert "status_validation" in html


def test_to_html_status_classes(sample_oracle_results):
    """Test to_html uses correct CSS classes"""
    reporter = OracleReporter()
    report = reporter.generate_report(sample_oracle_results)

    html = reporter.to_html(report)

    # Check for status classes
    assert 'class="status passed"' in html
    assert 'class="status failed"' in html
    assert 'class="result-item passed"' in html
    assert 'class="result-item failed"' in html


def test_to_html_custom_title():
    """Test to_html with custom title"""
    reporter = OracleReporter()
    report = reporter.generate_report([])

    html = reporter.to_html(report, title="Custom Oracle Report")

    assert "<title>Custom Oracle Report</title>" in html
    assert "<h1>Custom Oracle Report</h1>" in html


# ================================================================
# Text Output Tests
# ================================================================

def test_to_text_contains_summary(sample_oracle_results):
    """Test to_text contains summary"""
    reporter = OracleReporter()
    report = reporter.generate_report(sample_oracle_results)

    text = reporter.to_text(report)

    assert "ORACLE REPORT" in text
    assert report.summary in text
    assert "Total Oracle checks: 4" in text
    assert "Passed: 3" in text
    assert "Failed: 1" in text


def test_to_text_contains_results(sample_oracle_results):
    """Test to_text contains individual results"""
    reporter = OracleReporter()
    report = reporter.generate_report(sample_oracle_results)

    text = reporter.to_text(report)

    assert "[PASSED]" in text
    assert "[FAILED]" in text
    assert "relational_range_topk" in text


def test_to_text_contains_evidence(sample_oracle_results):
    """Test to_text includes evidence when present"""
    reporter = OracleReporter()
    report = reporter.generate_report(sample_oracle_results)

    text = reporter.to_text(report)

    assert "Evidence:" in text
    assert "search_range" in text


# ================================================================
# Save Report Tests
# ================================================================

def test_save_report_json(sample_oracle_results):
    """Test saving report as JSON"""
    reporter = OracleReporter()
    report = reporter.generate_report(sample_oracle_results)

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name

    try:
        reporter.save_report(report, temp_path, ReportFormat.JSON)

        # Verify file exists and has valid content
        assert os.path.exists(temp_path)

        with open(temp_path, 'r') as f:
            content = f.read()
            parsed = json.loads(content)
            assert parsed["summary"]["total_oracles"] == 4
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_save_report_html(sample_oracle_results):
    """Test saving report as HTML"""
    reporter = OracleReporter()
    report = reporter.generate_report(sample_oracle_results)

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html') as f:
        temp_path = f.name

    try:
        reporter.save_report(report, temp_path, ReportFormat.HTML)

        # Verify file exists and has valid HTML
        assert os.path.exists(temp_path)

        with open(temp_path, 'r') as f:
            content = f.read()
            assert "<!DOCTYPE html>" in content
            assert "</html>" in content
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_save_report_text(sample_oracle_results):
    """Test saving report as text"""
    reporter = OracleReporter()
    report = reporter.generate_report(sample_oracle_results)

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        temp_path = f.name

    try:
        reporter.save_report(report, temp_path, ReportFormat.TEXT)

        # Verify file exists and has content
        assert os.path.exists(temp_path)

        with open(temp_path, 'r') as f:
            content = f.read()
            assert "ORACLE REPORT" in content
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_save_report_all_formats(sample_oracle_results):
    """Test saving report with all supported formats"""
    reporter = OracleReporter()
    report = reporter.generate_report(sample_oracle_results)

    # Test all supported formats
    formats_to_test = [
        (ReportFormat.JSON, ".json"),
        (ReportFormat.HTML, ".html"),
        (ReportFormat.TEXT, ".txt"),
    ]

    for fmt, ext in formats_to_test:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=ext) as f:
            temp_path = f.name

        try:
            reporter.save_report(report, temp_path, fmt)
            assert os.path.exists(temp_path)

            # Verify file has content
            with open(temp_path, 'r') as f:
                content = f.read()
                assert len(content) > 0
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


# ================================================================
# Summary Generation Tests
# ================================================================

def test_summary_all_passed():
    """Test summary when all passed"""
    reporter = OracleReporter()

    results = [
        OracleResult(oracle_id="o1", passed=True, details=""),
        OracleResult(oracle_id="o2", passed=True, details=""),
    ]

    summary = reporter._generate_summary(results, 2, 2)

    assert summary == "All 2 Oracle checks passed"


def test_summary_all_failed():
    """Test summary when all failed"""
    reporter = OracleReporter()

    results = [
        OracleResult(oracle_id="o1", passed=False, details=""),
        OracleResult(oracle_id="o2", passed=False, details=""),
    ]

    summary = reporter._generate_summary(results, 0, 2)

    assert "0/2 Oracle checks passed" in summary
    assert "2 failed" in summary


def test_summary_mixed_with_names():
    """Test summary with mixed results includes failed names"""
    reporter = OracleReporter()

    results = [
        OracleResult(oracle_id="o1", passed=True, details=""),
        OracleResult(oracle_id="failed_oracle", passed=False, details=""),
        OracleResult(oracle_id="also_failed", passed=False, details=""),
    ]

    summary = reporter._generate_summary(results, 1, 3)

    assert "1/3 Oracle checks passed" in summary
    assert "2 failed" in summary
    assert "failed_oracle" in summary
    assert "also_failed" in summary


def test_summary_empty():
    """Test summary with no results"""
    reporter = OracleReporter()

    summary = reporter._generate_summary([], 0, 0)

    assert summary == "No Oracle checks performed"
