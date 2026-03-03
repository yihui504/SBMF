"""
Bug Feature Extractor

Extracts features from bug reports for classification and analysis.
"""
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from core.models import ExecutionStatus, ErrorCategory


@dataclass
class BugFeatures:
    """
    Extracted features from a bug report

    Contains 20+ dimensions for bug classification and analysis.
    """
    # Basic info
    test_id: str = ""
    operation: str = ""

    # Status features
    status: str = ""
    status_category: str = ""  # SUCCESS, FAILURE, TIMEOUT, CRASH, PRECONDITION_FAILED

    # Error features
    error_message: str = ""
    error_category: str = ""
    has_error: bool = False
    error_code: Optional[int] = None
    error_keywords: List[str] = field(default_factory=list)

    # Input features
    input_dimension: int = 0
    input_metric_type: str = ""
    input_top_k: int = 0
    input_range: int = 0
    input_index_type: str = ""

    # Constraint violation features
    violated_constraints: List[str] = field(default_factory=list)
    constraint_severity: str = ""  # low, medium, high

    # Context features
    database_type: str = ""
    test_scope: str = ""
    is_boundary_test: bool = False
    is_stress_test: bool = False

    # Performance features
    execution_time_ms: float = 0.0
    is_slow: bool = False
    memory_usage_mb: float = 0.0

    # Oracle results
    oracle_passed_count: int = 0
    oracle_failed_count: int = 0
    oracle_total_count: int = 0
    oracle_pass_rate: float = 0.0

    # Pattern matching
    matched_patterns: List[str] = field(default_factory=list)
    pattern_match_scores: List[float] = field(default_factory=list)

    # Metadata
    extracted_at: float = field(default_factory=lambda: datetime.now().timestamp())
    feature_count: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "test_id": self.test_id,
            "operation": self.operation,
            "status": self.status,
            "status_category": self.status_category,
            "error_message": self.error_message,
            "error_category": self.error_category,
            "has_error": self.has_error,
            "error_code": self.error_code,
            "error_keywords": self.error_keywords,
            "input_dimension": self.input_dimension,
            "input_metric_type": self.input_metric_type,
            "input_top_k": self.input_top_k,
            "input_range": self.input_range,
            "input_index_type": self.input_index_type,
            "violated_constraints": self.violated_constraints,
            "constraint_severity": self.constraint_severity,
            "database_type": self.database_type,
            "test_scope": self.test_scope,
            "is_boundary_test": self.is_boundary_test,
            "is_stress_test": self.is_stress_test,
            "execution_time_ms": self.execution_time_ms,
            "is_slow": self.is_slow,
            "memory_usage_mb": self.memory_usage_mb,
            "oracle_passed_count": self.oracle_passed_count,
            "oracle_failed_count": self.oracle_failed_count,
            "oracle_total_count": self.oracle_total_count,
            "oracle_pass_rate": self.oracle_pass_rate,
            "matched_patterns": self.matched_patterns,
            "pattern_match_scores": self.pattern_match_scores,
            "extracted_at": self.extracted_at,
            "feature_count": self.feature_count,
        }


class BugFeatureExtractor:
    """
    Bug Feature Extractor

    Extracts 20+ dimensional features from bug reports and test results
    for intelligent classification and analysis.
    """

    # Common error patterns
    ERROR_PATTERNS = {
        "dimension": [r"dimension.*exceed", r"dimension.*too large", r"dimension.*limit"],
        "metric": [r"unsupported.*metric", r"metric.*not available", r"invalid.*metric"],
        "timeout": [r"timeout", r"timed out"],
        "connection": [r"connection.*refused", r"connection.*failed", r"cannot connect"],
        "memory": [r"out of memory", r"memory.*exceed", r"allocation.*failed"],
        "validation": [r"validation.*failed", r"invalid.*parameter", r"parameter.*error"],
        "concurrency": [r"deadlock", r"lock.*timeout", r"race.*condition"],
        "index": [r"incompatible.*index", r"index.*metric.*mismatch"],
    }

    # Boundary values for common parameters
    BOUNDARY_VALUES = {
        "dimension": [1, 32768],
        "top_k": [1, 10000],
    }

    def __init__(self):
        """Initialize feature extractor"""
        self._feature_count = 0

    def extract(self, test_case, execution_result, oracle_results: Optional[List] = None,
                context: Optional[Dict] = None) -> BugFeatures:
        """
        Extract features from test execution

        Args:
            test_case: The test case that was executed
            execution_result: Result from execution
            oracle_results: Results from oracle checks
            context: Additional context information

        Returns:
            BugFeatures with extracted features
        """
        features = BugFeatures()
        self._feature_count = 0

        # Basic info
        features.test_id = getattr(test_case, 'test_id', '')
        features.operation = getattr(test_case, 'operation', '')
        self._feature_count += 2

        # Status features
        self._extract_status_features(features, execution_result)

        # Error features
        self._extract_error_features(features, execution_result)

        # Input features
        self._extract_input_features(features, test_case)

        # Constraint features
        self._extract_constraint_features(features, oracle_results)

        # Context features
        self._extract_context_features(features, context)

        # Performance features
        self._extract_performance_features(features, execution_result)

        # Oracle features
        self._extract_oracle_features(features, oracle_results)

        # Pattern matching
        self._extract_pattern_features(features)

        features.feature_count = self._feature_count
        return features

    def _extract_status_features(self, features: BugFeatures, result: Any) -> None:
        """Extract status-related features"""
        if hasattr(result, 'status'):
            status = result.status
            if isinstance(status, ExecutionStatus):
                features.status = status.value
                features.status_category = status.value
            else:
                features.status = str(status)
                features.status_category = str(status)

            self._feature_count += 1

    def _extract_error_features(self, features: BugFeatures, result: Any) -> None:
        """Extract error-related features"""
        if hasattr(result, 'error') and result.error:
            features.has_error = True
            error_str = str(result.error)
            features.error_message = error_str[:500]  # Truncate long messages

            # Extract error code
            code_match = re.search(r'\(errno\s+(\d+)\)', error_str)
            if code_match:
                features.error_code = int(code_match.group(1))

            # Categorize error
            features.error_category = self._categorize_error(error_str)

            # Extract keywords
            features.error_keywords = self._extract_error_keywords(error_str)

            self._feature_count += 4

    def _extract_input_features(self, features: BugFeatures, test_case: Any) -> None:
        """Extract input-related features"""
        slot_values = getattr(test_case, 'slot_values', {})

        features.input_dimension = int(slot_values.get('dimension', 0))
        features.input_metric_type = str(slot_values.get('metric_type', ''))
        features.input_top_k = int(slot_values.get('top_k', 0))
        features.input_range = int(slot_values.get('search_range', 0))
        features.input_index_type = str(slot_values.get('index_type', ''))

        self._feature_count += 5

    def _extract_constraint_features(self, features: BugFeatures, oracle_results: Optional[List]) -> None:
        """Extract constraint violation features"""
        if not oracle_results:
            return

        for oracle_result in oracle_results:
            if hasattr(oracle_result, 'passed') and not oracle_result.passed:
                if hasattr(oracle_result, 'violated_slots'):
                    features.violated_constraints.extend(oracle_result.violated_slots)

        if features.violated_constraints:
            features.constraint_severity = self._assess_constraint_severity(features)

        self._feature_count += 1

    def _extract_context_features(self, features: BugFeatures, context: Optional[Dict]) -> None:
        """Extract context features"""
        if context:
            features.database_type = context.get('database_type', '')
            features.test_scope = context.get('test_scope', '')

        # Detect boundary test
        features.is_boundary_test = self._is_boundary_test(features)

        # Detect stress test
        features.is_stress_test = self._is_stress_test(features)

        self._feature_count += 3

    def _extract_performance_features(self, features: BugFeatures, result: Any) -> None:
        """Extract performance-related features"""
        if hasattr(result, 'elapsed_seconds'):
            features.execution_time_ms = result.elapsed_seconds * 1000

        # Classify as slow if > 1 second
        features.is_slow = features.execution_time_ms > 1000

        self._feature_count += 2

    def _extract_oracle_features(self, features: BugFeatures, oracle_results: Optional[List]) -> None:
        """Extract oracle-related features"""
        if not oracle_results:
            return

        features.oracle_total_count = len(oracle_results)
        features.oracle_passed_count = sum(1 for r in oracle_results if getattr(r, 'passed', False))
        features.oracle_failed_count = features.oracle_total_count - features.oracle_passed_count

        if features.oracle_total_count > 0:
            features.oracle_pass_rate = features.oracle_passed_count / features.oracle_total_count

        self._feature_count += 4

    def _extract_pattern_features(self, features: BugFeatures) -> None:
        """Extract pattern matching features"""
        symptoms = [features.error_message] + features.error_keywords
        symptoms = [s for s in symptoms if s]

        matched = []
        scores = []

        for pattern_type, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                for symptom in symptoms:
                    if re.search(pattern, symptom, re.IGNORECASE):
                        matched.append(pattern_type)
                        scores.append(0.8)  # Base match score
                        break

        features.matched_patterns = list(set(matched))
        features.pattern_match_scores = scores

        self._feature_count += 1

    # ================================================================
    # Helper Methods
    # ================================================================

    def _categorize_error(self, error_str: str) -> str:
        """Categorize error type"""
        error_lower = error_str.lower()

        if 'timeout' in error_lower:
            return 'timeout'
        elif 'connection' in error_lower or 'refused' in error_lower:
            return 'connection'
        elif 'dimension' in error_lower or 'parameter' in error_lower:
            return 'validation'
        elif 'memory' in error_lower:
            return 'memory'
        elif 'lock' in error_lower or 'deadlock' in error_lower:
            return 'concurrency'
        else:
            return 'unknown'

    def _extract_error_keywords(self, error_str: str) -> List[str]:
        """Extract meaningful keywords from error message"""
        keywords = []

        # Common error terms
        error_terms = [
            'timeout', 'refused', 'connection', 'exceeds', 'maximum', 'minimum',
            'invalid', 'unsupported', 'dimension', 'metric', 'memory', 'lock',
            'validation', 'parameter', 'index', 'cosine', 'l2', 'ip', 'hnsw'
        ]

        for term in error_terms:
            if term in error_str.lower():
                keywords.append(term)

        return keywords

    def _assess_constraint_severity(self, features: BugFeatures) -> str:
        """Assess severity of constraint violations"""
        count = len(features.violated_constraints)

        if count == 0:
            return 'none'
        elif count == 1:
            return 'low'
        elif count <= 2:
            return 'medium'
        else:
            return 'high'

    def _is_boundary_test(self, features: BugFeatures) -> bool:
        """Check if test is a boundary test"""
        return (
            features.input_dimension in self.BOUNDARY_VALUES['dimension'] or
            features.input_top_k in self.BOUNDARY_VALUES['top_k']
        )

    def _is_stress_test(self, features: BugFeatures) -> bool:
        """Check if test is a stress test"""
        return (
            features.input_dimension > 10000 or
            features.input_top_k > 1000 or
            features.is_slow
        )

    def get_feature_names(self) -> List[str]:
        """Get list of all feature names"""
        features = BugFeatures()
        return list(features.to_dict().keys())


__all__ = [
    "BugFeatures",
    "BugFeatureExtractor",
]
