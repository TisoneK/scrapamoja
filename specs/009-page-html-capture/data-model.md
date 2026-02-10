# Data Model: Page HTML Capture and Storage in Snapshots

**Feature**: 009-page-html-capture  
**Date**: 2025-01-29  
**Schema Version**: 1.1 (extension of existing 1.0)

## Core Entities

### PageSnapshot (Extended)

Represents a complete page capture including metadata and HTML file reference.

**Fields**:
```json
{
  "schema_version": "1.1",
  "captured_at": "ISO 8601 timestamp",
  "page": {
    "title": "string",
    "url": "string", 
    "content_length": "integer",
    "html_file": "string",           // NEW: relative path to HTML file
    "content_hash": "string"          // NEW: SHA-256 hash of HTML content
  },
  "session": {
    "session_id": "string",
    "status": "string",
    "browser_type": "string"
  },
  "timing": {
    "initialization_ms": "integer",
    "navigation_ms": "integer", 
    "search_ms": "integer",
    "total_ms": "integer"
  }
}
```

**Validation Rules**:
- `html_file`: Must be valid relative path, file must exist
- `content_hash`: Must be valid SHA-256 hash (64 hex characters)
- `content_length`: Must match actual HTML file size
- Backward compatibility: All existing fields unchanged

### HTMLFile

Represents the separate HTML file containing captured page content.

**File Structure**:
```
data/snapshots/html/
├── 20250129_143022_abc123def456.html
├── 20250129_143045_789ghi012jkl.html
└── ...
```

**Naming Convention**: `{timestamp}_{session_id}_{hash_prefix}.html`

**Content**:
- Raw HTML content from `page.content()`
- UTF-8 encoding
- No modifications or preprocessing

**Metadata** (embedded in filename):
- `timestamp`: ISO 8601 datetime (YYYYMMDD_HHMMSS)
- `session_id`: First 8 characters of browser session ID
- `hash_prefix`: First 12 characters of SHA-256 content hash

### ContentHash

Represents integrity verification data for HTML content.

**Format**: SHA-256 hash (64 hexadecimal characters)

**Generation**: `hashlib.sha256(html_content.encode('utf-8')).hexdigest()`

**Validation**: Hash verification on file load, corruption detection

## State Transitions

### Snapshot Creation Flow

```
1. Page Loaded → 2. HTML Captured → 3. Hash Generated → 4. File Written → 5. JSON Updated → 6. Snapshot Complete
```

**Error States**:
- HTML capture failure → Continue with metadata-only snapshot
- File write failure → Log error, continue with metadata-only
- Hash generation failure → Log error, continue without hash

### File Lifecycle

```
Created → Verified → Used → Optional Cleanup
```

**Cleanup Strategy**: Manual cleanup (not automated to preserve data)

## Relationships

```
PageSnapshot (1) ←→ (1) HTMLFile
PageSnapshot (1) ←→ (1) ContentHash
BrowserSession (1) ←→ (N) PageSnapshot
```

## Data Constraints

### Size Limits
- HTML file: < 50MB per file (configurable)
- Combined snapshot + HTML: < 10MB for 95% of typical pages
- Directory size: Monitored, alerts on excessive growth

### Encoding
- HTML files: UTF-8
- JSON snapshots: UTF-8
- Hash values: Hexadecimal (ASCII)

### Naming Constraints
- HTML filenames: Alphanumeric + underscores only
- Path separators: Forward slash (cross-platform compatible)
- Case sensitivity: Preserved (filesystem dependent)

## Integration Points

### Existing BrowserSession
- No changes required
- Uses existing `session_id` for HTML file naming
- Leverages existing error handling patterns

### Existing Snapshot Directory
- Extends `data/snapshots/` structure
- Adds `html/` subdirectory
- Maintains existing JSON file organization

### Existing Error Handling
- Graceful degradation on HTML capture failures
- Structured logging with correlation IDs
- Continues existing snapshot creation flow

## Backward Compatibility

### Schema Compatibility
- Existing schema 1.0 consumers ignore new fields
- New schema 1.1 consumers handle both formats
- No breaking changes to existing functionality

### File Compatibility
- Existing snapshots without HTML files continue to work
- New snapshots with HTML files provide enhanced functionality
- Mixed environment supported during transition

## Performance Considerations

### File I/O
- Asynchronous file operations
- Stream writing for large HTML content
- Progress monitoring for long operations

### Memory Usage
- HTML content not kept in memory after file write
- Hash generation uses streaming for large files
- Garbage collection friendly design

### Disk Usage
- Configurable size limits
- Cleanup utilities (manual)
- Storage monitoring and alerts
