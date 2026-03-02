"""
Tests for Three-Valued Logic System

Tests the three-valued logic (True, False, None) used for rule evaluation
in the Semantic Bug Mining Framework.
"""

import pytest
from typing import List, Optional

from core.three_valued_logic import ThreeValuedLogic


class TestComputeOverallPassed:
    """Tests for compute_overall_passed method"""

    def test_all_true_returns_true(self):
        """All True values should return True"""
        result = ThreeValuedLogic.compute_overall_passed([True, True, True])
        assert result is True

    def test_single_true_returns_true(self):
        """Single True value should return True"""
        result = ThreeValuedLogic.compute_overall_passed([True])
        assert result is True

    def test_one_false_makes_false(self):
        """One False in any position should return False"""
        test_cases: List[List[Optional[bool]]] = [
            [True, False, True],
            [False, True, True],
            [True, True, False],
            [False],
        ]
        for case in test_cases:
            result = ThreeValuedLogic.compute_overall_passed(case)
            assert result is False, f"Failed for case: {case}"

    def test_true_and_none_returns_true(self):
        """Mix of True and None should return True"""
        test_cases: List[List[Optional[bool]]] = [
            [True, None],
            [True, None, None],
            [None, True],
            [None, True, None],
            [True, True, None],
        ]
        for case in test_cases:
            result = ThreeValuedLogic.compute_overall_passed(case)
            assert result is True, f"Failed for case: {case}"

    def test_all_none_returns_none(self):
        """All None values should return None"""
        test_cases: List[List[Optional[bool]]] = [
            [None],
            [None, None],
            [None, None, None],
        ]
        for case in test_cases:
            result = ThreeValuedLogic.compute_overall_passed(case)
            assert result is None, f"Failed for case: {case}"

    def test_empty_list_returns_none(self):
        """Empty list should return None"""
        result = ThreeValuedLogic.compute_overall_passed([])
        assert result is None

    def test_false_overrides_none(self):
        """False should override None"""
        test_cases: List[List[Optional[bool]]] = [
            [False, None],
            [None, False],
            [False, None, None],
        ]
        for case in test_cases:
            result = ThreeValuedLogic.compute_overall_passed(case)
            assert result is False, f"Failed for case: {case}"

    def test_complex_mixtures(self):
        """Test complex combinations of all three values"""
        # False overrides everything
        assert ThreeValuedLogic.compute_overall_passed([True, False, None]) is False
        assert ThreeValuedLogic.compute_overall_passed([False, True, None]) is False
        assert ThreeValuedLogic.compute_overall_passed([None, False, True]) is False

        # True overrides None
        assert ThreeValuedLogic.compute_overall_passed([True, True, None]) is True
        assert ThreeValuedLogic.compute_overall_passed([None, True, True]) is True

        # Only None results in None
        assert ThreeValuedLogic.compute_overall_passed([None, None, None]) is None


class TestAndOperator:
    """Tests for and_operator method"""

    def test_true_and_true(self):
        """True AND True = True"""
        assert ThreeValuedLogic.and_operator(True, True) is True

    def test_true_and_false(self):
        """True AND False = False"""
        assert ThreeValuedLogic.and_operator(True, False) is False

    def test_false_and_true(self):
        """False AND True = False"""
        assert ThreeValuedLogic.and_operator(False, True) is False

    def test_false_and_false(self):
        """False AND False = False"""
        assert ThreeValuedLogic.and_operator(False, False) is False

    def test_true_and_none(self):
        """True AND None = None"""
        assert ThreeValuedLogic.and_operator(True, None) is None

    def test_none_and_true(self):
        """None AND True = None"""
        assert ThreeValuedLogic.and_operator(None, True) is None

    def test_false_and_none(self):
        """False AND None = False"""
        assert ThreeValuedLogic.and_operator(False, None) is False

    def test_none_and_false(self):
        """None AND False = False"""
        assert ThreeValuedLogic.and_operator(None, False) is False

    def test_none_and_none(self):
        """None AND None = None"""
        assert ThreeValuedLogic.and_operator(None, None) is None


class TestOrOperator:
    """Tests for or_operator method"""

    def test_true_or_true(self):
        """True OR True = True"""
        assert ThreeValuedLogic.or_operator(True, True) is True

    def test_true_or_false(self):
        """True OR False = True"""
        assert ThreeValuedLogic.or_operator(True, False) is True

    def test_false_or_true(self):
        """False OR True = True"""
        assert ThreeValuedLogic.or_operator(False, True) is True

    def test_false_or_false(self):
        """False OR False = False"""
        assert ThreeValuedLogic.or_operator(False, False) is False

    def test_true_or_none(self):
        """True OR None = True"""
        assert ThreeValuedLogic.or_operator(True, None) is True

    def test_none_or_true(self):
        """None OR True = True"""
        assert ThreeValuedLogic.or_operator(None, True) is True

    def test_false_or_none(self):
        """False OR None = None"""
        assert ThreeValuedLogic.or_operator(False, None) is None

    def test_none_or_false(self):
        """None OR False = None"""
        assert ThreeValuedLogic.or_operator(None, False) is None

    def test_none_or_none(self):
        """None OR None = None"""
        assert ThreeValuedLogic.or_operator(None, None) is None


class TestNotOperator:
    """Tests for not_operator method"""

    def test_not_true(self):
        """NOT True = False"""
        assert ThreeValuedLogic.not_operator(True) is False

    def test_not_false(self):
        """NOT False = True"""
        assert ThreeValuedLogic.not_operator(False) is True

    def test_not_none(self):
        """NOT None = None"""
        assert ThreeValuedLogic.not_operator(None) is None


class TestOperatorCombinations:
    """Tests for combinations of operators"""

    def test_de_morgans_law_with_none(self):
        """Test De Morgan's laws with three-valued logic"""
        # NOT (A AND B) = (NOT A) OR (NOT B)
        assert ThreeValuedLogic.not_operator(
            ThreeValuedLogic.and_operator(True, None)
        ) == ThreeValuedLogic.or_operator(
            ThreeValuedLogic.not_operator(True),
            ThreeValuedLogic.not_operator(None)
        )

        # NOT (A OR B) = (NOT A) AND (NOT B)
        assert ThreeValuedLogic.not_operator(
            ThreeValuedLogic.or_operator(False, None)
        ) == ThreeValuedLogic.and_operator(
            ThreeValuedLogic.not_operator(False),
            ThreeValuedLogic.not_operator(None)
        )

    def test_associativity(self):
        """Test associativity of AND and OR"""
        # (A AND B) AND C = A AND (B AND C)
        result1 = ThreeValuedLogic.and_operator(
            ThreeValuedLogic.and_operator(True, None),
            False
        )
        result2 = ThreeValuedLogic.and_operator(
            True,
            ThreeValuedLogic.and_operator(None, False)
        )
        assert result1 == result2

        # (A OR B) OR C = A OR (B OR C)
        result1 = ThreeValuedLogic.or_operator(
            ThreeValuedLogic.or_operator(True, None),
            False
        )
        result2 = ThreeValuedLogic.or_operator(
            True,
            ThreeValuedLogic.or_operator(None, False)
        )
        assert result1 == result2


class TestTruthTables:
    """Comprehensive truth table tests"""

    def test_and_truth_table(self):
        """Test complete AND truth table"""
        truth_table = {
            (True, True): True,
            (True, False): False,
            (True, None): None,
            (False, True): False,
            (False, False): False,
            (False, None): False,
            (None, True): None,
            (None, False): False,
            (None, None): None,
        }

        for (a, b), expected in truth_table.items():
            result = ThreeValuedLogic.and_operator(a, b)
            assert result == expected, f"AND({a}, {b}) = {result}, expected {expected}"

    def test_or_truth_table(self):
        """Test complete OR truth table"""
        truth_table = {
            (True, True): True,
            (True, False): True,
            (True, None): True,
            (False, True): True,
            (False, False): False,
            (False, None): None,
            (None, True): True,
            (None, False): None,
            (None, None): None,
        }

        for (a, b), expected in truth_table.items():
            result = ThreeValuedLogic.or_operator(a, b)
            assert result == expected, f"OR({a}, {b}) = {result}, expected {expected}"

    def test_not_truth_table(self):
        """Test complete NOT truth table"""
        truth_table = {
            True: False,
            False: True,
            None: None,
        }

        for a, expected in truth_table.items():
            result = ThreeValuedLogic.not_operator(a)
            assert result == expected, f"NOT({a}) = {result}, expected {expected}"
