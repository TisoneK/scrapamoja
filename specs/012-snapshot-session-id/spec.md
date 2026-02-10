# Feature Specification: Fix Snapshot Filenames to Use Session ID for Proper Uniqueness

**Feature Branch**: `012-snapshot-session-id`  
**Created**: January 29, 2026  
**Status**: Draft  
**Input**: Fix Snapshot Filenames to Use Session ID for Proper Uniqueness

## User Scenarios & Testing

### User Story 1 - Unique Snapshot Storage Per Session (Priority: P1)

When a user captures snapshots from multiple sessions, each session should produce uniquely named files that don't conflict with snapshots from other sessions, even if they're captured at similar times.

**Why this priority**: This is the core requirement preventing false "existing file" warnings and enabling proper session traceability. Without it, concurrent or sequential sessions overwrite each other's data.

**Independent Test**: Can be tested by running the example twice in succession and verifying that both sets of snapshots coexist with different filenames. Delivers immediate value by eliminating filename collisions.

**Acceptance Scenarios**:

1. **Given** a session with ID `8b6bce3d` running a snapshot capture, **When** the snapshot is saved, **Then** the filename must include the session ID in format `{page_name}_{session_id}_{timestamp}.json`
2. **Given** two different sessions capture snapshots at nearly identical times, **When** both snapshots are saved to disk, **Then** both files must coexist without conflict or warnings
3. **Given** a user runs the same test twice with $env:TEST_MODE=1, **When** comparing the data/snapshots directory, **Then** all snapshots should have unique filenames traceable to their respective sessions

---

### User Story 2 - Session-Traceable Screenshot Filenames (Priority: P1)

Screenshots should include session ID in their filenames so they can be traced back to the session that captured them and referenced correctly in snapshot JSON.

**Why this priority**: Screenshots are critical debugging artifacts. Without session ID in the filename, it's impossible to know which session produced a screenshot, especially when multiple snapshots exist.

**Independent Test**: Can be tested by capturing a snapshot with screenshots and verifying the screenshot filename matches the pattern `{page_name}_{session_id}_{timestamp}.png` and is correctly referenced in the JSON metadata.

**Acceptance Scenarios**:

1. **Given** a snapshot capture includes screenshots, **When** the screenshot is saved to data/snapshots/screenshots/, **Then** the filename must include the session ID
2. **Given** the snapshot JSON metadata contains a screenshot reference, **When** examining the filepath field, **Then** it must include the session ID in the filename
3. **Given** a user reviews snapshot metadata, **When** they see the screenshot_filepath, **Then** they can extract the session ID directly from the filename

---

### User Story 3 - No False "Existing File" Warnings (Priority: P1)

The system should never warn about "existing" files when different sessions capture data at similar times, since each session has a unique ID.

**Why this priority**: False warnings degrade user confidence and hide real problems. This directly addresses the issue described in the root cause.

**Independent Test**: Can be tested by running two snapshots and verifying no warnings appear in logs about existing files, combined with verification that both snapshots exist independently.

**Acceptance Scenarios**:

1. **Given** session A completes with snapshot filename including its session ID, **When** session B captures a snapshot with a different session ID at a similar time, **Then** no warning should appear about existing files
2. **Given** data/snapshots already contains snapshots from previous runs, **When** a new session with a different session_id captures data, **Then** no false warnings should be generated about file conflicts

---

### Edge Cases

- What happens when a session ID contains special characters that aren't valid in filenames? (Session IDs should be sanitized if needed)
- How does the system handle timestamps with identical second precision across sessions?
- What if screenshot directory doesn't exist when trying to save? (Should be created if missing)

## Requirements

### Functional Requirements

- **FR-001**: Snapshot filenames MUST include session_id in format: `{page_name}_{session_id}_{timestamp}.json`
- **FR-002**: Screenshot filenames MUST include session_id in format: `{page_name}_{session_id}_{timestamp}.png`
- **FR-003**: Snapshot JSON metadata MUST reference screenshot filepath with complete filename including session_id
- **FR-004**: Session ID in filename MUST be derived from the current session's session_id property
- **FR-005**: Each unique session MUST produce unique filenames even when capturing at similar times
- **FR-006**: Snapshot storage directory structure MUST remain: data/snapshots/ for JSON and data/snapshots/screenshots/ for PNG files
- **FR-007**: System MUST support multiple concurrent snapshots without filename collisions
- **FR-008**: Session ID extraction from filenames MUST be possible through string parsing of the filename

### Key Entities

- **Snapshot**: Represents a captured webpage state with metadata, JSON configuration, and optional screenshots. Key attributes: page_name, session_id, timestamp, screenshot_filepath
- **Session**: Represents a unique scraping session. Key attributes: session_id (unique identifier), start_time, end_time
- **Screenshot**: Image file captured during snapshot with metadata. Key attributes: filename (includes session_id), filepath, timestamp

## Success Criteria

### Measurable Outcomes

- **SC-001**: Running the example twice with $env:TEST_MODE=1 produces two independent sets of snapshots with zero filename conflicts
- **SC-002**: Snapshot JSON metadata correctly references screenshot files that include session ID and exist in data/snapshots/screenshots/ directory
- **SC-003**: No "existing file" warnings appear in logs when multiple sessions capture snapshots at similar times
- **SC-004**: All snapshot files in data/snapshots/ can be traced to their originating session by parsing the session_id from the filename
- **SC-005**: Session ID appears as a consistently formatted string segment in both JSON and PNG filenames (between page_name and timestamp)

## Implementation Notes

### Current State
- Filenames: `{page_name}_{timestamp}.json` and `{page_name}_{timestamp}.png`
- No session_id in filenames causes collisions between different sessions

### Target State
- Filenames: `{page_name}_{session_id}_{timestamp}.json` and `{page_name}_{session_id}_{timestamp}.png`
- Session ID ensures uniqueness across concurrent and sequential sessions
- Example: `wikipedia_search_8b6bce3d_20260129_082735.json`

### Assumptions

1. Session ID is always available when snapshots are being saved
2. Session IDs are already unique and don't require additional validation for filename use
3. Timestamp format remains consistent: `YYYYMMDD_HHMMSS`
4. JSON metadata already has a structure for storing screenshot filepath (may need update to reference complete filename)
5. Target is Python 3.11+ with async/await patterns per project architecture
