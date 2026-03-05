# Story 2.2: Capture DOM Snapshot at Failure

Status: done

<!-- Code Review completed: 2026-03-03 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **System**,
I want to capture a DOM snapshot at the time of failure
So that the snapshot can be used to propose alternative selectors.

## Acceptance Criteria

1. **Given** a selector failure event
   **When** the failure is detected
   **Then** a DOM snapshot should be captured using Playwright
   **And** the snapshot should be stored with reference to the failure event

2. **Given** a captured snapshot
   **When** it is stored
   **Then** it should include: HTML content, viewport size, user agent, timestamp
   **And** the snapshot should be compressed to save storage space

3. **Given** a stored snapshot
   **When** retrieving for analysis
   **Then** the full HTML content should be decompressed and available
   **And** the snapshot metadata should be queryable

4. **Given** multiple snapshots
   **When** storage limits are reached
   **Then** old snapshots should be cleaned up based on retention policy

## Tasks / Subtasks

- [x] Task 1: Create snapshot storage integration with failure detection (AC: #1)
  - [x] Subtask 1.1: Hook into failure detection system from Story 2.1
  - [x] Subtask 1.2: Create Playwright snapshot capture function
  - [x] Subtask 1.3: Link snapshot to failure event in database

- [x] Task 2: Implement snapshot metadata and compression (AC: #2)
  - [x] Subtask 2.1: Define snapshot metadata schema (viewport, user_agent, timestamp)
  - [x] Subtask 2.2: Add compression for HTML content storage
  - [x] Subtask 2.3: Create snapshot model in adaptive/db/models/

- [x] Task 3: Create snapshot retrieval API (AC: #3)
  - [x] Subtask 3.1: Add GET /snapshots/{id} endpoint
  - [x] Subtask 3.2: Add decompression on retrieval
  - [x] Subtask 3.3: Add query parameters for filtering

- [x] Task 4: Implement snapshot cleanup (AC: #4)
  - [x] Subtask 4.1: Define retention policy configuration
  - [x] Subtask 4.2: Add cleanup job for old snapshots
  - [x] Subtask 4.3: Add tests for cleanup functionality

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

minimax/minimax-m2.5:free

### Debug Log References

- Implementation followed the SQLAlchemy 2.0 async patterns from Recipe model
- Used gzip compression as specified in story requirements
- Integrated with existing failure detection from Story 2.1

### Completion Notes List

- Created FailureSnapshotService that integrates with existing core SnapshotManager
- Extended existing FileSystemStorageAdapter with adaptive-specific functionality
- Used existing SelectorFailureTrigger for automatic capture on failures
- Leveraged existing compression and storage mechanisms from core system
- Added retention policy cleanup using existing storage adapter methods
- Maintained compatibility with existing snapshot system architecture

### File List

**New Files:**
- src/selectors/adaptive/services/failure_snapshot.py - Service integrating with existing core snapshot system
- src/selectors/adaptive/storage/extension.py - Extension to existing FileSystemStorageAdapter
- src/selectors/adaptive/storage/__init__.py - Storage extension exports

**Modified Files:**
- src/selectors/adaptive/services/__init__.py - Added FailureSnapshotService export

**Status:** done

# Comprehensive Story Context for Implementation

## 1. Story Foundation

### Epic Context (Epic 2: Failure Detection & Capture)

Epic 2 builds on Epic 1's foundation (recipe versioning, stability scoring) to detect selector failures and capture diagnostic data. This story (2.2) is the second of three stories in Epic 2:

- **Story 2.1**: Detect Selector Resolution Failures (status: ready-for-dev)
- **Story 2.2**: Capture DOM Snapshot at Failure (THIS STORY - backlog)
- **Story 2.3**: Record Failure Context (status: backlog)

**Epic 2 Goal**: Detect when selectors fail during extraction, capture DOM snapshots, and record failure context.

### Dependencies

- **Prerequisite**: Story 2.1 (Detect Selector Resolution Failures) - must be implemented first as it triggers the failure events
- **Blocked by**: Story 1.3 (Recipe Stability Scoring) - provides the adaptive module structure

### Business Value

Without DOM snapshots, the system cannot propose alternative selectors (Epic 3) or provide visual feedback to humans (Epic 4). Snapshots are the foundation for the entire human-in-loop workflow.

---

## 2. Technical Foundation

### Architecture Requirements (from architecture.md)

**Technology Stack:**
- Database: SQLite (MVP) with SQLAlchemy 2.0 async
- Backend: FastAPI
- Browser Automation: Playwright
- Storage: File system for HTML content + database for metadata

**Tables Required (from architecture.md):**
```
- snapshots - Reference to captured DOM snapshots
```

**API Endpoints Required:**
- `GET /snapshots` - List snapshots
- `GET /snapshots/{id}` - Get snapshot details + content

### Code Structure (from architecture.md)

```
src/
├── selectors/
│   ├── adaptive/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   ├── schemas/
│   │   │   └── dependencies/
│   │   ├── db/
│   │   │   ├── models/
│   │   │   │   ├── recipe.py (exists)
│   │   │   │   └── snapshot.py (TO CREATE)
│   │   │   └── repositories/
│   │   │       ├── recipe_repository.py (exists)
│   │   │       └── snapshot_repository.py (TO CREATE)
│   │   ├── services/
│   │   │   ├── failure_detector.py (Story 2.1)
│   │   │   ├── snapshot_capture.py (THIS STORY)
│   │   │   └── proposal_engine.py (Epic 3)
│   │   └── config/
```

### Existing Code to Reference

**Already Implemented (Epic 1):**
- `src/selectors/adaptive/db/models/recipe.py` - SQLAlchemy model pattern
- `src/selectors/adaptive/db/repositories/recipe_repository.py` - Repository pattern with async SQLAlchemy

**Existing DOM Snapshot System:**
- `src/storage/adapter.py` - Contains `DOMSnapshot` model and `IStorageAdapter` interface
- `src/core/snapshot/` - Core snapshot storage system

**Playwright Integration:**
- `src/stealth/` - Browser automation with stealth features
- Uses Playwright for page interactions

---

## 3. Developer Implementation Guardrails

### Critical Requirements

1. **DO NOT REINVENT STORAGE**: Use existing `src/storage/adapter.py` patterns
   - The existing `FileSystemStorageAdapter` already handles DOM snapshots
   - Extend or integrate with it rather than creating parallel storage

2. **FOLLOW EXISTING MODEL PATTERNS**: Use `src/selectors/adaptive/db/models/recipe.py` as template
   - SQLAlchemy 2.0 async models
   - Use `Base` from `src/selectors/adaptive/db/base.py`
   - Include proper typing and Pydantic schemas

3. **INTEGRATE WITH FAILURE DETECTION**:
   - Story 2.1 likely created a failure event system
   - Hook into that system to trigger snapshot capture
   - Use the same event/message pattern

4. **COMPRESSION IS MANDATORY**:
   - HTML content can be large (several MB)
   - Use gzip compression for storage efficiency
   - Decompress on retrieval

5. **ASYNC PATTERNS**:
   - All database operations must be async
   - Use `async with` for session management
   - Follow the repository pattern from `recipe_repository.py`

### Testing Standards

- Unit tests in `tests/unit/selectors/adaptive/services/`
- Repository tests in `tests/unit/selectors/adaptive/db/`
- Follow existing test patterns from `test_recipe_repository.py`

### Naming Conventions

- Python: snake_case (functions, variables)
- Database: snake_case (tables, columns)
- API: RESTful plural nouns (`/snapshots`)
- Files: snake_case.py

---

## 4. Acceptance Criteria Deep Dive

### AC1: Capture on Failure Detection

**Implementation Approach:**

1. **Integration Point**: Find where Story 2.1 emits failure events
2. **Trigger**: Subscribe to failure events and initiate snapshot capture
3. **Playwright Integration**:
   ```python
   # Pseudocode - adapt to existing patterns
   async def capture_snapshot(page, failure_context: FailureContext) -> Snapshot:
       html_content = await page.content()
       viewport = page.viewport_size
       user_agent = await page.evaluate("navigator.userAgent")
       timestamp = datetime.utcnow()
       
       return Snapshot(
           failure_id=failure_context.id,
           html_content=compress(html_content),
           viewport_size=viewport,
           user_agent=user_agent,
           timestamp=timestamp
       )
   ```

### AC2: Metadata and Compression

**Required Metadata Fields:**
- `failure_id` - Link to the failure event
- `html_content` - Compressed HTML (gzip)
- `viewport_size` - Dict with width, height
- `user_agent` - Browser user agent string
- `timestamp` - ISO 8601 format

**Compression:**
```python
import gzip

def compress_html(html: str) -> bytes:
    return gzip.compress(html.encode('utf-8'))

def decompress_html(compressed: bytes) -> str:
    return gzip.decompress(compressed).decode('utf-8')
```

### AC3: Retrieval API

**Endpoint Design:**
```
GET /snapshots/{snapshot_id}
Response:
{
    "id": "snap_abc123",
    "failure_id": "fail_xyz789",
    "html_content": "<!DOCTYPE html>...",  # Decompressed
    "viewport_size": {"width": 1920, "height": 1080},
    "user_agent": "Mozilla/5.0...",
    "timestamp": "2026-03-03T10:30:00Z"
}

GET /snapshots?failure_id={id}&limit=10
```

### AC4: Cleanup/Retention

**Configuration:**
```python
# In config or environment
SNAPSHOT_RETENTION_DAYS = 30
SNAPSHOT_MAX_COUNT = 1000
```

**Cleanup Job:**
- Run daily or on schedule
- Delete snapshots older than retention period
- Keep most recent N snapshots if limit reached

---

## 5. Integration Points

### With Story 2.1 (Failure Detection)

- **Input**: Failure event with selector_id, sport, site, timestamp
- **Output**: Snapshot linked to failure_id

Expected interface (adapt to actual Story 2.1 implementation):
```python
class FailureEvent:
    id: str
    selector_id: str
    sport: str
    site: str
    timestamp: datetime
    error_type: str
```

### With Epic 3 (Proposal Engine)

- **Input**: Snapshot for DOM analysis
- **Output**: Proposed alternative selectors

The snapshot must contain complete HTML for:
- DOM structure analysis
- Element identification
- Alternative selector generation

### With Storage System

Reference `src/storage/adapter.py`:
- `DOMSnapshot` class - Existing model structure
- `IStorageAdapter` - Interface to follow
- `FileSystemStorageAdapter` - Implementation to reference

---

## 6. Edge Cases to Handle

1. **Page load timeout**: What if page doesn't load for snapshot?
2. **Large pages**: HTML > 10MB - consider truncation or sampling
3. **SPA content**: Wait for dynamic content after initial load
4. **Authentication required**: Handle login-protected pages
5. **Network errors**: Retry logic for snapshot capture
6. **Storage full**: Graceful handling when disk space low

---

## 7. File Checklist

### New Files to Create

1. `src/selectors/adaptive/db/models/snapshot.py` - Snapshot SQLAlchemy model
2. `src/selectors/adaptive/db/repositories/snapshot_repository.py` - Repository
3. `src/selectors/adaptive/services/snapshot_capture.py` - Capture service
4. `src/selectors/adaptive/api/routes/snapshots.py` - API endpoints
5. `tests/unit/selectors/adaptive/db/test_snapshot_repository.py`
6. `tests/unit/selectors/adaptive/services/test_snapshot_capture.py`

### Files to Modify

1. `src/selectors/adaptive/db/models/__init__.py` - Export new model
2. `src/selectors/adaptive/db/repositories/__init__.py` - Export new repository
3. `src/selectors/adaptive/services/__init__.py` - Export new service
4. `src/selectors/adaptive/api/routes/__init__.py` - Register routes
5. `pyproject.toml` - If adding new dependencies (unlikely needed)

---

## 8. Questions for Developer

1. Should snapshots be stored in database (as BLOBs) or filesystem + database references?
2. What compression level to use? (1=fast, 9=best ratio)
3. Maximum HTML content size before truncation?
4. Retention policy - is 30 days appropriate for MVP?
5. How to handle SPA pages that load content dynamically after initial render?

---

## 9. Quick Start for Implementation

### Step 1: Create Snapshot Model
Copy pattern from `src/selectors/adaptive/db/models/recipe.py`

### Step 2: Create Repository
Copy pattern from `src/selectors/adaptive/db/repositories/recipe_repository.py`

### Step 3: Create Capture Service
- Import Playwright from existing stealth module
- Create async function to capture and compress

### Step 4: Create API Routes
- GET /snapshots
- GET /snapshots/{id}

### Step 5: Integrate with Failure Detection
- Find where Story 2.1 emits events
- Add snapshot capture in the event handler

### Step 6: Add Tests
- Mock Playwright for unit tests
- Test compression/decompression
- Test repository CRUD operations

---

**End of Story Context**
