"""
Security Tester

Tests for security vulnerabilities in concurrent operations.
"""
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import re


class VulnerabilityType(Enum):
    """Types of security vulnerabilities"""
    SQL_INJECTION = "sql_injection"
    COMMAND_INJECTION = "command_injection"
    UNVALIDATED_INPUT = "unvalidated_input"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    RACE_CONDITION = "race_condition"
    AUTHORIZATION_BYPASS = "auth_bypass"
    DATA_LEAK = "data_leak"
    DENIAL_OF_SERVICE = "dos"


@dataclass
class SecurityTest:
    """
    A security test case
    """
    test_id: str
    name: str
    vulnerability_type: VulnerabilityType
    description: str
    input_data: Dict[str, Any]
    expected_behavior: str  # blocked, sanitized, allowed
    severity: str = "medium"

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "test_id": self.test_id,
            "name": self.name,
            "vulnerability_type": self.vulnerability_type.value,
            "description": self.description,
            "input_data": self.input_data,
            "expected_behavior": self.expected_behavior,
            "severity": self.severity,
        }


@dataclass
class SecurityTestResult:
    """
    Result of a security test
    """
    test_id: str
    vulnerable: bool
    severity: str
    description: str
    actual_behavior: str
    recommendation: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "test_id": self.test_id,
            "vulnerable": self.vulnerable,
            "severity": self.severity,
            "description": self.description,
            "actual_behavior": self.actual_behavior,
            "recommendation": self.recommendation,
            "evidence": self.evidence,
        }


class SecurityTester:
    """
    Security Tester

    Tests for security vulnerabilities in database operations.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize security tester

        Args:
            config: Configuration options
        """
        self.config = config or {}
        self._test_count = 0

    def generate_injection_tests(self, operation: str,
                                  input_fields: List[str]) -> List[SecurityTest]:
        """
        Generate injection attack tests

        Args:
            operation: Operation being tested
            input_fields: List of input field names

        Returns:
            List of security tests
        """
        tests = []

        # SQL injection payloads
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "1' UNION SELECT * FROM passwords--",
            "admin'--",
            "admin' #",
            "1' AND 1=1--",
        ]

        for payload in sql_payloads:
            for field in input_fields:
                test = SecurityTest(
                    test_id=self._generate_test_id(),
                    name=f"SQL Injection: {field}",
                    vulnerability_type=VulnerabilityType.SQL_INJECTION,
                    description=f"Test SQL injection via {field}",
                    input_data={field: payload},
                    expected_behavior="blocked",
                    severity="critical",
                )
                tests.append(test)

        # Command injection payloads
        cmd_payloads = [
            "; cat /etc/passwd",
            "| ls -la",
            "&& whoami",
            "`id`",
            "$(whoami)",
        ]

        for payload in cmd_payloads:
            for field in input_fields:
                test = SecurityTest(
                    test_id=self._generate_test_id(),
                    name=f"Command Injection: {field}",
                    vulnerability_type=VulnerabilityType.COMMAND_INJECTION,
                    description=f"Test command injection via {field}",
                    input_data={field: payload},
                    expected_behavior="blocked",
                    severity="critical",
                )
                tests.append(test)

        return tests

    def generate_input_validation_tests(self, operation: str,
                                         input_fields: List[str]) -> List[SecurityTest]:
        """
        Generate input validation tests

        Args:
            operation: Operation being tested
            input_fields: List of input field names

        Returns:
            List of security tests
        """
        tests = []

        # Boundary value overflow
        overflow_tests = [
            ("dimension", 999999999),
            ("limit", -1),
            ("offset", -1),
            ("batch_size", 9999999),
        ]

        for field, value in overflow_tests:
            if field in input_fields:
                test = SecurityTest(
                    test_id=self._generate_test_id(),
                    name=f"Integer Overflow: {field}",
                    vulnerability_type=VulnerabilityType.UNVALIDATED_INPUT,
                    description=f"Test integer overflow via {field}",
                    input_data={field: value},
                    expected_behavior="blocked",
                    severity="high",
                )
                tests.append(test)

        # String overflow
        for field in input_fields:
            if "name" in field.lower() or "id" in field.lower():
                test = SecurityTest(
                    test_id=self._generate_test_id(),
                    name=f"String Overflow: {field}",
                    vulnerability_type=VulnerabilityType.UNVALIDATED_INPUT,
                    description=f"Test buffer overflow via {field}",
                    input_data={field: "A" * 100000},
                    expected_behavior="blocked",
                    severity="high",
                )
                tests.append(test)

        # Special characters
        special_char_payloads = [
            "../../../etc/passwd",
            "\x00\x01\x02\x03",
            "<script>alert('xss')</script>",
            "{{7*7}}",  # Template injection
            "${7*7}",   # Expression injection
        ]

        for payload in special_char_payloads:
            for field in input_fields:
                test = SecurityTest(
                    test_id=self._generate_test_id(),
                    name=f"Special Characters: {field}",
                    vulnerability_type=VulnerabilityType.UNVALIDATED_INPUT,
                    description=f"Test special character handling in {field}",
                    input_data={field: payload},
                    expected_behavior="sanitized",
                    severity="medium",
                )
                tests.append(test)

        return tests

    def generate_dos_tests(self, operation: str,
                           input_fields: List[str]) -> List[SecurityTest]:
        """
        Generate denial-of-service tests

        Args:
            operation: Operation being tested
            input_fields: List of input field names

        Returns:
            List of security tests
        """
        tests = []

        # Large query parameters
        dos_tests = [
            ("top_k", 999999999),
            ("dimension", 999999999),
            ("count", 999999999),
        ]

        for field, value in dos_tests:
            if field in input_fields:
                test = SecurityTest(
                    test_id=self._generate_test_id(),
                    name=f"DoS: Large {field}",
                    vulnerability_type=VulnerabilityType.DENIAL_OF_SERVICE,
                    description=f"Test DoS via large {field}",
                    input_data={field: value},
                    expected_behavior="blocked",
                    severity="high",
                )
                tests.append(test)

        # Nested/complex queries
        if "filter" in input_fields or "query" in input_fields:
            test = SecurityTest(
                test_id=self._generate_test_id(),
                name="DoS: Complex Query",
                vulnerability_type=VulnerabilityType.DENIAL_OF_SERVICE,
                description="Test DoS via complex nested query",
                input_data={
                    "filter": " AND ".join([f"field{i}=value{i}" for i in range(1000)])
                },
                expected_behavior="blocked",
                severity="high",
            )
            tests.append(test)

        return tests

    def generate_authorization_tests(self, operation: str,
                                      resources: List[str]) -> List[SecurityTest]:
        """
        Generate authorization bypass tests

        Args:
            operation: Operation being tested
            resources: List of resources

        Returns:
            List of security tests
        """
        tests = []

        # Try accessing other users' resources
        for resource in resources[:3]:
            test = SecurityTest(
                test_id=self._generate_test_id(),
                name=f"Auth Bypass: {resource}",
                vulnerability_type=VulnerabilityType.AUTHORIZATION_BYPASS,
                description=f"Test unauthorized access to {resource}",
                input_data={"collection": resource, "user_id": "other_user"},
                expected_behavior="blocked",
                severity="critical",
            )
            tests.append(test)

        # Privilege escalation
        test = SecurityTest(
            test_id=self._generate_test_id(),
            name="Privilege Escalation",
            vulnerability_type=VulnerabilityType.AUTHORIZATION_BYPASS,
            description="Test privilege escalation via role modification",
            input_data={"role": "admin", "action": "delete"},
            expected_behavior="blocked",
            severity="critical",
        )
        tests.append(test)

        return tests

    def analyze_response_for_vulnerabilities(self,
                                              test: SecurityTest,
                                              response: Dict) -> SecurityTestResult:
        """
        Analyze a response for security vulnerabilities

        Args:
            test: The security test that was run
            response: Response from the system

        Returns:
            Security test result
        """
        vulnerable = False
        severity = test.severity
        actual_behavior = "allowed"
        recommendation = "No issues found"

        # Check if request was blocked
        status = response.get("status", "")
        error = response.get("error", "")
        data = response.get("data", {})

        if status == "error" or status == "blocked":
            actual_behavior = "blocked"
            vulnerable = False
            recommendation = "Input properly blocked"
        elif "invalid" in error.lower() or "not allowed" in error.lower():
            actual_behavior = "blocked"
            vulnerable = False
            recommendation = "Input properly rejected"
        else:
            # Request was allowed - check if it should have been
            if test.expected_behavior == "blocked":
                vulnerable = True
                actual_behavior = "allowed (should be blocked)"
                recommendation = self._get_mitigation_recommendation(test.vulnerability_type)

            # Check for data leakage in response
            if self._check_data_leak(data):
                vulnerable = True
                severity = "high"
                actual_behavior += " + data leak"
                recommendation = "Block input and sanitize responses"

        return SecurityTestResult(
            test_id=test.test_id,
            vulnerable=vulnerable,
            severity=severity,
            description=test.description,
            actual_behavior=actual_behavior,
            recommendation=recommendation,
            evidence={
                "response_status": status,
                "response_error": error,
            }
        )

    def _check_data_leak(self, data: Any) -> bool:
        """Check if response contains sensitive data"""
        if not isinstance(data, dict):
            return False

        sensitive_patterns = [
            "password", "passwd", "secret", "token", "api_key",
            "private_key", "credit_card", "ssn", "social_security"
        ]

        data_str = str(data).lower()

        for pattern in sensitive_patterns:
            if pattern in data_str:
                return True

        return False

    def _get_mitigation_recommendation(self,
                                       vuln_type: VulnerabilityType) -> str:
        """Get mitigation recommendation for vulnerability type"""
        recommendations = {
            VulnerabilityType.SQL_INJECTION: "Use parameterized queries and input validation",
            VulnerabilityType.COMMAND_INJECTION: "Avoid shell commands, use whitelisting",
            VulnerabilityType.UNVALIDATED_INPUT: "Implement strict input validation and sanitization",
            VulnerabilityType.DENIAL_OF_SERVICE: "Add rate limiting and resource quotas",
            VulnerabilityType.AUTHORIZATION_BYPASS: "Implement proper access control checks",
            VulnerabilityType.DATA_LEAK: "Filter sensitive data from responses",
            VulnerabilityType.RACE_CONDITION: "Use proper locking and atomic operations",
        }

        return recommendations.get(vuln_type, "Review and patch security vulnerability")

    def generate_all_tests(self, operation: str,
                           input_fields: List[str],
                           resources: List[str]) -> List[SecurityTest]:
        """
        Generate all security tests

        Args:
            operation: Operation being tested
            input_fields: List of input field names
            resources: List of resources

        Returns:
            List of all security tests
        """
        all_tests = []

        all_tests.extend(self.generate_injection_tests(operation, input_fields))
        all_tests.extend(self.generate_input_validation_tests(operation, input_fields))
        all_tests.extend(self.generate_dos_tests(operation, input_fields))
        all_tests.extend(self.generate_authorization_tests(operation, resources))

        return all_tests

    def get_stats(self) -> Dict:
        """Get tester statistics"""
        return {
            "total_tests_generated": self._test_count,
        }

    def _generate_test_id(self) -> str:
        """Generate a unique test ID"""
        self._test_count += 1
        return f"SEC_TEST_{self._test_count:04d}"


__all__ = [
    "VulnerabilityType",
    "SecurityTest",
    "SecurityTestResult",
    "SecurityTester",
]
