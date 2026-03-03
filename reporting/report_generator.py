"""
Report Generator

Generates reports in multiple formats with intelligent content selection.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import time
from datetime import datetime
from pathlib import Path


class ReportFormat(Enum):
    """Report output formats"""
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    TEXT = "text"
    PDF = "pdf"  # Stub for future implementation


class ReportSection(Enum):
    """Report sections"""
    SUMMARY = "summary"
    TEST_RESULTS = "test_results"
    BUGS_FOUND = "bugs_found"
    ANOMALIES = "anomalies"
    RACE_CONDITIONS = "race_conditions"
    SECURITY_ISSUES = "security_issues"
    TRENDS = "trends"
    INSIGHTS = "insights"
    RECOMMENDATIONS = "recommendations"
    METRICS = "metrics"
    COVERAGE = "coverage"


@dataclass
class ReportConfig:
    """Configuration for report generation"""
    title: str = "Bug Mining Report"
    format: ReportFormat = ReportFormat.MARKDOWN
    sections: List[ReportSection] = field(default_factory=lambda: [
        ReportSection.SUMMARY,
        ReportSection.TEST_RESULTS,
        ReportSection.BUGS_FOUND,
        ReportSection.ANOMALIES,
        ReportSection.RECOMMENDATIONS,
    ])
    include_charts: bool = True
    include_timestamps: bool = True
    include_raw_data: bool = False
    max_raw_items: int = 100


@dataclass
class ReportData:
    """Data for report generation"""
    # Test results
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    test_duration: float = 0.0

    # Bugs
    bugs_found: List[Dict] = field(default_factory=list)
    bug_categories: Dict[str, int] = field(default_factory=dict)

    # Anomalies
    anomalies_detected: List[Dict] = field(default_factory=list)
    anomaly_count: int = 0

    # Race conditions
    race_conditions: List[Dict] = field(default_factory=list)
    race_count: int = 0

    # Security issues
    security_vulnerabilities: List[Dict] = field(default_factory=list)
    vulnerability_count: int = 0

    # Coverage
    coverage_percentage: float = 0.0
    coverage_details: Dict = field(default_factory=dict)

    # Trends
    trend_data: List[Dict] = field(default_factory=list)

    # Insights
    insights: List[Dict] = field(default_factory=list)

    # Recommendations
    recommendations: List[Dict] = field(default_factory=list)

    # Metadata
    start_time: float = field(default_factory=time.time)
    end_time: float = field(default_factory=time.time)
    target_system: str = ""
    test_config: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "test_duration": self.test_duration,
            "bugs_found": self.bugs_found[:100],  # Limit size
            "bug_categories": self.bug_categories,
            "anomalies_detected": self.anomalies_detected[:100],
            "anomaly_count": self.anomaly_count,
            "race_conditions": self.race_conditions[:100],
            "race_count": self.race_count,
            "security_vulnerabilities": self.security_vulnerabilities[:100],
            "vulnerability_count": self.vulnerability_count,
            "coverage_percentage": self.coverage_percentage,
            "coverage_details": self.coverage_details,
            "trend_data": self.trend_data,
            "insights": self.insights,
            "recommendations": self.recommendations,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "target_system": self.target_system,
            "test_config": self.test_config,
        }


class ReportGenerator:
    """
    Report Generator

    Generates reports in multiple formats.
    """

    def __init__(self, config: Optional[ReportConfig] = None):
        """
        Initialize report generator

        Args:
            config: Report configuration
        """
        self.config = config or ReportConfig()

    def generate(self, data: ReportData,
                output_path: Optional[Path] = None) -> str:
        """
        Generate a report

        Args:
            data: Report data
            output_path: Output file path

        Returns:
            Generated report content
        """
        if self.config.format == ReportFormat.JSON:
            content = self._generate_json(data)
        elif self.config.format == ReportFormat.HTML:
            content = self._generate_html(data)
        elif self.config.format == ReportFormat.MARKDOWN:
            content = self._generate_markdown(data)
        elif self.config.format == ReportFormat.TEXT:
            content = self._generate_text(data)
        else:
            content = self._generate_markdown(data)  # Default

        # Save to file if path provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

        return content

    def _generate_json(self, data: ReportData) -> str:
        """Generate JSON report"""
        report = {
            "title": self.config.title,
            "generated_at": datetime.now().isoformat(),
            "format": "json",
            "data": data.to_dict(),
        }

        return json.dumps(report, indent=2, ensure_ascii=False)

    def _generate_html(self, data: ReportData) -> str:
        """Generate HTML report"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{self.config.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }}
        .metric {{ background: #f5f5f5; padding: 20px; border-radius: 8px; text-align: center; }}
        .metric-value {{ font-size: 32px; font-weight: bold; color: #007bff; }}
        .metric-label {{ color: #666; font-size: 14px; }}
        .bug {{ background: #ffebee; padding: 10px; margin: 5px 0; border-left: 4px solid #f44336; }}
        .anomaly {{ background: #fff3e0; padding: 10px; margin: 5px 0; border-left: 4px solid #ff9800; }}
        .recommendation {{ background: #e8f5e9; padding: 10px; margin: 5px 0; border-left: 4px solid #4caf50; }}
        .pass {{ color: #4caf50; font-weight: bold; }}
        .fail {{ color: #f44336; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>{self.config.title}</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <h2>Summary</h2>
    <div class="summary">
        <div class="metric">
            <div class="metric-value">{data.total_tests}</div>
            <div class="metric-label">Total Tests</div>
        </div>
        <div class="metric">
            <div class="metric-value {'pass' if data.passed_tests == data.total_tests else 'fail'}">{data.passed_tests}</div>
            <div class="metric-label">Passed</div>
        </div>
        <div class="metric">
            <div class="metric-value">{data.bugs_found and len(data.bugs_found) or 0}</div>
            <div class="metric-label">Bugs Found</div>
        </div>
        <div class="metric">
            <div class="metric-value">{data.coverage_percentage:.1f}%</div>
            <div class="metric-label">Coverage</div>
        </div>
    </div>

    <h2>Bugs Found</h2>
    """

        for bug in data.bugs_found[:20]:
            html += f"""
    <div class="bug">
        <strong>{bug.get('pattern_name', 'Unknown')}</strong> ({bug.get('severity', 'medium').upper()})
        <p>{bug.get('description', '')}</p>
        <p><em>Category: {bug.get('category', 'unknown')}</em></p>
    </div>
    """

        html += """
    <h2>Recommendations</h2>
    """

        for rec in data.recommendations[:10]:
            html += f"""
    <div class="recommendation">
        <strong>{rec.get('title', 'Recommendation')}</strong>
        <p>{rec.get('description', '')}</p>
    </div>
    """

        html += """
</body>
</html>
"""
        return html

    def _generate_markdown(self, data: ReportData) -> str:
        """Generate Markdown report"""
        md = f"""# {self.config.title}

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Target System**: {data.target_system or 'N/A'}

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {data.total_tests} |
| Passed | {data.passed_tests} |
| Failed | {data.failed_tests} |
| Pass Rate | {(data.passed_tests / data.total_tests * 100) if data.total_tests > 0 else 0:.1f}% |
| Duration | {data.test_duration:.2f}s |
| Bugs Found | {len(data.bugs_found)} |
| Anomalies | {data.anomaly_count} |
| Race Conditions | {data.race_count} |
| Security Issues | {data.vulnerability_count} |
| Coverage | {data.coverage_percentage:.1f}% |

"""

        # Bugs section
        if data.bugs_found:
            md += f"## Bugs Found ({len(data.bugs_found)})\n\n"
            for bug in data.bugs_found[:20]:
                severity_emoji = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(bug.get('severity', 'low'), "⚪")

                md += f"""### {severity_emoji} {bug.get('pattern_name', 'Unknown Bug')}
- **Category**: {bug.get('category', 'unknown')}
- **Severity**: {bug.get('severity', 'low').upper()}
- **Description**: {bug.get('description', 'No description')}
- **Root Cause**: {bug.get('root_cause', 'Unknown')}

"""

        # Anomalies section
        if data.anomalies_detected:
            md += f"## Anomalies Detected ({data.anomaly_count})\n\n"
            for anomaly in data.anomalies_detected[:10]:
                md += f"- **{anomaly.get('anomaly_type', 'unknown')}**: {anomaly.get('description', '')}\n"

            md += "\n"

        # Race conditions section
        if data.race_conditions:
            md += f"## Race Conditions ({data.race_count})\n\n"
            for race in data.race_conditions[:10]:
                md += f"- **{race.get('race_type', 'unknown')}**: {race.get('description', '')}\n"

            md += "\n"

        # Security issues section
        if data.security_vulnerabilities:
            md += f"## Security Issues ({data.vulnerability_count})\n\n"
            for vuln in data.security_vulnerabilities[:10]:
                md += f"- **{vuln.get('vulnerability_type', 'unknown')}**: {vuln.get('description', '')}\n"

            md += "\n"

        # Insights section
        if data.insights:
            md += "## Key Insights\n\n"
            for insight in data.insights[:10]:
                md += f"### {insight.get('title', 'Insight')}\n"
                md += f"{insight.get('description', '')}\n\n"

        # Recommendations section
        if data.recommendations:
            md += "## Recommendations\n\n"
            for rec in data.recommendations[:10]:
                md += f"### {rec.get('title', 'Recommendation')}\n"
                md += f"{rec.get('description', '')}\n"
                if rec.get('priority'):
                    md += f"**Priority**: {rec.get('priority')}\n"
                md += "\n"

        md += "---\n\n*Report generated by Semantic Bug Mining Framework*"

        return md

    def _generate_text(self, data: ReportData) -> str:
        """Generate plain text report"""
        text = f"""{'='*60}
{self.config.title}
{'='*60}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Target System: {data.target_system or 'N/A'}

SUMMARY
-------
Total Tests:    {data.total_tests}
Passed:         {data.passed_tests}
Failed:         {data.failed_tests}
Pass Rate:      {(data.passed_tests / data.total_tests * 100) if data.total_tests > 0 else 0:.1f}%
Duration:       {data.test_duration:.2f}s

Issues Found:
  Bugs:             {len(data.bugs_found)}
  Anomalies:        {data.anomaly_count}
  Race Conditions:  {data.race_count}
  Security Issues:  {data.vulnerability_count}
  Coverage:         {data.coverage_percentage:.1f}%

"""

        if data.bugs_found:
            text += f"\nBUGS FOUND ({len(data.bugs_found)})\n"
            text += "-"*40 + "\n"
            for bug in data.bugs_found[:20]:
                text += f"\n[{bug.get('severity', 'low').upper()}] {bug.get('pattern_name', 'Unknown')}\n"
                text += f"  Category: {bug.get('category', 'unknown')}\n"
                text += f"  {bug.get('description', 'No description')[:80]}\n"

        if data.recommendations:
            text += f"\n\nRECOMMENDATIONS\n"
            text += "-"*40 + "\n"
            for i, rec in enumerate(data.recommendations[:10], 1):
                text += f"\n{i}. {rec.get('title', 'Recommendation')}\n"
                text += f"   {rec.get('description', '')}\n"

        text += f"\n\n{'='*60}\n"
        text += "End of Report\n"
        text += f"{'='*60}\n"

        return text

    def generate_summary(self, data: ReportData) -> str:
        """Generate a quick summary"""
        return f"""
Test Summary:
  Total: {data.total_tests}
  Passed: {data.passed_tests}
  Failed: {data.failed_tests}
  Bugs: {len(data.bugs_found)}
  Anomalies: {data.anomaly_count}
  Race Conditions: {data.race_count}
  Security Issues: {data.vulnerability_count}
  Coverage: {data.coverage_percentage:.1f}%
  Duration: {data.test_duration:.2f}s
""".strip()


__all__ = [
    "ReportFormat",
    "ReportSection",
    "ReportConfig",
    "ReportData",
    "ReportGenerator",
]
