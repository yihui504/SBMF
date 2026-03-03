"""
Bug Knowledge Base

Stores and manages bug patterns, historical data, and fix templates.
"""
import json
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum


class BugSeverity(Enum):
    """Bug severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BugCategory(Enum):
    """Bug categories"""
    VALIDATION = "validation"        # Input validation errors
    LOGIC = "logic"                 # Logic errors
    PERFORMANCE = "performance"      # Performance issues
    CONCURRENCY = "concurrency"      # Concurrency issues
    SECURITY = "security"           # Security vulnerabilities
    CONFIGURATION = "configuration"  # Configuration errors
    API_MISMATCH = "api_mismatch"    # API compatibility issues
    INFRA = "infra"                 # Infrastructure issues


@dataclass
class FixSuggestion:
    """A fix suggestion"""
    type: str  # validation, code_change, config_update, etc.
    description: str
    code_template: Optional[str] = None
    safe: bool = True  # Whether the template is pre-validated
    estimated_effort: str = "medium"  # low, medium, high
    references: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'FixSuggestion':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class BugPattern:
    """
    A bug pattern in the knowledge base

    Represents a type of bug that has been seen before,
    along with symptoms, root cause, and fix suggestions.
    """
    pattern_id: str
    name: str
    category: BugCategory
    severity: BugSeverity
    description: str

    # Detection
    symptoms: List[str] = field(default_factory=list)
    detection_rules: List[str] = field(default_factory=list)
    error_patterns: List[str] = field(default_factory=list)

    # Analysis
    root_cause: str = ""
    related_patterns: List[str] = field(default_factory=list)

    # Fix
    fix_suggestions: List[FixSuggestion] = field(default_factory=list)

    # Metadata
    occurrence_count: int = 0
    last_seen: float = 0.0
    created_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['category'] = self.category.value
        data['severity'] = self.severity.value
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'BugPattern':
        """Create from dictionary"""
        data['category'] = BugCategory(data['category'])
        data['severity'] = BugSeverity(data['severity'])

        # Convert fix_suggestions from dicts to objects
        if 'fix_suggestions' in data and data['fix_suggestions']:
            data['fix_suggestions'] = [
                FixSuggestion.from_dict(s) if isinstance(s, dict) else s
                for s in data['fix_suggestions']
            ]

        return cls(**data)

    def match_symptoms(self, symptoms: List[str]) -> float:
        """
        Calculate how well given symptoms match this pattern

        Returns:
            Match score (0-1)
        """
        if not symptoms:
            return 0.0

        matches = 0
        for s in symptoms:
            for p in self.symptoms:
                # Check if pattern symptom is contained in symptom text OR vice versa
                if p.lower() in s.lower() or s.lower() in p.lower():
                    matches += 1
                    break

        return matches / len(symptoms) if symptoms else 0.0


class BugKnowledgeBase:
    """
    Bug Knowledge Base

    Stores bug patterns, historical data, and fix templates.
    Provides search and matching capabilities.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize bug knowledge base

        Args:
            storage_path: Path to knowledge base file
        """
        self.storage_path = storage_path or Path("bug_knowledge_base.json")
        self._patterns: Dict[str, BugPattern] = {}
        self._load()

    # ================================================================
    # Pattern Management
    # ================================================================

    def add_pattern(self, pattern: BugPattern) -> None:
        """Add a bug pattern to the knowledge base"""
        self._patterns[pattern.pattern_id] = pattern
        self._save()

    def get_pattern(self, pattern_id: str) -> Optional[BugPattern]:
        """Get a pattern by ID"""
        return self._patterns.get(pattern_id)

    def remove_pattern(self, pattern_id: str) -> bool:
        """Remove a pattern"""
        if pattern_id in self._patterns:
            del self._patterns[pattern_id]
            self._save()
            return True
        return False

    def list_patterns(self, category: Optional[BugCategory] = None) -> List[BugPattern]:
        """List all patterns, optionally filtered by category"""
        patterns = list(self._patterns.values())

        if category:
            patterns = [p for p in patterns if p.category == category]

        return sorted(patterns, key=lambda x: -x.occurrence_count)

    def update_pattern_occurrence(self, pattern_id: str) -> None:
        """Update occurrence count for a pattern"""
        if pattern_id in self._patterns:
            pattern = self._patterns[pattern_id]
            pattern.occurrence_count += 1
            pattern.last_seen = time.time()
            self._save()

    # ================================================================
    # Search and Matching
    # ================================================================

    def search_by_symptoms(self, symptoms: List[str],
                          threshold: float = 0.3) -> List[Tuple[BugPattern, float]]:
        """
        Search for patterns matching given symptoms

        Args:
            symptoms: List of symptoms to match
            threshold: Minimum match score

        Returns:
            List of (pattern, score) tuples, sorted by score descending
        """
        matches = []

        for pattern in self._patterns.values():
            score = pattern.match_symptoms(symptoms)
            if score >= threshold:
                matches.append((pattern, score))

        return sorted(matches, key=lambda x: -x[1])

    def search_by_category(self, category: BugCategory) -> List[BugPattern]:
        """Search for patterns by category"""
        return [p for p in self._patterns.values() if p.category == category]

    def search_by_severity(self, severity: BugSeverity) -> List[BugPattern]:
        """Search for patterns by severity"""
        return [p for p in self._patterns.values() if p.severity == severity]

    def search_by_tag(self, tag: str) -> List[BugPattern]:
        """Search for patterns by tag"""
        return [p for p in self._patterns.values() if tag in p.tags]

    def find_similar_patterns(self, pattern_id: str,
                            min_overlap: int = 1) -> List[BugPattern]:
        """
        Find patterns similar to a given pattern

        Args:
            pattern_id: Pattern to compare
            min_overlap: Minimum symptom overlap

        Returns:
            List of similar patterns
        """
        if pattern_id not in self._patterns:
            return []

        target = self._patterns[pattern_id]
        similar = []

        for pid, pattern in self._patterns.items():
            if pid == pattern_id:
                continue

            # Check symptom overlap
            overlap = len(set(target.symptoms) & set(pattern.symptoms))
            if overlap >= min_overlap:
                similar.append(pattern)

        return similar

    # ================================================================
    # Fix Suggestions
    # ================================================================

    def get_fix_suggestions(self, pattern_id: str) -> List[FixSuggestion]:
        """Get fix suggestions for a pattern"""
        pattern = self.get_pattern(pattern_id)
        if not pattern:
            return []
        return pattern.fix_suggestions

    def get_safe_fix_templates(self) -> Dict[str, str]:
        """
        Get all safe (pre-validated) fix code templates

        Returns:
            Dict of {pattern_id: code_template}
        """
        templates = {}

        for pattern in self._patterns.values():
            for suggestion in pattern.fix_suggestions:
                if suggestion.safe and suggestion.code_template:
                    templates[pattern.pattern_id] = suggestion.code_template
                    break  # Use first safe template

        return templates

    # ================================================================
    # Statistics
    # ================================================================

    def get_stats(self) -> Dict:
        """Get knowledge base statistics"""
        categories = {}
        severities = {}

        for pattern in self._patterns.values():
            cat = pattern.category.value
            sev = pattern.severity.value

            categories[cat] = categories.get(cat, 0) + 1
            severities[sev] = severities.get(sev, 0) + 1

        return {
            "total_patterns": len(self._patterns),
            "categories": categories,
            "severities": severities,
            "total_occurrences": sum(p.occurrence_count for p in self._patterns.values()),
            "safe_templates": len(self.get_safe_fix_templates()),
        }

    # ================================================================
    # Persistence
    # ================================================================

    def _load(self) -> None:
        """Load knowledge base from disk"""
        if not self.storage_path.exists():
            # Initialize with default patterns
            self._initialize_default_patterns()
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                for pattern_data in data.get("patterns", []):
                    pattern = BugPattern.from_dict(pattern_data)
                    self._patterns[pattern.pattern_id] = pattern

        except Exception as e:
            print(f"[WARNING] Failed to load knowledge base: {e}")
            self._initialize_default_patterns()

    def _save(self) -> None:
        """Save knowledge base to disk"""
        try:
            data = {
                "version": "1.0",
                "patterns": [p.to_dict() for p in self._patterns.values()],
            }

            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"[WARNING] Failed to save knowledge base: {e}")

    def _initialize_default_patterns(self) -> None:
        """Initialize with default bug patterns for vector databases"""
        default_patterns = [
            # Dimension validation errors
            BugPattern(
                pattern_id="P001",
                name="Dimension Exceeds Maximum",
                category=BugCategory.VALIDATION,
                severity=BugSeverity.HIGH,
                description="Input dimension exceeds the maximum supported value",
                symptoms=[
                    "dimension too large",
                    "exceeds maximum dimension",
                    "dimension limit exceeded",
                    "invalid dimension size",
                    "exceeds",
                    "maximum"
                ],
                detection_rules=[
                    "dimension > MAX_DIMENSION",
                    "dimension parameter > limit"
                ],
                root_cause="Missing input validation for dimension parameter",
                fix_suggestions=[
                    FixSuggestion(
                        type="validation",
                        description="Add input validation for dimension",
                        code_template="""
def validate_dimension(dimension: int, max_dim: int) -> int:
    if not isinstance(dimension, int):
        raise TypeError(f"Dimension must be int, got {type(dimension).__name__}")
    if dimension < 1:
        raise ValueError(f"Dimension must be >= 1, got {dimension}")
    if dimension > max_dim:
        raise ValueError(f"Dimension {dimension} exceeds maximum {max_dim}")
    return dimension
                        """,
                        safe=True,
                        estimated_effort="low"
                    ),
                    FixSuggestion(
                        type="documentation",
                        description="Update API documentation to clarify dimension limits",
                        safe=True,
                        estimated_effort="low"
                    )
                ],
                tags=["dimension", "validation", "input"]
            ),

            # Metric type errors
            BugPattern(
                pattern_id="P002",
                name="Unsupported Metric Type",
                category=BugCategory.API_MISMATCH,
                severity=BugSeverity.MEDIUM,
                description="Requested metric type is not supported by the database",
                symptoms=[
                    "unsupported metric type",
                    "metric type not available",
                    "invalid metric",
                    "unknown metric",
                    "not supported"
                ],
                detection_rules=[
                    "metric_type not in SUPPORTED_METRICS"
                ],
                root_cause="Client requested a metric type not supported by the database",
                fix_suggestions=[
                    FixSuggestion(
                        type="validation",
                        description="Validate metric type against supported list",
                        code_template="""
SUPPORTED_METRICS = {"L2", "IP", "COSINE"}

def validate_metric_type(metric_type: str) -> str:
    metric_upper = metric_type.upper()
    if metric_upper not in SUPPORTED_METRICS:
        raise ValueError(f"Unsupported metric type: {metric_type}. "
                        f"Supported: {', '.join(SUPPORTED_METRICS)}")
    return metric_upper
                        """,
                        safe=True,
                        estimated_effort="low"
                    )
                ],
                tags=["metric", "validation", "api"]
            ),

            # Index combination errors
            BugPattern(
                pattern_id="P003",
                name="Incompatible Index Combination",
                category=BugCategory.API_MISMATCH,
                severity=BugSeverity.HIGH,
                description="Certain index types cannot be used with specific metric types",
                symptoms=[
                    "incompatible index and metric",
                    "unsupported combination",
                    "index metric mismatch"
                ],
                detection_rules=[
                    "index_type == 'HNSW' and metric_type == 'COSINE'"
                ],
                root_cause="Database does not support HNSW index with COSINE metric",
                fix_suggestions=[
                    FixSuggestion(
                        type="validation",
                        description="Add pre-condition check for index-metric compatibility",
                        code_template="""
INCOMPATIBLE_COMBINATIONS = {
    ("HNSW", "COSINE"),
    # Add more incompatible combinations
}

def validate_index_metric(index_type: str, metric_type: str) -> None:
    if (index_type, metric_type) in INCOMPATIBLE_COMBINATIONS:
        raise ValueError(
            f"Combination of index_type='{index_type}' and "
            f"metric_type='{metric_type}' is not supported. "
            f"Consider using IVF or FLAT index with COSINE metric."
        )
                        """,
                        safe=True,
                        estimated_effort="medium"
                    )
                ],
                tags=["index", "metric", "validation", "compatibility"]
            ),

            # Search range validation
            BugPattern(
                pattern_id="P004",
                name="Invalid Search Range",
                category=BugCategory.LOGIC,
                severity=BugSeverity.MEDIUM,
                description="Search range is smaller than top_k, causing incomplete results",
                symptoms=[
                    "search range less than top k",
                    "insufficient search range",
                    "incomplete results"
                ],
                detection_rules=[
                    "search_range < top_k"
                ],
                root_cause="Logic error: search_range must be >= top_k for complete results",
                fix_suggestions=[
                    FixSuggestion(
                        type="validation",
                        description="Add constraint validation",
                        code_template="""
def validate_search_params(top_k: int, search_range: int) -> None:
    if search_range < top_k:
        raise ValueError(
            f"search_range ({search_range}) must be >= top_k ({top_k}). "
            f"Set search_range to at least top_k for complete results."
        )
                        """,
                        safe=True,
                        estimated_effort="low"
                    )
                ],
                tags=["search", "validation", "logic"]
            ),

            # Connection timeout
            BugPattern(
                pattern_id="P005",
                name="Database Connection Timeout",
                category=BugCategory.INFRA,
                severity=BugSeverity.CRITICAL,
                description="Failed to connect to database within timeout period",
                symptoms=[
                    "connection timeout",
                    "connection refused",
                    "database unavailable"
                ],
                detection_rules=[
                    "connection_time > timeout"
                ],
                root_cause="Database is not running or network issue",
                fix_suggestions=[
                    FixSuggestion(
                        type="infrastructure",
                        description="Verify database is running and accessible",
                        safe=True,
                        estimated_effort="low"
                    ),
                    FixSuggestion(
                        type="configuration",
                        description="Increase connection timeout if database is slow",
                        safe=True,
                        estimated_effort="low"
                    )
                ],
                tags=["connection", "infrastructure", "timeout"]
            ),

            # Memory limit exceeded
            BugPattern(
                pattern_id="P006",
                name="Memory Limit Exceeded",
                category=BugCategory.PERFORMANCE,
                severity=BugSeverity.HIGH,
                description="Operation exceeded available memory",
                symptoms=[
                    "out of memory",
                    "memory limit exceeded",
                    "allocation failed"
                ],
                detection_rules=[
                    "memory_usage > max_memory"
                ],
                root_cause="Vector size or batch size too large for available memory",
                fix_suggestions=[
                    FixSuggestion(
                        type="configuration",
                        description="Reduce batch size or vector dimension",
                        safe=True,
                        estimated_effort="low"
                    ),
                    FixSuggestion(
                        type="code_change",
                        description="Implement batch processing for large datasets",
                        safe=True,
                        estimated_effort="high"
                    )
                ],
                tags=["memory", "performance", "resource"]
            ),
        ]

        for pattern in default_patterns:
            self.add_pattern(pattern)

    def export_patterns(self, output_path: Optional[Path] = None) -> str:
        """
        Export patterns to JSON file

        Args:
            output_path: Output file path

        Returns:
            Path to exported file
        """
        output_path = output_path or Path("bug_patterns_export.json")

        try:
            data = {
                "version": "1.0",
                "exported_at": time.time(),
                "patterns": [p.to_dict() for p in self._patterns.values()],
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return str(output_path)

        except Exception as e:
            print(f"[ERROR] Failed to export patterns: {e}")
            return ""

    def import_patterns(self, input_path: Path) -> int:
        """
        Import patterns from JSON file

        Args:
            input_path: Input file path

        Returns:
            Number of patterns imported
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            count = 0
            for pattern_data in data.get("patterns", []):
                pattern = BugPattern.from_dict(pattern_data)
                if pattern.pattern_id not in self._patterns:
                    self.add_pattern(pattern)
                    count += 1

            return count

        except Exception as e:
            print(f"[ERROR] Failed to import patterns: {e}")
            return 0


__all__ = [
    "BugSeverity",
    "BugCategory",
    "FixSuggestion",
    "BugPattern",
    "BugKnowledgeBase",
]
