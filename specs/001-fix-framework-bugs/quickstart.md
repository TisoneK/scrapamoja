# Quickstart: Fix Framework Bugs

**Date**: 2025-01-29  
**Purpose**: Quick reference for implementing and testing framework bug fixes

## Overview

This feature fixes four critical bugs that prevent the Scorewise scraper framework from functioning:

1. **RetryConfig missing execute_with_retry method** - Blocks resilience operations
2. **BrowserSession session_id None handling** - Prevents session creation
3. **FileSystemStorageAdapter missing list_files method** - Blocks session persistence
4. **CircuitBreaker async await issues** - Causes resource leaks

## Implementation Steps

### Step 1: Fix RetryConfig (Bug #1)

**File**: `src/browser/resilience.py`

```python
# Add this method to RetryConfig class
async def execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
    """Execute operation with retry configuration."""
    import asyncio
    
    for attempt in range(self.max_attempts):
        try:
            return await operation(*args, **kwargs)
        except Exception as e:
            if attempt == self.max_attempts - 1:
                raise
            if not any(isinstance(e, exc_type) for exc_type in self.exceptions):
                raise
            await asyncio.sleep(self.delay * (self.backoff_factor ** attempt))
```

### Step 2: Fix BrowserSession (Bug #2)

**File**: `src/browser/session.py`

```python
# Modify __post_init__ method
def __post_init__(self):
    if self.session_id is None:
        import uuid
        self.session_id = str(uuid.uuid4())
    
    from src.core.logging import get_logger
    self._logger = get_logger(f"browser_session.{self.session_id[:8]}")
```

### Step 3: Fix FileSystemStorageAdapter (Bug #3)

**File**: `src/storage/adapter.py`

```python
# Add this method to FileSystemStorageAdapter class
async def list_files(self, pattern: str = "*") -> List[str]:
    """List files matching pattern in storage directory."""
    from pathlib import Path
    
    storage_path = Path(self.storage_path)
    if not storage_path.exists():
        return []
    
    files = []
    for file_path in storage_path.glob(pattern):
        if file_path.is_file():
            files.append(str(file_path.relative_to(storage_path)))
    return files
```

### Step 4: Fix CircuitBreaker Usage (Bug #4)

**File**: `src/browser/resilience.py` and other usage locations

```python
# Find all CircuitBreaker.call() usage and ensure proper awaiting
# Before (causing warning):
result = circuit_breaker.call(operation)

# After (properly awaited):
result = await circuit_breaker.call(operation)
```

## Testing

### Manual Validation

1. **Run the browser lifecycle example**:
   ```bash
   cd c:\Users\tison\Dev\scorewise\scraper
   python -m examples.browser_lifecycle_example
   ```

2. **Expected results**:
   - No AttributeError for RetryConfig.execute_with_retry
   - No TypeError for session_id slicing
   - No warnings about missing list_files method
   - No RuntimeWarning about unawaited coroutines
   - All timing information displayed
   - Clean session cleanup

### Component Testing

1. **Test RetryConfig**:
   ```python
   # Test retry functionality
   retry_config = RetryConfig(max_attempts=3, delay=0.1)
   result = await retry_config.execute_with_retry(some_async_operation)
   ```

2. **Test BrowserSession**:
   ```python
   # Test with None session_id
   session = BrowserSession(session_id=None, configuration=config)
   assert session.session_id is not None
   ```

3. **Test FileSystemStorageAdapter**:
   ```python
   # Test file listing
   adapter = FileSystemStorageAdapter("./test_storage")
   files = await adapter.list_files("*.json")
   ```

4. **Test CircuitBreaker**:
   ```python
   # Test proper async usage
   breaker = CircuitBreaker(failure_threshold=3)
   result = await breaker.call(some_async_operation)
   ```

## Validation Checklist

### Pre-Fix Validation
- [ ] Browser lifecycle example fails with AttributeError
- [ ] Session creation fails with TypeError
- [ ] Storage adapter shows missing method warning
- [ ] RuntimeWarning about unawaited coroutines appears

### Post-Fix Validation
- [ ] Browser lifecycle example runs successfully
- [ ] All timing information displayed correctly
- [ ] No critical errors or warnings
- [ ] Session cleanup completes without resource leaks
- [ ] Session persistence works if tested

### Regression Testing
- [ ] Existing functionality still works
- [ ] No breaking changes to public APIs
- [ ] Backward compatibility maintained
- [ ] Performance not degraded

## Common Issues

### Issue: RetryConfig import errors
**Solution**: Ensure proper imports for asyncio and Callable types

### Issue: BrowserSession logging errors
**Solution**: Verify get_logger import and session_id generation

### Issue: FileSystemStorageAdapter path errors
**Solution**: Check storage_path exists and has proper permissions

### Issue: CircuitBreaker still showing warnings
**Solution**: Search for all CircuitBreaker.call() usage and ensure awaiting

## Files Modified

1. `src/browser/resilience.py` - RetryConfig and CircuitBreaker fixes
2. `src/browser/session.py` - BrowserSession session_id handling
3. `src/storage/adapter.py` - FileSystemStorageAdapter list_files method
4. `examples/browser_lifecycle_example.py` - Test validation (no changes needed)

## Dependencies

### Required Imports
```python
import uuid          # For session ID generation
import asyncio       # For retry delays
from pathlib import Path  # For file operations
from typing import Callable, List, Any  # Type hints
```

### Existing Dependencies
- Playwright (async API)
- Framework logging system
- Existing browser management components

## Next Steps

After implementing fixes:

1. **Run manual validation** using browser lifecycle example
2. **Verify all success criteria** from specification
3. **Update documentation** if any API changes were needed
4. **Create integration tests** for future regression prevention
5. **Deploy fixes** to make framework functional again

## Support

If issues arise during implementation:

1. Check the FRAMEWORK_BUGS.md file for detailed error information
2. Review the research.md for technical decisions
3. Consult the data-model.md for entity relationships
4. Run individual component tests to isolate issues

## Success Metrics

The fixes are successful when:

- Browser lifecycle example runs end-to-end without critical errors
- All timing information displays correctly
- No RuntimeWarning messages appear
- Session creation and cleanup work properly
- Framework becomes usable for browser automation tasks
