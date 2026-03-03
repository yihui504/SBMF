"""
Tests for SeekDBProfilePlugin.

Tests SeekDB-specific skip logic and result post-processing.
"""

import pytest
from profiles import SeekDBProfilePlugin, SeekDBConstants
from oracle.base import TestCase


# ================================================================
# Fixtures
# ================================================================

@pytest.fixture
def seekdb_profile():
    """Create a SeekDBProfilePlugin instance with logging disabled for tests"""
    return SeekDBProfilePlugin(enable_logging=False)


@pytest.fixture
def valid_test_case():
    """Create a valid test case"""
    return TestCase(
        test_id="test_001",
        operation="search",
        slot_values={
            "dimension": 512,
            "metric_type": "L2",
            "top_k": 10
        }
    )


# ================================================================
# Basic Tests
# ================================================================

def test_seekdb_profile_creation():
    """Test SeekDBProfilePlugin creation"""
    profile = SeekDBProfilePlugin()

    assert profile.get_name() == "SeekDBProfilePlugin"
    assert profile.enable_logging is True


def test_seekdb_profile_without_logging():
    """Test SeekDBProfilePlugin without logging"""
    profile = SeekDBProfilePlugin(enable_logging=False)

    assert profile.enable_logging is False
    assert profile.logger is None


def test_seekdb_profile_supported_operations():
    """Test get_supported_operations"""
    profile = SeekDBProfilePlugin(enable_logging=False)

    operations = profile.get_supported_operations()

    assert "search" in operations
    assert "insert" in operations
    assert "delete" in operations
    assert "create_index" in operations


def test_seekdb_profile_description():
    """Test get_description"""
    profile = SeekDBProfilePlugin(enable_logging=False)

    description = profile.get_description()

    assert "SeekDB" in description
    assert "L2" in description


# ================================================================
# Skip Logic - Unsupported Combinations
# ================================================================

def test_skip_cosine_hnsw_combination(seekdb_profile):
    """Test skipping COSINE + HNSW combination"""
    test_case = TestCase(
        test_id="test_cosine_hnsw",
        operation="search",
        slot_values={
            "metric_type": "COSINE",
            "index_type": "HNSW"
        }
    )

    result = seekdb_profile.should_skip_test(test_case)

    assert result is not None
    assert "COSINE" in result
    assert "HNSW" in result
    assert "not supported" in result


def test_allow_l2_hnsw_combination(seekdb_profile):
    """Test L2 + HNSW is allowed"""
    test_case = TestCase(
        test_id="test_l2_hnsw",
        operation="search",
        slot_values={
            "metric_type": "L2",
            "index_type": "HNSW"
        }
    )

    result = seekdb_profile.should_skip_test(test_case)

    assert result is None


# ================================================================
# Skip Logic - Dimension Range
# ================================================================

def test_skip_dimension_below_minimum(seekdb_profile):
    """Test skipping dimension below minimum"""
    test_case = TestCase(
        test_id="test_dim_low",
        operation="search",
        slot_values={"dimension": 0}
    )

    result = seekdb_profile.should_skip_test(test_case)

    assert result is not None
    assert "below minimum" in result
    assert "1" in result


def test_skip_dimension_above_maximum(seekdb_profile):
    """Test skipping dimension above maximum"""
    test_case = TestCase(
        test_id="test_dim_high",
        operation="search",
        slot_values={"dimension": 40000}
    )

    result = seekdb_profile.should_skip_test(test_case)

    assert result is not None
    assert "exceeds maximum" in result
    assert "32768" in result


def test_skip_dimension_negative(seekdb_profile):
    """Test skipping negative dimension"""
    test_case = TestCase(
        test_id="test_dim_neg",
        operation="search",
        slot_values={"dimension": -100}
    )

    result = seekdb_profile.should_skip_test(test_case)

    assert result is not None
    assert "below minimum" in result


def test_allow_valid_dimensions(seekdb_profile):
    """Test valid dimensions are allowed"""
    valid_dimensions = [1, 100, 512, 1024, 32768]

    for dim in valid_dimensions:
        test_case = TestCase(
            test_id=f"test_dim_{dim}",
            operation="search",
            slot_values={"dimension": dim}
        )

        result = seekdb_profile.should_skip_test(test_case)
        assert result is None, f"Dimension {dim} should be allowed"


def test_skip_dimension_invalid_type(seekdb_profile):
    """Test skipping invalid dimension type"""
    test_case = TestCase(
        test_id="test_dim_type",
        operation="search",
        slot_values={"dimension": "invalid"}
    )

    result = seekdb_profile.should_skip_test(test_case)

    assert result is not None
    assert "must be a number" in result


# ================================================================
# Skip Logic - ef_construction
# ================================================================

def test_skip_ef_construction_too_large(seekdb_profile):
    """Test skipping ef_construction too large"""
    test_case = TestCase(
        test_id="test_ef_high",
        operation="create_index",
        slot_values={"ef_construction": 600}
    )

    result = seekdb_profile.should_skip_test(test_case)

    assert result is not None
    assert "exceeds maximum" in result
    assert "500" in result


def test_allow_valid_ef_construction(seekdb_profile):
    """Test valid ef_construction values"""
    valid_values = [1, 40, 100, 500]

    for ef in valid_values:
        test_case = TestCase(
            test_id=f"test_ef_{ef}",
            operation="create_index",
            slot_values={"ef_construction": ef}
        )

        result = seekdb_profile.should_skip_test(test_case)
        assert result is None, f"ef_construction {ef} should be allowed"


# ================================================================
# Skip Logic - top_k
# ================================================================

def test_skip_top_k_too_large(seekdb_profile):
    """Test skipping top_k too large"""
    test_case = TestCase(
        test_id="test_topk_high",
        operation="search",
        slot_values={"top_k": 20000}
    )

    result = seekdb_profile.should_skip_test(test_case)

    assert result is not None
    assert "exceeds maximum" in result


def test_skip_top_k_below_one(seekdb_profile):
    """Test skipping top_k below 1"""
    test_case = TestCase(
        test_id="test_topk_low",
        operation="search",
        slot_values={"top_k": 0}
    )

    result = seekdb_profile.should_skip_test(test_case)

    assert result is not None
    assert "at least 1" in result


# ================================================================
# Skip Logic - search_range
# ================================================================

def test_skip_search_range_too_large(seekdb_profile):
    """Test skipping search_range too large"""
    test_case = TestCase(
        test_id="test_range_high",
        operation="search",
        slot_values={"search_range": 70000}
    )

    result = seekdb_profile.should_skip_test(test_case)

    assert result is not None
    assert "exceeds maximum" in result


def test_skip_search_range_below_one(seekdb_profile):
    """Test skipping search_range below 1"""
    test_case = TestCase(
        test_id="test_range_low",
        operation="search",
        slot_values={"search_range": 0}
    )

    result = seekdb_profile.should_skip_test(test_case)

    assert result is not None
    assert "at least 1" in result


# ================================================================
# Skip Logic - Metric Type
# ================================================================

def test_skip_unsupported_metric_type(seekdb_profile):
    """Test skipping unsupported metric type"""
    test_case = TestCase(
        test_id="test_metric_bad",
        operation="search",
        slot_values={"metric_type": "HAMMING"}
    )

    result = seekdb_profile.should_skip_test(test_case)

    assert result is not None
    assert "not supported" in result
    assert "HAMMING" in result


def test_allow_supported_metric_types(seekdb_profile):
    """Test all supported metric types"""
    for metric in SeekDBConstants.SUPPORTED_METRIC_TYPES:
        test_case = TestCase(
            test_id=f"test_metric_{metric}",
            operation="search",
            slot_values={"metric_type": metric}
        )

        result = seekdb_profile.should_skip_test(test_case)
        assert result is None, f"Metric type {metric} should be supported"


# ================================================================
# Skip Logic - Index Type
# ================================================================

def test_skip_unsupported_index_type(seekdb_profile):
    """Test skipping unsupported index type"""
    test_case = TestCase(
        test_id="test_index_bad",
        operation="create_index",
        slot_values={"index_type": "ANNOY"}
    )

    result = seekdb_profile.should_skip_test(test_case)

    assert result is not None
    assert "not supported" in result


def test_allow_supported_index_types(seekdb_profile):
    """Test all supported index types"""
    for index in SeekDBConstants.SUPPORTED_INDEX_TYPES:
        test_case = TestCase(
            test_id=f"test_index_{index}",
            operation="create_index",
            slot_values={"index_type": index}
        )

        result = seekdb_profile.should_skip_test(test_case)
        assert result is None, f"Index type {index} should be supported"


# ================================================================
# Post-Process Logic - Dict Results
# ================================================================

def test_post_process_dict_with_ids_and_scores(seekdb_profile):
    """Test post-processing dict with ids and scores"""
    result = {
        "ids": [1, 2, 3],
        "scores": [0.9, 0.8, 0.7]
    }

    processed = seekdb_profile.post_process_result(result)

    assert processed["ids"] == [1, 2, 3]
    assert processed["scores"] == [0.9, 0.8, 0.7]
    assert processed["total"] == 3
    assert "_processed_by" in processed


def test_post_process_dict_without_total(seekdb_profile):
    """Test post-processing dict without total field"""
    result = {
        "ids": [1, 2, 3, 4, 5]
    }

    processed = seekdb_profile.post_process_result(result)

    assert processed["total"] == 5
    assert processed["scores"] == []


def test_post_process_dict_with_single_score(seekdb_profile):
    """Test post-processing dict with single score field"""
    result = {
        "ids": [1, 2, 3],
        "score": [0.1, 0.2, 0.3]
    }

    processed = seekdb_profile.post_process_result(result)

    assert "scores" in processed
    assert processed["scores"] == [0.1, 0.2, 0.3]
    assert "score" not in processed


def test_post_process_dict_single_score_value(seekdb_profile):
    """Test post-processing dict with single score value"""
    result = {
        "ids": [1, 2, 3],
        "score": 0.95
    }

    processed = seekdb_profile.post_process_result(result)

    assert processed["scores"] == [0.95]


def test_post_process_empty_dict(seekdb_profile):
    """Test post-processing empty dict"""
    result = {}

    processed = seekdb_profile.post_process_result(result)

    assert processed["ids"] == []
    assert processed["scores"] == []
    assert processed["total"] == 0


# ================================================================
# Post-Process Logic - List Results
# ================================================================

def test_post_process_list_of_integers(seekdb_profile):
    """Test post-processing list of integers (assumed ids)"""
    result = [1, 2, 3, 4, 5]

    processed = seekdb_profile.post_process_result(result)

    assert processed["ids"] == [1, 2, 3, 4, 5]
    assert processed["scores"] == []
    assert processed["total"] == 5


def test_post_process_list_of_dicts(seekdb_profile):
    """Test post-processing list of dicts"""
    result = [
        {"id": 1, "score": 0.9},
        {"id": 2, "score": 0.8},
        {"id": 3, "distance": 0.1}
    ]

    processed = seekdb_profile.post_process_result(result)

    assert processed["ids"] == [1, 2, 3]
    assert processed["scores"] == [0.9, 0.8, 0.1]
    assert processed["total"] == 3


def test_post_process_list_of_dicts_with_distance(seekdb_profile):
    """Test post-processing list with distance field"""
    result = [
        {"id": 1, "distance": 0.5},
        {"id": 2, "distance": 0.3}
    ]

    processed = seekdb_profile.post_process_result(result)

    assert processed["scores"] == [0.5, 0.3]


def test_post_process_non_list_non_dict(seekdb_profile):
    """Test post-processing non-list, non-dict result"""
    result = "some string result"

    processed = seekdb_profile.post_process_result(result)

    assert processed == "some string result"


def test_post_process_none(seekdb_profile):
    """Test post-processing None result"""
    result = None

    processed = seekdb_profile.post_process_result(result)

    assert processed is None


# ================================================================
# Integration Tests
# ================================================================

def test_full_workflow_no_skip(seekdb_profile, valid_test_case):
    """Test full workflow with valid test case"""
    skip_reason = seekdb_profile.should_skip_test(valid_test_case)
    assert skip_reason is None

    result = {"ids": [1, 2], "scores": [0.5, 0.3]}
    processed = seekdb_profile.post_process_result(result)
    assert processed["total"] == 2


def test_full_workflow_with_skip(seekdb_profile):
    """Test full workflow with skipped test case"""
    test_case = TestCase(
        test_id="test_skip",
        operation="search",
        slot_values={"metric_type": "COSINE", "index_type": "HNSW"}
    )

    skip_reason = seekdb_profile.should_skip_test(test_case)
    assert skip_reason is not None


def test_multiple_skip_reasons_first_wins(seekdb_profile):
    """Test that first skip reason is returned"""
    test_case = TestCase(
        test_id="test_multi",
        operation="search",
        slot_values={
            "metric_type": "COSINE",  # Triggers combination skip
            "index_type": "HNSW",
            "dimension": 99999,  # Also exceeds max
            "top_k": 99999  # Also exceeds max
        }
    )

    skip_reason = seekdb_profile.should_skip_test(test_case)

    # First check is combination, so that should be returned
    assert "COSINE" in skip_reason
    assert "HNSW" in skip_reason


def test_seekdb_constants(seekdb_profile):
    """Test SeekDBConstants values"""
    assert "L2" in SeekDBConstants.SUPPORTED_METRIC_TYPES
    assert "HNSW" in SeekDBConstants.SUPPORTED_INDEX_TYPES
    assert ("COSINE", "HNSW") in SeekDBConstants.UNSUPPORTED_COMBINATIONS
    assert SeekDBConstants.MAX_DIMENSION == 32768
