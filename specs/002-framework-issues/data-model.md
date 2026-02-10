# Data Model: Fix Framework Issues

**Feature**: 002-framework-issues  
**Date**: 2026-01-29  
**Purpose**: Entity definitions and modifications for framework issue fixes

## Entity Overview

This document describes the entities involved in fixing the remaining framework issues, focusing on modifications to existing components rather than new entities.

## Modified Entities

### FileSystemStorageAdapter

**Purpose**: File-based storage adapter with complete interface compliance  
**Location**: `src/storage/adapter.py`  
**Modifications**: Adding missing `store()` and `delete()` methods

#### Fields (Existing)
- `base_path: pathlib.Path` - Base directory for storage operations
- `_logger: structlog.BoundLogger` - Structured logging instance

#### Methods (New)
- `store(key: str, value: Any) -> None` - Store data with JSON serialization
- `delete(key: str) -> None` - Delete stored data file

#### Method Signatures
```python
async def store(self, key: str, value: Any) -> None:
    """Store data with given key using JSON serialization."""
    
async def delete(self, key: str) -> None:
    """Delete data file for given key."""
```

#### State Transitions
- **File Creation**: `store()` creates new JSON file or overwrites existing
- **File Deletion**: `delete()` removes file if exists, no error if missing
- **Error States**: StorageError raised on file system failures

#### Validation Rules
- Key must be non-empty string
- Value must be JSON-serializable
- File operations must be atomic where possible
- Error handling must follow existing StorageError pattern

---

### BrowserSession

**Purpose**: Browser session management with enhanced subprocess cleanup  
**Location**: `src/browser/session.py`  
**Modifications**: Enhanced cleanup for Windows subprocess handling

#### Fields (Existing)
- `session_id: str` - Unique session identifier
- `browser: Optional[playwright.async_api.Browser]` - Playwright browser instance
- `_subprocess_handles: List[Any]` - Track subprocess handles for cleanup (new)

#### Methods (Enhanced)
- `close() -> None` - Enhanced with subprocess handle cleanup
- `_cleanup_subprocesses() -> None` - New method for Windows-specific cleanup

#### Method Signatures
```python
async def close(self) -> None:
    """Close session with enhanced subprocess cleanup."""
    
def _cleanup_subprocess_handles(self) -> None:
    """Clean up subprocess handles with Windows-specific handling."""
```

#### State Transitions
- **Normal Close**: Browser and contexts closed, subprocesses cleaned up
- **Error Close**: Best effort cleanup with error logging
- **Windows Cleanup**: Additional subprocess handle management

#### Validation Rules
- All cleanup operations must be non-blocking
- Errors during cleanup must be logged but not raise exceptions
- Subprocess handles must be checked for closed state before access

---

### BrowserLifecycleExample

**Purpose**: Enhanced browser lifecycle example with test mode support  
**Location**: `examples/browser_lifecycle_example.py`  
**Modifications**: Add TEST_MODE environment variable support

#### Fields (Existing)
- `snapshot_dir: pathlib.Path` - Directory for snapshot storage
- `headless: bool` - Browser headless mode
- `timeout_ms: int` - Operation timeout in milliseconds

#### Methods (Enhanced)
- `navigate_to_google() -> None` - Enhanced with test mode detection
- `_get_navigation_url() -> str` - New method for URL selection

#### Method Signatures
```python
async def navigate_to_google(self) -> None:
    """Navigate to Google or local test page based on TEST_MODE."""
    
def _get_navigation_url(self) -> str:
    """Get navigation URL based on test mode setting."""
```

#### State Transitions
- **Normal Mode**: Navigate to https://www.google.com
- **Test Mode**: Navigate to local file:// URL
- **Error Handling**: Retry/backoff for network failures

#### Validation Rules
- TEST_MODE must be detected via environment variable
- Local test pages must exist before use
- Navigation timeout must be configurable per mode

---

## New Supporting Entities

### TestPageProvider

**Purpose**: Provider for local test HTML pages in test mode  
**Location**: `examples/test_pages/` directory  
**Implementation**: Static HTML files with minimal structure

#### Files
- `google_stub.html` - Google search page stub with input field

#### Structure
```html
<!DOCTYPE html>
<html>
<head><title>Google Search Stub</title></head>
<body>
    <form>
        <input name="q" type="text" placeholder="Search">
        <button type="submit">Search</button>
    </form>
</body>
</html>
```

#### Validation Rules
- Must include elements expected by navigation logic
- Must be accessible via file:// protocol
- Must be self-contained (no external dependencies)

---

## Data Flow

### Storage Operations Flow
```
BrowserSession.persist_state()
    ↓
FileSystemStorageAdapter.store(key, data)
    ↓
JSON serialization to {base_path}/{key}.json
    ↓
Success/Error logging with correlation ID
```

### Cleanup Operations Flow
```
BrowserSession.close()
    ↓
Browser.close() (existing)
    ↓
_cleanup_subprocess_handles() (new)
    ↓
Windows-specific handle cleanup
    ↓
Success/Error logging
```

### Navigation Flow
```
BrowserLifecycleExample.navigate_to_google()
    ↓
_get_navigation_url() (new)
    ↓
TEST_MODE check → local or remote URL
    ↓
Page.goto() with retry/backoff
    ↓
Success/Error handling
```

---

## Error Handling

### Storage Errors
- **StorageError**: Raised for file system failures
- **Logging**: Structured logging with correlation IDs
- **Recovery**: Graceful degradation, operation failure logged

### Cleanup Errors
- **Best Effort**: Errors logged but don't prevent cleanup completion
- **Windows Handling**: Specific handling for closed pipe access
- **Resource Safety**: Ensure no resource leaks

### Navigation Errors
- **Retry Logic**: Automatic retry for transient failures
- **Fallback**: Test mode provides reliable alternative
- **Timeout Handling**: Configurable timeouts per mode

---

## Integration Points

### Storage Integration
- BrowserSession persistence uses FileSystemStorageAdapter
- Error handling follows existing StorageError patterns
- Structured logging with correlation IDs throughout

### Browser Integration
- Session cleanup integrates with existing lifecycle
- Subprocess management works with Playwright browser instances
- Windows-specific handling is transparent to other platforms

### Example Integration
- Test mode is optional enhancement to existing example
- Environment variable detection is standard practice
- Local pages provide reliable testing alternative

---

## Testing Considerations

### Storage Testing
- Test store/delete operations with various data types
- Verify error handling for permission issues
- Test concurrent access scenarios

### Cleanup Testing
- Verify subprocess cleanup on Windows
- Test error handling during cleanup
- Validate no resource leaks remain

### Navigation Testing
- Test both normal and test mode operation
- Verify retry/backoff logic
- Test timeout handling in both modes

---

## Performance Considerations

### Storage Performance
- JSON serialization overhead is minimal for session data
- File operations are asynchronous and non-blocking
- Error handling doesn't impact normal operation performance

### Cleanup Performance
- Subprocess cleanup is fast and non-blocking
- Windows-specific handling adds minimal overhead
- Error handling doesn't delay cleanup completion

### Navigation Performance
- Local test pages load instantly vs network latency
- Retry logic only activates on failures
- Test mode provides predictable performance

---

## Security Considerations

### Storage Security
- File permissions follow system defaults
- No sensitive data in test mode
- JSON files are human-readable for debugging

### Subprocess Security
- Cleanup only affects processes created by session
- No external process manipulation
- Handle validation prevents access violations

### Navigation Security
- Test mode uses only local files
- No external network access in test mode
- Local pages are static and safe
