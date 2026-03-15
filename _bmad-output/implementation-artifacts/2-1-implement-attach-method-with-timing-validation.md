# Story 2.1: Implement attach() Method with Timing Validation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **site module developer**,  
I want **to attach the interceptor to a Playwright page before navigation**,  
So that **the interceptor can capture network responses as they occur**.

## Acceptance Criteria

1. **Given** a NetworkInterceptor instance and a Playwright page object, **When** attach(page) is called before page.goto(), **Then** the interceptor is successfully attached to the page

2. **And** **When** attach(page) is called after page.goto() has already occurred, **Then** a clear TimingError is raised with message: "attach() must be called before page.goto(). Call attach() first, then navigate."

3. **And** the attach method is `async def attach(self, page: Any) -> None`

## Tasks / Subtasks

- [x] Task 1: Implement attach() method that attaches to Playwright page (AC: #1)
  - [x] Subtask 1.1: Add instance variable to track if interceptor is attached (`_page: Any | None`)
  - [x] Subtask 1.2: Add instance variable to track if navigation has occurred (`_has_navigated: bool`)
  - [x] Subtask 1.3: Register for Playwright's 'request' event to detect navigation
  - [x] Subtask 1.4: Implement timing validation before attaching
- [x] Task 2: Implement timing validation with TimingError (AC: #2)
  - [x] Subtask 2.1: Detect if page has already navigated using page.url or response event
  - [x] Subtask 2.2: Raise TimingError with exact message: "attach() must be called before page.goto(). Call attach() first, then navigate."
  - [x] Subtask 2.3: Add unit tests for timing validation
- [x] Task 3: Verify attach() works correctly before navigation (AC: #1)
  - [x] Subtask 3.1: Ensure interceptor can be attached successfully
  - [x] Subtask 3.2: Integration test with Playwright page

## Dev Notes

### Technical Implementation Requirements

**File Location:**
- Primary implementation: `src/network/interception/interceptor.py`
- Tests: `tests/unit/network/interception/test_interceptor.py`

**Key Components:**
1. **Timing Detection Strategy:**
   - Use Playwright's `page.on('request')` event to detect if navigation has occurred
   - Alternative: Check if `page.url` is about:blank or a data: URL (but this is unreliable)
   - Best approach: Track first non-about:blank request as navigation indicator

2. **Attach Flow:**
   ```python
   async def attach(self, page: Any) -> None:
       # Check if already attached
       if self._page is not None:
           raise RuntimeError("Interceptor already attached. Call detach() first.")
       
       # Check if page has already navigated
       if self._has_navigated:
           raise TimingError("attach() must be called before page.goto(). Call attach() first, then navigate.")
       
       # Register for navigation detection
       self._page = page
       page.on("request", self._on_request)
   ```

3. **Navigation Detection:**
   - Use `page.on("request")` callback to detect first navigation request
   - Set `_has_navigated = True` when first request is detected
   - Ignore about:blank and data: URLs

4. **State Management:**
   - `_page: Any | None` - Reference to attached Playwright page
   - `_has_navigated: bool` - Track if navigation has occurred
   - `_request_handler` - Store event handler for cleanup

### Architecture Alignment

- **Class:** NetworkInterceptor (already exists in interceptor.py)
- **Constructor:** Already implemented (Story 1.2) - validates patterns, stores handler
- **Error Types:** TimingError already defined in exceptions.py
- **Pattern Matching:** Already implemented (Story 1.3) - uses patterns.py

### Source References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#NetworkInterceptor Class]
- [Source: src/network/interception/interceptor.py]
- [Source: src/network/interception/exceptions.py#TimingError]

### Testing Standards

- Follow patterns from Story 1.3 (test_patterns.py)
- Use pytest with pytest-asyncio for async tests
- Mock Playwright page object for unit tests
- Include integration test with real Playwright if available

### Project Structure Notes

- Module location: `src/network/interception/`
- Pattern: Same as Stories 1.1-1.3 implementation patterns
- No conflicts detected with previous implementations

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

N/A - Implementation complete

### Completion Notes List

- Implemented attach() method as async def attach(self, page: Any) -> None
- Added instance variables: _page, _has_navigated, _request_handler
- Implemented _on_request() callback to detect navigation via Playwright's 'request' event
- Navigation detection ignores about:blank and data: URLs
- Implemented detach() method to clean up event handlers
- Added is_attached property to check attachment state
- All unit tests pass (24 tests in test_interceptor.py)
- All 59 tests in network/interception module pass

### File List

**Files Modified:**
- `src/network/interception/interceptor.py` - Added attach(), detach(), _on_request(), and is_attached property
- `src/network/__init__.py` - Updated exports for new module structure

**Files Modified (Tests):**
- `tests/unit/network/interception/test_interceptor.py` - Added 14 new tests for attach/detach functionality + 2 integration tests

**Files Created:**
- `src/network/interception/__init__.py` - Module initialization
- `src/network/interception/models.py` - CapturedResponse dataclass
- `src/network/interception/exceptions.py` - Custom exceptions (PatternError, TimingError)
- `src/network/interception/patterns.py` - Pattern matching logic

**Files Deleted:**
- `src/network/interception.py` - Old single-file module (reorganized into package)

## Epic Context (Epic 2: Interceptor Lifecycle & Response Capture)

This story is part of Epic 2 which covers:
- Story 2.1: **Implement attach() Method with Timing Validation** (THIS STORY)
- Story 2.2: Implement Playwright Network Event Listener
- Story 2.3: Implement Response Capture  
- Story 2.4: Implement detach() Method

**FRs covered:** FR3, FR4, FR9, FR10, FR11, FR12, FR18, FR19, FR20, FR21

### Dependencies

- Story 1.1: CapturedResponse dataclass - COMPLETE
- Story 1.2: NetworkInterceptor constructor - COMPLETE
- Story 1.3: Pattern matching system - COMPLETE
- Story 2.2: Network event listener - DEPENDS ON THIS STORY

### Previous Epic Learnings

From Epic 1 (Core Module Setup & Pattern Matching):
- Pattern validation happens at constructor time (not runtime)
- Use patterns.py for isolated pattern matching logic
- TimingError exception already defined and imported in __init__.py
