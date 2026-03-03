# tests/test_seekdb_adapter.py
import pytest
from adapters.seekdb import SeekDBAdapter
from core.models import ErrorCategory, SemanticCase, SlotScope, ExecutionStatus

def test_seekdb_adapter_capabilities():
    adapter = SeekDBAdapter(host="localhost", port=2881)
    caps = adapter.get_capabilities()

    assert "insert" in caps.supported_operations
    assert "search" in caps.supported_operations

def test_seekdb_map_slot_to_param():
    adapter = SeekDBAdapter(host="localhost", port=2881)

    assert adapter.map_slot_to_param("search_range") == "ef"
    assert adapter.map_slot_to_param("top_k") == "top_k"

def test_seekdb_transform_value():
    adapter = SeekDBAdapter(host="localhost", port=2881)

    # metric_type should be uppercased
    assert adapter.transform_value("metric_type", "l2") == "L2"
    # other values should pass through
    assert adapter.transform_value("top_k", 10) == 10

def test_seekdb_classify_error():
    adapter = SeekDBAdapter(host="localhost", port=2881)

    assert adapter.classify_error(TimeoutError()) == ErrorCategory.INFRA_SUSPECT
    assert adapter.classify_error(ConnectionError()) == ErrorCategory.INFRA_SUSPECT
    assert adapter.classify_error(ValueError("invalid dimension")) == ErrorCategory.PRODUCT_SUSPECT
    assert adapter.classify_error(KeyError("missing field")) == ErrorCategory.PRODUCT_SUSPECT

def test_seekdb_connect():
    adapter = SeekDBAdapter(host="localhost", port=2881)

    # Should handle connection gracefully (may fail without actual database)
    result = adapter.connect()
    assert isinstance(result, bool)
    assert adapter.is_connected() == result

def test_seekdb_disconnect():
    adapter = SeekDBAdapter(host="localhost", port=2881)
    adapter._connected = True
    adapter.disconnect()
    assert adapter.is_connected() is False

def test_seekdb_execute_test_search():
    adapter = SeekDBAdapter(host="localhost", port=2881)

    test_case = SemanticCase(
        test_id="test_1",
        operation="search",
        slot_values={"top_k": 10, "search_range": 100},
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    result = adapter.execute_test(test_case)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.elapsed_seconds >= 0
