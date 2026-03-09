---
generated: 2026-03-09
project: scrapamoja
workflow: correct-course
status: approved
---

# Sprint Change Proposal

**Date:** 2026-03-09  
**Project:** scrapamoja  
**Workflow:** Correct Course - Sprint Change Management

---

## Section 1: Issue Summary

### Problem Statement

Flashscore was built with its own complete selector management system, and then the adaptive selector engine was built separately as a parallel system. Both systems are complete but incompatible - they don't integrate seamlessly.

### Context

This issue was discovered during integration analysis after all 6 epics (Epic 1-6) were completed. The implementation work is correct, but the two systems were designed independently without integration planning.

### Evidence

1. **Selector Loading Mismatch:** Flashscore does manual YAML → SemanticSelector conversion instead of using the engine's native context-aware loading.

2. **Context System Duplication:**
   - Flashscore uses `SelectorContext` (primary/secondary/tertiary + DOMState)
   - Engine uses `DOMContext` (URL + page_type + navigation_state)
   - Two different structures that don't align

3. **Selector Registration Timing:** Manual timing vs engine's automatic context-based loading

4. **Strategy Format Incompatibility:**
   - Flashscore format: `{type, selector, weight}`
   - Engine format: `StrategyPattern(type, priority, config)`

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Status | Impact |
|------|--------|--------|
| Epic 1 (Fallback Resolution) | Done | Works but not optimally integrated |
| Epic 2 (YAML Hints) | Done | Must use engine's native loading |
| Epic 3 (Failure Capture) | Done | Works but not optimized |
| Epic 4 (Graceful Degradation) | Done | No changes needed |
| Epic 5 (WebSocket Notifications) | Done | Works independently |
| Epic 6 (Health Monitoring) | Done | Works independently |

**Conclusion:** All 6 completed epics remain valid but aren't optimally integrated with the adaptive engine.

### Artifact Conflicts

| Artifact | Conflict Level | Required Action |
|----------|---------------|----------------|
| PRD | Low | Document integration patterns |
| Architecture | Medium | Add unified context model spec |
| UI/UX | None | No impact |

### Technical Impact

- Flashscore doesn't leverage engine's full capabilities:
  - ❌ No automatic fallback chains
  - ❌ No confidence scoring optimization
  - ❌ No context-aware selector resolution
  - ❌ Manual maintenance overhead

---

## Section 3: Recommended Approach

### Selected Path: Direct Adjustment (Option 1)

**Recommendation:** Create Epic 7: Selector System Integration

### Justification

1. **Preserves Completed Work:** No rollback needed - all 6 epics are correctly implemented
2. **Achieves Full Integration:** Enables all adaptive engine capabilities
3. **Reasonable Effort:** Medium complexity with manageable risk
4. **Positions for Future:** Enables new features built on integrated system

### Options Evaluated

| Option | Viable | Selected |
|--------|--------|----------|
| Option 1: Direct Adjustment | ✅ Yes | ✅ YES |
| Option 2: Rollback | ❌ No | - |
| Option 3: MVP Review | ✅ Yes (but unnecessary) | - |

### Effort & Risk Assessment

| Factor | Assessment |
|--------|------------|
| Effort | Medium |
| Risk | Medium |
| Timeline Impact | 1-2 sprints |

---

## Section 4: Detailed Change Proposals

### Change Proposal 1: Architecture Documentation Update

**File:** `_bmad-output/planning-artifacts/architecture.md`

**Section:** Integration Points (add new subsection)

**Change:**
```markdown
### Flashscore Integration (Critical)

**Context System Unification:**
Flashscore uses SelectorContext (primary/secondary/tertiary + DOMState) while the engine uses DOMContext (URL + page_type + navigation_state). A unified context model must be defined.

**Required Integration Steps:**
1. Flashscore must use engine's native context-aware selector loading
2. Strategy format must be converted to engine's StrategyPattern
3. Selector registration must use engine's automatic timing
```

**Rationale:** Prevent future integration issues by documenting the required integration pattern.

**Status:** ✅ Approved

---

### Change Proposal 2: Create Epic 7 - Selector System Integration

**New Epic:** Epic 7: Selector System Integration

**Goal:** Unify Flashscore's selector management system with the adaptive selector engine to enable full capabilities.

**Stories:**

#### Story 7.1: Unified Context Model

**Description:** Combine SelectorContext and DOMContext into single unified model

**Acceptance Criteria:**
- Define mapping between Flashscore and engine contexts
- Create unified context class that supports both paradigms
- All existing selectors work with new context model

---

#### Story 7.2: Native YAML Loading

**Description:** Refactor Flashscore to use engine's context-aware loading

**Acceptance Criteria:**
- Remove manual YAML → SemanticSelector conversion
- Flashscore uses engine's `load_selectors_for_context()` method
- Loading happens automatically on scraper initialization

---

#### Story 7.3: Strategy Format Standardization

**Description:** Convert Flashscore strategy format to engine's StrategyPattern

**Acceptance Criteria:**
- All selector configs use StrategyPattern format
- Automatic conversion layer for legacy configs
- All existing selectors remain functional

---

#### Story 7.4: Registration Automation

**Description:** Implement automatic selector registration timing

**Acceptance Criteria:**
- Remove manual selector registration calls
- Registration happens automatically via engine hooks
- Selectors available immediately on scraper startup

---

**Post-Integration Capabilities:**

✅ Automatic hierarchical selector resolution  
✅ Confidence-based strategy selection  
✅ Context-aware fallback chains  
✅ Centralized selector management  
✅ Built-in quality control and validation  

**Status:** ✅ Approved

---

## Section 5: Implementation Handoff

### Scope Classification: Moderate

Requires backlog reorganization (Epic 7 creation) and PO/SM coordination.

### Handoff Recipients

| Role | Responsibility |
|------|----------------|
| **Development Team** | Implement integration changes (Stories 7.1-7.4) |
| **Product Owner** | Create Epic 7 in backlog, prioritize stories |
| **Architect** | Define unified context model specification |

### Responsibilities Detail

**Development Team:**
- Code implementation for all 4 stories
- Unit and integration testing
- Update documentation
- Verify all existing functionality still works

**Product Owner:**
- Add Epic 7 to backlog with 4 stories
- Prioritize based on project goals
- Define acceptance criteria for each story
- Coordinate with Scrum Master on sprint planning

**Architect:**
- Design unified context model
- Define context mapping rules
- Review implementation approach
- Ensure no breaking changes

### Success Criteria

1. Flashscore uses engine's native loading instead of manual conversion
2. Confidence scoring works for all Flashscore selectors
3. Automatic fallback chains function without manual intervention
4. All existing tests pass
5. Documentation updated with integration details

### Timeline Recommendation

- **Sprint N+1:** Epic 7 created, Story 7.1 (Unified Context Model)
- **Sprint N+2:** Stories 7.2-7.3 (Native Loading + Strategy Standardization)
- **Sprint N+3:** Story 7.4 (Registration Automation) + Testing

---

## Approval

**Status:** ✅ Approved by Tisone on 2026-03-09

**Next Action:** Product Owner to create Epic 7 in backlog

---

*Generated by Correct Course Workflow - BMAD*
