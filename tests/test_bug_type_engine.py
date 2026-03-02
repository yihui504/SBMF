# tests/test_bug_type_engine.py
import pytest
from core.models import *
from core.bug_type_engine import BugTypeEngine

def test_derive_type_1_illegal_success():
    test_case = TestCase(
        test_id="test_1",
        operation="insert",
        slot_values={"dimension": 0},
        raw_parameters={},
        is_legal=False,
        scope=SlotScope.COLLECTION
    )
    execution_result = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        result_data=None,
        error=None,
        elapsed_seconds=0.1
    )

    derivation = BugTypeEngine.derive_bug_type(
        test_case=test_case,
        rule_result=None,
        execution_result=execution_result,
        error_has_root_cause=False,
        precondition_passed=True
    )

    assert derivation.bug_type == BugType.TYPE_1
    assert "非法操作未报错" in derivation.reason

def test_derive_type_2_bad_diagnostics():
    test_case = TestCase(
        test_id="test_2",
        operation="insert",
        slot_values={"dimension": 999999},
        raw_parameters={},
        is_legal=False,
        scope=SlotScope.COLLECTION
    )
    execution_result = ExecutionResult(
        status=ExecutionStatus.FAILURE,
        result_data=None,
        error=Exception("Invalid parameter"),
        elapsed_seconds=0.1
    )

    derivation = BugTypeEngine.derive_bug_type(
        test_case=test_case,
        rule_result=None,
        execution_result=execution_result,
        error_has_root_cause=False,
        precondition_passed=True
    )

    assert derivation.bug_type == BugType.TYPE_2

def test_derive_type_3_legal_failure():
    test_case = TestCase(
        test_id="test_3",
        operation="search",
        slot_values={"top_k": 10},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )
    execution_result = ExecutionResult(
        status=ExecutionStatus.FAILURE,
        result_data=None,
        error=Exception("Connection error"),
        elapsed_seconds=0.1
    )

    derivation = BugTypeEngine.derive_bug_type(
        test_case=test_case,
        rule_result=None,
        execution_result=execution_result,
        error_has_root_cause=True,
        precondition_passed=True
    )

    assert derivation.bug_type == BugType.TYPE_3

def test_derive_type_4_semantic_violation():
    from dataclasses import dataclass

    @dataclass
    class MockRuleEvaluationResult:
        overall_passed: bool = False

    test_case = TestCase(
        test_id="test_4",
        operation="search",
        slot_values={"top_k": 10},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )
    execution_result = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        result_data=None,
        error=None,
        elapsed_seconds=0.1
    )
    rule_result = MockRuleEvaluationResult(overall_passed=False)

    derivation = BugTypeEngine.derive_bug_type(
        test_case=test_case,
        rule_result=rule_result,
        execution_result=execution_result,
        error_has_root_cause=True,
        precondition_passed=True
    )

    assert derivation.bug_type == BugType.TYPE_4

def test_derive_not_a_bug():
    test_case = TestCase(
        test_id="test_5",
        operation="insert",
        slot_values={"dimension": 0},
        raw_parameters={},
        is_legal=False,
        scope=SlotScope.COLLECTION
    )
    execution_result = ExecutionResult(
        status=ExecutionStatus.FAILURE,
        result_data=None,
        error=Exception("dimension must be >= 1"),
        elapsed_seconds=0.1
    )

    derivation = BugTypeEngine.derive_bug_type(
        test_case=test_case,
        rule_result=None,
        execution_result=execution_result,
        error_has_root_cause=True,
        precondition_passed=True
    )

    assert derivation.bug_type is None
    assert "预期行为" in derivation.reason

def test_derive_precondition_failed():
    test_case = TestCase(
        test_id="test_6",
        operation="search",
        slot_values={"top_k": 10},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )
    execution_result = ExecutionResult(
        status=ExecutionStatus.FAILURE,
        result_data=None,
        error=None,
        elapsed_seconds=0.1
    )

    derivation = BugTypeEngine.derive_bug_type(
        test_case=test_case,
        rule_result=None,
        execution_result=execution_result,
        error_has_root_cause=True,
        precondition_passed=False  # Precondition failed
    )

    assert derivation.bug_type is None
    assert "预条件" in derivation.reason

def test_derive_timeout():
    test_case = TestCase(
        test_id="test_7",
        operation="search",
        slot_values={"top_k": 10},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )
    execution_result = ExecutionResult(
        status=ExecutionStatus.TIMEOUT,
        result_data=None,
        error=None,
        elapsed_seconds=30.0
    )

    derivation = BugTypeEngine.derive_bug_type(
        test_case=test_case,
        rule_result=None,
        execution_result=execution_result,
        error_has_root_cause=True,
        precondition_passed=True
    )

    assert derivation.bug_type == BugType.TYPE_3
