"""
Three-Valued Logic System for Semantic Bug Mining Framework

This module implements a three-valued logic system (True, False, None) used for
rule evaluation in the Semantic Bug Mining Framework.

Values:
- True: Rule explicitly passed
- False: Rule explicitly failed
- None: Cannot evaluate (condition not met/parameter missing)
"""

from typing import List, Optional


class ThreeValuedLogic:
    """Three-valued logic system for rule evaluation"""

    @staticmethod
    def compute_overall_passed(results: List[Optional[bool]]) -> Optional[bool]:
        """
        Compute overall evaluation result from a list of results.

        Rules:
        1. False + anything → False
        2. True + None → True
        3. All None → None (not evaluable)

        None is not implicitly treated as True or False.

        Args:
            results: List of boolean results or None

        Returns:
            Overall result: True, False, or None
        """
        if not results:
            return None

        # Rule 1: False + anything → False
        if any(r is False for r in results):
            return False

        # Check for explicit True and None values
        has_true = any(r is True for r in results)
        has_none = any(r is None for r in results)

        # Rule 2: True + None → True
        if has_true and has_none:
            return True

        # Rule 3: All None → None
        if has_none and not has_true:
            return None

        # All True
        if has_true and not has_none:
            return True

        return None

    @staticmethod
    def and_operator(a: Optional[bool], b: Optional[bool]) -> Optional[bool]:
        """
        Three-valued logic AND operation (∧).

        Truth table:
        a ∧ b | True  | False | None
        --------|-------|-------|------
        True    | True  | False | None
        False   | False | False | False
        None    | None  | False | None

        Args:
            a: First operand (True, False, or None)
            b: Second operand (True, False, or None)

        Returns:
            Result of AND operation
        """
        if a is False or b is False:
            return False
        if a is None or b is None:
            return None
        return True

    @staticmethod
    def or_operator(a: Optional[bool], b: Optional[bool]) -> Optional[bool]:
        """
        Three-valued logic OR operation (∨).

        Truth table:
        a ∨ b | True  | False | None
        --------|-------|-------|------
        True    | True  | True  | True
        False   | True  | False | None
        None    | True  | None  | None

        Args:
            a: First operand (True, False, or None)
            b: Second operand (True, False, or None)

        Returns:
            Result of OR operation
        """
        if a is True or b is True:
            return True
        if a is None or b is None:
            return None
        return False

    @staticmethod
    def not_operator(a: Optional[bool]) -> Optional[bool]:
        """
        Three-valued logic NOT operation (¬).

        Truth table:
        a | ¬a
        ---|---
        True | False
        False| True
        None | None

        Args:
            a: Operand (True, False, or None)

        Returns:
            Result of NOT operation
        """
        if a is None:
            return None
        return not a
