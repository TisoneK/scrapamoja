# Story 4.2: Service Unavailability Handling

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **scraper system**,
I want **to handle adaptive service unavailability gracefully**,
So that **the scraper continues with primary selectors when the adaptive module is down**.

## Acceptance Criteria

1. **Given** the adaptive module is completely unavailable **When** a selector fails and fallback is needed **Then** the system detects the unavailability **And** continues with primary selectors only **And** logs a warning about adaptive service being unavailable

2. **Given** adaptive service timeout **When** the API call exceeds the timeout **Then** the timeout exception is caught **And** fallback to primary selector continues **And** the timeout is logged for diagnostics

3. **Given** intermittent adaptive service failures **When** a request fails **Then** retry logic is applied (configurable retries) **And** if all retries fail, graceful degradation kicks in

4. **Given** recovery of adaptive service **When** a new request is made after unavailability **Then** the system detects the service is back **And** normal adaptive integration resumes **And** no manual restart is required

## Tasks / Subtasks

- [x] Task 1: Implement service availability detection (AC: 1, 4)
  - [x] Subtask 1.1: Add health check method to AdaptiveAPIClient
  - [x] Subtask 1.2: Implement connection state tracking (available/unavailable/recovering)
  - [x] Subtask 1.3: Add automatic recovery detection on next request
- [x] Task 2: Handle complete service unavailability (AC: 1)
  - [x] Subtask 2.1: Detect ConnectionError, HTTPError exceptions from API calls
  - [x] Subtask 2.2: Skip adaptive API and continue with primary selectors
  - [x] Subtask 2.3: Log warning with diagnostic information
- [x] Task 3: Handle service timeout (AC: 2)
  - [x] Subtask 3.1: Catch timeout exceptions from httpx/aiohttp
  - [x] Subtask 3.2: Log timeout diagnostics with selector_id and page_url
  - [x] Subtask 3.3: Fallback to primary selector on timeout
- [x] Task 4: Implement retry logic with graceful degradation (AC: 3)
  - [x] Subtask 4.1: Add configurable retry count (default: 3)
  - [x] Subtask 4.2: Add exponential backoff between retries
  - [x] Subtask 4.3: After all retries fail, activate graceful degradation
- [x] Task 5: Service recovery detection (AC: 4)
  - [x] Subtask 5.1: Track time since last failure
  - [x] Subtask 5.2: Retry connection after recovery timeout (default: 60s)
  - [x] Subtask 5.3: Resume normal adaptive integration automatically

## Dev Notes

### Architecture Patterns (MUST FOLLOW)

- **Integration Pattern**: In-process integration (import adaptive module directly into scraper)
- **Connection Management**: Singleton pattern (single shared connection)
- **Fallback Chain Pattern**: Linear chain (primary → fallback1 → fallback2 → API alternatives → graceful degradation)
- **Implementation Pattern**: Use @with_fallback decorator for fallback chains
- **Graceful Degradation**: When adaptive service unavailable, scraper continues with YAML-defined fallbacks only

### Project Structure

```
src/selectors/
├── adaptive/
│   ├── __init__.py              # EXISTS from Story 4-1
│   ├── api_client.py           # EXISTS - Modify to add unavailability handling
│   └── sync_adapter.py         # EXISTS from Story 4-1
├── fallback/
│   ├── __init__.py             # EXISTS
│   ├── chain.py                # EXISTS - Modify for graceful degradation
│   └── models.py               # EXISTS
└── config.py                   # EXISTS - Add service availability config
```

### Existing Components to Leverage

- `src/selectors/adaptive/api_client.py` - AdaptiveAPIClient from Story 4-1 (add unavailability handling)
- `src/selectors/adaptive/sync_adapter.py` - SyncAdaptiveAPIClient from Story 4-1
- `src/selectors/fallback/chain.py` - FallbackChainExecutor (add graceful degradation)
- `src/selectors/hooks/submission.py` - FailureEventSubmissionService (singleton pattern reference)
- `src/selectors/config.py` - Configuration from Story 4-1

### Technical Requirements

1. **Async/Await**: ALL I/O operations must use `async def`
2. **Type Safety**: MyPy strict mode - all functions need type annotations
3. **Pydantic Models**: Use Pydantic models for all data transfer objects
4. **Custom Exceptions**: Use exceptions from `src/selectors/exceptions.py`
5. **Structured Logging**: Use structlog with correlation IDs

### Dependencies for Epic 4 Story 4-2

Epic 4-2 builds on:
- ✅ Story 4-1: Adaptive REST API Integration (complete, in review)
- ✅ Epic 3: Failure Event Capture & Logging (complete)
- ✅ Epic 2: YAML Hints & Selector Prioritization (complete)
- ✅ Epic 1: Automatic Fallback Resolution (complete)

---

## Dev Agent Guardrails

### Technical Requirements

| Requirement | Details | Source |
|-------------|---------|--------|
| Graceful Degradation | Scrapers continue with primary selectors when adaptive unavailable | NFR3 |
| API Timeout | Default 30s, configurable | NFR4 |
| Retry Logic | Configurable retries (default 3) | Epic 4-2 AC3 |
| Recovery Detection | Auto-resume after 60s (configurable) | Epic 4-2 AC4 |
| Fallback Resolution Time | ≤5 seconds total | NFR1 |

### Architecture Compliance

| Decision | Implementation | Source |
|----------|----------------|--------|
| In-process Integration | Import adaptive module directly | Architecture |
| Singleton Pattern | Single shared connection for API client | Architecture |
| Decorator Pattern | @with_fallback for fallback chains | Architecture |
| Graceful Degradation | Skip adaptive, continue with YAML fallbacks | Epic 4-2 |
| Linear Chain | Primary → Fallback1 → Fallback2 → API → Degrade | Epic 4 |

### Library/Framework Requirements

| Component | Technology | Version |
|-----------|------------|---------|
| HTTP Client | httpx | Latest stable (from 4-1) |
| Async | asyncio | Built-in |
| Type Annotations | MyPy strict | >=1.7.0 |
| Data Models | Pydantic | >=2.5.0 |

### File Structure Requirements

**Files to Modify:**
- `src/selectors/adaptive/api_client.py` - Add unavailability detection and graceful degradation
- `src/selectors/adaptive/sync_adapter.py` - Add unavailability handling to sync wrapper
- `src/selectors/fallback/chain.py` - Integrate graceful degradation in fallback chain
- `src/selectors/config.py` - Add service availability configuration

**New Files (if needed):**
- `src/selectors/adaptive/availability.py` - Service availability tracker (optional, can be in api_client)

### Testing Requirements

| Test Type | Location | Requirements |
|-----------|----------|--------------|
| Unit Tests | `tests/selectors/adaptive/` | @pytest.mark.unit |
| Integration Tests | `tests/integration/` | @pytest.mark.integration |
| Failure Scenario Tests | `tests/selectors/fallback/` | Mock unavailable service |

### Critical Don't-Miss Rules

- **ALWAYS** log warnings when adaptive service is unavailable (AC1)
- **ALWAYS** log timeout diagnostics with selector_id and page_url (AC2)
- **ALWAYS** implement configurable retry logic before graceful degradation (AC3)
- **ALWAYS** auto-detect service recovery without manual restart (AC4)
- **NEVER** crash the scraper when adaptive service fails
- **NEVER** block scraper operation - always have fallback path ready
- **ALWAYS** propagate correlation IDs through all operations

---

## Previous Story Intelligence

### From Story 4-1 (CRITICAL - READ BEFORE IMPLEMENTATION)

Story 4-1 created the AdaptiveAPIClient with:
- Singleton pattern for connection management
- Configurable timeout (default 30s)
- Connection pooling via httpx.AsyncClient
- Sync wrapper (SyncAdaptiveAPIClient) for synchronous usage

**Files to reuse/extend:**
- `src/selectors/adaptive/api_client.py` - ADD unavailability handling to existing class
- `src/selectors/adaptive/sync_adapter.py` - ADD unavailability handling to sync wrapper

**Key patterns from Story 4-1:**
- Singleton pattern for AdaptiveAPIClient
- Configurable timeout in AdaptiveAPIConfig
- Graceful failure handling (already exists partially)

### From Epic 3 (Context)

**Existing patterns to leverage:**
- `FailureEventSubmissionService` - Uses retry queue and graceful failure handling
- `PostExtractionValidator` - Validation layer pattern
- Retry queue with max size limit → Apply similar pattern for API retries

---

## Latest Tech Information

### Graceful Degradation Patterns (2026)

| Pattern | Use Case | Implementation |
|---------|----------|----------------|
| Circuit Breaker | Prevent cascade failures | Track failures, open circuit after threshold |
| Retry with Backoff | Transient failures | Exponential backoff, max retries |
| Fallback Chain | Ultimate backup | Continue with primary selectors |
| Health Check | Detect recovery | Ping service before request |

**Recommendation:** Implement a lightweight circuit breaker pattern:
- Track consecutive failures
- After 3 failures, mark service unavailable
- After 60s (configurable), try once to recover
- If recovery fails, reset failure count and try again

### Best Practices for Service Unavailability

1. **Detection**: Catch httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError
2. **Logging**: Use WARNING level, include selector_id, page_url, error type
3. **Retry**: Exponential backoff (1s, 2s, 4s) with max 3 attempts
4. **Recovery**: Track last successful call time, retry after timeout

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

**Story ID:** 4.2
**Story Key:** 4-2-service-unavailability-handling
**Epic:** 4 - Graceful Degradation
**Status:** review
**Created:** 2026-03-08
**Completed:** 2026-03-08

### Completion Notes

- Comprehensive context engine analysis completed
- Story 4-1 AdaptiveAPIClient foundation identified for extension
- Graceful degradation patterns documented
- All acceptance criteria mapped to implementation tasks
- Developer guardrails established for flawless implementation

### Implementation Summary

#### Files Modified:
- `src/selectors/adaptive/api_client.py` - Added service availability tracking, circuit breaker, retry logic
- `src/selectors/adaptive/sync_adapter.py` - Added synchronous service availability handling
- `src/selectors/config.py` - Added service availability configuration options

#### New Files:
- `tests/selectors/adaptive/test_service_unavailability.py` - Comprehensive unit tests

#### Key Features Implemented:
1. **ServiceState Enum**: AVAILABLE, UNAVAILABLE, RECOVERING states
2. **Circuit Breaker Pattern**: After 3 consecutive failures, service marked unavailable
3. **Retry with Exponential Backoff**: Default 3 retries with 2.0 backoff factor
4. **Recovery Detection**: After 60s recovery timeout, attempts to reconnect
5. **Graceful Degradation**: Returns empty alternatives when service unavailable

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

### Completion Notes List
