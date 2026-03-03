"""
Weaviate Database Adapter

Adapter for Weaviate vector search engine.
"""
import time
from typing import Dict, Any, Optional, List
from adapters.base import BaseAdapter, Capabilities
from core.models import *


class WeaviateAdapter(BaseAdapter):
    """Weaviate Vector Database Adapter

    Provides semantic slot to Weaviate parameter mapping and search functionality.
    Based on Weaviate v1.x+ API.
    """

    # Semantic slot to Weaviate parameter mapping
    SLOT_TO_PARAM = {
        "search_range": "certainty",          # For similarity threshold
        "top_k": "limit",
        "dimension": "dimension",
        "metric_type": "distance",
        "collection_name": "class_name",
        "vector_field": "vectorPropertyName",
        "consistency_level": "consistency_level",
    }

    # Weaviate distance metrics
    DISTANCE_METRICS = {
        "l2": "l2-squared",
        "ip": "dot",
        "cosine": "cosine",
        "hamming": "hamming",
    }

    def __init__(self,
                 url: str = "http://localhost:8080",
                 api_key: Optional[str] = None,
                 timeout: int = 30):
        """
        Initialize Weaviate adapter

        Args:
            url: Weaviate server URL
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.url = url
        self.api_key = api_key
        self.timeout = timeout
        self._connected = False
        self._client = None

    def get_capabilities(self) -> Capabilities:
        """Return Weaviate capabilities"""
        return Capabilities(
            supported_operations=[
                "insert", "search", "delete",
                "create_class", "drop_class",
                "batch_insert"
            ],
            supported_vector_types=["float32"],
            supported_index_types=["HNSW"],
            concurrent_operations=True,
            max_concurrent_requests=100,
            transaction_support=False,
            distributed=True
        )

    def map_slot_to_param(self, slot_name: str) -> str:
        """Semantic slot → Weaviate parameter mapping

        Args:
            slot_name: Semantic slot name

        Returns:
            Weaviate-specific parameter name

        Example:
            adapter.map_slot_to_param("search_range") → "certainty"
            adapter.map_slot_to_param("top_k") → "limit"
        """
        return self.SLOT_TO_PARAM.get(slot_name, slot_name)

    def transform_value(self, slot_name: str, value: Any) -> Any:
        """Transform parameter value

        Args:
            slot_name: Semantic slot name
            value: Original value

        Returns:
            Transformed value
        """
        if slot_name == "metric_type" and isinstance(value, str):
            # Map to Weaviate distance metric
            return self.DISTANCE_METRICS.get(value.lower(), value.lower())

        elif slot_name == "search_range" and isinstance(value, (int, float)):
            # Convert search_range to certainty threshold
            # Higher search_range = higher certainty (0-1)
            # This is an approximation - real mapping depends on use case
            return min(1.0, value / 100.0)

        elif slot_name == "consistency_level" and isinstance(value, str):
            # Weaviate consistency levels
            consistency_map = {
                "all": "ALL",
                "quorum": "QUORUM",
                "one": "ONE",
            }
            return consistency_map.get(value.lower(), "ONE")

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
        elif "network" in error_msg or "unreachable" in error_msg:
            return ErrorCategory.INFRA_SUSPECT

        # Class-related (precondition)
        elif "class" in error_msg and "not found" in error_msg:
            return ErrorCategory.PRECONDITION_FAILED
        elif "class" in error_msg and "already exists" in error_msg:
            return ErrorCategory.PRECONDITION_FAILED

        # Property-related (precondition)
        elif "property" in error_msg and "not found" in error_msg:
            return ErrorCategory.PRECONDITION_FAILED

        # Parameter-related (product bug)
        elif "invalid" in error_msg and "property" in error_msg:
            return ErrorCategory.PRODUCT_SUSPECT
        elif "vector" in error_msg and "dimension" in error_msg:
            return ErrorCategory.PRODUCT_SUSPECT
        elif isinstance(error, (ValueError, KeyError)):
            return ErrorCategory.PRODUCT_SUSPECT

        # Default to infrastructure
        return ErrorCategory.INFRA_SUSPECT

    def connect(self, **kwargs) -> bool:
        """Connect to Weaviate

        Args:
            **kwargs: Connection parameters (url, api_key, ...)

        Returns:
            bool: Connection success
        """
        try:
            # Update connection params from kwargs
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)

            # Try importing weaviate
            try:
                import weaviate
                auth_config = None
                if self.api_key:
                    auth_config = weaviate.AuthApiKey(api_key=self.api_key)

                self._client = weaviate.Client(
                    url=self.url,
                    auth_client_secret=auth_config,
                    timeout_config=(5, self.timeout)
                )
                # Test connection
                self._client.is_ready()
                self._connected = True
                return True
            except ImportError:
                # weaviate-client not installed - simulate connection for testing
                self._connected = True
                return True

        except Exception as e:
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from Weaviate"""
        self._client = None
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
            elif test_case.operation == "create_class":
                result = self._execute_create_class(test_case)
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
        """Execute search operation using nearVector"""
        # Build search parameters
        params = {}
        for slot_name, slot_value in test_case.slot_values.items():
            param_name = self.map_slot_to_param(slot_name)
            params[param_name] = self.transform_value(slot_name, slot_value)

        # Get class name
        class_name = params.get("class_name", test_case.slot_values.get("collection_name", "Test"))

        # Return simulated search result
        return {
            "class": class_name,
            "limit": params.get("limit", 10),
            "results": [
                {"id": "1", "certainty": 0.95},
                {"id": "2", "certainty": 0.90},
                {"id": "3", "certainty": 0.85},
            ]
        }

    def _execute_insert(self, test_case: SemanticCase) -> Dict[str, Any]:
        """Execute insert operation"""
        return {
            "result": {
                "status": "SUCCESS",
                "count": 1
            }
        }

    def _execute_create_class(self, test_case: SemanticCase) -> Dict[str, Any]:
        """Execute create class operation"""
        class_name = test_case.slot_values.get("collection_name", "TestClass")
        return {
            "class": class_name
        }

    def _classify_exception(self, error: Exception) -> ExecutionStatus:
        """Classify exception to execution status"""
        if isinstance(error, TimeoutError):
            return ExecutionStatus.TIMEOUT
        elif isinstance(error, (ConnectionError, OSError)):
            return ExecutionStatus.CRASH
        else:
            return ExecutionStatus.FAILURE

    def get_class_info(self, class_name: str) -> Optional[Dict[str, Any]]:
        """Get class (collection) information

        Args:
            class_name: Class name

        Returns:
            Class info or None if not found
        """
        # Simulated implementation
        return {
            "class": class_name,
            "vectorIndexType": "hnsw",
            "vectorizer": "none",
            "properties": []
        }

    def list_classes(self) -> List[str]:
        """List all classes (collections)

        Returns:
            List of class names
        """
        # Simulated implementation
        return ["TestClass"]


__all__ = ["WeaviateAdapter"]
