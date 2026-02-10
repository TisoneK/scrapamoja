# Data Model: Core Module Refactoring Fix

**Feature**: `011-fix-snapshot-refactor`  
**Created**: 2025-01-29  
**Status**: Draft

## Entity Definitions

### DOMSnapshot (Existing Entity - No Changes Required)

**Purpose**: Represents a complete DOM snapshot with metadata for debugging and failure analysis

**Attributes**:
- `page_id: str` - Unique identifier for the page/session
- `url: Optional[str]` - Page URL at time of capture
- `timestamp: Optional[float]` - Unix timestamp of capture
- `title: Optional[str]` - Page title at time of capture
- `content: Optional[str]` - HTML content of the page
- `selector_results: Optional[Dict[str, Any]]` - Results of custom selector evaluations
- `network_requests: Optional[List[Dict[str, Any]]]` - Network request logs
- `console_logs: Optional[List[Dict[str, Any]]]` - Console log entries
- `screenshot_path: Optional[str]` - **FIXED**: Path to screenshot file (properly scoped)
- `html_metadata: Optional[Dict[str, Any]]` - HTML file capture metadata
- `screenshot_metadata: Optional[Dict[str, Any]]` - Screenshot capture metadata

**Validation Rules**:
- `page_id` is required and non-empty
- `timestamp` defaults to current time if not provided
- All optional fields default to None or empty collections
- `screenshot_path` is properly derived from `screenshot_metadata["filepath"]`

### ScreenshotMetadata (Existing Structure - No Changes Required)

**Purpose**: Rich metadata for screenshot capture operations

**Structure**:
```python
{
    "filepath": str,           # Relative filename (e.g., "page_id_1234567890.png")
    "captured_at": str,        # ISO 8601 timestamp with timezone
    "width": int,             # Image width in pixels
    "height": int,            # Image height in pixels
    "file_size_bytes": int,   # File size in bytes
    "capture_mode": str,      # "fullpage" or "viewport"
    "format": str            # Always "png"
}
```

**Validation Rules**:
- `filepath` is required and non-empty
- `captured_at` must be valid ISO 8601 format
- `width` and `height` are non-negative integers
- `file_size_bytes` is positive integer
- `capture_mode` must be "fullpage" or "viewport"
- `format` must be "png"

### HTMLMetadata (Existing Structure - No Changes Required)

**Purpose**: Rich metadata for HTML file capture operations

**Structure**:
```python
{
    "filepath": str,           # Relative filename (e.g., "html/page_id_1234567890.html")
    "captured_at": str,        # ISO 8601 timestamp with timezone
    "file_size_bytes": int,   # File size in bytes
    "content_length": int,    # Content string length
    "content_hash": str,      # SHA-256 hash of content
    "format": str            # Always "html"
}
```

**Validation Rules**:
- `filepath` is required and non-empty
- `captured_at` must be valid ISO 8601 format
- `file_size_bytes` and `content_length` are positive integers
- `content_hash` must be valid SHA-256 hex string
- `format` must be "html"

## Variable Scope Model

### Method Scope Variables in `capture_snapshot()`

**Properly Scoped Variables**:
- `screenshot_metadata: Optional[dict]` - Local variable, defined line 121
- `html_metadata: Optional[dict]` - Local variable, defined line 126
- `snapshot: DOMSnapshot` - Local variable, defined line 128

**Fixed Variable Access**:
- **Before Fix**: `screenshot_path` (undefined)
- **After Fix**: `screenshot_metadata["filepath"] if screenshot_metadata else None`

## State Transitions

### DOMSnapshot Lifecycle

1. **Initialization**: DOMSnapshot object created with all parameters
2. **Metadata Population**: Screenshot and HTML metadata captured asynchronously
3. **File Storage**: Snapshot saved to JSON file with all metadata
4. **Loading**: Snapshot can be loaded from file for analysis
5. **Cleanup**: Old snapshots can be automatically cleaned up

### Error Handling States

1. **Screenshot Failure**: `screenshot_metadata` remains None, logging continues
2. **HTML Failure**: `html_metadata` remains None, logging continues
3. **General Failure**: Exception raised with structured logging

## Integration Contracts

### Browser Session Integration

**Input**: Playwright Page object
**Output**: DOMSnapshot with rich metadata
**Error Handling**: BrowserError with descriptive messages

### File System Integration

**Storage Location**: `data/snapshots/` directory
**File Naming**: `{page_id}_{timestamp}.{extension}`
**Subdirectories**: `html/` for HTML files
**Cleanup**: Automatic cleanup based on age

### JSON Serialization

**Schema**: Version-controlled JSON structure
**Encoding**: UTF-8 with ensure_ascii=False
**Formatting**: Pretty-printed with 2-space indentation
**Compatibility**: Backward compatible with existing snapshots

## Validation Rules Summary

### Critical Validations
- All required fields must be present before object creation
- File paths must be valid relative paths
- Timestamps must be in correct format
- Metadata structures must match expected schemas

### Graceful Degradation
- Screenshot capture failure should not prevent HTML capture
- HTML capture failure should not prevent screenshot capture
- Missing optional metadata should be handled gracefully

### Error Boundaries
- Individual capture operations are isolated
- One failure should not cascade to other operations
- All errors are logged with correlation IDs
