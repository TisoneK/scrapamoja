# Story 4.1: Adaptive REST API Integration

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **scraper system**,
I want **to call the adaptive REST API for alternative resolution**,
So that **I can get alternative selector suggestions when primary selectors fail**.

## Acceptance Criteria

1. **Given** a failed primary selector **When** calling the adaptive REST API **Then** a request is sent with selector_id and page_url **And** alternative selectors are returned if available

2. **Given** a successful API call **When** alternatives are received **Then** the alternatives are used as fallbacks **And** the fallback chain is extended with these alternatives

3. **Given** an API call with a selector that has no alternatives **When** the API responds **Then** an empty alternatives list is returned **And** no error is raised

4. **Given** adaptive API integration **When** configuring the API client **Then** timeout is configurable (default 30s per NFR4) **And** connection pooling is enabled (per NFR5)

## Tasks / Subtasks

- [x] Task 1: Create AdaptiveAPIClient class (AC: 1, 2, 3, 4)
  - [x] Subtask 1.1: Implement async API client with timeout configuration
  - [x] Subtask 1.2: Implement connection pooling (singleton pattern per architecture)
  - [x] Subtask 1.3: Handle empty alternatives response gracefully
- [x] Task 2: Integrate API client with fallback chain (AC: 2)
  - [x] Subtask 2.1: Extend fallback chain with API-returned alternatives
  - [x] Subtask 2.2: Ensure alternatives are tried after YAML-defined fallbacks
- [x] Task 3: Add configuration support (AC: 4)
  - [x] Subtask 3.1: Add configurable timeout (default 30s)
  - [x] Subtask 3.2: Configure connection pooling parameters
- [x] Task 4: Performance test suite (AC: NFR1)
  - [x] Subtask 4.1: Create latency test to verify ≤5s fallback resolution
  - [x] Subtask 4.2: Test timeout behavior

## Dev Notes

### Architecture Patterns (MUST FOLLOW)

- **Integration Pattern**: In-process integration (import adaptive module directly into scraper)
- **Connection Management**: Singleton pattern (single shared connection)
- **Fallback Chain Pattern**: Linear chain (primary → fallback1 → fallback2 → API alternatives)
- **Implementation Pattern**: Use @with_fallback decorator for fallback chains

### Project Structure (NEW FILES)

```
src/selectors/
├── adaptive/
│   ├── __init__.py
│   ├── api_client.py     # NEW - AdaptiveAPIClient for REST calls
│   └── sync_adapter.py   # NEW - Sync wrapper for async adaptive module
```

### Existing Components to Leverage

- `src/selectors/adaptive/` - Already exists (API, DB models, services)
- `src/selectors/fallback/chain.py` - FallbackChainExecutor from Epic 1
- `src/selectors/hooks/post_extraction.py` - PostExtractionValidator from Epic 3
- `src/selectors/hooks/submission.py` - FailureEventSubmissionService from Epic 3

### Technical Requirements

1. **Async/Await**: ALL I/O operations must use `async def`
2. **Type Safety**: MyPy strict mode - all functions need type annotations
3. **Pydantic Models**: Use Pydantic models for all data transfer objects
4. **Custom Exceptions**: Use exceptions from `src/selectors/exceptions.py`
5. **Structured Logging**: Use structlog with correlation IDs

### Dependencies for Epic 4

Epic 4 (Graceful Degradation) builds on:
- ✅ Validation layer hooks (Epic 3)
- ✅ Failure event capture (Epic 3)
- ✅ DB submission service (Epic 3)
- ✅ Retry queue (Epic 3)

### Project Structure Notes

- Alignment with unified project structure (paths, modules, naming)
- Detected conflicts or variances (with rationale): N/A

### References

- Source: _bmad-output/planning-artifacts/epics.md#Story-4.1
- Source: _bmad-output/planning-artifacts/architecture.md#Integration-Architecture
- Source: _bmad-output/planning-artifacts/prd.md#Integration-Architecture
- Source: _bmad-output/planning-artifacts/architecture.md#Fallback-Chain-Patterns

---

## Dev Agent Guardrails

### Technical Requirements

| Requirement | Details | Source |
|------------|---------|--------|
| API Timeout | Default 30s, configurable | NFR4 |
| Connection Pooling | Enabled, singleton pattern | NFR5 |
| Fallback Resolution Time | ≤5 seconds | NFR1 |
| Integration Pattern | In-process import | Architecture |
| Error Handling | Graceful degradation | PRD |

### Architecture Compliance

| Decision | Implementation | Source |
|----------|----------------|--------|
| In-process Integration | Import adaptive module directly | Architecture |
| Validation Layer | Check results after extraction | Architecture |
| Linear Chain | Primary → Fallback1 → Fallback2 | Architecture |
| Singleton | Single shared connection | Architecture |
| Decorator Pattern | @with_fallback decorator | Architecture |

### Library/Framework Requirements

| Component | Technology | Version |
|-----------|------------|---------|
| HTTP Client | httpx or aiohttp | Latest stable |
| Async | asyncio | Built-in |
| Type Annotations | MyPy strict | >=1.7.0 |
| Data Models | Pydantic | >=2.5.0 |

### File Structure Requirements

**New Files to Create:**
- `src/selectors/adaptive/api_client.py` - AdaptiveAPIClient class
- `src/selectors/adaptive/sync_adapter.py` - Sync wrapper (HIGH PRIORITY from Epic 3 Retro)

**Files to Modify:**
- `src/selectors/fallback/chain.py` - Add API alternative integration
- `src/selectors/engine.py` - Add API client initialization

### Testing Requirements

| Test Type | Location | Requirements |
|-----------|----------|--------------|
| Unit Tests | `tests/selectors/adaptive/` | @pytest.mark.unit |
| Integration Tests | `tests/integration/` | @pytest.mark.integration |
| Performance Tests | `tests/performance/` | ≤5s latency (NFR1) |

### Critical Don't-Miss Rules

- **ALWAYS** use existing selector engine for DOM operations
- **NEVER** create raw HTTP clients - use httpx/aiohttp with proper pooling
- **ALWAYS** follow singleton pattern for connection management
- **NEVER** block event loops - use async patterns throughout
- **ALWAYS** use structured logging with correlation IDs

---

## Previous Story Intelligence

### From Epic 3 Retro (CRITICAL - READ BEFORE IMPLEMENTATION)

The Epic 3 retrospective identified HIGH PRIORITY technical debt that MUST be addressed in Epic 4:

| # | Action Item | Priority | Apply To |
|---|-------------|----------|----------|
| 1 | Fix datetime.utcnow() in Story 1-4 | HIGH | This story if you touch datetime |
| 2 | Migrate Pydantic ConfigDict | HIGH | Any new Pydantic models |
| 3 | Create proper sync adapter | HIGH | src/selectors/adaptive/sync_adapter.py |
| 4 | Create performance test suite | HIGH | tests/performance/ |

**Key Learnings from Epic 3:**
- Singleton pattern for submission service works well - REUSE for AdaptiveAPIClient
- Retry queue with max size limit (1000) - apply similar pattern for API calls
- Fire-and-forget for non-blocking operations - consider for non-critical API calls
- ContextVar for correlation ID tracking - MUST propagate to API client

**Issues Encountered in Epic 3 (Avoid Repeating):**
- Story 3-5 was marked complete but core methods were missing - VERIFY YOUR IMPLEMENTATION
- Don't mark done until implementation verified by tests

### From Epic 3 Stories

**Files created in Epic 3:**
- `src/selectors/hooks/submission.py` - FailureEventSubmissionService (singleton)
- `src/selectors/hooks/post_extraction.py` - PostExtractionValidator

**Patterns to reuse:**
- Singleton pattern: `FailureEventSubmissionService` → Apply to `AdaptiveAPIClient`
- Retry queue: Similar to failure event queue for API call failures
- Configurable timeout: 30s default in SubmissionService → Same for API client
- Graceful failure handling: Don't crash scraper when API unavailable

---

## Latest Tech Information

### API Client Libraries (2026-03)

| Library | Pros | Cons |
|---------|------|------|
| httpx | Async support, connection pooling, modern | Newer than aiohttp |
| aiohttp | Battle-tested, extensive features | Slightly older API |

**Recommendation:** Use **httpx** for cleaner async API and connection pooling support

### Best Practices for API Integration

1. **Connection Pooling**: Use httpx.AsyncClient with limits
2. **Timeout**: Configure both connect and read timeouts
3. **Retries**: Use httpx-retry or custom retry logic
4. **Error Handling**: Don't expose internal errors to scraper

---

## Project Context Reference

### Technology Stack (From project-context.md)

- Python 3.11+ (asyncio-first)
- Playwright >=1.40.0
- FastAPI >=0.104.0
- SQLAlchemy >=2.0.0
- Pydantic >=2.5.0

### Naming Conventions (MUST FOLLOW)

- Classes: PascalCase (BrowserSession, AdaptiveAPIClient)
- Functions/variables: snake_case (extract_primary, api_client)
- Constants: UPPER_SNAKE_CASE (MAX_RETRIES, DEFAULT_TIMEOUT)
- Modules: snake_case (browser_management, adaptive)

### Testing Standards

- pytest markers: @pytest.mark.unit, @pytest.mark.integration
- Use pytest-mock for external dependencies
- Integration tests in tests/integration/
- Unit tests in tests/selectors/

---

## Story Completion Status

**Story ID:** 4.1
**Story Key:** 4-1-adaptive-rest-api-integration
**Epic:** 4 - Graceful Degradation
**Status:** ready-for-dev
**Created:** 2026-03-08

### Completion Notes

- Comprehensive context engine analysis completed
- All Epic 3 learnings incorporated
- Technical debt items from Epic 3 Retro identified
- Architecture patterns and requirements documented
- Developer guardrails established for flawless implementation

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

### Completion Notes List

- Story file created with full context from epics, PRD, architecture
- Epic 3 learnings and technical debt items incorporated
- All acceptance criteria and technical requirements documented
- ✅ IMPLEMENTATION COMPLETE:
  - Created AdaptiveAPIClient with singleton pattern for connection pooling
  - Created SyncAdaptiveAPIClient for synchronous usage
  - Implemented configurable timeout (default 30s per NFR4)
  - Added AdaptiveAPIIntegration class to fallback chain
  - Added AdaptiveAPIConfig for configuration management
  - Created performance tests verifying ≤5s latency (NFR1)
  - Graceful degradation on API failures/timeout

### File List

- `src/selectors/adaptive/__init__.py` (created)
- `src/selectors/adaptive/api_client.py` (created)
- `src/selectors/adaptive/sync_adapter.py` (created)
- `src/selectors/fallback/chain.py` (modified - added AdaptiveAPIIntegration)
- `src/selectors/fallback/models.py` (modified - added api_alternatives to FallbackResult)
- `src/selectors/config.py` (modified - added AdaptiveAPIConfig)
- `tests/performance/test_adaptive_api_client.py` (created)
