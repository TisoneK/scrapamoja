# Implementation Plan: Snapshot Timing and Telemetry Fixes

**Branch**: `014-snapshot-timing-fix` | **Date**: 2025-01-29 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/014-snapshot-timing-fix/spec.md`

## Summary

This feature addresses critical timing and error issues in the 012-selector-engine-integration implementation. The primary issue is that snapshot JSON metadata is written after replay attempts, causing offline HTML replay and integrity verification to fail. Additional issues include a missing telemetry method and Playwright timeout warnings. The solution involves reordering the snapshot persistence logic and resolving method errors to achieve framework-grade reliability.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: playwright>=1.40.0, pytest>=7.4.0, pytest-asyncio>=0.21.0, pydantic>=2.5.0, structlog>=23.2.0  
**Storage**: JSON files (session data, snapshots), InfluxDB (telemetry metrics)  
**Testing**: pytest, pytest-asyncio, pytest-mock, pytest-cov  
**Target Platform**: Linux server (production), cross-platform (development)  
**Project Type**: Single project with deep modularity  
**Performance Goals**: Maintain current operation latency and throughput; no performance degradation from timing fixes  
**Constraints**: Must maintain backward compatibility during migration; configuration changes must apply within 5 seconds without subsystem restarts  
**Scale/Scope**: Medium - focused on browser lifecycle example with potential application to broader system

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Compliance Verification

✅ **Principle VII - Production Fault Tolerance & Resilience**: This feature directly supports this principle by fixing snapshot JSON timing issues that cause replay failures, ensuring consistent behavior and graceful degradation.

✅ **Principle VIII - Observability & Structured Logging**: The telemetry method fix ensures proper structured logging output without AttributeError exceptions, maintaining the observability requirements.

✅ **Deep Modularity**: Changes are localized to specific components (DOMSnapshotManager, BrowserLifecycleExample) without affecting the broader architecture.

✅ **Asynchronous-First Design**: All fixes maintain async/await patterns and non-blocking operations.

### Gates Status: **PASS** - No constitutional violations identified

## Project Structure

### Documentation (this feature)

```text
specs/014-snapshot-timing-fix/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── browser/
│   ├── snapshot.py          # DOMSnapshotManager - timing fixes
│   └── manager.py           # BrowserManager - integration points
├── selectors/
│   └── engine/              # Selector engine - telemetry integration
└── storage/
    └── adapter.py           # File storage - JSON persistence

examples/
├── browser_lifecycle_example.py  # Main example - telemetry method fix
├── selector_config_loader.py     # YAML config loader - integration
└── wikipedia_selectors.yaml      # Selector configurations

tests/
├── integration/
│   └── test_snapshot_timing.py   # Integration tests for timing fixes
└── unit/
    ├── test_snapshot_manager.py  # Unit tests for DOMSnapshotManager
    └── test_browser_lifecycle.py # Unit tests for BrowserLifecycleExample
```

**Structure Decision**: Single project structure with focused changes to existing modules. The fixes are primarily in the browser snapshot system and example code, maintaining the established deep modularity pattern.

## Complexity Tracking

No constitutional violations requiring justification. All changes are within existing architectural boundaries and maintain compliance with established principles.
