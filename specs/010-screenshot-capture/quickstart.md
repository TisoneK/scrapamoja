# Quickstart Guide: Screenshot Capture with Organized File Structure

**Created**: 2025-01-29  
**Version**: 1.0  
**Purpose**: Implementation guide for screenshot capture feature

## Overview

This guide provides step-by-step instructions for implementing screenshot capture functionality in the browser lifecycle snapshot system. The feature adds visual documentation capabilities alongside existing metadata and HTML capture.

## Key Changes

### Enhanced capture_snapshot() Method

The existing `capture_snapshot()` method in `examples/browser_lifecycle_example.py` is extended with screenshot capture capabilities:

```python
async def capture_snapshot(
    self,
    capture_screenshot: bool = True,
    screenshot_mode: str = "fullpage",
    screenshot_quality: int = 90
) -> Optional[str]:
```

### New Directory Structure

```
data/snapshots/
├── wikipedia_search_20260129_082735.json    # Snapshot metadata
├── html/                                    # HTML files (existing)
│   └── wikipedia_search_20260129_082735.html
└── screenshots/                             # Screenshot files (new)
    └── wikipedia_search_20260129_082735.png
```

### Extended JSON Schema

Snapshot JSON now includes optional screenshot metadata:

```json
{
  "schema_version": "1.2",
  "page": {
    "screenshot": {
      "filepath": "screenshots/wikipedia_search_20260129_082735.png",
      "captured_at": "2025-01-29T12:30:45.456Z",
      "width": 1920,
      "height": 3000,
      "file_size_bytes": 245760,
      "capture_mode": "fullpage",
      "format": "png"
    }
  }
}
```

## File Structure

### Modified Files

```
src/examples/
└── browser_lifecycle_example.py              # MODIFIED: Enhanced capture_snapshot()
```

### New Files

```
data/snapshots/screenshots/                    # NEW: Screenshot storage directory
└── *.png                                     # NEW: Captured screenshot files
```

## Implementation Steps

### Step 1: Update capture_snapshot() Method

Add screenshot capture functionality to the existing method:

```python
async def capture_snapshot(
    self,
    capture_screenshot: bool = True,
    screenshot_mode: str = "fullpage",
    screenshot_quality: int = 90
) -> Optional[str]:
    """Enhanced snapshot capture with screenshot support."""
    
    # ... existing HTML capture code ...
    
    # Add screenshot capture
    screenshot_file_path = None
    if capture_screenshot:
        try:
            print("  * Capturing page screenshot...")
            screenshot_filename = self._generate_screenshot_filename(timestamp)
            screenshot_dir = self.snapshot_dir / "screenshots"
            screenshot_dir.mkdir(exist_ok=True)
            screenshot_file_path = screenshot_dir / screenshot_filename
            
            # Capture screenshot using Playwright
            screenshot_options = {
                "path": str(screenshot_file_path),
                "type": "png",
                "quality": screenshot_quality
            }
            
            if screenshot_mode == "fullpage":
                screenshot_options["full_page"] = True
            
            await self.page.screenshot(**screenshot_options)
            
            # Get screenshot metadata
            file_size = screenshot_file_path.stat().st_size
            image = Image.open(screenshot_file_path)
            width, height = image.size
            
            print(f"  [PASS] Screenshot saved ({file_size} bytes, {width}x{height})")
            
        except Exception as screenshot_error:
            print(f"  [WARN] Screenshot capture failed: {screenshot_error}")
            print("  * Continuing with metadata-only snapshot...")
            screenshot_file_path = None
    
    # ... continue with existing JSON creation ...
    
    # Add screenshot metadata to snapshot if successful
    if screenshot_file_path:
        snapshot_data["page"]["screenshot"] = {
            "filepath": f"screenshots/{screenshot_filename}",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "width": width,
            "height": height,
            "file_size_bytes": file_size,
            "capture_mode": screenshot_mode,
            "format": "png"
        }
```

### Step 2: Add Screenshot Utility Methods

Add helper methods for screenshot filename generation:

```python
def _generate_screenshot_filename(self, timestamp: str) -> str:
    """Generate screenshot filename matching snapshot JSON."""
    return f"wikipedia_search_{timestamp}.png"

def _get_image_dimensions(self, image_path: Path) -> tuple[int, int]:
    """Get image dimensions from file."""
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            return img.size
    except ImportError:
        # Fallback if PIL not available
        return (0, 0)
```

### Step 3: Update Schema Version

Update the snapshot schema version to reflect new capabilities:

```python
snapshot_data = {
    "schema_version": "1.2",  # Updated from 1.1
    "captured_at": datetime.now(timezone.utc).isoformat(),
    # ... rest of snapshot data ...
}
```

### Step 4: Add Dependencies

Ensure required dependencies are available:

```python
# Add to imports if not already present
from PIL import Image
from pathlib import Path
```

## Usage Examples

### Basic Screenshot Capture

```python
# Create example with screenshot capture (default settings)
example = BrowserLifecycleExample()
success = await example.run()
# Screenshot will be captured automatically
```

### Custom Screenshot Settings

```python
# Modify the capture_snapshot call for custom settings
async def capture_snapshot_with_custom_settings(self):
    return await self.capture_snapshot(
        capture_screenshot=True,
        screenshot_mode="viewport",  # Only visible area
        screenshot_quality=95         # Higher quality
    )
```

### Disable Screenshot Capture

```python
# Capture snapshot without screenshot
async def capture_metadata_only(self):
    return await self.capture_snapshot(
        capture_screenshot=False
    )
```

## Error Handling

### Graceful Degradation

The implementation handles screenshot capture failures gracefully:

```python
try:
    # Screenshot capture logic
    await self.page.screenshot(**screenshot_options)
except Exception as e:
    print(f"  [WARN] Screenshot capture failed: {e}")
    print("  * Continuing with metadata-only snapshot...")
    # Continue with JSON snapshot creation
```

### Common Error Scenarios

1. **Permission Denied**: Screenshots directory not writable
   - **Handling**: Log error, continue with JSON only
   
2. **Disk Space Full**: Insufficient space for screenshot file
   - **Handling**: Log error, continue with JSON only
   
3. **Browser Not Ready**: Page not fully loaded
   - **Handling**: Wait for page load, retry capture
   
4. **Large Screenshot**: File size exceeds limits
   - **Handling**: Log warning, reduce quality if possible

## Performance Considerations

### Screenshot Capture Timing

- **Fullpage captures**: 2-5 seconds typical
- **Viewport captures**: 0.5-2 seconds typical
- **File write operations**: <1 second typical

### Memory Usage

- Screenshot data streamed directly to disk
- Peak memory usage: ~50MB for large screenshots
- No significant memory leaks expected

### File Size Management

- Typical fullpage screenshots: 1-5MB
- Typical viewport screenshots: 100KB-1MB
- Quality settings impact file size significantly

## Configuration Options

### Screenshot Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `fullpage` | Capture entire page content | Complete documentation |
| `viewport` | Capture visible area only | Performance testing |

### Quality Settings

| Quality | File Size | Image Quality | Recommended Use |
|---------|-----------|---------------|-----------------|
| 70 | Small | Good | Performance critical |
| 90 | Medium | Very Good | Default setting |
| 100 | Large | Excellent | High quality needed |

## Testing and Validation

### Manual Testing Steps

1. **Basic Capture Test**:
   ```bash
   python -m examples.browser_lifecycle_example
   ```
   - Verify both JSON and PNG files are created
   - Check screenshot filename matches JSON base name

2. **Viewport Mode Test**:
   ```python
   # Modify capture_snapshot call to use viewport mode
   await self.capture_snapshot(screenshot_mode="viewport")
   ```
   - Verify screenshot shows only visible area
   - Check dimensions match browser viewport

3. **Error Handling Test**:
   - Set screenshots directory to read-only
   - Verify graceful degradation to metadata-only
   - Check appropriate error logging

4. **Backward Compatibility Test**:
   - Run with existing v1.1 snapshots
   - Verify existing functionality unchanged
   - Check new fields are optional

### Validation Checklist

- [ ] Screenshot files created in correct directory
- [ ] Filenames match parent JSON snapshot names
- [ ] JSON schema updated to version 1.2
- [ ] Screenshot metadata accurate and complete
- [ ] Error handling works for various failure modes
- [ ] Performance impact within acceptable limits
- [ ] Backward compatibility maintained

## Troubleshooting

### Common Issues

#### Screenshot Not Created

**Symptoms**: JSON file created but no PNG file
**Causes**:
- Permission denied on screenshots directory
- Disk space insufficient
- Screenshot capture API failed

**Solutions**:
- Check directory permissions
- Verify available disk space
- Review error logs for specific failure reason

#### Large Screenshot Files

**Symptoms**: PNG files much larger than expected
**Causes**:
- Very long pages with fullpage capture
- High quality settings
- Complex page content

**Solutions**:
- Use viewport mode for large pages
- Reduce quality setting
- Consider page-specific optimizations

#### Performance Degradation

**Symptoms**: Snapshot capture much slower than before
**Causes**:
- Large fullpage screenshots
- Slow disk I/O
- Browser rendering issues

**Solutions**:
- Use viewport mode when appropriate
- Check disk performance
- Verify browser health

### Debug Information

Enable detailed logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Key log messages to watch for:
- `Screenshot saved` - Successful capture
- `Screenshot capture failed` - Capture failure
- `Permission denied` - File system issue
- `Disk space` - Storage issue

## Migration Guide

### From v1.1 to v1.2

1. **Update Code**: Add screenshot parameters to `capture_snapshot()` calls
2. **Create Directory**: Ensure `data/snapshots/screenshots/` exists
3. **Test Compatibility**: Verify existing functionality unchanged
4. **Enable Screenshots**: Set `capture_screenshot=True` to enable new feature

### Rollback Plan

If issues occur with screenshot capture:

1. **Disable Feature**: Set `capture_screenshot=False`
2. **Remove Screenshots**: Delete `screenshots/` directory if needed
3. **Reset Schema**: Use schema version 1.1 for compatibility
4. **Report Issues**: Document problems for resolution

## Best Practices

### Screenshot Capture

1. **Use Appropriate Mode**: Choose fullpage vs viewport based on needs
2. **Monitor File Sizes**: Watch for unusually large screenshot files
3. **Handle Errors Gracefully**: Always provide fallback behavior
4. **Clean Up Old Files**: Implement cleanup for orphaned screenshots

### Performance Optimization

1. **Quality Settings**: Balance quality vs file size
2. **Capture Timing**: Capture after page fully loaded
3. **Resource Management**: Stream large files to disk
4. **Error Recovery**: Implement retry logic for transient failures

### Maintenance

1. **Monitor Disk Usage**: Track screenshot storage consumption
2. **Validate Files**: Periodically verify screenshot integrity
3. **Update Dependencies**: Keep Playwright and image libraries current
4. **Document Changes**: Maintain updated documentation for customizations
