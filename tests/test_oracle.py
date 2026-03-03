"""
Tests for Oracle Layer.

Tests AST nodes, base types, and built-in Oracle checkers.
"""

import pytest
from oracle import (
    # AST Nodes
    ASTNodeType,
    ComparisonOperator,
    ASTNode,
    LiteralNode,
    ComparisonNode,
    FieldAccessNode,
    SlotReferenceNode,
    LogicalAndNode,
    LogicalOrNode,
    LogicalNotNode,
    slot_ref,
    field_access,
    literal,
    compare,
    logical_and,
    logical_or,
    logical_not,
    # Base Types
    OracleCategory,
    Severity,
    Precondition,
    TriggerCondition,
    ValidationLogic,
    OracleDefinition,
    OracleResult,
    TestCase,
    ExecutionResult,
    # Oracle Checker
    OracleChecker,
    OracleCheckerRegistry,
    register_oracle,
    get_oracle,
    get_all_oracles,
    get_oracles_by_category,
    # Built-in Checkers
    RangeConstraintOracle,
    EnumConstraintOracle,
    RelationalConstraintOracle,
    StatusValidationOracle,
)


# ================================================================
# AST Node Tests
# ================================================================

def test_literal_node():
    """Test literal node creation"""
    node = literal(42)
    assert isinstance(node, LiteralNode)
    assert node.value == 42
    assert node.node_type == ASTNodeType.LITERAL


def test_slot_reference_node():
    """Test slot reference node"""
    node = slot_ref("dimension", scope="COLLECTION")
    assert isinstance(node, SlotReferenceNode)
    assert node.slot_name == "dimension"
    assert node.scope == "COLLECTION"
    assert node.node_type == ASTNodeType.SLOT_REFERENCE


def test_field_access_node():
    """Test field access node"""
    node = field_access("result", "status")
    assert isinstance(node, FieldAccessNode)
    assert node.object_path == ["result", "status"]
    assert node.node_type == ASTNodeType.FIELD_ACCESS


def test_comparison_node():
    """Test comparison node"""
    left = slot_ref("dimension")
    right = literal(100)
    node = compare(left, ComparisonOperator.GT, right)
    assert isinstance(node, ComparisonNode)
    assert node.operator == ComparisonOperator.GT


def test_logical_and_node():
    """Test logical AND node"""
    node = logical_and(literal(True), literal(False))
    assert isinstance(node, LogicalAndNode)
    assert len(node.operands) == 2


def test_logical_or_node():
    """Test logical OR node"""
    node = logical_or(literal(True), literal(False))
    assert isinstance(node, LogicalOrNode)
    assert len(node.operands) == 2


def test_logical_not_node():
    """Test logical NOT node"""
    node = logical_not(literal(True))
    assert isinstance(node, LogicalNotNode)
    assert node.operand.value == True


# ================================================================
# Base Types Tests
# ================================================================

def test_oracle_definition():
    """Test OracleDefinition creation"""
    definition = OracleDefinition(
        oracle_id="test_oracle",
        name="Test Oracle",
        category=OracleCategory.CONSISTENCY,
        description="Test description",
        trigger_condition=TriggerCondition(),
        validation_logic=ValidationLogic(root=literal(True)),
        severity=Severity.HIGH,
        evidence_required=False
    )

    assert definition.oracle_id == "test_oracle"
    assert definition.category == OracleCategory.CONSISTENCY
    assert definition.severity == Severity.HIGH


def test_oracle_result():
    """Test OracleResult creation"""
    result = OracleResult(
        oracle_id="test_oracle",
        passed=True,
        details="Check passed"
    )

    assert result.oracle_id == "test_oracle"
    assert result.passed is True
    assert result.to_dict()["oracle_id"] == "test_oracle"


def test_test_case():
    """Test TestCase creation"""
    case = TestCase(
        test_id="test_001",
        operation="search",
        parameters={"ef": 128},
        slot_values={"dimension": 256}
    )

    assert case.test_id == "test_001"
    assert case.operation == "search"
    assert case.slot_values["dimension"] == 256


def test_execution_result():
    """Test ExecutionResult creation"""
    result = ExecutionResult(
        status="SUCCESS",
        data={"count": 10},
        execution_time=0.5
    )

    assert result.status == "SUCCESS"
    assert result.data["count"] == 10


# ================================================================
# Oracle Checker Registry Tests
# ================================================================

def test_oracle_checker_registry():
    """Test OracleCheckerRegistry"""
    registry = OracleCheckerRegistry()

    # Create a mock checker
    class MockChecker(OracleChecker):
        def get_definition(self):
            return OracleDefinition(
                oracle_id="mock",
                name="Mock",
                category=OracleCategory.CUSTOM,
                description="Mock oracle",
                trigger_condition=TriggerCondition(),
                validation_logic=ValidationLogic(root=literal(True)),
                severity=Severity.LOW
            )

        def check(self, test_case, result):
            return OracleResult(
                oracle_id="mock",
                passed=True,
                details="Mock check"
            )

    checker = MockChecker()

    # Register
    registry.register(checker)

    # Get
    retrieved = registry.get("mock")
    assert retrieved is checker

    # Get all
    all_checkers = registry.get_all()
    assert len(all_checkers) == 1

    # Get by category
    category_checkers = registry.get_by_category(OracleCategory.CUSTOM)
    assert len(category_checkers) == 1


def test_register_duplicate_oracle():
    """Test registering duplicate Oracle ID"""
    registry = OracleCheckerRegistry()

    class MockChecker(OracleChecker):
        def get_definition(self):
            return OracleDefinition(
                oracle_id="duplicate",
                name="Mock",
                category=OracleCategory.CUSTOM,
                description="Mock oracle",
                trigger_condition=TriggerCondition(),
                validation_logic=ValidationLogic(root=literal(True)),
                severity=Severity.LOW
            )

        def check(self, test_case, result):
            return OracleResult(oracle_id="duplicate", passed=True, details="")

    checker1 = MockChecker()
    checker2 = MockChecker()

    registry.register(checker1)

    # Should raise ValueError for duplicate
    with pytest.raises(ValueError, match="already registered"):
        registry.register(checker2)


# ================================================================
# Range Constraint Oracle Tests
# ================================================================

def test_range_oracle_pass():
    """Test range constraint Oracle - pass case"""
    oracle = RangeConstraintOracle(
        slot_name="dimension",
        min_value=1,
        max_value=2048
    )

    test_case = TestCase(
        test_id="test_001",
        operation="search",
        slot_values={"dimension": 512}
    )

    result = ExecutionResult(status="SUCCESS")

    oracle_result = oracle.check(test_case, result)

    assert oracle_result.passed is True
    assert "within range" in oracle_result.details.lower()


def test_range_oracle_fail_min():
    """Test range constraint Oracle - fail minimum"""
    oracle = RangeConstraintOracle(
        slot_name="dimension",
        min_value=1,
        max_value=2048
    )

    test_case = TestCase(
        test_id="test_001",
        operation="search",
        slot_values={"dimension": 0}
    )

    result = ExecutionResult(status="SUCCESS")

    oracle_result = oracle.check(test_case, result)

    assert oracle_result.passed is False
    assert oracle_result.violated_slots == ["dimension"]


def test_range_oracle_fail_max():
    """Test range constraint Oracle - fail maximum"""
    oracle = RangeConstraintOracle(
        slot_name="dimension",
        min_value=1,
        max_value=2048
    )

    test_case = TestCase(
        test_id="test_001",
        operation="search",
        slot_values={"dimension": 4096}
    )

    result = ExecutionResult(status="SUCCESS")

    oracle_result = oracle.check(test_case, result)

    assert oracle_result.passed is False
    assert oracle_result.violated_slots == ["dimension"]


def test_range_oracle_exclusive():
    """Test range constraint Oracle - exclusive bounds"""
    oracle = RangeConstraintOracle(
        slot_name="dimension",
        min_value=1,
        max_value=2048,
        inclusive_min=False,
        inclusive_max=False
    )

    # Test exclusive min
    test_case = TestCase(
        test_id="test_001",
        operation="search",
        slot_values={"dimension": 1}
    )

    result = ExecutionResult(status="SUCCESS")
    oracle_result = oracle.check(test_case, result)

    assert oracle_result.passed is False  # 1 is excluded


# ================================================================
# Enum Constraint Oracle Tests
# ================================================================

def test_enum_oracle_pass():
    """Test enum constraint Oracle - pass case"""
    oracle = EnumConstraintOracle(
        slot_name="metric_type",
        allowed_values=["L2", "IP", "COSINE"]
    )

    test_case = TestCase(
        test_id="test_001",
        operation="search",
        slot_values={"metric_type": "L2"}
    )

    result = ExecutionResult(status="SUCCESS")

    oracle_result = oracle.check(test_case, result)

    assert oracle_result.passed is True


def test_enum_oracle_fail():
    """Test enum constraint Oracle - fail case"""
    oracle = EnumConstraintOracle(
        slot_name="metric_type",
        allowed_values=["L2", "IP", "COSINE"]
    )

    test_case = TestCase(
        test_id="test_001",
        operation="search",
        slot_values={"metric_type": "INVALID"}
    )

    result = ExecutionResult(status="SUCCESS")

    oracle_result = oracle.check(test_case, result)

    assert oracle_result.passed is False
    assert oracle_result.violated_slots == ["metric_type"]


# ================================================================
# Relational Constraint Oracle Tests
# ================================================================

def test_relational_oracle_pass():
    """Test relational constraint Oracle - pass case"""
    oracle = RelationalConstraintOracle(
        left_slot="search_range",
        operator=ComparisonOperator.GE,
        right_slot="top_k"
    )

    test_case = TestCase(
        test_id="test_001",
        operation="search",
        slot_values={"search_range": 100, "top_k": 50}
    )

    result = ExecutionResult(status="SUCCESS")

    oracle_result = oracle.check(test_case, result)

    assert oracle_result.passed is True


def test_relational_oracle_fail():
    """Test relational constraint Oracle - fail case"""
    oracle = RelationalConstraintOracle(
        left_slot="search_range",
        operator=ComparisonOperator.GE,
        right_slot="top_k"
    )

    test_case = TestCase(
        test_id="test_001",
        operation="search",
        slot_values={"search_range": 50, "top_k": 100}
    )

    result = ExecutionResult(status="SUCCESS")

    oracle_result = oracle.check(test_case, result)

    assert oracle_result.passed is False
    assert oracle_result.violated_slots == ["search_range"]


def test_relational_oracle_all_operators():
    """Test relational constraint Oracle - all operators"""
    test_cases = [
        (ComparisonOperator.EQ, 100, 100, True),
        (ComparisonOperator.EQ, 100, 200, False),
        (ComparisonOperator.NE, 100, 200, True),
        (ComparisonOperator.NE, 100, 100, False),
        (ComparisonOperator.GT, 200, 100, True),
        (ComparisonOperator.GT, 100, 200, False),
        (ComparisonOperator.GE, 200, 100, True),
        (ComparisonOperator.GE, 100, 100, True),
        (ComparisonOperator.LT, 100, 200, True),
        (ComparisonOperator.LT, 200, 100, False),
        (ComparisonOperator.LE, 100, 200, True),
        (ComparisonOperator.LE, 200, 100, False),
    ]

    for op, left, right, expected_passed in test_cases:
        oracle = RelationalConstraintOracle(
            left_slot="a",
            operator=op,
            right_slot="b"
        )

        test_case = TestCase(
            test_id="test_001",
            operation="search",
            slot_values={"a": left, "b": right}
        )

        result = ExecutionResult(status="SUCCESS")
        oracle_result = oracle.check(test_case, result)

        assert oracle_result.passed == expected_passed, f"Failed for {op.value}: {left} vs {right}"


# ================================================================
# Status Validation Oracle Tests
# ================================================================

def test_status_oracle_success_expected():
    """Test status validation Oracle - expecting success"""
    oracle = StatusValidationOracle(expected_status="SUCCESS")

    test_case = TestCase(test_id="test_001", operation="search")

    result = ExecutionResult(status="SUCCESS")

    oracle_result = oracle.check(test_case, result)

    assert oracle_result.passed is True


def test_status_oracle_fail_when_expected_success():
    """Test status validation Oracle - fail when expecting success"""
    oracle = StatusValidationOracle(expected_status="SUCCESS")

    test_case = TestCase(test_id="test_001", operation="search")

    result = ExecutionResult(status="FAILURE")

    oracle_result = oracle.check(test_case, result)

    assert oracle_result.passed is False


def test_status_oracle_can_check_always_true():
    """Test that StatusValidationOracle can always check"""
    oracle = StatusValidationOracle()
    test_case = TestCase(test_id="test_001", operation="any_operation")

    assert oracle.can_check(test_case) is True


# ================================================================
# Integration Tests
# ================================================================

def test_multiple_oracles_same_test():
    """Test running multiple Oracle checkers on same test"""
    oracles = [
        RangeConstraintOracle("dimension", min_value=1, max_value=2048),
        EnumConstraintOracle("metric_type", allowed_values=["L2", "IP"]),
        RelationalConstraintOracle("search_range", ComparisonOperator.GE, "top_k"),
    ]

    test_case = TestCase(
        test_id="test_001",
        operation="search",
        slot_values={
            "dimension": 512,
            "metric_type": "L2",
            "search_range": 100,
            "top_k": 50
        }
    )

    result = ExecutionResult(status="SUCCESS")

    results = []
    for oracle in oracles:
        results.append(oracle.check(test_case, result))

    # All should pass
    assert all(r.passed for r in results)


def test_global_registry():
    """Test global Oracle registry functions"""
    # Create and register a checker
    class TestOracle(OracleChecker):
        def get_definition(self):
            return OracleDefinition(
                oracle_id="test_global",
                name="Test",
                category=OracleCategory.CUSTOM,
                description="Test",
                trigger_condition=TriggerCondition(),
                validation_logic=ValidationLogic(root=literal(True)),
                severity=Severity.LOW
            )

        def check(self, test_case, result):
            return OracleResult(oracle_id="test_global", passed=True, details="")

    oracle = TestOracle()
    register_oracle(oracle)

    # Get from registry
    retrieved = get_oracle("test_global")
    assert retrieved is oracle

    # Get all
    all_oracles = get_all_oracles()
    assert oracle in all_oracles

    # Get by category
    category_oracles = get_oracles_by_category(OracleCategory.CUSTOM)
    assert oracle in category_oracles
