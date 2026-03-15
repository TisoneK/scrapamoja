# Story 2.4: Implement detach() Method

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **site module developer**,  
I want **to detach the interceptor when interception is complete**,  
So that **resources are properly cleaned up**.

## Acceptance Criteria

1. **Given** an attached interceptor, **When** detach() is called, **Then** the Playwright event listeners are removed

2. **And** all resources are cleaned up properly

3. **And** **When** detach() is called after the page has been closed (late detach), **Then** no exception is raised and no resources leak

## Tasks / Subtasks

- [x] Task 1: Remove Playwright event listeners (AC: #1)
  - [x] Subtask 1.1: Identify all event listeners registered in attach()
  - [x] Subtask 1.2: Implement proper listener removal in detach()
  - [x] Subtask 1.3: Verify listeners are fully removed
- [x] Task 2: Clean up all resources (AC: #2)
  - [x] Subtask 2.1: Clear any internal state references
  - [x] Subtask 2.2: Set page reference to None
  - [x] Subtask 2.3: Verify no resource leaks after detach
- [x] Task 3: Handle late detach gracefully (AC: #3)
  - [x] Subtask 3.1: Test detach() after page.close()
  - [x] Subtask 3.2: Test detach() without prior attach()
  - [x] Subtask 3.3: Verify no exceptions in any late detach scenario

## Dev Notes

### Technical Implementation Requirements

**File Location:**
- Primary implementation: `src/network/interception/interceptor.py`
- Tests: `tests/unit/network/interception/test_interceptor.py`

**Key Components:**

1. **detach() Method Signature:**
   ```python
   async def detach(self) -> None:
       """Detach the interceptor from the page and clean up resources."""
   ```

2. **Event Listener Cleanup:**
   - Registered via: `page.on('response', self._handle_response)` in `attach()`
   - Must remove via: `page.off('response', self._handle_response)`
   - Handle case where page is already closed (page may be None or invalid)

3. **Resource Cleanup Checklist:**
   - Remove event listeners from page
   - Set `self._page = None` to release reference
   - Clear `_has_navigated` flag back to False (ready for reattach)
   - Clear any other session-specific state

4. **Late Detach Handling (Critical):**
   - Try/except all cleanup operations
   - Never raise exception even if page is closed
   - Log warning if detach called without prior attach
   - Silently handle already-removed listeners

5. **Idempotency:**
   - Multiple detach() calls should be safe
   - First detach cleans up; subsequent calls do nothing

### Project Structure Notes

**Module Structure (from Epic 1):**
- `src/network/interception/__init__.py` - exports NetworkInterceptor, CapturedResponse
- `src/network/interception/interceptor.py` - NetworkInterceptor class (THIS STORY)
- `src/network/interception/models.py` - CapturedResponse dataclass
- `src/network/interception/exceptions.py` - NetworkError, TimingError, PatternError
- `src/network/interception/patterns.py` - pattern matching logic

**Dependencies:**
- Playwright >= 1.40.0
- Python 3.11+ with async/await
- Already implemented: 
  - Story 1.1 (module structure)
  - Story 1.2 (constructor)
  - Story 1.3 (pattern matching)
  - Story 2.1 (attach method)
  - Story 2.2 (network event listener)
  - Story 2.3 (response capture)

### Implementation Pattern (Based on Previous Stories)

```python
# Reference: Story 2-3 implementation for _handle_response
# The attach() method registers listeners like this:
# await page.on('response', self._handle_response)

# The detach() method must remove them:
async def detach(self) -> None:
    """Detach the interceptor from the page and clean up resources."""
    # 1. Remove event listener if page exists
    if self._page is not None:
        try:
            # Check if page is still valid (not closed)
            if hasattr(self._page, 'off'):
                self._page.off('response', self._handle_response)
        except Exception:
            # Page closed or invalid - late detach scenario
            # Silently handle - don't raise
            pass
    
    # 2. Clear page reference
    self._page = None
    
    # 3. Reset session-specific state (ready for potential reattach)
    self._has_navigated = False
    
    # 4. Log if dev logging enabled
    if self._dev_logging:
        logger.info("interceptor_detached", message="Resources cleaned up")

# Note: Patterns and handler are set at construction time and remain on the instance.
# They are NOT cleared in detach() - they persist for potential reattach to new page.
```

### Architecture Compliance

**MUST follow these architectural decisions:**

1. **Idempotent Operation**: detach() can be called multiple times safely
2. **Late Detach**: Never raise exception - always handle gracefully
3. **Resource Cleanup**: Release ALL references to enable GC
4. **Silent Failure**: Don't expose Playwright internals in errors

**Anti-Patterns to Avoid:**
- NOT raising exceptions on late detach
- NOT leaking page references after detach
- NOT keeping listener references after removal
- NOT clearing patterns in detach() (they persist for reattach)
- NOT requiring attach() before detach() (idempotent)

### Testing Requirements

**Test Coverage (100% failure mode coverage target):**

1. **Happy Path Tests:**
   - Verify event listener is removed after detach
   - Verify page reference is cleared
   - Verify multiple detach() calls are safe

2. **Edge Case Tests:**
   - detach() called without prior attach() - should not raise
   - detach() called after page.close() - should not raise
   - detach() called after page.goto() without attach() - should not raise
   - Multiple detach() calls - all should be safe

3. **Mock Pattern:**
   - Mock Playwright page object
   - Test without full browser
   - Verify listener removal is called

### References

- [Source: epics.md#Story-24-Implement-detach-Method]
- [Source: architecture.md#Lifecycle-Management]
- [Source: architecture.md#Interface-Design]
- Related: Story 2.1 (attach method), Story 2.2 (event listener), Story 2.3 (response capture)
- Playwright docs: https://playwright.dev/python/docs/api/class-page#page-event-listeners

## Change Log

- 2026-03-15: Enhanced detach() method with late detach handling (try/except all cleanup operations)
- 2026-03-15: Added 5 new edge case tests for detach() - covers AC #3 scenarios
- 2026-03-15: Updated status from ready-for-dev to review

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

- Implementation builds on Story 2.1 (attach) and Story 2.2 (event listener)
- Response handler already exists: _handle_response method
- Must properly remove the 'response' listener registered in attach()

### Completion Notes List

- Enhanced `detach()` method in NetworkInterceptor to handle late detach scenarios gracefully
- Added try/except blocks around all page.off() calls to prevent exceptions when page is closed
- Added warning log when detach() called without prior attach() (when dev_logging enabled)
- Added info log when cleanup completes (when dev_logging enabled)
- Implemented idempotent detach - safe to call multiple times
- All 41 tests in test_interceptor.py pass (11 detach-related tests including 5 new edge case tests)

### File List

- `src/network/interception/interceptor.py` - Enhanced detach() method with late detach handling
- `tests/unit/network/interception/test_interceptor.py` - Added 5 new edge case tests for detach()
