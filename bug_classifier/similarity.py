"""
Bug Similarity Matcher

Matches new bugs against historical patterns using similarity algorithms.
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from bug_classifier.feature_extractor import BugFeatures
from bug_classifier.knowledge_base import BugPattern, BugKnowledgeBase


@dataclass
class SimilarityMatch:
    """A similarity match result"""
    pattern: BugPattern
    score: float
    matched_features: List[str]
    confidence: str  # low, medium, high


class BugSimilarityMatcher:
    """
    Bug Similarity Matcher

    Matches new bug reports against historical patterns using
    feature similarity and various matching algorithms.
    """

    def __init__(self, knowledge_base: BugKnowledgeBase):
        """
        Initialize similarity matcher

        Args:
            knowledge_base: Bug knowledge base to search
        """
        self.kb = knowledge_base

    def match(self, features: BugFeatures,
             threshold: float = 0.3) -> List[SimilarityMatch]:
        """
        Match bug features against knowledge base patterns

        Args:
            features: Extracted bug features
            threshold: Minimum similarity threshold

        Returns:
            List of similarity matches, sorted by score descending
        """
        matches = []

        for pattern in self.kb.list_patterns():
            score, matched_features = self._compute_similarity(features, pattern)

            if score >= threshold:
                matches.append(SimilarityMatch(
                    pattern=pattern,
                    score=score,
                    matched_features=matched_features,
                    confidence=self._assess_confidence(score)
                ))

        return sorted(matches, key=lambda m: -m.score)

    def _compute_similarity(self, features: BugFeatures,
                           pattern: BugPattern) -> Tuple[float, List[str]]:
        """
        Compute similarity score between features and pattern

        Returns:
            Tuple of (score, matched_features)
        """
        score = 0.0
        matched = []
        max_score = 0.0

        # Symptom matching (40% weight)
        symptom_score, symptom_matched = self._match_symptoms(features, pattern)
        max_score += 0.4
        score += symptom_score * 0.4
        matched.extend(symptom_matched)

        # Category matching (20% weight)
        category_score, category_matched = self._match_category(features, pattern)
        max_score += 0.2
        score += category_score * 0.2
        matched.extend(category_matched)

        # Error pattern matching (20% weight)
        error_score, error_matched = self._match_error_patterns(features, pattern)
        max_score += 0.2
        score += error_score * 0.2
        matched.extend(error_matched)

        # Input feature matching (10% weight)
        input_score, input_matched = self._match_input_features(features, pattern)
        max_score += 0.1
        score += input_score * 0.1
        matched.extend(input_matched)

        # Tag matching (10% weight)
        tag_score, tag_matched = self._match_tags(features, pattern)
        max_score += 0.1
        score += tag_score * 0.1
        matched.extend(tag_matched)

        # Normalize score
        if max_score > 0:
            score = score / max_score

        return score, list(set(matched))

    def _match_symptoms(self, features: BugFeatures,
                       pattern: BugPattern) -> Tuple[float, List[str]]:
        """Match symptoms against pattern"""
        if not pattern.symptoms:
            return 0.0, []

        matched = []
        symptoms_to_match = [
            features.error_message,
            *features.error_keywords,
            *features.violated_constraints
        ]

        for symptom in symptoms_to_match:
            for pattern_symptom in pattern.symptoms:
                if pattern_symptom.lower() in symptom.lower():
                    matched.append("symptom:" + pattern_symptom)
                    break

        score = len(matched) / len(pattern.symptoms) if pattern.symptoms else 0.0
        return score, matched

    def _match_category(self, features: BugFeatures,
                       pattern: BugPattern) -> Tuple[float, List[str]]:
        """Match category"""
        # Map error categories to bug categories
        category_map = {
            "timeout": "performance",
            "connection": "infra",
            "validation": "validation",
            "memory": "performance",
            "concurrency": "concurrency",
        }

        inferred_category = category_map.get(features.error_category, "")

        if inferred_category == pattern.category.value:
            return 1.0, ["category_match"]
        elif inferred_category:
            return 0.0, []
        else:
            return 0.0, []

    def _match_error_patterns(self, features: BugFeatures,
                            pattern: BugPattern) -> Tuple[float, List[str]]:
        """Match error patterns"""
        if not pattern.error_patterns:
            return 0.0, []

        matched = []

        for pattern_str in pattern.error_patterns:
            if re.search(pattern_str, features.error_message, re.IGNORECASE):
                matched.append("error_pattern:" + pattern_str)

        score = len(matched) / len(pattern.error_patterns) if pattern.error_patterns else 0.0
        return score, matched

    def _match_input_features(self, features: BugFeatures,
                             pattern: BugPattern) -> Tuple[float, List[str]]:
        """Match input features"""
        matched = []
        score = 0.0

        # Check for dimension-related patterns
        if "dimension" in pattern.tags:
            if features.input_dimension > 0:
                score += 0.3
                matched.append("has_dimension")

            # Check for boundary values
            if features.is_boundary_test and "boundary" in pattern.tags:
                score += 0.4
                matched.append("is_boundary")

        # Check for metric-related patterns
        if "metric" in pattern.tags and features.input_metric_type:
            score += 0.5
            matched.append("has_metric")

        return score, matched

    def _match_tags(self, features: BugFeatures,
                   pattern: BugPattern) -> Tuple[float, List[str]]:
        """Match tags"""
        matched = []

        for tag in pattern.tags:
            if tag == "dimension" and features.input_dimension > 0:
                matched.append("tag:dimension")
            elif tag == "metric" and features.input_metric_type:
                matched.append("tag:metric")
            elif tag == "validation" and features.violated_constraints:
                matched.append("tag:validation")
            elif tag == "search" and features.operation == "search":
                matched.append("tag:search")

        score = len(matched) / len(pattern.tags) if pattern.tags else 0.0
        return score, matched

    def _assess_confidence(self, score: float) -> str:
        """Assess confidence level from score"""
        if score >= 0.8:
            return "high"
        elif score >= 0.5:
            return "medium"
        else:
            return "low"

    def get_best_match(self, features: BugFeatures,
                       min_threshold: float = 0.3) -> Optional[SimilarityMatch]:
        """
        Get the best matching pattern

        Args:
            features: Bug features to match
            min_threshold: Minimum similarity threshold

        Returns:
            Best match or None
        """
        matches = self.match(features, threshold=min_threshold)
        return matches[0] if matches else None


import re

__all__ = [
    "SimilarityMatch",
    "BugSimilarityMatcher",
]
