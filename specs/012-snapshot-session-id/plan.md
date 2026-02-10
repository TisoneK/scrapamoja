# Implementation Plan: Fix Snapshot Filenames to Use Session ID for Proper Uniqueness

**Branch**: `012-snapshot-session-id` | **Date**: January 29, 2026 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/012-snapshot-session-id/spec.md`

## Summary

The snapshot naming system currently uses only timestamp-based filenames, causing collisions between different sessions capturing data at similar times. This fix updates filenames to include the session_id, ensuring each session produces unique, traceable snapshots. 

**Primary Requirement**: Update filename format from `{page_name}_{timestamp}.json` to `{page_name}_{session_id}_{timestamp}.json` and similarly for screenshots.

**Technical Approach**: Modify snapshot capture and save operations in `src/browser/snapshot.py` to include session_id in generated filenames, update JSON metadata to reference complete screenshot paths with session ID, and ensure backward compatibility with snapshot loading.

## Technical Context

**Language/Version**: Python 3.11+ with asyncio  
**Primary Dependencies**: Playwright (async API), pathlib for filesystem operations, JSON for metadata  
**Storage**: File system-based storage in `data/snapshots/` directory with subdirectory `data/snapshots/screenshots/`  
**Testing**: pytest with async support for validation  
**Target Platform**: Linux server / CLI environment  
**Project Type**: Single project (monolithic scraper architecture)  
**Performance Goals**: Minimal overhead - filename generation should add <1ms latency per snapshot  
**Constraints**: Session ID must be readily available at snapshot capture time; filename format must remain POSIX-compliant  
**Scale/Scope**: Supports concurrent snapshot captures without filename collisions; supports retention and cleanup of old snapshots

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Required Compliance Gates

- **✅ Deep Modularity**: Snapshot filename generation is isolated in dedicated methods; session_id dependency is passed explicitly (no shared global state)
- **✅ Implementation-First Development**: No automated tests required in this phase; manual validation via running example twice to verify unique filenames
- **✅ Production Resilience**: Graceful handling of missing session_id; automatic directory creation if screenshots directory doesn't exist
- **✅ Neutral Naming Convention**: "session_id" is structural and descriptive; no qualitative language used
- **✅ No Architecture Violations**: Changes are localized to snapshot filename generation; no new dependencies; no breaking API changes for public interfaces

### Technical Constraints Validation

- **✅ Technology Stack**: Python 3.11+ with asyncio; no new dependencies introduced; JSON output remains compatible
- **✅ Session Management**: Session ID is already available in browser lifecycle context; no new session tracking required
- **✅ File System Operations**: Standard pathlib operations; consistent with existing code patterns

### Quality Gates

- All snapshot files created with session ID in filename
- Screenshot references in JSON metadata include session ID
- No "existing file" warnings for different sessions
- Session ID extractable from all filenames

## Project Structure

### Documentation (this feature)

```text
specs/012-snapshot-session-id/
├── plan.md              # This file
├── research.md          # Phase 0 output (TBD)
├── data-model.md        # Phase 1 output (TBD)
├── quickstart.md        # Phase 1 output (TBD)
├── contracts/           # Phase 1 output (TBD)
│   └── snapshot-api.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
src/browser/
├── snapshot.py          # PRIMARY: Update _save_snapshot(), _capture_screenshot(), capture_snapshot() methods
├── exceptions.py        # Reference: No changes needed
└── ...

src/models/
├── selector_models.py   # REVIEW: Check if DOMSnapshot model needs session_id field

examples/
└── browser_lifecycle_example.py  # VALIDATION: Run twice to verify unique filenames

data/snapshots/
├── {page_name}_{session_id}_{timestamp}.json    # NEW: Session ID included
├── {page_name}_{session_id}_{timestamp}.png     # REFERENCE: Old format without session_id
└── screenshots/
    └── {page_name}_{session_id}_{timestamp}.png # NEW: Session ID included
```

**Structure Decision**: Localized changes to snapshot capture module. Single project architecture. No new files or modules required. Changes are backward-compatible at JSON schema level (new fields added, existing fields preserved).

## Complexity Tracking

> No Constitution violations identified. All changes are localized and modular.

| Item | Status |
|------|--------|
| Module Responsibility | Single - snapshot.py handles all filename generation |
| API Compatibility | Preserved - public method signatures unchanged; only internal behavior modified |
| Testing Strategy | Manual validation with example; no test code required per constitution |
| Session ID Availability | Confirmed - available in page context during snapshot capture |
