"""
Tests for Profile Plugin Errors.

Tests ProfileError and its subclasses.
"""

import pytest
from profiles.errors import (
    ProfileError,
    ProfileSkipError,
    ProfilePostProcessError,
    ProfileRegistrationError,
)


# ================================================================
# ProfileError Tests
# ================================================================

def test_profile_error_basic():
    """Test basic ProfileError creation"""
    error = ProfileError("Something went wrong")

    assert str(error) == "Something went wrong"
    assert error.message == "Something went wrong"
    assert error.profile_name is None
    assert error.context == {}


def test_profile_error_with_profile_name():
    """Test ProfileError with profile name"""
    error = ProfileError(
        message="Connection failed",
        profile_name="SeekDB"
    )

    assert "[SeekDB]" in str(error)
    assert "Connection failed" in str(error)
    assert error.profile_name == "SeekDB"


def test_profile_error_with_context():
    """Test ProfileError with context"""
    error = ProfileError(
        message="Invalid parameter",
        context={"param": "dimension", "value": -1}
    )

    assert "Invalid parameter" in str(error)
    assert "(param=dimension, value=-1)" in str(error)
    assert error.context == {"param": "dimension", "value": -1}


def test_profile_error_full():
    """Test ProfileError with all fields"""
    error = ProfileError(
        message="Database error",
        profile_name="TestDB",
        context={"host": "localhost", "port": 5432}
    )

    error_str = str(error)
    assert "[TestDB]" in error_str
    assert "Database error" in error_str
    assert "host=localhost" in error_str
    assert "port=5432" in error_str


def test_profile_error_to_dict():
    """Test ProfileError to_dict conversion"""
    error = ProfileError(
        message="Test error",
        profile_name="TestProfile",
        context={"key": "value"}
    )

    result = error.to_dict()
    assert result["error_type"] == "ProfileError"
    assert result["message"] == "Test error"
    assert result["profile_name"] == "TestProfile"
    assert result["context"] == {"key": "value"}


def test_profile_error_is_exception():
    """Test that ProfileError is an Exception"""
    error = ProfileError("Test")

    assert isinstance(error, Exception)
    assert isinstance(error, ProfileError)

    # Can be raised and caught
    with pytest.raises(ProfileError, match="Test"):
        raise error


# ================================================================
# ProfileSkipError Tests
# ================================================================

def test_skip_error_basic():
    """Test basic ProfileSkipError creation"""
    error = ProfileSkipError(skip_reason="Feature not supported")

    assert "SKIP:" in str(error)
    assert "Feature not supported" in str(error)
    assert error.skip_reason == "Feature not supported"
    assert error.test_case_id is None


def test_skip_error_with_test_case_id():
    """Test ProfileSkipError with test case ID"""
    error = ProfileSkipError(
        skip_reason="COSINE + HNSW not supported",
        test_case_id="test_001"
    )

    error_str = str(error)
    assert "SKIP:" in error_str
    assert "COSINE + HNSW not supported" in error_str
    assert "test_case_id=test_001" in error_str
    assert error.test_case_id == "test_001"


def test_skip_error_with_profile_name():
    """Test ProfileSkipError with profile name"""
    error = ProfileSkipError(
        skip_reason="Invalid dimension",
        profile_name="SeekDB"
    )

    error_str = str(error)
    assert "[SeekDB]" in error_str
    assert "SKIP:" in error_str
    assert "Invalid dimension" in error_str
    assert error.profile_name == "SeekDB"


def test_skip_error_with_context():
    """Test ProfileSkipError with additional context"""
    error = ProfileSkipError(
        skip_reason="Dimension out of range",
        test_case_id="test_002",
        context={"dimension": 99999, "max": 32768}
    )

    error_str = str(error)
    assert "Dimension out of range" in error_str
    assert "test_case_id=test_002" in error_str
    assert "dimension=99999" in error_str
    assert "max=32768" in error_str


def test_skip_error_to_dict():
    """Test ProfileSkipError to_dict conversion"""
    error = ProfileSkipError(
        skip_reason="Not supported",
        test_case_id="test_001",
        profile_name="TestDB"
    )

    result = error.to_dict()
    assert result["error_type"] == "ProfileSkipError"
    assert result["message"] == "Not supported"
    assert result["profile_name"] == "TestDB"
    assert result["context"]["test_case_id"] == "test_001"


def test_skip_error_inheritance():
    """Test that ProfileSkipError inherits from ProfileError"""
    error = ProfileSkipError(skip_reason="Test")

    assert isinstance(error, ProfileError)
    assert isinstance(error, Exception)

    # Can be caught as ProfileError
    try:
        raise error
    except ProfileError as e:
        assert e.skip_reason == "Test"


# ================================================================
# ProfilePostProcessError Tests
# ================================================================

def test_post_process_error_basic():
    """Test basic ProfilePostProcessError creation"""
    error = ProfilePostProcessError(
        message="Failed to parse result"
    )

    assert "POST_PROCESS_ERROR:" in str(error)
    assert "Failed to parse result" in str(error)
    assert error.original_result is None
    assert error.processing_step is None


def test_post_process_error_with_result():
    """Test ProfilePostProcessError with original result"""
    original = {"raw": "invalid data"}
    error = ProfilePostProcessError(
        message="Cannot parse",
        original_result=original
    )

    assert error.original_result == original
    assert "Cannot parse" in str(error)


def test_post_process_error_with_step():
    """Test ProfilePostProcessError with processing step"""
    error = ProfilePostProcessError(
        message="Validation failed",
        processing_step="validate_scores"
    )

    error_str = str(error)
    assert "POST_PROCESS_ERROR:" in error_str
    assert "Validation failed" in error_str
    assert "processing_step=validate_scores" in error_str
    assert error.processing_step == "validate_scores"


def test_post_process_error_full():
    """Test ProfilePostProcessError with all fields"""
    original = {"ids": [1, 2], "scores": "invalid"}
    error = ProfilePostProcessError(
        message="Invalid score format",
        original_result=original,
        processing_step="normalize_scores",
        profile_name="SeekDB"
    )

    error_str = str(error)
    assert "[SeekDB]" in error_str
    assert "POST_PROCESS_ERROR:" in error_str
    assert "Invalid score format" in error_str
    assert "processing_step=normalize_scores" in error_str


def test_post_process_error_to_dict():
    """Test ProfilePostProcessError to_dict conversion"""
    error = ProfilePostProcessError(
        message="Process failed",
        original_result={"data": "test"},
        processing_step="step1"
    )

    result = error.to_dict()
    assert result["error_type"] == "ProfilePostProcessError"
    assert result["message"] == "Process failed"
    assert result["context"]["processing_step"] == "step1"


def test_post_process_error_inheritance():
    """Test that ProfilePostProcessError inherits from ProfileError"""
    error = ProfilePostProcessError(message="Test")

    assert isinstance(error, ProfileError)
    assert isinstance(error, Exception)


# ================================================================
# ProfileRegistrationError Tests
# ================================================================

def test_registration_error_basic():
    """Test basic ProfileRegistrationError creation"""
    error = ProfileRegistrationError(
        message="Profile already exists"
    )

    assert "REGISTRATION_ERROR:" in str(error)
    assert "Profile already exists" in str(error)


def test_registration_error_with_profile_name():
    """Test ProfileRegistrationError with profile name"""
    error = ProfileRegistrationError(
        message="Duplicate registration",
        profile_name="SeekDB"
    )

    error_str = str(error)
    assert "[SeekDB]" in error_str
    assert "REGISTRATION_ERROR:" in error_str
    assert "Duplicate registration" in error_str
    assert error.profile_name == "SeekDB"


def test_registration_error_with_context():
    """Test ProfileRegistrationError with context"""
    error = ProfileRegistrationError(
        message="Profile not found",
        profile_name="MissingDB",
        context={"available": ["SeekDB", "Milvus"]}
    )

    error_str = str(error)
    assert "Profile not found" in error_str
    assert "available=" in error_str
    assert error.context["available"] == ["SeekDB", "Milvus"]


def test_registration_error_to_dict():
    """Test ProfileRegistrationError to_dict conversion"""
    error = ProfileRegistrationError(
        message="Registration failed",
        profile_name="TestDB"
    )

    result = error.to_dict()
    assert result["error_type"] == "ProfileRegistrationError"
    assert result["message"] == "Registration failed"
    assert result["profile_name"] == "TestDB"


def test_registration_error_inheritance():
    """Test that ProfileRegistrationError inherits from ProfileError"""
    error = ProfileRegistrationError(message="Test")

    assert isinstance(error, ProfileError)
    assert isinstance(error, Exception)


# ================================================================
# Integration Tests
# ================================================================

def test_catch_all_profile_errors():
    """Test catching all ProfileError subclasses"""
    errors = [
        ProfileError("Base error"),
        ProfileSkipError("Skip", test_case_id="test_1"),
        ProfilePostProcessError("Post process", processing_step="step1"),
        ProfileRegistrationError("Registration", profile_name="TestDB"),
    ]

    for error in errors:
        try:
            raise error
        except ProfileError as e:
            # All should be catchable as ProfileError
            assert e is error


def test_error_message_clarity():
    """Test that error messages are clear and informative"""
    # Skip error
    skip_error = ProfileSkipError(
        skip_reason="HNSW not supported for COSINE",
        test_case_id="test_cosine_hnsw"
    )
    skip_msg = str(skip_error)
    assert "SKIP" in skip_msg
    assert "HNSW not supported for COSINE" in skip_msg

    # Post process error
    post_error = ProfilePostProcessError(
        message="Failed to extract scores",
        processing_step="extract_scores",
        original_result={"data": "malformed"}
    )
    post_msg = str(post_error)
    assert "POST_PROCESS_ERROR" in post_msg
    assert "Failed to extract scores" in post_msg
    assert "extract_scores" in post_msg

    # Registration error
    reg_error = ProfileRegistrationError(
        message="Profile 'SeekDB' already registered",
        profile_name="Registry"
    )
    reg_msg = str(reg_error)
    assert "REGISTRATION_ERROR" in reg_msg
    assert "already registered" in reg_msg
