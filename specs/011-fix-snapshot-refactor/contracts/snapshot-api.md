# API Contracts: Core Module Refactoring Fix

**Feature**: `011-fix-snapshot-refactor`  
**Created**: 2025-01-29  
**Status**: Draft

## Module API Contract

### DOMSnapshotManager Class

#### Public Methods

##### `capture_snapshot()`
**Purpose**: Capture comprehensive DOM snapshot with rich metadata
**Signature**:
```python
async def capture_snapshot(
    self,
    page: Page,
    page_id: str,
    include_screenshot: bool = True,
    include_html_file: bool = True,
    screenshot_mode: str = "fullpage",
    include_network: bool = True,
    include_console: bool = True,
    custom_selectors: Optional[List[str]] = None
) -> DOMSnapshot
```

**Parameters**:
- `page: Page` - Playwright page object (required)
- `page_id: str` - Unique page identifier (required)
- `include_screenshot: bool` - Capture screenshot flag (default: True)
- `include_html_file: bool` - Capture HTML file flag (default: True)
- `screenshot_mode: str` - Screenshot mode: "fullpage" or "viewport" (default: "fullpage")
- `include_network: bool` - Include network requests (default: True)
- `include_console: bool` - Include console logs (default: True)
- `custom_selectors: Optional[List[str]]` - Custom CSS selectors to evaluate (default: None)

**Returns**: `DOMSnapshot` object with all captured data and metadata

**Exceptions**:
- `BrowserError` - When Playwright is not available or capture fails

**Behavior Changes**:
- **FIXED**: Logging statement now correctly references `screenshot_metadata["filepath"]`
- No breaking changes to method signature or return value

##### `load_snapshot()`
**Purpose**: Load snapshot from file
**Signature**:
```python
async def load_snapshot(
    self,
    page_id: str,
    timestamp: Optional[float] = None
) -> Optional[DOMSnapshot]
```

**Parameters**:
- `page_id: str` - Page identifier to load
- `timestamp: Optional[float]` - Specific timestamp to load (default: most recent)

**Returns**: `DOMSnapshot` object or None if not found

**Behavior**: No changes required

##### `list_snapshots()`
**Purpose**: List available snapshots
**Signature**:
```python
def list_snapshots(
    self,
    page_id: Optional[str] = None
) -> List[Dict[str, Any]]
```

**Parameters**:
- `page_id: Optional[str]` - Filter by specific page ID (default: all)

**Returns**: List of snapshot metadata dictionaries

**Behavior**: No changes required

##### `cleanup_old_snapshots()`
**Purpose**: Clean up old snapshot files
**Signature**:
```python
async def cleanup_old_snapshots(
    self,
    max_age_days: int = 7
) -> int
```

**Parameters**:
- `max_age_days: int` - Maximum age in days (default: 7)

**Returns**: Number of deleted files

**Behavior**: No changes required

### DOMSnapshot Class

#### Constructor
**Purpose**: Create DOM snapshot object
**Signature**:
```python
def __init__(
    self,
    page_id: str,
    url: Optional[str] = None,
    timestamp: Optional[float] = None,
    title: Optional[str] = None,
    content: Optional[str] = None,
    selector_results: Optional[Dict[str, Any]] = None,
    network_requests: Optional[List[Dict[str, Any]]] = None,
    console_logs: Optional[List[Dict[str, Any]]] = None,
    screenshot_path: Optional[str] = None,
    html_metadata: Optional[Dict[str, Any]] = None,
    screenshot_metadata: Optional[Dict[str, Any]] = None
)
```

**Behavior**: No changes required

#### Methods

##### `to_dict()`
**Purpose**: Convert snapshot to dictionary
**Signature**:
```python
def to_dict() -> Dict[str, Any]
```

**Returns**: Dictionary representation of snapshot

**Behavior**: No changes required

## Internal API Contracts

### Screenshot Capture Method

#### `_capture_screenshot()`
**Purpose**: Capture screenshot with rich metadata
**Signature**:
```python
async def _capture_screenshot(
    self,
    page: Page,
    page_id: str,
    screenshot_mode: str = "fullpage"
) -> dict
```

**Returns**: Dictionary with screenshot metadata or None on failure

**Metadata Structure**:
```python
{
    "filepath": str,
    "captured_at": str,
    "width": int,
    "height": int,
    "file_size_bytes": int,
    "capture_mode": str,
    "format": str
}
```

**Behavior**: No changes required

### HTML Capture Method

#### `_capture_html_file()`
**Purpose**: Capture HTML content with rich metadata
**Signature**:
```python
async def _capture_html_file(
    self,
    page: Page,
    page_id: str,
    content: str
) -> dict
```

**Returns**: Dictionary with HTML metadata or None on failure

**Metadata Structure**:
```python
{
    "filepath": str,
    "captured_at": str,
    "file_size_bytes": int,
    "content_length": int,
    "content_hash": str,
    "format": str
}
```

**Behavior**: No changes required

## Error Handling Contracts

### Exception Types

#### BrowserError
**Purpose**: Browser-related operation failures
**Fields**:
- `code: str` - Error code (e.g., "PLAYWRIGHT_NOT_AVAILABLE", "SNAPSHOT_CAPTURE_FAILED")
- `message: str` - Human-readable error message

### Logging Contracts

#### Structured Logging
**Logger Name**: `browser.snapshots`
**Log Levels**:
- `INFO` - Successful operations
- `WARNING` - Non-critical failures (screenshot/HTML capture)
- `ERROR` - Critical failures (snapshot capture, file operations)

**Log Fields**:
- `page_id: str` - Page identifier for correlation
- `url: str` - Page URL (when available)
- `error: str` - Error message (for ERROR/WARNING levels)
- `error_type: str` - Exception type (for ERROR level)
- `screenshot: bool` - Whether screenshot was captured (FIXED: properly referenced)

## File System Contracts

### Directory Structure
```
data/snapshots/
├── {page_id}_{timestamp}.json    # Snapshot metadata
├── {page_id}_{timestamp}.png     # Screenshot files
└── html/
    └── {page_id}_{timestamp}.html # HTML files
```

### File Naming Conventions
- **JSON**: `{page_id}_{timestamp}.json`
- **PNG**: `{page_id}_{timestamp}.png`
- **HTML**: `html/{page_id}_{timestamp}.html`
- **Timestamp**: Unix timestamp (seconds since epoch)

### File Formats
- **JSON**: UTF-8 encoded, pretty-printed, 2-space indentation
- **PNG**: Standard PNG format for screenshots
- **HTML**: UTF-8 encoded HTML content

## Integration Contracts

### Browser Session Integration
**Required**: Playwright Page object with proper context
**Optional**: Network event listeners for request logging
**Optional**: Console event listeners for log capture

### JSON Schema Compatibility
**Current Version**: 1.2 (with screenshot and HTML metadata)
**Backward Compatibility**: Existing snapshots remain readable
**Forward Compatibility**: New fields are optional

### Performance Contracts
**Screenshot Capture**: < 5 seconds for typical pages
**HTML Capture**: < 1 second for typical pages
**JSON Serialization**: < 100ms for typical snapshots
**File I/O**: Non-blocking async operations

## Testing Contracts

### Unit Test Requirements
- Module imports without NameError or ImportError
- Variable references are properly scoped
- Metadata structures are correctly formatted
- Error handling works as expected

### Integration Test Requirements
- End-to-end snapshot capture works
- Screenshot and HTML files are created correctly
- JSON files contain proper metadata
- Cleanup operations work correctly

### Regression Test Requirements
- Existing functionality continues to work
- No breaking changes to public APIs
- Backward compatibility maintained
