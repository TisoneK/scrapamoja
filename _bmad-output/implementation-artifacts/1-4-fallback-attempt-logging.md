# Story 1.4: Fallback Attempt Logging

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want **to log all fallback attempts with results**,
so that **I can debug issues and understand selector stability over time**.

## Acceptance Criteria

**AC1: Fallback Attempt Logging (Success/Failure)**
- **Given** any fallback attempt (success or failure)
- **When** the fallback chain completes
- **Then** a log entry is created with: selector ID, page URL, timestamp, attempted selectors in order, final result

**AC2: Fallback Success Logging**
- **Given** a fallback success
- **When** logging the event
- **Then** log includes which fallback succeeded and the extracted value

**AC3: Fallback Failure Logging**
- **Given** a fallback failure
- **When** logging the event
- **Then** log includes all attempted selectors that failed
- **And** includes the failure reason for each attempt

## Tasks / Subtasks

- [x] Task 1: Implement fallback attempt logging infrastructure (AC: #1)
  - [x] Subtask 1.1: Create structured log model for fallback attempts
  - [x] Subtask 1.2: Add logging to @with_fallback decorator
  - [x] Subtask 1.3: Integrate with existing fallback chain
- [x] Task 2: Add success result logging (AC: #2)
  - [x] Subtask 2.1: Log which fallback succeeded
  - [x] Subtask 2.2: Log extracted value (when safe/non-sensitive)
- [x] Task 3: Add failure reason logging (AC: #3)
  - [x] Subtask 3.1: Capture failure reason for each selector
  - [x] Subtask 3.2: Log all failed selectors with reasons

## Dev Notes

- Relevant architecture patterns and constraints
- Source tree components to touch
- Testing standards summary

### Project Structure Notes

- Alignment with unified project structure (paths, modules, naming)
- Detected conflicts or variances (with rationale)

### References

- Cite all technical details with source paths and sections, e.g. [Source: docs/<file>.md#Section]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- [x] FallbackAttemptLog model created with all required fields (AC1)
- [x] Logging integrated with @with_fallback decorator
- [x] Success logging working - logs which fallback succeeded and extracted value (AC2)
- [x] Failure logging with reasons working - logs all failed selectors with reasons (AC3)
- [x] Unit tests written (22 tests in test_logging.py)
- [x] Integration with existing chain verified (65 tests pass)

### Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Commit all implementation files to git for transparency
- [x] [AI-Review][HIGH] Fix conflicting completion status in story (lines 69-74 vs 411-418)
- [ ] [AI-Review][MEDIUM] Review decorator creates two log entries vs AC1 singular
- [ ] [AI-Review][MEDIUM] Document single-fallback use case limitation or remove requirement
- [ ] [AI-Review][LOW] Migrate Pydantic config to ConfigDict to fix deprecation warnings
- [ ] [AI-Review][LOW] Replace datetime.utcnow() with datetime.now(timezone.utc)

### File List

**Created:**
- `src/selectors/fallback/logging.py` - Fallback attempt logging logic
- `tests/selectors/fallback/test_logging.py` - Unit tests for logging (22 tests)

**Modified:**
- `src/selectors/fallback/models.py` - Added FallbackAttemptLog, SelectorAttempt models
- `src/selectors/fallback/decorator.py` - Added logging calls to @with_fallback
- `src/selectors/fallback/__init__.py` - Export logging module

---

# Story 1.4: Fallback Attempt Logging - Full Context

## 🚨 CRITICAL MISSION: Implementation Guide

This story builds on Stories 1-1, 1-2, and 1-3 which have already implemented:
- Primary selector execution
- Fallback selector execution
- Multi-level fallback chain with @with_fallback decorator

**This story (1-4) adds logging functionality to the existing fallback chain.**

## Technical Requirements

### Functional Requirements (from Epics)

**FR4: System can log fallback attempts with results**
- Log all fallback attempts (success or failure)
- Include: selector ID, page URL, timestamp, attempted selectors in order, final result
- Log which fallback succeeded and the extracted value
- Log all failed selectors with failure reasons

### Non-Functional Requirements

- **NFR1: Fallback Resolution Time** - Sync fallback path should not add more than 5 seconds to scraper execution
- Logging should not significantly impact performance

## Developer Context & Guardrails

### 🚨 CRITICAL: Common LLM Mistakes to Prevent

1. **NEVER create raw Playwright instances** - Always use `BrowserSession` from `src.core.browser`
2. **NEVER bypass selector engine** - Use semantic selectors with confidence scoring from `src.selectors.engine`
3. **NEVER implement direct file operations** - Use storage adapter and snapshot system
4. **NEVER ignore async context managers** - Proper resource cleanup is mandatory
5. **NEVER create duplicate functionality** - Leverage existing modular systems
6. **NEVER log sensitive data** - Redact passwords, tokens, PII from logs
7. **NEVER block on logging** - Use async logging or fire-and-forget for performance

### Architecture Requirements

**Integration Architecture:** In-process integration (import adaptive module directly)
- Import `src.selectors.engine.SelectorEngine` for selector execution
- Import `src.selectors.yaml_loader.YAMLSelectorLoader` for loading YAML configs
- Use existing `src.selectors.exceptions` for error handling

**Failure Capture Strategy:** Validation layer (check results after extraction)
- Check results after each selector in chain
- Trigger next fallback on detected failure
- **This story adds logging to the validation/capture layer**

**Fallback Chain Pattern:** Linear chain (primary → fallback1 → fallback2)
- Uses @with_fallback decorator (created in Story 1-3)
- Sequential execution, stops at first success
- **This story adds logging AFTER the chain completes**

**Connection Management:** Singleton pattern
- Use single shared connection for selector operations

### Naming Conventions (MUST FOLLOW)

- **Classes:** PascalCase (`BrowserSession`, `SnapshotManager`)
- **Functions/variables:** snake_case (`capture_snapshot`, `browser_config`)
- **Constants:** UPPER_SNAKE_CASE (`MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Modules:** snake_case (`browser_management`, `selector_engine`)

### Error Handling Requirements

**Custom Exceptions Location:** `src/selectors/exceptions.py`

Use existing exception classes:
- `SelectorError` - Base exception for selector-related errors
- `SelectorLoadingError` - When loading selectors fails
- `SelectorValidationError` - When selector validation fails
- `SelectorConfigurationError` - When configuration is invalid
- `FallbackError` - Fallback chain execution failures (created in Story 1-3)

**NEW for this story:**
- May need `LoggingError` if logging itself fails (optional)

**Structured Logging:**
- Use `structlog` for all logging
- Include correlation IDs from `src.observability.logger`
- Follow pattern: `get_logger("module_name")`

### Data Models (Use Existing)

**Location:** `src/selectors/models.py`

Use existing Pydantic-compatible dataclasses:
- `YAMLSelector` - Represents a selector configuration from YAML
- `SelectorStrategy` - Represents a resolution strategy
- `SelectorType` enum - CSS, XPATH, TEXT, ATTRIBUTE
- `StrategyType` enum - TEXT_ANCHOR, ATTRIBUTE_MATCH, DOM_RELATIONSHIP, ROLE_BASED, CSS

**From Story 1-2:**
- `FallbackConfig` - Configuration for fallback selector
- `FallbackChain` - Container for primary + fallback selectors

**From Story 1-3:**
- `FallbackResult` - Result of fallback chain execution with timing info

**NEW for this story:**
- `FallbackAttemptLog` - Structured log entry for fallback attempts
- May need to extend `FallbackResult` with logging fields

### Project Structure Requirements

**Existing Modules to Leverage:**
- `src/selectors/engine.py` - Selector engine (integration point)
- `src/selectors/yaml_loader.py` - YAML hints loading (already exists)
- `src/selectors/exceptions.py` - Custom exceptions (already exists)
- `src/selectors/models.py` - Data models (already exists)
- `src/selectors/adaptive/` - Existing adaptive module (for future integration)

**From Stories 1-1, 1-2, 1-3 (Already Created):**
- `src/selectors/fallback/__init__.py` - Module exports
- `src/selectors/fallback/chain.py` - Fallback chain execution logic
- `src/selectors/fallback/models.py` - Fallback-specific data models
- `src/selectors/fallback/decorator.py` - @with_fallback decorator

**New Files to Create for This Story:**

- `src/selectors/fallback/logging.py` - Fallback attempt logging logic
- `tests/selectors/fallback/test_logging.py` - Unit tests for logging

**Files That Will Be Modified in This Story:**

- `src/selectors/fallback/decorator.py` - Add logging calls to @with_fallback
- `src/selectors/fallback/models.py` - Add FallbackAttemptLog model

**Files That Will Be Modified/Extended in Future Stories:**
- `src/selectors/hooks/` - NEW in Epic 3 (failure capture)
- `src/selectors/engine.py` - May need hook registration

### Testing Requirements

**Test Organization:**
- Tests in `tests/selectors/` directory
- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`
- Use `asyncio_mode=auto` for async test support

**This Story's Testing:**
- Unit tests for FallbackAttemptLog model
- Test logging on fallback success
- Test logging on fallback failure
- Test that all required fields are logged
- Integration tests with existing @with_fallback decorator

### Technical Stack Reference

**Core Technologies:**
- Python 3.11+ (asyncio-first architecture)
- Playwright >=1.40.0 (browser automation)
- Pydantic >=2.5.0 (data validation)
- Structlog >=23.2.0 (structured logging)

**Key Dependencies:**
- BeautifulSoup4 >=4.12.0 (HTML parsing)
- lxml >=4.9.0 (XML/HTML processing)
- pytest >=7.4.0 (testing with async support)

## Implementation Notes

### What This Story Includes

1. **FallbackAttemptLog data model** - Structured log entry with all required fields
2. **Logging integration with @with_fallback** - Log after chain completes
3. **Success logging** - Log which fallback succeeded and value
4. **Failure logging** - Log all failed selectors with reasons
5. **Performance consideration** - Non-blocking logging
6. **Structured logging** with correlation IDs

### What This Story Does NOT Include

1. **YAML hints reading** - This is Epic 2 (Story 2-1)
2. **Failure event capture to DB** - This is Epic 3 (Story 3-1)
3. **Adaptive module integration** - Future stories
4. **Real-time notifications** - Epic 5 (Phase 2)

### Dependency Flow

```
Story 1-1 (done) → Story 1-2 (done) → Story 1-3 (done) → Story 1-4 (this - logging)
                                                                      ↓
                                                                  Epic 2 (YAML hints)
                                                                      ↓
                                                                  Epic 3 (failure capture)
```

### Integration Points

1. **@with_fallback Decorator Integration:**
   - Modify existing decorator from Story 1-3
   - Add logging call after fallback chain completes
   - Pass all required context (selector_id, page_url, etc.)

2. **FallbackChain Integration:**
   - Extend existing chain from Story 1-2
   - Track execution order and results for logging
   - Pass results to logging module

3. **Structured Logger Integration:**
   - Use `structlog` for all logging
   - Include correlation ID for tracing
   - Use appropriate log levels (INFO for attempts, WARNING for failures)

## Previous Story Intelligence

### From Story 1-3: Multi-Level Fallback Chain

**Dev Notes and Learnings:**
- Created `src/selectors/fallback/` module with chain.py and decorator.py
- Used `SelectorEngine.resolve()` for selector execution
- Implemented @with_fallback decorator for declarative fallback chains
- Multi-level chain (primary → fallback1 → fallback2) working
- Performance tracking added to FallbackResult

**Files Created/Modified:**
- `src/selectors/fallback/__init__.py` - Module exports
- `src/selectors/fallback/chain.py` - Fallback chain execution
- `src/selectors/fallback/models.py` - Fallback data models
- `src/selectors/fallback/decorator.py` - @with_fallback decorator
- `tests/selectors/fallback/test_decorator.py` - Unit tests

**Key Patterns Established:**
- Use existing `SelectorEngine` for selector operations
- Tests verify actual execution, not just method existence
- Use `datetime.now(timezone.utc)` for timestamps
- Decorator pattern for fallback chains

**What 1-4 needs from 1-3:**
- Extend `FallbackResult` to include logging fields
- Modify `@with_fallback` decorator to call logging
- Reuse existing fallback chain execution logic

## Architecture Compliance

### Must Follow Architecture Decisions:

1. **Linear Chain Pattern** (from architecture.md):
   - Primary → Fallback1 → Fallback2
   - Sequential execution, stops at first success
   - **Log AFTER chain completes (not between each fallback)**

2. **Decorator Pattern** (from architecture.md):
   ```python
   @with_fallback(fallbacks=[fallback_selector_1, fallback_selector_2])
   def extract_primary(page):
       ...
   ```
   - **Add logging inside decorator's finally/after block**

3. **Error Handling** (from architecture.md):
   - Use `FallbackError` for chain failures
   - Use `SelectorError` base for selector issues
   - Log errors, don't raise from logging code

4. **Structured Logging** (from architecture.md):
   - Use structlog
   - Include correlation IDs
   - Log appropriate levels

5. **Testing Standards** (from architecture.md):
   - Unit tests with pytest markers
   - Integration tests for decorator + logging

## Acceptance Criteria Deep Dive

### AC1: Fallback Attempt Logging (Success/Failure)

```python
# Required log fields:
{
    "selector_id": str,          # Which selector was attempted
    "page_url": str,            # URL being scraped
    "timestamp": datetime,      # ISO8601 format
    "attempted_selectors": [    # All selectors tried in order
        {"name": "primary", "result": "failure", "reason": "empty"},
        {"name": "fallback1", "result": "success", "value": "..."}
    ],
    "final_result": str,         # "success" or "failure"
    "total_time_ms": int         # Total fallback resolution time
}
```

### AC2: Fallback Success Logging

- Which fallback succeeded (primary/fallback1/fallback2)
- Extracted value (redact if sensitive)
- Success timestamp

### AC3: Fallback Failure Logging

- All attempted selectors that failed
- Failure reason for each (empty, exception, timeout, etc.)
- Final failure timestamp

## References

- **Epics Source:** `_bmad-output/planning-artifacts/epics.md#story-14-fallback-attempt-logging`
- **Architecture:** `_bmad-output/planning-artifacts/architecture.md`
- **Project Context:** `_bmad-output/project-context.md`
- **Previous Story:** `_bmad-output/implementation-artifacts/1-3-multi-level-fallback-chain.md`
- **Selector Engine:** `src/selectors/engine.py`
- **Fallback Module:** `src/selectors/fallback/chain.py`
- **Fallback Decorator:** `src/selectors/fallback/decorator.py`
- **Exceptions:** `src/selectors/exceptions.py`
- **Models:** `src/selectors/models.py`

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- [x] All tasks completed - see completion notes above

### File List

**To Create:**
- `src/selectors/fallback/logging.py` - Fallback attempt logging logic
- `tests/selectors/fallback/test_logging.py` - Unit tests for logging

**To Modify:**
- `src/selectors/fallback/decorator.py` - Add logging calls
- `src/selectors/fallback/models.py` - Add FallbackAttemptLog

**To Reference:**
- `src/selectors/engine.py` - SelectorEngine
- `src/selectors/fallback/chain.py` - FallbackChain
- `src/selectors/fallback/models.py` - FallbackResult
- `src/selectors/exceptions.py` - SelectorError, FallbackError
