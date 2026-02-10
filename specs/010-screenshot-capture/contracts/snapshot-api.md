# Snapshot API Contract: Screenshot Capture Extension

**Created**: 2025-01-29  
**Version**: 1.2  
**Purpose**: API contract for screenshot capture functionality in browser lifecycle snapshots

## Extended capture_snapshot() Method

### Method Signature

```python
async def capture_snapshot(
    self,
    capture_screenshot: bool = True,
    screenshot_mode: str = "fullpage",
    screenshot_quality: int = 90
) -> Optional[str]:
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `capture_screenshot` | boolean | No | True | Whether to capture screenshot along with snapshot |
| `screenshot_mode` | string | No | "fullpage" | Capture mode: "fullpage" or "viewport" |
| `screenshot_quality` | integer | No | 90 | PNG quality setting (1-100) |

### Return Value

- **Type**: `Optional[str]`
- **Success**: Path to saved snapshot JSON file
- **Failure**: `None` (with appropriate error logging)

### Error Handling

| Error Type | Handling | Return Value | Logging |
|-------------|----------|--------------|---------|
| Screenshot capture failed | Graceful degradation | JSON path only | Warning logged |
| File write permission denied | Graceful degradation | JSON path only | Error logged |
| Disk space insufficient | Graceful degradation | JSON path only | Error logged |
| Invalid screenshot mode | Default to fullpage | JSON path only | Warning logged |
| Browser not ready | Retry or fail | None | Error logged |

## JSON Schema Extension

### Schema Version 1.2

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Browser Snapshot with Screenshot",
  "version": "1.2",
  "type": "object",
  "properties": {
    "schema_version": {
      "type": "string",
      "enum": ["1.0", "1.1", "1.2"],
      "description": "Snapshot schema version"
    },
    "captured_at": {
      "type": "string",
      "format": "date-time",
      "description": "Snapshot capture timestamp"
    },
    "page": {
      "type": "object",
      "properties": {
        "title": {"type": "string"},
        "url": {"type": "string"},
        "content_length": {"type": "integer"},
        "html_file": {"type": "string"},
        "content_hash": {"type": "string"},
        "screenshot": {
          "type": "object",
          "properties": {
            "filepath": {
              "type": "string",
              "pattern": "^screenshots/.*\\.png$",
              "description": "Relative path to screenshot file"
            },
            "captured_at": {
              "type": "string",
              "format": "date-time",
              "description": "Screenshot capture timestamp"
            },
            "width": {
              "type": "integer",
              "minimum": 1,
              "description": "Screenshot width in pixels"
            },
            "height": {
              "type": "integer",
              "minimum": 1,
              "description": "Screenshot height in pixels"
            },
            "file_size_bytes": {
              "type": "integer",
              "minimum": 1,
              "description": "Screenshot file size in bytes"
            },
            "capture_mode": {
              "type": "string",
              "enum": ["fullpage", "viewport"],
              "description": "Screenshot capture mode"
            },
            "format": {
              "type": "string",
              "enum": ["png"],
              "description": "Screenshot file format"
            }
          },
          "required": ["filepath", "captured_at", "width", "height", "file_size_bytes", "capture_mode", "format"],
          "additionalProperties": false
        }
      },
      "required": ["title", "url", "content_length"]
    },
    "session": {
      "type": "object",
      "properties": {
        "session_id": {"type": "string"},
        "status": {"type": "string"},
        "browser_type": {"type": "string"}
      },
      "required": ["session_id", "status", "browser_type"]
    },
    "timing": {
      "type": "object",
      "properties": {
        "initialization_ms": {"type": "integer"},
        "navigation_ms": {"type": "integer"},
        "search_ms": {"type": "integer"},
        "snapshot_ms": {"type": "integer"},
        "total_ms": {"type": "integer"}
      },
      "required": ["total_ms"]
    }
  },
  "required": ["schema_version", "captured_at", "page", "session", "timing"],
  "additionalProperties": false
}
```

### Example Snapshot with Screenshot

```json
{
  "schema_version": "1.2",
  "captured_at": "2025-01-29T12:30:45.123Z",
  "page": {
    "title": "Playwright browser automation - Search results - Wikipedia",
    "url": "https://en.wikipedia.org/wiki/Special:Search?search=Playwright+browser+automation",
    "content_length": 571222,
    "html_file": "html/wikipedia_search_20260129_082735.html",
    "content_hash": "c3279cf093e4e1952ae4f48e91da1a20be5ad19df57302db4473180b504ea59c",
    "screenshot": {
      "filepath": "screenshots/wikipedia_search_20260129_082735.png",
      "captured_at": "2025-01-29T12:30:45.456Z",
      "width": 1920,
      "height": 3000,
      "file_size_bytes": 245760,
      "capture_mode": "fullpage",
      "format": "png"
    }
  },
  "schema_version": "1.2",
  "session": {
    "session_id": "fcb2ef5d-da54-4e75-9ede-8475c6dcbc08",
    "status": "active",
    "browser_type": "chromium"
  },
  "timing": {
    "initialization_ms": 1769,
    "navigation_ms": 2353,
    "search_ms": 8677,
    "snapshot_ms": 125,
    "total_ms": 12865
  }
}
```

## File System Contract

### Directory Structure

```
data/snapshots/
├── {snapshot_name}.json           # Snapshot metadata
├── html/                          # HTML files (existing)
│   └── {snapshot_name}.html
└── screenshots/                   # Screenshot files (new)
    └── {snapshot_name}.png
```

### File Naming Convention

**Pattern**: `{snapshot_base_name}.png`

**Rules**:
- Must match parent JSON snapshot base name exactly
- Must use `.png` extension
- Must be valid filename for target operating system
- Must be unique within screenshots directory

### File Operations

| Operation | Success Condition | Error Handling |
|-----------|-------------------|----------------|
| Create screenshots directory | Directory exists or created successfully | Log error, continue without screenshot |
| Save screenshot file | File written successfully | Log error, continue with JSON only |
| Verify screenshot file | File exists and readable | Log warning, continue with JSON |
| Get file metadata | File stats retrieved successfully | Use default values, log warning |

## Performance Contract

### Timing Requirements

| Operation | Maximum Time | Measurement |
|-----------|--------------|-------------|
| Screenshot capture | 30 seconds | From API call to file save |
| File write operation | 10 seconds | From data to disk write |
| Metadata collection | 5 seconds | File stats and dimensions |
| Total snapshot overhead | 45 seconds | Including existing operations |

### Resource Limits

| Resource | Limit | Monitoring |
|-----------|-------|------------|
| Screenshot file size | 10MB recommended | File size check |
| Memory usage | 50MB peak | Memory monitoring |
| Disk space | 1GB available | Space check |
| Concurrent captures | 5 maximum | Throttling |

## Error Handling Contract

### Error Categories

#### Recoverable Errors
- Screenshot capture timeout
- Temporary file system issues
- Browser rendering delays
- Network connectivity issues

**Handling**: Retry with exponential backoff, max 3 attempts

#### Non-Recoverable Errors
- Permission denied
- Disk space full
- Invalid screenshot mode
- Browser not available

**Handling**: Log error, continue with metadata-only snapshot

#### Degraded Operation
- Large screenshot files
- Slow capture performance
- Quality reduction needed

**Handling**: Adjust settings, log performance warnings

### Error Response Format

```python
class ScreenshotCaptureError(Exception):
    """Base exception for screenshot capture errors"""
    pass

class ScreenshotTimeoutError(ScreenshotCaptureError):
    """Screenshot capture timed out"""
    pass

class ScreenshotFileError(ScreenshotCaptureError):
    """File system error during screenshot operations"""
    pass
```

## Integration Contract

### Browser Lifecycle Integration

#### Pre-conditions
- Browser session must be active
- Page must be loaded completely
- Playwright page object must be available

#### Post-conditions
- Screenshot file created (if successful)
- JSON snapshot updated with screenshot metadata
- Original snapshot functionality preserved

#### Side Effects
- Additional disk space usage for screenshot files
- Increased snapshot capture time
- Additional file system operations

### Backward Compatibility

#### Version Compatibility
- v1.0 snapshots: Compatible (no screenshot field)
- v1.1 snapshots: Compatible (no screenshot field)
- v1.2 snapshots: Full screenshot support

#### API Compatibility
- Existing `capture_snapshot()` calls work unchanged
- New parameters are optional with sensible defaults
- Return value format unchanged

#### Data Compatibility
- Existing snapshot consumers continue to work
- New consumers handle optional screenshot field
- Schema version indicates feature availability

## Validation Contract

### Input Validation

| Parameter | Validation | Error Response |
|-----------|------------|----------------|
| `capture_screenshot` | Boolean type | Default to True |
| `screenshot_mode` | Enum value | Default to "fullpage" |
| `screenshot_quality` | 1-100 range | Default to 90 |

### Output Validation

| Field | Validation | Error Handling |
|-------|------------|----------------|
| `filepath` | Valid relative path | Use placeholder, log error |
| `width` | Positive integer | Use 0, log error |
| `height` | Positive integer | Use 0, log error |
| `file_size_bytes` | Positive integer | Use 0, log error |
| `capture_mode` | Valid enum | Use "fullpage", log error |

### Schema Validation

- JSON schema validation for output structure
- Type checking for all fields
- Required field validation
- Enum value validation
- Pattern matching for file paths

## Configuration Contract

### Default Settings

```python
DEFAULT_SCREENSHOT_CONFIG = {
    "capture_enabled": True,
    "mode": "fullpage",
    "quality": 90,
    "max_file_size_mb": 10,
    "timeout_seconds": 30,
    "retry_attempts": 3
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SCREENSHOT_CAPTURE_ENABLED` | "true" | Enable/disable screenshot capture |
| `SCREENSHOT_DEFAULT_MODE` | "fullpage" | Default capture mode |
| `SCREENSHOT_QUALITY` | "90" | Default PNG quality |
| `SCREENSHOT_MAX_SIZE_MB` | "10" | Maximum screenshot file size |

### Configuration Validation

- Environment variables validated on startup
- Invalid values logged and defaults applied
- Configuration changes require restart
- Runtime configuration updates supported for some settings
