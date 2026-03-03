"""
Tests for Profile Plugin Registry.

Tests ProfilePluginRegistry class and global registry functions.
"""

import pytest
from profiles import (
    ProfilePluginRegistry,
    register_profile,
    get_profile,
    unregister_profile,
    list_profiles,
    get_all_profiles,
    get_global_registry,
    reset_global_registry,
    SeekDBProfilePlugin,
    ProfileRegistrationError,
    BaseProfilePlugin,
)
from oracle.base import TestCase


# ================================================================
# Mock Profile for Testing
# ================================================================

class MockProfile(BaseProfilePlugin):
    """Mock profile for testing"""

    def __init__(self, name="MockProfile"):
        super().__init__(name)
        self.should_skip_return = None

    def should_skip_test(self, test_case: TestCase) -> str:
        return self.should_skip_return

    def post_process_result(self, result):
        return result


# ================================================================
# Test Fixtures
# ================================================================

@pytest.fixture
def clean_registry():
    """Provide a clean registry for each test"""
    registry = ProfilePluginRegistry()
    yield registry
    # Cleanup is automatic since registry is local


@pytest.fixture
def mock_profile():
    """Provide a mock profile instance"""
    return MockProfile("TestMock")


# ================================================================
# Basic Registration Tests
# ================================================================

def test_register_profile(clean_registry, mock_profile):
    """Test basic profile registration"""
    clean_registry.register("mock", mock_profile)

    assert clean_registry.is_registered("mock")
    assert clean_registry.count() == 1
    assert "mock" in clean_registry.list_all()


def test_register_multiple_profiles(clean_registry):
    """Test registering multiple profiles"""
    profile1 = MockProfile("Profile1")
    profile2 = MockProfile("Profile2")
    profile3 = SeekDBProfilePlugin(enable_logging=False)

    clean_registry.register("p1", profile1)
    clean_registry.register("p2", profile2)
    clean_registry.register("seekdb", profile3)

    assert clean_registry.count() == 3
    assert set(clean_registry.list_all()) == {"p1", "p2", "seekdb"}


def test_register_duplicate_disallowed(clean_registry, mock_profile):
    """Test that duplicate registration raises error by default"""
    clean_registry.register("mock", mock_profile)

    with pytest.raises(ProfileRegistrationError, match="already registered"):
        clean_registry.register("mock", mock_profile)


def test_register_duplicate_allowed_with_overwrite(clean_registry, mock_profile):
    """Test that duplicate registration works when allow_overwrite=True"""
    registry = ProfilePluginRegistry(allow_overwrite=True)

    profile1 = mock_profile
    profile2 = MockProfile("NewMock")

    registry.register("mock", profile1)
    assert registry.get("mock") is profile1

    registry.register("mock", profile2)
    assert registry.get("mock") is profile2


# ================================================================
# Get Profile Tests
# ================================================================

def test_get_existing_profile(clean_registry, mock_profile):
    """Test getting an existing profile"""
    clean_registry.register("mock", mock_profile)

    retrieved = clean_registry.get("mock")

    assert retrieved is mock_profile
    assert retrieved.get_name() == "TestMock"


def test_get_nonexistent_profile(clean_registry):
    """Test getting a nonexistent profile returns None"""
    result = clean_registry.get("nonexistent")

    assert result is None


def test_get_or_raise_success(clean_registry, mock_profile):
    """Test get_or_raise with existing profile"""
    clean_registry.register("mock", mock_profile)

    retrieved = clean_registry.get_or_raise("mock")

    assert retrieved is mock_profile


def test_get_or_raise_failure(clean_registry):
    """Test get_or_raise with nonexistent profile raises error"""
    with pytest.raises(ProfileRegistrationError, match="not registered"):
        clean_registry.get_or_raise("nonexistent")


# ================================================================
# Unregister Tests
# ================================================================

def test_unregister_existing_profile(clean_registry, mock_profile):
    """Test unregistering an existing profile"""
    clean_registry.register("mock", mock_profile)

    result = clean_registry.unregister("mock")

    assert result is True
    assert not clean_registry.is_registered("mock")
    assert clean_registry.count() == 0


def test_unregister_nonexistent_profile(clean_registry):
    """Test unregistering a nonexistent profile returns False"""
    result = clean_registry.unregister("nonexistent")

    assert result is False


def test_unregister_and_reregister(clean_registry, mock_profile):
    """Test that profile can be re-registered after unregister"""
    clean_registry.register("mock", mock_profile)
    clean_registry.unregister("mock")

    # Should be able to register again without error
    new_profile = MockProfile("NewMock")
    clean_registry.register("mock", new_profile)

    assert clean_registry.get("mock") is new_profile


# ================================================================
# List and Query Tests
# ================================================================

def test_list_all_returns_names(clean_registry):
    """Test list_all returns profile names"""
    clean_registry.register("p1", MockProfile("P1"))
    clean_registry.register("p2", MockProfile("P2"))
    clean_registry.register("p3", MockProfile("P3"))

    names = clean_registry.list_all()

    assert set(names) == {"p1", "p2", "p3"}
    assert len(names) == 3


def test_list_all_empty_registry(clean_registry):
    """Test list_all on empty registry"""
    names = clean_registry.list_all()

    assert names == []


def test_get_all_returns_instances(clean_registry):
    """Test get_all returns profile instances"""
    p1 = MockProfile("P1")
    p2 = MockProfile("P2")

    clean_registry.register("p1", p1)
    clean_registry.register("p2", p2)

    profiles = clean_registry.get_all()

    assert len(profiles) == 2
    assert p1 in profiles
    assert p2 in profiles


def test_count(clean_registry):
    """Test count method"""
    assert clean_registry.count() == 0

    clean_registry.register("p1", MockProfile("P1"))
    assert clean_registry.count() == 1

    clean_registry.register("p2", MockProfile("P2"))
    assert clean_registry.count() == 2

    clean_registry.unregister("p1")
    assert clean_registry.count() == 1


def test_is_registered(clean_registry, mock_profile):
    """Test is_registered method"""
    assert not clean_registry.is_registered("mock")

    clean_registry.register("mock", mock_profile)
    assert clean_registry.is_registered("mock")


# ================================================================
# Clear Tests
# ================================================================

def test_clear_registry(clean_registry):
    """Test clearing the registry"""
    clean_registry.register("p1", MockProfile("P1"))
    clean_registry.register("p2", MockProfile("P2"))
    clean_registry.register("p3", MockProfile("P3"))

    assert clean_registry.count() == 3

    clean_registry.clear()

    assert clean_registry.count() == 0
    assert clean_registry.list_all() == []


# ================================================================
# Get Info Tests
# ================================================================

def test_get_info_existing_profile(clean_registry, mock_profile):
    """Test getting info for existing profile"""
    clean_registry.register("mock", mock_profile)

    info = clean_registry.get_info("mock")

    assert info is not None
    assert info["name"] == "mock"
    assert info["type"] == "MockProfile"
    assert info["plugin_name"] == "TestMock"
    assert "description" in info


def test_get_info_seekdb_profile(clean_registry):
    """Test getting info for SeekDB profile"""
    profile = SeekDBProfilePlugin(enable_logging=False)
    clean_registry.register("seekdb", profile)

    info = clean_registry.get_info("seekdb")

    assert info["name"] == "seekdb"
    assert info["type"] == "SeekDBProfilePlugin"
    assert "SeekDB" in info["description"]


def test_get_info_nonexistent_profile(clean_registry):
    """Test getting info for nonexistent profile returns None"""
    info = clean_registry.get_info("nonexistent")

    assert info is None


# ================================================================
# Validation Tests
# ================================================================

def test_register_with_invalid_name(clean_registry, mock_profile):
    """Test registering with invalid name raises ValueError"""
    with pytest.raises(ValueError, match="non-empty string"):
        clean_registry.register("", mock_profile)

    with pytest.raises(ValueError, match="non-empty string"):
        clean_registry.register(None, mock_profile)


def test_register_with_invalid_profile(clean_registry):
    """Test registering non-BaseProfilePlugin raises ValueError"""
    with pytest.raises(ValueError, match="BaseProfilePlugin"):
        clean_registry.register("invalid", "not a profile")


# ================================================================
# Magic Methods Tests
# ================================================================

def test_contains_operator(clean_registry, mock_profile):
    """Test 'in' operator"""
    clean_registry.register("mock", mock_profile)

    assert "mock" in clean_registry
    assert "nonexistent" not in clean_registry


def test_len_function(clean_registry):
    """Test len() function"""
    assert len(clean_registry) == 0

    clean_registry.register("p1", MockProfile("P1"))
    assert len(clean_registry) == 1

    clean_registry.register("p2", MockProfile("P2"))
    assert len(clean_registry) == 2


def test_repr(clean_registry):
    """Test __repr__ method"""
    clean_registry.register("p1", MockProfile("P1"))
    clean_registry.register("p2", MockProfile("P2"))

    repr_str = repr(clean_registry)

    assert "ProfilePluginRegistry" in repr_str
    assert "count=2" in repr_str
    assert "p1" in repr_str
    assert "p2" in repr_str


# ================================================================
# Global Registry Tests
# ================================================================

def test_global_registry_is_singleton():
    """Test that global registry is a singleton"""
    reset_global_registry()

    registry1 = get_global_registry()
    registry2 = get_global_registry()

    assert registry1 is registry2


def test_register_profile_to_global():
    """Test registering to global registry"""
    reset_global_registry()

    profile = MockProfile("GlobalMock")
    register_profile("global", profile)

    retrieved = get_profile("global")

    assert retrieved is profile


def test_list_profiles_global():
    """Test listing profiles from global registry"""
    reset_global_registry()

    register_profile("p1", MockProfile("P1"))
    register_profile("p2", MockProfile("P2"))

    names = list_profiles()

    assert set(names) == {"p1", "p2"}


def test_get_all_profiles_global():
    """Test getting all profiles from global registry"""
    reset_global_registry()

    p1 = MockProfile("P1")
    p2 = MockProfile("P2")

    register_profile("p1", p1)
    register_profile("p2", p2)

    profiles = get_all_profiles()

    assert len(profiles) == 2
    assert p1 in profiles
    assert p2 in profiles


def test_unregister_profile_from_global():
    """Test unregistering from global registry"""
    reset_global_registry()

    profile = MockProfile("GlobalMock")
    register_profile("global", profile)

    result = unregister_profile("global")

    assert result is True
    assert get_profile("global") is None


def test_reset_global_registry():
    """Test resetting global registry"""
    register_profile("p1", MockProfile("P1"))
    register_profile("p2", MockProfile("P2"))

    assert get_global_registry().count() == 2

    reset_global_registry()

    assert get_global_registry().count() == 0


# ================================================================
# Integration Tests
# ================================================================

def test_register_and_use_seekdb_profile():
    """Test registering and using SeekDB profile through registry"""
    reset_global_registry()

    profile = SeekDBProfilePlugin(enable_logging=False)
    register_profile("seekdb", profile)

    # Retrieve and use
    retrieved = get_profile("seekdb")

    test_case = TestCase(
        test_id="test_001",
        operation="search",
        slot_values={"dimension": 512}
    )

    skip_reason = retrieved.should_skip_test(test_case)
    assert skip_reason is None  # Valid test case

    # Test with invalid case
    invalid_case = TestCase(
        test_id="test_002",
        operation="search",
        slot_values={"dimension": 99999}  # Exceeds max
    )

    skip_reason = retrieved.should_skip_test(invalid_case)
    assert skip_reason is not None
    assert "exceeds maximum" in skip_reason


def test_multiple_isolated_registries():
    """Test that multiple registries are isolated"""
    registry1 = ProfilePluginRegistry()
    registry2 = ProfilePluginRegistry()

    profile1 = MockProfile("Profile1")
    profile2 = MockProfile("Profile2")

    registry1.register("p", profile1)
    registry2.register("p", profile2)

    # Each registry should have its own profile
    assert registry1.get("p") is profile1
    assert registry2.get("p") is profile2

    # Clearing one shouldn't affect the other
    registry1.clear()
    assert registry1.count() == 0
    assert registry2.count() == 1


def test_registry_with_seekdb_and_mock_profiles():
    """Test registry with mixed profile types"""
    registry = ProfilePluginRegistry()

    mock = MockProfile("Mock")
    seekdb = SeekDBProfilePlugin(enable_logging=False)

    registry.register("mock", mock)
    registry.register("seekdb", seekdb)

    assert registry.count() == 2

    # Get info for each
    mock_info = registry.get_info("mock")
    seekdb_info = registry.get_info("seekdb")

    assert mock_info["type"] == "MockProfile"
    assert seekdb_info["type"] == "SeekDBProfilePlugin"
