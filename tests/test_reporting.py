"""
Tests for M6: Smart Reporting
"""
import pytest
import tempfile
import time
from pathlib import Path

from reporting.report_generator import (
    ReportGenerator, ReportConfig, ReportData, ReportFormat, ReportSection
)
from reporting.insight_generator import InsightGenerator, InsightType, Insight
from reporting.trend_analyzer import TrendAnalyzer, TrendDirection, Trend
from reporting.agent import ReportingAgent, ReportingConfig, ReportResult


# ================================================================
# Report Generator Tests
# ================================================================

class TestReportGenerator:
    """Test report generator"""

    def test_initialization(self):
        """Test generator initialization"""
        config = ReportConfig(title="Test Report")
        generator = ReportGenerator(config)

        assert generator.config.title == "Test Report"

    def test_generate_json(self):
        """Test JSON report generation"""
        config = ReportConfig(format=ReportFormat.JSON)
        generator = ReportGenerator(config)
        data = self._create_test_data()

        content = generator.generate(data)

        # Check for JSON structure
        assert '"title"' in content or '"Bug Mining Report"' in content
        assert '"total_tests"' in content

    def test_generate_markdown(self):
        """Test Markdown report generation"""
        config = ReportConfig(format=ReportFormat.MARKDOWN, title="Test Report")
        generator = ReportGenerator(config)
        data = self._create_test_data()

        content = generator.generate(data)

        assert "# Test Report" in content
        assert "## Summary" in content
        assert "Total Tests" in content

    def test_generate_html(self):
        """Test HTML report generation"""
        config = ReportConfig(format=ReportFormat.HTML, title="Test Report")
        generator = ReportGenerator(config)
        data = self._create_test_data()

        content = generator.generate(data)

        assert "<!DOCTYPE html>" in content
        assert "<title>Test Report</title>" in content

    def test_generate_summary(self):
        """Test quick summary generation"""
        generator = ReportGenerator()
        data = self._create_test_data()

        summary = generator.generate_summary(data)

        assert "Total:" in summary
        assert "Passed:" in summary
        assert "Bugs:" in summary

    def test_save_to_file(self):
        """Test saving report to file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ReportConfig(title="Test Report")
            generator = ReportGenerator(config)
            data = self._create_test_data()

            output_path = Path(tmpdir) / "report.md"
            generator.generate(data, output_path)

            assert output_path.exists()

            content = output_path.read_text()
            assert "# Test Report" in content

    def _create_test_data(self) -> ReportData:
        """Create test report data"""
        return ReportData(
            total_tests=100,
            passed_tests=85,
            failed_tests=15,
            test_duration=123.45,
            bugs_found=[
                {
                    "pattern_name": "Dimension Error",
                    "category": "validation",
                    "severity": "high",
                    "description": "Dimension exceeds maximum",
                    "root_cause": "Missing validation",
                },
            ],
            bug_categories={"validation": 10, "logic": 5},
            anomalies_detected=[
                {
                    "anomaly_type": "performance",
                    "description": "High response time",
                    "severity": "medium",
                }
            ],
            anomaly_count=5,
            coverage_percentage=75.5,
            insights=[
                {
                    "title": "Test Insight",
                    "description": "Analysis finding",
                }
            ],
            recommendations=[
                {
                    "title": "Test Recommendation",
                    "description": "Suggested action",
                    "priority": "high",
                }
            ],
            target_system="TestDB",
        )


# ================================================================
# Insight Generator Tests
# ================================================================

class TestInsightGenerator:
    """Test insight generator"""

    def test_initialization(self):
        """Test generator initialization"""
        generator = InsightGenerator()

        stats = generator.get_stats()
        assert stats["total_insights_generated"] == 0

    def test_generate_insights(self):
        """Test insight generation"""
        generator = InsightGenerator()

        data = {
            "bugs_found": [
                {"category": "validation", "severity": "high"},
                {"category": "validation", "severity": "high"},
                {"category": "validation", "severity": "high"},
            ],
            "anomalies_detected": [],
            "coverage_percentage": 60,
        }

        insights = generator.generate_insights(data)

        assert len(insights) > 0

    def test_bug_pattern_insights(self):
        """Test bug pattern insight generation"""
        generator = InsightGenerator()

        data = {
            "bugs_found": [
                {"category": "validation", "severity": "high", "pattern_name": "Dim Error"},
                {"category": "validation", "severity": "high", "pattern_name": "Type Error"},
                {"category": "validation", "severity": "medium", "pattern_name": "Metric Error"},
                {"category": "logic", "severity": "low", "pattern_name": "Logic Bug"},
            ],
            "anomalies_detected": [],
        }

        insights = generator.generate_insights(data)

        # Should have bug pattern insight
        bug_insights = [i for i in insights if i.type == InsightType.BUG_PATTERN]
        assert len(bug_insights) > 0

    def test_coverage_insights(self):
        """Test coverage gap insight generation"""
        generator = InsightGenerator()

        data = {
            "bugs_found": [],
            "anomalies_detected": [],
            "coverage_percentage": 65,  # Low coverage
            "coverage_details": {"module_a": 80, "module_b": 50},
        }

        insights = generator.generate_insights(data)

        # Should have coverage insight
        coverage_insights = [i for i in insights if i.type == InsightType.COVERAGE_GAP]
        assert len(coverage_insights) > 0

    def test_security_insights(self):
        """Test security risk insight generation"""
        generator = InsightGenerator()

        data = {
            "bugs_found": [],
            "anomalies_detected": [],
            "coverage_percentage": 90,
            "security_vulnerabilities": [
                {"severity": "critical"},
                {"severity": "high"},
                {"severity": "high"},
                {"severity": "high"},
            ],
        }

        insights = generator.generate_insights(data)

        # Should have security insight
        security_insights = [i for i in insights if i.type == InsightType.SECURITY_RISK]
        assert len(security_insights) > 0

    def test_insight_trends(self):
        """Test insight trend analysis"""
        generator = InsightGenerator()

        # Add some history
        for i in range(5):
            data = {
                "bugs_found": [{"category": "test"}] * (i + 1),
                "anomalies_detected": [],
                "coverage_percentage": 80,
            }
            generator.generate_insights(data)

        trends = generator.get_insight_trends()

        assert "bug_trend" in trends
        assert trends["bug_trend"] == "increasing"


# ================================================================
# Trend Analyzer Tests
# ================================================================

class TestTrendAnalyzer:
    """Test trend analyzer"""

    def test_initialization(self):
        """Test analyzer initialization"""
        analyzer = TrendAnalyzer()

        stats = analyzer.get_stats()
        assert stats["total_metrics"] == 0

    def test_add_data_point(self):
        """Test adding data points"""
        analyzer = TrendAnalyzer()

        analyzer.add_data_point("bugs", 5)
        analyzer.add_data_point("bugs", 7)
        analyzer.add_data_point("bugs", 6)

        points = analyzer.get_time_series("bugs")

        assert len(points) == 3

    def test_analyze_trends(self):
        """Test trend analysis"""
        analyzer = TrendAnalyzer()

        # Add increasing data
        for i in range(10):
            analyzer.add_data_point("test_metric", 10 + i)

        trends = analyzer.analyze_trends()

        assert len(trends) > 0
        assert trends[0].direction == TrendDirection.INCREASING

    def test_decreasing_trend(self):
        """Test decreasing trend detection"""
        analyzer = TrendAnalyzer()

        # Add decreasing data
        for i in range(10):
            analyzer.add_data_point("test_metric", 100 - i * 5)

        trends = analyzer.analyze_trends()

        assert trends[0].direction == TrendDirection.DECREASING

    def test_stable_trend(self):
        """Test stable trend detection"""
        analyzer = TrendAnalyzer()

        # Add stable data
        for i in range(10):
            analyzer.add_data_point("test_metric", 50 + (i % 2))

        trends = analyzer.analyze_trends()

        # Should detect as stable (small variation)
        assert len(trends) > 0

    def test_predict_next(self):
        """Test prediction"""
        import time
        analyzer = TrendAnalyzer()

        # Add trend data with delays to create time spread
        for i in range(10):
            analyzer.add_data_point("test_metric", 10 + i * 2)
            if i < 9:  # Don't sleep after last one
                time.sleep(0.001)  # Small delay

        prediction = analyzer.predict_next("test_metric", horizon=3)

        # Should return prediction with enough time-separated points
        assert prediction is not None
        assert "predicted_values" in prediction
        assert len(prediction["predicted_values"]) == 3

    def test_get_all_metrics(self):
        """Test getting all tracked metrics"""
        analyzer = TrendAnalyzer()

        analyzer.add_data_point("metric1", 10)
        analyzer.add_data_point("metric2", 20)

        metrics = analyzer.get_all_metrics()

        assert len(metrics) == 2
        assert "metric1" in metrics
        assert "metric2" in metrics


# ================================================================
# Reporting Agent Tests
# ================================================================

class TestReportingAgent:
    """Test reporting agent"""

    def test_initialization(self):
        """Test agent initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ReportingAgent(Path(tmpdir))

            assert agent.runtime is not None
            assert agent.report_generator is not None

    def test_generate_report(self):
        """Test report generation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ReportingAgent(Path(tmpdir))
            data = self._create_test_data()

            results = agent.generate_report(data, formats=[ReportFormat.MARKDOWN])

            assert len(results) > 0
            assert results[0].success

    def test_generate_multiple_formats(self):
        """Test generating multiple formats"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ReportingAgent(Path(tmpdir))
            data = self._create_test_data()

            results = agent.generate_report(
                data,
                formats=[ReportFormat.MARKDOWN, ReportFormat.JSON]
            )

            assert len(results) == 2
            assert all(r.success for r in results)

    def test_get_insights(self):
        """Test getting insights"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ReportingAgent(Path(tmpdir))
            data = self._create_test_data()

            insights = agent.get_insights(data)

            assert isinstance(insights, list)

    def test_get_trends(self):
        """Test getting trends"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ReportingAgent(Path(tmpdir))

            # Add some trend data
            for i in range(10):
                data = self._create_test_data()
                agent.generate_report(data)

            trends = agent.get_trends()

            assert isinstance(trends, list)

    def test_predict_metrics(self):
        """Test metric prediction"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ReportingAgent(Path(tmpdir))

            # Add trend data
            for i in range(10):
                data = self._create_test_data()
                agent.generate_report(data)

            predictions = agent.predict_metrics(["bugs_found"], horizon=3)

            assert isinstance(predictions, dict)

    def test_get_summary(self):
        """Test getting summary"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ReportingAgent(Path(tmpdir))
            data = self._create_test_data()

            agent.generate_report(data)

            summary = agent.get_summary()

            assert "Latest Report Summary" in summary

    def test_get_statistics(self):
        """Test getting statistics"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ReportingAgent(Path(tmpdir))

            stats = agent.get_statistics()

            assert "agent_stats" in stats
            assert "insight_stats" in stats
            assert "trend_stats" in stats

    def _create_test_data(self) -> ReportData:
        """Create test report data"""
        return ReportData(
            total_tests=100,
            passed_tests=90,
            failed_tests=10,
            test_duration=45.0,
            bugs_found=[
                {"category": "validation", "severity": "medium", "pattern_name": "Bug 1"},
            ] * 5,
            bug_categories={"validation": 5},
            coverage_percentage=80.0,
            target_system="TestSystem",
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
