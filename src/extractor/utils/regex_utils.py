"""
Regex pattern matching utilities for the extractor module.

This module provides optimized regex pattern compilation, caching,
and common pattern utilities for data extraction.
"""

import re
from typing import Any, Dict, List, Optional, Pattern, Tuple, Union


class RegexUtils:
    """Utility class for regex operations with caching and optimization."""
    
    def __init__(self):
        """Initialize regex utilities with empty cache."""
        self._pattern_cache: Dict[str, Pattern] = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def compile_pattern(
        self,
        pattern: str,
        flags: int = 0,
        use_cache: bool = True
    ) -> Pattern:
        """
        Compile regex pattern with optional caching.
        
        Args:
            pattern: Regex pattern string
            flags: Regex flags (re.IGNORECASE, etc.)
            use_cache: Whether to use pattern caching
            
        Returns:
            Compiled regex pattern
        """
        cache_key = f"{pattern}:{flags}"
        
        if use_cache and cache_key in self._pattern_cache:
            self._cache_hits += 1
            return self._pattern_cache[cache_key]
        
        self._cache_misses += 1
        compiled_pattern = re.compile(pattern, flags)
        
        if use_cache:
            self._pattern_cache[cache_key] = compiled_pattern
        
        return compiled_pattern
    
    def find_all(
        self,
        pattern: str,
        text: str,
        flags: int = 0,
        group: Optional[int] = None,
        use_cache: bool = True
    ) -> List[str]:
        """
        Find all matches of pattern in text.
        
        Args:
            pattern: Regex pattern to match
            text: Text to search in
            flags: Regex flags
            group: Group number to extract (None for full match)
            use_cache: Whether to use pattern caching
            
        Returns:
            List of matches
        """
        compiled_pattern = self.compile_pattern(pattern, flags, use_cache)
        matches = compiled_pattern.findall(text)
        
        if group is not None:
            # Extract specific group if pattern has groups
            return [match[group] if isinstance(match, tuple) else match for match in matches]
        
        return matches
    
    def find_first(
        self,
        pattern: str,
        text: str,
        flags: int = 0,
        group: Optional[int] = None,
        use_cache: bool = True
    ) -> Optional[str]:
        """
        Find first match of pattern in text.
        
        Args:
            pattern: Regex pattern to match
            text: Text to search in
            flags: Regex flags
            group: Group number to extract (None for full match)
            use_cache: Whether to use pattern caching
            
        Returns:
            First match or None if not found
        """
        compiled_pattern = self.compile_pattern(pattern, flags, use_cache)
        match = compiled_pattern.search(text)
        
        if match:
            if group is not None:
                return match.group(group)
            return match.group(0)
        
        return None
    
    def extract_numbers(
        self,
        text: str,
        decimal_places: Optional[int] = None,
        use_cache: bool = True
    ) -> List[Union[int, float]]:
        """
        Extract all numbers from text.
        
        Args:
            text: Text to extract numbers from
            decimal_places: If specified, convert to float with this precision
            use_cache: Whether to use pattern caching
            
        Returns:
            List of numbers (int or float)
        """
        # Pattern matches integers and decimals
        pattern = r'-?\d+(?:\.\d+)?'
        matches = self.find_all(pattern, text, use_cache=use_cache)
        
        numbers = []
        for match in matches:
            if '.' in match:
                num = float(match)
                if decimal_places is not None:
                    num = round(num, decimal_places)
                numbers.append(num)
            else:
                numbers.append(int(match))
        
        return numbers
    
    def extract_emails(self, text: str, use_cache: bool = True) -> List[str]:
        """
        Extract email addresses from text.
        
        Args:
            text: Text to extract emails from
            use_cache: Whether to use pattern caching
            
        Returns:
            List of email addresses
        """
        # Basic email pattern
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return self.find_all(pattern, text, re.IGNORECASE, use_cache=use_cache)
    
    def extract_phone_numbers(
        self,
        text: str,
        country_code: str = "US",
        use_cache: bool = True
    ) -> List[str]:
        """
        Extract phone numbers from text.
        
        Args:
            text: Text to extract phone numbers from
            country_code: Country code for pattern matching
            use_cache: Whether to use pattern caching
            
        Returns:
            List of phone numbers
        """
        if country_code.upper() == "US":
            # US phone number patterns
            patterns = [
                r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # 555-555-5555, 555.555.5555, 5555555555
                r'\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b',  # (555) 555-5555
                r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\s*(?:ext\.?\s*\d+)?\b',  # With extension
            ]
        else:
            # Generic international pattern
            patterns = [
                r'\b\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b'
            ]
        
        phone_numbers = []
        for pattern in patterns:
            matches = self.find_all(pattern, text, use_cache=use_cache)
            phone_numbers.extend(matches)
        
        return phone_numbers
    
    def extract_all_matches(
        self,
        pattern: str,
        text: str,
        flags: int = 0,
        group: int = 0,
        use_cache: bool = True
    ) -> List[str]:
        """
        Extract all matches from text using regex pattern.
        
        Args:
            pattern: Regular expression pattern
            text: Text to search in
            flags: Regex flags
            group: Group index to extract (0 for full match)
            use_cache: Whether to use cached compiled pattern
            
        Returns:
            List of all matching strings
        """
        try:
            compiled_pattern = self.compile_pattern(pattern, flags, use_cache)
            matches = compiled_pattern.findall(text)
            
            # Extract specific group if needed
            if group != 0 and matches:
                result = []
                for match in matches:
                    if isinstance(match, tuple) and len(match) > group:
                        result.append(match[group])
                    elif isinstance(match, str):
                        result.append(match)
                return result
            elif isinstance(matches[0], tuple):
                # If matches are tuples, return first group
                return [match[0] for match in matches]
            else:
                return matches
                
        except Exception as e:
            return []
    
    def extract_named_groups(
        self,
        pattern: str,
        text: str,
        flags: int = 0,
        use_cache: bool = True
    ) -> List[Dict[str, str]]:
        """
        Extract matches with named groups from text using regex pattern.
        
        Args:
            pattern: Regular expression pattern with named groups
            text: Text to search in
            flags: Regex flags
            use_cache: Whether to use cached compiled pattern
            
        Returns:
            List of dictionaries with named group matches
        """
        try:
            compiled_pattern = self.compile_pattern(pattern, flags, use_cache)
            matches = compiled_pattern.finditer(text)
            
            result = []
            for match in matches:
                if match.groupdict():
                    result.append(match.groupdict())
                else:
                    # If no named groups, use numbered groups
                    groups = {}
                    for i, group in enumerate(match.groups()):
                        groups[f"group_{i+1}"] = group
                    result.append(groups)
            
            return result
            
        except Exception as e:
            return []
    
    def extract_with_context(
        self,
        pattern: str,
        text: str,
        context_chars: int = 50,
        flags: int = 0,
        use_cache: bool = True
    ) -> List[Dict[str, str]]:
        """
        Extract matches with surrounding context.
        
        Args:
            pattern: Regular expression pattern
            text: Text to search in
            context_chars: Number of characters before and after match
            flags: Regex flags
            use_cache: Whether to use cached compiled pattern
            
        Returns:
            List of dictionaries with match and context
        """
        try:
            compiled_pattern = self.compile_pattern(pattern, flags, use_cache)
            matches = compiled_pattern.finditer(text)
            
            result = []
            for match in matches:
                start = max(0, match.start() - context_chars)
                end = min(len(text), match.end() + context_chars)
                
                result.append({
                    "match": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                    "context_before": text[start:match.start()],
                    "context_after": text[match.end():end],
                    "full_context": text[start:end]
                })
            
            return result
            
        except Exception as e:
            return []
    
    def validate_pattern(
        self,
        pattern: str,
        flags: int = 0
    ) -> Dict[str, Any]:
        """
        Validate regex pattern and return information about it.
        
        Args:
            pattern: Regular expression pattern to validate
            flags: Regex flags
            
        Returns:
            Dictionary with validation results
        """
        try:
            compiled_pattern = re.compile(pattern, flags)
            
            return {
                "valid": True,
                "pattern": pattern,
                "flags": flags,
                "groups": compiled_pattern.groups,
                "groupindex": compiled_pattern.groupindex,
                "pattern_names": list(compiled_pattern.groupindex.keys())
            }
            
        except re.error as e:
            return {
                "valid": False,
                "pattern": pattern,
                "flags": flags,
                "error": str(e),
                "error_position": getattr(e, 'pos', None),
                "groups": 0,
                "groupindex": {},
                "pattern_names": []
            }
    
    def get_pattern_complexity(self, pattern: str) -> Dict[str, Any]:
        """
        Analyze regex pattern complexity.
        
        Args:
            pattern: Regular expression pattern
            
        Returns:
            Dictionary with complexity metrics
        """
        complexity = {
            "length": len(pattern),
            "groups": pattern.count('(') - pattern.count('\\('),  # Approximate
            "alternations": pattern.count('|'),
            "quantifiers": len(re.findall(r'[*+?{}]', pattern)),
            "character_classes": pattern.count('['),
            "anchors": len(re.findall(r'^|\$', pattern)),
            "lookarounds": len(re.findall(r'\(\?[:=!]', pattern)),
            "complexity_score": 0
        }
        
        # Calculate complexity score
        complexity["complexity_score"] = (
            complexity["length"] * 0.1 +
            complexity["groups"] * 2 +
            complexity["alternations"] * 3 +
            complexity["quantifiers"] * 1 +
            complexity["character_classes"] * 1.5 +
            complexity["lookarounds"] * 4
        )
        
        return complexity

    def clean_whitespace(self, text: str) -> str:
        """Clean and normalize whitespace in text."""
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        # Trim leading/trailing whitespace
        return text.strip()
    
    def extract_urls(self, text: str, use_cache: bool = True) -> List[str]:
        """
        Extract URLs from text.
        
        Args:
            text: Text to extract URLs from
            use_cache: Whether to use pattern caching
            
        Returns:
            List of URLs
        """
        # URL pattern
        pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
        return self.find_all(pattern, text, use_cache=use_cache)
    
    def validate_pattern(self, pattern: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a regex pattern is compilable.
        
        Args:
            pattern: Regex pattern to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            re.compile(pattern)
            return True, None
        except re.error as e:
            return False, str(e)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get pattern cache statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0
        
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "cached_patterns": len(self._pattern_cache),
        }
    
    def clear_cache(self):
        """Clear the pattern cache."""
        self._pattern_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0


# Common regex patterns
class CommonPatterns:
    """Commonly used regex patterns."""
    
    EMAIL = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    US_PHONE = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    US_PHONE_WITH_AREA = r'\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b'
    URL = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
    NUMBERS = r'-?\d+(?:\.\d+)?'
    INTEGER = r'-?\d+'
    DECIMAL = r'-?\d+\.\d+'
    WORD = r'\b\w+\b'
    WHITESPACE = r'\s+'
    HTML_TAG = r'<[^>]+>'
    HTML_COMMENT = r'<!--.*?-->'
    CSS_CLASS = r'class=["\']([^"\']+)["\']'
    CSS_ID = r'id=["\']([^"\']+)["\']'
    DATE_ISO = r'\d{4}-\d{2}-\d{2}'
    DATE_US = r'\d{1,2}/\d{1,2}/\d{4}'
    TIME = r'\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?'
