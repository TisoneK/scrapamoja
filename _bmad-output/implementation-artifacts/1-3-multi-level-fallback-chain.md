# Story 1.3: Multi-Level Fallback Chain

**Status:** done

**Epic:** 1 - Automatic Fallback Resolution  
**Story Key:** 1-3-multi-level-fallback-chain  
**Generated:** 2026-03-07

---

## Story

As a **scraper system**,
I want **to chain multiple fallback levels (minimum 2)**,
so that **there are multiple recovery options when the first fallback also fails**.

## Acceptance Criteria

**AC1: Multi-Level Fallback Execution**
- **Given** a primary selector failure
- **When** the fallback chain is executed
- **Then** fallback1 is attempted first
- **And** if fallback1 succeeds, the result is returned
- **And** if fallback1 fails, fallback2 is attempted

**AC2: All Fallbacks Fail**
- **Given** both fallback1 and fallback2 fail
- **When** the fallback chain completes
- **Then** the system returns failure with all attempted selectors logged
- **And** the chain stops at the first successful fallback

**AC3: Performance Monitoring**
- **Given** a linear chain configuration (primary → fallback1 → fallback2)
- **When** the chain executes
- **Then** each selector is tried in order until success or all fail
- **And** the total fallback resolution time is tracked for performance monitoring

## Technical Requirements

### Functional Requirements (from Epics)

1. **FR3: System can chain multiple fallback levels (minimum 2)**
   - Build multi-level fallback chain structure
   - Execute selectors in order (primary → fallback1 → fallback2)
   - Return first successful result
   - Track all attempted selectors

### Non-Functional Requirements

- **NFR1: Fallback Resolution Time** - Sync fallback path should not add more than 5 seconds to scraper execution

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
- Check results after each selector in chain
- Trigger next fallback on detected failure

**Fallback Chain Pattern:** Linear chain (primary → fallback1 → fallback2)
- This story implements multi-level chaining
- Use @with_fallback decorator (NEW in this story)
- Sequential execution, stops at first success

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
- `FallbackError` - Fallback chain execution failures

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

**NEW for this story:**
- `FallbackResult` - Result of fallback chain execution with timing info

### Project Structure Requirements

**Existing Modules to Leverage:**
- `src/selectors/engine.py` - Selector engine (integration point)
- `src/selectors/yaml_loader.py` - YAML hints loading (already exists)
- `src/selectors/exceptions.py` - Custom exceptions (already exists)
- `src/selectors/models.py` - Data models (already exists)
- `src/selectors/adaptive/` - Existing adaptive module (for future integration)

**From Story 1-2 (Already Created):**
- `src/selectors/fallback/__init__.py` - Module exports
- `src/selectors/fallback/chain.py` - Fallback chain execution logic
- `src/selectors/fallback/models.py` - Fallback-specific data models

**New Files to Create for This Story:**

- `src/selectors/fallback/decorator.py` - @with_fallback decorator
- `tests/selectors/fallback/test_decorator.py` - Unit tests for decorator

**Files That Will Be Modified/Extended in Future Stories:**
- `src/selectors/hooks/` - NEW in Story 3-1 (failure capture)
- `src/selectors/engine.py` - May need hook registration

### Testing Requirements

**Test Organization:**
- Tests in `tests/selectors/` directory
- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`
- Use `asyncio_mode=auto` for async test support

**This Story's Testing:**
- Unit tests for @with_fallback decorator
- Test multi-level chain execution (primary → fallback1 → fallback2)
- Test performance tracking for fallback resolution
- Integration tests with existing selector engine
- Mock Playwright browser instances in unit tests

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

1. **@with_fallback decorator** - Declarative fallback chain definition
2. **Multi-level fallback execution** - Chain 2+ fallback levels
3. **Performance tracking** - Track total fallback resolution time
4. **Linear chain logic** - Execute selectors in order until success or all fail
5. **Result tracking** - Return first successful result
6. **Error handling** using existing exception classes
7. **Structured logging** with correlation IDs

### What This Story Does NOT Include

1. **Fallback attempt logging** - This is Story 1-4
2. **YAML hints reading** - This is Epic 2 (Story 2-1)
3. **Failure event capture to DB** - This is Epic 3 (Story 3-1)
4. **Adaptive module integration** - Future stories

### Dependency Flow

```
Story 1-1 (done) → Story 1-2 (done) → Story 1-3 (this) → Story 1-4 (logging)
                                              ↓
                                         Epic 2 (YAML hints)
                                              ↓
                                         Epic 3 (failure capture)
```

### Integration Points

1. **Selector Engine Integration:**
   - Use `SelectorEngine.resolve(selector_name, context)` for all selector executions
   - Pass `DOMContext` for page context
   - Handle `SelectorError` exceptions

2. **Fallback Chain Integration:**
   - Extend existing `FallbackChain` from Story 1-2
   - Use `FallbackConfig` for each fallback level
   - Track execution order and results

3. **Decorator Pattern:**
   - Create `@with_fallback(fallbacks=[...])` decorator
   - Decorate extraction functions with fallback chains
   - Chain multiple fallbacks cleanly

## Previous Story Intelligence

### From Story 1-2: Fallback Selector Execution

**Dev Notes and Learnings:**
- Created `src/selectors/fallback/` module with chain.py and models.py
- Used `SelectorEngine.resolve()` for fallback selector execution
- Fixed deprecated `datetime.utcnow()` usage - replaced with `datetime.now(timezone.utc)`
- Tests verify actual execution with mock page

**Files Created/Modified:**
- `src/selectors/fallback/__init__.py` - Module exports
- `src/selectors/fallback/chain.py` - Fallback chain execution (single-level)
- `src/selectors/fallback/models.py` - Fallback data models
- `tests/selectors/fallback/test_chain.py` - 20 tests

**Key Patterns Established:**
- Use existing `SelectorEngine` for selector operations
- Tests should verify actual execution, not just method existence
- Use `datetime.now(timezone.utc)` for timestamps (not deprecated `utcnow()`)

## Architecture Compliance

### Must Follow Architecture Decisions:

1. **Linear Chain Pattern** (from architecture.md):
   - Primary → Fallback1 → Fallback2
   - Sequential execution, stops at first success
   - YAML hints determine fallback order (future Epic 2)

2. **Decorator Pattern** (from architecture.md):
   ```python
   @with_fallback(fallbacks=[fallback_selector_1, fallback_selector_2])
   def extract_primary(page):
       ...
   ```
   - Declarative, easy to understand
   - Chain multiple fallbacks cleanly
   - Located in `src/selectors/fallback/decorator.py`

3. **Error Handling** (from architecture.md):
   - Use `FallbackError` for chain failures
   - Use `SelectorError` base for selector issues

4. **Testing Standards** (from architecture.md):
   - Unit tests with pytest markers
   - Integration tests for hook wiring

## References

- **Epics Source:** `_bmad-output/planning-artifacts/epics.md#story-13-multi-level-fallback-chain`
- **Architecture:** `_bmad-output/planning-artifacts/architecture.md`
- **Project Context:** `_bmad-output/project-context.md`
- **Previous Story:** `_bmad-output/implementation-artifacts/1-2-fallback-selector-execution.md`
- **Selector Engine:** `src/selectors/engine.py`
- **Fallback Module:** `src/selectors/fallback/chain.py`
- **Exceptions:** `src/selectors/exceptions.py`
- **Models:** `src/selectors/models.py`

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

- Tests to create: tests/selectors/fallback/test_decorator.py

### Completion Notes List

- [x] @with_fallback decorator implemented
- [x] Multi-level fallback chain execution working
- [x] Performance tracking for fallback resolution
- [x] Linear chain pattern verified
- [x] Error handling implemented
- [x] Structured logging added
- [x] Unit tests written

### File List

**To Create:**
- `src/selectors/fallback/decorator.py` - @with_fallback decorator
- `tests/selectors/fallback/test_decorator.py` - Unit tests for decorator

**To Reference:**
- `src/selectors/engine.py` - SelectorEngine
- `src/selectors/fallback/chain.py` - FallbackChain from Story 1-2
- `src/selectors/fallback/models.py` - FallbackConfig, FallbackChain
- `src/selectors/context.py` - DOMContext
- `src/selectors/exceptions.py` - SelectorError, FallbackError
- `src/models/selector_models.py` - SemanticSelector, StrategyPattern
