<!--
Sync Impact Report:
- Version change: 1.2.0 → 1.3.0 (minor version - principle added)
- Modified principles: None
- Added sections: Principle VII - Neutral Naming Convention
- Removed sections: None
- Templates requiring updates:
  ✅ plan-template.md - Constitution Check section updated with Neutral Naming Convention
  ✅ spec-template.md - Requirements section aligned with naming constraints
  ✅ tasks-template.md - Task categorization reflects neutral naming requirements
- Follow-up TODOs: None - all templates updated to include naming convention compliance
-->
# Scorewise Scraper Constitution

## Core Principles

### I. Selector-First Engineering
Every feature starts with semantic selector definitions; Selectors must be multi-strategy with confidence scoring; Direct hardcoded selectors forbidden outside Selector Engine; DOM volatility is intentional - meaning persists, structure does not.

### II. Stealth-Aware Design
Human behavior emulation is mandatory; Anti-bot detection avoidance required; Browser fingerprint normalization essential; Rate limiting and session longevity controls enforced; Production impact on stealth settings must be conservative.

### III. Deep Modularity
Granular components with single responsibilities; Modules can nest arbitrarily deep; Clear contracts between components; Each module independently testable and documented; No organizational-only libraries allowed.

### IV. Implementation-First Development
No automated tests required; Direct implementation approach with manual validation; DOM snapshot integration for failure analysis; Code reviews serve as primary validation; Sanity checks through manual execution and inspection.

### V. Production Resilience
Graceful failure handling with retry and recovery; Checkpointing and resume capability required; Structured logging with correlation IDs; Resource lifecycle control mandatory; Never lose progress, never crash full run.

### VI. Module Lifecycle Management
The module must explicitly define initialization, active operation, error handling, recovery, and shutdown phases; The module must own its internal state and may not rely on shared global state; The module must expose a clear public contract (inputs, outputs, failure modes); Other modules may interact only through this contract, never through internal methods or data; A failure inside one module must be contained and recoverable, and must not implicitly crash or stall other modules.

### VII. Neutral Naming Convention
All code artifacts must use neutral, structural, and descriptive language only; Avoid qualitative, promotional, or marketing-style descriptors; Forbidden terms include: advanced, updated, powerful, sophisticated, intuitive, smart, intelligent, robust, scalable, modern, cutting-edge, next-gen, enterprise-grade, production-ready, high-performance, optimized, seamless, comprehensive, flexible, extensible, state-of-the-art, future-proof, best-in-class, industry-standard, battle-tested, world-class, mission-critical, resilient, efficient, elegant, clean, simple, lightweight, heavy-duty, turnkey, plug-and-play, or similar value-laden descriptors; Names must describe function and structure, not perceived quality or market position.

## Technical Constraints

### Technology Stack Requirements
Python 3.11+ with asyncio; Playwright (async API) for all browser automation; JSON output with schema versioning; No requests library or BeautifulSoup; Only Playwright for HTTP interactions and DOM querying.

### Selector Engineering Requirements
Multi-strategy selector resolution (primary, secondary, tertiary); Confidence scoring with thresholds (>0.8 for production); Context scoping for tab-aware selection; DOM snapshot integration on failure; Selector drift detection and adaptation.

### Stealth & Anti-Detection Requirements
Realistic browser fingerprints; Human-like interaction timing; Mouse movement and scroll simulation; Proxy management with residential IPs; Session persistence and warming.

## Development Workflow

### Implementation Phases
Phase 0: Research and selector discovery; Phase 1: Design with contracts and data models; Phase 2: Task generation with dependency ordering; Phase 3: Implementation following selector-first approach.

### Quality Gates
All selector definitions must pass confidence thresholds; Stealth configuration must be production-ready; Error handling must be comprehensive; Documentation must be complete for each module.

### Review Process
Code reviews must verify constitution compliance; Selector engineering decisions require justification; Stealth settings must be reviewed for production readiness; All PRs must validate against constitution principles.

## Governance

This constitution supersedes all other practices; Amendments require documentation, approval, and migration plan; All implementation must follow selector-first, stealth-aware, modular design; Templates and workflows must align with constitution principles.

**Version**: 1.3.0 | **Ratified**: 2025-01-27 | **Last Amended**: 2025-01-27
