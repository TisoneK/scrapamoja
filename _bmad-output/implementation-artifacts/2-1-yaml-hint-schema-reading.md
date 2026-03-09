# Story 2.1: YAML Hint Schema Reading

**Status:** done

**Epic:** 2 - YAML Hints & Selector Prioritization  
**Story Key:** 2-1-yaml-hint-schema-reading  
**Generated:** 2026-03-07

---

## Story

As a **scraper system**,
I want **to read hint schema from YAML selectors**,
so that **the system can understand the metadata and hints defined for each selector**.

## Acceptance Criteria

**AC1: YAML Hint Parsing**
- **Given** a YAML selector configuration file
- **When** the selector engine loads the configuration
- **Then** all hint fields are parsed from the YAML
- **And** the hints are available to the fallback chain logic

**AC2: Hint Deserialization**
- **Given** a YAML selector with hints defined (stability, priority, alternatives)
- **When** the selector is loaded
- **Then** the hints are deserialized into a structured format
- **And** stored with the selector metadata

**AC3: Default Hint Values**
- **Given** a YAML selector without hints
- **When** the selector is loaded
- **Then** default hint values are applied
- **And** no errors are raised

## Technical Requirements

### Functional Requirements (from Epics)

1. **FR5: System can read hint schema from YAML selectors**
   - Parse all hint fields from YAML configuration
   - Deserialize hints into structured format
   - Make hints available to fallback chain logic
   - Apply default values for missing hints

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
6. **NEVER parse YAML manually** - Use existing `YAMLSelectorLoader`

### Architecture Requirements

**Integration Architecture:** In-process integration (import adaptive module directly)
- Import `src.selectors.yaml_loader.YAMLSelectorLoader` for loading YAML configs
- Use existing `src.selectors.exceptions` for error handling
- Extend existing YAML loading infrastructure

**Failure Capture Strategy:** Validation layer (check results after extraction)
- This story focuses on loading hints, not failure capture

**Fallback Chain Pattern:** Linear chain (primary → fallback1 → fallback2)
- Hints will influence fallback chain behavior in Story 2-2

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
- `SelectorHint` - Data model for selector hints (stability, priority, alternatives)
- `HintSchema` - Schema for validating YAML hint fields

### Project Structure Requirements

**Existing Modules to Leverage:**
- `src/selectors/yaml_loader.py` - YAML selector loading (already exists)
- `src/selectors/exceptions.py` - Custom exceptions (already exists)
- `src/selectors/models.py` - Data models (already exists)
- `src/selectors/engine.py` - Selector engine (integration point)

**New Files to Create for This Story:**
- `src/selectors/hints/__init__.py` - Module exports
- `src/selectors/hints/models.py` - Hint data models
- `src/selectors/hints/parser.py` - Hint parsing logic
- `tests/selectors/hints/test_parser.py` - Unit tests for hint parsing

**Files That Will Be Modified in This Story:**
- `src/selectors/yaml_loader.py` - Extend to parse hint fields
- `src/selectors/models.py` - Add SelectorHint and HintSchema models

**Files That Will Be Modified/Extended in Future Stories:**
- `src/selectors/fallback/chain.py` - Use hints for fallback strategy (Story 2-2)
- `src/selectors/fallback/decorator.py` - Use hints for prioritization (Story 2-3)

### Testing Requirements

**Test Organization:**
- Tests in `tests/selectors/` directory
- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`
- Use `asyncio_mode=auto` for async test support

**This Story's Testing:**
- Unit tests for hint parsing
- Test YAML file loading with hints
- Test deserialization of hint fields
- Test default value application
- Integration tests with existing YAMLSelectorLoader

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
- PyYAML >=6.0 (YAML parsing)

## Implementation Notes

### What This Story Includes

1. **YAML hint schema reading** - Parse hint fields from YAML configuration
2. **Hint deserialization** - Convert YAML hints to structured Python objects
3. **Default hint values** - Apply sensible defaults for missing hints
4. **Integration with existing YAML loader** - Extend YAMLSelectorLoader
5. **Structured logging** with correlation IDs

### What This Story Does NOT Include

1. **Hint-based fallback strategy** - This is Story 2-2
2. **Stability-based prioritization** - This is Story 2-3
3. **Failure event capture** - This is Epic 3
4. **Adaptive module integration** - Future stories

### Dependency Flow

```
Story 1-1 (done) → Story 1-2 (done) → Story 1-3 (done) → Story 1-4 (done)
                                                              ↓
                                                    Epic 2 (YAML hints) → Story 2-1 (this) → Story 2-2 → Story 2-3
                                                              ↓
                                                    Epic 3 (failure capture)
```

### Integration Points

1. **YAMLSelectorLoader Integration:**
   - Extend existing `YAMLSelectorLoader` to parse hint fields
   - Modify `load_selector_from_file()` to extract hints
   - Store hints in Selector metadata

2. **Selector Engine Integration:**
   - Make hints available through SelectorEngine
   - Pass hints to fallback chain logic
   - Hints influence fallback behavior in Story 2-2

3. **Data Model Integration:**
   - Create `SelectorHint` and `HintSchema` models
   - Integrate with existing YAMLSelector model

## Previous Story Intelligence

### From Story 1-4: Fallback Attempt Logging

**Dev Notes and Learnings:**
- Completed fallback chain implementation with @with_fallback decorator
- Created `src/selectors/fallback/` module with chain.py, decorator.py, models.py, logging.py
- Fixed deprecated `datetime.utcnow()` usage - replaced with `datetime.now(timezone.utc)`
- Tests verify actual execution with mock page

**Files Created/Modified:**
- `src/selectors/fallback/logging.py` - Fallback attempt logging logic
- `tests/selectors/fallback/test_logging.py` - Unit tests for logging (22 tests)
- `src/selectors/fallback/models.py` - Added FallbackAttemptLog, SelectorAttempt models
- `src/selectors/fallback/decorator.py` - Added logging calls to @with_fallback
- `src/selectors/fallback/__init__.py` - Export logging module

**Key Patterns Established:**
- Use existing modules and extend functionality
- Tests should verify actual execution, not just method existence
- Use `datetime.now(timezone.utc)` for timestamps
- Decorator pattern for fallback chains

## Architecture Compliance

### Must Follow Architecture Decisions:

1. **YAML Configuration Structure** (from architecture.md):
   - Hints defined in YAML selectors under `hints` key
   - Example YAML structure:
     ```yaml
     selector:
       name: "primary"
       strategy: "css"
       pattern: ".main-content"
       hints:
         stability: 0.9
         priority: 1
         alternatives: ["fallback1", "fallback2"]
     ```

2. **Data Validation** (from architecture.md):
   - Use Pydantic models for validation
   - Located in `src/selectors/models.py`
   - Extend existing YAMLSelector model

3. **Error Handling** (from architecture.md):
   - Use existing `SelectorLoadingError` for YAML parsing errors
   - Use `SelectorConfigurationError` for invalid hint formats

4. **Testing Standards** (from architecture.md):
   - Unit tests with pytest markers
   - Integration tests for YAML loading

## References

- **Epics Source:** `_bmad-output/planning-artifacts/epics.md#story-21-yaml-hint-schema-reading`
- **Architecture:** `_bmad-output/planning-artifacts/architecture.md`
- **Project Context:** `_bmad-output/project-context.md`
- **Previous Story:** `_bmad-output/implementation-artifacts/1-4-fallback-attempt-logging.md`
- **YAML Loader:** `src/selectors/yaml_loader.py`
- **Models:** `src/selectors/models.py`
- **Exceptions:** `src/selectors/exceptions.py`

---

## Dev Agent Record

### Agent Model Used

giga-potato-thinking

### Debug Log References

- All tests passed successfully
- Hint parsing functionality verified

### Completion Notes List

- [x] YAML hint schema reading implemented
- [x] SelectorHint and HintSchema models created
- [x] YAMLSelectorLoader extended to parse hints
- [x] Default hint values applied
- [x] Unit tests for hint parsing written
- [x] Integration with existing YAML loading verified

### Change Log

- Added `src/selectors/hints/` module with models and parser
- Modified `src/selectors/models.py` to support hints property
- Extended `src/selectors/yaml_loader.py` to parse hint fields
- Added `tests/selectors/hints/test_parser.py` with comprehensive tests

### File List

**Created:**
- `src/selectors/hints/__init__.py` - Module exports
- `src/selectors/hints/models.py` - Hint data models
- `src/selectors/hints/parser.py` - Hint parsing logic
- `tests/selectors/hints/test_parser.py` - Unit tests for hint parsing

**Modified:**
- `src/selectors/yaml_loader.py` - Extend to parse hint fields
- `src/selectors/models.py` - Add SelectorHint and HintSchema models

**To Reference:**
- `src/selectors/yaml_loader.py` - Existing YAML loading
- `src/selectors/models.py` - Existing selector models
- `src/selectors/exceptions.py` - Selector error classes
