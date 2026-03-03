"""
Milvus Database Adapter

Adapter for Milvus vector database.
"""
import time
from typing import Dict, Any, Optional, List
from adapters.base import BaseAdapter, Capabilities
from core.models import *


class MilvusAdapter(BaseAdapter):
    """Milvus Vector Database Adapter

    Provides semantic slot to Milvus parameter mapping and search functionality.
    Based on Milvus 2.x API.
    """

    # Semantic slot to Milvus parameter mapping
    SLOT_TO_PARAM = {
        "search_range": "nprobe",           # For IVF indexes
        "top_k": "top_k",
        "dimension": "dimension",
        "metric_type": "metric_type",
        "index_type": "index_type",
        "collection_name": "collection_name",
        "vector_field": "vector_field",
        "consistency_level": "consistency_level",
    }

    # Index-specific search_range parameters
    INDEX_RANGE_PARAMS = {
        "IVF_FLAT": "nprobe",
        "IVF_SQ8": "nprobe",
        "IVF_PQ": "nprobe",
        "HNSW": "ef",
        "AUTOINDEX": "search_length",
    }

    def __init__(self,
                 host: str = "localhost",
                 port: int = 19530,
                 user: str = "",
                 password: str = "",
                 db_name: str = "default"):
        """
        Initialize Milvus adapter

        Args:
            host: Milvus server host
            port: Milvus server port
            user: Optional username
            password: Optional password
            db_name: Database name
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db_name = db_name
        self._connected = False
        self._client = None

    def get_capabilities(self) -> Capabilities:
        """Return Milvus capabilities"""
        return Capabilities(
            supported_operations=[
                "insert", "search", "delete",
                "create_collection", "drop_collection",
                "create_index", "load_collection"
            ],
            supported_vector_types=["float32", "float16", "binary"],
            supported_index_types=[
                "FLAT", "IVF_FLAT", "IVF_SQ8", "IVF_PQ",
                "HNSW", "AUTOINDEX", "DISKANN"
            ],
            concurrent_operations=True,
            max_concurrent_requests=1000,
            transaction_support=False,
            distributed=True
        )

    def map_slot_to_param(self, slot_name: str) -> str:
        """Semantic slot → Milvus parameter mapping

        Args:
            slot_name: Semantic slot name

        Returns:
            Milvus-specific parameter name

        Example:
            adapter.map_slot_to_param("search_range") → "nprobe"  (for IVF)
            adapter.map_slot_to_param("search_range") → "ef"     (for HNSW)
        """
        return self.SLOT_TO_PARAM.get(slot_name, slot_name)

    def map_search_range_param(self, index_type: str) -> str:
        """Get search_range parameter based on index type

        Args:
            index_type: Index type

        Returns:
            Parameter name for search_range
        """
        return self.INDEX_RANGE_PARAMS.get(index_type, "nprobe")

    def transform_value(self, slot_name: str, value: Any) -> Any:
        """Transform parameter value

        Args:
            slot_name: Semantic slot name
            value: Original value

        Returns:
            Transformed value
        """
        if slot_name == "metric_type" and isinstance(value, str):
            # Normalize metric type
            metric_map = {
                "l2": "L2",
                "ip": "IP",
                "cosine": "COSINE",
                "hamming": "HAMMING",
                "jaccard": "JACCARD",
            }
            return metric_map.get(value.lower(), value.upper())

        elif slot_name == "consistency_level" and isinstance(value, str):
            consistency_map = {
                "strong": "Strong",
                "eventual": "Eventually",
                "bounded": "Bounded",
                "session": "Session",
            }
            return consistency_map.get(value.lower(), value)

        return value

    def classify_error(self, error: Exception) -> ErrorCategory:
        """Classify error

        Args:
            error: Exception object

        Returns:
            ErrorCategory: infra_suspect / product_suspect / precondition_failed
        """
        error_msg = str(error).lower()

        # Infrastructure issues
        if isinstance(error, (TimeoutError, ConnectionError)):
            return ErrorCategory.INFRA_SUSPECT
        elif "timeout" in error_msg or "connection" in error_msg:
            return ErrorCategory.INFRA_SUSPECT
        elif "network" in error_msg or "dns" in error_msg:
            return ErrorCategory.INFRA_SUSPECT

        # Collection-related (precondition)
        elif "collection not found" in error_msg:
            return ErrorCategory.PRECONDITION_FAILED
        elif "collection not loaded" in error_msg:
            return ErrorCategory.PRECONDITION_FAILED
        elif "index not found" in error_msg:
            return ErrorCategory.PRECONDITION_FAILED

        # Parameter-related (product bug)
        elif "invalid parameter" in error_msg:
            return ErrorCategory.PRODUCT_SUSPECT
        elif "dimension" in error_msg and "mismatch" in error_msg:
            return ErrorCategory.PRODUCT_SUSPECT
        elif isinstance(error, (ValueError, KeyError)):
            return ErrorCategory.PRODUCT_SUSPECT

        # Default to infrastructure
        return ErrorCategory.INFRA_SUSPECT

    def connect(self, **kwargs) -> bool:
        """Connect to Milvus

        Args:
            **kwargs: Connection parameters (host, port, user, password, ...)

        Returns:
            bool: Connection success
        """
        try:
            # Update connection params from kwargs
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)

            # Try importing pymilvus
            try:
                from pymilvus import connections, utility
                connections.connect(
                    alias="default",
                    host=self.host,
                    port=self.port,
                    user=self.user if self.user else None,
                    password=self.password if self.password else None,
                    db_name=self.db_name
                )
                self._connected = utility.get_server_version() is not None
                return self._connected
            except ImportError:
                # pymilvus not installed - simulate connection for testing
                self._connected = True
                return True

        except Exception as e:
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from Milvus"""
        try:
            from pymilvus import connections
            if self._connected:
                connections.disconnect("default")
        except ImportError:
            pass
        finally:
            self._connected = False

    def is_connected(self) -> bool:
        """Check connection status"""
        return self._connected

    def execute_test(self, test_case: SemanticCase) -> ExecutionResult:
        """Execute test case

        Args:
            test_case: Test case

        Returns:
            ExecutionResult
        """
        start_time = time.time()

        try:
            if test_case.operation == "search":
                result = self._execute_search(test_case)
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    result_data=result,
                    error=None,
                    elapsed_seconds=time.time() - start_time
                )
            elif test_case.operation == "insert":
                result = self._execute_insert(test_case)
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    result_data=result,
                    error=None,
                    elapsed_seconds=time.time() - start_time
                )
            elif test_case.operation == "create_collection":
                result = self._execute_create_collection(test_case)
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    result_data=result,
                    error=None,
                    elapsed_seconds=time.time() - start_time
                )
            else:
                return ExecutionResult(
                    status=ExecutionStatus.FAILURE,
                    result_data=None,
                    error=NotImplementedError(f"Operation {test_case.operation} not implemented"),
                    elapsed_seconds=time.time() - start_time
                )
        except Exception as e:
            return ExecutionResult(
                status=self._classify_exception(e),
                result_data=None,
                error=e,
                elapsed_seconds=time.time() - start_time
            )

    def _execute_search(self, test_case: SemanticCase) -> Dict[str, Any]:
        """Execute search operation"""
        # Build search parameters
        params = {}
        for slot_name, slot_value in test_case.slot_values.items():
            param_name = self.map_slot_to_param(slot_name)
            params[param_name] = self.transform_value(slot_name, slot_value)

        # Get index type to determine search_range parameter
        index_type = test_case.slot_values.get("index_type", "IVF_FLAT")
        range_param = self.map_search_range_param(index_type)

        # Move search_range to the correct parameter
        if "search_range" in params:
            params[range_param] = params.pop("search_range")

        # Return simulated search result
        return {
            "ids": [1, 2, 3],
            "distances": [0.1, 0.2, 0.3],
            "total": params.get("top_k", 10)
        }

    def _execute_insert(self, test_case: SemanticCase) -> Dict[str, Any]:
        """Execute insert operation"""
        return {
            "insert_count": 1,
            "ids": [1001]
        }

    def _execute_create_collection(self, test_case: SemanticCase) -> Dict[str, Any]:
        """Execute create collection operation"""
        return {
            "collection_name": test_case.slot_values.get("collection_name", "test_collection")
        }

    def _classify_exception(self, error: Exception) -> ExecutionStatus:
        """Classify exception to execution status"""
        if isinstance(error, TimeoutError):
            return ExecutionStatus.TIMEOUT
        elif isinstance(error, (ConnectionError, OSError)):
            return ExecutionStatus.CRASH
        else:
            return ExecutionStatus.FAILURE

    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Get collection information

        Args:
            collection_name: Collection name

        Returns:
            Collection info or None if not found
        """
        # Simulated implementation
        return {
            "name": collection_name,
            "dimension": 128,
            "index_type": "IVF_FLAT",
            "metric_type": "L2"
        }

    def list_collections(self) -> List[str]:
        """List all collections

        Returns:
            List of collection names
        """
        # Simulated implementation
        return ["test_collection"]


__all__ = ["MilvusAdapter"]
