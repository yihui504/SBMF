"""
Bug Classification and Analysis System

Provides intelligent bug analysis, classification, and fix recommendations.
"""

from bug_classifier.knowledge_base import BugKnowledgeBase, BugPattern
from bug_classifier.feature_extractor import BugFeatureExtractor
from bug_classifier.similarity import BugSimilarityMatcher
from bug_classifier.agent import BugAnalysisAgent

__all__ = [
    "BugKnowledgeBase",
    "BugPattern",
    "BugFeatureExtractor",
    "BugSimilarityMatcher",
    "BugAnalysisAgent",
]
