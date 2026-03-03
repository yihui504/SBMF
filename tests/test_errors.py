"""
Tests for Contract error infrastructure.

Tests the exception hierarchy, ValidationLocation, ValidationIssue,
and DependencyCycle classes.
"""

import pytest
from contract.errors import (
    ContractError,
    ContractParseError,
    ContractValidationError,
    DependencyCycleError,
    PriorityConflictError,
    AmbiguousDependencyRefError,
    UndefinedDependencyRefError,
    ValidationLocation,
    ValidationIssue,
    DependencyCycle,
)


# ================================================================
# ContractError 基类测试
# ================================================================

def test_contract_error_is_exception():
    """Test that ContractError is an Exception subclass"""
    assert issubclass(ContractError, Exception)

    err = ContractError("Base error")
    assert str(err) == "Base error"


# ================================================================
# ContractParseError 测试
# ================================================================

def test_parse_error_basic():
    """Test ContractParseError without location"""
    err = ContractParseError("Missing required field: slot_name")

    assert err.message == "Missing required field: slot_name"
    assert err.location is None
    assert "Missing required field" in str(err)
    assert "slot_name" in str(err)


def test_parse_error_with_location():
    """Test ContractParseError with ValidationLocation"""
    loc = ValidationLocation(scope="COLLECTION", slot_name="dimension")
    err = ContractParseError("Type mismatch", location=loc)

    assert err.message == "Type mismatch"
    assert err.location == loc
    assert "scope:COLLECTION.slot:dimension" in str(err)
    assert "Type mismatch" in str(err)


def test_parse_error_with_full_location():
    """Test ContractParseError with complete location information"""
    loc = ValidationLocation(
        scope="COLLECTION",
        slot_name="dimension",
        rule_id="check_dim",
        field_path="rules[0].relational.operator"
    )
    err = ContractParseError("Invalid operator", location=loc)

    expected = "scope:COLLECTION.slot:dimension.rule:check_dim.rules[0].relational.operator"
    assert expected in str(err)


def test_parse_error_empty_location():
    """Test ContractParseError with empty ValidationLocation"""
    loc = ValidationLocation()
    err = ContractParseError("Unknown error", location=loc)

    assert str(err) == "<unknown>: Unknown error"


# ================================================================
# ValidationLocation 测试
# ================================================================

def test_validation_location_empty():
    """Test empty ValidationLocation"""
    loc = ValidationLocation()
    assert loc.scope is None
    assert loc.slot_name is None
    assert loc.rule_id is None
    assert loc.field_path is None
    assert loc.format() == "<unknown>"


def test_validation_location_scope_only():
    """Test ValidationLocation with scope only"""
    loc = ValidationLocation(scope="DATABASE")
    assert loc.format() == "scope:DATABASE"


def test_validation_location_scope_and_slot():
    """Test ValidationLocation with scope and slot_name"""
    loc = ValidationLocation(scope="COLLECTION", slot_name="dimension")
    assert loc.format() == "scope:COLLECTION.slot:dimension"


def test_validation_location_with_rule():
    """Test ValidationLocation with rule_id"""
    loc = ValidationLocation(
        scope="COLLECTION",
        slot_name="dimension",
        rule_id="check_range"
    )
    assert loc.format() == "scope:COLLECTION.slot:dimension.rule:check_range"


def test_validation_location_with_field_path():
    """Test ValidationLocation with field_path containing dots"""
    loc = ValidationLocation(
        scope="COLLECTION",
        slot_name="dimension",
        field_path="rules[0].relational.operator"
    )
    result = loc.format()
    assert "scope:COLLECTION" in result
    assert "slot:dimension" in result
    assert "rules[0].relational.operator" in result


def test_validation_location_complete():
    """Test ValidationLocation with all fields"""
    loc = ValidationLocation(
        scope="INDEX",
        slot_name="ef",
        rule_id="ef_constraint",
        field_path="rules[0].range.min_value"
    )
    expected = "scope:INDEX.slot:ef.rule:ef_constraint.rules[0].range.min_value"
    assert loc.format() == expected


# ================================================================
# ValidationIssue 测试
# ================================================================

def test_validation_issue_basic():
    """Test ValidationIssue creation"""
    loc = ValidationLocation(slot_name="dimension")
    issue = ValidationIssue(
        error_code="DUP_SLOT",
        message="Duplicate slot name",
        location=loc
    )

    assert issue.error_code == "DUP_SLOT"
    assert issue.message == "Duplicate slot name"
    assert issue.location == loc
    assert issue.severity == "ERROR"  # default


def test_validation_issue_with_warning():
    """Test ValidationIssue with WARNING severity"""
    loc = ValidationLocation(slot_name="top_k")
    issue = ValidationIssue(
        error_code="LOW_PRIORITY",
        message="Priority is high (>200)",
        location=loc,
        severity="WARNING"
    )

    assert issue.severity == "WARNING"


def test_validation_issue_format():
    """Test ValidationIssue.format() output"""
    loc = ValidationLocation(scope="COLLECTION", slot_name="dimension")
    issue = ValidationIssue(
        error_code="DUP_SLOT",
        message="Duplicate slot name",
        location=loc
    )

    formatted = issue.format()
    assert "[DUP_SLOT]" in formatted
    assert "scope:COLLECTION.slot:dimension" in formatted
    assert "Duplicate slot name" in formatted


def test_validation_issue_format_empty_location():
    """Test ValidationIssue.format() with empty location"""
    loc = ValidationLocation()
    issue = ValidationIssue(
        error_code="GLOBAL_ERROR",
        message="Generic error",
        location=loc
    )

    formatted = issue.format()
    assert "[GLOBAL_ERROR]" in formatted
    assert "<unknown>:" in formatted


def test_validation_issue_to_dict():
    """Test ValidationIssue.to_dict() output"""
    loc = ValidationLocation(
        scope="COLLECTION",
        slot_name="dimension",
        rule_id="check_range",
        field_path="rules[0].relational.operator"
    )
    issue = ValidationIssue(
        error_code="DUP_SLOT",
        message="Duplicate slot",
        location=loc,
        severity="ERROR"
    )

    result = issue.to_dict()
    assert result == {
        "error_code": "DUP_SLOT",
        "message": "Duplicate slot",
        "location": {
            "scope": "COLLECTION",
            "slot_name": "dimension",
            "rule_id": "check_range",
            "field_path": "rules[0].relational.operator",
        },
        "severity": "ERROR",
    }


def test_validation_issue_to_dict_minimal():
    """Test ValidationIssue.to_dict() with minimal location"""
    loc = ValidationLocation(slot_name="top_k")
    issue = ValidationIssue(
        error_code="INVALID_RANGE",
        message="Range invalid",
        location=loc
    )

    result = issue.to_dict()
    assert result["error_code"] == "INVALID_RANGE"
    assert result["location"]["scope"] is None
    assert result["location"]["slot_name"] == "top_k"
    assert result["location"]["rule_id"] is None
    assert result["location"]["field_path"] is None


# ================================================================
# ContractValidationError 测试
# ================================================================

def test_validation_error_single_issue():
    """Test ContractValidationError with single issue"""
    issues = [
        ValidationIssue(
            error_code="DUP_SLOT",
            message="Duplicate slot",
            location=ValidationLocation(slot_name="x")
        )
    ]
    err = ContractValidationError(issues)

    assert len(err.issues) == 1
    assert "1 issue(s)" in str(err)
    assert "[DUP_SLOT]" in str(err)


def test_validation_error_multiple_issues():
    """Test ContractValidationError with multiple issues"""
    issues = [
        ValidationIssue(
            error_code="DUP_SLOT",
            message="Duplicate slot",
            location=ValidationLocation(slot_name="x")
        ),
        ValidationIssue(
            error_code="CYCLE",
            message="Dependency cycle",
            location=ValidationLocation()
        )
    ]
    err = ContractValidationError(issues)

    assert len(err.issues) == 2
    assert "2 issue(s)" in str(err)
    assert "[DUP_SLOT]" in str(err)
    assert "[CYCLE]" in str(err)


def test_validation_error_get_errors():
    """Test get_errors() filters ERROR severity"""
    issues = [
        ValidationIssue("ERR1", "Error 1", ValidationLocation(), "ERROR"),
        ValidationIssue("WARN1", "Warning 1", ValidationLocation(), "WARNING"),
        ValidationIssue("ERR2", "Error 2", ValidationLocation(), "ERROR"),
    ]
    err = ContractValidationError(issues)

    errors = err.get_errors()
    assert len(errors) == 2
    assert all(i.severity == "ERROR" for i in errors)


def test_validation_error_get_warnings():
    """Test get_warnings() filters WARNING severity"""
    issues = [
        ValidationIssue("ERR1", "Error 1", ValidationLocation(), "ERROR"),
        ValidationIssue("WARN1", "Warning 1", ValidationLocation(), "WARNING"),
        ValidationIssue("WARN2", "Warning 2", ValidationLocation(), "WARNING"),
    ]
    err = ContractValidationError(issues)

    warnings = err.get_warnings()
    assert len(warnings) == 2
    assert all(i.severity == "WARNING" for i in warnings)


def test_validation_error_issues_is_tuple():
    """Test that ContractValidationError.issues is a tuple (immutable)"""
    issues = [
        ValidationIssue("ERR1", "Error 1", ValidationLocation()),
        ValidationIssue("ERR2", "Error 2", ValidationLocation()),
    ]
    err = ContractValidationError(issues)

    # issues 属性应该是 tuple
    assert isinstance(err.issues, tuple)
    assert len(err.issues) == 2


def test_validation_error_issues_cannot_modify():
    """Test that ContractValidationError.issues is immutable (tuple)"""
    issues = [
        ValidationIssue("ERR1", "Error 1", ValidationLocation()),
    ]
    err = ContractValidationError(issues)

    # tuple 没有 append 方法，应该抛出 AttributeError
    with pytest.raises(AttributeError):
        err.issues.append(ValidationIssue("ERR2", "Error 2", ValidationLocation()))

    # 验证原始输入 list 被转换为 tuple
    assert isinstance(err.issues, tuple)


# ================================================================
# DependencyCycle 测试
# ================================================================

def test_dependency_cycle_creation():
    """Test DependencyCycle creation"""
    cycle = DependencyCycle([("COLLECTION", "a"), ("COLLECTION", "b")])

    assert cycle.cycle_path == [("COLLECTION", "a"), ("COLLECTION", "b")]


def test_dependency_cycle_format_two_nodes():
    """Test DependencyCycle.format() with two nodes"""
    cycle = DependencyCycle([("COLLECTION", "a"), ("COLLECTION", "b")])

    formatted = cycle.format()
    assert formatted == "COLLECTION.a → COLLECTION.b → COLLECTION.a"


def test_dependency_cycle_format_three_nodes():
    """Test DependencyCycle.format() with three nodes"""
    cycle = DependencyCycle([
        ("COLLECTION", "a"),
        ("COLLECTION", "b"),
        ("INDEX", "ef")
    ])

    formatted = cycle.format()
    assert "COLLECTION.a →" in formatted
    assert "COLLECTION.b →" in formatted
    assert "INDEX.ef →" in formatted
    assert formatted.endswith("→ COLLECTION.a")  # 闭环


def test_dependency_cycle_format_multi_scope():
    """Test DependencyCycle.format() with mixed scopes"""
    cycle = DependencyCycle([
        ("COLLECTION", "dimension"),
        ("COLLECTION", "top_k"),
        ("INDEX", "ef")
    ])

    formatted = cycle.format()
    assert "COLLECTION.dimension →" in formatted
    assert "COLLECTION.top_k →" in formatted
    assert "INDEX.ef →" in formatted


def test_dependency_cycle_to_validation_issue():
    """Test DependencyCycle.to_validation_issue()"""
    cycle = DependencyCycle([("COLLECTION", "x"), ("COLLECTION", "y")])

    issue = cycle.to_validation_issue()

    assert issue.error_code == "DEPENDENCY_CYCLE"
    assert "COLLECTION.x → COLLECTION.y → COLLECTION.x" in issue.message
    assert issue.severity == "ERROR"
    assert issue.location.format() == "<unknown>"  # 循环无单一位置


def test_dependency_cycle_empty_path():
    """Test DependencyCycle with empty path (edge case)"""
    cycle = DependencyCycle([])

    formatted = cycle.format()
    # 空路径应返回空字符串或仅闭环（实际使用中不应发生）
    assert formatted == "" or formatted.endswith("→ ")


# ================================================================
# DependencyCycleError 测试
# ================================================================

def test_dependency_cycle_error_creation():
    """Test DependencyCycleError creation"""
    cycle = DependencyCycle([("COLLECTION", "a"), ("COLLECTION", "b")])
    err = DependencyCycleError(cycle)

    assert err.cycle == cycle
    assert len(err.issues) == 1
    assert err.issues[0].error_code == "DEPENDENCY_CYCLE"


def test_dependency_cycle_error_message():
    """Test DependencyCycleError string representation"""
    cycle = DependencyCycle([("COLLECTION", "a"), ("COLLECTION", "b")])
    err = DependencyCycleError(cycle)

    err_str = str(err)
    assert "1 issue(s)" in err_str
    assert "[DEPENDENCY_CYCLE]" in err_str
    assert "COLLECTION.a → COLLECTION.b → COLLECTION.a" in err_str


# ================================================================
# PriorityConflictError 测试
# ================================================================

def test_priority_conflict_error_single():
    """Test PriorityConflictError with single conflict"""
    err = PriorityConflictError(
        slot_name="dimension",
        conflicts=[(10, ["check_dim_1", "check_dim_2"])]
    )

    assert err.slot_name == "dimension"
    assert len(err.issues) == 1
    assert err.issues[0].error_code == "PRIORITY_CONFLICT"


def test_priority_conflict_error_multiple():
    """Test PriorityConflictError with multiple conflicts"""
    err = PriorityConflictError(
        slot_name="top_k",
        conflicts=[
            (50, ["check_top_k_1", "check_top_k_2"]),
            (100, ["default_check_1", "default_check_2", "default_check_3"])
        ]
    )

    assert len(err.issues) == 2
    assert err.issues[0].message.endswith("have same priority 50")
    assert err.issues[1].message.endswith("have same priority 100")


def test_priority_conflict_error_message():
    """Test PriorityConflictError string representation"""
    err = PriorityConflictError(
        slot_name="dimension",
        conflicts=[(10, ["rule_a", "rule_b"])]
    )

    err_str = str(err)
    assert "1 issue(s)" in err_str  # 单个 conflicts 列表产生 1 个 issue
    assert "[PRIORITY_CONFLICT]" in err_str
    assert "slot:dimension" in err_str


def test_priority_conflict_error_location():
    """Test PriorityConflictError sets correct location"""
    err = PriorityConflictError(
        slot_name="ef",
        conflicts=[(20, ["ef_rule_1", "ef_rule_2"])]
    )

    issue = err.issues[0]
    assert issue.location.slot_name == "ef"
    assert issue.location.format() == "slot:ef"


# ================================================================
# UndefinedDependencyRefError 测试
# ================================================================

def test_undefined_dependency_ref_error():
    """Test UndefinedDependencyRefError creation and message"""
    err = UndefinedDependencyRefError(
        ref_name="unknown_slot",
        ref_scope="COLLECTION",
        source_slot="dimension"
    )

    assert err.ref_name == "unknown_slot"
    assert err.ref_scope == "COLLECTION"
    assert err.source_slot == "dimension"

    err_str = str(err)
    assert "1 issue(s)" in err_str
    assert "[UNDEFINED_DEPENDENCY_REF]" in err_str
    assert "undefined slot 'unknown_slot'" in err_str
    assert "COLLECTION" in err_str


# ================================================================
# 异常层次验证
# ================================================================

def test_exception_hierarchy():
    """Test that all custom exceptions inherit from ContractError"""
    assert issubclass(ContractParseError, ContractError)
    assert issubclass(ContractValidationError, ContractError)
    assert issubclass(DependencyCycleError, ContractValidationError)
    assert issubclass(PriorityConflictError, ContractValidationError)
    assert issubclass(AmbiguousDependencyRefError, ContractValidationError)
    assert issubclass(UndefinedDependencyRefError, ContractValidationError)


# ================================================================
# 可捕获性测试
# ================================================================

def test_catch_as_contract_error():
    """Test that specific errors can be caught as ContractError"""
    try:
        raise ContractParseError("Test error")
    except ContractError as e:
        assert isinstance(e, ContractParseError)
        assert str(e) == "Test error"


def test_catch_validation_error_as_contract_error():
    """Test that ContractValidationError can be caught as ContractError"""
    issues = [ValidationIssue("TEST", "Test", ValidationLocation())]
    try:
        raise ContractValidationError(issues)
    except ContractError as e:
        assert isinstance(e, ContractValidationError)
