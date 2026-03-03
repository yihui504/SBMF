"""
Tests for DependencyGraph.

Tests the DependencyGraph class which builds dependency graphs,
detects cycles, and performs topological sorting.
"""

import pytest
from contract.schema import DependencyGraph
from contract.types import SlotKey
from contract.errors import DependencyCycleError, DependencyCycle


# ================================================================
# 基础构建测试
# ================================================================

def test_empty_dependency_graph():
    """Test empty dependency graph"""
    graph = DependencyGraph(slots=(), edges=())

    assert graph.is_empty()
    assert graph.slots == ()
    assert graph.edges == ()


def test_single_slot_no_dependencies():
    """Test single slot with no dependencies"""
    slot_a = SlotKey(scope="COLLECTION", slot_name="dimension")
    graph = DependencyGraph(slots=(slot_a,), edges=())

    assert not graph.is_empty()
    assert len(graph.slots) == 1
    assert len(graph.edges) == 0
    assert graph.get_dependencies(slot_a) == ()
    assert graph.get_dependents(slot_a) == ()


def test_simple_dependency_chain():
    """Test simple dependency chain: A -> B -> C"""
    slot_a = SlotKey(scope="COLLECTION", slot_name="a")
    slot_b = SlotKey(scope="COLLECTION", slot_name="b")
    slot_c = SlotKey(scope="COLLECTION", slot_name="c")

    # A depends on B, B depends on C
    # Edges: (A, B), (B, C)
    graph = DependencyGraph(
        slots=(slot_a, slot_b, slot_c),
        edges=((slot_a, slot_b), (slot_b, slot_c))
    )

    assert len(graph.slots) == 3
    assert len(graph.edges) == 2

    # A depends on B
    assert graph.get_dependencies(slot_a) == (slot_b,)
    assert graph.get_dependents(slot_b) == (slot_a,)

    # B depends on C
    assert graph.get_dependencies(slot_b) == (slot_c,)
    assert graph.get_dependents(slot_c) == (slot_b,)


def test_multiple_dependencies():
    """Test slot with multiple dependencies: A -> B, A -> C"""
    slot_a = SlotKey(scope="COLLECTION", slot_name="a")
    slot_b = SlotKey(scope="COLLECTION", slot_name="b")
    slot_c = SlotKey(scope="COLLECTION", slot_name="c")

    # A depends on both B and C
    graph = DependencyGraph(
        slots=(slot_a, slot_b, slot_c),
        edges=((slot_a, slot_b), (slot_a, slot_c))
    )

    assert len(graph.edges) == 2
    deps_a = graph.get_dependencies(slot_a)
    assert len(deps_a) == 2
    assert slot_b in deps_a
    assert slot_c in deps_a


def test_diamond_dependency():
    """Test diamond dependency pattern
       A
      / \
     B   C
      \ /
       D
    """
    slot_a = SlotKey(scope="COLLECTION", slot_name="a")
    slot_b = SlotKey(scope="COLLECTION", slot_name="b")
    slot_c = SlotKey(scope="COLLECTION", slot_name="c")
    slot_d = SlotKey(scope="COLLECTION", slot_name="d")

    # A -> B, A -> C, B -> D, C -> D
    graph = DependencyGraph(
        slots=(slot_a, slot_b, slot_c, slot_d),
        edges=((slot_a, slot_b), (slot_a, slot_c), (slot_b, slot_d), (slot_c, slot_d))
    )

    assert len(graph.slots) == 4
    assert len(graph.edges) == 4

    # D has two dependents: B and C
    dependents_d = graph.get_dependents(slot_d)
    assert len(dependents_d) == 2
    assert slot_b in dependents_d
    assert slot_c in dependents_d


# ================================================================
# 拓扑排序测试
# ================================================================

def test_topological_sort_empty():
    """Test topological sort on empty graph"""
    graph = DependencyGraph(slots=(), edges=())
    result = graph.topological_sort()

    assert result == []


def test_topological_sort_single():
    """Test topological sort with single slot"""
    slot_a = SlotKey(scope="COLLECTION", slot_name="a")
    graph = DependencyGraph(slots=(slot_a,), edges=())
    result = graph.topological_sort()

    assert result == [slot_a]


def test_topological_sort_chain():
    """Test topological sort with dependency chain
       Result should be: C, B, A (dependencies first)
    """
    slot_a = SlotKey(scope="COLLECTION", slot_name="a")
    slot_b = SlotKey(scope="COLLECTION", slot_name="b")
    slot_c = SlotKey(scope="COLLECTION", slot_name="c")

    # A depends on B, B depends on C
    graph = DependencyGraph(
        slots=(slot_a, slot_b, slot_c),
        edges=((slot_a, slot_b), (slot_b, slot_c))
    )

    result = graph.topological_sort()

    # C should come first (no dependencies)
    # B should come after C
    # A should come last (depends on both)
    assert result.index(slot_c) < result.index(slot_b)
    assert result.index(slot_b) < result.index(slot_a)


def test_topological_sort_diamond():
    """Test topological sort with diamond pattern
       A
      / \
     B   C
      \ /
       D
    """
    slot_a = SlotKey(scope="COLLECTION", slot_name="a")
    slot_b = SlotKey(scope="COLLECTION", slot_name="b")
    slot_c = SlotKey(scope="COLLECTION", slot_name="c")
    slot_d = SlotKey(scope="COLLECTION", slot_name="d")

    graph = DependencyGraph(
        slots=(slot_a, slot_b, slot_c, slot_d),
        edges=((slot_a, slot_b), (slot_a, slot_c), (slot_b, slot_d), (slot_c, slot_d))
    )

    result = graph.topological_sort()

    # D has no dependencies, should come first
    # B and C depend on D, should come after D
    # A depends on B and C, should come last
    assert result.index(slot_d) < result.index(slot_b)
    assert result.index(slot_d) < result.index(slot_c)
    assert result.index(slot_b) < result.index(slot_a)
    assert result.index(slot_c) < result.index(slot_a)


# ================================================================
# 循环检测测试
# ================================================================

def test_detect_cycle_none():
    """Test cycle detection on acyclic graph"""
    slot_a = SlotKey(scope="COLLECTION", slot_name="a")
    slot_b = SlotKey(scope="COLLECTION", slot_name="b")
    slot_c = SlotKey(scope="COLLECTION", slot_name="c")

    graph = DependencyGraph(
        slots=(slot_a, slot_b, slot_c),
        edges=((slot_a, slot_b), (slot_b, slot_c))
    )

    cycle = graph.detect_cycle()
    assert cycle is None


def test_detect_cycle_simple_self_loop():
    """Test cycle detection with self-loop: A -> A"""
    slot_a = SlotKey(scope="COLLECTION", slot_name="a")

    graph = DependencyGraph(
        slots=(slot_a,),
        edges=((slot_a, slot_a))
    )

    cycle = graph.detect_cycle()
    assert cycle is not None
    assert "COLLECTION.a" in cycle.format()


def test_detect_cycle_two_nodes():
    """Test cycle detection with two nodes: A -> B -> A"""
    slot_a = SlotKey(scope="COLLECTION", slot_name="a")
    slot_b = SlotKey(scope="COLLECTION", slot_name="b")

    graph = DependencyGraph(
        slots=(slot_a, slot_b),
        edges=((slot_a, slot_b), (slot_b, slot_a))
    )

    cycle = graph.detect_cycle()
    assert cycle is not None
    # Cycle should include both A and B
    cycle_str = cycle.format()
    assert "COLLECTION.a" in cycle_str
    assert "COLLECTION.b" in cycle_str


def test_detect_cycle_three_nodes():
    """Test cycle detection with three nodes: A -> B -> C -> A"""
    slot_a = SlotKey(scope="COLLECTION", slot_name="a")
    slot_b = SlotKey(scope="COLLECTION", slot_name="b")
    slot_c = SlotKey(scope="COLLECTION", slot_name="c")

    graph = DependencyGraph(
        slots=(slot_a, slot_b, slot_c),
        edges=((slot_a, slot_b), (slot_b, slot_c), (slot_c, slot_a))
    )

    cycle = graph.detect_cycle()
    assert cycle is not None
    cycle_str = cycle.format()
    assert "COLLECTION.a" in cycle_str
    assert "COLLECTION.b" in cycle_str
    assert "COLLECTION.c" in cycle_str


def test_detect_cycle_complex():
    """Test cycle detection in complex graph with partial cycle"""
    slot_a = SlotKey(scope="COLLECTION", slot_name="a")
    slot_b = SlotKey(scope="COLLECTION", slot_name="b")
    slot_c = SlotKey(scope="COLLECTION", slot_name="c")
    slot_d = SlotKey(scope="COLLECTION", slot_name="d")

    # A -> B -> C -> B (cycle between B and C)
    # D is independent
    graph = DependencyGraph(
        slots=(slot_a, slot_b, slot_c, slot_d),
        edges=((slot_a, slot_b), (slot_b, slot_c), (slot_c, slot_b))
    )

    cycle = graph.detect_cycle()
    assert cycle is not None
    # Cycle should involve B and C
    cycle_str = cycle.format()
    assert "COLLECTION.b" in cycle_str
    assert "COLLECTION.c" in cycle_str


def test_validate_no_cycles_pass():
    """Test validate_no_cycles on acyclic graph"""
    slot_a = SlotKey(scope="COLLECTION", slot_name="a")
    slot_b = SlotKey(scope="COLLECTION", slot_name="b")

    graph = DependencyGraph(
        slots=(slot_a, slot_b),
        edges=((slot_a, slot_b),)
    )

    # Should not raise
    graph.validate_no_cycles()


def test_validate_no_cycles_fail():
    """Test validate_no_cycles raises on cyclic graph"""
    slot_a = SlotKey(scope="COLLECTION", slot_name="a")
    slot_b = SlotKey(scope="COLLECTION", slot_name="b")

    graph = DependencyGraph(
        slots=(slot_a, slot_b),
        edges=((slot_a, slot_b), (slot_b, slot_a))
    )

    with pytest.raises(DependencyCycleError) as exc_info:
        graph.validate_no_cycles()

    assert exc_info.value.cycle is not None
    assert "COLLECTION.a" in exc_info.value.cycle.format()


# ================================================================
# 跨 scope 依赖测试
# ================================================================

def test_cross_scope_dependencies():
    """Test dependencies across different scopes"""
    slot_db = SlotKey(scope="DATABASE", slot_name="name")
    slot_coll = SlotKey(scope="COLLECTION", slot_name="name")
    slot_idx = SlotKey(scope="INDEX", slot_name="name")

    # Collection.name depends on Database.name
    # Index.name depends on Collection.name
    graph = DependencyGraph(
        slots=(slot_db, slot_coll, slot_idx),
        edges=((slot_coll, slot_db), (slot_idx, slot_coll))
    )

    # Verify dependencies are tracked correctly across scopes
    assert graph.get_dependencies(slot_coll) == (slot_db,)
    assert graph.get_dependencies(slot_idx) == (slot_coll,)

    # Topological sort should respect scope boundaries
    result = graph.topological_sort()
    assert result.index(slot_db) < result.index(slot_coll)
    assert result.index(slot_coll) < result.index(slot_idx)


# ================================================================
# 集成测试：SemanticValidator + DependencyGraph
# ================================================================

def test_integration_with_validator():
    """Test DependencyGraph through SemanticValidator"""
    from contract.validator import ContractSchemaValidator
    from contract.semantic_validator import SemanticValidator

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

    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()
    result = semantic_validator.validate(validated)

    # Verify dependency graph is built
    assert result.dependency_graph is not None
    assert not result.dependency_graph.is_empty()
    assert len(result.dependency_graph.slots) == 3

    # Verify topological order: dimension -> top_k -> search_range
    sorted_slots = result.dependency_graph.topological_sort()
    slot_names = [s.slot_name for s in sorted_slots]
    assert slot_names.index("dimension") < slot_names.index("top_k")
    assert slot_names.index("top_k") < slot_names.index("search_range")


def test_integration_cycle_detection():
    """Test cycle detection through SemanticValidator"""
    from contract.validator import ContractSchemaValidator
    from contract.semantic_validator import SemanticValidator
    from contract.errors import DependencyCycleError

    data = {
        "core_slots": [
            {
                "slot_name": "a",
                "description": "Slot A",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [{"slot_name": "b", "reason": "A depends on B"}]
            },
            {
                "slot_name": "b",
                "description": "Slot B",
                "type": "integer",
                "scope": "COLLECTION",
                "depends_on": [{"slot_name": "a", "reason": "B depends on A"}]
            }
        ]
    }

    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(data)

    semantic_validator = SemanticValidator()

    with pytest.raises(DependencyCycleError) as exc_info:
        semantic_validator.validate(validated)

    # Verify cycle is detected
    assert exc_info.value.cycle is not None
    cycle_str = exc_info.value.cycle.format()
    assert "COLLECTION.a" in cycle_str
    assert "COLLECTION.b" in cycle_str
