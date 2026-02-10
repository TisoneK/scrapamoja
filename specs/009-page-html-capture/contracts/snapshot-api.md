# Snapshot API Contract: HTML File Capture Extension

**Feature**: 009-page-html-capture  
**Date**: 2025-01-29  
**API Version**: 1.1 (extension of existing 1.0)

## Extended Snapshot Interface

### capture_snapshot() Method Extension

**Existing Signature**:
```python
async def capture_snapshot(self) -> Optional[str]
```

**Extended Behavior**:
- Returns path to JSON snapshot file (unchanged)
- Creates HTML file alongside JSON snapshot
- Adds HTML file reference and hash to JSON content

**Input Parameters**: None (uses current page state)

**Return Value**: `Optional[str]` - Path to JSON snapshot file

**Error Handling**:
- HTML capture failures: Log warning, continue with metadata-only snapshot
- File write failures: Log error, continue with metadata-only snapshot
- Hash generation failures: Log error, continue without hash

## JSON Schema Extension

### Extended Page Object

```json
{
  "page": {
    "title": "string",
    "url": "string",
    "content_length": "integer",
    "html_file": "string",           // NEW: Relative path to HTML file
    "content_hash": "string"         // NEW: SHA-256 hash of HTML content
  }
}
```

### Field Specifications

#### html_file (NEW)
- **Type**: string
- **Format**: Relative path from snapshot directory
- **Example**: `"html/20250129_143022_abc123def456.html"`
- **Required**: No (graceful degradation)
- **Validation**: Path must exist, file must be readable

#### content_hash (NEW)
- **Type**: string
- **Format**: 64-character hexadecimal string
- **Example**: `"a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"`
- **Required**: No (graceful degradation)
- **Validation**: Valid SHA-256 hash, matches HTML file content

## File System Contract

### HTML File Structure

```
data/snapshots/html/
├── {timestamp}_{session_id}_{hash_prefix}.html
└── ...
```

### Naming Convention

**Pattern**: `{YYYYMMDD_HHMMSS}_{session_id}_{hash_prefix}.html`

**Components**:
- `timestamp`: 15-character datetime string
- `session_id`: First 8 characters of browser session ID
- `hash_prefix`: First 12 characters of SHA-256 content hash

**Example**: `20250129_143022_abc123def456.html`

### File Content Contract

**Encoding**: UTF-8
**Content**: Raw HTML from `page.content()`
**Size**: < 50MB (configurable limit)
**Line Endings**: Preserved from source

## Error Handling Contract

### Graceful Degradation Scenarios

#### HTML Capture Failure
```python
try:
    html_content = await page.content()
except Exception as e:
    logger.warning(f"HTML capture failed: {e}")
    # Continue with metadata-only snapshot
```

#### File Write Failure
```python
try:
    with open(html_filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
except (IOError, PermissionError) as e:
    logger.error(f"HTML file write failed: {e}")
    # Continue with metadata-only snapshot
```

#### Hash Generation Failure
```python
try:
    content_hash = hashlib.sha256(html_content.encode('utf-8')).hexdigest()
except Exception as e:
    logger.error(f"Hash generation failed: {e}")
    content_hash = None
    # Continue without hash
```

## Performance Contract

### Timing Requirements
- HTML capture: < 5 seconds for typical pages
- File write: < 2 seconds for < 10MB files
- Hash generation: < 1 second for < 50MB files
- Total overhead: < 10% vs metadata-only capture

### Resource Limits
- Memory usage: < 100MB additional during capture
- Disk I/O: Streaming for files > 5MB
- Concurrent operations: Single snapshot at a time

## Integration Contract

### BrowserSession Compatibility
- No changes to BrowserSession class
- Uses existing session_id for file naming
- Leverages existing error handling patterns

### Backward Compatibility
- Existing schema 1.0 consumers: Ignore new fields
- New schema 1.1 consumers: Handle both formats
- Mixed environment: Supported during transition

### Directory Structure
```
data/snapshots/
├── wikipedia_search_20250129_143022.json    # Existing JSON
├── html/
│   ├── 20250129_143022_abc123def456.html   # New HTML file
│   └── ...
└── ...
```

## Validation Contract

### Content Integrity
```python
def verify_html_integrity(json_snapshot: dict, html_file_path: str) -> bool:
    """Verify HTML file matches hash in JSON snapshot"""
    if 'content_hash' not in json_snapshot.get('page', {}):
        return True  # No hash to verify against
    
    with open(html_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    calculated_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
    stored_hash = json_snapshot['page']['content_hash']
    
    return calculated_hash == stored_hash
```

### File Existence Check
```python
def verify_html_file_exists(json_snapshot: dict, snapshot_dir: Path) -> bool:
    """Verify HTML file referenced in JSON exists"""
    if 'html_file' not in json_snapshot.get('page', {}):
        return True  # No HTML file referenced
    
    html_file_path = snapshot_dir / json_snapshot['page']['html_file']
    return html_file_path.exists() and html_file_path.is_file()
```

## Configuration Contract

### Size Limits
```python
HTML_MAX_SIZE = 50 * 1024 * 1024  # 50MB
SNAPSHOT_MAX_SIZE = 10 * 1024 * 1024  # 10MB for 95% of pages
```

### Directory Configuration
```python
SNAPSHOT_DIR = Path("data/snapshots")
HTML_SUBDIR = "html"
```

### Logging Configuration
```python
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
```

## Testing Contract

### Manual Validation Steps
1. Capture snapshot with HTML file
2. Verify JSON contains html_file reference
3. Verify HTML file exists at referenced path
4. Verify content_hash matches file content
5. Load HTML file in browser to verify rendering
6. Test graceful degradation scenarios

### Success Criteria
- HTML file created for 100% of successful captures
- Content hash verification passes for 99.9% of files
- File size limits enforced for all captures
- Backward compatibility maintained for existing consumers
