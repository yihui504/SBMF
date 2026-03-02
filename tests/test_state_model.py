# tests/test_state_model.py
import pytest
from state.scoped import ScopedStateModel, StateIdentifier
from core.models import SlotScope

def test_state_model_collection_states():
    """Test StateModel returns valid states for COLLECTION scope"""
    model = ScopedStateModel()

    states = model.get_valid_states(SlotScope.COLLECTION)
    assert "empty" in states
    assert "has_data" in states
    assert "not_exist" in states
    assert "creating" in states
    assert "deleting" in states
    assert "error" in states

def test_state_model_transitions():
    """Test StateModel returns valid transitions for COLLECTION scope"""
    model = ScopedStateModel()

    transitions = model.get_valid_transitions(SlotScope.COLLECTION)
    assert "has_data" in transitions.get("empty", [])
    assert "empty" in transitions.get("has_data", [])
    assert "creating" in transitions.get("not_exist", [])

def test_state_model_is_transition_legal():
    """Test StateModel validates transition legality"""
    model = ScopedStateModel()

    # Valid transition
    assert model.is_transition_legal(SlotScope.COLLECTION, "empty", "has_data") is True

    # Invalid transition
    assert model.is_transition_legal(SlotScope.COLLECTION, "not_exist", "has_data") is False

def test_state_model_get_current_state():
    """Test StateModel returns current state (simplified for Phase 1)"""
    model = ScopedStateModel()

    state = model.get_current_state(SlotScope.COLLECTION, "test_collection", adapter=None)
    assert state == "not_exist"  # Simplified implementation

def test_state_identifier():
    """Test StateIdentifier dataclass"""
    from state.scoped import StateIdentifier

    id1 = StateIdentifier(scope=SlotScope.COLLECTION, name="test")
    id2 = StateIdentifier(scope=SlotScope.COLLECTION, name="test")
    id3 = StateIdentifier(scope=SlotScope.DATABASE, name="test")

    # Same scope and name should have same hash
    assert hash(id1) == hash(id2)
    # Different scope should have different hash
    assert hash(id1) != hash(id3)
