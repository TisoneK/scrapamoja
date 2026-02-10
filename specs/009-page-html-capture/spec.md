# Feature Specification: Page HTML Capture and Storage in Snapshots

**Feature Branch**: `009-page-html-capture`  
**Created**: 2025-01-29  
**Status**: Draft  
**Input**: User description: "FEATURE: Store Full HTML Content in Page Snapshots - Add the capability to store full page HTML content in snapshots so that captured pages can be replayed/reviewed offline, HTML can be used for verification and testing, TEST_MODE can use previously captured real pages for reliable offline testing, and snapshots provide a complete record of the page state"

## Clarifications

### Session 2025-01-29

- Q: HTML Storage Approach → A: Store HTML file path/location reference in JSON, with HTML saved as separate file
- Q: HTML File Organization → A: Store HTML files in dedicated subdirectory (e.g., snapshots/html/) with timestamp-based naming
- Q: Missing/Corrupted HTML File Handling → A: Graceful degradation: Log warning, continue with metadata-only snapshot, clear error message

## User Scenarios & Testing *(mandatory)*

### User Story 1 - HTML Content Capture (Priority: P1)

As a developer using the browser lifecycle system, I want to capture the complete HTML content of pages in snapshots so that I can review and analyze the exact page state offline.

**Why this priority**: This is the core functionality that enables all other use cases and provides immediate value for debugging and testing.

**Independent Test**: Can be fully tested by capturing a snapshot of a known webpage and verifying the HTML content is stored correctly in the JSON output.

**Acceptance Scenarios**:

1. **Given** a browser session with a loaded page, **When** I capture a snapshot, **Then** the snapshot JSON contains a reference to the HTML file location and the HTML file is created
2. **Given** a snapshot with HTML file reference, **When** I parse the JSON, **Then** the file path is valid and the HTML file exists
3. **Given** a snapshot file and HTML file, **When** I examine the combined size, **Then** it remains reasonable (< 10MB for typical pages)

---

### User Story 2 - Offline HTML Replay (Priority: P2)

As a developer, I want to load previously captured HTML content into a browser for offline testing and verification so that I can test without network dependencies.

**Why this priority**: Enables reliable offline testing and reduces dependency on live websites during development.

**Independent Test**: Can be fully tested by loading a captured HTML snapshot into a browser via data: URL or temporary file and verifying the page renders correctly.

**Acceptance Scenarios**:

1. **Given** a snapshot containing HTML file reference, **When** I load the HTML file via browser, **Then** the page renders correctly
2. **Given** a snapshot with HTML file reference, **When** I load the referenced HTML file, **Then** all page elements are preserved
3. **Given** multiple snapshots with HTML files, **When** I load them sequentially, **Then** each renders independently without conflicts

---

### User Story 3 - Content Integrity Verification (Priority: P3)

As a developer, I want to verify that captured HTML content has not been corrupted so that I can trust the integrity of stored snapshots.

**Why this priority**: Ensures data reliability and enables detection of storage or transmission errors.

**Independent Test**: Can be fully tested by capturing a snapshot, modifying the HTML content, and verifying the hash check detects the corruption.

**Acceptance Scenarios**:

1. **Given** a newly captured snapshot, **When** I verify the content hash, **Then** it matches the stored hash value
2. **Given** a snapshot with corrupted HTML content, **When** I verify the content hash, **Then** the hash mismatch is detected
3. **Given** a snapshot file, **When** I load and re-save it, **Then** the content hash remains unchanged

---

### Edge Cases

- How does system handle pages with dynamic content that changes during capture?
- What happens when the page contains binary data or non-UTF-8 content?
- How does system handle pages with security restrictions (CSP, same-origin)?
- What happens when disk space is insufficient for storing large HTML content?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST capture complete page HTML content during snapshot creation
- **FR-002**: System MUST store HTML file path reference under "page.html_file" field in snapshot JSON
- **FR-003**: System MUST generate and store SHA-256 content hash for integrity verification
- **FR-004**: System MUST save HTML content as separate file in dedicated subdirectory with timestamp-based naming convention
- **FR-005**: System MUST maintain backward compatibility with existing snapshot format
- **FR-006**: System MUST provide reasonable file size limits for typical web pages (< 10MB)
- **FR-007**: System MUST support loading captured HTML files directly in browser
- **FR-008**: System MUST validate content integrity using stored hash values
- **FR-009**: System MUST handle encoding issues gracefully (UTF-8 fallback)
- **FR-010**: System MUST not degrade performance of snapshot capture operations
- **FR-011**: System MUST handle missing/corrupted HTML files with graceful degradation and clear error messaging

### Technical Constraints (Constitution Alignment)

- **TC-001**: No requests library or BeautifulSoup allowed - only Playwright for HTML content extraction
- **TC-002**: All HTML content must be captured within existing browser session context
- **TC-003**: Content hash calculation must use SHA-256 for consistency with existing systems
- **TC-004**: JSON serialization must handle special characters and Unicode properly
- **TC-005**: Deep modularity required - HTML capture should be a separate concern from metadata capture
- **TC-006**: Implementation-first development - direct implementation with manual validation
- **TC-007**: Neutral naming convention required - use structural, descriptive language only

### Key Entities *(include if feature involves data)*

- **PageSnapshot**: Represents a complete page capture including metadata and HTML content
- **HTMLFile**: Represents the separate HTML file containing captured page content with metadata (size, hash, encoding)
- **ContentHash**: Represents integrity verification data for HTML content
- **SnapshotFormat**: Defines the structure and versioning of snapshot JSON files

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Snapshots include HTML file references for 100% of captured pages
- **SC-002**: HTML content integrity verification passes for 99.9% of HTML files
- **SC-003**: Combined snapshot and HTML file sizes remain under 10MB for 95% of typical web pages
- **SC-004**: Offline HTML replay successfully renders 100% of captured HTML files
- **SC-005**: Snapshot capture performance degradation is less than 10% compared to metadata-only capture
- **SC-006**: Backward compatibility is maintained for 100% of existing snapshot consumers
