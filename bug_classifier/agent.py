"""
Bug Analysis Agent

AI agent for intelligent bug analysis and fix recommendations.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from agent.runtime import AgentRuntime, AgentConfig
from agent.memory import AgentMemory, MemoryType
from bug_classifier.knowledge_base import BugKnowledgeBase, BugPattern, FixSuggestion
from bug_classifier.feature_extractor import BugFeatureExtractor, BugFeatures
from bug_classifier.similarity import BugSimilarityMatcher, SimilarityMatch


@dataclass
class BugAnalysisResult:
    """Result of bug analysis"""
    bug_detected: bool
    pattern_id: Optional[str] = None
    pattern_name: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    confidence: str = "low"  # low, medium, high
    root_cause: str = ""
    symptoms: List[str] = None
    fix_suggestions: List[Dict] = None
    similar_bugs: List[str] = None
    extracted_features: Dict = None

    def __post_init__(self):
        if self.symptoms is None:
            self.symptoms = []
        if self.fix_suggestions is None:
            self.fix_suggestions = []
        if self.similar_bugs is None:
            self.similar_bugs = []
        if self.extracted_features is None:
            self.extracted_features = {}

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "bug_detected": self.bug_detected,
            "pattern_id": self.pattern_id,
            "pattern_name": self.pattern_name,
            "category": self.category,
            "severity": self.severity,
            "confidence": self.confidence,
            "root_cause": self.root_cause,
            "symptoms": self.symptoms,
            "fix_suggestions": self.fix_suggestions,
            "similar_bugs": self.similar_bugs,
            "extracted_features": self.extracted_features,
        }


class BugAnalysisAgent:
    """
    Bug Analysis Agent

    Uses knowledge base, similarity matching, and intelligent reasoning
    to analyze bugs and generate fix recommendations.
    """

    def __init__(self, knowledge_base: Optional[BugKnowledgeBase] = None):
        """
        Initialize bug analysis agent

        Args:
            knowledge_base: Bug knowledge base (creates new if None)
        """
        self.kb = knowledge_base or BugKnowledgeBase()
        self.extractor = BugFeatureExtractor()
        self.matcher = BugSimilarityMatcher(self.kb)

        # Create agent runtime for advanced capabilities
        config = AgentConfig(
            agent_id="bug_analysis_agent",
            enable_monitoring=True,
            enable_memory=True
        )
        self.runtime = AgentRuntime(config)

    def analyze(self, test_case: Any, execution_result: Any,
               oracle_results: Optional[List] = None,
               context: Optional[Dict] = None) -> BugAnalysisResult:
        """
        Analyze a test execution for bugs

        Args:
            test_case: The test case that was executed
            execution_result: Result from execution
            oracle_results: Results from oracle checks
            context: Additional context

        Returns:
            BugAnalysisResult with analysis findings
        """
        # Start agent runtime
        self.runtime.start()

        try:
            # Extract features
            features = self.extractor.extract(
                test_case, execution_result, oracle_results, context
            )

            # Store in memory
            self.runtime.remember(
                f"features_{features.test_id}",
                features.to_dict(),
                MemoryType.SHORT_TERM
            )

            # Check if there's an actual bug (failure or constraint violation)
            is_bug = self._is_bug(features, execution_result)

            if not is_bug:
                return BugAnalysisResult(bug_detected=False)

            # Match against patterns
            matches = self.matcher.match(features, threshold=0.2)

            if not matches:
                # No pattern matched, create generic analysis
                return self._create_generic_analysis(features)

            # Use best match
            best_match = matches[0]

            # Update pattern occurrence
            self.kb.update_pattern_occurrence(best_match.pattern.pattern_id)

            # Create analysis result
            result = BugAnalysisResult(
                bug_detected=True,
                pattern_id=best_match.pattern.pattern_id,
                pattern_name=best_match.pattern.name,
                category=best_match.pattern.category.value,
                severity=best_match.pattern.severity.value,
                confidence=best_match.confidence,
                root_cause=best_match.pattern.root_cause,
                symptoms=best_match.pattern.symptoms,
                fix_suggestions=self._format_fix_suggestions(best_match.pattern.fix_suggestions),
                similar_bugs=self._get_similar_bugs(best_match.pattern),
                extracted_features=features.to_dict()
            )

            # Store analysis in memory
            self.runtime.remember(
                f"analysis_{features.test_id}",
                result.to_dict(),
                MemoryType.LONG_TERM,
                metadata={"pattern_id": best_match.pattern.pattern_id}
            )

            return result

        finally:
            self.runtime.stop()

    def _is_bug(self, features: BugFeatures, execution_result: Any) -> bool:
        """Determine if the execution result indicates a bug"""
        # Check if execution failed
        if features.status_category in ["FAILURE", "TIMEOUT", "CRASH", "PRECONDITION_FAILED"]:
            return True

        # Check if constraints were violated
        if features.violated_constraints:
            return True

        # Check if oracles failed
        if features.oracle_failed_count > 0:
            return True

        return False

    def _create_generic_analysis(self, features: BugFeatures) -> BugAnalysisResult:
        """Create analysis when no pattern matched"""
        # Infer category from error
        category_map = {
            "timeout": "performance",
            "connection": "infra",
            "validation": "validation",
            "memory": "performance",
            "concurrency": "concurrency",
        }
        category = category_map.get(features.error_category, "unknown")

        # Infer severity
        if category == "infra":
            severity = "critical"
        elif features.oracle_failed_count > 2:
            severity = "high"
        else:
            severity = "medium"

        return BugAnalysisResult(
            bug_detected=True,
            category=category,
            severity=severity,
            confidence="low",
            root_cause="Unknown pattern - needs manual analysis",
            symptoms=[features.error_message] + features.error_keywords,
            extracted_features=features.to_dict()
        )

    def _format_fix_suggestions(self, suggestions: List[FixSuggestion]) -> List[Dict]:
        """Format fix suggestions for output"""
        formatted = []

        for suggestion in suggestions:
            formatted.append({
                "type": suggestion.type,
                "description": suggestion.description,
                "code_template": suggestion.code_template,
                "safe": suggestion.safe,
                "estimated_effort": suggestion.estimated_effort,
                "references": suggestion.references
            })

        return formatted

    def _get_similar_bugs(self, pattern: BugPattern) -> List[str]:
        """Get list of similar bug pattern IDs"""
        similar = self.kb.find_similar_patterns(pattern.pattern_id, min_overlap=1)
        return [p.pattern_id for p in similar]

    def batch_analyze(self, test_cases: List[Any],
                     execution_results: List[Any],
                     context: Optional[Dict] = None) -> List[BugAnalysisResult]:
        """
        Analyze multiple test executions in batch

        Args:
            test_cases: List of test cases
            execution_results: List of execution results
            context: Shared context

        Returns:
            List of analysis results
        """
        if len(test_cases) != len(execution_results):
            raise ValueError("test_cases and execution_results must have same length")

        results = []
        for test_case, exec_result in zip(test_cases, execution_results):
            result = self.analyze(test_case, exec_result, context=context)
            results.append(result)

        return results

    def get_statistics(self) -> Dict:
        """Get analysis statistics"""
        return {
            "agent_stats": self.runtime.get_stats(),
            "kb_stats": self.kb.get_stats(),
        }

    def learn_from_feedback(self, pattern_id: str, was_correct: bool,
                          actual_category: Optional[str] = None) -> None:
        """
        Learn from feedback to improve future analysis

        Args:
            pattern_id: Pattern that was matched
            was_correct: Whether the pattern match was correct
            actual_category: Actual bug category if different
        """
        # Store feedback in memory
        self.runtime.remember(
            f"feedback_{pattern_id}",
            {
                "was_correct": was_correct,
                "actual_category": actual_category,
                "timestamp": self._agent._memory if hasattr(self, '_agent') else None
            },
            MemoryType.LONG_TERM
        )

        # Could update pattern statistics here
        # For now, just log the feedback
        if not was_correct:
            print(f"[INFO] Pattern {pattern_id} needs adjustment. "
                  f"Actual: {actual_category}")


__all__ = [
    "BugAnalysisResult",
    "BugAnalysisAgent",
]
