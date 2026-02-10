# Quickstart Guide: Page HTML Capture and Storage in Snapshots

**Feature**: 009-page-html-capture  
**Date**: 2025-01-29  
**Prerequisites**: Browser lifecycle system, Playwright, Python 3.11+

## Overview

This feature extends the existing browser lifecycle snapshot system to capture complete HTML content as separate files with JSON references. This enables offline testing, verification, and complete page state preservation.

## Key Changes

### Before (Schema 1.0)
```json
{
  "schema_version": "1.0",
  "page": {
    "title": "Python (programming language) - Wikipedia",
    "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
    "content_length": 4232
  }
}
```

### After (Schema 1.1)
```json
{
  "schema_version": "1.1",
  "page": {
    "title": "Python (programming language) - Wikipedia",
    "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
    "content_length": 4232,
    "html_file": "html/20250129_143022_abc123def456.html",
    "content_hash": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"
  }
}
```

## File Structure

```
data/snapshots/
├── wikipedia_search_20250129_143022.json    # Metadata snapshot
└── html/
    └── 20250129_143022_abc123def456.html   # HTML content
```

## Implementation Steps

### Step 1: Extend capture_snapshot() Method

Modify the existing `capture_snapshot()` method in `examples/browser_lifecycle_example.py`:

```python
async def capture_snapshot(self) -> Optional[str]:
    """Extended to capture HTML content as separate file"""
    stage_start = time.time()
    print("\n" + "=" * 60)
    print("STAGE 4: Capture Page Snapshot")
    print("=" * 60)
    
    try:
        print("  * Capturing page content...")
        # Get page content through Playwright
        content = await self.page.content()
        title = await self.page.title()
        url = self.page.url
        
        # NEW: Generate content hash
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        # NEW: Create HTML file
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        session_prefix = self.session.session_id[:8]
        hash_prefix = content_hash[:12]
        html_filename = f"{timestamp}_{session_prefix}_{hash_prefix}.html"
        
        # NEW: Create html subdirectory if needed
        html_dir = self.snapshot_dir / "html"
        html_dir.mkdir(exist_ok=True)
        
        # NEW: Write HTML file
        html_filepath = html_dir / html_filename
        print(f"  * Writing HTML content to {html_filepath}...")
        with open(html_filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        print("  * Building snapshot metadata...")
        # Create snapshot with schema versioning
        snapshot_data = {
            "schema_version": "1.1",  # Updated schema version
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "page": {
                "title": title,
                "url": url,
                "content_length": len(content),
                "html_file": f"html/{html_filename}",  # NEW: HTML file reference
                "content_hash": content_hash           # NEW: Content hash
            },
            "session": {
                "session_id": self.session.session_id,
                "status": self.session.status.value,
                "browser_type": self.session.configuration.browser_type.value
            },
            "timing": {
                "initialization_ms": int(self.stage_times.get("initialization", 0) * 1000),
                "navigation_ms": int(self.stage_times.get("navigation", 0) * 1000),
                "search_ms": int(self.stage_times.get("search", 0) * 1000),
                "total_ms": int((time.time() - self.start_time) * 1000)
            }
        }
        
        # Generate timestamped filename for JSON
        json_filename = f"wikipedia_search_{timestamp}.json"
        json_filepath = self.snapshot_dir / json_filename
        
        print(f"  * Writing snapshot to {json_filepath}...")
        # Write snapshot to disk
        with open(json_filepath, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, indent=2)
        
        elapsed = time.time() - stage_start
        self.stage_times["snapshot"] = elapsed
        
        print(f"  [PASS] Snapshot saved in {elapsed:.2f}s")
        print(f"    - JSON: {json_filepath.name}")
        print(f"    - HTML: {html_filename}")
        print(f"    - Title: {title}")
        print(f"    - Size: {len(content)} bytes")
        
        return str(json_filepath)
        
    except Exception as e:
        # NEW: Graceful degradation for HTML capture failures
        print(f"  [WARN] HTML capture failed: {e}")
        print("  * Continuing with metadata-only snapshot...")
        
        # Fallback to original implementation
        # ... (original code here)
        
        return str(json_filepath)
```

### Step 2: Add Required Imports

Add these imports to the top of the file:

```python
import hashlib  # NEW: For content hashing
```

### Step 3: Test the Implementation

Run the example to verify HTML capture works:

```bash
python -m examples.browser_lifecycle_example
```

Expected output:
```
  * Writing HTML content to data/snapshots/html/20250129_143022_abc123def456.html...
  * Writing snapshot to data/snapshots/wikipedia_search_20250129_143022.json...
  [PASS] Snapshot saved in 1.23s
    - JSON: wikipedia_search_20250129_143022.json
    - HTML: 20250129_143022_abc123def456.html
    - Title: Python (programming language) - Wikipedia
    - Size: 4232 bytes
```

## Usage Examples

### Loading HTML Content for Offline Testing

```python
import json
from pathlib import Path

def load_snapshot_with_html(snapshot_path: str):
    """Load snapshot and HTML content for offline testing"""
    with open(snapshot_path, 'r') as f:
        snapshot = json.load(f)
    
    # Load HTML content if available
    html_content = None
    if 'html_file' in snapshot.get('page', {}):
        html_path = Path(snapshot_path).parent / snapshot['page']['html_file']
        if html_path.exists():
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
    
    return snapshot, html_content

# Usage
snapshot, html = load_snapshot_with_html('data/snapshots/wikipedia_search_20250129_143022.json')
if html:
    print(f"Loaded HTML content: {len(html)} bytes")
    # Use html_content for offline testing or verification
```

### Verifying Content Integrity

```python
import hashlib

def verify_snapshot_integrity(snapshot_path: str) -> bool:
    """Verify HTML file matches stored hash"""
    with open(snapshot_path, 'r') as f:
        snapshot = json.load(f)
    
    page_data = snapshot.get('page', {})
    if 'html_file' not in page_data or 'content_hash' not in page_data:
        return True  # No HTML content to verify
    
    html_path = Path(snapshot_path).parent / page_data['html_file']
    if not html_path.exists():
        return False
    
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    calculated_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
    stored_hash = page_data['content_hash']
    
    return calculated_hash == stored_hash

# Usage
is_valid = verify_snapshot_integrity('data/snapshots/wikipedia_search_20250129_143022.json')
print(f"Snapshot integrity: {'Valid' if is_valid else 'Invalid'}")
```

### Loading HTML in Browser

```python
from playwright.async_api import async_playwright

async def load_html_in_browser(html_file_path: str):
    """Load captured HTML file in browser for testing"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Load HTML file
        await page.goto(f"file://{html_file_path}")
        
        # Verify page loaded correctly
        title = await page.title()
        print(f"Page title: {title}")
        
        await browser.close()

# Usage
import asyncio
html_path = "data/snapshots/html/20250129_143022_abc123def456.html"
asyncio.run(load_html_in_browser(html_path))
```

## Error Handling

### Common Scenarios

1. **HTML Capture Failure**: System continues with metadata-only snapshot
2. **File Write Permission Error**: Logs error, continues with metadata
3. **Disk Space Insufficient**: Logs error, continues with metadata
4. **Hash Generation Failure**: Logs error, continues without hash

### Monitoring

Monitor these log messages for issues:
- `[WARN] HTML capture failed: ...`
- `[ERROR] HTML file write failed: ...`
- `[ERROR] Hash generation failed: ...`

## Backward Compatibility

### Existing Consumers
- Continue to work unchanged (ignore new fields)
- Can gradually adopt HTML file features when ready

### Migration Path
1. Deploy new version with HTML capture
2. Existing snapshots continue to work
3. New snapshots include HTML files
4. Consumers can optionally use HTML content

## Performance Considerations

### Expected Overhead
- HTML capture: < 5 seconds additional
- File write: < 2 seconds additional  
- Hash generation: < 1 second additional
- Total: < 10% performance impact

### Size Impact
- Typical pages: < 10MB total (JSON + HTML)
- Large pages: Up to 50MB HTML file
- Disk usage: Monitor growth in `data/snapshots/html/`

## Troubleshooting

### Common Issues

1. **HTML file not found**: Check `html_file` path in JSON
2. **Hash mismatch**: File may be corrupted, recapture
3. **Permission denied**: Check write permissions to snapshot directory
4. **Large file size**: Check if page is unusually large

### Debug Commands

```bash
# Check snapshot structure
cat data/snapshots/wikipedia_search_20250129_143022.json | jq .

# Verify HTML file exists
ls -la data/snapshots/html/

# Check file sizes
du -h data/snapshots/
```

## Next Steps

1. **Test Implementation**: Run the example and verify HTML capture
2. **Validate Integrity**: Use verification functions to ensure data consistency
3. **Update Consumers**: Modify any tools that use snapshots to leverage HTML content
4. **Monitor Performance**: Track overhead and disk usage in production
5. **Document Usage**: Update team documentation on new HTML capture capabilities
