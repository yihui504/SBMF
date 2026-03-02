# tests/test_adapters.py
import pytest
from abc import ABC
from adapters.base import BaseAdapter, Capabilities

def test_adapter_interface():
    # 测试接口可以被子类化
    class TestAdapter(BaseAdapter):
        def get_capabilities(self):
            return Capabilities(
                supported_operations=["test"],
                supported_vector_types=["float32"],
                supported_index_types=["IVF"],
                concurrent_operations=False,
                max_concurrent_requests=None,
                transaction_support=False,
                distributed=False
            )

        def map_slot_to_param(self, slot_name):
            return slot_name

        def transform_value(self, slot_name, value):
            return value

        def classify_error(self, error):
            return ErrorCategory.PRODUCT_SUSPECT

        def connect(self, **kwargs):
            return True

        def disconnect(self):
            pass

        def is_connected(self):
            return True

        def execute_test(self, test_case):
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                result_data=None,
                error=None,
                elapsed_seconds=0.0
            )

    adapter = TestAdapter()
    caps = adapter.get_capabilities()
    assert caps.supported_operations == ["test"]

def test_capabilities_dataclass():
    caps = Capabilities(
        supported_operations=["insert", "search"],
        supported_vector_types=["float32", "int8"],
        supported_index_types=["IVF", "HNSW"],
        concurrent_operations=True,
        max_concurrent_requests=10,
        transaction_support=False,
        distributed=True
    )

    assert caps.supported_operations == ["insert", "search"]
    assert caps.concurrent_operations is True
    assert caps.max_concurrent_requests == 10
    assert caps.transaction_support is False
    assert caps.distributed is True
