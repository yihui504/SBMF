"""
Tests for Contract Builder.

Tests the ContractBuilder class and Contract class which
convert SemanticallyValidContract to the final Contract object.
"""

import pytest
from contract.validator import ContractSchemaValidator
from contract.semantic_validator import SemanticValidator
from contract.builder import ContractBuilder, build_contract
from contract import Contract, SemanticallyValidContract
from contract.types import SlotKey, SlotReference


# ================================================================
# ContractBuilder 基础测试
# ================================================================

def test_contract_builder_creates_contract():
    """Test that ContractBuilder creates a Contract object"""
    # 简单的 contract 数据
    data = {
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

    # 完整的验证流程（跳过 parser，直接用 dict）
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    # 构建最终 Contract
    builder = ContractBuilder()
    contract = builder.build(semantically_valid)

    assert isinstance(contract, Contract)
    assert contract.database_name == "test_db"
    assert contract.version == "1.0"
    assert len(contract.core_slots) == 1


def test_build_contract_convenience_function():
    """Test the build_contract convenience function"""
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

    # Skip parser, use dict directly
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    # 使用便捷函数
    contract = build_contract(semantically_valid)

    assert isinstance(contract, Contract)


def test_contract_core_slots_is_tuple():
    """Test that Contract.core_slots is a tuple (immutable)"""
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

    # Skip parser, use dict directly
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    contract = build_contract(semantically_valid)

    assert isinstance(contract.core_slots, tuple)
    # 尝试修改应该失败
    with pytest.raises(TypeError):
        contract.core_slots[0] = "something"


# ================================================================
# Contract 业务逻辑方法测试
# ================================================================

def test_contract_get_slot():
    """Test Contract.get_slot() method"""
    data = {
        "database_name": "test_db",
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
                "description": "Top K results",
                "type": "integer",
                "scope": "DATABASE",
                "depends_on": []
            }
        ]
    }

    # Skip parser, use dict directly
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    contract = build_contract(semantically_valid)

    # 获取存在的 slot
    slot = contract.get_slot("COLLECTION", "dimension")
    assert slot is not None
    assert slot.slot_name == "dimension"
    assert slot.scope == "COLLECTION"

    # 获取另一个存在的 slot
    slot2 = contract.get_slot("DATABASE", "top_k")
    assert slot2 is not None
    assert slot2.slot_name == "top_k"

    # 获取不存在的 slot
    slot3 = contract.get_slot("COLLECTION", "nonexistent")
    assert slot3 is None


def test_contract_get_slot_by_key():
    """Test Contract.get_slot_by_key() method"""
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

    # Skip parser, use dict directly
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    contract = build_contract(semantically_valid)

    key = SlotKey(scope="COLLECTION", slot_name="dimension")
    slot = contract.get_slot_by_key(key)

    assert slot is not None
    assert slot.slot_name == "dimension"

    # 测试不存在的 key
    key2 = SlotKey(scope="COLLECTION", slot_name="nonexistent")
    slot2 = contract.get_slot_by_key(key2)
    assert slot2 is None


def test_contract_get_dependencies():
    """Test Contract.get_dependencies() method"""
    data = {
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
                "description": "Top K results",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [
                    {"slot_name": "dimension", "reason": "depends on dimension"}
                ]
            }
        ]
    }

    # Skip parser, use dict directly
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    contract = build_contract(semantically_valid)

    # dimension 没有依赖
    deps_dim = contract.get_dependencies("COLLECTION", "dimension")
    assert len(deps_dim) == 0

    # top_k 依赖 dimension
    deps_topk = contract.get_dependencies("COLLECTION", "top_k")
    assert len(deps_topk) == 1
    assert deps_topk[0].slot_name == "dimension"
    assert deps_topk[0].scope == "COLLECTION"


def test_contract_get_rules():
    """Test Contract.get_rules() method"""
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
                        "enabled": False,
                        "priority": 200,
                        "enum": {"allowed_values": [128, 256, 512]}
                    }
                ]
            }
        ]
    }

    # Skip parser, use dict directly
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    contract = build_contract(semantically_valid)

    # 获取所有规则
    rules = contract.get_rules("COLLECTION", "dimension")
    assert len(rules) == 2
    assert rules[0].rule_id == "range_check"
    assert rules[1].rule_id == "enum_check"


def test_contract_get_enabled_rules():
    """Test Contract.get_enabled_rules() method"""
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
                        "enabled": False,
                        "priority": 200,
                        "enum": {"allowed_values": [128, 256]}
                    }
                ]
            }
        ]
    }

    # Skip parser, use dict directly
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    contract = build_contract(semantically_valid)

    # 获取启用的规则
    enabled_rules = contract.get_enabled_rules("COLLECTION", "dimension")
    assert len(enabled_rules) == 1
    assert enabled_rules[0].rule_id == "enabled_rule"


def test_contract_get_topological_order():
    """Test Contract.get_topological_order() method"""
    data = {
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
                "description": "Top K results",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [{"slot_name": "dimension", "reason": "depends on dimension"}]
            },
            {
                "slot_name": "search_range",
                "description": "Search range",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [{"slot_name": "top_k", "reason": "depends on top_k"}]
            }
        ]
    }

    # Skip parser, use dict directly
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    contract = build_contract(semantically_valid)

    # 获取拓扑排序
    order = contract.get_topological_order()
    assert len(order) == 3

    # dimension 应该在 top_k 之前，top_k 应该在 search_range 之前
    slot_names = [s.slot_name for s in order]
    assert slot_names.index("dimension") < slot_names.index("top_k")
    assert slot_names.index("top_k") < slot_names.index("search_range")


def test_contract_get_slots_by_scope():
    """Test Contract.get_slots_by_scope() method"""
    data = {
        "core_slots": [
            {
                "slot_name": "db_name",
                "description": "Database name",
                "type": "string",
                "scope": "DATABASE",
                "depends_on": []
            },
            {
                "slot_name": "coll_name",
                "description": "Collection name",
                "type": "string",
                "scope": "COLLECTION",
                "depends_on": []
            },
            {
                "slot_name": "dimension",
                "description": "Vector dimension",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": []
            }
        ]
    }

    # Skip parser, use dict directly
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    contract = build_contract(semantically_valid)

    # 获取 DATABASE scope 的 slots
    db_slots = contract.get_slots_by_scope("DATABASE")
    assert len(db_slots) == 1
    assert db_slots[0].slot_name == "db_name"

    # 获取 COLLECTION scope 的 slots
    coll_slots = contract.get_slots_by_scope("COLLECTION")
    assert len(coll_slots) == 2
    coll_slot_names = [s.slot_name for s in coll_slots]
    assert "coll_name" in coll_slot_names
    assert "dimension" in coll_slot_names


def test_contract_has_dependency():
    """Test Contract.has_dependency() method"""
    data = {
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
                "description": "Top K results",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [
                    {"slot_name": "dimension", "reason": "depends on dimension"}
                ]
            }
        ]
    }

    # Skip parser, use dict directly
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    contract = build_contract(semantically_valid)

    # top_k 依赖 dimension
    assert contract.has_dependency("COLLECTION", "top_k", "COLLECTION", "dimension")

    # dimension 不依赖 top_k
    assert not contract.has_dependency("COLLECTION", "dimension", "COLLECTION", "top_k")

    # 不存在的依赖
    assert not contract.has_dependency("COLLECTION", "top_k", "DATABASE", "nonexistent")


# ================================================================
# 端到端集成测试
# ================================================================

def test_end_to_end_validation_flow():
    """Test complete end-to-end validation flow"""
    from contract.parser import get_default_parser

    yaml_content = """
database_name: test_db
version: "1.0"

core_slots:
  - slot_name: dimension
    description: "Vector dimension"
    type: integer
    scope: COLLECTION
    depends_on: []

  - slot_name: top_k
    description: "Top K results"
    type: integer
    scope: COLLECTION
    depends_on:
      - slot_name: dimension
        reason: "depends on dimension"

  - slot_name: search_range
    description: "Search range"
    type: integer
    scope: COLLECTION
    depends_on:
      - slot_name: top_k
        reason: "depends on top_k"
    rules:
      - rule_id: range_check
        type: relational
        severity: HIGH
        enabled: true
        priority: 100
        relational:
          operator: ">="
          reference_slot: top_k
          error_message: "search_range must be >= top_k"
"""

    # Step 1: Parse
    parser = get_default_parser()
    raw_data = parser.load_string(yaml_content)

    # Step 2: Schema validation
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(raw_data)

    # Step 3: Semantic validation
    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    # Step 4: Build Contract
    contract = build_contract(semantically_valid)

    # Verify final Contract
    assert contract.database_name == "test_db"
    assert contract.version == "1.0"
    assert len(contract.core_slots) == 3

    # Verify dependency graph
    assert not contract.dependency_graph.is_empty()
    assert len(contract.dependency_graph.slots) == 3

    # Verify topological order
    order = contract.get_topological_order()
    slot_names = [s.slot_name for s in order]
    assert slot_names == ["dimension", "top_k", "search_range"]


# ================================================================
# Contract 不可变性测试
# ================================================================

def test_contract_is_frozen():
    """Test that Contract is frozen (immutable)"""
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

    # Skip parser, use dict directly
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    contract = build_contract(semantically_valid)

    # 尝试修改字段应该失败
    with pytest.raises(Exception):  # FrozenInstanceError is a subclass of Exception
        contract.database_name = "new_name"

    with pytest.raises(Exception):
        contract.core_slots = ()


# ================================================================
# 空值测试
# ================================================================

def test_contract_with_empty_database_name_and_version():
    """Test Contract with None database_name and version"""
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

    # Skip parser, use dict directly
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    contract = build_contract(semantically_valid)

    assert contract.database_name is None
    assert contract.version is None


def test_contract_with_empty_slots():
    """Test Contract with no core_slots"""
    data = {"core_slots": []}

    # Skip parser, use dict directly
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    contract = build_contract(semantically_valid)

    assert len(contract.core_slots) == 0
    assert contract.dependency_graph.is_empty()
