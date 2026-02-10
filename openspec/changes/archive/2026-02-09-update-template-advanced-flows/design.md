## Context

The current site template (`src/sites/_template`) provides only basic flow organization patterns that don't scale for complex modern web applications. Real-world implementations like Flashscore, GitHub, and Wikipedia have evolved sophisticated multi-level flow architectures that the template doesn't reflect. This gap leads to developers creating under-engineered solutions that struggle with complex SPA navigation, filtering, and extraction requirements.

Current state: Template supports only flat flow structure
Desired state: Template supports four architectural patterns from simple to complex
Stakeholders: Site developers using the template for new scraper implementations

## Goals / Non-Goals

**Goals:**
- Provide comprehensive architectural guidance for flow organization
- Support complexity-based template generation (simple/standard/complex)
- Enable domain-specific flow separation (navigation/extraction/filtering/authentication)
- Maintain backward compatibility with existing simple sites
- Reduce cognitive load for developers choosing appropriate patterns

**Non-Goals:**
- Modify existing scraper implementations (only template changes)
- Change core scraping engine behavior
- Implement new flow execution logic (only organizational changes)
- Create new programming paradigms or frameworks

## Decisions

### Template Structure Organization
**Decision**: Use hierarchical directory structure with pattern examples
**Rationale**: Developers can see and copy the exact pattern they need rather than reading abstract documentation. Real examples reduce implementation errors.

**Alternative considered**: Single configurable template with complexity flags
**Rejected**: Would be more complex to maintain and harder for developers to understand specific patterns.

### Flow Domain Separation
**Decision**: Standardize on four domain categories: navigation/, extraction/, filtering/, authentication/
**Rationale**: These cover 95% of real-world flow needs and align with observed patterns from Flashscore, GitHub, Wikipedia implementations.

**Alternative considered**: Let developers create arbitrary subfolder names
**Rejected**: Would reduce consistency across sites and make template guidance less effective.

### Setup Script Enhancement
**Decision**: Add complexity assessment questions to template generation process
**Rationale**: Automated complexity assessment reduces decision fatigue and ensures appropriate pattern selection.

**Alternative considered**: Manual pattern selection after template creation
**Rejected**: Developers often stick with default pattern, leading to under-engineering.

## Risks / Trade-offs

**Risk**: Template complexity may overwhelm new developers
**Mitigation**: Provide clear pattern selection guide and start with simple examples

**Risk**: Breaking changes to existing template usage
**Mitigation**: Maintain simple pattern as default, add advanced patterns as additional options

**Trade-off**: Increased template size vs. comprehensive guidance
**Decision**: Favor comprehensive guidance - disk space is cheap, developer time is expensive

**Trade-off**: More setup steps vs. better long-term architecture
**Decision**: Accept slightly more initial setup for significantly better scalability

## Migration Plan

1. **Phase 1**: Create new template structure alongside existing (no breaking changes)
2. **Phase 2**: Update documentation with pattern selection guidance
3. **Phase 3**: Enhance setup script with complexity assessment
4. **Phase 4**: Deprecate old simple-only template (future release)

**Rollback strategy**: Keep original template as `simple/` subfolder, maintain compatibility

## Open Questions

- Should we provide automated migration tools for existing sites using old template?
- How do we handle sites that start simple but grow to need complex patterns?
- Should we include pattern validation in the setup script to prevent anti-patterns?
