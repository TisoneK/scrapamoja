# Story 1.2: Implement NetworkInterceptor Constructor with Pattern Validation

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **site module developer**,  
I want **to create a NetworkInterceptor with URL patterns and a handler callback**,  
So that **the interceptor can match network responses against my specified patterns**.

## Acceptance Criteria

1. **Given** a NetworkInterceptor constructor with patterns and handler parameters, **When** valid patterns are provided, **Then** the interceptor is created successfully

2. **And** **When** invalid patterns (empty list, invalid regex if provided) are provided, **Then** a clear PatternError is raised with descriptive message

3. **And** the constructor accepts patterns: list[str], handler: Callable, dev_logging: bool = False

## Tasks / Subtasks

- [x] Task 1: Implement NetworkInterceptor.__init__ with pattern storage (AC: #1, #3)
  - [x] Subtask 1.1: Accept patterns: list[str] parameter
  - [x] Subtask 1.2: Accept handler: Callable[[CapturedResponse], Awaitable[None]] parameter
  - [x] Subtask 1.3: Accept dev_logging: bool = False parameter
  - [x] Subtask 1.4: Store patterns internally for later matching
  - [x] Subtask 1.5: Store handler callback reference
  - [x] Subtask 1.6: Initialize dev_logging flag
- [x] Task 2: Implement pattern validation at construction time (AC: #2)
  - [x] Subtask 2.1: Validate patterns is not empty list
  - [x] Subtask 2.2: Validate each pattern string is non-empty
  - [x] Subtask 2.3: If regex patterns provided, validate regex syntax
  - [x] Subtask 2.4: Raise PatternError with clear, actionable message for invalid patterns
- [x] Task 3: Add type annotations and docstrings (AC: #1)
  - [x] Subtask 3.1: Add MyPy strict mode type annotations
  - [x] Subtask 3.2: Add comprehensive docstrings
- [x] Task 4: Write unit tests (AC: #1)
  - [x] Subtask 4.1: Test valid pattern creation
  - [x] Subtask 4.2: Test empty list raises PatternError
  - [x] Subtask 4.3: Test invalid regex raises PatternError
  - [x] Subtask 4.4: Test dev_logging default is False

## Dev Notes

### Project Structure Notes

- **Module Location**: `src/network/interception/` - Already created in Story 1.1
- **File to Modify**: `src/network/interception/interceptor.py` - Already exists as placeholder from Story 1.1
- **Alignment**: Follows the `src/module_name/` pattern established in project-context.md
- **Previous Story**: Story 1.1 created the module structure and CapturedResponse dataclass
- **Critical**: This story builds ON TOP of Story 1.1's foundation - don't recreate what was already done

### Architecture Patterns to Follow

From architecture.md:
- **Constructor Args (LOCKED)**: `patterns: list[str]`, `handler: Callable`, `dev_logging: bool = False`
- **NOT a config object** - args are direct constructor parameters as specified in PRD
- **Storage Pattern**: callback-only (no in-memory list storage) - handler invoked for each matched response
- **Pattern Validation**: At construction time with clear PatternError messages
- **Exception Classes**: PatternError already exists in `src/network/interception/exceptions.py` (created in Story 1.1)

### Key Constraints

1. **Constructor Signature (LOCKED)**:
   ```python
   def __init__(
       self,
       patterns: list[str],
       handler: Callable[[CapturedResponse], Awaitable[None]],
       dev_logging: bool = False
   ) -> None: ...
   ```

2. **Handler Type**: Must be async callable that accepts CapturedResponse and returns None

3. **dev_logging**: Default is False (disabled), when True enables verbose logging

4. **Pattern Storage**: Store patterns for later use by pattern matching system (Story 1.3)

5. **No attach() implementation**: That comes in Story 2.1 - just constructor for now

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Interface-Design]
- [Source: _bmad-output/planning-artifacts/architecture.md#API-Surface-Pattern]
- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.2]
- [Source: _bmad-output/implementation-artifacts/1-1-create-module-structure-and-capturedresponse-dataclass.md]
- [Source: _bmad-output/project-context.md#Language-Specific-Rules]
- [Source: _bmad-output/project-context.md#Framework-Specific-Rules]

---

## Additional Developer Context

### Technical Requirements Summary

1. **NetworkInterceptor Constructor (LOCKED)**:
   ```python
   from typing import Callable, Awaitable
   from src.network.interception.models import CapturedResponse
   from src.network.interception.exceptions import PatternError
   
   class NetworkInterceptor:
       def __init__(
           self,
           patterns: list[str],
           handler: Callable[[CapturedResponse], Awaitable[None]],
           dev_logging: bool = False
       ) -> None:
           """Initialize NetworkInterceptor with patterns and handler.
           
           Args:
               patterns: List of URL patterns to match against network responses.
               handler: Async callback invoked for each matched response.
               dev_logging: Enable verbose logging for debugging (default: False).
           
           Raises:
               PatternError: If patterns list is empty or contains invalid patterns.
           """
           # Implementation here
   ```

2. **Pattern Validation Rules**:
   - Empty list `[]` → PatternError: "patterns list cannot be empty"
   - Empty string in list `[""]` → PatternError: "pattern cannot be empty string"
   - Invalid regex `["[invalid"]` → PatternError: "invalid regex pattern: ..."

3. **Internal Storage**:
   - Store `self._patterns = patterns` for later matching (Story 1.3)
   - Store `self._handler = handler` for callback invocation
   - Store `self._dev_logging = dev_logging` for logging control

### Testing Requirements

- **Framework**: pytest with asyncio_mode=auto
- **Location**: `tests/unit/network/interception/test_interceptor.py`
- **Tests to Write**:
  - `test_constructor_valid_patterns()` - Valid creation
  - `test_constructor_empty_patterns_raises_error()` - Empty list validation
  - `test_constructor_empty_string_pattern_raises_error()` - Empty string validation
  - `test_constructor_invalid_regex_raises_error()` - Regex validation
  - `test_constructor_dev_logging_default_false()` - Default value check
  - `test_constructor_stores_handler()` - Handler storage check
  - `test_constructor_stores_patterns()` - Pattern storage check

### Quality Gates

1. All files must have proper docstrings
2. MyPy strict mode must pass
3. Black formatting (88 char limit) must pass
4. Ruff linting must pass
5. 100% test coverage for pattern validation logic
6. All acceptance criteria must be satisfied

### What NOT to Do

- **NOT** implement attach() or detach() methods (wait for Epic 2)
- **NOT** implement actual pattern matching logic (wait for Story 1.3)
- **NOT** create any Playwright code in this story (constructor only)
- **NOT** use "body" field name (must be "raw_bytes" - already done in Story 1.1)
- **NOT** add list storage methods (callback-only pattern)
- **NOT** change the constructor signature (LOCKED by architecture)

### Previous Story Learnings (Story 1.1)

From Story 1.1 implementation:
- Module structure created at `src/network/interception/`
- CapturedResponse dataclass implemented with url, status, headers, raw_bytes fields
- TimingError and PatternError exception classes created
- Tests for models and exceptions already passing
- Backward-compatible classes added to support existing code

**Actionable Context for Story 1.2**:
- PatternError class already exists in `src/network/interception/exceptions.py` - import and use it
- CapturedResponse already imported in Story 1.1's interceptor.py placeholder
- Test structure already exists at `tests/unit/network/interception/`
- Don't need to create new exception classes - reuse existing PatternError

### Next Stories Context

This story establishes the foundation for:
- **Story 1.3**: Pattern matching system implementation (uses patterns stored here)
- **Epic 2**: Interceptor lifecycle (attach/detach) - will use handler stored here
- **Epic 3**: Error handling and developer experience (dev_logging flag used here)

The constructor implemented here will be used throughout all subsequent stories.

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

### Completion Notes List

- Created comprehensive story context with architectural guardrails
- Story 1.2 builds on Story 1.1's foundation (module structure and CapturedResponse)
- Previous story learnings incorporated: PatternError class already exists
- Constructor signature LOCKED by architecture - do not modify
- Pattern validation at construction time is key requirement
- No Playwright code needed - just constructor and validation logic

### Implementation Notes (2026-03-15)

**Implementation Completed:**
- Implemented NetworkInterceptor.__init__ with full pattern validation
- Constructor accepts: patterns: list[str], handler: Callable, dev_logging: bool = False
- Pattern validation at construction time:
  - Validates non-empty patterns list
  - Validates each pattern is non-empty string
  - Validates regex syntax using re.compile()
  - Raises PatternError with descriptive messages
- Stores patterns as list and compiles regex for efficiency
- All 13 unit tests pass covering:
  - Valid pattern creation
  - Empty list error
  - Empty string pattern error  
  - Invalid regex error
  - dev_logging default (False)
  - Handler storage
  - Pattern storage and copying
  - Compiled patterns

**Code Quality:**
- Black formatting: Passed
- Ruff linting: Passed
- All 23 tests in network/interception module pass

**Files Modified:**
- src/network/interception/interceptor.py - Full implementation
- tests/unit/network/interception/test_interceptor.py - New test file

### File List

**Files to MODIFY:**
- `src/network/interception/interceptor.py` - Implement NetworkInterceptor.__init__

**Files to CREATE:**
- `tests/unit/network/interception/test_interceptor.py` - Constructor tests

**Files to VERIFY EXIST (from Story 1.1):**
- `src/network/interception/exceptions.py` - PatternError class
- `src/network/interception/models.py` - CapturedResponse class
- `src/network/interception/__init__.py` - Public API exports
