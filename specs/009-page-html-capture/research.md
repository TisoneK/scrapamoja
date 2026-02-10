# Phase 0 Research: Page HTML Capture and Storage in Snapshots

**Feature**: 009-page-html-capture  
**Date**: 2025-01-29  
**Research Focus**: HTML file capture integration with existing browser lifecycle system

## Research Findings

### Current Snapshot Implementation Analysis

**Decision**: Extend existing `capture_snapshot()` method in `browser_lifecycle_example.py`  
**Rationale**: The current implementation already captures HTML content via `await self.page.content()` but only stores metadata. Extending this method maintains consistency and leverages existing error handling and timing infrastructure.  
**Alternatives considered**: 
- Create separate HTML capture service (rejected: adds complexity, breaks existing workflow)
- Modify BrowserSession core API (rejected: too invasive for this specific feature)

### File Organization Strategy

**Decision**: Store HTML files in `data/snapshots/html/` subdirectory with timestamp-based naming  
**Rationale**: Follows existing snapshot directory structure, provides clear separation, prevents filename conflicts, and maintains chronological ordering.  
**Alternatives considered**:
- Store alongside JSON files (rejected: clutters snapshot directory)
- Use UUID-based naming (rejected: less readable, harder to debug)
- Session-based subdirectories (rejected: adds unnecessary complexity)

### HTML File Naming Convention

**Decision**: Use format `{timestamp}_{session_id}_{hash_prefix}.html`  
**Rationale**: Provides uniqueness, traceability to session, and quick integrity verification. Timestamp ensures chronological ordering, session_id links to browser session, hash_prefix allows quick content identification.  
**Alternatives considered**:
- Simple timestamp only (rejected: potential collisions, no session linkage)
- UUID only (rejected: not human-readable, no session context)

### JSON Schema Extension

**Decision**: Add `page.html_file` and `page.content_hash` fields to existing snapshot schema  
**Rationale**: Maintains backward compatibility while adding required functionality. Existing consumers will ignore new fields, and new consumers can leverage HTML file references.  
**Alternatives considered**:
- New schema version (rejected: unnecessary breaking change)
- Separate HTML metadata file (rejected: complicates snapshot management)

### Error Handling Strategy

**Decision**: Graceful degradation with structured logging  
**Rationale**: Aligns with Constitution Principle V (Production Resilience) and existing error handling patterns in the codebase. HTML file capture failure should not prevent snapshot creation.  
**Alternatives considered**:
- Strict failure on HTML capture error (rejected: breaks existing functionality)
- Silent HTML capture failures (rejected: hides important information)

### Performance Considerations

**Decision**: Asynchronous HTML file writing with size monitoring  
**Rationale**: Maintains non-blocking behavior consistent with Playwright async patterns. Size monitoring prevents excessive disk usage and provides early warning for large pages.  
**Alternatives considered**:
- Synchronous file writing (rejected: blocks async event loop)
- No size monitoring (rejected: risk of disk space issues)

### Integration Points

**Decision**: Modify only the `capture_snapshot()` method in the example file  
**Rationale**: This is the designated extension point for snapshot functionality. Core browser lifecycle components remain unchanged, following Constitution Principle III (Deep Modularity).  
**Alternatives considered**:
- Modify BrowserSession class (rejected: core component changes)
- Create new snapshot manager (rejected: over-engineering for this scope)

## Technical Decisions Summary

1. **HTML Storage**: File-based with JSON references (confirmed from clarification)
2. **File Location**: `data/snapshots/html/` subdirectory
3. **Naming**: `{timestamp}_{session_id}_{hash_prefix}.html`
4. **Schema Extension**: Add `html_file` and `content_hash` fields
5. **Error Handling**: Graceful degradation with logging
6. **Performance**: Async file operations with size monitoring
7. **Integration**: Extend existing `capture_snapshot()` method only

## Constitution Compliance Assessment

- **Selector-First Engineering**: N/A (no new selectors required)
- **Stealth-Aware Design**: N/A (HTML capture doesn't affect browser fingerprinting)
- **Deep Modularity**: ✅ (isolated to snapshot method, no core changes)
- **Implementation-First Development**: ✅ (direct implementation approach)
- **Production Resilience**: ✅ (graceful degradation, error handling)
- **Module Lifecycle Management**: ✅ (no new modules, extends existing lifecycle)
- **Neutral Naming Convention**: ✅ (uses structural, descriptive names)

## Next Steps

All technical unknowns resolved. Ready to proceed to Phase 1 design phase with data modeling and contract definition.
