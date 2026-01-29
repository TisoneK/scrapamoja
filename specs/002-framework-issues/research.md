# Research Document: Fix Framework Issues

**Feature**: 002-framework-issues  
**Date**: 2026-01-29  
**Purpose**: Technical decisions and implementation approaches for remaining framework issues

## Storage Interface Implementation

### Issue Analysis
The FileSystemStorageAdapter is missing `store()` and `delete()` methods that are called by BrowserSession during persistence and cleanup operations.

### Technical Decision
**Decision**: Implement missing methods following the existing adapter pattern in FileSystemStorageAdapter.

**Rationale**: 
- Maintains consistency with existing storage interface
- Minimal code changes required
- Follows established error handling patterns
- Preserves backward compatibility

**Implementation Approach**:
```python
async def store(self, key: str, value: Any) -> None:
    """Store data with given key."""
    try:
        file_path = self.base_path / f"{key}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(value, f, indent=2)
    except Exception as e:
        self._logger.error("store_failed", key=key, error=str(e))
        raise StorageError("store", key, str(e))

async def delete(self, key: str) -> None:
    """Delete data with given key."""
    try:
        file_path = self.base_path / f"{key}.json"
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        self._logger.error("delete_failed", key=key, error=str(e))
        raise StorageError("delete", key, str(e))
```

**Alternatives Considered**:
- Create separate storage interface class - Rejected due to unnecessary complexity
- Use existing methods with different signatures - Rejected due to breaking changes

---

## Test Mode Navigation Support

### Issue Analysis
Navigation to Google fails in CI environments due to network restrictions or regional blocking, preventing end-to-end testing of the browser lifecycle example.

### Technical Decision
**Decision**: Add TEST_MODE environment variable support with local HTML test pages.

**Rationale**:
- Enables reliable testing without external dependencies
- Maintains existing navigation flow for production use
- Provides stable test environment for CI/CD
- Minimal changes to existing example code

**Implementation Approach**:
1. Create `examples/test_pages/google_stub.html` with search input
2. Modify browser lifecycle example to detect TEST_MODE environment variable
3. Use local file:// URLs when in test mode
4. Add retry/backoff logic for transient network failures

**Test Page Structure**:
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

**Navigation Logic Enhancement**:
```python
if os.getenv('TEST_MODE'):
    url = f"file://{Path(__file__).parent}/test_pages/google_stub.html"
else:
    url = "https://www.google.com"
```

**Alternatives Considered**:
- Mock network requests - Rejected due to complexity
- Use different external site - Rejected due to similar reliability issues
- Skip navigation in tests - Rejected due to incomplete testing

---

## Subprocess Cleanup on Windows

### Issue Analysis
Asyncio subprocess deallocator warnings appear on Windows during browser process shutdown, indicating potential resource leaks.

### Technical Decision
**Decision**: Enhance session cleanup to ensure subprocess handles are properly closed before asyncio loop shutdown.

**Rationale**:
- Addresses Windows-specific asyncio behavior
- Prevents resource leaks in production
- Maintains clean log output
- Follows subprocess management best practices

**Implementation Approach**:
1. Add explicit subprocess handle cleanup in BrowserSession.close()
2. Guard against closed pipe access in cleanup methods
3. Ensure cleanup happens before asyncio loop shutdown
4. Add structured logging for cleanup operations

**Cleanup Enhancement**:
```python
async def close(self):
    """Close session with enhanced subprocess cleanup."""
    try:
        if self._browser and not self._browser.contexts:
            await self._browser.close()
            self._browser = None
    except Exception as e:
        self._logger.warning("browser_close_failed", error=str(e))
    
    # Explicit cleanup of any remaining subprocess references
    if hasattr(self, '_subprocess_handles'):
        for handle in self._subprocess_handles:
            try:
                if handle and not handle.closed:
                    handle.close()
            except Exception:
                pass  # Ignore cleanup errors
```

**Windows-Specific Considerations**:
- Check pipe state before access
- Use try/except blocks for cleanup operations
- Ensure proper ordering of cleanup operations

**Alternatives Considered**:
- Ignore warnings - Rejected due to potential resource leaks
- Use different subprocess approach - Rejected due to framework impact
- Add platform-specific code only - Rejected due to maintenance complexity

---

## Technical Dependencies

### Required Libraries
- **pathlib**: For file path operations (already in use)
- **asyncio**: For async operations (already in use)
- **json**: For data serialization (already in use)
- **os**: For environment variable access (already in use)

### Integration Points
- **BrowserSession**: Subprocess cleanup enhancements
- **FileSystemStorageAdapter**: Missing method implementations
- **Browser Lifecycle Example**: Test mode support
- **Storage Error Handling**: Consistent error patterns

### Testing Strategy
- Manual validation through browser lifecycle example
- Test mode verification without network access
- Windows subprocess cleanup verification
- Storage operations testing with error scenarios

---

## Implementation Complexity

### Storage Interface: LOW
- Simple method additions following existing patterns
- No breaking changes to existing API
- Straightforward error handling

### Test Mode Support: MEDIUM
- Requires new test page creation
- Environment variable handling
- Navigation logic modifications

### Subprocess Cleanup: MEDIUM
- Windows-specific considerations
- Careful error handling required
- Integration with existing cleanup flow

### Overall Complexity: LOW-MEDIUM
- No architectural changes required
- Maintains existing framework patterns
- Focused bug fixes with minimal scope

---

## Next Steps

1. Implement storage adapter missing methods
2. Create test pages and add TEST_MODE support
3. Enhance subprocess cleanup for Windows
4. Validate all fixes with browser lifecycle example
5. Update documentation as needed
