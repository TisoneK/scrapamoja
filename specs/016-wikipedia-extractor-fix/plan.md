# Implementation Plan: Wikipedia Extractor Integration Fix

**Branch**: `016-wikipedia-extractor-fix` | **Date**: 2026-01-29 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/016-wikipedia-extractor-fix/spec.md`

## Summary

Fix critical blocking issue where YAML selector files are not loaded into the selector engine, preventing real Wikipedia data extraction. The implementation will add automatic YAML selector loading, validation, and registration to enable the Wikipedia scraper to extract actual content instead of fallback mock data.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Playwright, PyYAML, existing selector engine  
**Storage**: File-based YAML selectors in `src/sites/wikipedia/selectors/`  
**Testing**: pytest with real browser integration tests  
**Target Platform**: Linux/Windows development environment  
**Project Type**: Single Python project with modular architecture  
**Performance Goals**: <2 second average extraction time with real data  
**Constraints**: Must maintain backward compatibility with existing fallback mechanisms  
**Scale/Scope**: Single site (Wikipedia) with 10+ YAML selector files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Core Principles Compliance

✅ **I. Semantic Selector-Centric Architecture**: Feature directly enhances selector engine with YAML loading, maintaining semantic selector approach
✅ **II. Deep Modularity**: Implementation follows modular pattern with separate YAML loading, validation, and registration components  
✅ **III. Asynchronous-First Design**: Uses existing async Playwright infrastructure
✅ **IV. Stealth & Human Behavior Emulation**: Maintains existing stealth configuration
✅ **V. Tab-Aware Context Scoping**: Preserves existing tab context handling
✅ **VI. Data Integrity & Schema Versioning**: Maintains existing data schema and validation
✅ **VII. Production Fault Tolerance & Resilience**: Adds graceful degradation and error handling
✅ **VIII. Observability & Structured Logging**: Enhances logging for selector loading and extraction

### Operating Constraints Compliance

✅ **A. Technical Requirements**: Uses existing Playwright real browser execution
✅ **B. Network & Proxy Strategy**: Maintains existing proxy configuration
✅ **C. Legal & Ethical Boundaries**: Wikipedia scraping for research/educational purposes
✅ **D. Research vs Production Modes**: Supports both modes with appropriate logging levels
✅ **E. Failure & Auto-Abort Policies**: Implements graceful degradation

**Result**: ✅ **PASSED** - No constitution violations identified

## Project Structure

### Documentation (this feature)

```text
specs/016-wikipedia-extractor-fix/
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
├── sites/
│   └── wikipedia/
│       ├── selectors/           # YAML selector files (existing)
│       │   ├── article_title.yaml
│       │   ├── article_content.yaml
│       │   ├── search_results.yaml
│       │   ├── infobox_rows.yaml
│       │   └── toc_sections.yaml
│       ├── flows/              # Extraction flows (existing)
│       │   └── extraction_flow.py
│       └── scraper.py          # Main scraper (existing)
├── selectors/
│   ├── engine.py               # Selector engine (existing)
│   ├── yaml_loader.py          # NEW: YAML selector loading
│   ├── validator.py            # NEW: Selector validation
│   └── registry.py             # NEW: Selector registry management
└── components/
    └── initializer.py          # NEW: Component context initialization

tests/
├── integration/
│   └── test_wikipedia_scraper_real.py  # Real browser tests (existing)
├── unit/
│   └── test_yaml_selectors.py          # NEW: YAML selector tests
└── fixtures/
    └── wikipedia_selectors/             # NEW: Test selector fixtures
```

**Structure Decision**: Single project structure with modular components. YAML selectors remain in site-specific directories, while selector loading infrastructure is centralized in the selectors module for reuse across sites.

---

## Phase 0: Research & Analysis

### Research Tasks

Based on the technical context and requirements, the following research areas need investigation:

1. **YAML Selector Loading Patterns**: Research existing YAML loading implementations in Python web scraping frameworks
2. **Selector Engine Integration**: Analyze current selector engine architecture to determine optimal integration points
3. **Component Context Initialization**: Investigate ComponentContext requirements and proper initialization patterns
4. **Error Handling Best Practices**: Research graceful degradation patterns for selector loading failures
5. **Performance Optimization**: Investigate caching strategies for loaded selectors to meet <2s extraction goals

### Research Findings

**Decision**: Use PyYAML for selector file parsing with custom validation schema  
**Rationale**: PyYAML is the standard Python YAML library with robust error handling and security features  
**Alternatives considered**: ruamel.yaml (more features but complex), JSON with YAML comments (lossy)

**Decision**: Implement selector loading as lazy initialization with caching  
**Rationale**: Balances startup performance with runtime efficiency, supports hot-reloading during development  
**Alternatives considered**: Eager loading (slower startup), on-demand loading (potential runtime delays)

**Decision**: Use existing ComponentContext patterns from modular components  
**Rationale**: Maintains consistency with existing architecture, reduces learning curve  
**Alternatives considered**: Custom context implementation (more maintenance), dependency injection (over-engineering)

---

## Phase 1: Design & Contracts - COMPLETED

### Generated Artifacts

✅ **research.md**: Comprehensive technical research with decisions on PyYAML, lazy loading, and integration patterns  
✅ **data-model.md**: Complete entity definitions with YAMLSelector, SelectorStrategy, SelectorRegistry, and supporting entities  
✅ **contracts/yaml-selector-api.md**: Full API specification with endpoints, data models, events, and integration requirements  
✅ **quickstart.md**: Implementation guide with code examples, testing strategies, and troubleshooting  
✅ **Agent Context Updated**: Windsurf context updated with Python 3.11+, Playwright, PyYAML information

### Design Decisions Confirmed

- **Technology Stack**: PyYAML for parsing, lazy initialization with caching, existing ComponentContext patterns
- **Architecture**: Modular design with separate loader, validator, and registry components
- **Integration**: Extend existing selector engine with YAML loading capabilities
- **Performance**: Target <2s extraction time with intelligent caching strategies
- **Error Handling**: Multi-level error handling with graceful degradation

### Constitution Compliance Re-Checked

✅ **All Core Principles**: Maintained with semantic selector-centric approach and deep modularity  
✅ **All Operating Constraints**: Compliant with existing Playwright infrastructure and stealth requirements  
✅ **No Violations**: Design follows all constitution requirements without complexity violations

---

## Planning Complete

**Status**: ✅ **READY FOR IMPLEMENTATION**  
**Next Step**: Use `/speckit.tasks` to generate actionable implementation tasks

The Wikipedia extractor integration fix is now fully planned with:
- Technical research completed and decisions documented
- Data models and API contracts defined
- Implementation guide with code examples ready
- Agent context updated for development environment
- All constitution requirements satisfied

The critical blocking issue (YAML selectors not loaded) has been thoroughly analyzed and a comprehensive solution designed. Ready to proceed with task generation and implementation.
