# Story 6.1: Record Human Decisions

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **System**,
I want to record every human decision with full context
so that there is a complete audit trail.

## Acceptance Criteria

1. Given a human takes an action (approve, reject, flag, create custom), When the action is processed, Then it should be recorded in the audit_log table with: action_type, selector_id, user_id, timestamp, context_snapshot
2. Given a decision is recorded, When stored, Then it should include: before_state, after_state, reason_if_provided, confidence_at_time

## Tasks / Subtasks

- [x] Task 1: Design and implement audit_log database schema (AC: 1, 2)
  - [x] Subtask 1.1: Create audit_log table with all required fields
  - [x] Subtask 1.2: Add proper indexes for query performance
  - [x] Subtask 1.3: Implement database migrations
- [x] Task 2: Create audit logging service layer (AC: 1, 2)
  - [x] Subtask 2.1: Implement AuditLogger class with record_decision method
  - [x] Subtask 2.2: Add context snapshot capture functionality
  - [x] Subtask 2.3: Implement before/after state capture
- [x] Task 3: Integrate audit logging into human decision points (AC: 1)
  - [x] Subtask 3.1: Hook into approval workflow
  - [x] Subtask 3.2: Hook into rejection workflow
  - [x] Subtask 3.3: Hook into flagging workflow
  - [x] Subtask 3.4: Hook into custom selector creation workflow
- [x] Task 4: Add comprehensive testing (AC: 1, 2)
  - [x] Subtask 4.1: Unit tests for audit logging service
  - [x] Subtask 4.2: Integration tests for workflow integration
  - [x] Subtask 4.3: Performance tests for high-volume logging

## Dev Notes

### Architecture Requirements

**Database Schema Requirements:**
- Use SQLAlchemy 2.0 with async support as specified in architecture [Source: _bmad-output/planning-artifacts/epics.md#Line 90]
- Implement audit_log table with fields: action_type, selector_id, user_id, timestamp, context_snapshot, before_state, after_state, reason_if_provided, confidence_at_time
- Add proper indexes for query performance: action_type, selector_id, user_id, timestamp
- Use SQLite for MVP, PostgreSQL for production [Source: _bmad-output/planning-artifacts/epics.md#Line 89]

**Technical Stack:**
- Backend: FastAPI for REST API endpoints [Source: _bmad-output/planning-artifacts/epics.md#Line 88]
- ORM: SQLAlchemy 2.0 with async support [Source: _bmad-output/planning-artifacts/epics.md#Line 90]
- Database: SQLite (MVP) / PostgreSQL (production) [Source: _bmad-output/planning-artifacts/epics.md#Line 89]

### Project Structure Notes

**New Module Location:**
- Create audit logging in `src/selectors/adaptive/` module [Source: _bmad-output/planning-artifacts/epics.md#Line 94]
- Follow existing scrapamoja codebase patterns (brownfield extension) [Source: _bmad-output/planning-artifacts/epics.md#Line 87]

**Integration Points:**
- Selector Engine: Listen for resolution failures [Source: _bmad-output/planning-artifacts/epics.md#Line 97]
- YAML Config: Extend with recipe metadata [Source: _bmad-output/planning-artifacts/epics.md#Line 99]

### Implementation Sequence Context

**Phase 1 Foundation:**
- This story is part of Phase 1: Foundation - Set up adaptive module, SQLite database, basic FastAPI endpoints [Source: _bmad-output/planning-artifacts/epics.md#Line 103]
- Audit logging is foundational to all subsequent adaptive features

### Developer Guardrails

**Database Implementation:**
- MUST use SQLAlchemy 2.0 async patterns
- MUST implement proper connection pooling
- MUST include database migrations using Alembic
- MUST add comprehensive error handling for database operations

**API Integration:**
- MUST integrate with existing FastAPI application structure
- MUST follow existing authentication patterns (API Keys) [Source: _bmad-output/planning-artifacts/epics.md#Line 92]
- MUST implement proper request/response validation using Pydantic

**Code Quality Standards:**
- MUST follow existing code patterns in scrapamoja codebase
- MUST include comprehensive type hints
- MUST implement proper logging using existing logging infrastructure
- MUST add unit tests with pytest following existing test patterns

**Performance Requirements:**
- MUST handle high-volume logging without blocking main workflows
- MUST implement async database operations
- MUST consider batch insert for high-frequency decisions
- MUST ensure audit logging doesn't slow down selector resolution

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Lines 462-517] - Epic 6 complete requirements
- [Source: _bmad-output/planning-artifacts/epics.md#Lines 86-106] - Technical requirements and implementation sequence
- [Source: _bmad-output/planning-artifacts/epics.md#Lines 87-94] - Architecture integration points

## Dev Agent Record

### Agent Model Used

Claude-3.5-Sonnet

### Debug Log References

### Completion Notes List

- ✅ **Database Schema Enhancement**: Extended audit_log table with selector_id and context_snapshot fields to meet AC1 and AC2 requirements
- ✅ **Database Migration**: Created and applied migration script to add new fields and indexes for performance
- ✅ **Audit Service Implementation**: Built comprehensive AuditLogger service with methods for all decision types (approve, reject, flag, custom selector creation)
- ✅ **API Integration**: Updated all human decision endpoints (approve, reject, flag, custom selector creation) to capture user context and pass to audit service
- ✅ **Context Capture**: Implemented full context snapshot capture with before/after state tracking for complete audit trail
- ✅ **Comprehensive Testing**: Created unit tests, integration tests, and performance tests for audit logging functionality

### File List

- `src/selectors/adaptive/db/models/audit_event.py` - Enhanced with selector_id and context_snapshot fields
- `src/selectors/adaptive/db/repositories/audit_event_repository.py` - Updated to support new fields
- `src/selectors/adaptive/services/audit_service.py` - New comprehensive audit logging service
- `src/selectors/adaptive/api/routes/failures.py` - Integrated audit logging into all decision endpoints
- `src/selectors/adaptive/db/migrations/add_audit_enhancements.sql` - Database migration for new fields
- `src/selectors/adaptive/services/__init__.py` - Updated exports for audit service
- `tests/integration/test_audit_service.py` - Comprehensive test suite for audit functionality

### Change Log

- **2026-03-06**: Implemented Story 6.1 - Record Human Decisions with full audit logging functionality including database schema enhancements, service layer implementation, API integration, and comprehensive testing
