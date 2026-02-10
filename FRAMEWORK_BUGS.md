# Framework Bugs Exposed by Browser Lifecycle Example

## Overview
Running `python -m examples.browser_lifecycle_example` exposes several critical bugs in the BrowserManager and related framework components. This document tracks these issues for fixing.

## Bug #1: RetryConfig Missing execute_with_retry Method

**File:** `src/browser/resilience.py`

**Location:** Line 229 in `execute_with_resilience()` method

**Error:**
```
AttributeError: 'RetryConfig' object has no attribute 'execute_with_retry'
```

**Root Cause:**
The `execute_with_resilience()` method tries to call:
```python
return await self.retry_configs[retry_config].execute_with_retry(...)
```

But the `RetryConfig` class doesn't have an `execute_with_retry()` method.

**Stack Trace:**
```
File "src/browser/resilience.py", line 229, in execute_with_resilience
    return await self.retry_configs[retry_config].execute_with_retry(
AttributeError: 'RetryConfig' object has no attribute 'execute_with_retry'
```

**Impact:**
- Blocks all session creation through BrowserManager
- BrowserManager.create_session() fails with resilience wrapper

**Fix Required:**
Implement the `execute_with_retry()` method in the RetryConfig class or fix the call site to use the correct method name.

---

## Bug #2: BrowserSession Dataclass Session ID Default Factory Not Triggered

**File:** `src/browser/session.py`

**Location:** Line 60 in `__post_init__()` method

**Error:**
```
TypeError: 'NoneType' object is not subscriptable
```

**Root Cause:**
In `src/browser/manager.py` line 91, the BrowserSession is created with explicit `session_id=None`:
```python
session = BrowserSession(
    session_id=session_id,  # This is None!
    configuration=configuration or BrowserConfiguration()
)
```

When a dataclass field has a `default_factory`, passing an explicit None value overrides the factory and sets the field to None. Then in `__post_init__()`, line 60 tries to slice None:
```python
self._logger = get_logger(f"browser_session.{self.session_id[:8]}")
                                             ~~~~~~~~~~~~~~~^^^^
TypeError: 'NoneType' object is not subscriptable
```

**Stack Trace:**
```
File "src/browser/session.py", line 60, in __post_init__
    self._logger = get_logger(f"browser_session.{self.session_id[:8]}")
TypeError: 'NoneType' object is not subscriptable
```

**Impact:**
- Session initialization fails
- Occurs when create_session() is called with session_id=None (the default)

**Fix Required:**
In `src/browser/manager.py` line 88-92, only pass session_id if it's not None:
```python
# Option 1: Don't pass session_id at all
session = BrowserSession(configuration=configuration or BrowserConfiguration())

# Option 2: Only pass if not None
kwargs = {'configuration': configuration or BrowserConfiguration()}
if session_id is not None:
    kwargs['session_id'] = session_id
session = BrowserSession(**kwargs)
```

---

## Bug #3: FileSystemStorageAdapter Missing list_files Method

**File:** `src/storage/adapter.py`

**Location:** Called during BrowserManager initialization in `_load_persisted_sessions()`

**Error:**
```
WARNING: 'FileSystemStorageAdapter' object has no attribute 'list_files'
```

**Root Cause:**
The BrowserManager calls storage adapter methods during initialization, but FileSystemStorageAdapter doesn't implement all required methods.

**Impact:**
- Non-blocking warning during manager initialization
- Prevents session persistence/recovery features from working
- BrowserManager still initializes despite this error

**Fix Required:**
Implement the missing `list_files()` method in FileSystemStorageAdapter class, or remove the call if it's not needed.

---

## Bug #4: CircuitBreaker.call Not Awaited

**File:** `src/browser/resilience.py` (likely)

**Error:**
```
RuntimeWarning: coroutine 'CircuitBreaker.call' was never awaited
```

**Root Cause:**
The CircuitBreaker is being called without await in an async context, or returning a coroutine instead of executing it.

**Impact:**
- Memory/resource leak from unawaited coroutines
- Resilience/circuit breaking may not work correctly

**Fix Required:**
Ensure all calls to CircuitBreaker.call() are properly awaited.

---

## Testing

The browser lifecycle example exposes these bugs when run:

```bash
cd /path/to/scraper
python -m examples.browser_lifecycle_example
```

Expected behavior after fixes:
1. Browser manager initializes successfully
2. Session is created with proper configuration
3. Page is created in the session
4. Navigation to Google completes
5. Search executes and results load
6. Snapshot is captured and saved
7. Session closes cleanly
8. All timing information is displayed

---

## Related Files

- `examples/browser_lifecycle_example.py` - The test that exposes these bugs
- `examples/README.md` - Documentation on how to run the example
- `src/browser/manager.py` - BrowserManager implementation
- `src/browser/session.py` - BrowserSession implementation  
- `src/browser/resilience.py` - Resilience and retry logic
- `src/storage/adapter.py` - Storage adapter implementations

---

## Priority

1. **CRITICAL** - Bug #1 (RetryConfig.execute_with_retry) - Blocks all BrowserManager usage
2. **CRITICAL** - Bug #2 (Session ID None) - Blocks all session creation
3. **HIGH** - Bug #3 (list_files) - Blocks session persistence
4. **MEDIUM** - Bug #4 (CircuitBreaker await) - Resource leak

---

## Remaining Issues Observed (2026-01-29)

These issues were observed when running the updated `examples/browser_lifecycle_example.py` after fixing the four critical bugs above. They should be addressed next.

### Issue A: Navigation Timeout

**Symptom:**
```
Navigation failed: Page.wait_for_selector: Timeout 30000ms exceeded.
Call log:
    - waiting for locator("input[name='q']") to be visible
```

**Context:**
- Observed during Stage 2 (Navigate to Google).
- Likely caused by network connectivity, regional blocking of Google, or a transient page structure / consent/redirect screen.

**Impact:**
- Prevents the example from completing end-to-end but is not a framework bug in the BrowserManager itself.

**Next Steps / Mitigation:**
- Verify network connectivity from CI/runner environment.
- Add test-mode configuration to use a stable local test page (e.g., `examples/test_pages/google_stub.html`) for CI.
- Add retry/backoff around page.wait_for_selector for robust tests.

---

### Issue B: Storage Interface Missing Methods

**Symptom:**
```
ERROR: 'FileSystemStorageAdapter' object has no attribute 'store'
WARNING: 'FileSystemStorageAdapter' object has no attribute 'delete'
```

**Context:**
- Observed during session persistence and cleanup phases.
- Persistence attempted in `BrowserSession` and failed; cleanup attempted at session close and failed.

**Impact:**
- Session persistence and cleanup features fail; leaves stale state in storage or prevents state recording.

**Fix Required:**
- Implement `store(key, value)` and `delete(key)` in `src/storage/adapter.py` for `FileSystemStorageAdapter`.
- Ensure the adapter follows the storage adapter interface used elsewhere in the repo (check `get_storage_adapter()` usage sites for expected behaviors).

---

### Issue C: Asyncio Subprocess Deallocator Warning

**Symptom:**
```
Exception ignored while calling deallocator <function BaseSubprocessTransport.__del__ ...>:
    File ".../asyncio/base_subprocess.py", line 134, in __del__
    File ".../asyncio/windows_utils.py", line 102, in fileno
ValueError: I/O operation on closed pipe
```

**Context:**
- Observed after session cleanup; related to the browser subprocess/proactor transport on Windows.

**Impact:**
- Unclean shutdown logs and potential resource issues on Windows runners.

**Fix Required / Mitigation:**
- Ensure Playwright browser subprocesses are closed before loop shutdown.
- Guard __repr__/fileno calls or ensure pipes are checked for closed state before access.
- Consider explicit subprocess handle close in session shutdown logic.

---

## Verification Steps

Run the example and confirm these issues are resolved after fixes:

```bash
python -m examples.browser_lifecycle_example
```

Look for:
- BrowserManager initialization logs
- Session creation and page creation logs
- Navigation to Google (or stub page) succeeds
- Snapshot creation
- Session cleanup completes with no storage adapter errors and no subprocess deallocator warnings

---

## New Recommended Tasks

- Implement `store()` and `delete()` in `src/storage/adapter.py` for `FileSystemStorageAdapter` (HIGH)
- Add a local test page stub and update the example to support `TEST_MODE` for CI (MED)
- Harden session shutdown to ensure subprocess pipes are closed safely on Windows (MED)
- Add an automated integration/regression test for the lifecycle example (MED)

