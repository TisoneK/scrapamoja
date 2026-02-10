# Quickstart Guide: Fix Framework Issues

**Feature**: 002-framework-issues  
**Date**: 2026-01-29  
**Purpose**: Implementation guide for remaining framework issue fixes

## Overview

This guide provides step-by-step instructions for implementing the three remaining framework issues: storage interface completion, test mode navigation support, and subprocess cleanup enhancements.

## Implementation Steps

### 1. Storage Interface Implementation

#### 1.1 Add Missing Methods to FileSystemStorageAdapter

**File**: `src/storage/adapter.py`

**Add these methods to the `FileSystemStorageAdapter` class**:

```python
async def store(self, key: str, value: Any) -> None:
    """Store data with given key using JSON serialization."""
    try:
        file_path = self.base_path / f"{key}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(value, f, indent=2)
        
        self._logger.info(
            "data_stored",
            key=key,
            file_path=str(file_path)
        )
        
    except Exception as e:
        self._logger.error(
            "store_failed",
            key=key,
            error=str(e)
        )
        raise StorageError("store", key, str(e))

async def delete(self, key: str) -> None:
    """Delete data file for given key."""
    try:
        file_path = self.base_path / f"{key}.json"
        if file_path.exists():
            file_path.unlink()
            
            self._logger.info(
                "data_deleted",
                key=key,
                file_path=str(file_path)
            )
        else:
            self._logger.debug(
                "data_not_found",
                key=key,
                message="File not found, no deletion needed"
            )
            
    except Exception as e:
        self._logger.error(
            "delete_failed",
            key=key,
            error=str(e)
        )
        raise StorageError("delete", key, str(e))
```

**Key Points**:
- Use JSON serialization for data persistence
- Follow existing error handling patterns with StorageError
- Include structured logging with correlation IDs
- Handle missing files gracefully in delete()

#### 1.2 Verify Implementation

**Test the implementation**:
```python
# Test storage operations
from src.storage.adapter import FileSystemStorageAdapter
import tempfile
from pathlib import Path

# Create temporary storage
with tempfile.TemporaryDirectory() as temp_dir:
    storage = FileSystemStorageAdapter(base_path=Path(temp_dir))
    
    # Test store
    await storage.store("test_key", {"data": "test_value"})
    
    # Test delete
    await storage.delete("test_key")
    
    print("Storage operations working correctly")
```

---

### 2. Test Mode Navigation Support

#### 2.1 Create Test Pages Directory

**Create directory**: `examples/test_pages/`

```bash
mkdir -p examples/test_pages
```

#### 2.2 Create Google Stub Page

**File**: `examples/test_pages/google_stub.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google Search Stub</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        form { margin: 20px 0; }
        input[type="text"] { 
            width: 300px; 
            padding: 8px; 
            border: 1px solid #ccc; 
            border-radius: 4px; 
        }
        button { 
            padding: 8px 16px; 
            background-color: #4285f4; 
            color: white; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer; 
        }
    </style>
</head>
<body>
    <h1>Google Search Stub</h1>
    <p>This is a test page for browser lifecycle example navigation.</p>
    
    <form>
        <input name="q" type="text" placeholder="Search Google or type a URL">
        <button type="submit">Google Search</button>
    </form>
    
    <script>
        // Simple form handling for testing
        document.querySelector('form').addEventListener('submit', function(e) {
            e.preventDefault();
            const input = document.querySelector('input[name="q"]');
            if (input.value) {
                document.body.innerHTML += '<p>Search submitted for: ' + input.value + '</p>';
            }
        });
    </script>
</body>
</html>
```

#### 2.3 Enhance Browser Lifecycle Example

**File**: `examples/browser_lifecycle_example.py`

**Add imports**:
```python
import os
from pathlib import Path
```

**Add URL selection method**:
```python
def _get_navigation_url(self) -> str:
    """Get navigation URL based on test mode setting."""
    if os.getenv('TEST_MODE'):
        test_page_path = Path(__file__).parent / "test_pages" / "google_stub.html"
        if not test_page_path.exists():
            raise FileNotFoundError(f"Test page not found: {test_page_path}")
        return f"file://{test_page_path.absolute()}"
    else:
        return "https://www.google.com"
```

**Modify navigate_to_google method**:
```python
async def navigate_to_google(self) -> None:
    """
    Stage 2: Navigate to Google or test page
    
    Demonstrates:
    - Page navigation with timeout handling
    - Waiting for specific elements
    - Retry logic for transient failures
    - Test mode support for CI environments
    
    Error handling: Navigation timeout, element not found
    """
    stage_start = time.time()
    print("\n" + "=" * 60)
    print("STAGE 2: Navigate to Google")
    print("=" * 60)
    
    max_attempts = 3
    base_delay = 1.0
    
    for attempt in range(1, max_attempts + 1):
        try:
            url = self._get_navigation_url()
            print(f"  * Navigating to {url}...")
            
            # Navigate with timeout
            await self.page.goto(url, timeout=self.timeout_ms)
            
            # Wait for search input
            await self.page.wait_for_selector('input[name="q"]', timeout=10000)
            
            elapsed = time.time() - stage_start
            self.stage_times["navigation"] = elapsed
            
            mode = "TEST MODE" if os.getenv('TEST_MODE') else "NORMAL MODE"
            print(f"  [PASS] Navigation completed in {elapsed:.2f}s ({mode})")
            return
            
        except Exception as e:
            if attempt == max_attempts:
                raise RuntimeError(f"Navigation failed after {max_attempts} attempts: {str(e)}")
            
            delay = base_delay * attempt
            print(f"  * Attempt {attempt} failed, retrying in {delay}s...")
            await asyncio.sleep(delay)
```

#### 2.4 Test Implementation

**Test normal mode**:
```bash
python -m examples.browser_lifecycle_example
```

**Test test mode**:
```bash
TEST_MODE=1 python -m examples.browser_lifecycle_example
```

---

### 3. Subprocess Cleanup Enhancement

#### 3.1 Track Subprocess Handles

**File**: `src/browser/session.py`

**Add to BrowserSession.__post_init__**:
```python
# Track subprocess handles for cleanup
self._subprocess_handles = []
```

**Add to browser creation**:
```python
# Track browser process handle
if browser and hasattr(browser, '_impl_obj'):
    self._subprocess_handles.append(browser._impl_obj)
```

#### 3.2 Enhanced Cleanup Method

**Add cleanup method to BrowserSession**:
```python
def _cleanup_subprocess_handles(self) -> None:
    """Clean up subprocess handles with Windows-specific handling."""
    for handle in self._subprocess_handles:
        try:
            if hasattr(handle, 'process') and handle.process:
                # Check if process is still running
                if handle.process.poll() is None:
                    # Try to terminate gracefully
                    try:
                        handle.process.terminate()
                        # Give it a moment to terminate
                        import time
                        time.sleep(0.1)
                        # Force kill if still running
                        if handle.process.poll() is None:
                            handle.process.kill()
                    except Exception:
                        pass  # Ignore termination errors
                        
        except Exception as e:
            # Log cleanup errors but don't raise
            if hasattr(self, '_logger'):
                self._logger.warning(
                    "subprocess_cleanup_error",
                    error=str(e)
                )
```

**Enhance close() method**:
```python
async def close(self) -> None:
    """Close browser session with enhanced subprocess cleanup."""
    try:
        self._logger.info(
            "closing_browser_session",
            session_id=self.session_id
        )
        
        # Close browser and contexts (existing logic)
        if self._browser:
            await self._browser.close()
            self._browser = None
            
        # Enhanced subprocess cleanup
        self._cleanup_subprocess_handles()
        
        self._logger.info(
            "browser_session_closed",
            session_id=self.session_id
        )
        
    except Exception as e:
        self._logger.error(
            "session_close_error",
            session_id=self.session_id,
            error=str(e)
        )
        raise
```

#### 3.3 Test Implementation

**Test subprocess cleanup**:
```python
# Create session and verify cleanup
session = await browser_manager.create_session()
# ... use session ...
await session.close()  # Should complete without subprocess warnings
```

---

## Testing Procedures

### Manual Testing

#### 1. Storage Interface Testing
```bash
# Run browser lifecycle example
python -m examples.browser_lifecycle_example

# Check for storage-related errors in logs
# Should see no "store" or "delete" method errors
```

#### 2. Test Mode Testing
```bash
# Normal mode (requires network)
python -m examples.browser_lifecycle_example

# Test mode (no network required)
TEST_MODE=1 python -m examples.browser_lifecycle_example

# Both should complete navigation successfully
```

#### 3. Subprocess Cleanup Testing
```bash
# Run example and check for subprocess warnings
python -m examples.browser_lifecycle_example

# Should see no "BaseSubprocessTransport" warnings on Windows
```

### Validation Checklist

- [ ] Storage operations complete without errors
- [ ] Test mode navigation works without network
- [ ] Normal mode navigation works with network
- [ ] Subprocess cleanup completes without warnings
- [ ] All logging includes correlation IDs
- [ ] Error handling is graceful and informative

---

## Common Issues

### Storage Issues

**Issue**: Permission denied errors
**Solution**: Ensure write permissions to storage directory

**Issue**: JSON serialization errors
**Solution**: Ensure all data is JSON-serializable

### Navigation Issues

**Issue**: Test page not found
**Solution**: Verify test page exists in correct location

**Issue**: Navigation timeout in normal mode
**Solution**: Check network connectivity and Google accessibility

### Subprocess Issues

**Issue**: Cleanup warnings persist
**Solution**: Verify all subprocess handles are tracked properly

**Issue**: Process termination hangs
**Solution**: Ensure proper timeout handling in cleanup

---

## Performance Considerations

### Storage Performance
- JSON serialization is fast for typical session data
- File operations are async and non-blocking
- Error handling doesn't impact normal operation

### Navigation Performance
- Local test pages load instantly
- Remote navigation depends on network
- Retry logic only activates on failures

### Cleanup Performance
- Subprocess cleanup is fast and non-blocking
- Windows-specific handling adds minimal overhead
- Best effort cleanup prioritizes resource release

---

## Files Modified

### New Files
- `examples/test_pages/google_stub.html` - Test page for navigation
- `specs/002-framework-issues/` - Documentation files

### Modified Files
- `src/storage/adapter.py` - Added store() and delete() methods
- `src/browser/session.py` - Enhanced subprocess cleanup
- `examples/browser_lifecycle_example.py` - Added test mode support

---

## Dependencies

### Required Dependencies
- `pathlib` - For file path operations (built-in)
- `asyncio` - For async operations (built-in)
- `json` - For data serialization (built-in)
- `os` - For environment variables (built-in)

### No New Dependencies Required
All implementation uses existing Python standard library and project dependencies.

---

## Next Steps

1. Implement all three fixes as described
2. Test each fix individually
3. Run complete browser lifecycle example validation
4. Update any relevant documentation
5. Commit changes with descriptive commit messages

---

## Success Metrics

- Browser lifecycle example completes without storage errors
- Test mode enables reliable CI/CD testing
- Subprocess cleanup eliminates Windows warnings
- All logging includes correlation IDs
- Error handling is graceful and informative
