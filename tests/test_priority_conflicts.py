"""
Tests for Rule Priority Conflict Detection.

Tests the _check_priority_conflicts method in SemanticValidator
which detects when multiple rules in the same slot have the same priority.
"""

import pytest
from contract.validator import ContractSchemaValidator
from contract.semantic_validator import SemanticValidator
from contract.errors import ContractValidationError, PriorityConflictError


# ================================================================
# 无冲突场景测试
# ================================================================

def test_no_rules_no_conflict():
    """Test slot with no rules"""
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

    assert len(result.core_slots) == 1
    assert len(result.core_slots[0].rules) == 0


def test_single_rule_no_conflict():
    """Test slot with single rule"""
    data = {
        "core_slots": [
            {
                "slot_name": "dimension",
                "description": "Vector dimension",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "range_check",
                        "type": "range",
                        "severity": "HIGH",
                        "enabled": True,
                        "priority": 100,
                        "range": {
                            "min_value": 1,
                            "max_value": 2048
                        }
                    }
                ]
            }
        ]
    }

    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    assert len(result.core_slots[0].rules) == 1


def test_multiple_rules_different_priorities():
    """Test slot with multiple rules having different priorities"""
    data = {
        "core_slots": [
            {
                "slot_name": "dimension",
                "description": "Vector dimension",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "range_check",
                        "type": "range",
                        "severity": "HIGH",
                        "enabled": True,
                        "priority": 100,
                        "range": {
                            "min_value": 1,
                            "max_value": 2048
                        }
                    },
                    {
                        "rule_id": "enum_check",
                        "type": "enum",
                        "severity": "MEDIUM",
                        "enabled": True,
                        "priority": 200,
                        "enum": {
                            "allowed_values": [128, 256, 512, 1024, 2048]
                        }
                    }
                ]
            }
        ]
    }

    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    assert len(result.core_slots[0].rules) == 2


def test_multiple_rules_default_priority():
    """Test slot with multiple rules all using default priority (100)
    This SHOULD detect conflict since they all have the same priority.
    """
    data = {
        "core_slots": [
            {
                "slot_name": "dimension",
                "description": "Vector dimension",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "range_check",
                        "type": "range",
                        "severity": "HIGH",
                        "enabled": True,
                        # No priority specified, defaults to 100
                        "range": {
                            "min_value": 1,
                            "max_value": 2048
                        }
                    },
                    {
                        "rule_id": "enum_check",
                        "type": "enum",
                        "severity": "MEDIUM",
                        "enabled": True,
                        # No priority specified, defaults to 100
                        "enum": {
                            "allowed_values": [128, 256, 512, 1024, 2048]
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

    error_msg = str(exc_info.value)
    assert "PRIORITY_CONFLICT" in error_msg
    assert "dimension" in error_msg
    assert "range_check" in error_msg
    assert "enum_check" in error_msg


def test_multiple_slots_no_conflict():
    """Test multiple slots with rules, but no conflicts within each slot"""
    data = {
        "core_slots": [
            {
                "slot_name": "dimension",
                "description": "Vector dimension",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "dim_range",
                        "type": "range",
                        "severity": "HIGH",
                        "enabled": True,
                        "priority": 100,
                        "range": {"min_value": 1, "max_value": 2048}
                    }
                ]
            },
            {
                "slot_name": "top_k",
                "description": "Top K results",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "top_k_range",
                        "type": "range",
                        "severity": "HIGH",
                        "enabled": True,
                        "priority": 100,  # Same priority but different slot, OK
                        "range": {"min_value": 1, "max_value": 100}
                    }
                ]
            }
        ]
    }

    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    # Both slots should have rules with priority 100, but no conflict
    assert len(result.core_slots) == 2


# ================================================================
# 冲突场景测试
# ================================================================

def test_priority_conflict_two_rules():
    """Test priority conflict with two rules having same priority"""
    data = {
        "core_slots": [
            {
                "slot_name": "dimension",
                "description": "Vector dimension",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "range_check",
                        "type": "range",
                        "severity": "HIGH",
                        "enabled": True,
                        "priority": 100,
                        "range": {"min_value": 1, "max_value": 2048}
                    },
                    {
                        "rule_id": "enum_check",
                        "type": "enum",
                        "severity": "MEDIUM",
                        "enabled": True,
                        "priority": 100,  # Same priority as range_check
                        "enum": {"allowed_values": [128, 256, 512, 1024, 2048]}
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

    error_msg = str(exc_info.value)
    assert "PRIORITY_CONFLICT" in error_msg
    assert "dimension" in error_msg
    assert "100" in error_msg
    assert "range_check" in error_msg
    assert "enum_check" in error_msg


def test_priority_conflict_three_rules():
    """Test priority conflict with three rules having same priority"""
    data = {
        "core_slots": [
            {
                "slot_name": "dimension",
                "description": "Vector dimension",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "range_check",
                        "type": "range",
                        "severity": "HIGH",
                        "enabled": True,
                        "priority": 50,
                        "range": {"min_value": 1, "max_value": 2048}
                    },
                    {
                        "rule_id": "enum_check",
                        "type": "enum",
                        "severity": "MEDIUM",
                        "enabled": True,
                        "priority": 50,
                        "enum": {"allowed_values": [128, 256, 512, 1024, 2048]}
                    },
                    {
                        "rule_id": "relational_check",
                        "type": "relational",
                        "severity": "LOW",
                        "enabled": True,
                        "priority": 50,
                        "relational": {
                            "operator": ">=",
                            "reference_slot": "min_dim",
                            "error_message": "dimension >= min_dim"
                        }
                    }
                ]
            },
            {
                "slot_name": "min_dim",
                "description": "Minimum dimension",
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

    error_msg = str(exc_info.value)
    assert "PRIORITY_CONFLICT" in error_msg
    assert "dimension" in error_msg
    assert "50" in error_msg
    # All three rule IDs should be mentioned
    assert "range_check" in error_msg
    assert "enum_check" in error_msg
    assert "relational_check" in error_msg


def test_multiple_conflicts_different_priorities():
    """Test slot with conflicts at multiple different priority levels"""
    data = {
        "core_slots": [
            {
                "slot_name": "dimension",
                "description": "Vector dimension",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "range_100_a",
                        "type": "range",
                        "severity": "HIGH",
                        "enabled": True,
                        "priority": 100,
                        "range": {"min_value": 1, "max_value": 100}
                    },
                    {
                        "rule_id": "range_100_b",
                        "type": "range",
                        "severity": "HIGH",
                        "enabled": True,
                        "priority": 100,
                        "range": {"min_value": 100, "max_value": 200}
                    },
                    {
                        "rule_id": "enum_200_a",
                        "type": "enum",
                        "severity": "MEDIUM",
                        "enabled": True,
                        "priority": 200,
                        "enum": {"allowed_values": [128, 256]}
                    },
                    {
                        "rule_id": "enum_200_b",
                        "type": "enum",
                        "severity": "MEDIUM",
                        "enabled": True,
                        "priority": 200,
                        "enum": {"allowed_values": [512, 1024]}
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

    error_msg = str(exc_info.value)
    # Should report both conflicts
    assert "PRIORITY_CONFLICT" in error_msg
    assert "dimension" in error_msg
    assert "100" in error_msg
    assert "200" in error_msg
    assert "range_100_a" in error_msg
    assert "range_100_b" in error_msg
    assert "enum_200_a" in error_msg
    assert "enum_200_b" in error_msg


# ================================================================
# 边界情况测试
# ================================================================

def test_mixed_conflict_and_valid_rules():
    """Test slot with some conflicting priorities and some valid unique priorities"""
    data = {
        "core_slots": [
            {
                "slot_name": "dimension",
                "description": "Vector dimension",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "range_100_a",
                        "type": "range",
                        "severity": "HIGH",
                        "enabled": True,
                        "priority": 100,
                        "range": {"min_value": 1, "max_value": 100}
                    },
                    {
                        "rule_id": "range_100_b",
                        "type": "range",
                        "severity": "HIGH",
                        "enabled": True,
                        "priority": 100,  # Conflict with range_100_a
                        "range": {"min_value": 100, "max_value": 200}
                    },
                    {
                        "rule_id": "enum_300",
                        "type": "enum",
                        "severity": "MEDIUM",
                        "enabled": True,
                        "priority": 300,  # Unique priority, no conflict
                        "enum": {"allowed_values": [128, 256]}
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

    error_msg = str(exc_info.value)
    # Should report conflict at priority 100 but not 300
    assert "PRIORITY_CONFLICT" in error_msg
    assert "100" in error_msg
    assert "range_100_a" in error_msg
    assert "range_100_b" in error_msg
    # Priority 300 should not be mentioned as conflict
    assert "300" not in error_msg or error_msg.count("300") <= 1


def test_disabled_rules_also_checked():
    """Test that disabled rules are also checked for priority conflicts"""
    data = {
        "core_slots": [
            {
                "slot_name": "dimension",
                "description": "Vector dimension",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "enabled_rule",
                        "type": "range",
                        "severity": "HIGH",
                        "enabled": True,
                        "priority": 100,
                        "range": {"min_value": 1, "max_value": 2048}
                    },
                    {
                        "rule_id": "disabled_rule",
                        "type": "enum",
                        "severity": "MEDIUM",
                        "enabled": False,  # Disabled but still checked
                        "priority": 100,
                        "enum": {"allowed_values": [128, 256, 512]}
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

    error_msg = str(exc_info.value)
    assert "PRIORITY_CONFLICT" in error_msg
    # Both rules should be mentioned regardless of enabled status
    assert "enabled_rule" in error_msg
    assert "disabled_rule" in error_msg


def test_zero_priority():
    """Test that priority 0 is handled correctly"""
    data = {
        "core_slots": [
            {
                "slot_name": "dimension",
                "description": "Vector dimension",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "rule_a",
                        "type": "range",
                        "severity": "HIGH",
                        "enabled": True,
                        "priority": 0,
                        "range": {"min_value": 1, "max_value": 2048}
                    },
                    {
                        "rule_id": "rule_b",
                        "type": "enum",
                        "severity": "MEDIUM",
                        "enabled": True,
                        "priority": 0,  # Same priority 0
                        "enum": {"allowed_values": [128, 256]}
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

    error_msg = str(exc_info.value)
    assert "PRIORITY_CONFLICT" in error_msg
    assert "0" in error_msg
    assert "rule_a" in error_msg
    assert "rule_b" in error_msg


# ================================================================
# 跨 scope 测试
# ================================================================

def test_cross_scope_no_conflict():
    """Test that same priority in different scopes does not cause conflict"""
    data = {
        "core_slots": [
            {
                "slot_name": "name",
                "description": "Database name",
                "type": "string",
                "scope": "DATABASE",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "db_name_rule",
                        "type": "enum",
                        "severity": "HIGH",
                        "enabled": True,
                        "priority": 100,
                        "enum": {"allowed_values": ["my_db", "test_db"]}
                    }
                ]
            },
            {
                "slot_name": "name",
                "description": "Collection name",
                "type": "string",
                "scope": "COLLECTION",
                "depends_on": [],
                "rules": [
                    {
                        "rule_id": "coll_name_rule",
                        "type": "enum",
                        "severity": "HIGH",
                        "enabled": True,
                        "priority": 100,  # Same priority but different scope, OK
                        "enum": {"allowed_values": ["my_collection", "test_collection"]}
                    }
                ]
            }
        ]
    }

    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    # Both should exist with no conflict
    assert len(result.core_slots) == 2
