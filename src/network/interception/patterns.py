"""Pattern matching for network interception.

This module provides URL pattern matching functionality with support for:
- String prefix matching (URL starts with pattern) - DEFAULT
- String substring matching (URL contains pattern) - FALLBACK
- Regex matching (if pattern starts with ^) - OPTIONAL

The matching order is fixed: prefix → substring → regex
"""

from __future__ import annotations

import re


def matches_prefix(pattern: str, url: str) -> bool:
    """Check if URL starts with pattern.

    This is the default fast path for pattern matching.

    Args:
        pattern: The pattern to match against
        url: The URL to check

    Returns:
        True if URL starts with pattern, False otherwise
    """
    return url.startswith(pattern)


def matches_substring(pattern: str, url: str) -> bool:
    """Check if URL contains pattern.

    This is the fallback matching strategy when prefix doesn't match.

    Args:
        pattern: The pattern to match against
        url: The URL to check

    Returns:
        True if URL contains pattern, False otherwise
    """
    return pattern in url


def is_regex_pattern(pattern: str) -> bool:
    """Determine if pattern should be treated as regex.

    Convention: Patterns starting with ^ are treated as regex.

    Args:
        pattern: The pattern to check

    Returns:
        True if pattern should use regex matching
    """
    return pattern.startswith("^")


def matches_regex(pattern: str, url: str) -> bool:
    """Check if URL matches regex pattern.

    Args:
        pattern: The regex pattern to match against
        url: The URL to check

    Returns:
        True if URL matches regex pattern, False otherwise
    """
    try:
        return bool(re.search(pattern, url))
    except re.error:
        return False


def match_url(patterns: list[str], url: str) -> bool:
    """Check if URL matches any of the provided patterns.

    Matching order:
    1. String prefix matching (default fast path)
    2. String substring matching (fallback)
    3. Regex matching (if pattern starts with ^)

    Args:
        patterns: List of URL patterns to match against
        url: The URL to check

    Returns:
        True if URL matches any pattern, False otherwise
    """
    for pattern in patterns:
        # Check if this is a regex pattern
        if is_regex_pattern(pattern):
            if matches_regex(pattern, url):
                return True
        else:
            # String matching (prefix first, then substring)
            if matches_prefix(pattern, url):
                return True
            if matches_substring(pattern, url):
                return True
    return False
