"""
Insight Generator

Analyzes test results and generates intelligent insights.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import Counter


class InsightType(Enum):
    """Types of insights"""
    BUG_PATTERN = "bug_pattern"           # Recurring bug patterns
    PERFORMANCE = "performance"           # Performance issues
    COVERAGE_GAP = "coverage_gap"         # Insufficient test coverage
    CORRELATION = "correlation"           # Correlated failures
    TREND = "trend"                      # Trends over time
    ANOMALY_CLUSTER = "anomaly_cluster"   # Clustered anomalies
    SECURITY_RISK = "security_risk"       # Security concerns
    PREDICTION = "prediction"             # Future predictions


@dataclass
class Insight:
    """
    An insight extracted from test results
    """
    insight_id: str
    type: InsightType
    title: str
    description: str
    severity: str  # low, medium, high, critical
    confidence: float  # 0-1
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "insight_id": self.insight_id,
            "type": self.type.value,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
        }


class InsightGenerator:
    """
    Insight Generator

    Analyzes test results and generates intelligent insights.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize insight generator

        Args:
            config: Configuration options
        """
        self.config = config or {}
        self._insight_count = 0
        self._history: List[Dict] = []

    def generate_insights(self, data: Dict) -> List[Insight]:
        """
        Generate insights from test data

        Args:
            data: Test data including bugs, anomalies, etc.

        Returns:
            List of insights
        """
        insights = []

        # Bug pattern insights
        insights.extend(self._analyze_bug_patterns(data))

        # Performance insights
        insights.extend(self._analyze_performance(data))

        # Coverage gap insights
        insights.extend(self._analyze_coverage(data))

        # Correlation insights
        insights.extend(self._analyze_correlations(data))

        # Anomaly cluster insights
        insights.extend(self._analyze_anomaly_clusters(data))

        # Security risk insights
        insights.extend(self._analyze_security_risks(data))

        # Store in history
        self._history.append({
            "timestamp": time.time(),
            "insight_count": len(insights),
            "data_summary": self._summarize_data(data),
        })

        return insights

    def _analyze_bug_patterns(self, data: Dict) -> List[Insight]:
        """Analyze bug patterns"""
        insights = []
        bugs = data.get("bugs_found", [])

        if not bugs:
            return insights

        # Group bugs by category
        by_category = Counter(b.get("category", "unknown") for b in bugs)

        # Find most common categories
        common_categories = by_category.most_common(3)

        for category, count in common_categories:
            if count >= 3:  # Only if significant
                category_bugs = [b for b in bugs if b.get("category") == category]

                # Check severity distribution
                severity_counts = Counter(b.get("severity", "low") for b in category_bugs)
                high_severity = severity_counts.get("high", 0) + severity_counts.get("critical", 0)

                severity = "medium"
                if high_severity > 2:
                    severity = "critical"
                elif high_severity > 0:
                    severity = "high"

                insight = Insight(
                    insight_id=self._generate_insight_id(),
                    type=InsightType.BUG_PATTERN,
                    title=f"Frequent {category.replace('_', ' ').title()} Bugs",
                    description=f"Found {count} bugs in {category}. {high_severity} are high/critical severity.",
                    severity=severity,
                    confidence=min(count / 10.0, 1.0),
                    evidence={
                        "category": category,
                        "count": count,
                        "severity_breakdown": dict(severity_counts),
                        "examples": [b.get("pattern_name", "unknown") for b in category_bugs[:3]],
                    },
                    recommendations=[
                        f"Review {category} handling code",
                        "Add additional validation checks",
                        "Consider code review for affected areas",
                    ]
                )
                insights.append(insight)

        return insights

    def _analyze_performance(self, data: Dict) -> List[Insight]:
        """Analyze performance issues"""
        insights = []
        anomalies = data.get("anomalies_detected", [])

        if not anomalies:
            return insights

        # Find performance anomalies
        perf_anomalies = [
            a for a in anomalies
            if a.get("anomaly_type") == "performance"
        ]

        if len(perf_anomalies) >= 3:
            # Get affected operations
            affected_ops = Counter(
                a.get("context", {}).get("operation", "unknown")
                for a in perf_anomalies
            )

            worst_op, worst_count = affected_ops.most_common(1)[0]

            insight = Insight(
                insight_id=self._generate_insight_id(),
                type=InsightType.PERFORMANCE,
                title=f"Performance Issues in {worst_op.title()}",
                description=f"Detected {len(perf_anomalies)} performance anomalies, {worst_count} in {worst_op}.",
                severity="high",
                confidence=0.8,
                evidence={
                    "total_anomalies": len(perf_anomalies),
                    "worst_operation": worst_op,
                    "operation_breakdown": dict(affected_ops),
                },
                recommendations=[
                    "Profile the operation for bottlenecks",
                    "Consider adding caching",
                    "Review database query optimization",
                ]
            )
            insights.append(insight)

        return insights

    def _analyze_coverage(self, data: Dict) -> List[Insight]:
        """Analyze test coverage gaps"""
        insights = []
        coverage = data.get("coverage_percentage", 0)
        coverage_details = data.get("coverage_details", {})

        if coverage < 80:
            severity = "critical" if coverage < 50 else "high"
        elif coverage < 90:
            severity = "medium"
        else:
            return insights  # Coverage is good

        # Find under-covered areas
        low_coverage = []
        for area, cov in coverage_details.items():
            if isinstance(cov, (int, float)) and cov < 70:
                low_coverage.append((area, cov))

        low_coverage.sort(key=lambda x: x[1])

        insight = Insight(
            insight_id=self._generate_insight_id(),
            type=InsightType.COVERAGE_GAP,
            title=f"Low Test Coverage: {coverage:.1f}%",
            description=f"Overall coverage is below target. {'Worst areas: ' + ', '.join([f'{a}({c:.0f}%)' for a, c in low_coverage[:3]]) if low_coverage else ''}",
            severity=severity,
            confidence=0.9,
            evidence={
                "coverage_percentage": coverage,
                "low_coverage_areas": low_coverage,
            },
            recommendations=[
                "Add tests for under-covered code paths",
                "Increase boundary value testing",
                "Add edge case tests",
            ]
        )
        insights.append(insight)

        return insights

    def _analyze_correlations(self, data: Dict) -> List[Insight]:
        """Analyze correlated failures"""
        insights = []
        bugs = data.get("bugs_found", [])

        if len(bugs) < 5:
            return insights

        # Check for bugs with same input patterns
        by_dimension = Counter()
        by_metric = Counter()

        for bug in bugs:
            for test in bug.get("affected_tests", []):
                if "dimension" in test:
                    by_dimension["dimension"] += 1
                if "metric_type" in test:
                    by_metric["metric_type"] += 1

        # Find correlations
        if by_dimension:
            dimension, count = by_dimension.most_common(1)[0]
            if count >= 3:
                insight = Insight(
                    insight_id=self._generate_insight_id(),
                    type=InsightType.CORRELATION,
                    title=f"Dimension-Related Bug Cluster",
                    description=f"{count} bugs related to dimension parameter validation.",
                    severity="medium",
                    confidence=0.7,
                    evidence={
                        "parameter": "dimension",
                        "bug_count": count,
                    },
                    recommendations=[
                        "Review dimension validation logic",
                        "Add comprehensive dimension range tests",
                    ]
                )
                insights.append(insight)

        return insights

    def _analyze_anomaly_clusters(self, data: Dict) -> List[Insight]:
        """Analyze clustered anomalies"""
        insights = []
        anomalies = data.get("anomalies_detected", [])

        if len(anomalies) < 5:
            return insights

        # Group by anomaly type
        by_type = Counter(a.get("anomaly_type", "unknown") for a in anomalies)

        # Find clusters
        for anomaly_type, count in by_type.items():
            if count >= 3:
                type_anomalies = [a for a in anomalies if a.get("anomaly_type") == anomaly_type]

                # Check severity
                high_severity = sum(
                    1 for a in type_anomalies
                    if a.get("severity") in ["high", "critical"]
                )

                severity = "medium"
                if high_severity > 2:
                    severity = "high"

                insight = Insight(
                    insight_id=self._generate_insight_id(),
                    type=InsightType.ANOMALY_CLUSTER,
                    title=f"{anomaly_type.title()} Anomaly Cluster",
                    description=f"Detected {count} {anomaly_type} anomalies forming a cluster.",
                    severity=severity,
                    confidence=min(count / 10.0, 1.0),
                    evidence={
                        "anomaly_type": anomaly_type,
                        "count": count,
                        "high_severity_count": high_severity,
                    },
                    recommendations=[
                        f"Investigate {anomaly_type} root cause",
                        "Consider adjusting thresholds",
                        "Review system resource allocation",
                    ]
                )
                insights.append(insight)

        return insights

    def _analyze_security_risks(self, data: Dict) -> List[Insight]:
        """Analyze security risks"""
        insights = []
        vulnerabilities = data.get("security_vulnerabilities", [])

        if not vulnerabilities:
            return insights

        # Count by severity
        by_severity = Counter(v.get("severity", "low") for v in vulnerabilities)

        critical_count = by_severity.get("critical", 0)
        high_count = by_severity.get("high", 0)

        if critical_count > 0 or high_count >= 3:
            insight = Insight(
                insight_id=self._generate_insight_id(),
                type=InsightType.SECURITY_RISK,
                title=f"Security Risk: {critical_count + high_count} High-Impact Vulnerabilities",
                description=f"Found {critical_count} critical and {high_count} high severity security issues.",
                severity="critical",
                confidence=0.95,
                evidence={
                    "critical_count": critical_count,
                    "high_count": high_count,
                    "severity_breakdown": dict(by_severity),
                },
                recommendations=[
                    "Address critical vulnerabilities immediately",
                    "Conduct security code review",
                    "Add security testing to CI/CD",
                ]
            )
            insights.append(insight)

        return insights

    def _summarize_data(self, data: Dict) -> Dict:
        """Create summary of data for history"""
        return {
            "total_tests": data.get("total_tests", 0),
            "bugs_found": len(data.get("bugs_found", [])),
            "anomalies": data.get("anomaly_count", 0),
            "coverage": data.get("coverage_percentage", 0),
        }

    def get_insight_trends(self) -> Dict:
        """
        Get trends from insight history

        Returns:
            Trend analysis results
        """
        if len(self._history) < 2:
            return {"message": "Insufficient data for trend analysis"}

        recent = self._history[-10:]  # Last 10 entries

        # Calculate trends
        bug_trend = []
        anomaly_trend = []

        for entry in recent:
            summary = entry.get("data_summary", {})
            bug_trend.append(summary.get("bugs_found", 0))
            anomaly_trend.append(summary.get("anomalies", 0))

        return {
            "bug_trend": "increasing" if bug_trend[-1] > bug_trend[0] else "decreasing",
            "anomaly_trend": "increasing" if anomaly_trend[-1] > anomaly_trend[0] else "decreasing",
            "recent_bug_counts": bug_trend,
            "recent_anomaly_counts": anomaly_trend,
        }

    def _generate_insight_id(self) -> str:
        """Generate a unique insight ID"""
        self._insight_count += 1
        return f"INSIGHT_{self._insight_count:04d}"

    def get_stats(self) -> Dict:
        """Get generator statistics"""
        return {
            "total_insights_generated": self._insight_count,
            "history_entries": len(self._history),
        }


__all__ = [
    "InsightType",
    "Insight",
    "InsightGenerator",
]
