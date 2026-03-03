"""
End-to-End Integration Tests for Contract DSL.

Tests the complete loading pipeline from YAML files to Contract objects.
"""

import pytest
from pathlib import Path
from contract import (
    load_contract,
    load_contract_from_string,
    load_contract_with_validation_result,
    Contract,
    ContractParseError,
    ContractValidationError,
    DependencyCycleError,
    PriorityConflictError,
)


# ================================================================
# load_contract() 基础测试
# ================================================================

def test_load_contract_from_file():
    """Test loading a contract from YAML file"""
    fixture_path = Path(__file__).parent / "fixtures" / "integration" / "seekdb_contract.yaml"

    contract = load_contract(fixture_path)

    assert isinstance(contract, Contract)
    assert contract.database_name == "seekdb_vector_db"
    assert contract.version == "1.0"
    assert len(contract.core_slots) > 0


def test_load_contract_with_complex_dependencies():
    """Test loading contract with complex dependency relationships"""
    fixture_path = Path(__file__).parent / "fixtures" / "integration" / "seekdb_contract.yaml"

    contract = load_contract(fixture_path)

    # Verify dependency chain: dimension -> top_k -> search_range
    dimension = contract.get_slot("COLLECTION", "dimension")
    top_k = contract.get_slot("COLLECTION", "top_k")
    search_range = contract.get_slot("COLLECTION", "search_range")

    assert dimension is not None
    assert top_k is not None
    assert search_range is not None

    # top_k depends on dimension
    top_k_deps = contract.get_dependencies("COLLECTION", "top_k")
    assert len(top_k_deps) > 0
    assert any(dep.slot_name == "dimension" for dep in top_k_deps)

    # search_range depends on top_k
    sr_deps = contract.get_dependencies("COLLECTION", "search_range")
    assert len(sr_deps) > 0
    assert any(dep.slot_name == "top_k" for dep in sr_deps)


def test_load_contract_topological_order():
    """Test that topological order respects dependencies"""
    fixture_path = Path(__file__).parent / "fixtures" / "integration" / "seekdb_contract.yaml"

    contract = load_contract(fixture_path)

    order = contract.get_topological_order()

    # dimension should come before top_k
    slot_names = [s.slot_name for s in order]
    if "dimension" in slot_names and "top_k" in slot_names:
        assert slot_names.index("dimension") < slot_names.index("top_k")

    # top_k should come before search_range
    if "top_k" in slot_names and "search_range" in slot_names:
        assert slot_names.index("top_k") < slot_names.index("search_range")


# ================================================================
# load_contract_from_string() 测试
# ================================================================

def test_load_contract_from_string_simple():
    """Test loading contract from YAML string"""
    yaml_content = """
database_name: test_db
version: "1.0"

core_slots:
  - slot_name: dimension
    description: "Vector dimension"
    type: integer
    scope: COLLECTION
    depends_on: []
    rules:
      - rule_id: dim_check
        type: range
        severity: HIGH
        enabled: true
        priority: 10
        range:
          min_value: 1
          max_value: 2048
"""

    contract = load_contract_from_string(yaml_content)

    assert contract.database_name == "test_db"
    assert contract.version == "1.0"
    assert len(contract.core_slots) == 1
    assert contract.core_slots[0].slot_name == "dimension"


def test_load_contract_from_string_with_dependencies():
    """Test loading contract with dependencies from string"""
    yaml_content = """
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
"""

    contract = load_contract_from_string(yaml_content)

    assert len(contract.core_slots) == 2

    # Verify dependency
    deps = contract.get_dependencies("COLLECTION", "top_k")
    assert len(deps) == 1
    assert deps[0].slot_name == "dimension"


# ================================================================
# load_contract_with_validation_result() 测试
# ================================================================

def test_load_contract_with_validation_result():
    """Test loading contract with validation info"""
    fixture_path = Path(__file__).parent / "fixtures" / "integration" / "seekdb_contract.yaml"

    contract, info = load_contract_with_validation_result(fixture_path)

    assert isinstance(contract, Contract)
    assert isinstance(info, dict)
    assert "slot_count" in info
    assert "edge_count" in info
    assert "scopes" in info
    assert "rule_count" in info
    assert "enabled_rule_count" in info

    # Verify info is accurate
    assert info["slot_count"] == len(contract.core_slots)
    assert info["rule_count"] == sum(len(slot.rules) for slot in contract.core_slots)


def test_validation_info_accurate():
    """Test that validation info is accurate"""
    yaml_content = """
core_slots:
  - slot_name: dimension
    description: "Vector dimension"
    type: integer
    scope: COLLECTION
    depends_on: []
    rules:
      - rule_id: rule1
        type: range
        severity: HIGH
        enabled: true
        priority: 10
        range: {min_value: 1, max_value: 100}
      - rule_id: rule2
        type: range
        severity: LOW
        enabled: false
        priority: 20
        range: {min_value: 50, max_value: 200}
"""

    contract, info = load_contract_with_validation_result(yaml_content)

    assert info["slot_count"] == 1
    assert info["rule_count"] == 2
    assert info["enabled_rule_count"] == 1  # Only rule1 is enabled
    assert "COLLECTION" in info["scopes"]


# ================================================================
# 错误处理测试
# ================================================================

def test_load_contract_invalid_yaml():
    """Test loading invalid YAML file"""
    from contract.parser import get_default_parser

    # Create a temporary invalid YAML file
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("invalid: yaml: content:\n  - broken")
        temp_path = f.name

    try:
        with pytest.raises(ContractParseError):
            load_contract(temp_path)
    finally:
        os.unlink(temp_path)


def test_load_contract_missing_required_field():
    """Test loading contract with missing required field"""
    yaml_content = """
# Missing core_slots
database_name: test_db
"""

    with pytest.raises(ContractParseError) as exc_info:
        load_contract_from_string(yaml_content)

    error_msg = str(exc_info.value)
    assert "core_slots" in error_msg.lower()


def test_load_contract_duplicate_slots():
    """Test loading contract with duplicate slots"""
    yaml_content = """
core_slots:
  - slot_name: dimension
    description: "First"
    type: integer
    scope: COLLECTION
    depends_on: []
  - slot_name: dimension
    description: "Duplicate"
    type: integer
    scope: COLLECTION
    depends_on: []
"""

    with pytest.raises(ContractValidationError) as exc_info:
        load_contract_from_string(yaml_content)

    error_msg = str(exc_info.value)
    assert "DUPLICATE_SLOT" in error_msg


def test_load_contract_undefined_dependency():
    """Test loading contract with undefined dependency"""
    yaml_content = """
core_slots:
  - slot_name: top_k
    description: "Top K"
    type: integer
    scope: COLLECTION
    depends_on:
      - slot_name: dimension
        reason: "depends on dimension"
"""

    with pytest.raises(ContractValidationError) as exc_info:
        load_contract_from_string(yaml_content)

    error_msg = str(exc_info.value)
    assert "UNDEFINED_DEPENDENCY_REF" in error_msg


def test_load_contract_dependency_cycle():
    """Test loading contract with dependency cycle"""
    yaml_content = """
core_slots:
  - slot_name: a
    description: "Slot A"
    type: integer
    scope: COLLECTION
    depends_on:
      - slot_name: b
        reason: "A depends on B"
  - slot_name: b
    description: "Slot B"
    type: integer
    scope: COLLECTION
    depends_on:
      - slot_name: a
        reason: "B depends on A"
"""

    with pytest.raises(DependencyCycleError) as exc_info:
        load_contract_from_string(yaml_content)

    assert exc_info.value.cycle is not None
    cycle_str = exc_info.value.cycle.format()
    assert "COLLECTION.a" in cycle_str
    assert "COLLECTION.b" in cycle_str


def test_load_contract_priority_conflict():
    """Test loading contract with priority conflict"""
    yaml_content = """
core_slots:
  - slot_name: dimension
    description: "Vector dimension"
    type: integer
    scope: COLLECTION
    depends_on: []
    rules:
      - rule_id: rule1
        type: range
        severity: HIGH
        enabled: true
        priority: 10
        range: {min_value: 1, max_value: 100}
      - rule_id: rule2
        type: range
        severity: HIGH
        enabled: true
        priority: 10  # Same priority as rule1
        range: {min_value: 50, max_value: 200}
"""

    with pytest.raises(ContractValidationError) as exc_info:
        load_contract_from_string(yaml_content)

    error_msg = str(exc_info.value)
    assert "PRIORITY_CONFLICT" in error_msg


# ================================================================
# Contract 业务逻辑测试（真实场景）
# ================================================================

def test_contract_get_rules_by_scope():
    """Test getting rules by scope from real contract"""
    fixture_path = Path(__file__).parent / "fixtures" / "integration" / "seekdb_contract.yaml"

    contract = load_contract(fixture_path)

    # Get COLLECTION scope slots
    collection_slots = contract.get_slots_by_scope("COLLECTION")
    assert len(collection_slots) > 0

    # Get DATABASE scope slots
    db_slots = contract.get_slots_by_scope("DATABASE")
    assert len(db_slots) > 0

    # Get INDEX scope slots
    index_slots = contract.get_slots_by_scope("INDEX")
    assert len(index_slots) > 0


def test_contract_enabled_rules_filtering():
    """Test filtering enabled rules from real contract"""
    fixture_path = Path(__file__).parent / "fixtures" / "integration" / "seekdb_contract.yaml"

    contract = load_contract(fixture_path)

    # Get dimension slot rules
    all_rules = contract.get_rules("COLLECTION", "dimension")
    enabled_rules = contract.get_enabled_rules("COLLECTION", "dimension")

    # All rules in the test contract are enabled
    assert len(enabled_rules) == len(all_rules)


def test_contract_dependency_graph_queries():
    """Test dependency graph queries on real contract"""
    fixture_path = Path(__file__).parent / "fixtures" / "integration" / "seekdb_contract.yaml"

    contract = load_contract(fixture_path)

    # Test has_dependency
    assert contract.has_dependency("COLLECTION", "top_k", "COLLECTION", "dimension")
    assert contract.has_dependency("COLLECTION", "search_range", "COLLECTION", "top_k")

    # Test non-existent dependency
    assert not contract.has_dependency("COLLECTION", "dimension", "COLLECTION", "top_k")


def test_contract_immutability():
    """Test that loaded contract is immutable"""
    yaml_content = """
core_slots:
  - slot_name: dimension
    description: "Vector dimension"
    type: integer
    scope: COLLECTION
    depends_on: []
"""

    contract = load_contract_from_string(yaml_content)

    # Attempt to modify should raise exception
    with pytest.raises(Exception):
        contract.database_name = "modified"

    with pytest.raises(Exception):
        contract.core_slots = ()


# ================================================================
# 边界情况测试
# ================================================================

def test_load_empty_contract():
    """Test loading contract with no slots"""
    yaml_content = """
database_name: empty_db
version: "1.0"
core_slots: []
"""

    contract = load_contract_from_string(yaml_content)

    assert contract.database_name == "empty_db"
    assert len(contract.core_slots) == 0
    assert contract.dependency_graph.is_empty()


def test_load_contract_minimal():
    """Test loading minimal valid contract"""
    yaml_content = """
core_slots: []
"""

    contract = load_contract_from_string(yaml_content)

    assert contract.database_name is None
    assert contract.version is None
    assert len(contract.core_slots) == 0


def test_load_contract_with_special_characters():
    """Test loading contract with special characters in descriptions"""
    yaml_content = """
database_name: "test-db-with-special_chars"
version: "1.0-beta"

core_slots:
  - slot_name: slot_with_underscore
    description: "Description with special chars: test and data"
    type: string
    scope: COLLECTION
    depends_on: []
"""

    contract = load_contract_from_string(yaml_content)

    assert contract.database_name == "test-db-with-special_chars"
    assert contract.version == "1.0-beta"
    assert contract.core_slots[0].slot_name == "slot_with_underscore"


# ================================================================
# 文件路径处理测试
# ================================================================

def test_load_contract_with_path_object():
    """Test loading with Path object"""
    fixture_path = Path(__file__).parent / "fixtures" / "integration" / "seekdb_contract.yaml"

    contract = load_contract(fixture_path)

    assert isinstance(contract, Contract)


def test_load_contract_with_string_path():
    """Test loading with string path"""
    fixture_path = str(Path(__file__).parent / "fixtures" / "integration" / "seekdb_contract.yaml")

    contract = load_contract(fixture_path)

    assert isinstance(contract, Contract)


def test_load_contract_nonexistent_file():
    """Test loading non-existent file"""
    with pytest.raises(ContractParseError):
        load_contract("/nonexistent/file.yaml")
