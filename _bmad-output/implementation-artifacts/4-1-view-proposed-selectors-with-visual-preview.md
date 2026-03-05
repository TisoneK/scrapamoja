# Story 4.1: View Proposed Selectors with Visual Preview

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Python Developer**,
I want to view proposed selectors with visual previews
So that I can understand what the selector will capture before approving.

## Acceptance Criteria

1. **Given** a selector failure with proposed alternatives
   **When** I view the failure details
   **Then** I should see: the failed selector, each proposed alternative with confidence score, visual preview highlighting what each selector captures

2. **Given** the visual preview
   **When** displayed
   **Then** it should clearly show: matched elements highlighted, unmatched elements dimmed, context around the match

## Tasks / Subtasks

- [x] Task 1: Create Failure Detail API Endpoint (AC: #1)
  - [x] Subtask 1.1: Create GET /failures/{id} endpoint returning failure + alternatives
  - [x] Subtask 1.2: Include confidence scores in response
  - [x] Subtask 1.3: Include snapshot reference for visual preview

- [x] Task 2: Create Visual Preview Component (AC: #2)
  - [x] Subtask 2.1: Implement DOM snapshot renderer
  - [x] Subtask 2.2: Add element highlighting for matched selectors
  - [x] Subtask 2.3: Implement dimming for unmatched elements
  - [x] Subtask 2.4: Add context display around matches

- [x] Task 3: Create Failure Dashboard List View (AC: #1)
  - [x] Subtask 3.1: Create GET /failures endpoint with filtering
  - [x] Subtask 3.2: Display failure cards with summary info
  - [x] Subtask 3.3: Add navigation to detail view

- [x] Task 4: Integration & Tests (AC: #1, #2)
  - [x] Subtask 4.1: Connect frontend to API endpoints
  - [x] Subtask 4.2: Add unit tests for API responses
  - [x] Subtask 4.3: Add integration tests for visual preview

---

## Critical Architecture Requirements

### Module Structure
Per architecture, all new code goes in:
- **Python Backend**: `src/selectors/adaptive/`
- **Frontend**: `ui/escalation/` (new React app with Vite)

### API Requirements (from Architecture)
```
GET  /failures         - List selector failures (with filtering)
GET  /failures/{id}   - Get failure details + snapshot + alternatives
POST /failures/{id}/approve   - Approve proposed selector
POST /failures/{id}/reject    - Reject with reason
```

### Frontend Components Required
- FailureDashboard - List of selector failures
- FailureDetailView - Snapshot + proposed alternatives  
- VisualPreview - DOM snapshot renderer with highlighting
- ApprovalPanel - Approve/Reject/Modify actions

### Technology Stack
- **Backend**: FastAPI, SQLAlchemy 2.0 (async), Pydantic
- **Frontend**: React + TypeScript + Vite + Tailwind CSS + Shadcn/UI
- **State**: React Query (server state) + Zustand (UI state)
- **Authentication**: API Keys (simple, per architecture)

### Database Tables (from Epic 1-3)
- `recipes` - Already implemented
- `snapshots` - Already implemented (Story 2.2)
- `audit_log` - Already implemented (Epic 6)
- `weights` - Already implemented (Epic 5)

### Integration Points
- **Selector Engine**: Listen for resolution failures (Story 2.1)
- **Snapshot System**: Reference captured snapshots (Story 2.2)
- **Proposal Engine**: Get alternative selectors (Story 3.1-3.3)
- **Confidence Scorer**: Already implemented (Story 3.2)
- **Blast Radius**: Already implemented (Story 3.3)

---

## Developer Guardrails

### DO NOT REINVENT
- Use existing `ConfidenceScorer` from `src/selectors/adaptive/services/confidence_scorer.py`
- Use existing `AlternativeSelector` from Story 3.2
- Use existing `BlastRadiusResult` from Story 3.3
- Use existing snapshot model from Story 2.2

### MUST USE
- FastAPI for all API endpoints
- SQLAlchemy 2.0 async patterns (already established)
- Pydantic for request/response validation
- React Query for server state management
- Tailwind CSS for styling (per architecture)

### Naming Conventions
- Python: `snake_case` for functions/variables
- TypeScript: `camelCase` variables, `PascalCase` components
- API Response: `{"data": {...}}` format per architecture
- Errors: RFC 7807 format `{"type": "...", "title": "...", "detail": "..."}`

### File Structure (per Architecture)
```
src/selectors/adaptive/
├── api/
│   ├── routes/
│   │   └── failures.py    # NEW: Failure endpoints
│   ├── schemas/
│   │   └── failures.py   # NEW: Pydantic schemas
│   └── dependencies/
├── services/
│   ├── failure_service.py  # NEW: Business logic
│   ├── confidence_scorer.py  # EXISTING (Story 3.2)
│   └── blast_radius.py     # EXISTING (Story 3.3)
└── db/
    └── models/
        ├── recipe.py       # EXISTING
        └── snapshot.py     # EXISTING (Story 2.2)

ui/escalation/
├── components/
│   ├── failures/
│   │   ├── FailureDashboard.tsx    # NEW
│   │   ├── FailureDetailView.tsx   # NEW
│   │   ├── VisualPreview.tsx       # NEW
│   │   └── ApprovalPanel.tsx       # NEW
│   └── ui/                         # Shadcn components
├── pages/
│   └── FailuresPage.tsx            # NEW
├── hooks/
│   └── useFailures.ts              # NEW: React Query hooks
└── api/
    └── failures.ts                 # NEW: API client
```

---

## Technical Implementation Notes

### Visual Preview Implementation
The visual preview should:
1. Render the captured DOM snapshot (HTML) in an iframe or sanitized container
2. Apply CSS highlighting to elements matching each proposed selector
3. Show confidence scores as badges next to each alternative
4. Display blast radius information (from Story 3.3) for impact awareness

### API Response Structure
```python
# GET /failures/{id} response
{
  "data": {
    "failure_id": "uuid",
    "selector_id": "string",
    "failed_selector": "string",
    "sport": "string",
    "site": "string",
    "timestamp": "ISO8601",
    "snapshot_id": "uuid",
    "alternatives": [
      {
        "selector": "string",
        "strategy": "css|xpath|text|attribute",
        "confidence_score": 0.85,
        "blast_radius": {...},
        "highlight_css": "string"
      }
    ]
  }
}
```

### Frontend State Management
- React Query for: fetching failures, caching, loading states
- Zustand for: selected failure, modal states, filters

---

## References

- [Source: _bmad-output/planning-artifacts/epics.md#333-348] - Story 4.1 requirements with BDD acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#173-204] - API Endpoints and Frontend Architecture
- [Source: _bmad-output/planning-artifacts/architecture.md#218-257] - Code Organization and Module Structure
- [Source: _bmad-output/planning-artifacts/architecture.md#331-344] - API Response Formats

### Previous Epic Dependencies
- [Source: _bmad-output/implementation-artifacts/2-1-detect-selector-resolution-failures.md] - Failure detection (Story 2.1)
- [Source: _bmad-output/implementation-artifacts/2-2-capture-dom-snapshot-at-failure.md] - Snapshot capture (Story 2.2)
- [Source: _bmad-output/implementation-artifacts/3-1-analyze-dom-structure.md] - DOM analysis (Story 3.1)
- [Source: _bmad-output/implementation-artifacts/3-2-generate-confidence-scores.md] - Confidence scoring (Story 3.2)
- [Source: _bmad-output/implementation-artifacts/3-3-calculate-blast-radius.md] - Blast radius (Story 3.3)

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

- Implemented following architecture from _bmad-output/planning-artifacts/architecture.md
- Used existing ConfidenceScorer from src/selectors/adaptive/services/confidence_scorer.py
- Used existing BlastRadiusCalculator from src/selectors/adaptive/services/blast_radius.py
- Used existing FailureEvent model and repository from Story 2.1-2.3

### Completion Notes List

✅ **Completed Tasks:**
- Created FastAPI endpoints for failures (GET /failures, GET /failures/{id}, POST approve/reject)
- Implemented FailureService with confidence scoring integration
- Created Pydantic schemas for API request/response validation
- Created React components: VisualPreview, FailureDashboard, FailureDetailView, ApprovalPanel
- Added comprehensive unit tests (12 tests, all passing)
- Created API client for external consumption

### File List

**Backend (Python):**
- `src/selectors/adaptive/api/schemas/failures.py` - Pydantic schemas
- `src/selectors/adaptive/api/routes/failures.py` - FastAPI routes
- `src/selectors/adaptive/api/app.py` - FastAPI application
- `src/selectors/adaptive/api/client.py` - API client
- `src/selectors/adaptive/services/failure_service.py` - Business logic

**Frontend (React/TypeScript):**
- `ui/escalation/components/failures/VisualPreview.tsx`
- `ui/escalation/components/failures/FailureDashboard.tsx`
- `ui/escalation/components/failures/FailureDetailView.tsx`
- `ui/escalation/components/failures/ApprovalPanel.tsx`
- `ui/escalation/components/failures/index.ts`
- `ui/escalation/hooks/useFailures.ts` - React Query hooks
- `ui/escalation/pages/FailuresPage.tsx` - Main page component

**Tests:**
- `tests/selectors/adaptive/test_failure_service.py`
