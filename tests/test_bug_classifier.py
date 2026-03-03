"""
Tests for Bug Classification and Analysis (M4)
"""
import pytest
import tempfile
from pathlib import Path

from bug_classifier.knowledge_base import (
    BugKnowledgeBase, BugPattern, BugSeverity, BugCategory,
    FixSuggestion
)
from bug_classifier.feature_extractor import BugFeatureExtractor, BugFeatures
from bug_classifier.similarity import BugSimilarityMatcher, SimilarityMatch
from bug_classifier.agent import BugAnalysisAgent, BugAnalysisResult
from bug_classifier.fix_generator import FixValidator, FixValidationResult


# ================================================================
# BugKnowledgeBase Tests
# ================================================================

class TestBugKnowledgeBase:
    """Test bug knowledge base"""

    def test_initialization(self):
        """Test knowledge base initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = BugKnowledgeBase(Path(tmpdir) / "test_kb.json")
            assert len(kb.list_patterns()) > 0  # Should have default patterns

    def test_add_pattern(self):
        """Test adding a pattern"""
        kb = BugKnowledgeBase()
        pattern = BugPattern(
            pattern_id="TEST_001",
            name="Test Pattern",
            category=BugCategory.VALIDATION,
            severity=BugSeverity.MEDIUM,
            description="A test pattern"
        )

        kb.add_pattern(pattern)
        assert kb.get_pattern("TEST_001") is pattern

    def test_search_by_symptoms(self):
        """Test searching by symptoms"""
        kb = BugKnowledgeBase()

        matches = kb.search_by_symptoms(["dimension too large"])
        assert len(matches) > 0
        assert matches[0][1] > 0  # Should have a score

    def test_search_by_symptoms_error_message(self):
        """Test searching by actual error message"""
        kb = BugKnowledgeBase()

        # Test with actual error message format
        matches = kb.search_by_symptoms(["Dimension 99999 exceeds maximum 32768"])
        assert len(matches) > 0  # Should match P001

    def test_get_fix_suggestions(self):
        """Test getting fix suggestions"""
        kb = BugKnowledgeBase()
        suggestions = kb.get_fix_suggestions("P001")

        assert len(suggestions) > 0
        assert suggestions[0].type == "validation"

    def test_safe_fix_templates(self):
        """Test getting safe fix templates"""
        kb = BugKnowledgeBase()
        templates = kb.get_safe_fix_templates()

        assert len(templates) > 0
        # All templates should be marked safe
        assert all(isinstance(t, str) for t in templates.values())

    def test_pattern_occurrence_tracking(self):
        """Test updating pattern occurrence"""
        kb = BugKnowledgeBase()
        initial_count = kb.get_pattern("P001").occurrence_count

        kb.update_pattern_occurrence("P001")
        new_count = kb.get_pattern("P001").occurrence_count

        assert new_count == initial_count + 1

    def test_export_import_patterns(self):
        """Test exporting and importing patterns"""
        kb1 = BugKnowledgeBase()

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "export.json"
            kb1.export_patterns(export_path)

            # Create new KB and import
            kb2 = BugKnowledgeBase(Path(tmpdir) / "new_kb.json")
            count = kb2.import_patterns(export_path)

            assert count > 0


# ================================================================
# BugFeatureExtractor Tests
# ================================================================

class TestBugFeatureExtractor:
    """Test bug feature extractor"""

    def test_extraction(self):
        """Test feature extraction"""
        extractor = BugFeatureExtractor()

        # Create mock test case and result
        class TestCase:
            test_id = "TEST_001"
            operation = "search"
            slot_values = {"dimension": 99999, "metric_type": "L2", "top_k": 10}

        class ExecutionResult:
            status = "FAILURE"
            error = ValueError("Dimension 99999 exceeds maximum 32768")
            elapsed_seconds = 0.5

        features = extractor.extract(TestCase(), ExecutionResult(), None)

        assert features.test_id == "TEST_001"
        assert features.operation == "search"
        assert features.status == "FAILURE"
        assert features.has_error
        assert features.input_dimension == 99999
        assert features.execution_time_ms == 500

    def test_boundary_detection(self):
        """Test boundary test detection"""
        extractor = BugFeatureExtractor()

        class TestCase:
            test_id = "BOUNDARY_001"
            operation = "search"
            slot_values = {"dimension": 1}  # Boundary value

        class ExecutionResult:
            status = "SUCCESS"
            error = None
            elapsed_seconds = 0.1

        features = extractor.extract(TestCase(), ExecutionResult(), None)

        assert features.is_boundary_test

    def test_oracle_features(self):
        """Test oracle-related features"""
        extractor = BugFeatureExtractor()

        class TestCase:
            test_id = "ORACLE_001"
            operation = "search"
            slot_values = {}

        class ExecutionResult:
            status = "SUCCESS"
            error = None
            elapsed_seconds = 0.1

        # Mock oracle results
        class OracleResult:
            passed = False
            violated_slots = ["dimension"]

        oracle_results = [OracleResult(), OracleResult()]

        features = extractor.extract(TestCase(), ExecutionResult(), oracle_results)

        assert features.oracle_total_count == 2
        assert features.oracle_failed_count == 2
        assert features.violated_constraints == ["dimension", "dimension"]


# ================================================================
# BugSimilarityMatcher Tests
# ================================================================

class TestBugSimilarityMatcher:
    """Test bug similarity matcher"""

    def test_matching(self):
        """Test pattern matching"""
        kb = BugKnowledgeBase()
        matcher = BugSimilarityMatcher(kb)

        # Create features that match P001 (Dimension Exceeds Maximum)
        features = BugFeatures(
            error_message="Dimension 99999 exceeds maximum 32768",
            error_keywords=["dimension", "exceeds", "maximum"],
            input_dimension=99999
        )

        matches = matcher.match(features, threshold=0.1)

        assert len(matches) > 0
        assert matches[0].pattern.pattern_id == "P001"
        assert matches[0].score > 0

    def test_best_match(self):
        """Test getting best match"""
        kb = BugKnowledgeBase()
        matcher = BugSimilarityMatcher(kb)

        features = BugFeatures(
            error_message="Dimension 99999 exceeds maximum 32768",
            error_keywords=["dimension", "exceeds"],
            input_dimension=99999
        )

        best = matcher.get_best_match(features, min_threshold=0.1)

        assert best is not None
        assert best.pattern.pattern_id == "P001"

    def test_no_match(self):
        """Test when no pattern matches"""
        kb = BugKnowledgeBase()
        matcher = BugSimilarityMatcher(kb)

        features = BugFeatures(
            error_message="Some unknown error XYZ123",
            status_category="SUCCESS"
        )

        matches = matcher.match(features, threshold=0.5)
        assert len(matches) == 0


# ================================================================
# BugAnalysisAgent Tests
# ================================================================

class TestBugAnalysisAgent:
    """Test bug analysis agent"""

    def test_initialization(self):
        """Test agent initialization"""
        agent = BugAnalysisAgent()
        assert agent.kb is not None
        assert agent.extractor is not None
        assert agent.matcher is not None

    def test_analysis_with_bug(self):
        """Test analyzing a test with a bug"""
        agent = BugAnalysisAgent()

        # Create test case with dimension error
        class TestCase:
            test_id = "TEST_001"
            operation = "search"
            slot_values = {"dimension": 99999, "metric_type": "L2"}

        class ExecutionResult:
            status = "FAILURE"
            error = ValueError("Dimension 99999 exceeds maximum 32768")
            elapsed_seconds = 0.1

        result = agent.analyze(TestCase(), ExecutionResult())

        assert result.bug_detected
        assert result.pattern_id == "P001"
        assert "dimension" in result.pattern_name.lower()
        assert result.category == "validation"
        assert len(result.fix_suggestions) > 0

    def test_analysis_without_bug(self):
        """Test analyzing a successful test"""
        agent = BugAnalysisAgent()

        class TestCase:
            test_id = "TEST_001"
            operation = "search"
            slot_values = {"dimension": 512, "metric_type": "L2", "top_k": 10}

        class ExecutionResult:
            status = "SUCCESS"
            error = None
            elapsed_seconds = 0.1

        result = agent.analyze(TestCase(), ExecutionResult())

        assert not result.bug_detected

    def test_batch_analyze(self):
        """Test batch analysis"""
        agent = BugAnalysisAgent()

        # Create multiple test cases
        test_cases = [
            self._create_test_case("TEST_001", 99999),
            self._create_test_case("TEST_002", 512),
        ]

        results = [
            self._create_result(True),
            self._create_result(False)
        ]

        analysis_results = agent.batch_analyze(test_cases, results)

        assert len(analysis_results) == 2
        assert analysis_results[0].bug_detected  # First has bug
        assert not analysis_results[1].bug_detected  # Second is successful

    def _create_test_case(self, test_id, dimension):
        """Helper to create test case"""
        class TestCase:
            pass
        tc = TestCase()
        tc.test_id = test_id
        tc.operation = "search"
        tc.slot_values = {"dimension": dimension}
        return tc

    def _create_result(self, has_error):
        """Helper to create execution result"""
        class ExecutionResult:
            pass
        er = ExecutionResult()
        if has_error:
            er.status = "FAILURE"
            er.error = ValueError("Dimension too large")
            er.elapsed_seconds = 0.1
        else:
            er.status = "SUCCESS"
            er.error = None
            er.elapsed_seconds = 0.1
        return er


# ================================================================
# FixValidator Tests
# ================================================================

class TestFixValidator:
    """Test fix validator"""

    def test_validate_safe_code(self):
        """Test validating safe code"""
        validator = FixValidator()
        code = '''
def validate_dimension(dimension: int) -> int:
    if dimension < 1:
        raise ValueError("Dimension must be positive")
    return dimension
'''

        result = validator.validate(code, "P001")

        assert result.is_safe
        assert result.syntax_valid
        assert len(result.issues) == 0
        assert result.score > 0.8

    def test_validate_unsafe_code(self):
        """Test validating unsafe code"""
        validator = FixValidator()
        code = "result = eval(user_input)  # Dangerous!"

        result = validator.validate(code, "P001")

        assert not result.is_safe
        assert len(result.issues) > 0

    def test_validate_syntax_error(self):
        """Test validating code with syntax error"""
        validator = FixValidator()
        code = "def broken(  # Missing closing paren"

        result = validator.validate(code, "P001")

        assert not result.syntax_valid
        assert result.score < 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
