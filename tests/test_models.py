"""
Test module for core models enum types.

This module tests all enum type definitions in core/models.py following TDD principles.
"""

import pytest
from enum import Enum


class TestSlotType:
    """Test SlotType enum"""

    def test_slot_type_exists(self):
        """Test that SlotType enum can be imported"""
        from core.models import SlotType
        assert SlotType is not None

    def test_slot_type_values(self):
        """Test that SlotType has all required values"""
        from core.models import SlotType
        assert SlotType.INTEGER.value == "integer"
        assert SlotType.FLOAT.value == "float"
        assert SlotType.STRING.value == "string"
        assert SlotType.ENUM.value == "enum"
        assert SlotType.BOOLEAN.value == "boolean"
        assert SlotType.VECTOR.value == "vector"

    def test_slot_type_is_enum(self):
        """Test that SlotType is an Enum"""
        from core.models import SlotType
        assert issubclass(SlotType, Enum)


class TestSlotScope:
    """Test SlotScope enum"""

    def test_slot_scope_exists(self):
        """Test that SlotScope enum can be imported"""
        from core.models import SlotScope
        assert SlotScope is not None

    def test_slot_scope_values(self):
        """Test that SlotScope has all required values"""
        from core.models import SlotScope
        assert SlotScope.DATABASE.value == "DATABASE"
        assert SlotScope.COLLECTION.value == "COLLECTION"
        assert SlotScope.PARTITION.value == "PARTITION"
        assert SlotScope.INDEX.value == "INDEX"
        assert SlotScope.REPLICA.value == "REPLICA"

    def test_slot_scope_is_enum(self):
        """Test that SlotScope is an Enum"""
        from core.models import SlotScope
        assert issubclass(SlotScope, Enum)


class TestBugType:
    """Test BugType enum"""

    def test_bug_type_exists(self):
        """Test that BugType enum can be imported"""
        from core.models import BugType
        assert BugType is not None

    def test_bug_type_values(self):
        """Test that BugType has all required values"""
        from core.models import BugType
        assert BugType.TYPE_1.value == "TYPE_1"
        assert BugType.TYPE_2.value == "TYPE_2"
        assert BugType.TYPE_3.value == "TYPE_3"
        assert BugType.TYPE_4.value == "TYPE_4"

    def test_bug_type_is_enum(self):
        """Test that BugType is an Enum"""
        from core.models import BugType
        assert issubclass(BugType, Enum)


class TestExecutionStatus:
    """Test ExecutionStatus enum"""

    def test_execution_status_exists(self):
        """Test that ExecutionStatus enum can be imported"""
        from core.models import ExecutionStatus
        assert ExecutionStatus is not None

    def test_execution_status_values(self):
        """Test that ExecutionStatus has all required values"""
        from core.models import ExecutionStatus
        assert ExecutionStatus.SUCCESS.value == "SUCCESS"
        assert ExecutionStatus.FAILURE.value == "FAILURE"
        assert ExecutionStatus.CRASH.value == "CRASH"
        assert ExecutionStatus.TIMEOUT.value == "TIMEOUT"
        assert ExecutionStatus.PRECONDITION_FAILED.value == "PRECONDITION_FAILED"

    def test_execution_status_is_enum(self):
        """Test that ExecutionStatus is an Enum"""
        from core.models import ExecutionStatus
        assert issubclass(ExecutionStatus, Enum)


class TestSeverity:
    """Test Severity enum"""

    def test_severity_exists(self):
        """Test that Severity enum can be imported"""
        from core.models import Severity
        assert Severity is not None

    def test_severity_values(self):
        """Test that Severity has all required values"""
        from core.models import Severity
        assert Severity.HIGH.value == "HIGH"
        assert Severity.MEDIUM.value == "MEDIUM"
        assert Severity.LOW.value == "LOW"

    def test_severity_is_enum(self):
        """Test that Severity is an Enum"""
        from core.models import Severity
        assert issubclass(Severity, Enum)


class TestErrorCategory:
    """Test ErrorCategory enum"""

    def test_error_category_exists(self):
        """Test that ErrorCategory enum can be imported"""
        from core.models import ErrorCategory
        assert ErrorCategory is not None

    def test_error_category_values(self):
        """Test that ErrorCategory has all required values"""
        from core.models import ErrorCategory
        assert ErrorCategory.INFRA_SUSPECT.value == "infra_suspect"
        assert ErrorCategory.PRODUCT_SUSPECT.value == "product_suspect"
        assert ErrorCategory.PRECONDITION_FAILED.value == "precondition_failed"

    def test_error_category_is_enum(self):
        """Test that ErrorCategory is an Enum"""
        from core.models import ErrorCategory
        assert issubclass(ErrorCategory, Enum)


class TestOracleCategory:
    """Test OracleCategory enum"""

    def test_oracle_category_exists(self):
        """Test that OracleCategory enum can be imported"""
        from core.models import OracleCategory
        assert OracleCategory is not None

    def test_oracle_category_values(self):
        """Test that OracleCategory has all required values"""
        from core.models import OracleCategory
        assert OracleCategory.MONOTONICITY.value == "monotonicity"
        assert OracleCategory.CONSISTENCY.value == "consistency"
        assert OracleCategory.CORRECTNESS.value == "correctness"
        assert OracleCategory.PERFORMANCE.value == "performance"

    def test_oracle_category_is_enum(self):
        """Test that OracleCategory is an Enum"""
        from core.models import OracleCategory
        assert issubclass(OracleCategory, Enum)


class TestASTNodeType:
    """Test ASTNodeType enum"""

    def test_ast_node_type_exists(self):
        """Test that ASTNodeType enum can be imported"""
        from core.models import ASTNodeType
        assert ASTNodeType is not None

    def test_ast_node_type_values(self):
        """Test that ASTNodeType has all required values"""
        from core.models import ASTNodeType
        assert ASTNodeType.COMPARISON.value == "comparison"
        assert ASTNodeType.FIELD_ACCESS.value == "field_access"
        assert ASTNodeType.SLOT_REFERENCE.value == "slot_reference"
        assert ASTNodeType.FILTER_VALIDATION.value == "filter_validation"
        assert ASTNodeType.LOGICAL_AND.value == "logical_and"
        assert ASTNodeType.LOGICAL_OR.value == "logical_or"
        assert ASTNodeType.LOGICAL_NOT.value == "logical_not"

    def test_ast_node_type_is_enum(self):
        """Test that ASTNodeType is an Enum"""
        from core.models import ASTNodeType
        assert issubclass(ASTNodeType, Enum)


class TestComparisonOperator:
    """Test ComparisonOperator enum"""

    def test_comparison_operator_exists(self):
        """Test that ComparisonOperator enum can be imported"""
        from core.models import ComparisonOperator
        assert ComparisonOperator is not None

    def test_comparison_operator_values(self):
        """Test that ComparisonOperator has all required values"""
        from core.models import ComparisonOperator
        assert ComparisonOperator.LESS_THAN.value == "<"
        assert ComparisonOperator.LESS_THAN_OR_EQUAL.value == "<="
        assert ComparisonOperator.GREATER_THAN.value == ">"
        assert ComparisonOperator.GREATER_THAN_OR_EQUAL.value == ">="
        assert ComparisonOperator.EQUAL.value == "=="
        assert ComparisonOperator.NOT_EQUAL.value == "!="

    def test_comparison_operator_is_enum(self):
        """Test that ComparisonOperator is an Enum"""
        from core.models import ComparisonOperator
        assert issubclass(ComparisonOperator, Enum)


class TestEvidenceSource:
    """Test EvidenceSource enum"""

    def test_evidence_source_exists(self):
        """Test that EvidenceSource enum can be imported"""
        from core.models import EvidenceSource
        assert EvidenceSource is not None

    def test_evidence_source_values(self):
        """Test that EvidenceSource has all required values"""
        from core.models import EvidenceSource
        assert EvidenceSource.OFFICIAL_DOCUMENTATION.value == "official_documentation"
        assert EvidenceSource.CODE_ANALYSIS.value == "code_analysis"
        assert EvidenceSource.LLM_DISCOVERED.value == "llm_discovered"
        assert EvidenceSource.MANUAL.value == "manual"

    def test_evidence_source_is_enum(self):
        """Test that EvidenceSource is an Enum"""
        from core.models import EvidenceSource
        assert issubclass(EvidenceSource, Enum)


class TestReviewStatus:
    """Test ReviewStatus enum"""

    def test_review_status_exists(self):
        """Test that ReviewStatus enum can be imported"""
        from core.models import ReviewStatus
        assert ReviewStatus is not None

    def test_review_status_values(self):
        """Test that ReviewStatus has all required values"""
        from core.models import ReviewStatus
        assert ReviewStatus.PENDING.value == "pending"
        assert ReviewStatus.APPROVED.value == "approved"
        assert ReviewStatus.REJECTED.value == "rejected"

    def test_review_status_is_enum(self):
        """Test that ReviewStatus is an Enum"""
        from core.models import ReviewStatus
        assert issubclass(ReviewStatus, Enum)


class TestRuleType:
    """Test RuleType enum"""

    def test_rule_type_exists(self):
        """Test that RuleType enum can be imported"""
        from core.models import RuleType
        assert RuleType is not None

    def test_rule_type_values(self):
        """Test that RuleType has all required values"""
        from core.models import RuleType
        assert RuleType.RELATIONAL.value == "relational"
        assert RuleType.RANGE.value == "range"
        assert RuleType.CONDITIONAL.value == "conditional"
        assert RuleType.ENUM.value == "enum"

    def test_rule_type_is_enum(self):
        """Test that RuleType is an Enum"""
        from core.models import RuleType
        assert issubclass(RuleType, Enum)


class TestDataclassModels:
    """Test dataclass models"""

    def test_slot_dataclass(self):
        """Test Slot and CoreSlot dataclass"""
        from core.models import Slot, CoreSlot, SlotType, SlotScope, SlotDependency

        slot = CoreSlot(
            slot_name="dimension",
            description="向量维度",
            type=SlotType.INTEGER,
            scope=SlotScope.COLLECTION,
            depends_on=[]
        )

        assert slot.slot_name == "dimension"
        assert slot.type == SlotType.INTEGER
        assert slot.scope == SlotScope.COLLECTION
        assert slot.description == "向量维度"
        assert slot.depends_on == []
        assert slot.constraints is None

    def test_slot_dependency_dataclass(self):
        """Test SlotDependency dataclass"""
        from core.models import SlotDependency

        dep = SlotDependency(slot_name="other_slot", reason="depends on this")
        assert dep.slot_name == "other_slot"
        assert dep.reason == "depends on this"

    def test_slot_constraints_dataclass(self):
        """Test SlotConstraints dataclass"""
        from core.models import SlotConstraints, RangeConstraint, EnumConstraint

        # Test with range constraint
        range_constraint = RangeConstraint(min=0, max=100, inclusive=True)
        constraints = SlotConstraints(range=range_constraint)
        assert constraints.range.min == 0
        assert constraints.range.max == 100
        assert constraints.range.inclusive is True
        assert constraints.enum is None

        # Test with enum constraint
        enum_constraint = EnumConstraint(values=["a", "b", "c"])
        enum_constraints = SlotConstraints(enum=enum_constraint)
        assert enum_constraints.enum.values == ["a", "b", "c"]
        assert enum_constraints.range is None

    def test_rule_dataclass(self):
        """Test Rule and RelationalRule dataclass"""
        from core.models import Rule, RelationalRule, RuleType, Severity, ComparisonOperator

        rule = RelationalRule(
            rule_id="test_rule",
            type=RuleType.RELATIONAL,
            severity=Severity.HIGH,
            enabled=True,
            priority=10,
            operator=ComparisonOperator.GREATER_THAN_OR_EQUAL,
            reference_slot="top_k",
            error_message="test error"
        )

        assert rule.operator == ComparisonOperator.GREATER_THAN_OR_EQUAL
        assert rule.priority == 10
        assert rule.rule_id == "test_rule"
        assert rule.type == RuleType.RELATIONAL
        assert rule.severity == Severity.HIGH
        assert rule.enabled is True
        assert rule.reference_slot == "top_k"
        assert rule.error_message == "test error"

    def test_contract_dataclass(self):
        """Test Contract dataclass"""
        from core.models import Contract, CoreSlot, SlotType, SlotScope

        slot1 = CoreSlot(
            slot_name="dimension",
            description="向量维度",
            type=SlotType.INTEGER,
            scope=SlotScope.COLLECTION,
            depends_on=[]
        )

        contract = Contract(
            database_name="test_db",
            version="1.0.0",
            core_slots=[slot1]
        )

        assert contract.database_name == "test_db"
        assert contract.version == "1.0.0"
        assert len(contract.core_slots) == 1
        assert contract.core_slots[0].slot_name == "dimension"

    def test_testcase_dataclass(self):
        """Test TestCase dataclass"""
        from core.models import TestCase, SlotScope

        testcase = TestCase(
            test_id="test_001",
            operation="create_collection",
            slot_values={"dimension": 128, "metric_type": "L2"},
            raw_parameters={"collection_name": "test", "dimension": 128},
            is_legal=True,
            scope=SlotScope.COLLECTION
        )

        assert testcase.test_id == "test_001"
        assert testcase.operation == "create_collection"
        assert testcase.slot_values == {"dimension": 128, "metric_type": "L2"}
        assert testcase.raw_parameters == {"collection_name": "test", "dimension": 128}
        assert testcase.is_legal is True
        assert testcase.scope == SlotScope.COLLECTION
        assert testcase.get_slot_value("dimension") == 128
        assert testcase.get_slot_value("nonexistent") is None

    def test_execution_result_dataclass(self):
        """Test ExecutionResult dataclass"""
        from core.models import ExecutionResult, ExecutionStatus

        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            result_data={"collection_id": "123"},
            error=None,
            elapsed_seconds=1.5
        )

        assert result.status == ExecutionStatus.SUCCESS
        assert result.result_data == {"collection_id": "123"}
        assert result.error is None
        assert result.elapsed_seconds == 1.5

    def test_gate_result_dataclass(self):
        """Test GateResult dataclass"""
        from core.models import GateResult

        gate_result = GateResult(
            passed=True,
            reason="All checks passed"
        )

        assert gate_result.passed is True
        assert gate_result.reason == "All checks passed"
