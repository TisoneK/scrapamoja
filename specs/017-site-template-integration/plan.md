# Implementation Plan: Site Template Integration Framework

**Branch**: `017-site-template-integration` | **Date**: 2025-01-29 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/017-site-template-integration/spec.md`

## Summary

Create a standardized template framework that enables rapid development of site scrapers by leveraging existing Scorewise framework components. The template will extend BaseSiteScraper, integrate with the existing selector engine via YAML configuration, utilize the extractor module for data transformations, and provide automatic integration with browser lifecycle management, screenshot capture, and HTML capture features.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Playwright, PyYAML, existing framework components (BaseSiteScraper, BaseFlow, DOMContext, ExtractionRule, SemanticSelector)  
**Storage**: File-based YAML configuration, JSON schema for validation  
**Testing**: pytest with existing test framework patterns  
**Target Platform**: Cross-platform (Windows/Linux/macOS)  
**Project Type**: Framework extension with template structure  
**Performance Goals**: Template scrapers achieve same performance as hand-coded scrapers (<100ms overhead)  
**Constraints**: Must integrate with existing framework without breaking changes  
**Scale/Scope**: Support unlimited site scrapers with centralized registry

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Compliance Assessment

✅ **I. Semantic Selector-Centric Architecture**: Template scrapers MUST use existing selector engine, no hardcoded selectors allowed
✅ **II. Deep Modularity with Single Responsibility**: Template structure follows modular patterns with distinct components (integration_bridge, selector_loader, extraction/rules)
✅ **III. Asynchronous-First Design with Playwright Real Browser Execution**: Leverages existing async BaseSiteScraper and Playwright integration
✅ **IV. Stealth & Human Behavior Emulation**: Inherits existing stealth configuration from BaseSiteScraper
✅ **V. Tab-Aware Context Scoping**: Utilizes existing DOMContext for tab management
✅ **VI. Data Integrity & Schema Versioning**: Leverages existing extractor module with schema validation
✅ **VII. Production Fault Tolerance & Resilience**: Inherits existing error handling and retry logic from BaseSiteScraper
✅ **VIII. Observability & Structured Logging**: Utilizes existing logging framework throughout template components

### Gates Passed: All 8 core principles satisfied

**Post-Design Constitution Re-evaluation**: ✅ PASSED
- All design decisions align with constitutional principles
- Template framework leverages existing components without violating modularity
- Integration patterns maintain selector-first engineering
- No complexity violations detected
- Framework consistency preserved across all template implementations

## Project Structure

### Documentation (this feature)

```text
specs/017-site-template-integration/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── template-api.md
│   └── registry-api.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/sites/
├── base/                    # Existing base framework
│   ├── site_scraper.py      # BaseSiteScraper (existing)
│   ├── flow.py              # BaseFlow (existing)
│   └── template/            # NEW: Template framework
│       ├── __init__.py
│       ├── site_template.py         # Template base class
│       ├── integration_bridge.py   # Framework integration bridge
│       ├── selector_loader.py       # YAML selector integration
│       ├── site_registry.py         # Central scraper registry
│       └── validation.py            # Template validation framework
├── github/                  # Example template implementation
│   ├── __init__.py
│   ├── scraper.py           # GitHubScraper extends BaseSiteScraper
│   ├── flow.py              # GitHubFlow extends BaseFlow
│   ├── config.py            # GitHub-specific configuration
│   ├── integration_bridge.py # GitHub integration bridge
│   ├── selector_loader.py   # GitHub YAML selector loader
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── rules.py         # GitHub extraction rules using existing extractor
│   │   └── models.py        # GitHub data models extending base
│   ├── selectors/           # YAML selectors for existing engine
│   │   ├── search_input.yaml
│   │   ├── repository_list.yaml
│   │   └── repository_details.yaml
│   └── flows/
│       ├── search_flow.py
│       └── pagination_flow.py
└── wikipedia/               # Existing implementation (reference)
    └── [existing files...]

tests/sites/
├── template/                # Template framework tests
│   ├── unit/
│   ├── integration/
│   └── fixtures/
└── github/                  # GitHub template tests
    ├── unit/
    ├── integration/
    └── fixtures/
```

**Structure Decision**: Template framework extends existing base classes while providing standardized structure for new site scrapers. The `src/sites/base/template/` directory contains reusable template components, while individual site directories (like `github/`) contain site-specific implementations following the template pattern.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
