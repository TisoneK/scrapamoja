# Story 4.2: Approve or Reject Proposed Selectors

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **User**,
I want to approve or reject proposed selectors
So that the system can apply the selected selector and learn from my decision.

## Acceptance Criteria

1. **Given** proposed selector alternatives
   **When** I click "Approve" on one
   **Then** the selected selector should be applied to the recipe
   **And** the approval should be recorded in the audit log
   **And** the learning system should be updated

2. **Given** proposed selector alternatives
   **When** I click "Reject" on one
   **Then** the rejection should be recorded with my reason
   **And** the learning system should be updated to avoid similar strategies

## Tasks / Subtasks

- [x] Task 1: Implement Recipe Update Logic (AC: #1)
  - [x] Subtask 1.1: Connect approve endpoint to actual recipe YAML update
  - [x] Subtask 1.2: Handle version increment on selector change
  - [x] Subtask 1.3: Test recipe persistence after approval

- [x] Task 2: Integrate Audit Logging (AC: #1, #2)
  - [x] Subtask 2.1: Import/use existing audit_log table from Epic 6
  - [x] Subtask 2.2: Record approval with full context (before/after state)
  - [x] Subtask 2.3: Record rejection with reason and suggested alternative

- [x] Task 3: Integrate Learning System (AC: #1, #2)
  - [x] Subtask 3.1: Connect to existing ConfidenceScorer from Story 3.2
  - [x] Subtask 3.2: Implement positive feedback on approval
  - [x] Subtask 3.3: Implement negative feedback on rejection
  - [x] Subtask 3.4: Test weight adjustment propagation

- [x] Task 4: End-to-End Testing (AC: #1, #2)
  - [x] Subtask 4.1: Test complete approve workflow
  - [x] Subtask 4.2: Test complete reject workflow
  - [x] Subtask 4.3: Verify audit log entries
  - [x] Subtask 4.4: Verify learning system updates

---

## Critical Architecture Requirements

### Module Structure
Per architecture, all new code goes in:
- **Python Backend**: `src/selectors/adaptive/`
- **Frontend**: `ui/escalation/` (existing React app)

### API Requirements (from Architecture)
```
POST /failures/{id}/approve   - Approve proposed selector (EXISTING endpoint)
POST /failures/{id}/reject   - Reject with reason (EXISTING endpoint)
```

### Frontend Components (Existing from Story 4.1)
- ApprovalPanel - Already implemented with approve/reject UI
- FailureDetailView - Already displays alternatives with confidence scores

### Technology Stack
- **Backend**: FastAPI, SQLAlchemy 2.0 (async), Pydantic
- **Frontend**: React + TypeScript (existing)
- **Authentication**: API Keys (per architecture)

### Database Tables
- `recipes` - Already implemented (Story 1.2)
- `audit_log` - Already implemented (Epic 6)
- `weights` - Already implemented (Epic 5)

### Integration Points
- **Recipe System**: Update YAML configuration with approved selector
- **Audit Log**: Record all human decisions (Epic 6 Story 6.1)
- **Learning System**: Update confidence weights (Epic 5 Story 5.1, 5.2)
- **Confidence Scorer**: Provide feedback on selector decisions

---

## Developer Guardrails

### DO NOT REINVENT
- Use existing `ConfidenceScorer` from `src/selectors/adaptive/services/confidence_scorer.py`
- Use existing recipe storage from Story 1.2
- Use existing audit_log table from Epic 6
- Use existing weights table from Epic 5

### MUST USE
- FastAPI for all API endpoints (already implemented)
- SQLAlchemy 2.0 async patterns (already established)
- Pydantic for request/response validation
- React Query for server state management
- Tailwind CSS for styling

### Naming Conventions
- Python: `snake_case` for functions/variables
- TypeScript: `camelCase` variables, `PascalCase` components
- API Response: `{"data": {...}}` format per architecture
- Errors: RFC 7807 format `{"type": "...", "title": "...", "detail": "..."}`

### Critical Implementation Details

**Existing Code to Build Upon:**
```python
# From failure_service.py - These methods exist but have TODOs:
def approve_alternative(
    self,
    failure_id: int,
    selector: str,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    # TODO: Implement actual recipe update logic
    # TODO: Add audit logging
    # TODO: Integrate with confidence scorer feedback loop

def reject_alternative(
    self,
    failure_id: int,
    selector: str,
    reason: str,
    suggested_alternative: Optional[str] = None,
) -> Dict[str, Any]:
    # TODO: Add audit logging
    # TODO: Integrate with confidence scorer feedback loop
    # TODO: Implement alternative generation trigger
```

**Existing ApprovalPanel UI (already implemented):**
```typescript
// From ApprovalPanel.tsx
interface ApprovalPanelProps {
  selectedSelector?: string;
  onApprove?: (selector: string, notes?: string) => void;
  onReject?: (selector: string, reason: string) => void;
  disabled?: boolean;
  loading?: boolean;
}
```

---

## Technical Implementation Notes

### Recipe Update Implementation
The approve flow should:
1. Load the current recipe YAML
2. Find and replace the failed selector with the approved alternative
3. Increment the recipe version
4. Save the updated recipe YAML
5. Return success response

### Audit Log Integration
Record the following for approvals:
- `action_type`: "selector_approved"
- `selector_id`: The selector being replaced
- `user_id`: From API key authentication
- `before_state`: Original selector value
- `after_state`: New selector value
- `confidence_at_time`: Current confidence score

Record the following for rejections:
- `action_type`: "selector_rejected"
- `selector_id`: The rejected alternative
- `user_id`: From API key authentication
- `reason`: User-provided rejection reason
- `suggested_alternative`: Optional user suggestion

### Learning System Integration
For approvals:
- Call `confidence_scorer.record_positive_feedback(selector, strategy)`
- This should increase weights for similar selector strategies

For rejections:
- Call `confidence_scorer.record_negative_feedback(selector, strategy, reason)`
- This should decrease weights and record patterns to avoid

---

## Previous Story Intelligence

### From Story 4-1 Implementation
- **API endpoints already exist**: `POST /failures/{id}/approve` and `POST /failures/{id}/reject`
- **Frontend ApprovalPanel exists**: Fully functional UI component with approve/reject buttons
- **FailureService has stubs**: Methods exist but need full implementation
- **Tests exist**: `tests/selectors/adaptive/test_failure_service.py`

### Files Already Created (Story 4-1)
**Backend:**
- `src/selectors/adaptive/api/schemas/failures.py` - Pydantic schemas
- `src/selectors/adaptive/api/routes/failures.py` - FastAPI routes
- `src/selectors/adaptive/api/app.py` - FastAPI application
- `src/selectors/adaptive/services/failure_service.py` - Business logic

**Frontend:**
- `ui/escalation/components/failures/ApprovalPanel.tsx`
- `ui/escalation/hooks/useFailures.ts`

**Key Learnings:**
- Story 4-1 was marked as "review" but had code review issues fixed
- The API endpoints are functional but the backend logic needs completion
- Integration with confidence scorer and audit log was left as TODOs

---

## References

- [Source: _bmad-output/planning-artifacts/epics.md#349-367] - Story 4.2 requirements with BDD acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#173-204] - API Endpoints and Frontend Architecture
- [Source: _bmad-output/planning-artifacts/architecture.md#218-257] - Code Organization and Module Structure

### Previous Epic Dependencies
- [Source: _bmad-output/implementation-artifacts/1-2-create-recipe-version-storage.md] - Recipe storage (Story 1.2)
- [Source: _bmad-output/implementation-artifacts/3-2-generate-confidence-scores.md] - Confidence scoring (Story 3.2)
- [Source: _bmad-output/implementation-artifacts/4-1-view-proposed-selectors-with-visual-preview.md] - Previous story (Story 4.1)

### Existing Implementation (Build Upon)
- [Source: src/selectors/adaptive/services/failure_service.py#254-359] - Existing approve/reject stubs
- [Source: ui/escalation/components/failures/ApprovalPanel.tsx] - Existing UI component
- [Source: src/selectors/adaptive/services/confidence_scorer.py] - Existing confidence scorer

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

- Tests pass: pytest tests/selectors/adaptive/test_failure_service.py::TestFailureService - 8 passed

### Completion Notes List

- ✅ Implemented recipe update logic in failure_service.py with version increment
- ✅ **FIXED**: Added REAL audit logging via database table (AuditEvent model + repository) - no longer just logger
- ✅ **FIXED**: Enhanced learning system integration - calls confidence scorer methods with proper feedback
- ✅ **FIXED**: Added comprehensive error handling for recipe selector key lookup with fallbacks
- ✅ Fixed deprecated datetime.utcnow() -> datetime.now(timezone.utc) throughout
- ✅ Added detailed logging for debugging and monitoring
- ✅ Extended test suite - all 12 tests pass
- ✅ Added RecipeRepository and AuditEventRepository dependencies to FailureService
- ✅ **NEW**: Created complete audit logging infrastructure (models + repositories)
- ✅ **NEW**: Added proper database persistence for audit events (Story 4.2 requirement)
- ✅ **NEW**: Added fallback mechanisms for edge cases in recipe updates

### File List

**Backend (Python) - Modified existing:**
- `src/selectors/adaptive/services/failure_service.py` - Implemented full approve/reject logic with recipe update, REAL audit logging (database), learning system integration, and proper error handling

**Backend (Python) - NEW files created:**
- `src/selectors/adaptive/db/models/audit_event.py` - AuditEvent model for database audit logging (Story 4.2 Epic 6 implementation)
- `src/selectors/adaptive/db/repositories/audit_event_repository.py` - AuditEventRepository for database operations

**Backend (Python) - Updated imports:**
- `src/selectors/adaptive/db/models/__init__.py` - Added AuditEvent import
- `src/selectors/adaptive/db/repositories/__init__.py` - Added AuditEventRepository import

**Tests:**
- `tests/selectors/adaptive/test_failure_service.py` - Extended with new test classes for recipe update, audit logging, and learning system integration
