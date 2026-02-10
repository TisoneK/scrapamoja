## Context

The current selector system uses a flat structure with 6 YAML files that cannot handle the complex multi-layer navigation requirements of the flashscore workflow. The workflow requires tab-scoped selectors, context-dependent selectors for tertiary navigation, and different selectors for each tab context. The existing selector engine lacks the architectural foundation to manage hierarchical organization and context-aware loading.

Current constraints:
- Existing selector loading system expects flat file structure
- No context management for navigation states
- Performance concerns with loading all selectors upfront
- Migration complexity from flat to hierarchical structure

## Goals / Non-Goals

**Goals:**
- Implement hierarchical selector organization with primary/secondary/tertiary folder structure
- Create context-aware selector loading system that dynamically loads based on navigation state
- Enable tab-scoped selectors that activate based on current UI context
- Provide navigation context management to track and validate state transitions
- Maintain performance through intelligent caching and lazy loading

**Non-Goals:**
- Complete rewrite of existing selector engine (extend current architecture)
- Support for non-FlashScore workflows (focus on flashscore requirements)
- Real-time selector updates without page refresh
- Backward compatibility with flat YAML structure (breaking change accepted)

## Decisions

### Hierarchical Folder Structure
**Decision**: Use three-level folder hierarchy (primary/secondary/tertiary) based on navigation context
**Rationale**: Maps directly to flashscore workflow's multi-layer navigation and provides clear separation of concerns
**Alternatives considered**: 
- Two-level structure (insufficient for STATS sub-tabs)
- Tag-based organization (complex to manage and validate)

### Context-Aware Loading Architecture
**Decision**: Implement SelectorContextManager that tracks navigation state and loads appropriate selector sets
**Rationale**: Provides centralized state management and enables dynamic loading without performance overhead
**Alternatives considered**:
- Event-driven loading (complex to debug and maintain)
- Static selector sets per page (insufficient for dynamic content)

### Selector Caching Strategy
**Decision**: Use LRU cache with context-based invalidation
**Rationale**: Balances performance with memory usage and ensures stale selectors are refreshed
**Alternatives considered**:
- No caching (performance issues)
- Full cache invalidation (unnecessary reloading)

### Migration Approach
**Decision**: Create migration utility that transforms flat YAML files to hierarchical structure
**Rationale**: Provides automated migration path and reduces manual effort
**Alternatives considered**:
- Manual migration (error-prone and time-consuming)
- Parallel support (increases complexity)

## Risks / Trade-offs

**Performance Risk**: Increased file system operations for hierarchical loading
→ Mitigation: Implement intelligent caching and lazy loading

**Migration Risk**: Data loss during transformation from flat to hierarchical structure
→ Mitigation: Create backup and validation utilities

**Complexity Risk**: Increased system complexity may impact maintainability
→ Mitigation: Comprehensive documentation and clear separation of concerns

**Compatibility Risk**: Breaking change may affect existing integrations
→ Mitigation: Clear migration guide and deprecation timeline

**Memory Usage Risk**: Caching multiple selector contexts may increase memory footprint
→ Mitigation: LRU cache with size limits and context-based cleanup

## Migration Plan

1. **Phase 1**: Create hierarchical folder structure and validation utilities
2. **Phase 2**: Implement SelectorContextManager and context-aware loading
3. **Phase 3**: Develop migration utility for existing flat YAML files
4. **Phase 4**: Add tab-scoped selector support and caching
5. **Phase 5**: Integration testing and performance optimization
6. **Phase 6**: Documentation update and deployment

**Rollback Strategy**: Maintain flat structure backup and feature flag for hierarchical loading

## Open Questions

- How to handle selector conflicts between different contexts?
- What is the optimal cache size for selector contexts?
- Should we support custom folder structures beyond the defined hierarchy?
- How to validate selector completeness across all required contexts?
