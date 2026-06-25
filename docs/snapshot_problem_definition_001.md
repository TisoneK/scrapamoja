# Snapshot System Redesign: Context-Aware Bundle Architecture

Your instinct is correct. What you're describing is a shift from a flat artifact dump to a context-aware snapshot bundle. That will significantly improve:

- **Retrieval speed**
- **Failure traceability** 
- **Debug specificity**
- **Storage organization**
- **Operational clarity**

Let's redesign this properly.

## 1️⃣ Problem With Current Structure

### Current structure:
```
data/snapshots/
├── {page}_{session}_{timestamp}.json
├── screenshots/
├── html/
```

### Issues:
- No contextual grouping (site/module/function)
- Hard to trace which scraper component produced it
- Weak multi-tenant isolation
- HTML naming mismatch
- Scaling risk (too many files in one directory)

This becomes painful when you scale to 10k+ snapshots.

## 2️⃣ Proposed Context-Aware Snapshot Bundle

### New Structure
```
data/snapshots/
└── <site>/
    └── <module_or_component>/
        └── <YYYYMMDD>/
            └── <HHMMSS_micro>_<session_id>/
                ├── meta.json
                ├── html/
                │   ├── fullpage.html
                │   └── element_{selector_hash}.html
                ├── screenshots/
                │   └── viewport.png
                └── logs/
                    ├── console.json
                    └── network.json
```

### Example
```
data/snapshots/
└── flashscore/
    └── basketball_match_list/
        └── 20260213/
            └── 113753_839201/
                ├── meta.json
                ├── html/
                ├── screenshots/
                └── logs/
```

## 3️⃣ Why This Is Superior

### ✔ Isolation by Site
No cross-site collision.

### ✔ Isolation by Module
You can debug:
- `match_list`
- `match_details` 
- `odds_extractor`

independently.

### ✔ Date Partitioning
Prevents directory overload. Filesystems degrade when thousands of files exist in one folder.

### ✔ Snapshot as Atomic Unit
Each snapshot becomes a self-contained forensic bundle.

This mirrors how:
- Kubernetes logs are partitioned
- Observability tools structure trace data
- Distributed systems isolate failures

## 4️⃣ HTML Capture Upgrade: Element + Full Page

This is an important optimization. Instead of always capturing just one type, make it robust to capture both when needed.

### Dual Capture Strategy
```python
class SnapshotMode(Enum):
    FULL_PAGE = "full"
    SELECTOR = "selector" 
    MINIMAL = "minimal"
    BOTH = "both"  # Capture both full page and element
```

### File Naming Convention
- **Full page**: `fullpage.html`
- **Element**: `element_{selector_hash}.html`

The selector hash ensures:
- **Uniqueness**: Different selectors get different files
- **Traceability**: You can map element files back to their selectors
- **Relationship**: `fullpage.html` and `element_{hash}.html` clearly belong together

### Capture Implementation
```python
# Full page capture
full_html = await page.content()

# Element capture with hash naming
selector = ".match-list"
element = await page.query_selector(selector)
element_html = await element.inner_html()
selector_hash = hashlib.md5(selector.encode()).hexdigest()[:8]
element_filename = f"element_{selector_hash}.html"
```

### Benefits of Dual Approach
- **Context**: Full page shows the overall structure
- **Focus**: Element capture shows the specific area of interest
- **Debugging**: Compare element behavior within full page context
- **Diffing**: Smaller element files are easier to diff when debugging selector issues

This makes snapshots:
- **More comprehensive** (both macro and micro view)
- **Better organized** (clear file relationships)
- **Easier to debug** (targeted element analysis with full context)

## 5️⃣ Performance Optimizations

### A. Conditional Artifact Capture

Add flags:
```python
capture_html=True
capture_screenshot=False
capture_network=False
capture_console=False
```

**Production mode:**
- Only capture on failure
- Only capture selector HTML

**Debug mode:**
- Capture everything

### B. Async Parallel Saving

Instead of sequential:
```python
await save_json()
await save_html()
await save_png()
```

Do:
```python
await asyncio.gather(
    save_json(),
    save_html(),
    save_png()
)
```

Improves speed.

### C. Deduplication via Content Hash

If:
```python
html_hash == last_snapshot_hash
```

→ Skip writing HTML file. Only update metadata.

This dramatically reduces disk usage.

## 6️⃣ Advanced Specificity: Component Identity

You mentioned: `snapshot/<site><module/function><date>_<time>/`

**Do not mix them into a single string.**

Instead structure metadata explicitly:
```python
snapshot_context = {
    "site": "flashscore",
    "module": "basketball",
    "component": "match_list",
    "function": "extract_live_matches"
}
```

Then use this to build folder hierarchy.

This allows future:
- Snapshot filtering by component
- Metrics per module
- Failure heatmaps

## 7️⃣ Recommended SnapshotManager Refactor

Your `capture_snapshot()` signature should evolve to:
```python
async def capture_snapshot(
    self,
    page,
    site: str,
    module: str,
    component: str,
    session_id: str,
    mode: SnapshotMode = SnapshotMode.SELECTOR,
    selector: Optional[str] = None,
    capture_full_page: bool = False,
    capture_network: bool = False,
    capture_console: bool = False,
):
```

This removes ambiguity and enforces specificity.

## 8️⃣ Make Snapshots Event-Driven

Instead of manual calls everywhere, integrate with:
- Selector failure handler
- Retry exhaustion
- Timeout events
- Extraction mismatch

Example:
```python
if selector_result.matched_count == 0:
    await snapshot_manager.capture_snapshot(...)
```

Now snapshots become automatic resilience artifacts.

## 9️⃣ Long-Term: Snapshot Intelligence Layer

If you want scrapamoja to evolve further, add:
- Snapshot diff comparison
- Selector drift detection
- DOM mutation alerts
- Performance regression tracking

Now your system becomes self-monitoring.

## 🔟 Final Architecture Verdict

Your proposed redesign is:

### ✔ More scalable
### ✔ More maintainable  
### ✔ More searchable
### ✔ More production-oriented
### ✔ More performant
### ✔ More future-proof

**This is the correct direction.**
