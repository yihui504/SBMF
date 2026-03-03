"""
Tests for Contract Schema Validator.

Tests the ContractSchemaValidator class which performs structural validation
of raw YAML data.
"""

import pytest
from pathlib import Path
from contract.validator import ContractSchemaValidator
from contract.schema import ValidatedRawContract, ValidatedRawSlot
from contract.errors import ContractParseError


# ================================================================
# Test data
# ================================================================

VALID_MINIMAL = {"core_slots": []}

VALID_BASIC_SLOT = {
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

VALID_COMPLETE_SLOT = {
    "database_name": "test_db",
    "version": "1.0",
    "core_slots": [
        {
            "slot_name": "dimension",
            "description": "Vector dimension",
            "type": "integer",
            "scope": "COLLECTION",
            "depends_on": [],
            "constraints": {
                "range": {
                    "min": 1,
                    "max": 32768,
                    "inclusive": True
                }
            },
            "rules": [
                {
                    "rule_id": "dim_check",
                    "type": "range",
                    "severity": "HIGH",
                    "enabled": True,
                    "priority": 10,
                    "range": {
                        "min_value": 1,
                        "max_value": 32768,
                        "inclusive_min": True,
                        "inclusive_max": True
                    }
                }
            ]
        }
    ]
}

VALID_WITH_DEPENDENCIES = {
    "core_slots": [
        {
            "slot_name": "top_k",
            "description": "Top K",
            "type": "integer",
            "scope": "COLLECTION",
            "depends_on": ["dimension", {"slot_name": "search_range", "reason": "depends on it"}]
        }
    ]
}

VALID_WITH_RELATIONAL_RULE = {
    "core_slots": [
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
                    "priority": 10,
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
# ContractSchemaValidator.basic 测试
# ================================================================

def test_validator_init():
    """Test validator instantiation"""
    validator = ContractSchemaValidator()
    assert validator is not None


# ================================================================
# Top-level validation 测试
# ================================================================

def test_validate_minimal_contract():
    """Test validation of minimal valid contract"""
    validator = ContractSchemaValidator()
    result = validator.validate(VALID_MINIMAL)

    assert isinstance(result, ValidatedRawContract)
    assert result.database_name is None
    assert result.version is None
    assert len(result.core_slots) == 0


def test_validate_missing_core_slots():
    """Test that missing core_slots raises error"""
    validator = ContractSchemaValidator()
    data = {"database_name": "test"}

    with pytest.raises(ContractParseError) as exc_info:
        validator.validate(data)

    assert "Missing required field" in str(exc_info.value)
    assert "core_slots" in str(exc_info.value)


def test_validate_core_slots_not_list():
    """Test that core_slots not being a list raises error"""
    validator = ContractSchemaValidator()
    data = {"core_slots": "not a list"}

    with pytest.raises(ContractParseError) as exc_info:
        validator.validate(data)

    assert "must be a list" in str(exc_info.value)


def test_validate_with_optional_fields():
    """Test validation with optional database_name and version"""
    validator = ContractSchemaValidator()
    result = validator.validate(VALID_COMPLETE_SLOT)

    assert result.database_name == "test_db"
    assert result.version == "1.0"


# ================================================================
# Slot validation 测试
# ================================================================

def test_validate_basic_slot():
    """Test validation of basic slot"""
    validator = ContractSchemaValidator()
    result = validator.validate(VALID_BASIC_SLOT)

    assert len(result.core_slots) == 1
    slot = result.core_slots[0]
    assert slot.slot_name == "dimension"
    assert slot.type == "integer"
    assert slot.scope == "COLLECTION"
    assert len(slot.depends_on) == 0


def test_validate_slot_not_dict():
    """Test that slot not being a dict raises error"""
    validator = ContractSchemaValidator()
    data = {"core_slots": ["just a string"]}

    with pytest.raises(ContractParseError) as exc_info:
        validator.validate(data)

    assert "must be a dict" in str(exc_info.value)
    assert "index 0" in str(exc_info.value)


def test_validate_missing_slot_name():
    """Test that missing slot_name raises error"""
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "description": "No slot_name",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": []
            }
        ]
    }

    with pytest.raises(ContractParseError) as exc_info:
        validator.validate(data)

    assert "Missing required field" in str(exc_info.value)
    assert "slot_name" in str(exc_info.value)


def test_validate_empty_slot_name():
    """Test that empty slot_name raises error"""
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": "",
                "description": "Empty",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": []
            }
        ]
    }

    with pytest.raises(ContractParseError) as exc_info:
        validator.validate(data)

    assert "cannot be empty" in str(exc_info.value)


def test_validate_wrong_slot_name_type():
    """Test that non-string slot_name raises error"""
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": 123,
                "description": "Wrong type",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": []
            }
        ]
    }

    with pytest.raises(ContractParseError) as exc_info:
        validator.validate(data)

    assert "must be str" in str(exc_info.value)


# ================================================================
# Enum value validation 测试
# ================================================================

def test_validate_invalid_type():
    """Test that invalid type raises error"""
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": "test",
                "description": "Test",
                "type": "invalid_type",
                "scope": "COLLECTION",
                "depends_on": []
            }
        ]
    }

    with pytest.raises(ContractParseError) as exc_info:
        validator.validate(data)

    assert "Invalid type 'invalid_type'" in str(exc_info.value)
    assert "integer" in str(exc_info.value)  # Valid types are listed


def test_validate_invalid_scope():
    """Test that invalid scope raises error"""
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": "test",
                "description": "Test",
                "type": "integer",
                "scope": "INVALID_SCOPE",
                "depends_on": []
            }
        ]
    }

    with pytest.raises(ContractParseError) as exc_info:
        validator.validate(data)

    assert "Invalid scope 'INVALID_SCOPE'" in str(exc_info.value)
    assert "COLLECTION" in str(exc_info.value)  # Valid scopes are listed


# ================================================================
# Depends_on validation 测试
# ================================================================

def test_validate_depends_on_string_format():
    """Test depends_on with string format"""
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": "top_k",
                "description": "Top K",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": ["dimension", "ef"]
            }
        ]
    }

    result = validator.validate(data)
    assert len(result.core_slots[0].depends_on) == 2
    assert result.core_slots[0].depends_on[0].slot_name == "dimension"
    assert result.core_slots[0].depends_on[0].reason is None


def test_validate_depends_on_dict_format():
    """Test depends_on with dict format"""
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": "top_k",
                "description": "Top K",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [
                    {"slot_name": "dimension", "reason": "depends on dimension"}
                ]
            }
        ]
    }

    result = validator.validate(data)
    assert len(result.core_slots[0].depends_on) == 1
    assert result.core_slots[0].depends_on[0].slot_name == "dimension"
    assert result.core_slots[0].depends_on[0].reason == "depends on dimension"


def test_validate_depends_on_not_list():
    """Test that depends_on not being a list raises error"""
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": "test",
                "description": "Test",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": "not a list"
            }
        ]
    }

    with pytest.raises(ContractParseError) as exc_info:
        validator.validate(data)

    assert "must be a list" in str(exc_info.value)
    assert "depends_on" in str(exc_info.value)


def test_validate_depends_on_empty_string():
    """Test that empty dependency string raises error"""
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": "test",
                "description": "Test",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [""]
            }
        ]
    }

    with pytest.raises(ContractParseError) as exc_info:
        validator.validate(data)

    assert "cannot be empty" in str(exc_info.value)


# ================================================================
# Rules validation 测试
# ================================================================

def test_validate_rules():
    """Test validation of rules"""
    validator = ContractSchemaValidator()
    result = validator.validate(VALID_COMPLETE_SLOT)

    assert result.core_slots[0].rules is not None
    assert len(result.core_slots[0].rules) == 1


def test_validate_rules_not_list():
    """Test that rules not being a list raises error"""
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": "test",
                "description": "Test",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": "not a list"
            }
        ]
    }

    with pytest.raises(ContractParseError) as exc_info:
        validator.validate(data)

    assert "must be a list" in str(exc_info.value)
    assert "rules" in str(exc_info.value)


# ================================================================
# Rule validation 测试
# ================================================================

def test_validate_rule_missing_id():
    """Test that rule without rule_id raises error"""
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": "test",
                "description": "Test",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "type": "relational",
                        "severity": "HIGH",
                        "enabled": True,
                        "relational": {
                            "operator": ">=",
                            "reference_slot": "x",
                            "error_message": "test"
                        }
                    }
                ]
            }
        ]
    }

    with pytest.raises(ContractParseError) as exc_info:
        validator.validate(data)

    assert "Missing required field" in str(exc_info.value)
    assert "rule_id" in str(exc_info.value)


def test_validate_rule_invalid_type():
    """Test that invalid rule type raises error"""
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": "test",
                "description": "Test",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "test_rule",
                        "type": "invalid_type",
                        "severity": "HIGH",
                        "enabled": True
                    }
                ]
            }
        ]
    }

    with pytest.raises(ContractParseError) as exc_info:
        validator.validate(data)

    assert "Invalid rule type 'invalid_type'" in str(exc_info.value)


def test_validate_rule_invalid_severity():
    """Test that invalid severity raises error"""
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": "test",
                "description": "Test",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "test_rule",
                        "type": "relational",
                        "severity": "INVALID",
                        "enabled": True,
                        "relational": {
                            "operator": ">=",
                            "reference_slot": "x",
                            "error_message": "test"
                        }
                    }
                ]
            }
        ]
    }

    with pytest.raises(ContractParseError) as exc_info:
        validator.validate(data)

    assert "Invalid severity 'INVALID'" in str(exc_info.value)


def test_validate_relational_rule():
    """Test validation of relational rule"""
    validator = ContractSchemaValidator()
    result = validator.validate(VALID_WITH_RELATIONAL_RULE)

    assert result.core_slots[0].rules is not None
    assert len(result.core_slots[0].rules) == 1


def test_validate_relational_rule_missing_relational_field():
    """Test that relational rule without 'relational' field raises error"""
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": "test",
                "description": "Test",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "test_rule",
                        "type": "relational",
                        "severity": "HIGH",
                        "enabled": True
                        # Missing 'relational' field
                    }
                ]
            }
        ]
    }

    with pytest.raises(ContractParseError) as exc_info:
        validator.validate(data)

    assert "requires 'relational' field" in str(exc_info.value)


def test_validate_relational_rule_invalid_operator():
    """Test that invalid operator raises error"""
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": "test",
                "description": "Test",
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
                            "operator": "invalid_op",
                            "reference_slot": "x",
                            "error_message": "test"
                        }
                    }
                ]
            }
        ]
    }

    with pytest.raises(ContractParseError) as exc_info:
        validator.validate(data)

    assert "Invalid operator 'invalid_op'" in str(exc_info.value)


def test_validate_priority_field():
    """Test that priority field accepts integer"""
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": "test",
                "description": "Test",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "test_rule",
                        "type": "relational",
                        "severity": "HIGH",
                        "enabled": True,
                        "priority": 50,
                        "relational": {
                            "operator": ">=",
                            "reference_slot": "x",
                            "error_message": "test"
                        }
                    }
                ]
            }
        ]
    }

    result = validator.validate(data)
    assert result.core_slots[0].rules[0]["priority"] == 50


# ================================================================
# Constraints validation 测试
# ================================================================

def test_validate_range_constraint():
    """Test validation of range constraint"""
    validator = ContractSchemaValidator()
    result = validator.validate(VALID_COMPLETE_SLOT)

    assert result.core_slots[0].constraints is not None
    assert "range" in result.core_slots[0].constraints


# ================================================================
# File-based validation 测试
# ================================================================

def test_validate_valid_contract_files():
    """Test validation of valid contract YAML files"""
    validator = ContractSchemaValidator()
    fixtures_dir = Path(__file__).parent / "fixtures" / "valid_contracts"

    yaml_files = list(fixtures_dir.glob("*.yaml"))
    assert len(yaml_files) > 0, "No fixture files found"

    for yaml_file in yaml_files:
        # Load using parser
        from contract.parser import get_default_parser
        parser = get_default_parser()
        raw_data = parser.load_file(yaml_file)

        # Validate
        result = validator.validate(raw_data)
        assert isinstance(result, ValidatedRawContract)


def test_validate_invalid_contract_files():
    """Test that invalid contract YAML files raise errors"""
    validator = ContractSchemaValidator()
    fixtures_dir = Path(__file__).parent / "fixtures" / "invalid_contracts"

    yaml_files = list(fixtures_dir.glob("*.yaml"))
    assert len(yaml_files) > 0, "No fixture files found"

    for yaml_file in yaml_files:
        # Load using parser
        from contract.parser import get_default_parser
        parser = get_default_parser()

        try:
            raw_data = parser.load_file(yaml_file)
            # Try to validate - should raise ContractParseError
            with pytest.raises(ContractParseError):
                validator.validate(raw_data)
        except ContractParseError:
            # Parser error is also acceptable
            pass


# ================================================================
# 边界情况测试
# ================================================================

def test_validate_empty_core_slots_list():
    """Test validation with empty core_slots list"""
    validator = ContractSchemaValidator()
    data = {"core_slots": []}

    result = validator.validate(data)
    assert len(result.core_slots) == 0


def test_validate_multiple_slots():
    """Test validation with multiple slots"""
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": "dimension",
                "description": "Dimension",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": []
            },
            {
                "slot_name": "top_k",
                "description": "Top K",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": ["dimension"]
            }
        ]
    }

    result = validator.validate(data)
    assert len(result.core_slots) == 2
    assert result.core_slots[0].slot_name == "dimension"
    assert result.core_slots[1].slot_name == "top_k"


# ================================================================
# 验证边界（不做语义检查）
# ================================================================

def test_schema_validator_does_not_check_duplicates():
    """Test that schema validator does NOT check for duplicate slot names

    This is important - duplicate detection is SemanticValidator's job.
    SchemaValidator should accept duplicate slots.
    """
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": "dimension",  # Duplicate name
                "description": "First",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": []
            },
            {
                "slot_name": "dimension",  # Duplicate name
                "description": "Second",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": []
            }
        ]
    }

    # Should NOT raise error - duplicates are semantic validation
    result = validator.validate(data)
    assert len(result.core_slots) == 2
    # Both slots have the same name - semantic validator will catch this


def test_schema_validator_does_not_check_reference_slot_existence():
    """Test that schema validator does NOT check if reference_slot exists

    This is important - reference existence is SemanticValidator's job.
    SchemaValidator should accept any valid string for reference_slot.
    """
    validator = ContractSchemaValidator()
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
                        "rule_id": "range_check",
                        "type": "relational",
                        "severity": "HIGH",
                        "enabled": True,
                        "relational": {
                            "operator": ">=",
                            "reference_slot": "nonexistent_slot",  # Does not exist
                            "error_message": "test"
                        }
                    }
                ]
            }
        ]
    }

    # Should NOT raise error - reference existence is semantic validation
    result = validator.validate(data)
    assert result.core_slots[0].rules[0]["relational"]["reference_slot"] == "nonexistent_slot"


def test_schema_validator_does_not_check_depends_on_existence():
    """Test that schema validator does NOT check if depends_on slots exist

    This is important - dependency existence is SemanticValidator's job.
    SchemaValidator should accept any valid string for dependency.
    """
    validator = ContractSchemaValidator()
    data = {
        "core_slots": [
            {
                "slot_name": "top_k",
                "description": "Top K",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": ["nonexistent_slot"]  # Does not exist
            }
        ]
    }

    # Should NOT raise error - dependency existence is semantic validation
    result = validator.validate(data)
    assert result.core_slots[0].depends_on[0].slot_name == "nonexistent_slot"
