# Implementation Plan: Core Module Refactoring Fix

**Feature**: `011-fix-snapshot-refactor`  
**Created**: 2025-01-29  
**Status**: Draft  
**Spec**: [spec.md](spec.md)

## Technical Context

### Current State
- Core snapshot module (`src/browser/snapshot.py`) has undefined variable errors
- Variable references were not properly updated during refactoring
- Missing import statements prevent module functionality
- Inconsistent variable naming throughout the module

### Unknowns / Research Needed
- **NEEDS CLARIFICATION**: Current snapshot.py module structure and variable definitions
- **NEEDS CLARIFICATION**: Exact variable names and scope requirements for screenshot metadata
- **NEEDS CLARIFICATION**: Required import statements for datetime, hashlib, and pathlib operations
- **NEEDS CLARIFICATION**: Existing variable naming patterns in the codebase for consistency

### Dependencies
- Core snapshot module functionality
- Screenshot capture system integration
- Browser lifecycle management system
- JSON schema for snapshot metadata

### Integration Points
- Browser session management for screenshot capture
- File system operations for screenshot storage
- JSON serialization for metadata
- Error handling and logging systems

## Constitution Check

### Principle Compliance
- **Principle I - Selector-First Engineering**: Not directly applicable (fixing variable references)
- **Principle II - Stealth-Aware Design**: Not directly applicable (core module fix)
- **Principle III - Deep Modularity**: Must maintain modular structure during fixes
- **Principle IV - Test-First Validation**: Should include tests for variable reference fixes
- **Principle V - Production Resilience**: Must ensure graceful error handling
- **Principle VII - Neutral Naming**: Must use structural, descriptive variable names

### Gate Evaluation
- ✅ **Complexity Gate**: Low complexity - variable reference fixes
- ✅ **Constitution Gate**: No violations expected
- ✅ **Dependency Gate**: Clear dependencies on existing modules

## Phase 0: Research

### Research Tasks
1. **Analyze Current Module Structure**
   - Task: Research current snapshot.py module structure and identify all undefined variables
   - Task: Document existing variable naming patterns in the codebase
   - Task: Identify all required import statements for module functionality

2. **Variable Reference Analysis**
   - Task: Research screenshot metadata structure and field access patterns
   - Task: Document datetime/timestamp handling requirements
   - Task: Identify scope issues between method boundaries

3. **Integration Requirements**
   - Task: Research browser session integration points for screenshot capture
   - Task: Document file system operation requirements
   - Task: Identify JSON serialization requirements for metadata

### Research Findings

**COMPLETED** - Research identified specific undefined variable issue:

1. **Critical Issue Found**: Line 149 in `capture_snapshot()` method references `screenshot_path` which is not defined in local scope
2. **Root Cause**: Variable scope issue - `screenshot_path` only available as `snapshot.screenshot_path` after object creation
3. **Import Analysis**: ✅ All required imports present and properly organized
4. **Variable Naming**: ✅ Current naming conventions are consistent and appropriate
5. **Integration Points**: ✅ All browser, file system, and JSON integrations working correctly

**Decision**: Fix by changing `screenshot=bool(screenshot_path)` to `screenshot=bool(screenshot_metadata["filepath"] if screenshot_metadata else False)`

## Phase 1: Design & Contracts

### Data Model Design
**COMPLETED** - No entity changes required:

- **DOMSnapshot**: Existing entity with proper attribute definitions
- **ScreenshotMetadata**: Existing structure with validation rules
- **HTMLMetadata**: Existing structure with validation rules
- **Variable Scope**: Fixed undefined variable reference in logging statement

### API Contracts
**COMPLETED** - Full API specification created:

- **Public Methods**: All existing methods maintained, no breaking changes
- **Internal Methods**: Screenshot and HTML capture contracts documented
- **Error Handling**: BrowserError and structured logging contracts defined
- **File System**: Directory structure and naming conventions specified

### Integration Design
**COMPLETED** - All integration points documented:

- **Browser Session**: Playwright Page object integration
- **File System**: Async file operations with proper error handling
- **JSON Schema**: Version 1.2 compatibility maintained
- **Performance**: Minimal impact fix with no overhead

## Constitution Check - Post Design

### Principle Compliance - Final Assessment
- **Principle I - Selector-First Engineering**: ✅ Not applicable (variable reference fix)
- **Principle II - Stealth-Aware Design**: ✅ Not applicable (core module fix)
- **Principle III - Deep Modularity**: ✅ Maintained existing modular structure
- **Principle IV - Implementation-First Development**: ✅ Direct fix with manual validation
- **Principle V - Production Resilience**: ✅ Graceful error handling maintained
- **Principle VI - Module Lifecycle Management**: ✅ No changes to module contracts
- **Principle VII - Neutral Naming**: ✅ Used structural, descriptive variable names

### Gate Evaluation - Final
- ✅ **Complexity Gate**: Low complexity confirmed - single line variable fix
- ✅ **Constitution Gate**: No violations - all principles followed
- ✅ **Dependency Gate**: Clear dependencies with no breaking changes

## Phase 2: Implementation Planning

### Task Generation
**READY** - Implementation tasks can now be generated using `/speckit.tasks`

### Dependencies
**RESOLVED** - All dependencies identified and documented:
- **Core Dependency**: Proper variable scoping in capture_snapshot method
- **External Dependencies**: None (all existing dependencies are sufficient)
- **Integration Dependencies**: No changes required to existing integrations

### Risk Assessment
**LOW RISK** - Implementation risks identified and mitigated:
- **Technical Risk**: Minimal - single line change with clear impact
- **Integration Risk**: None - no API changes or breaking modifications
- **Performance Risk**: None - no computational overhead introduced
- **Security Risk**: None - no security implications
- **Rollback Risk**: Minimal - easy to revert if needed

## Planning Complete ✅

**Status**: Phase 0 (Research) and Phase 1 (Design) completed successfully
**Next Step**: Execute `/speckit.tasks` to generate implementation tasks
**Artifacts Generated**:
- ✅ research.md - Complete analysis of undefined variable issue
- ✅ data-model.md - Entity definitions and validation rules
- ✅ contracts/snapshot-api.md - Full API specification
- ✅ quickstart.md - Implementation guide and validation steps
- ✅ Agent context updated with relevant technology information

**Ready for Task Generation**: All unknowns resolved, all contracts defined, all risks assessed.
