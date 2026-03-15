# Story 1.3: Implement Pattern Matching System

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **site module developer**,  
I want **to use flexible URL pattern matching (prefix, substring, regex)**,  
So that **I can capture exactly the network responses I need**.

## Acceptance Criteria

1. **Given** registered patterns in the interceptor, **When** a network response URL is evaluated, **Then** the pattern matching follows this order:

   1. **First**, string prefix matching (URL starts with pattern) - this is the default fast path
   2. **If no prefix match**, string substring matching (URL contains pattern) - this is the fallback
   3. **If regex is specified** for a pattern, regex matching is used instead of string matching

2. **And** all pattern matching logic is isolated in patterns.py for independent unit testing

3. **And** the pattern matching can be tested without instantiating the full NetworkInterceptor

## Tasks / Subtasks

- [x] Task 1: Implement prefix matching in patterns.py (AC: #1)
  - [x] Subtask 1.1: Create `matches_prefix(pattern: str, url: str) -> bool` function
  - [x] Subtask 1.2: Default matching uses prefix (URL starts with pattern)
  - [x] Subtask 1.3: Add unit tests for prefix matching
- [x] Task 2: Implement substring matching fallback (AC: #1)
  - [x] Subtask 2.1: Create `matches_substring(pattern: str, url: str) -> bool` function
  - [x] Subtask 2.2: Fallback to substring if prefix doesn't match
  - [x] Subtask 2.2: Add unit tests for substring matching
- [x] Task 3: Implement regex matching (AC: #1)
  - [x] Subtask 3.1: Create `matches_regex(pattern: str, url: str) -> bool` function
  - [x] Subtask 3.2: Allow optional regex per pattern (flag or prefix indicator)
  - [x] Subtask 3.3: Pre-compile regex patterns for efficiency
  - [x] Subtask 3.4: Add unit tests for regex matching
- [x] Task 4: Implement unified match function (AC: #1)
  - [x] Subtask 4.1: Create `match_url(patterns: list[str], url: str) -> bool` function
  - [x] Subtask 4.2: Implement matching order: prefix → substring → regex
  - [x] Subtask 4.3: Add comprehensive unit tests
- [x] Task 5: Integrate with NetworkInterceptor (AC: #2)
  - [x] Subtask 5.1: Update NetworkInterceptor to use patterns.py matching functions
  - [x] Subtask 5.2: Remove inline pattern matching from interceptor.py
  - [x] Subtask 5.3: Ensure patterns.py can be tested independently

## Dev Notes

### 🚨 CRITICAL ARCHITECTURE DISCREPANCY - MUST FIX

**This is a CRITICAL issue from Story 1.2 that MUST be corrected:**

The current `interceptor.py` (from Story 1.2) uses **regex by default**:
```python
self._compiled_patterns: list[re.Pattern[str]] = [
    re.compile(pattern) for pattern in self._patterns
]
```

However, the **Epic explicitly requires** (FR5-FR7):
- **FR5**: String prefix matching for URL patterns (**default** behavior)
- **FR6**: String substring matching for URL patterns (fallback)
- **FR7**: Optional regex-based pattern matching per interceptor instance

**The acceptance criteria is CLEAR:**
> "First, string prefix matching (URL starts with pattern) - **this is the default fast path**"

**You MUST change the implementation to:**
1. Use string prefix matching by DEFAULT (not regex)
2. Use substring matching as FALLBACK
3. Only use regex if explicitly specified for a pattern

### Project Structure Notes

- **Module Location**: `src/network/interception/` - Already created in Story 1.1
- **File to Modify**: `src/network/interception/patterns.py` - Currently a placeholder (8 lines)
- **File to Update**: `src/network/interception/interceptor.py` - Currently uses regex by default
- **Alignment**: Follows the `src/module_name/` pattern established in project-context.md
- **Previous Stories**: 
  - Story 1.1: Created module structure and CapturedResponse dataclass
  - Story 1.2: Implemented constructor with pattern validation (BUT used regex by default - MUST FIX)

### Architecture Patterns to Follow

From architecture.md:
- **Pattern Matching**: string prefix/substring default, regex optional
- **patterns.py isolated**: Pattern matching logic must be in patterns.py for independent unit testing
- **NOT regex by default**: The current implementation violates the architecture!

### Key Constraints

1. **MATCHING ORDER (LOCKED)**:
   - First: String prefix matching (URL starts with pattern) - **DEFAULT**
   - Second: String substring matching (URL contains pattern) - **FALLBACK**
   - Third: Regex matching (if specified for a pattern) - **OPTIONAL**

2. **Default is STRING matching, NOT regex**:
   ```python
   # WRONG (current implementation):
   re.compile(pattern)  # regex by default
   
   # CORRECT (required):
   url.startswith(pattern)  # prefix by default
   url in url  # substring as fallback
   ```

3. **Regex Specification**:
   - How to indicate a pattern should use regex? Options:
     - Prefix with `regex:` indicator
     - Use a separate data structure with pattern + type
     - **Recommend**: Use `^` at start of pattern to indicate regex intent (common convention)

4. **Testing Isolation**:
   - patterns.py must work WITHOUT importing NetworkInterceptor
   - Create pure functions: `matches_prefix()`, `matches_substring()`, `matches_regex()`, `match_url()`
   - Test patterns.py in complete isolation

5. **Integration**:
   - NetworkInterceptor will call patterns.py functions
   - Remove inline matching from interceptor.py
   - Ensure backward compatibility for any existing code

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Pattern-Matching]
- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.3]
- [Source: _bmad-output/implementation-artifacts/1-2-implement-networkinterceptor-constructor-with-pattern-validation.md]
- [Source: _bmad-output/project-context.md#Language-Specific-Rules]
- [Source: _bmad-output/project-context.md#Framework-Specific-Rules]

---

## Additional Developer Context

### Technical Requirements Summary

#### Pattern Matching Functions (Required in patterns.py)

```python
# src/network/interception/patterns.py

def matches_prefix(pattern: str, url: str) -> bool:
    """Check if URL starts with pattern.
    
    Args:
        pattern: The pattern to match against
        url: The URL to check
        
    Returns:
        True if URL starts with pattern, False otherwise
    """
    return url.startswith(pattern)


def matches_substring(pattern: str, url: str) -> bool:
    """Check if URL contains pattern.
    
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
    import re
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
```

#### NetworkInterceptor Integration

Update `interceptor.py` to use patterns.py:

```python
from src.network.interception.patterns import match_url

class NetworkInterceptor:
    # ... existing code ...
    
    def _matches(self, url: str) -> bool:
        """Check if URL matches any registered pattern.
        
        Uses patterns.py matching functions for isolated testing.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL matches any pattern
        """
        return match_url(self._patterns, url)
```

### Testing Requirements

- **Framework**: pytest with asyncio_mode=auto
- **Location**: `tests/unit/network/interception/test_patterns.py`
- **Tests to Write**:
  - `test_matches_prefix_true()` - URL starts with pattern
  - `test_matches_prefix_false()` - URL doesn't start with pattern
  - `test_matches_substring_true()` - URL contains pattern
  - `test_matches_substring_false()` - URL doesn't contain pattern
  - `test_is_regex_pattern_true()` - Pattern starts with ^
  - `test_is_regex_pattern_false()` - Normal string pattern
  - `test_matches_regex_true()` - Regex match succeeds
  - `test_matches_regex_false()` - Regex match fails
  - `test_match_url_prefix_first()` - Prefix matching is tried first
  - `test_match_url_substring_fallback()` - Substring tried if prefix fails
  - `test_match_url_regex_optional()` - Regex only if ^ prefix
  - `test_match_url_no_match()` - Returns False when no pattern matches
  - `test_match_url_empty_patterns()` - Returns False for empty list

### Quality Gates

1. All files must have proper docstrings
2. MyPy strict mode must pass
3. Black formatting (88 char limit) must pass
4. Ruff linting must pass
5. 100% test coverage for pattern matching logic
6. All acceptance criteria must be satisfied
7. **CRITICAL**: Default matching must be STRING (prefix), NOT regex

### What NOT to Do

- **NOT** use regex by default (violates Epic requirements)
- **NOT** skip testing patterns.py in isolation
- **NOT** put matching logic in interceptor.py (must be in patterns.py)
- **NOT** change the constructor signature (LOCKED by Story 1.2)
- **NOT** implement attach() or detach() methods (wait for Epic 2)
- **NOT** use "body" field name (must be "raw_bytes" - already done in Story 1.1)

### Previous Story Learnings (Story 1.2)

From Story 1.2 implementation:
- Constructor validates patterns at construction time
- Patterns are stored in `self._patterns` list
- Regex is compiled at construction time (BUT this is WRONG - needs fixing!)
- PatternError is raised for invalid patterns

**CRITICAL ISSUE TO FIX**:
The current implementation uses regex by default:
```python
self._compiled_patterns: list[re.Pattern[str]] = [
    re.compile(pattern) for pattern in self._patterns
]
```

This MUST be changed to use string prefix/substring matching by default.

### Next Stories Context

This story establishes the foundation for:
- **Epic 2**: Interceptor lifecycle (attach/detach) - will use match_url()
- **Epic 3**: Error handling and developer experience (pattern mismatch warnings)

The pattern matching system implemented here will be used throughout all subsequent stories.

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

### Completion Notes List

- Created comprehensive story context with architectural guardrails
- **CRITICAL**: Identified that Story 1.2 implemented regex by default, but Epic requires string prefix/substring by default
- This story MUST fix the architecture discrepancy
- Previous story learnings incorporated: PatternError class exists, patterns stored in constructor
- Constructor signature LOCKED - but matching logic in patterns.py can/should be changed
- Pattern validation at construction time is already done (Story 1.2) - matching logic is what needs implementation

### Implementation Notes (2026-03-15)

**Completed Implementation:**
- Implemented pattern matching system in `patterns.py` with:
  - `matches_prefix()` - String prefix matching (DEFAULT)
  - `matches_substring()` - String substring matching (FALLBACK)
  - `is_regex_pattern()` - Detects regex patterns (those starting with ^)
  - `matches_regex()` - Regex matching (OPTIONAL)
  - `match_url()` - Unified function implementing matching order: prefix → substring → regex

**NetworkInterceptor Integration:**
- Updated `interceptor.py` to use `match_url()` from patterns.py
- Removed inline regex compilation (`_compiled_patterns`)
- Updated validation to only validate regex patterns (those starting with ^)
- Added `_matches()` method that uses patterns.py

**Testing:**
- Created comprehensive test suite in `tests/unit/network/interception/test_patterns.py`
- Updated existing tests in `test_interceptor.py` to match new behavior
- All 38 tests pass
- Ruff linting passes
- Black formatting passes

**Key Architectural Fix:**
- FIXED: Changed default matching from regex to string prefix/substring
- This aligns with Epic 1 requirements (FR5-FR7)

### File List

**Files MODIFIED:**
- `src/network/interception/patterns.py` - Implemented pattern matching functions
- `src/network/interception/interceptor.py` - Updated to use patterns.py, removed inline regex
- `src/network/__init__.py` - Added exports for NetworkInterceptor, CapturedResponse, pattern functions

**Files CREATED:**
- `tests/unit/network/interception/test_patterns.py` - Comprehensive pattern matching tests (25 tests)

**Files UPDATED (tests):**
- `tests/unit/network/interception/test_interceptor.py` - Updated to match new behavior

**Files DELETED:**
- `src/network/interception.py` - Replaced by `src/network/interception/` directory

**Files VERIFIED EXIST (from Stories 1.1, 1.2):**
- `src/network/interception/__init__.py` - Public API exports
- `src/network/interception/exceptions.py` - PatternError class
- `src/network/interception/models.py` - CapturedResponse class
