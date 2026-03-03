"""
Tests for Contract Semantic Validator.

Tests the SemanticValidator class which performs semantic validation
and normalization.
"""

import pytest
from pathlib import Path
from contract.validator import ContractSchemaValidator
from contract.semantic_validator import SemanticValidator
from contract.schema import (
    ValidatedRawContract,
    NormalizedSlot,
    NormalizedRule,
)
from contract.types import NormalizedRelationalRule
from contract.errors import ContractParseError, ContractValidationError
from contract.types import SlotKey, SlotReference


# ================================================================
# Valid test data
# ================================================================

VALID_BASIC = {
    "database_name": "test_db",
    "version": "1.0",
    "core_slots": [
        {
            "slot_name": "dimension",
            "description": "Vector dimension",
            "type": "integer",
            "scope": "COLLECTION",
            "depends_on": []
        }
    ]
}

VALID_WITH_DEPENDENCIES = {
    "core_slots": [
        {
            "slot_name": "dimension",
            "description": "Vector dimension",
            "type": "integer",
            "scope": "COLLECTION",
            "depends_on": []
        },
        {
            "slot_name": "top_k",
            "description": "Top K",
            "type": "integer",
            "scope": "COLLECTION",
            "depends_on": [{"slot_name": "dimension", "reason": "depends on dimension"}]
        }
    ]
}

VALID_WITH_RULES = {
    "core_slots": [
        {
            "slot_name": "top_k",
            "description": "Top K results",
            "type": "integer",
            "scope": "COLLECTION",
            "depends_on": []
        },
        {
            "slot_name": "search_range",
            "description": "Search range",
            "type": "integer",
            "scope": "COLLECTION",
            "depends_on": [],
            "rules": [
                {
                    "rule_id": "range_check",
                    "type": "relational",
                    "severity": "HIGH",
                    "enabled": True,
                    "relational": {
                        "operator": ">=",
                        "reference_slot": "top_k",
                        "error_message": "search_range must be >= top_k"
                    }
                }
            ]
        }
    ]
}


# ================================================================
# SemanticValidator 基础测试
# ================================================================

def test_semantic_validator_init():
    """Test SemanticValidator instantiation"""
    validator = SemanticValidator()
    assert validator is not None


# ================================================================
# 端到端测试：Parser + Schema + Semantic
# ================================================================

def test_valid_contract_passes_semantic_validation():
    """Test that valid contract passes semantic validation"""
    # Step 1: Schema validation
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(VALID_BASIC)

    # Step 2: Semantic validation
    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    assert result.database_name == "test_db"
    assert result.version == "1.0"
    assert len(result.core_slots) == 1
    assert result.core_slots[0].slot_name == "dimension"


def test_valid_contract_with_dependencies():
    """Test semantic validation with valid dependencies"""
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(VALID_WITH_DEPENDENCIES)

    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    assert len(result.core_slots) == 2
    assert result.core_slots[1].slot_name == "top_k"
    assert len(result.core_slots[1].depends_on) == 1
    assert result.core_slots[1].depends_on[0].slot_name == "dimension"


def test_valid_contract_with_rules():
    """Test semantic validation with rules"""
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(VALID_WITH_RULES)

    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    assert len(result.core_slots) == 2
    # Find the slot with rules (search_range)
    search_range = next(s for s in result.core_slots if s.slot_name == "search_range")
    assert len(search_range.rules) == 1
    rule = search_range.rules[0]
    assert rule.rule_id == "range_check"
    assert rule.is_relational is True


# ================================================================
# 重复 slot 检测测试
# ================================================================

def test_duplicate_slots_same_scope():
    """Test that duplicate slots in same scope are detected"""
    data = {
        "core_slots": [
            {
                "slot_name": "dimension",
                "description": "First",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": []
            },
            {
                "slot_name": "dimension",
                "description": "Duplicate",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": []
            }
        ]
    }

    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    with pytest.raises(ContractValidationError) as exc_info:
        semantic_validator.validate(validated)

    assert "DUPLICATE_SLOT" in str(exc_info.value)
    assert "dimension" in str(exc_info.value)


def test_duplicate_slots_different_scope_allowed():
    """Test that duplicate slots in different scopes are allowed"""
    data = {
        "core_slots": [
            {
                "slot_name": "name",
                "description": "Database name",
                "type": "string",
                "scope": "DATABASE",
                "depends_on": []
            },
            {
                "slot_name": "name",
                "description": "Collection name",
                "type": "string",
                "scope": "COLLECTION",
                "depends_on": []
            }
        ]
    }

    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    # 两个 name slot 在不同 scope，应该通过
    assert len(result.core_slots) == 2


# ================================================================
# 引用存在性检查测试
# ================================================================

def test_undefined_dependency_reference():
    """Test that undefined dependency references are detected"""
    data = {
        "core_slots": [
            {
                "slot_name": "top_k",
                "description": "Top K",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": ["nonexistent_slot"]
            }
        ]
    }

    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    with pytest.raises(ContractValidationError) as exc_info:
        semantic_validator.validate(validated)

    assert "UNDEFINED_DEPENDENCY_REF" in str(exc_info.value)
    assert "nonexistent_slot" in str(exc_info.value)


def test_undefined_reference_slot():
    """Test that undefined reference_slot in rules is detected"""
    data = {
        "core_slots": [
            {
                "slot_name": "search_range",
                "description": "Search range",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "test_rule",
                        "type": "relational",
                        "severity": "HIGH",
                        "enabled": True,
                        "relational": {
                            "operator": ">=",
                            "reference_slot": "nonexistent",
                            "error_message": "test"
                        }
                    }
                ]
            }
        ]
    }

    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    with pytest.raises(ContractValidationError) as exc_info:
        semantic_validator.validate(validated)

    assert "UNDEFINED_REFERENCE_SLOT" in str(exc_info.value)
    assert "nonexistent" in str(exc_info.value)


def test_valid_references_pass():
    """Test that valid references pass validation"""
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(VALID_WITH_DEPENDENCIES)

    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    # 应该通过验证
    assert result.core_slots[1].depends_on[0].slot_name == "dimension"


# ================================================================
# 标准化测试
# ================================================================

def test_depends_on_normalization():
    """Test that depends_on is normalized to SlotReference"""
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(VALID_WITH_DEPENDENCIES)

    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    top_k = result.core_slots[1]
    assert len(top_k.depends_on) == 1
    dep = top_k.depends_on[0]
    assert isinstance(dep, SlotReference)
    assert dep.slot_name == "dimension"
    assert dep.scope == "COLLECTION"
    assert dep.reason == "depends on dimension"


def test_rules_normalization():
    """Test that rules are normalized to NormalizedRule"""
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(VALID_WITH_RULES)

    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    # Find the slot with rules (search_range)
    slot = next(s for s in result.core_slots if s.slot_name == "search_range")
    assert len(slot.rules) == 1
    rule = slot.rules[0]
    assert isinstance(rule, NormalizedRule)
    assert rule.rule_id == "range_check"
    assert rule.is_relational is True

    body = rule.body
    assert isinstance(body, NormalizedRelationalRule)
    assert body.operator == ">="


# ================================================================
# 多错误聚合测试
# ================================================================

def test_multiple_errors_aggregated():
    """Test that multiple semantic errors are aggregated"""
    data = {
        "core_slots": [
            {
                "slot_name": "dimension",
                "description": "First",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": []
            },
            {
                "slot_name": "dimension",
                "description": "Duplicate",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": []
            },
            {
                "slot_name": "top_k",
                "description": "Top K",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": ["nonexistent"]
            }
        ]
    }

    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    with pytest.raises(ContractValidationError) as exc_info:
        semantic_validator.validate(validated)

    error_str = str(exc_info.value)
    # 应该聚合多个错误
    assert "issue(s)" in error_str
    assert "DUPLICATE_SLOT" in error_str
    assert "UNDEFINED_DEPENDENCY_REF" in error_str


# ================================================================
# 文件集成测试
# ================================================================

def test_valid_fixtures():
    """Test that valid fixtures pass semantic validation"""
    schema_validator = ContractSchemaValidator()
    semantic_validator = SemanticValidator()

    fixtures_dir = Path(__file__).parent / "fixtures" / "valid_contracts"
    yaml_files = list(fixtures_dir.glob("*.yaml"))

    for yaml_file in yaml_files:
        # Load and validate
        from contract.parser import get_default_parser
        parser = get_default_parser()
        raw_data = parser.load_file(yaml_file)

        validated = schema_validator.validate(raw_data)
        result = semantic_validator.validate(validated)

        assert isinstance(result, object)


def test_invalid_semantic_fixtures():
    """Test that semantic-invalid fixtures fail"""
    schema_validator = ContractSchemaValidator()
    semantic_validator = SemanticValidator()

    fixtures_dir = Path(__file__).parent / "fixtures" / "semantic_invalid"
    yaml_files = list(fixtures_dir.glob("*.yaml"))

    for yaml_file in yaml_files:
        from contract.parser import get_default_parser
        parser = get_default_parser()

        try:
            raw_data = parser.load_file(yaml_file)
            validated = schema_validator.validate(raw_data)
            with pytest.raises(ContractValidationError):
                semantic_validator.validate(validated)
        except ContractParseError:
            # Parser or schema error is acceptable
            pass


# ================================================================
# SlotKey 测试
# ================================================================

def test_slot_key_creation():
    """Test SlotKey creation"""
    key1 = SlotKey(scope="COLLECTION", slot_name="dimension")
    key2 = SlotKey(scope="COLLECTION", slot_name="dimension")

    assert key1 == key2
    assert hash(key1) == hash(key2)
    assert str(key1) == "COLLECTION.dimension"


def test_slot_key_from_string():
    """Test SlotKey.from_string()"""
    key = SlotKey.from_string("COLLECTION.dimension")
    assert key.scope == "COLLECTION"
    assert key.slot_name == "dimension"


def test_slot_key_from_string_invalid():
    """Test SlotKey.from_string() with invalid string"""
    with pytest.raises(ValueError):
        SlotKey.from_string("invalid-format")


def test_slot_key_different():
    """Test that different SlotKeys are not equal"""
    key1 = SlotKey(scope="COLLECTION", slot_name="dimension")
    key2 = SlotKey(scope="COLLECTION", slot_name="top_k")

    assert key1 != key2


# ================================================================
# SlotReference 测试
# ================================================================

def test_slot_reference_creation():
    """Test SlotReference creation"""
    ref = SlotReference(scope="COLLECTION", slot_name="dimension")
    assert ref.scope == "COLLECTION"
    assert ref.slot_name == "dimension"
    assert ref.reason is None


def test_slot_reference_with_reason():
    """Test SlotReference with reason"""
    ref = SlotReference(
        scope="COLLECTION",
        slot_name="dimension",
        reason="primary key"
    )
    assert ref.reason == "primary key"


def test_slot_reference_key_property():
    """Test SlotReference.key property"""
    ref = SlotReference(scope="COLLECTION", slot_name="dimension")
    key = ref.key
    assert key.scope == "COLLECTION"
    assert key.slot_name == "dimension"


def test_slot_reference_str():
    """Test SlotReference string representation"""
    ref1 = SlotReference(scope="COLLECTION", slot_name="dimension")
    assert str(ref1) == "COLLECTION.dimension"

    ref2 = SlotReference(
        scope="COLLECTION",
        slot_name="dimension",
        reason="primary key"
    )
    assert "primary key" in str(ref2)


# ================================================================
# 类型安全测试
# ================================================================

def test_normalized_slot_type_safety():
    """Test NormalizedSlot has type-safe fields"""
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(VALID_BASIC)

    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    slot = result.core_slots[0]
    assert isinstance(slot.depends_on, list)
    assert isinstance(slot.rules, list)

    # 检查 rules 元素类型
    if slot.rules:
        for rule in slot.rules:
            assert isinstance(rule, NormalizedRule)


def test_normalized_rule_properties():
    """Test NormalizedRule type check properties"""
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(VALID_WITH_RULES)

    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    # Find the slot with rules (search_range)
    slot = next(s for s in result.core_slots if s.slot_name == "search_range")
    rule = slot.rules[0]

    # 类型检查属性
    assert rule.is_relational is True
    assert rule.is_range is False
    assert rule.is_enum is False
    assert rule.is_conditional is False

    # get_active_rule 返回 body
    assert isinstance(rule.get_active_rule(), NormalizedRelationalRule)


# ================================================================
# 边界情况测试
# ================================================================

def test_empty_core_slots():
    """Test validation with empty core_slots"""
    data = {"core_slots": []}

    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    assert len(result.core_slots) == 0


def test_no_dependencies():
    """Test normalization with empty depends_on"""
    data = {
        "core_slots": [
            {
                "slot_name": "dimension",
                "description": "Vector dimension",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": []
            }
        ]
    }

    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    assert len(result.core_slots[0].depends_on) == 0


def test_no_rules():
    """Test normalization with no rules"""
    data = {
        "core_slots": [
            {
                "slot_name": "dimension",
                "description": "Vector dimension",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": []
            }
        ]
    }

    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    assert len(result.core_slots[0].rules) == 0


# ================================================================
# 不同 scope 允许同名测试
# ================================================================

def test_different_scope_same_name_allowed():
    """Test that same slot_name in different scopes is allowed"""
    data = {
        "core_slots": [
            {
                "slot_name": "name",
                "description": "DB name",
                "type": "string",
                "scope": "DATABASE",
                "depends_on": []
            },
            {
                "slot_name": "name",
                "description": "Collection name",
                "type": "string",
                "scope": "COLLECTION",
                "depends_on": []
            },
            {
                "slot_name": "name",
                "description": "Index name",
                "type": "string",
                "scope": "INDEX",
                "depends_on": []
            }
        ]
    }

    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    # 应该通过验证 - 3 个 name 在不同 scope
    assert len(result.core_slots) == 3

    # 验证每个 slot 的 key 是不同的
    keys = [slot.key for slot in result.core_slots]
    assert len(keys) == 3
    assert len(set(keys)) == 3  # 全部唯一
