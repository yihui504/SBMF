"""
Oracle Report Generator

生成 Oracle 检查报告，支持多种输出格式。
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

from oracle.base import OracleResult


# ================================================================
# Report Format Enum
# ================================================================

class ReportFormat(Enum):
    """报告格式"""
    JSON = "json"
    HTML = "html"
    TEXT = "text"
    # PDF = "pdf"  # TODO: Future implementation


# ================================================================
# Oracle Report Data Class
# ================================================================

@dataclass
class OracleReport:
    """Oracle 检查报告

    Attributes:
        total_oracles: Oracle 总数
        passed_count: 通过数量
        failed_count: 失败数量
        skipped_count: 跳过数量
        results: Oracle 结果列表
        summary: 报告摘要
        generated_at: 生成时间
        duration_seconds: 总耗时（秒）
    """
    total_oracles: int
    passed_count: int
    failed_count: int
    skipped_count: int
    results: List[OracleResult]
    summary: str
    generated_at: datetime = field(default_factory=datetime.now)
    duration_seconds: float = 0.0

    @property
    def pass_rate(self) -> float:
        """通过率

        Returns:
            float: 通过率 (0.0 - 1.0)
        """
        if self.total_oracles == 0:
            return 1.0
        return self.passed_count / self.total_oracles

    @property
    def has_failures(self) -> bool:
        """是否有失败"""
        return self.failed_count > 0

    @property
    def failed_oracles(self) -> List[OracleResult]:
        """获取失败的 Oracle 结果"""
        return [r for r in self.results if not r.passed]

    @property
    def passed_oracles(self) -> List[OracleResult]:
        """获取通过的 Oracle 结果"""
        return [r for r in self.results if r.passed]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            Dict[str, Any]: 报告字典
        """
        return {
            "summary": {
                "total_oracles": self.total_oracles,
                "passed_count": self.passed_count,
                "failed_count": self.failed_count,
                "skipped_count": self.skipped_count,
                "pass_rate": round(self.pass_rate * 100, 2),
                "has_failures": self.has_failures,
                "summary_text": self.summary,
            },
            "generated_at": self.generated_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "results": [r.to_dict() for r in self.results]
        }


# ================================================================
# Oracle Reporter Class
# ================================================================

class OracleReporter:
    """Oracle 报告生成器

    职责：
    - 聚合 Oracle 检查结果
    - 生成统计信息
    - 输出多种格式的报告

    Example:
        >>> reporter = OracleReporter(oracles)
        >>> results = [oracle1.check(test_case, result), ...]
        >>> report = reporter.generate_report(results)
        >>> print(report.summary)
        >>> json_output = reporter.to_json(report)
        >>> html_output = reporter.to_html(report)
    """

    def __init__(self, oracles: Optional[List] = None):
        """初始化 Oracle Reporter

        Args:
            oracles: Oracle 检查器列表（可选，用于元数据）
        """
        self.oracles = oracles or []
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None

    def start_timer(self):
        """开始计时"""
        self._start_time = datetime.now()

    def stop_timer(self) -> float:
        """停止计时并返回耗时

        Returns:
            float: 耗时（秒）
        """
        if self._start_time is None:
            return 0.0

        self._end_time = datetime.now()
        duration = (self._end_time - self._start_time).total_seconds()
        return duration

    def generate_report(self, results: List[OracleResult]) -> OracleReport:
        """生成 Oracle 报告

        Args:
            results: Oracle 检查结果列表

        Returns:
            OracleReport: Oracle 报告
        """
        duration = self.stop_timer()

        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)
        total = len(results)

        summary = self._generate_summary(results, passed, total)

        return OracleReport(
            total_oracles=total,
            passed_count=passed,
            failed_count=failed,
            skipped_count=0,  # TODO: Implement skip tracking
            results=results,
            summary=summary,
            duration_seconds=duration
        )

    def aggregate_results(self, test_results: List[List[OracleResult]]) -> OracleReport:
        """聚合多个测试的 Oracle 结果

        Args:
            test_results: 每个测试的 Oracle 结果列表的列表

        Returns:
            OracleReport: 聚合后的报告
        """
        # Flatten all results
        all_results: List[OracleResult] = []
        for results in test_results:
            all_results.extend(results)

        return self.generate_report(all_results)

    def _generate_summary(
        self,
        results: List[OracleResult],
        passed_count: int,
        total_count: int
    ) -> str:
        """生成报告摘要

        Args:
            results: Oracle 结果列表
            passed_count: 通过数量
            total_count: 总数量

        Returns:
            str: 摘要文本
        """
        if total_count == 0:
            return "No Oracle checks performed"

        failed_oracles = [r for r in results if not r.passed]

        if passed_count == total_count:
            return f"All {total_count} Oracle checks passed"

        parts = [
            f"{passed_count}/{total_count} Oracle checks passed",
            f"{len(failed_oracles)} failed"
        ]

        if failed_oracles:
            failed_names = [r.oracle_id for r in failed_oracles]
            parts.append(f"(Failed: {', '.join(failed_names)})")

        return ", ".join(parts)

    # ================================================================
    # Output Format Methods
    # ================================================================

    def to_json(self, report: OracleReport, indent: int = 2) -> str:
        """生成 JSON 格式报告

        Args:
            report: Oracle 报告
            indent: JSON 缩进空格数

        Returns:
            str: JSON 格式报告

        Example:
            >>> json_str = reporter.to_json(report)
            >>> print(json_str)
        """
        return json.dumps(report.to_dict(), indent=indent, ensure_ascii=False)

    def to_html(self, report: OracleReport, title: str = "Oracle Report") -> str:
        """生成 HTML 格式报告

        Args:
            report: Oracle 报告
            title: 报告标题

        Returns:
            str: HTML 格式报告

        Example:
            >>> html_str = reporter.to_html(report)
            >>> with open("report.html", "w") as f:
            ...     f.write(html_str)
        """
        html_parts = []

        # HTML header
        html_parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        .summary {{
            background-color: #f8f9fa;
            border-left: 4px solid #007bff;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .summary.passed {{
            border-left-color: #28a745;
        }}
        .summary.failed {{
            border-left-color: #dc3545;
        }}
        .stats {{
            display: flex;
            gap: 20px;
            margin: 20px 0;
        }}
        .stat {{
            flex: 1;
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 32px;
            font-weight: bold;
            color: #007bff;
        }}
        .stat-label {{
            color: #6c757d;
            font-size: 14px;
            margin-top: 5px;
        }}
        .results {{
            margin-top: 30px;
        }}
        .result-item {{
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 10px;
        }}
        .result-item.passed {{
            border-left: 4px solid #28a745;
        }}
        .result-item.failed {{
            border-left: 4px solid #dc3545;
        }}
        .oracle-id {{
            font-weight: bold;
            color: #495057;
        }}
        .status {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            margin-left: 10px;
        }}
        .status.passed {{
            background-color: #d4edda;
            color: #155724;
        }}
        .status.failed {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        .details {{
            margin-top: 10px;
            color: #6c757d;
        }}
        .evidence {{
            margin-top: 10px;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
        }}
        .timestamp {{
            color: #6c757d;
            font-size: 12px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
""")

        # Summary section
        summary_class = "passed" if not report.has_failures else "failed"
        html_parts.append(f"""
        <div class="summary {summary_class}">
            <strong>Summary:</strong> {report.summary}
        </div>
""")

        # Stats section
        pass_rate = round(report.pass_rate * 100, 1)
        html_parts.append("""
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{}</div>
                <div class="stat-label">Total Checks</div>
            </div>
            <div class="stat">
                <div class="stat-value">{}</div>
                <div class="stat-label">Passed</div>
            </div>
            <div class="stat">
                <div class="stat-value">{}</div>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat">
                <div class="stat-value">{}%</div>
                <div class="stat-label">Pass Rate</div>
            </div>
        </div>
""".format(
            report.total_oracles,
            report.passed_count,
            report.failed_count,
            pass_rate
))

        # Results section
        html_parts.append("""
        <div class="results">
            <h2>Detailed Results</h2>
""")

        for result in report.results:
            status_class = "passed" if result.passed else "failed"
            status_text = "PASSED" if result.passed else "FAILED"

            html_parts.append(f"""
            <div class="result-item {status_class}">
                <div>
                    <span class="oracle-id">{result.oracle_id}</span>
                    <span class="status {status_class}">{status_text}</span>
                </div>
                <div class="details">{result.details}</div>
""")

            # Evidence section
            if result.evidence:
                html_parts.append(f"""
                <div class="evidence">Evidence: {json.dumps(result.evidence, indent=2)}</div>
""")

            # Violated slots
            if result.violated_slots:
                html_parts.append(f"""
                <div class="details">Violated slots: {', '.join(result.violated_slots)}</div>
""")

            html_parts.append("""
            </div>
""")

        # Footer
        html_parts.append("""
        </div>
        <div class="timestamp">
            Generated: {} | Duration: {:.2f}s
        </div>
    </div>
</body>
</html>
""".format(
            report.generated_at.strftime("%Y-%m-%d %H:%M:%S"),
            report.duration_seconds
))

        return "\n".join(html_parts)

    def to_text(self, report: OracleReport) -> str:
        """生成纯文本格式报告

        Args:
            report: Oracle 报告

        Returns:
            str: 纯文本格式报告

        Example:
            >>> text = reporter.to_text(report)
            >>> print(text)
        """
        lines = []

        lines.append("=" * 60)
        lines.append("ORACLE REPORT")
        lines.append("=" * 60)
        lines.append("")

        # Summary
        lines.append("Summary:")
        lines.append(f"  {report.summary}")
        lines.append("")

        # Stats
        lines.append("Statistics:")
        lines.append(f"  Total Oracle checks: {report.total_oracles}")
        lines.append(f"  Passed: {report.passed_count}")
        lines.append(f"  Failed: {report.failed_count}")
        lines.append(f"  Pass rate: {round(report.pass_rate * 100, 1)}%")
        lines.append("")

        # Detailed results
        lines.append("Detailed Results:")
        lines.append("-" * 60)

        for result in report.results:
            status = "PASSED" if result.passed else "FAILED"
            lines.append(f"\n[{status}] {result.oracle_id}")
            lines.append(f"  Details: {result.details}")

            if result.violated_slots:
                lines.append(f"  Violated slots: {', '.join(result.violated_slots)}")

            if result.evidence:
                lines.append(f"  Evidence: {result.evidence}")

        lines.append("")
        lines.append("-" * 60)
        lines.append(f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Duration: {report.duration_seconds:.2f}s")

        return "\n".join(lines)

    def save_report(
        self,
        report: OracleReport,
        file_path: str,
        format: ReportFormat = ReportFormat.JSON
    ) -> None:
        """保存报告到文件

        Args:
            report: Oracle 报告
            file_path: 文件路径
            format: 报告格式

        Raises:
            ValueError: 如果格式不支持

        Example:
            >>> reporter.save_report(report, "report.json", ReportFormat.JSON)
            >>> reporter.save_report(report, "report.html", ReportFormat.HTML)
        """
        if format == ReportFormat.JSON:
            content = self.to_json(report)
        elif format == ReportFormat.HTML:
            content = self.to_html(report)
        elif format == ReportFormat.TEXT:
            content = self.to_text(report)
        else:
            raise ValueError(f"Unsupported format: {format}")

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)


__all__ = [
    "ReportFormat",
    "OracleReport",
    "OracleReporter",
]
