# Data Model: Screenshot Capture with Organized File Structure

**Created**: 2025-01-29  
**Purpose**: Entity definitions and data structures for screenshot capture feature

## Core Entities

### Screenshot

Represents a captured screenshot file with associated metadata.

**Fields**:
- `filepath` (string, required): Relative path to screenshot file (e.g., "screenshots/wikipedia_search_20260129_082735.png")
- `captured_at` (datetime, required): Timestamp when screenshot was captured (ISO 8601 format)
- `width` (integer, required): Screenshot width in pixels
- `height` (integer, required): Screenshot height in pixels
- `file_size_bytes` (integer, required): Size of screenshot file in bytes
- `capture_mode` (enum, required): Capture mode used ("fullpage" or "viewport")
- `format` (string, required): File format (always "png")

**Validation Rules**:
- `filepath` must end with ".png" extension
- `filepath` must be relative to snapshot directory
- `width` and `height` must be positive integers
- `file_size_bytes` must be positive integer
- `capture_mode` must be valid enum value
- `captured_at` must be valid ISO 8601 datetime

### ScreenshotMetadata

Contains structured information about screenshot capture settings and results.

**Fields**:
- `capture_settings` (object, required): Settings used for screenshot capture
  - `mode` (enum): "fullpage" or "viewport"
  - `quality` (integer, optional): Quality setting (1-100, default: 90)
  - `format` (string): Always "png"
- `capture_results` (object, required): Results of screenshot capture
  - `success` (boolean): Whether capture succeeded
  - `error_message` (string, optional): Error message if capture failed
  - `capture_duration_ms` (integer): Time taken to capture screenshot
- `file_info` (object, required): Information about saved file
  - `filename` (string): Base filename without path
  - `directory` (string): Directory path relative to snapshot root
  - `full_path` (string): Complete relative path from snapshot root

### CaptureMode

Enumeration of supported screenshot capture modes.

**Values**:
- `fullpage`: Capture entire page content including scrollable areas
- `viewport`: Capture only the visible browser viewport area

**Default**: `fullpage`

## Extended Snapshot Schema

### PageSnapshot Extension

Existing PageSnapshot entity extended with screenshot support.

**New Fields**:
```json
{
  "schema_version": "1.2",
  "page": {
    // ... existing page fields ...
    "screenshot": {
      "filepath": "screenshots/wikipedia_search_20260129_082735.png",
      "captured_at": "2025-01-29T12:30:45.123Z",
      "width": 1920,
      "height": 3000,
      "file_size_bytes": 245760,
      "capture_mode": "fullpage",
      "format": "png"
    }
  }
}
```

**Backward Compatibility**:
- Schema version updated from "1.1" to "1.2"
- Screenshot field is optional
- Existing v1.0 and v1.1 snapshots remain valid
- Screenshot capture defaults to disabled for compatibility

## File Structure

### Directory Organization

```
data/snapshots/
├── wikipedia_search_20260129_082735.json    # Snapshot metadata
├── html/                                    # HTML files (existing)
│   └── wikipedia_search_20260129_082735.html
└── screenshots/                             # Screenshot files (new)
    └── wikipedia_search_20260129_082735.png
```

### Naming Convention

**Pattern**: `{snapshot_base_name}.png`

**Examples**:
- `wikipedia_search_20260129_082735.png`
- `google_search_20260129_083045.png`

**Rules**:
- Must match parent JSON snapshot base name exactly
- Must use `.png` extension
- Must be unique within screenshots directory
- Must be valid filename for target operating system

## State Transitions

### Screenshot Capture Lifecycle

1. **Initiation**: Screenshot capture requested during snapshot creation
2. **Configuration**: Capture mode and settings applied
3. **Capture**: Playwright screenshot API executed
4. **Validation**: File created and metadata collected
5. **Storage**: File saved to screenshots directory
6. **Reference**: Filepath added to snapshot JSON
7. **Completion**: Capture process finished

### Error States

- **Capture Failed**: Screenshot API returned error
- **File Write Failed**: Unable to save screenshot file
- **Permission Denied**: No write access to screenshots directory
- **Disk Space Full**: Insufficient space for screenshot file
- **Invalid Path**: Screenshots directory path is invalid

## Data Relationships

### Snapshot-Screenshot Relationship

- **One-to-One**: Each snapshot can have at most one screenshot
- **Optional**: Screenshot is optional, snapshot can exist without it
- **Dependent**: Screenshot lifecycle depends on snapshot lifecycle
- **Referenced**: Screenshot referenced by relative filepath in snapshot JSON

### File System Dependencies

- **Directory Creation**: Screenshots directory created if missing
- **Path Resolution**: Relative paths resolved from snapshot directory
- **File Management**: Screenshots managed independently of JSON files
- **Cleanup**: Screenshots cleaned up when corresponding snapshots deleted

## Data Constraints

### File Size Limits

- **Maximum Recommended**: 10MB per screenshot file
- **Warning Threshold**: 5MB per screenshot file
- **Quality Adjustment**: Automatic quality reduction for large captures

### Dimension Limits

- **Minimum Width**: 320 pixels
- **Minimum Height**: 240 pixels
- **Maximum Practical**: 50,000 pixels (either dimension)
- **Recommended Range**: 800-4000 pixels for typical web pages

### Performance Constraints

- **Capture Timeout**: 30 seconds maximum
- **File Write Timeout**: 10 seconds maximum
- **Memory Usage**: Screenshot data streamed to disk
- **Concurrent Captures**: Limited to prevent resource exhaustion

## Validation Examples

### Valid Screenshot Object

```json
{
  "filepath": "screenshots/wikipedia_search_20260129_082735.png",
  "captured_at": "2025-01-29T12:30:45.123Z",
  "width": 1920,
  "height": 3000,
  "file_size_bytes": 245760,
  "capture_mode": "fullpage",
  "format": "png"
}
```

### Invalid Screenshot Object

```json
{
  "filepath": "screenshots/screenshot.jpg",  // Wrong extension
  "captured_at": "invalid-date",             // Invalid datetime
  "width": -100,                              // Negative dimension
  "height": 0,                                // Zero dimension
  "file_size_bytes": -1,                       // Negative size
  "capture_mode": "invalid",                   // Invalid mode
  "format": "jpg"                             // Wrong format
}
```

## Migration Considerations

### Schema Migration

- **v1.1 → v1.2**: Add optional screenshot field
- **Backward Compatibility**: Existing v1.1 consumers continue to work
- **Forward Compatibility**: New consumers handle missing screenshot field
- **Data Validation**: Validate screenshot data when present

### File System Migration

- **Directory Creation**: Screenshots directory created on first use
- **Existing Snapshots**: No impact on existing snapshot files
- **Cleanup Strategy**: Optional cleanup of orphaned screenshot files
