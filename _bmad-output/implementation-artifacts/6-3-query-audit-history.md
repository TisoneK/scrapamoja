# Story 6.3: Query Audit History

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **User**,
I want to query audit history by selector, date, or user
so that I can investigate past decisions.

## Acceptance Criteria

1. Given the audit log, When I query by selector_id, Then I should see all decisions related to that selector
2. Given the audit log, When I query by date range, Then I should see all decisions within that period
3. Given the audit log, When I query by user, Then I should see all decisions made by that user

## Tasks / Subtasks

- [ ] Task 1: Implement audit query service layer (AC: 1, 2, 3)
  - [ ] Subtask 1.1: Create AuditQueryService with filtering by selector_id
  - [ ] Subtask 1.2: Add date range filtering capability
  - [ ] Subtask 1.3: Add user_id filtering capability
  - [ ] Subtask 1.4: Implement combined multi-criteria queries
- [ ] Task 2: Build audit query API endpoints (AC: 1, 2, 3)
  - [ ] Subtask 2.1: GET /audit/log endpoint with query parameters
  - [ ] Subtask 2.2: GET /audit/log/selector/{selector_id}
  - [ ] Subtask 2.3: GET /audit/log/user/{user_id}
  - [ ] Subtask 2.4: GET /audit/log/date-range?start=...&end=...
- [ ] Task 3: Implement pagination and sorting (AC: 1, 2, 3)
  - [ ] Subtask 3.1: Add cursor-based pagination for large result sets
  - [ ] Subtask 3.2: Add sorting options (date, user, selector)
  - [ ] Subtask 3.3: Add limit and offset support
- [ ] Task 4: Create comprehensive testing (AC: 1, 2, 3)
  - [ ] Subtask 4.1: Unit tests for AuditQueryService
  - [ ] Subtask 4.2: Integration tests for API endpoints
  - [ ] Subtask 4.3: Performance tests for large datasets

## Dev Notes

### Architecture Requirements

**Database Schema (from Story 6.1):**
- audit_log table already exists with fields: action_type, selector_id, user_id, timestamp, context_snapshot, before_state, after_state, reason_if_provided, confidence_at_time
- Indexes already exist: action_type, selector_id, user_id, timestamp
- Uses SQLAlchemy 2.0 with async support [Source: _bmad-output/planning-artifacts/architecture.md#Line 152]

**Technical Stack:**
- Backend: FastAPI for REST API endpoints [Source: _bmad-output/planning-artifacts/architecture.md#Line 168]
- ORM: SQLAlchemy 2.0 with async support [Source: _bmad-output/planning-artifacts/architecture.md#Line 152]
- Database: SQLite (MVP) / PostgreSQL (production) [Source: _bmad-output/planning-artifacts/architecture.md#Line 151]

**API Endpoints Required:**
- GET /audit/log - Query audit history with filters
- GET /audit/log/selector/{selector_id} - Get all decisions for a selector
- GET /audit/log/user/{user_id} - Get all decisions by a user
- GET /audit/log/date-range - Get decisions within date range

### Project Structure Notes

**Module Location:**
- Create query service: `src/selectors/adaptive/services/audit_query_service.py`
- Add new API routes: `src/selectors/adaptive/api/routes/audit_query.py`
- Build on existing `src/selectors/adaptive/` module

**Integration Points:**
- Use existing audit_log table from Story 6.1 [Source: _bmad-output/implementation-artifacts/6-1-record-human-decisions.md#Line 119]
- Use existing audit_event_repository.py from Story 6.1 [Source: _bmad-output/implementation-artifacts/6-1-record-human-decisions.md#Line 120]
- Follow Story 6.2 patterns for trail API [Source: _bmad-output/implementation-artifacts/6-2-maintain-complete-audit-trail.md#Line 56]

### Previous Story Intelligence

**Story 6.1 Learnings:**
- Database schema uses SQLAlchemy 2.0 async patterns successfully
- Audit service integration works well with existing FastAPI structure
- Comprehensive testing approach validated (unit + integration + performance)
- File organization pattern established: models, repositories, services, routes

**Story 6.2 Context (in-progress):**
- AuditTrailService is being implemented with chronological ordering
- Connected decision detection logic is being added
- User attribution and filtering capabilities are in progress
- Trail endpoints: GET /audit/trail, GET /audit/trail/{selector_id}, GET /audit/trail/user/{user_id}

**Code Patterns to Follow:**
- Use existing AuditEvent model structure from Story 6.1
- Follow repository pattern established in audit_event_repository.py
- Use Pydantic models for API request/response validation
- Reuse Story 6.2's pagination and filtering patterns

### Developer Guardrails

**Database Implementation:**
- MUST use SQLAlchemy 2.0 async patterns from Stories 6.1 and 6.2
- MUST reuse existing audit_log table and indexes
- MUST add additional indexes for query performance if needed
- MUST ensure queries are optimized for large datasets

**API Integration:**
- MUST follow FastAPI patterns established in Stories 6.1 and 6.2
- MUST use existing authentication (API Keys) [Source: _bmad-output/planning-artifacts/architecture.md#Line 211]
- MUST implement proper request/response validation using Pydantic
- MUST follow existing error handling patterns (RFC 7807)
- MUST use consistent response format with Story 6.2 trail endpoints

**Query Features:**
- MUST support filtering by selector_id (exact match)
- MUST support filtering by date range (start_date, end_date)
- MUST support filtering by user_id
- MUST support combined multi-criteria queries
- MUST support pagination (limit, offset, cursor)
- MUST support sorting (by date, user, selector)

**Code Quality Standards:**
- MUST follow existing code patterns in scrapamoja codebase [Source: _bmad-output/project-context.md#Line 431-437]
- MUST include comprehensive type hints (MyPy strict mode) [Source: _bmad-output/project-context.md#Line 264]
- MUST implement proper logging using existing logging infrastructure
- MUST add unit tests with pytest following existing test patterns

**Performance Requirements:**
- MUST handle large audit logs efficiently with pagination
- MUST implement async database operations
- MUST optimize complex multi-criteria queries
- MUST ensure query endpoints don't block main workflows

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Lines 498-517] - Story 6.3 complete requirements
- [Source: _bmad-output/planning-artifacts/epics.md#Lines 462-481] - Epic 6 complete context
- [Source: _bmad-output/planning-artifacts/architecture.md#Lines 164-183] - API endpoints and patterns
- [Source: _bmad-output/planning-artifacts/architecture.md#Lines 146-161] - Database architecture
- [Source: _bmad-output/implementation-artifacts/6-1-record-human-decisions.md] - Story 6.1 implementation (audit_log table)
- [Source: _bmad-output/implementation-artifacts/6-2-maintain-complete-audit-trail.md] - Story 6.2 implementation (trail endpoints)

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

### Completion Notes List

### File List

### Change Log
