"""
Fix Recommendation Generator and Validator

Generates and validates fix suggestions for bugs.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import ast
import subprocess


@dataclass
class FixValidationResult:
    """Result of fix validation"""
    is_safe: bool
    has_tests: bool
    syntax_valid: bool
    issues: List[str]
    score: float  # 0-1


@dataclass
class FixRecommendation:
    """A fix recommendation with full details"""
    bug_pattern_id: str
    bug_name: str
    description: str
    severity: str

    # The fix
    fix_type: str  # validation, code_change, config_update, etc.
    fix_description: str
    code_fix: Optional[str] = None

    # Validation
    is_safe: bool = True
    estimated_effort: str = "medium"

    # Execution guidance
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    steps: List[str] = None

    # Testing
    test_to_verify: Optional[str] = None
    expected_result: Optional[str] = None

    def __post_init__(self):
        if self.steps is None:
            self.steps = []

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "bug_pattern_id": self.bug_pattern_id,
            "bug_name": self.bug_name,
            "description": self.description,
            "severity": self.severity,
            "fix_type": self.fix_type,
            "fix_description": self.fix_description,
            "code_fix": self.code_fix,
            "is_safe": self.is_safe,
            "estimated_effort": self.estimated_effort,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "steps": self.steps,
            "test_to_verify": self.test_to_verify,
            "expected_result": self.expected_result,
        }


class FixValidator:
    """
    Fix Validator

    Validates that fix code is safe, syntactically correct,
    and follows best practices.
    """

    def validate(self, code: str, pattern_id: str) -> FixValidationResult:
        """
        Validate fix code

        Args:
            code: Code to validate
            pattern_id: Associated bug pattern

        Returns:
            FixValidationResult with validation findings
        """
        issues = []
        score = 1.0
        has_tests = False

        # Syntax validation
        syntax_valid = self._check_syntax(code, issues)
        if not syntax_valid:
            score -= 0.5

        # Safety checks
        is_safe = self._check_safety(code, issues)

        # Test presence (simplified check)
        has_tests = self._has_test_code(code)

        # Additional quality checks
        self._check_code_quality(code, issues)

        # Calculate final score
        if issues:
            score -= min(0.1 * len(issues), 0.4)

        return FixValidationResult(
            is_safe=is_safe,
            has_tests=has_tests,
            syntax_valid=syntax_valid,
            issues=issues,
            score=max(0.0, score)
        )

    def _check_syntax(self, code: str, issues: List[str]) -> bool:
        """Check if code is syntactically valid"""
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            issues.append(f"Syntax error: {e}")
            return False

    def _check_safety(self, code: str, issues: List[str]) -> bool:
        """Check if code follows safety practices"""
        is_safe = True

        # Check for dangerous operations
        dangerous_patterns = [
            (r'\beval\s*\(', "Avoid using eval() - security risk"),
            (r'\bexec\s*\(', "Avoid using exec() - security risk"),
            (r'pass\s*$', "Empty except block - may hide errors"),
            (r'except\s*:', "Bare except - catches all exceptions including SystemExit"),
        ]

        for pattern, message in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(f"Safety: {message}")
                is_safe = False

        # Check for SQL injection patterns
        sql_injection_patterns = [
            (r'f"[^"]*\{.*?\}[^"]*"\s*\)', "Potential SQL injection in f-string"),
            (r'".*\+.*\*', "Potential SQL injection with string concatenation"),
        ]

        for pattern, message in sql_injection_patterns:
            if re.search(pattern, code):
                issues.append(f"Security: {message}")
                is_safe = False

        return is_safe

    def _has_test_code(self, code: str) -> bool:
        """Check if code includes tests"""
        test_indicators = ['test_', 'assert', 'unittest.', 'pytest.']
        return any(indicator in code for indicator in test_indicators)

    def _check_code_quality(self, code: str, issues: List[str]) -> None:
        """Check code quality"""
        # Check for very long lines
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                issues.append(f"Line {i}: Too long ({len(line)} chars, max 120)")

        # Check for multiple blank lines
        blank_count = 0
        for line in lines:
            if not line.strip():
                blank_count += 1
                if blank_count > 2:
                    issues.append("Multiple blank lines (use max 2)")
                    break
            else:
                blank_count = 0


import re

__all__ = [
    "FixValidationResult",
    "FixRecommendation",
    "FixValidator",
]
