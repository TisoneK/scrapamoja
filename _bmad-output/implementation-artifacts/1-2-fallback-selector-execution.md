# Story 1.2: Fallback Selector Execution

**Status:** done

**Epic:** 1 - Automatic Fallback Resolution  
**Story Key:** 1-2-fallback-selector-execution  
**Generated:** 2026-03-06

---

## Story

As a **scraper system**,
I want **to execute a fallback selector when the primary fails**,
so that **data extraction continues even when the primary selector breaks due to DOM changes**.

## Acceptance Criteria

**AC1: Fallback Selector Execution**
- **Given** a primary selector that fails (returns empty or raises exception)
- **When** the fallback mechanism is triggered
- **Then** the fallback selector is executed against the same page
- **And** the fallback result is returned if successful

**AC2: Failure Event Logging**
- **Given** a primary selector failure with error details
- **When** the fallback is attempted
- **Then** the failure event is logged with selector ID, URL, timestamp, and failure type
- **And** the fallback attempt result is also logged

## Technical Requirements

### Functional Requirements (from Epics)

1. **FR2: System can execute fallback selector when primary fails**
   - Detect primary selector failure (empty result or exception)
   - Trigger fallback chain execution
   - Execute fallback selector against same page context
   - Return fallback result if successful

### Non-Functional Requirements

- **NFR1: Fallback Resolution Time** - Sync fallback path should not add more than 5 seconds to scraper execution
- **NFR4: API Timeout Handling** - External API calls have configurable timeouts (default 30s) with appropriate error handling

## Developer Context & Guardrails

### 🚨 CRITICAL: Common LLM Mistakes to Prevent

1. **NEVER create raw Playwright instances** - Always use `BrowserSession` from `src.core.browser`
2. **NEVER bypass selector engine** - Use semantic selectors with confidence scoring from `src.selectors.engine`
3. **NEVER implement direct file operations** - Use storage adapter and snapshot system
4. **NEVER ignore async context managers** - Proper resource cleanup is mandatory
5. **NEVER create duplicate functionality** - Leverage existing modular systems

### Architecture Requirements

**Integration Architecture:** In-process integration (import adaptive module directly)
- Import `src.selectors.engine.SelectorEngine` for selector execution
- Import `src.selectors.yaml_loader.YAMLSelectorLoader` for loading YAML configs
- Use existing `src.selectors.exceptions` for error handling

**Failure Capture Strategy:** Validation layer (check results after extraction)
- Check results after primary extraction completes
- Trigger fallback on detected failure

**Fallback Chain Pattern:** Linear chain (primary → fallback1 → fallback2)
- This story implements single-level fallback
- Story 1-3 will add multi-level chaining

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

**NEW for this story:**
- `FallbackError` - Fallback chain execution failures (add to exceptions.py if needed)

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

**NEW for this story:**
- `FallbackConfig` - Configuration for fallback selector (selector name, priority, etc.)
- `FallbackChain` - Container for primary + fallback selectors

### Project Structure Requirements

**Existing Modules to Leverage:**
- `src/selectors/engine.py` - Selector engine (integration point)
- `src/selectors/yaml_loader.py` - YAML hints loading (already exists)
- `src/selectors/exceptions.py` - Custom exceptions (already exists)
- `src/selectors/models.py` - Data models (already exists)
- `src/selectors/adaptive/` - Existing adaptive module (for future integration)

**New Files to Create for This Story:**

This story establishes fallback execution:
- `src/selectors/fallback/__init__.py` - Module exports
- `src/selectors/fallback/chain.py` - Fallback chain execution logic
- `src/selectors/fallback/models.py` - Fallback-specific data models
- `tests/selectors/fallback/test_chain.py` - Unit tests for fallback chain

**Files That Will Be Modified/Extended in Future Stories:**
- `src/selectors/fallback/decorator.py` - NEW in Story 1-3 (@with_fallback decorator)
- `src/selectors/hooks/` - NEW in Story 3-1 (failure capture)
- `src/selectors/engine.py` - May need hook registration

### Testing Requirements

**Test Organization:**
- Tests in `tests/selectors/` directory
- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`
- Use `asyncio_mode=auto` for async test support

**This Story's Testing:**
- Unit tests for fallback chain execution
- Integration tests with existing selector engine
- Mock Playwright browser instances in unit tests
- Test fallback triggering on primary failure
- Test failure event logging

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

1. **Fallback chain execution** - Detect primary failure and execute fallback
2. **Failure event capture** - Log failure details (selector ID, URL, timestamp, type)
3. **Fallback result handling** - Return fallback result if successful
4. **Linear chain foundation** - Single-level fallback (Story 1-3 adds multi-level)
5. **Error handling** using existing exception classes
6. **Structured logging** with correlation IDs

### What This Story Does NOT Include

1. **Multi-level fallback chaining** - This is Story 1-3
2. **@with_fallback decorator** - This is Story 1-3
3. **YAML hints reading** - This is Epic 2 (Story 2-1)
4. **Failure event capture to DB** - This is Epic 3 (Story 3-1)
5. **Adaptive module integration** - Future stories

### Dependency Flow

```
Story 1-1 (done) → Story 1-2 (this) → Story 1-3 (chain) → Story 1-4 (logging)
                        ↓
                   Epic 2 (YAML hints)
                        ↓
                   Epic 3 (failure capture)
```

### Integration Points

1. **Selector Engine Integration:**
   - Use `SelectorEngine.resolve(selector_name, context)` for fallback execution
   - Pass `DOMContext` for page context
   - Handle `SelectorError` exceptions

2. **YAML Loader Integration:**
   - Use `YAMLSelectorLoader.load_selector_from_file(file_path)` to get fallback config
   - Look for fallback selector definitions in YAML

3. **Failure Event Logging:**
   - Create structured log entry for primary failure
   - Include: selector_id, page_url, timestamp, failure_type
   - Log fallback attempt result

## Previous Story Intelligence

### From Story 1-1: Primary Selector Execution

**Dev Notes and Learnings:**
- Used `SelectorEngine.resolve()` for primary selector execution
- Fixed broken imports in `src/selectors.yaml_loader` and `src/selectors.validator`
- Tests verify actual execution with mock page, not just attribute existence

**Files Created/Modified:**
- `src/selectors/yaml_loader.py` - Fixed broken imports
- `src/selectors/validator.py` - Fixed broken imports
- `tests/selectors/test_primary_selector_execution.py` - 12 tests

**Key Patterns Established:**
- Use existing `SelectorEngine` for selector operations
- Import from correct modules (not recreated)
- Tests should verify actual execution, not just method existence

## References

- **Epics Source:** `_bmad-output/planning-artifacts/epics.md#story-12-fallback-selector-execution`
- **Architecture:** `_bmad-output/planning-artifacts/architecture.md`
- **Project Context:** `_bmad-output/project-context.md`
- **Previous Story:** `_bmad-output/implementation-artifacts/1-1-primary-selector-execution.md`
- **Selector Engine:** `src/selectors/engine.py`
- **YAML Loader:** `src/selectors/yaml_loader.py`
- **Exceptions:** `src/selectors/exceptions.py`
- **Models:** `src/selectors/models.py`

---

## Dev Agent Record

### Agent Model Used

MiniMax M2.5 (free tier)

### Debug Log References

- Tests to create: tests/selectors/fallback/test_chain.py

### Completion Notes List

- [x] Fallback chain execution working
- [x] Primary failure detection functional
- [x] Fallback selector execution working
- [x] Failure event logging implemented
- [x] Error handling implemented
- [x] Structured logging added
- [x] Unit tests written (20 tests, all passing)

### Code Review Fixes (2026-03-07)

- [x] Fixed deprecated `datetime.utcnow()` usage - replaced with `datetime.now(timezone.utc)` in:
  - `src/selectors/fallback/chain.py` (9 occurrences)
  - `src/selectors/fallback/models.py` (1 occurrence)
  - `tests/selectors/fallback/test_chain.py` (4 occurrences)
- [x] Added `timezone` import to all affected files

### File List

**To Create:**
- `src/selectors/fallback/__init__.py` - Module exports
- `src/selectors/fallback/chain.py` - Fallback chain execution
- `src/selectors/fallback/models.py` - Fallback data models
- `tests/selectors/fallback/test_chain.py` - Unit tests

**To Reference:**
- `src/selectors/engine.py` - SelectorEngine
- `src/selectors/context.py` - DOMContext
- `src/selectors/exceptions.py` - SelectorError classes
- `src/models/selector_models.py` - SemanticSelector, StrategyPattern
