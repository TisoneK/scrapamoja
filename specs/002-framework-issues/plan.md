# Implementation Plan: Fix Framework Issues

**Branch**: `002-framework-issues` | **Date**: 2026-01-29 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-framework-issues/spec.md`

## Summary

This feature addresses three remaining framework issues identified after the initial critical bug fixes: missing storage adapter interface methods, navigation timeout problems in CI environments, and subprocess cleanup warnings on Windows. The implementation focuses on completing the storage interface, adding test mode support for reliable navigation testing, and ensuring clean subprocess shutdown.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Playwright (async API), asyncio, pathlib, structlog  
**Storage**: File-based storage with JSON persistence  
**Testing**: Manual validation through browser lifecycle example  
**Target Platform**: Windows CI/CD environments and local development  
**Project Type**: Browser automation framework  
**Performance Goals**: Clean shutdown without warnings, reliable test execution  
**Constraints**: Must maintain backward compatibility, no external network dependencies for test mode  
**Scale/Scope**: Framework-level fixes affecting all browser automation operations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Required Compliance Gates

- **Selector-First Engineering**: Not directly applicable to storage/subprocess fixes
- **Stealth-Aware Design**: Not directly applicable to infrastructure fixes
- **Deep Modularity**: Storage adapter methods will be modular components with single responsibilities
- **Implementation-First Development**: Direct implementation with manual validation via browser lifecycle example
- **Production Resilience**: Storage operations and subprocess cleanup will include graceful failure handling
- **Module Lifecycle Management**: Storage adapter and subprocess cleanup will follow proper lifecycle patterns
- **Neutral Naming Convention**: All new methods and classes will use structural, descriptive language

### Technical Constraints Validation

- **Technology Stack**: Python 3.11+ with asyncio; Playwright (async API) only; JSON output with schema versioning
- **Selector Engineering**: Not applicable to storage/subprocess fixes
- **Stealth Requirements**: Not applicable to infrastructure fixes

### Quality Gates

- Storage adapter methods must follow existing patterns
- Test mode must work without external dependencies
- Subprocess cleanup must work on Windows without warnings
- Error handling must be comprehensive

## Project Structure

### Documentation (this feature)

```text
specs/002-framework-issues/
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
├── storage/
│   └── adapter.py           # FileSystemStorageAdapter modifications
├── browser/
│   └── session.py           # Subprocess cleanup improvements
└── examples/
    ├── browser_lifecycle_example.py  # Test mode enhancements
    └── test_pages/          # Local HTML pages for test mode
        └── google_stub.html
```

**Structure Decision**: Single project structure with targeted modifications to existing storage and browser modules, plus new test pages for local testing.

## Complexity Tracking

> **No Constitution violations identified - all fixes align with existing framework patterns**

## Phase 0: Research - COMPLETED

**Generated**: `research.md` with technical decisions for all three framework issues

**Key Decisions**:
- Storage interface: Implement missing methods following existing patterns
- Test mode: Add environment variable support with local HTML pages
- Subprocess cleanup: Enhance Windows-specific handle management

## Phase 1: Design & Contracts - COMPLETED

**Generated Artifacts**:
- `data-model.md` - Entity definitions and modifications
- `contracts/api.md` - Interface definitions and usage contracts
- `quickstart.md` - Implementation guide with step-by-step instructions

**Design Decisions**:
- Modular storage adapter methods with proper error handling
- Test mode integration with existing navigation flow
- Windows-specific subprocess cleanup with graceful error handling

## Next Steps

Proceed to `/speckit.tasks` to generate actionable implementation tasks for the three framework issues:

1. **Storage Interface Implementation** - Add missing store() and delete() methods
2. **Test Mode Navigation Support** - Create local test pages and environment variable handling  
3. **Subprocess Cleanup Enhancement** - Windows-specific subprocess handle management

All design artifacts are complete and ready for task generation.
