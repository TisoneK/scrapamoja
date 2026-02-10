# Research: Snapshot Timing and Telemetry Fixes

**Purpose**: Technical research and decision analysis for snapshot JSON timing fixes and telemetry method resolution
**Created**: 2025-01-29
**Feature**: 014-snapshot-timing-fix

## Issue Analysis

### Issue 1: Snapshot JSON Timing Bug

**Current Implementation Analysis**:
- Location: `examples/browser_lifecycle_example.py` in `run()` method
- Execution order: `capture_snapshot()` → `replay_snapshot()` → `verify_integrity()` → `snapshot_metadata_write()`
- Problem: JSON persistence happens after replay attempts

**Root Cause Investigation**:
```python
# Current problematic flow in browser_lifecycle_example.py
snapshot_file = await self.capture_snapshot()  # Captures HTML/screenshot, but not JSON

# Replay attempts happen here
await self.demonstrate_offline_html_replay(snapshot_file)
await self.demonstrate_content_integrity_verification(snapshot_file)

# JSON metadata written too late
# This happens in the background after replay attempts
```

**Decision**: Move JSON persistence to be synchronous within `capture_snapshot()` method
**Rationale**: Ensures metadata availability before any consumer operations
**Alternatives considered**:
- Async persistence with await: Would require major refactoring of all consumers
- Separate persistence step: Adds complexity and potential for missed calls
- Background persistence with polling: Unreliable and adds latency

### Issue 2: Missing Telemetry Method

**Current Implementation Analysis**:
- Location: `examples/browser_lifecycle_example.py` line ~1014
- Error: `'BrowserLifecycleExample' object has no attribute 'display_telemetry_summary'`
- Current workaround: Commented out call with placeholder message

**Decision**: Remove the method call entirely (Option A)
**Rationale**: Cleaner than stub method; telemetry is not part of public API for this example
**Alternatives considered**:
- Stub method implementation: Adds unnecessary code
- Full telemetry implementation: Out of scope for this fix
- Conditional call based on availability: Adds complexity

### Issue 3: Playwright Timeout Warnings

**Current Implementation Analysis**:
- Warning: `Timeout 1500ms exceeded waiting for .mw-search-result-heading a`
- Cause: Snapshot module runs search-page waits after navigation to article page
- Impact: Log noise, no functional impact

**Decision**: Gate waits by page type (optional fix)
**Rationale**: Eliminates irrelevant waits on article pages
**Alternatives considered**:
- Remove all waits: Could break legitimate search result captures
- Increase timeout: Doesn't address root cause
- Ignore warnings: Doesn't improve developer experience

## Technical Implementation Details

### Snapshot JSON Persistence Fix

**Target Component**: `src/browser/snapshot.py` - `DOMSnapshotManager`
**Required Changes**:
1. Modify `capture()` method to persist JSON synchronously
2. Ensure `persist()` method completes before returning
3. Maintain backward compatibility with existing API

**Implementation Strategy**:
```python
# New approach in DOMSnapshotManager.capture()
async def capture(self, page, snapshot_id=None):
    # Capture HTML and screenshot (existing)
    html_content = await page.content()
    screenshot_path = await self._capture_screenshot(page)
    
    # Create snapshot metadata
    snapshot = Snapshot(
        id=snapshot_id or self._generate_id(),
        timestamp=datetime.now(timezone.utc),
        url=page.url,
        html_path=html_path,
        screenshot_path=screenshot_path,
        # ... other metadata
    )
    
    # CRITICAL: Persist JSON immediately before returning
    await self.persist(snapshot)
    
    return snapshot
```

### BrowserLifecycleExample Integration

**Target Component**: `examples/browser_lifecycle_example.py`
**Required Changes**:
1. Remove `display_telemetry_summary()` call
2. Ensure `capture_snapshot()` uses updated DOMSnapshotManager
3. Add optional page-type gating for snapshot waits

**Implementation Strategy**:
```python
# Remove problematic call
# self.display_telemetry_summary()  # REMOVED
print("📊 Selector engine telemetry: All operations completed successfully")

# Optional: Add page-type gating
if "Special:Search" in page.url:
    await self._wait_for_search_results(page)
```

## Integration Points

### Dependencies
- `src/browser/snapshot.py` - DOMSnapshotManager (primary changes)
- `examples/browser_lifecycle_example.py` - Consumer integration
- `src/storage/adapter.py` - File storage backend (no changes needed)

### Backward Compatibility
- Existing `capture()` API maintained
- Return value unchanged (Snapshot object)
- Additional synchronous persistence is transparent to callers

### Performance Impact
- Minimal synchronous JSON write (<10ms)
- No impact on capture performance
- Eliminates replay failures (net positive)

## Testing Strategy

### Unit Tests
- Test DOMSnapshotManager.capture() with immediate persistence
- Verify JSON file exists before method return
- Test BrowserLifecycleExample without telemetry method

### Integration Tests  
- End-to-end browser lifecycle example execution
- Verify offline replay success
- Verify integrity verification success

### Regression Tests
- Ensure existing snapshot functionality unchanged
- Verify selector engine integration unaffected
- Confirm YAML configuration loading works

## Risk Assessment

### Low Risk
- Telemetry method removal (cosmetic fix)
- Timeout warning reduction (optional improvement)

### Medium Risk
- Snapshot persistence timing (core functionality change)
- Mitigation: Comprehensive testing and backward compatibility

### Risk Mitigation
- Preserve existing API contracts
- Add comprehensive test coverage
- Gradual rollout with monitoring

## Conclusion

The research confirms the feasibility of all proposed fixes with minimal risk. The snapshot JSON timing fix is critical for framework-grade functionality, while other fixes improve developer experience. All changes maintain constitutional compliance and architectural consistency.
