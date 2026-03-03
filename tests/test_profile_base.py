"""
Tests for BaseProfilePlugin Interface.

Tests BaseProfilePlugin abstract class and SkipDecision helper.
"""

import pytest
from profiles.base import BaseProfilePlugin, SkipDecision
from oracle.base import TestCase


# ================================================================
# Mock Profile Plugin for Testing
# ================================================================

class MockProfilePlugin(BaseProfilePlugin):
    """Mock implementation for testing"""

    def __init__(self, name: str = "MockProfile", skip_config: dict = None):
        super().__init__(name)
        self.skip_config = skip_config or {}

    def should_skip_test(self, test_case: TestCase) -> str:
        """Mock skip logic"""
        # Check dimension
        dimension = test_case.slot_values.get('dimension')
        if dimension is not None and dimension > 32768:
            return f"Dimension {dimension} exceeds maximum 32768"

        # Check metric + index combination
        metric = test_case.slot_values.get('metric_type')
        index = test_case.slot_values.get('index_type')
        if metric == 'COSINE' and index == 'HNSW':
            return "COSINE + HNSW not supported"

        return None

    def post_process_result(self, result):
        """Mock post-processing"""
        if isinstance(result, dict):
            # Add a processed flag
            result['_processed'] = True
        return result


# ================================================================
# BaseProfilePlugin Tests
# ================================================================

def test_profile_plugin_creation():
    """Test creating a profile plugin"""
    plugin = MockProfilePlugin(name="TestPlugin")

    assert plugin.get_name() == "TestPlugin"
    assert str(plugin) == "MockProfilePlugin(name='TestPlugin')"


def test_profile_plugin_default_name():
    """Test profile plugin with default name"""
    plugin = MockProfilePlugin()

    assert plugin.get_name() == "MockProfile"


def test_profile_plugin_repr():
    """Test __repr__ method"""
    plugin = MockProfilePlugin(name="MyProfile")

    repr_str = repr(plugin)
    assert "MockProfilePlugin" in repr_str
    assert "MyProfile" in repr_str


def test_should_skip_test_returns_none():
    """Test should_skip_test returning None (don't skip)"""
    plugin = MockProfilePlugin()

    test_case = TestCase(
        test_id="test_001",
        operation="search",
        slot_values={"dimension": 512, "metric_type": "L2"}
    )

    result = plugin.should_skip_test(test_case)
    assert result is None


def test_should_skip_test_returns_reason():
    """Test should_skip_test returning skip reason"""
    plugin = MockProfilePlugin()

    # Test dimension too large
    test_case = TestCase(
        test_id="test_002",
        operation="search",
        slot_values={"dimension": 99999}
    )

    result = plugin.should_skip_test(test_case)
    assert result is not None
    assert "99999" in result
    assert "exceeds maximum" in result


def test_should_skip_test_cosine_hnsw():
    """Test should_skip_test for COSINE + HNSW combination"""
    plugin = MockProfilePlugin()

    test_case = TestCase(
        test_id="test_003",
        operation="search",
        slot_values={"metric_type": "COSINE", "index_type": "HNSW"}
    )

    result = plugin.should_skip_test(test_case)
    assert result == "COSINE + HNSW not supported"


def test_post_process_result_dict():
    """Test post_process_result with dict input"""
    plugin = MockProfilePlugin()

    result = {"ids": [1, 2, 3], "scores": [0.1, 0.2, 0.3]}
    processed = plugin.post_process_result(result)

    assert processed["_processed"] is True
    assert processed["ids"] == [1, 2, 3]


def test_post_process_result_non_dict():
    """Test post_process_result with non-dict input"""
    plugin = MockProfilePlugin()

    result = "some string result"
    processed = plugin.post_process_result(result)

    assert processed == "some string result"


def test_validate_test_case_default():
    """Test default validate_test_case implementation"""
    plugin = MockProfilePlugin()

    test_case = TestCase(
        test_id="test_001",
        operation="search",
        slot_values={"dimension": 512}
    )

    result = plugin.validate_test_case(test_case)
    assert result is None


def test_get_supported_operations_default():
    """Test default get_supported_operations implementation"""
    plugin = MockProfilePlugin()

    result = plugin.get_supported_operations()
    assert result == []


def test_get_description_default():
    """Test default get_description implementation"""
    plugin = MockProfilePlugin(name="TestProfile")

    result = plugin.get_description()
    assert "TestProfile" in result
    assert "Profile Plugin" in result


# ================================================================
# Abstract Method Enforcement Tests
# ================================================================

def test_abstract_methods_must_be_implemented():
    """Test that abstract methods must be implemented"""
    with pytest.raises(TypeError):
        # Cannot instantiate abstract class directly
        BaseProfilePlugin(name="Test")


# ================================================================
# SkipDecision Tests
# ================================================================

def test_skip_decision_do_not_skip():
    """Test SkipDecision.do_not_skip()"""
    decision = SkipDecision.do_not_skip()

    assert decision.should_skip is False
    assert decision.reason is None
    assert decision.to_skip_reason() is None


def test_skip_decision_skip_with_reason():
    """Test SkipDecision.skip_with_reason()"""
    decision = SkipDecision.skip_with_reason("Feature not supported")

    assert decision.should_skip is True
    assert decision.reason == "Feature not supported"
    assert decision.category == SkipDecision.OTHER
    assert decision.to_skip_reason() == "Feature not supported"


def test_skip_decision_with_category():
    """Test SkipDecision with custom category"""
    decision = SkipDecision.skip_with_reason(
        "HNSW not supported",
        category=SkipDecision.NOT_SUPPORTED
    )

    assert decision.category == SkipDecision.NOT_SUPPORTED
    assert decision.to_skip_reason() == "[not_supported] HNSW not supported"


def test_skip_decision_to_skip_reason_not_skipping():
    """Test to_skip_reason when not skipping"""
    decision = SkipDecision(should_skip=False)

    assert decision.to_skip_reason() is None


def test_skip_decision_to_skip_reason_with_category_other():
    """Test to_skip_reason with OTHER category (no prefix)"""
    decision = SkipDecision(
        should_skip=True,
        reason="Some reason",
        category=SkipDecision.OTHER
    )

    result = decision.to_skip_reason()
    assert result == "Some reason"
    assert "[other]" not in result


def test_skip_decision_categories():
    """Test all skip decision categories"""
    categories = [
        SkipDecision.NOT_SUPPORTED,
        SkipDecision.CONFIG_LIMITATION,
        SkipDecision.VERSION_MISMATCH,
        SkipDecision.TEMPORARY_DISABLE,
        SkipDecision.OTHER,
    ]

    for category in categories:
        decision = SkipDecision.skip_with_reason("Test", category=category)
        assert decision.category == category


def test_skip_decision_custom_category():
    """Test SkipDecision with custom category string"""
    decision = SkipDecision(
        should_skip=True,
        reason="Custom skip",
        category="custom_category"
    )

    assert decision.category == "custom_category"
    assert decision.to_skip_reason() == "[custom_category] Custom skip"


# ================================================================
# Integration Tests
# ================================================================

def test_profile_plugin_full_workflow():
    """Test full workflow: validate -> skip -> process"""
    plugin = MockProfilePlugin(name="WorkflowTest")

    # Step 1: Create test case
    test_case = TestCase(
        test_id="workflow_001",
        operation="search",
        slot_values={"dimension": 512, "metric_type": "L2"}
    )

    # Step 2: Validate
    validation_result = plugin.validate_test_case(test_case)
    assert validation_result is None

    # Step 3: Check skip
    skip_reason = plugin.should_skip_test(test_case)
    assert skip_reason is None

    # Step 4: Post-process result
    raw_result = {"ids": [1, 2], "scores": [0.5, 0.3]}
    processed_result = plugin.post_process_result(raw_result)
    assert processed_result["_processed"] is True


def test_profile_plugin_skip_workflow():
    """Test workflow when test should be skipped"""
    plugin = MockProfilePlugin()

    test_case = TestCase(
        test_id="skip_001",
        operation="search",
        slot_values={"dimension": 99999}
    )

    skip_reason = plugin.should_skip_test(test_case)
    assert skip_reason is not None
    assert "exceeds maximum" in skip_reason


def test_multiple_profile_plugins():
    """Test using multiple profile plugins"""
    plugin1 = MockProfilePlugin(name="Profile1")
    plugin2 = MockProfilePlugin(name="Profile2")

    test_case = TestCase(
        test_id="multi_001",
        operation="search",
        slot_values={"dimension": 512}
    )

    # Both plugins should handle the same test case
    skip1 = plugin1.should_skip_test(test_case)
    skip2 = plugin2.should_skip_test(test_case)

    assert skip1 == skip2 == None


def test_profile_plugin_with_empty_slot_values():
    """Test profile plugin with empty slot values"""
    plugin = MockProfilePlugin()

    test_case = TestCase(
        test_id="empty_001",
        operation="search",
        slot_values={}
    )

    skip_reason = plugin.should_skip_test(test_case)
    assert skip_reason is None  # No reason to skip
