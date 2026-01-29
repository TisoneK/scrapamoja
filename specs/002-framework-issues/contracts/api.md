# API Contracts: Fix Framework Issues

**Feature**: 002-framework-issues  
**Date**: 2026-01-29  
**Purpose**: Interface definitions and usage contracts for framework issue fixes

## Storage Adapter Interface

### FileSystemStorageAdapter Methods

#### store() Method

**Signature**:
```python
async def store(self, key: str, value: Any) -> None
```

**Purpose**: Store data with given key using JSON serialization

**Parameters**:
- `key: str` - Unique identifier for stored data (must be non-empty)
- `value: Any` - Data to store (must be JSON-serializable)

**Returns**: None

**Raises**:
- `StorageError` - On file system failures or serialization errors

**Usage Example**:
```python
storage = FileSystemStorageAdapter(base_path=Path("./data"))
await storage.store("session_state", {"user_id": "123", "timestamp": "2026-01-29"})
```

**Error Handling Contract**:
- Invalid key format → StorageError with descriptive message
- Serialization failure → StorageError with serialization error details
- File system error → StorageError with underlying error information
- Success → Structured logging with correlation ID

**Performance Contract**:
- Operation completes within 100ms for typical session data
- Non-blocking async operation
- Atomic file write where supported by filesystem

---

#### delete() Method

**Signature**:
```python
async def delete(self, key: str) -> None
```

**Purpose**: Delete stored data file for given key

**Parameters**:
- `key: str` - Identifier for data to delete (must be non-empty)

**Returns**: None

**Raises**:
- `StorageError` - On file system failures

**Usage Example**:
```python
storage = FileSystemStorageAdapter(base_path=Path("./data"))
await storage.delete("session_state")  # Removes ./data/session_state.json
```

**Error Handling Contract**:
- Invalid key format → StorageError with descriptive message
- File system error → StorageError with underlying error information
- File not found → No error (graceful deletion)
- Success → Structured logging with correlation ID

**Performance Contract**:
- Operation completes within 50ms for typical file deletion
- Non-blocking async operation
- Graceful handling of missing files

---

## Browser Session Interface

### Enhanced close() Method

**Signature**:
```python
async def close(self) -> None
```

**Purpose**: Close browser session with enhanced subprocess cleanup

**Parameters**: None

**Returns**: None

**Side Effects**:
- Closes browser instance and all contexts
- Cleans up subprocess handles on Windows
- Logs cleanup operations with correlation ID

**Usage Example**:
```python
session = await browser_manager.create_session()
# ... use session ...
await session.close()  # Enhanced cleanup with subprocess handling
```

**Error Handling Contract**:
- Browser close errors → Logged as warnings, cleanup continues
- Subprocess cleanup errors → Logged as warnings, no exception raised
- Success → Structured logging with cleanup details
- Best effort cleanup → Always attempts to clean up all resources

**Platform-Specific Behavior**:
- **Windows**: Additional subprocess handle cleanup with closed pipe checking
- **Linux/macOS**: Standard cleanup behavior
- **All platforms**: Graceful error handling with detailed logging

**Performance Contract**:
- Cleanup completes within 1 second for normal operation
- Non-blocking async operation
- Resource cleanup is prioritized over speed

---

## Browser Lifecycle Example Interface

### Enhanced Navigation Methods

#### _get_navigation_url() Method

**Signature**:
```python
def _get_navigation_url(self) -> str
```

**Purpose**: Get navigation URL based on test mode setting

**Parameters**: None

**Returns**: str - URL for navigation (local or remote)

**Environment Variables**:
- `TEST_MODE` - If set to any value, uses local test pages

**Usage Example**:
```python
example = BrowserLifecycleExample()
url = example._get_navigation_url()
# Returns: "file:///path/to/test_pages/google_stub.html" if TEST_MODE set
# Returns: "https://www.google.com" otherwise
```

**Behavior Contract**:
- **TEST_MODE not set**: Returns "https://www.google.com"
- **TEST_MODE set**: Returns local file:// URL to test page
- **Test page missing**: Raises FileNotFoundError with descriptive message

---

#### navigate_to_google() Method

**Signature**:
```python
async def navigate_to_google(self) -> None
```

**Purpose**: Navigate to Google or local test page with retry logic

**Parameters**: None

**Returns**: None

**Side Effects**:
- Navigates browser page to appropriate URL
- Implements retry/backoff for network failures
- Logs navigation attempts with correlation ID

**Usage Example**:
```python
example = BrowserLifecycleExample()
await example.navigate_to_google()  # Uses local or remote URL based on TEST_MODE
```

**Error Handling Contract**:
- Network timeout → Retry with exponential backoff (max 3 attempts)
- Navigation failure → RuntimeError with detailed error information
- Test page errors → FileNotFoundError with path information
- Success → Structured logging with navigation details

**Retry Logic Contract**:
- **First attempt**: Immediate navigation
- **Second attempt**: After 1 second delay
- **Third attempt**: After 2 second delay
- **Final failure**: Raise RuntimeError with all attempt details

**Performance Contract**:
- Local test page navigation: < 100ms
- Remote navigation: Depends on network, with 30s timeout
- Retry overhead: Minimal, only on failures

---

## Integration Contracts

### Storage Adapter Integration

**BrowserSession → FileSystemStorageAdapter**:
```python
# Session persistence
await self._storage.store(f"session_{self.session_id}", state_data)

# Session cleanup
await self._storage.delete(f"session_{self.session_id}")
```

**Contract Requirements**:
- All storage operations use correlation IDs from session
- Storage errors are logged but don't prevent session operation
- File paths follow consistent naming convention
- JSON serialization handles all session state data

---

### Subprocess Management Integration

**BrowserSession → Playwright Browser**:
```python
# Enhanced cleanup
if self._browser:
    await self._browser.close()
    self._cleanup_subprocess_handles()  # Windows-specific cleanup
```

**Contract Requirements**:
- Cleanup happens after standard browser close
- Windows-specific handling is transparent to other platforms
- Subprocess handles are tracked throughout session lifecycle
- Cleanup errors don't prevent session closure

---

### Test Mode Integration

**Environment → BrowserLifecycleExample**:
```python
# URL selection
if os.getenv('TEST_MODE'):
    url = self._get_test_page_url()
else:
    url = "https://www.google.com"
```

**Contract Requirements**:
- TEST_MODE detection happens at runtime
- Local test pages are bundled with example
- Navigation logic is identical for both modes
- Error handling is consistent across modes

---

## Error Type Contracts

### StorageError

**Purpose**: File system and storage operation errors

**Attributes**:
- `operation: str` - Type of operation (store, delete, etc.)
- `key: str` - Data key involved in error
- `message: str` - Detailed error description

**Usage**:
```python
raise StorageError("store", key, f"Failed to write file: {str(e)}")
```

---

### RuntimeError (Navigation)

**Purpose**: Navigation failures after retry attempts

**Attributes**:
- Standard RuntimeError with detailed message
- Includes retry attempt details
- Includes underlying error information

**Usage**:
```python
raise RuntimeError(f"Navigation failed after {attempts} attempts: {last_error}")
```

---

## Performance Contracts

### Storage Operations

| Operation | Expected Time | Maximum Time | Notes |
|-----------|---------------|--------------|-------|
| store() | < 100ms | 500ms | Typical session data |
| delete() | < 50ms | 200ms | File deletion |
| list_files() | < 50ms | 200ms | Directory listing |

### Session Operations

| Operation | Expected Time | Maximum Time | Notes |
|-----------|---------------|--------------|-------|
| close() | < 1s | 5s | Includes subprocess cleanup |
| _cleanup_subprocess_handles() | < 100ms | 500ms | Windows-specific |

### Navigation Operations

| Operation | Expected Time | Maximum Time | Notes |
|-----------|---------------|--------------|-------|
| navigate_to_google() (test mode) | < 100ms | 500ms | Local file |
| navigate_to_google() (remote) | < 5s | 30s | Network-dependent |

---

## Testing Contracts

### Storage Testing

**Unit Test Requirements**:
- Test store/delete with various data types
- Test error handling for file system failures
- Test concurrent access scenarios
- Test file permission issues

**Integration Test Requirements**:
- Test with actual BrowserSession persistence
- Test cleanup operations
- Test error recovery scenarios

---

### Subprocess Testing

**Unit Test Requirements**:
- Test subprocess handle tracking
- Test Windows-specific cleanup logic
- Test error handling during cleanup

**Integration Test Requirements**:
- Test with actual browser sessions
- Test cleanup on different platforms
- Test resource leak prevention

---

### Navigation Testing

**Unit Test Requirements**:
- Test URL selection logic
- Test environment variable detection
- Test retry/backoff logic

**Integration Test Requirements**:
- Test navigation in both modes
- Test timeout handling
- Test error recovery scenarios
