# Story 7.2: Intercepted API Mode

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer, I want to use Intercepted API Mode for network capture, so that I can extract data from sites that require browser initialization.

**FRs covered:** FR3 - SCR-002

## Acceptance Criteria

1. Given a browser session with network interception enabled, when the browser navigates to a page, then network responses are captured before reaching the DOM
2. Given URL pattern configuration in site module, when network responses are received, then only responses matching the configured patterns are captured
3. Given a captured API response, when interception occurs, then the raw response (body, headers, status) is accessible to the extraction handler
4. Given non-matching network traffic (images, CSS, analytics), when responses arrive, then they are ignored without affecting performance
5. Given the network listener is attached before navigation, when the page loads, then all responses during page load are captured
6. Given intercepted response content, when captured, then it is accessible for further processing by encoding detectors/decoders (SCR-004, SCR-005)
7. Given network interception mode is configured, when extraction is triggered, then the InterceptedExtractionHandler is instantiated (not placeholder)

## Tasks / Subtasks

- [x] Task 1: Implement network response interceptor (AC: #1, #5)
  - [x] Subtask 1.1: Create network listener module in src/network/
  - [x] Subtask 1.2: Implement Playwright network event handlers (request/response)
  - [x] Subtask 1.3: Ensure listener attaches before navigation
  - [x] Subtask 1.4: Handle async response body capture
- [x] Task 2: Implement URL pattern matching (AC: #2, #4)
  - [x] Subtask 2.1: Define URL pattern config in site module
  - [x] Subtask 2.2: Implement regex-based pattern matching
  - [x] Subtask 2.3: Filter non-matching responses efficiently
  - [ ] Subtask 2.4: Add CLI support for pattern testing (NOT IMPLEMENTED - marked [x] in error)
- [x] Task 3: Implement InterceptedExtractionHandler (AC: #7)
  - [x] Subtask 3.1: Replace placeholder in src/extraction/router.py
  - [x] Subtask 3.2: Implement browser session initialization with interception
  - [x] Subtask 3.3: Wire up network listener to handler
  - [x] Subtask 3.4: Return captured responses
- [x] Task 4: Integration with extraction router (AC: #7)
  - [x] Subtask 4.1: Verify router returns functional handler for "intercepted" mode
  - [x] Subtask 4.2: Test with existing site configs
  - [x] Subtask 4.3: Ensure handler follows ExtractionHandlerProtocol
- [x] Task 5: Testing (AC: all)
  - [x] Subtask 5.1: Unit tests for URL pattern matching
  - [x] Subtask 5.2: Integration tests with mock browser session
  - [ ] Subtask 5.3: End-to-end test with actual network capture (NOT IMPLEMENTED - only mock tests exist)

## Dev Notes

### Technical Stack

- **Runtime:** Python 3.11+ (asyncio-first)
- **HTTP Client:** httpx (from Epic 1)
- **Browser Automation:** Playwright >=1.40.0
- **Config Validation:** Pydantic (existing from story 3-1)
- **Async:** asyncio (native)

### Architecture Context

**Previous Work (Story 7-1):**
- Extraction mode router created in `src/extraction/router.py`
- `InterceptedExtractionHandler` placeholder exists (raises NotImplementedError)
- Routing logic implemented in `ExtractionModeRouter.get_handler()`

**Required Implementation:**
- Replace placeholder `InterceptedExtractionHandler` with functional implementation
- Create network listener module (SCR-002) in `src/network/`
- Implement URL pattern matching for selective capture

**Extraction Mode Context:**
| Mode | Description | Implementation Status |
|------|-------------|----------------------|
| `raw` / `direct` | Direct API Mode (HTTP without browser) | Epic 1 - Existing |
| `intercepted` | Intercepted API Mode (Network capture) | **This Story** |
| `hybrid` | Hybrid Mode (Browser session + HTTP) | Phase 2 - Story 7-3 |
| `dom` | DOM Mode (Existing browser extraction) | Legacy - Existing |

### Implementation Patterns to Follow

**Pattern 1: Protocol-Based Interface**
- Use Python Protocol (structural subtyping) for extraction mode interfaces
- Do NOT use inheritance - use duck typing
- Reference: Architecture doc - Output contract enforced via Protocol
- Already followed in Story 7-1

**Pattern 2: Error Structure (SHARED)**
- All errors must carry: module, operation, url, status_code, detail, partial_data
- Location: `src/network/` for network errors
- Reference: Architecture doc Pattern 2

**Pattern 4: Config Model Structure**
- Config flows inward — the module owns its config shape
- Pydantic model defined inside the module that uses it

**Module Structure:**
- Follow existing `src/{module_name}/` pattern
- Each module has `__init__.py` for clean API
- Each module has `interfaces.py` for dependency injection
- SCR-002 goes in `src/network/`

### Project Structure Notes

- Existing extraction router: `src/extraction/router.py`
- Existing HTTP transport: `src/network/direct_api.py`
- Site config model: `src/sites/base/site_config.py`
- Boundary rule: Site modules touch ONLY `src/sites/` directory (NFR15)
- **Exception:** SCR-002 lives in `src/network/`, not `src/sites/`

### Key Dependencies

1. **Story 7-1 (Mode Declaration):** Provides routing infrastructure
2. **Epic 1 (HTTP Transport):** Provides base HTTP client (for hybrid mode later)
3. **Playwright:** Network event API for interception
4. **Future: SCR-004, SCR-005:** Encoding detection and decoding (hand off captured responses)

### SCR-002 Feature Requirements (from docs/proposals/browser_api_hybrid/FEATURE_02_NETWORK_INTERCEPTION.md)

**What This Feature Adds:**
- A **network response listener** that can be attached to any Playwright browser session
- URL pattern matching so only relevant API responses are captured (not images, fonts, analytics, etc.)
- Captured responses stored and returned alongside or instead of DOM-extracted data
- Configuration per site module specifying which URL patterns to intercept
- CLI and logging support to inspect intercepted responses during development

**Success Criteria:**
- A site module can configure URL patterns to intercept during browser navigation
- Matching responses are captured and returned as structured data
- Non-matching responses (images, CSS, analytics) are ignored without affecting performance
- The listener attaches before navigation begins and captures responses reliably
- Works correctly alongside existing DOM extraction in the same browser session
- Intercepted response content is accessible for further processing by decoders

**Out of Scope:**
- Decoding binary or protobuf responses (covered by SCR-004, SCR-005)
- Cloudflare bypass (covered by SCR-003)
- WebSocket interception (future roadmap item)

### References

- Architecture: [_bmad-output/planning-artifacts/architecture.md#extraction-mode-management](_bmad-output/planning-artifacts/architecture.md)
- Architecture: [_bmad-output/planning-artifacts/architecture.md#pattern-1-protocol-based-interface](_bmad-output/planning-artifacts/architecture.md)
- Epics: [_bmad-output/planning-artifacts/epics.md#story-72-intercepted-api-mode-phase-2](_bmad-output/planning-artifacts/epics.md)
- Feature Proposal: [docs/proposals/browser_api_hybrid/FEATURE_02_NETWORK_INTERCEPTION.md](docs/proposals/browser_api_hybrid/FEATURE_02_NETWORK_INTERCEPTION.md)
- Previous Story: [_bmad-output/implementation-artifacts/7-1-mode-declaration-and-routing.md](_bmad-output/implementation-artifacts/7-1-mode-declaration-and-routing.md)
- Project Context: [_bmad-output/project-context.md](_bmad-output/project-context.md)

### Important Notes from PRD/Epics

> **FR3:** The system supports Intercepted API Mode for network capture (Phase 2)

> **Note:** This is SCR-002 - Network Response Interception

> **AiScore Discovery Context:** After navigating to `m.aiscore.com/basketball` with Playwright and logging all network responses, the following was observed:
> ```
> [200] https://api.aiscore.com/v1/m/api/matches?lang=2&sport_id=2&date=20260310&tz=03:00
> ```
> This confirmed all basketball match data was available directly from the network layer - DOM contained no useful data.

### Previous Story Learnings (from 7-1)

1. **Default mode changed:** Story 7-1 changed default from PLAYWRIGHT to RAW (Direct API) - verify this doesn't affect intercepted mode
2. **Handler pattern:** RawExtractionHandler shows proper async client lifecycle (reuse with `_get_client()`, close with `close()`)
3. **Protocol compliance:** All handlers must follow ExtractionHandlerProtocol
4. **Tests:** 13 tests in test_extraction_mode_routing.py - consider adding tests for intercepted mode

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- Implemented NetworkListener in src/network/interception.py - attaches to Playwright pages and captures network responses
- Implemented InterceptionConfig for URL pattern matching using regex
- Implemented InterceptedResponse dataclass to store captured response data
- Replaced placeholder InterceptedExtractionHandler with functional implementation
- Added InterceptedConfig to SiteConfig for site-specific URL pattern configuration
- Created comprehensive unit tests in tests/network/test_interception.py (16 tests, all passing)
- All existing tests pass (13 extraction tests + 16 new network tests)

### Review Fixes Applied

- **Fixed:** Added `close()` method to ExtractionHandlerProtocol for type safety
- **Fixed:** Added `close()` method to HybridExtractionHandler and PlaywrightExtractionHandler
- **Fixed:** Made browser launch configurable via browser_config parameter
- **Fixed:** Marked Subtask 2.4 (CLI support) as not implemented
- **Fixed:** Marked Subtask 5.3 (E2E test) as not implemented - only mock tests exist

### Code Review Fixes (2026-03-14)

- **Fixed:** Committed all untracked code to git (src/extraction/, src/network/interception.py, etc.)
- **Fixed:** Added 7 new tests for InterceptedExtractionHandler in tests/extraction/test_extraction_mode_routing.py
- **Fixed:** Bug in close() method - now properly closes Playwright page before setting to None
- **Fixed:** All tests passing (20 extraction tests + 16 network tests)

### File List

- src/network/interception.py (new - SCR-002 network listener)
- src/network/__init__.py (modified - added exports)
- src/sites/base/site_config.py (modified - added InterceptedConfig)
- src/extraction/router.py (modified - implemented InterceptedExtractionHandler)
- tests/network/test_interception.py (new - interception tests)
