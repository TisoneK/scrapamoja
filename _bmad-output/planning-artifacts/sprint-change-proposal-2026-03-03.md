# Sprint Change Proposal

**Date:** 2026-03-03  
**Trigger:** Issue identified during Epic 2 implementation - "The adaptive module was meant to extend existing systems not reinvent the wheel"

---

## 1. Issue Summary

### Problem Statement
The adaptive module (`src/selectors/adaptive/`) is creating new services that duplicate existing robust systems in the codebase, specifically:

1. **StabilityScoringService** duplicates **ConfidenceScorer** functionality
2. Both services calculate similar scores (0.0-1.0 range) for selector reliability

### Context
- Architecture document specified: "Extend existing YAML selector engine" and "Minimal invasion - Extend existing patterns, don't rewrite"
- Dev notes in stories explicitly stated: "DO NOT REINVENT STORAGE" and "FOLLOW EXISTING MODEL PATTERNS"
- The module IS attempting to integrate with existing systems (snapshot, storage adapter), but gaps exist

### Evidence
- Existing: [`src/selectors/confidence.py`](src/selectors/confidence.py:46) - `ConfidenceScorer` with weights, strategy history tracking
- New: [`src/selectors/adaptive/services/stability_scoring.py`](src/selectors/adaptive/services/stability_scoring.py:25) - `StabilityScoringService` with similar functionality

---

## 2. Impact Analysis

### Epic Impact

| Epic | Current Status | Impact |
|------|---------------|--------|
| Epic 1: Foundation & Schema | done | May need refactoring |
| Epic 2: Failure Detection & Capture | in-progress | Fix integration gaps |
| Epic 3: Alternative Selector Proposal | backlog | Depends on Epic 2 fixes |
| Epic 4: Human Verification Workflow | backlog | No change |
| Epic 5: Learning & Weight Adjustment | backlog | MUST refactor to use existing |
| Epic 6: Audit Logging | backlog | No change |
| Epic 7: Escalation UI | backlog | No change |
| Epic 8: Feature Flags | backlog | No change |

### Artifact Conflicts

| Artifact | Current State | Required Change |
|----------|---------------|-----------------|
| Architecture.md | Says "Extend existing patterns" | Add explicit "MUST reuse existing confidence system" |
| Epic 5 (Learning) | Plans new weight system | Must extend existing ConfidenceScorer |
| Story 1.3 | Implements StabilityScoring | Refactor to extend ConfidenceScorer |

### Technical Impact

**Areas of Duplication Found:**
1. **Scoring Systems**: `ConfidenceScorer` vs `StabilityScoringService`
   - Both calculate 0.0-1.0 scores
   - Both track strategy history
   - Both use weighted factors

**Areas Correctly Integrated:**
1. **Snapshot System**: `failure_snapshot.py` correctly uses `SnapshotManager`, `SelectorFailureTrigger`
2. **Storage**: `extension.py` correctly extends `FileSystemStorageAdapter`

---

## 3. Recommended Approach

**Selected: Option 1 - Direct Adjustment**

Refactor the adaptive module to properly extend existing systems rather than creating parallel implementations.

### Rationale
- Existing systems are robust and well-tested
- Reduces code duplication and maintenance burden
- Maintains architectural consistency
- Lower risk than rolling back or MVP changes

### Effort: Medium | Risk: Low

---

## 4. Detailed Change Proposals

### Change 1: Refactor StabilityScoringService to Extend ConfidenceScorer

**Story:** [1.3] Implement Recipe Stability Scoring

**OLD:**
```python
# src/selectors/adaptive/services/stability_scoring.py
class StabilityScoringService:
    """New service with duplicate scoring logic"""
    def calculate_stability_score(self, success_count, failure_count, ...):
        # Own implementation
```

**NEW:**
```python
# src/selectors/adaptive/services/stability_scoring.py
from src.selectors.confidence import ConfidenceScorer

class StabilityScoringService(ConfidenceScorer):
    """Extended from existing ConfidenceScorer for recipe stability"""
    
    def calculate_recipe_stability(self, recipe_id: str) -> float:
        # Uses parent class methods + stability-specific logic
        base_confidence = self.get_strategy_confidence(recipe_id)
        # Add generation tracking, parent-child inheritance
```

**Rationale:** The existing `ConfidenceScorer` already tracks strategy history and calculates confidence. Extend it rather than duplicate.

### Change 2: Update Epic 5 (Learning & Weight Adjustment) Scope

**Epic:** 5 - Learning & Weight Adjustment

**OLD Scope:**
- Create new weight system from scratch

**NEW Scope:**
- Extend existing `ConfidenceScorer` and `ConfidenceWeights`
- Add adaptive-specific weight adjustments (generation survival, parent-child inheritance)
- Use existing `ConfidenceThresholdManager`

### Change 3: Add Integration Enforcement to Architecture

**File:** [`_bmad-output/planning-artifacts/architecture.md`](_bmad-output/planning-artifacts/architecture.md)

**Add new section:**

```
## Integration Enforcement Rules

### MUST EXTEND - Do Not Reimplement
1. **Confidence Scoring**: Use `src/selectors/confidence.py` → extend `ConfidenceScorer`
2. **Snapshot Capture**: Use `src/core/snapshot/` → integrate via `SnapshotManager`
3. **Storage**: Use `src/storage/adapter.py` → extend `IStorageAdapter`
4. **Browser/Session**: Use `src/stealth/` → extend existing coordinators
5. **Validation**: Use `src/selectors/validation/` → extend `ConfidenceValidator`

### Pattern for Extension
```python
# CORRECT: Extend existing
class AdaptiveConfidenceScorer(ConfidenceScorer):
    def __init__(self):
        super().__init__()
        self._adaptive_weights = AdaptiveWeights()

# WRONG: Create parallel system  
class NewScoringService:  # DON'T DO THIS
    def calculate(self):
        # own implementation
```
```

### Change 4: Update Story Context Templates

Add explicit guardrails to all future story contexts:

```markdown
### Integration Requirements (MANDATORY)

- [ ] Does this require a NEW service/class? → Check if existing system can be extended
- [ ] Check existing systems FIRST before creating new:
  - Scoring: `src/selectors/confidence.py`
  - Storage: `src/storage/adapter.py`
  - Snapshot: `src/core/snapshot/`
  - Browser: `src/stealth/`
```

---

## 5. Implementation Handoff

### Scope Classification: **Moderate**

Requires backlog reorganization and PO/SM coordination for refactoring.

### Handoff Recipients

| Role | Responsibility |
|------|----------------|
| **Dev Agent** | Refactor StabilityScoringService to extend ConfidenceScorer |
| **SM/PM** | Update Epic 5 scope, create refactoring stories |
| **Architect** | Update architecture.md with integration enforcement rules |

### Deliverables

1. Refactored `stability_scoring.py` extending existing `ConfidenceScorer`
2. Updated Epic 5 scope document
3. Updated architecture.md with integration rules
4. New story: "Refactor adaptive module to use existing ConfidenceScorer"

### Success Criteria

- [ ] `StabilityScoringService` inherits from or uses `ConfidenceScorer`
- [ ] No duplicate scoring logic in adaptive module
- [ ] All new stories must document existing systems to extend before implementation

---

## 6. Approval

**Do you approve this Sprint Change Proposal for implementation?**

- [ ] Yes - Proceed with implementation
- [ ] No - Needs revision
- [ ] Revise specific section

---

## Appendix: Existing Systems to Extend

| Need | Use This | Location |
|------|----------|----------|
| Confidence scoring | `ConfidenceScorer` | `src/selectors/confidence.py` |
| Confidence weights | `ConfidenceWeights` | `src/selectors/confidence.py` |
| Threshold management | `ConfidenceThresholdManager` | `src/selectors/confidence/thresholds.py` |
| Snapshot capture | `SnapshotManager` | `src/core/snapshot/manager.py` |
| Storage adapter | `FileSystemStorageAdapter` | `src/storage/adapter.py` |
| Validation rules | `ConfidenceValidator` | `src/selectors/validation/confidence_rules.py` |
| Selector models | `SelectorResult`, `ConfidenceMetrics` | `src/models/selector_models.py` |
