"""Unit tests for pattern matching functions.

These tests verify the pattern matching functionality in patterns.py
which provides URL matching with prefix, substring, and regex support.
"""

import pytest

from src.network.interception.patterns import (
    is_regex_pattern,
    match_url,
    matches_prefix,
    matches_regex,
    matches_substring,
)


class TestMatchesPrefix:
    """Tests for the matches_prefix function."""

    def test_matches_prefix_true(self) -> None:
        """Test URL starts with pattern - should return True."""
        assert (
            matches_prefix(
                "https://api.example.com", "https://api.example.com/v1/users"
            )
            is True
        )

    def test_matches_prefix_exact_match(self) -> None:
        """Test URL exactly matches pattern - should return True."""
        assert (
            matches_prefix("https://api.example.com", "https://api.example.com") is True
        )

    def test_matches_prefix_false(self) -> None:
        """Test URL doesn't start with pattern - should return False."""
        assert (
            matches_prefix("https://api.example.com", "https://other.example.com/data")
            is False
        )

    def test_matches_prefix_partial_overlap(self) -> None:
        """Test partial URL overlap is actually a prefix match - should return True."""
        # "https://api" IS a prefix of "https://api-other.com"
        assert matches_prefix("https://api", "https://api-other.com") is True

    def test_matches_prefix_empty_pattern(self) -> None:
        """Test empty pattern - should return True (empty is prefix of any string)."""
        assert matches_prefix("", "https://api.example.com") is True

    def test_matches_prefix_empty_url(self) -> None:
        """Test empty URL with non-empty pattern - should return False."""
        assert matches_prefix("https://api.example.com", "") is False


class TestMatchesSubstring:
    """Tests for the matches_substring function."""

    def test_matches_substring_true(self) -> None:
        """Test URL contains pattern - should return True."""
        assert matches_substring("api", "https://api.example.com/v1/users") is True

    def test_matches_substring_exact_match(self) -> None:
        """Test URL exactly matches pattern - should return True."""
        assert (
            matches_substring("https://api.example.com", "https://api.example.com")
            is True
        )

    def test_matches_substring_false(self) -> None:
        """Test URL doesn't contain pattern - should return False."""
        assert matches_substring("notpresent", "https://api.example.com/data") is False

    def test_matches_substring_multiple_occurrences(self) -> None:
        """Test URL contains pattern multiple times - should return True."""
        assert matches_substring("api", "https://api.example.com/api/v1") is True


class TestIsRegexPattern:
    """Tests for the is_regex_pattern function."""

    def test_is_regex_pattern_true(self) -> None:
        """Test pattern starts with ^ - should return True."""
        assert is_regex_pattern("^https://api\\..*") is True

    def test_is_regex_pattern_false(self) -> None:
        """Test normal string pattern - should return False."""
        assert is_regex_pattern("https://api.example.com") is False

    def test_is_regex_pattern_caret_in_middle(self) -> None:
        """Test ^ in middle of pattern - should return False."""
        assert is_regex_pattern("https://api^example.com") is False


class TestMatchesRegex:
    """Tests for the matches_regex function."""

    def test_matches_regex_true(self) -> None:
        """Test URL matches regex - should return True."""
        assert matches_regex(r"^https://api\..+", "https://api.example.com") is True

    def test_matches_regex_false(self) -> None:
        """Test URL doesn't match regex - should return False."""
        assert matches_regex(r"^https://api\..+", "http://other.com") is False

    def test_matches_regex_complex_pattern(self) -> None:
        """Test complex regex pattern - should return True."""
        assert (
            matches_regex(r"api/v[0-9]+/users", "https://site.com/api/v1/users") is True
        )

    def test_matches_regex_invalid_pattern(self) -> None:
        """Test invalid regex pattern - should return False."""
        assert matches_regex(r"[invalid", "any url") is False


class TestMatchUrl:
    """Tests for the unified match_url function."""

    def test_match_url_prefix_first(self) -> None:
        """Test prefix matching is tried first."""
        # URL starts with pattern - should match on prefix
        assert (
            match_url(["https://api.example.com"], "https://api.example.com/v1") is True
        )

    def test_match_url_substring_fallback(self) -> None:
        """Test substring matching is tried if prefix fails."""
        # URL contains but doesn't start with pattern - should match on substring
        assert match_url(["api.example"], "https://api.example.com/v1") is True

    def test_match_url_regex_optional(self) -> None:
        """Test regex only used if pattern starts with ^."""
        # Pattern with ^ should use regex
        assert match_url([r"^https://api\..+"], "https://api.example.com") is True

    def test_match_url_no_match(self) -> None:
        """Test no pattern matches - should return False."""
        assert match_url(["https://api.example.com"], "https://other.com/data") is False

    def test_match_url_empty_patterns(self) -> None:
        """Test empty patterns list - should return False."""
        assert match_url([], "https://api.example.com") is False

    def test_match_url_multiple_patterns(self) -> None:
        """Test multiple patterns - should match first matching one."""
        patterns = [
            "https://other.com",
            "https://api.example.com",
            "https://another.com",
        ]
        assert match_url(patterns, "https://api.example.com/v1") is True

    def test_match_url_mixed_pattern_types(self) -> None:
        """Test mixing prefix, substring, and regex patterns."""
        patterns = [
            "https://other.com",  # prefix
            "api.example",  # substring
            r"^https://regex\..+",  # regex
        ]
        # Should match on substring
        assert match_url(patterns, "https://site.com/api.example/path") is True

    def test_match_url_regex_not_used_for_non_caret(self) -> None:
        """Test regex metacharacters in non-^ patterns are treated as literals."""
        # Pattern looks like regex but doesn't start with ^
        # Should be treated as literal string (prefix first, then substring)
        assert (
            match_url([r"api.v1"], "https://api.v1.example.com") is True
        )  # substring match
        assert (
            match_url([r"api.v1"], "https://api.v1.example.com") is True
        )  # exact match
