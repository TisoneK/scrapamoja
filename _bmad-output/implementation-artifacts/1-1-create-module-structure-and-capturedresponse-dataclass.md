# Story 1.1: Create Module Structure and CapturedResponse Dataclass

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **site module developer**,  
I want **the network interception module to have proper structure with a CapturedResponse dataclass**,  
So that **I can receive structured response data from captured network requests**.

## Acceptance Criteria

**Given** a new Scrapamoja project, **When** importing the NetworkInterceptor module, **Then** the module structure exists at `src/network/interception/` with all five files: `__init__.py`, `interceptor.py`, `models.py`, `exceptions.py`, `patterns.py`

**And** the old `src/network/interception.py` file has been removed

**And** the CapturedResponse dataclass is available with url, status, headers, and raw_bytes fields

**And** the dataclass fields are properly typed (url: str, status: int, headers: dict[str, str], raw_bytes: bytes | None)

## Tasks / Subtasks

- [x] Task 1: Create module directory structure at `src/network/interception/` (AC: #1)
  - [x] Subtask 1.1: Create `__init__.py` with public API exports
  - [x] Subtask 1.2: Create empty `interceptor.py` (NetworkInterceptor class placeholder)
  - [x] Subtask 1.3: Create empty `models.py` (CapturedResponse placeholder)
  - [x] Subtask 1.4: Create empty `exceptions.py` (TimingError, PatternError placeholders)
  - [x] Subtask 1.5: Create empty `patterns.py` (pattern matching placeholder)
- [x] Task 2: Implement CapturedResponse dataclass in `models.py` (AC: #3, #4)
  - [x] Subtask 2.1: Define dataclass with url: str
  - [x] Subtask 2.2: Define dataclass with status: int
  - [x] Subtask 2.3: Define dataclass with headers: dict[str, str]
  - [x] Subtask 2.4: Define dataclass with raw_bytes: bytes | None
  - [x] Subtask 2.5: Add proper type annotations (MyPy strict mode)
  - [x] Subtask 2.6: Add docstrings to dataclass and fields
- [x] Task 3: Export public API in `__init__.py` (AC: #1)
  - [x] Subtask 3.1: Export NetworkInterceptor from interceptor.py
  - [x] Subtask 3.2: Export CapturedResponse from models.py
  - [x] Subtask 3.3: Export TimingError, PatternError from exceptions.py
- [x] Task 4: Remove deprecated file `src/network/interception.py` (AC: #2)
  - [x] Subtask 4.1: Verify file exists before removal
  - [x] Subtask 4.2: Remove the file
  - [x] Subtask 4.3: Verify removal doesn't break imports
- [x] Task 5: Create basic test structure (AC: #1)
  - [x] Subtask 5.1: Create test directory `tests/unit/network/interception/`
  - [x] Subtask 5.2: Create placeholder test files

## Dev Notes

### Project Structure Notes

- **Module Location**: `src/network/interception/` - This is a NEW directory that replaces the existing `src/network/interception.py` file
- **Alignment**: Follows the `src/module_name/` pattern established in project-context.md
- **No Conflicts**: This is the first story in Epic 1, so no prior story context to consider
- **Critical**: The old `src/network/interception.py` must be REMOVED as part of this story

### Architecture Patterns to Follow

From architecture.md:
- **Directory Structure**: `src/network/interception/` with `__init__.py`, `interceptor.py`, `models.py`, `exceptions.py`, `patterns.py`
- **Naming**: PascalCase for classes (`NetworkInterceptor`, `CapturedResponse`), snake_case for functions/variables
- **Type Annotations**: MyPy strict mode - all functions need type annotations
- **Data Class**: Use `@dataclass` decorator from Python's dataclasses module
- **Async Patterns**: Not required for this story (dataclass only), but prepare for async in subsequent stories

### Key Constraints

1. **Response Field Naming**: MUST use `raw_bytes` NOT "body" - this is locked in PRD and architecture
2. **Type Hints**: Must use Python 3.11+ syntax (`dict[str, str]`, `bytes | None`)
3. **Module Exports**: `__init__.py` must export the public API cleanly
4. **No Playwright Code**: This story should NOT require any Playwright imports - that's for later stories

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Module-Architecture]
- [Source: _bmad-output/planning-artifacts/architecture.md#Response-Data-Structure]
- [Source: _bmad-output/planning-artifacts/architecture.md#Module-Structure]
- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.1]
- [Source: _bmad-output/project-context.md#Language-Specific-Rules]
- [Source: _bmad-output/project-context.md#Framework-Specific-Rules]

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

### Completion Notes List

- Created comprehensive story context with all architectural guardrails
- This is the first story in Epic 1 (Core Module Setup & Pattern Matching)
- No previous story learnings to incorporate
- No git history analysis needed (first story)
- No web research needed for this foundational story

### Implementation Summary

**Completed Tasks:**
1. Created module directory structure at `src/network/interception/`
2. Implemented CapturedResponse dataclass with url, status, headers, raw_bytes fields
3. Exported public API in `__init__.py`
4. Removed deprecated file `src/network/interception.py`
5. Created test structure at `tests/unit/network/interception/`

**Backward Compatibility:**
- Added backward-compatible classes (InterceptionConfig, InterceptedResponse, NetworkListener, create_network_error) to support existing code
- Updated `src/network/__init__.py` to re-export old classes

**Tests Added:**
- `tests/unit/network/interception/test_models.py` - 4 tests for CapturedResponse
- `tests/unit/network/interception/test_exceptions.py` - 6 tests for TimingError and PatternError

**Acceptance Criteria Status:**
- ✅ AC #1: Module structure exists at `src/network/interception/` with all five files
- ✅ AC #2: Old `src/network/interception.py` file has been removed
- ✅ AC #3: CapturedResponse dataclass is available with url, status, headers, and raw_bytes fields
- ✅ AC #4: Dataclass fields are properly typed (url: str, status: int, headers: dict[str, str], raw_bytes: bytes | None)

### Code Review Fixes Applied
- Fixed ruff linting errors (20 issues: whitespace, type annotations, imports)
- All quality gates now pass

### File List

**Files to CREATE:**
- `src/network/interception/__init__.py`
- `src/network/interception/interceptor.py`
- `src/network/interception/models.py`
- `src/network/interception/exceptions.py`
- `src/network/interception/patterns.py`
- `tests/unit/network/interception/__init__.py` (optional)
- `tests/unit/network/interception/test_models.py`
- `tests/unit/network/interception/test_exceptions.py` (optional)

**Files to DELETE:**
- `src/network/interception.py`

**Files to MODIFY:**
- Potentially `src/network/__init__.py` if it imports from old interception.py

---

## Additional Developer Context

### Technical Requirements Summary

1. **CapturedResponse Dataclass Fields** (LOCKED):
   ```python
   @dataclass
   class CapturedResponse:
       url: str                          # Request URL
       status: int                      # HTTP status code
       headers: dict[str, str]           # Response headers
       raw_bytes: bytes | None           # Raw response body (NOT "body")
   ```

2. **Exception Classes to Create** (for future use, placeholder now):
   ```python
   class TimingError(Exception):
       """Raised when attach() is called after page.goto()."""
       pass

   class PatternError(Exception):
       """Raised for invalid pattern input at construction time."""
       pass
   ```

3. **Public API Exports** (in `__init__.py`):
   ```python
   from src.network.interception.interceptor import NetworkInterceptor
   from src.network.interception.models import CapturedResponse
   from src.network.interception.exceptions import TimingError, PatternError

   __all__ = ["NetworkInterceptor", "CapturedResponse", "TimingError", "PatternError"]
   ```

### Testing Requirements

- **Framework**: pytest with asyncio_mode=auto
- **Location**: `tests/unit/network/interception/`
- **Coverage**: Test CapturedResponse dataclass creation and field types
- **Pattern**: Mock not needed for this story (pure dataclass)

### Quality Gates

1. All files must have proper docstrings
2. MyPy strict mode must pass
3. Black formatting (88 char limit) must pass
4. Ruff linting must pass
5. Old `src/network/interception.py` must be verified removed

### What NOT to Do

- **NOT** create any async code in this story (wait for story 1.2+)
- **NOT** implement NetworkInterceptor methods (placeholder only)
- **NOT** implement pattern matching logic (placeholder only)
- **NOT** use "body" field name (must be "raw_bytes")
- **NOT** create config objects (args are direct constructor parameters)
- **NOT** add list storage methods (callback-only pattern)

### Next Stories Context

This story establishes the foundation for:
- **Story 1.2**: NetworkInterceptor constructor with pattern validation
- **Story 1.3**: Pattern matching system implementation
- **Epic 2**: Interceptor lifecycle (attach/detach) and response capture
- **Epic 3**: Error handling and developer experience

The CapturedResponse dataclass created here will be used throughout all subsequent stories.
