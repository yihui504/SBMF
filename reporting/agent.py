"""
Reporting Agent

Agent for coordinating smart report generation.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

from agent.runtime import AgentRuntime, AgentConfig
from reporting.report_generator import (
    ReportGenerator, ReportConfig, ReportData, ReportFormat, ReportSection
)
from reporting.insight_generator import InsightGenerator, Insight, InsightType
from reporting.trend_analyzer import TrendAnalyzer, Trend


@dataclass
class ReportingConfig:
    """Configuration for reporting agent"""
    output_dir: Path
    formats: List[ReportFormat] = None
    generate_insights: bool = True
    analyze_trends: bool = True
    auto_generate: bool = True  # Auto-generate after tests

    def __post_init__(self):
        if self.formats is None:
            self.formats = [ReportFormat.MARKDOWN, ReportFormat.HTML]


@dataclass
class ReportResult:
    """Result of report generation"""
    success: bool
    format: ReportFormat
    output_path: str = ""
    error: str = ""
    insights_count: int = 0
    trends_count: int = 0


class ReportingAgent:
    """
    Reporting Agent

    Coordinates smart report generation with insights and trend analysis.
    """

    def __init__(self, output_dir: Path, config: Optional[ReportingConfig] = None):
        """
        Initialize reporting agent

        Args:
            output_dir: Directory for report output
            config: Reporting configuration
        """
        self.output_dir = Path(output_dir)
        self.config = config or ReportingConfig(output_dir=self.output_dir)

        # Initialize agent runtime
        agent_config = AgentConfig(
            agent_id="reporting_agent",
            enable_monitoring=True,
            enable_memory=True
        )
        self.runtime = AgentRuntime(agent_config)

        # Initialize components
        self.report_generator = ReportGenerator()
        self.insight_generator = InsightGenerator()
        self.trend_analyzer = TrendAnalyzer()

        # Report history
        self._report_history: List[Dict] = []

    def generate_report(self, data: ReportData,
                       formats: Optional[List[ReportFormat]] = None) -> List[ReportResult]:
        """
        Generate a report with insights and trends

        Args:
            data: Report data
            formats: Report formats (uses config if None)

        Returns:
            List of report generation results
        """
        self.runtime.start()

        try:
            formats = formats or self.config.formats
            results = []

            # Generate insights
            if self.config.generate_insights:
                insights = self.insight_generator.generate_insights(data.to_dict())
                data.insights = [i.to_dict() for i in insights]

                # Generate recommendations from insights
                data.recommendations = self._generate_recommendations(insights)
            else:
                insights = []
                data.recommendations = []

            # Analyze trends
            if self.config.analyze_trends:
                # Update trend data
                self._update_trend_data(data)

                # Get trends
                trends = self.trend_analyzer.analyze_trends()
                data.trend_data = [t.to_dict() for t in trends]
            else:
                trends = []

            # Generate reports in each format
            for fmt in formats:
                self.report_generator.config.format = fmt

                output_path = self.output_dir / f"report_{fmt.value}.{self._get_extension(fmt)}"

                try:
                    content = self.report_generator.generate(data, output_path)

                    result = ReportResult(
                        success=True,
                        format=fmt,
                        output_path=str(output_path),
                        insights_count=len(insights),
                        trends_count=len(trends),
                    )
                    results.append(result)

                except Exception as e:
                    result = ReportResult(
                        success=False,
                        format=fmt,
                        error=str(e),
                        insights_count=len(insights),
                        trends_count=len(trends),
                    )
                    results.append(result)

            # Store in history
            self._report_history.append({
                "timestamp": data.end_time,
                "formats": [f.value for f in formats],
                "results": [r.__dict__ for r in results],
                "insights_count": len(insights),
                "trends_count": len(trends),
            })

            # Store in memory
            self.runtime.remember(
                f"report_{int(data.end_time)}",
                data.to_dict(),
                "long_term"
            )

            return results

        finally:
            self.runtime.stop()

    def _update_trend_data(self, data: ReportData) -> None:
        """Update trend analyzer with new data"""
        # Add data points for key metrics
        self.trend_analyzer.add_data_point(
            "total_tests",
            data.total_tests,
            {"timestamp": data.end_time}
        )

        self.trend_analyzer.add_data_point(
            "bugs_found",
            len(data.bugs_found),
            {"timestamp": data.end_time}
        )

        self.trend_analyzer.add_data_point(
            "pass_rate",
            (data.passed_tests / data.total_tests * 100) if data.total_tests > 0 else 0,
            {"timestamp": data.end_time}
        )

        self.trend_analyzer.add_data_point(
            "coverage",
            data.coverage_percentage,
            {"timestamp": data.end_time}
        )

        self.trend_analyzer.add_data_point(
            "anomalies",
            data.anomaly_count,
            {"timestamp": data.end_time}
        )

    def _generate_recommendations(self, insights: List[Insight]) -> List[Dict]:
        """Generate recommendations from insights"""
        recommendations = []

        # Group insights by severity
        critical_insights = [i for i in insights if i.severity == "critical"]
        high_insights = [i for i in insights if i.severity == "high"]

        # High priority recommendations from critical insights
        for insight in critical_insights[:3]:
            recommendations.append({
                "title": f"Address: {insight.title}",
                "description": insight.description,
                "priority": "critical",
                "insight_id": insight.insight_id,
                "actions": insight.recommendations,
            })

        # Medium priority from high insights
        for insight in high_insights[:3]:
            recommendations.append({
                "title": f"Review: {insight.title}",
                "description": insight.description,
                "priority": "high",
                "insight_id": insight.insight_id,
                "actions": insight.recommendations,
            })

        # General recommendations if specific ones are few
        if len(recommendations) < 5:
            recommendations.extend([
                {
                    "title": "Improve Test Coverage",
                    "description": "Consider adding tests for edge cases and boundary conditions.",
                    "priority": "medium",
                },
                {
                    "title": "Review Bug Patterns",
                    "description": "Analyze recurring bug patterns for systemic fixes.",
                    "priority": "medium",
                },
                {
                    "title": "Monitor Performance Trends",
                    "description": "Keep track of performance metrics over time.",
                    "priority": "low",
                },
            ])

        return recommendations[:10]

    def get_insights(self, data: ReportData) -> List[Insight]:
        """Get insights from data"""
        return self.insight_generator.generate_insights(data.to_dict())

    def get_trends(self) -> List[Trend]:
        """Get current trends"""
        return self.trend_analyzer.analyze_trends()

    def predict_metrics(self, metric_names: List[str],
                       horizon: int = 5) -> Dict[str, Dict]:
        """
        Predict future values for metrics

        Args:
            metric_names: List of metric names to predict
            horizon: Prediction horizon

        Returns:
            Dictionary mapping metric names to predictions
        """
        predictions = {}

        for metric_name in metric_names:
            pred = self.trend_analyzer.predict_next(metric_name, horizon)
            if pred:
                predictions[metric_name] = pred

        return predictions

    def get_summary(self) -> str:
        """
        Get a quick summary of recent reporting

        Returns:
            Summary string
        """
        if not self._report_history:
            return "No reports generated yet."

        latest = self._report_history[-1]

        return f"""
Latest Report Summary:
  Generated: {latest['timestamp']}
  Formats: {', '.join(latest['formats'])}
  Insights: {latest['insights_count']}
  Trends: {latest['trends_count']}
  Status: {'Success' if all(r['success'] for r in latest['results']) else 'Errors'}
""".strip()

    def get_statistics(self) -> Dict:
        """Get reporting statistics"""
        return {
            "agent_stats": self.runtime.get_stats(),
            "total_reports": len(self._report_history),
            "insight_stats": self.insight_generator.get_stats(),
            "trend_stats": self.trend_analyzer.get_stats(),
        }

    def _get_extension(self, fmt: ReportFormat) -> str:
        """Get file extension for format"""
        extensions = {
            ReportFormat.JSON: "json",
            ReportFormat.HTML: "html",
            ReportFormat.MARKDOWN: "md",
            ReportFormat.TEXT: "txt",
            ReportFormat.PDF: "pdf",
        }
        return extensions.get(fmt, "txt")


__all__ = [
    "ReportingConfig",
    "ReportResult",
    "ReportingAgent",
]
