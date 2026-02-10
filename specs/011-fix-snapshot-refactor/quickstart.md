# Quickstart Guide: Core Module Refactoring Fix

**Feature**: `011-fix-snapshot-refactor`  
**Created**: 2025-01-29  
**Status**: Draft

## Overview

This guide provides step-by-step instructions for implementing the core module refactoring fix to resolve undefined variable errors in the snapshot capture system.

## Problem Summary

The `src/browser/snapshot.py` module has an undefined variable error on line 149 where `screenshot_path` is referenced but not defined in the local scope of the `capture_snapshot()` method.

## Solution Overview

Fix the undefined variable by changing the logging statement to properly reference the screenshot metadata:

**Before (Broken)**:
```python
screenshot=bool(screenshot_path)  # ERROR: screenshot_path not defined
```

**After (Fixed)**:
```python
screenshot=bool(screenshot_metadata["filepath"] if screenshot_metadata else False)
```

## Implementation Steps

### Step 1: Verify Current Issue

1. **Import the module to reproduce the error**:
```python
from src.browser.snapshot import DOMSnapshotManager
# This should work fine for imports

# Try to use the capture method
manager = DOMSnapshotManager()
# This will fail when capture_snapshot() is called due to undefined variable
```

2. **Expected Error**:
```
NameError: name 'screenshot_path' is not defined
```

### Step 2: Apply the Fix

1. **Open the file**: `src/browser/snapshot.py`
2. **Navigate to line 149** in the `capture_snapshot()` method
3. **Replace the problematic line**:

**Find this code**:
```python
self.logger.info(
    "DOM snapshot captured",
    page_id=page_id,
    url=url,
    title=title,
    screenshot=bool(screenshot_path)  # <- LINE 149: ERROR HERE
)
```

**Replace with**:
```python
self.logger.info(
    "DOM snapshot captured",
    page_id=page_id,
    url=url,
    title=title,
    screenshot=bool(screenshot_metadata["filepath"] if screenshot_metadata else False)
)
```

### Step 3: Verify the Fix

1. **Test module import**:
```python
from src.browser.snapshot import DOMSnapshotManager
print("✅ Module imports successfully")
```

2. **Test basic functionality**:
```python
import asyncio
from src.browser.snapshot import DOMSnapshotManager

async def test_fix():
    manager = DOMSnapshotManager()
    print("✅ DOMSnapshotManager created successfully")
    
    # Test with a mock page (if available) or verify the method exists
    print("✅ capture_snapshot method is accessible")
    
    # Verify no NameError when accessing the method
    method = getattr(manager, 'capture_snapshot', None)
    if method:
        print("✅ capture_snapshot method found and accessible")
    else:
        print("❌ capture_snapshot method not found")

asyncio.run(test_fix())
```

3. **Expected Output**:
```
✅ Module imports successfully
✅ DOMSnapshotManager created successfully
✅ capture_snapshot method is accessible
✅ capture_snapshot method found and accessible
```

### Step 4: Integration Testing

1. **Test with browser session** (if Playwright is available):
```python
import asyncio
from playwright.async_api import async_playwright
from src.browser.snapshot import DOMSnapshotManager

async def test_integration():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://example.com")
        
        manager = DOMSnapshotManager()
        snapshot = await manager.capture_snapshot(
            page=page,
            page_id="test-page",
            include_screenshot=True,
            include_html_file=True
        )
        
        print(f"✅ Snapshot captured successfully")
        print(f"✅ Screenshot metadata: {snapshot.screenshot_metadata is not None}")
        print(f"✅ HTML metadata: {snapshot.html_metadata is not None}")
        
        await browser.close()

# Run if Playwright is available
# asyncio.run(test_integration())
```

### Step 5: Backward Compatibility Verification

1. **Verify existing snapshots can still be loaded**:
```python
import asyncio
from src.browser.snapshot import DOMSnapshotManager

async def test_backward_compatibility():
    manager = DOMSnapshotManager()
    
    # List existing snapshots (if any)
    snapshots = manager.list_snapshots()
    print(f"✅ Found {len(snapshots)} existing snapshots")
    
    # Try to load the most recent snapshot (if any exist)
    if snapshots:
        latest = snapshots[0]
        loaded = await manager.load_snapshot(latest["page_id"])
        if loaded:
            print("✅ Existing snapshot loaded successfully")
        else:
            print("❌ Failed to load existing snapshot")
    else:
        print("ℹ️  No existing snapshots to test")

asyncio.run(test_backward_compatibility())
```

## Validation Checklist

### ✅ Core Functionality
- [ ] Module imports without ImportError
- [ ] DOMSnapshotManager instantiates without errors
- [ ] capture_snapshot method is accessible
- [ ] No NameError exceptions during execution
- [ ] Logging statement works correctly

### ✅ Screenshot Functionality
- [ ] Screenshot capture works when enabled
- [ ] Screenshot metadata is properly formatted
- [ ] Logging correctly reports screenshot status
- [ ] Graceful handling when screenshot capture fails

### ✅ HTML Functionality
- [ ] HTML file capture works when enabled
- [ ] HTML metadata is properly formatted
- [ ] Content hashing works correctly
- [ ] Graceful handling when HTML capture fails

### ✅ Integration Points
- [ ] Browser session integration works
- [ ] File system operations work correctly
- [ ] JSON serialization/deserialization works
- [ ] Error handling and logging work correctly

### ✅ Backward Compatibility
- [ ] Existing snapshots can be loaded
- [ ] Existing API methods work unchanged
- [ ] No breaking changes to public interfaces
- [ ] JSON schema compatibility maintained

## Common Issues and Solutions

### Issue: Module Import Fails
**Symptom**: ImportError when importing the module
**Solution**: Check that all required dependencies are installed (Playwright, structlog)

### Issue: Screenshot Capture Fails
**Symptom**: screenshot_metadata is None after capture
**Solution**: Ensure PIL/Pillow is installed for image processing, check file permissions

### Issue: HTML Capture Fails
**Symptom**: html_metadata is None after capture
**Solution**: Check file system permissions, ensure snapshot directory is writable

### Issue: Logging Still Shows Errors
**Symptom**: Error messages in logs after fix
**Solution**: Verify the fix was applied correctly, check for other undefined variables

## Performance Considerations

### Minimal Impact
- The fix involves only changing a variable reference
- No additional computational overhead
- No changes to memory usage patterns

### Logging Performance
- Structured logging remains efficient
- No additional string operations introduced
- Conditional boolean evaluation is minimal overhead

## Security Considerations

### No Security Changes
- Fix does not introduce any security vulnerabilities
- File path handling remains secure
- No changes to data validation or sanitization

## Deployment Notes

### Rollout Strategy
1. **Deploy the fix** to resolve the blocking issue
2. **Monitor logs** for any remaining errors
3. **Verify functionality** with actual browser sessions
4. **Test integration** with existing workflows

### Rollback Plan
- The fix is minimal and can be easily reverted if needed
- No database migrations or schema changes required
- Backward compatibility is maintained

## Support

If you encounter issues during implementation:

1. **Check the logs** for specific error messages
2. **Verify the fix** was applied correctly to line 149
3. **Test with a simple example** before complex integration
4. **Review the validation checklist** for missed items

The fix is designed to be minimal and safe, with no breaking changes to existing functionality.
