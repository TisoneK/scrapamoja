---
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics", "step-03-create-stories", "step-04-final-validation"]
status: "complete"
inputDocuments: 
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/architecture.md"
---

# scrapamoja - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for scrapamoja, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

**Fallback Chain Management:**
- FR1: System can execute primary selector for data extraction
- FR2: System can execute fallback selector when primary fails
- FR3: System can chain multiple fallback levels (minimum 2)
- FR4: System can log fallback attempts with results

**YAML Hints Integration:**
- FR5: System can read hint schema from YAML selectors
- FR6: System can use hints to determine fallback strategy
- FR7: System can prioritize selectors based on stability hints

**Failure Capture & Logging:**
- FR8: System can capture selector failure events
- FR9: System can log failure events with full context (selectorId, URL, timestamp, failureType)
- FR10: System can submit failure events to adaptive module DB

**Real-Time Notifications (Phase 2):**
- FR11: System can receive WebSocket notifications for failures
- FR12: System can receive confidence score updates
- FR13: System can receive selector health status updates

**Health & Monitoring (Phase 2):**
- FR14: System can query adaptive module for selector confidence scores
- FR15: System can display selector health status
- FR16: System can calculate blast radius for failures

**Integration Architecture:**
- FR17: System can call adaptive REST API for alternative resolution
- FR18: System can handle adaptive service unavailability gracefully
- FR19: System can operate with sync failure capture (immediate)
- FR20: System can operate with async failure capture (learning)

### NonFunctional Requirements

**Performance:**
- NFR1: Fallback Resolution Time - Sync fallback path should not add more than 5 seconds to scraper execution
- NFR2: WebSocket Connection - Maintain stable connection for real-time notifications with automatic reconnection

**Integration:**
- NFR3: Graceful Degradation - When adaptive services are unavailable, scraper continues with primary selectors only (no fallback)
- NFR4: API Timeout Handling - External API calls have configurable timeouts (default 30s) with appropriate error handling
- NFR5: Connection Pooling - Manage adaptive API connections efficiently to avoid resource exhaustion

### Additional Requirements

**From Architecture Document:**
- Integration Pattern: In-process integration (import adaptive module directly into scraper)
- Failure Capture Strategy: Validation layer (check results after extraction)
- Fallback Chain Pattern: Linear chain (primary → fallback1 → fallback2)
- Connection Management: Singleton pattern (single shared connection)
- Implementation Pattern: Use @with_fallback decorator for fallback chains
- Data Models: Use Pydantic models for failure events
- Custom Exceptions: Located in src/selectors/exceptions.py
- Naming Conventions: PascalCase (classes), snake_case (functions/variables), UPPER_SNAKE_CASE (constants)
- Test Requirements: Unit tests with pytest markers (@pytest.mark.unit, @pytest.mark.integration)
- Phase 2 Features (Deferred): WebSocket notifications, Health API with confidence scores, Blast radius analysis

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 1 | Primary selector execution |
| FR2 | Epic 1 | Fallback selector execution |
| FR3 | Epic 1 | Multi-level fallback chaining |
| FR4 | Epic 1 | Fallback attempt logging |
| FR5 | Epic 2 | YAML hint schema reading |
| FR6 | Epic 2 | Hint-based fallback strategy |
| FR7 | Epic 2 | Stability-based prioritization |
| FR8 | Epic 3 | Failure event capture |
| FR9 | Epic 3 | Full context failure logging |
| FR10 | Epic 3 | Adaptive DB submission |
| FR11 | Epic 5 | WebSocket failure notifications |
| FR12 | Epic 5 | Confidence score updates |
| FR13 | Epic 5 | Health status streaming |
| FR14 | Epic 6 | Confidence score queries |
| FR15 | Epic 6 | Health status display |
| FR16 | Epic 6 | Blast radius calculation |
| FR17 | Epic 4 | Adaptive REST API calls |
| FR18 | Epic 4 | Service unavailability handling |
| FR19 | Epic 3 | Sync failure capture |
| FR20 | Epic 3 | Async failure capture |

## Epic List

### Epic 1: Automatic Fallback Resolution
**Goal:** Enable the scraper to automatically recover from selector failures without manual intervention, ensuring continuous data extraction.

**FRs covered:** FR1, FR2, FR3, FR4 (Fallback Chain Management)

---

#### Story 1.1: Primary Selector Execution

As a **scraper system**,
I want **to execute a primary selector for data extraction**,
So that **data can be extracted from web pages using the main selector defined in the YAML configuration**.

**Acceptance Criteria:**

**Given** a YAML-configured selector with a primary selector defined
**When** the scraper invokes the selector engine for data extraction
**Then** the primary selector is executed against the page
**And** the extracted data is returned to the caller

**Given** a valid page with the expected DOM structure
**When** the primary selector is executed
**Then** the selector successfully extracts the data
**And** returns the expected value

---

#### Story 1.2: Fallback Selector Execution

As a **scraper system**,
I want **to execute a fallback selector when the primary fails**,
So that **data extraction continues even when the primary selector breaks due to DOM changes**.

**Acceptance Criteria:**

**Given** a primary selector that fails (returns empty or raises exception)
**When** the fallback mechanism is triggered
**Then** the fallback selector is executed against the same page
**And** the fallback result is returned if successful

**Given** a primary selector failure with error details
**When** the fallback is attempted
**Then** the failure event is logged with selector ID, URL, timestamp, and failure type
**And** the fallback attempt result is also logged

---

#### Story 1.3: Multi-Level Fallback Chain

As a **scraper system**,
I want **to chain multiple fallback levels (minimum 2)**,
So that **there are multiple recovery options when the first fallback also fails**.

**Acceptance Criteria:**

**Given** a primary selector failure
**When** the fallback chain is executed
**Then** fallback1 is attempted first
**And** if fallback1 succeeds, the result is returned
**And** if fallback1 fails, fallback2 is attempted

**Given** both fallback1 and fallback2 fail
**When** the fallback chain completes
**Then** the system returns failure with all attempted selectors logged
**And** the chain stops at the first successful fallback

**Given** a linear chain configuration (primary → fallback1 → fallback2)
**When** the chain executes
**Then** each selector is tried in order until success or all fail
**And** the total fallback resolution time is tracked for performance monitoring

---

#### Story 1.4: Fallback Attempt Logging

As a **developer**,
I want **to log all fallback attempts with results**,
So that **I can debug issues and understand selector stability over time**.

**Acceptance Criteria:**

**Given** any fallback attempt (success or failure)
**When** the fallback chain completes
**Then** a log entry is created with: selector ID, page URL, timestamp, attempted selectors in order, final result

**Given** a fallback success
**When** logging the event
**Then** log includes which fallback succeeded and the extracted value

**Given** a fallback failure
**When** logging the event
**Then** log includes all attempted selectors that failed
**And** includes the failure reason for each attempt

---

### Epic 2: YAML Hints & Selector Prioritization
**Goal:** Leverage YAML-defined hints to intelligently choose fallback strategies based on selector stability.

**FRs covered:** FR5, FR6, FR7 (YAML Hints Integration)

---

#### Story 2.1: YAML Hint Schema Reading

As a **scraper system**,
I want **to read hint schema from YAML selectors**,
So that **the system can understand the metadata and hints defined for each selector**.

**Acceptance Criteria:**

**Given** a YAML selector configuration file
**When** the selector engine loads the configuration
**Then** all hint fields are parsed from the YAML
**And** the hints are available to the fallback chain logic

**Given** a YAML selector with hints defined (stability, priority, alternatives)
**When** the selector is loaded
**Then** the hints are deserialized into a structured format
**And** stored with the selector metadata

**Given** a YAML selector without hints
**When** the selector is loaded
**Then** default hint values are applied
**And** no errors are raised

---

#### Story 2.2: Hint-Based Fallback Strategy

As a **scraper system**,
I want **to use hints to determine fallback strategy**,
So that **the fallback chain follows intelligent routing based on selector metadata**.

**Acceptance Criteria:**

**Given** a selector with defined hints including alternative selectors
**When** the primary selector fails
**Then** the fallback chain uses the hints to determine which alternatives to try
**And** the alternatives are attempted in the order specified in hints

**Given** a selector with a "strategy" hint (e.g., "linear", "priority", "adaptive")
**When** the fallback chain executes
**Then** the strategy determines how fallbacks are attempted
**And** the appropriate fallback behavior is applied

**Given** a selector with custom hint rules
**When** fallback is triggered
**Then** the custom rules are evaluated
**And** the fallback behavior follows the custom logic

---

#### Story 2.3: Stability-Based Prioritization

As a **developer**,
I want **to prioritize selectors based on stability hints**,
So that **more stable selectors are tried first, reducing the likelihood of repeated failures**.

**Acceptance Criteria:**

**Given** multiple selectors with different stability scores in hints
**When** building the fallback chain
**Then** selectors are ordered by stability (highest first)
**And** the most stable fallback is attempted before less stable ones

**Given** a selector with a stability score of 0.9 (high)
**When** compared to a selector with stability 0.5 (low)
**Then** the high-stability selector is prioritized in the fallback order
**And** low-stability selectors are tried as last resorts

**Given** historical stability data from the adaptive module
**When** constructing the fallback chain
**Then** the system can optionally use real stability metrics
**And** combine with YAML hints for optimal ordering

---

### Epic 3: Failure Event Capture & Logging
**Goal:** Capture all selector failure events with full context and submit them to the adaptive module database for analysis.

**FRs covered:** FR8, FR9, FR10, FR19, FR20 (Failure Capture + Sync/Async Capture)

---

#### Story 3.1: Selector Failure Event Capture

As a **scraper system**,
I want **to capture selector failure events**,
So that **all failures are detected and recorded for analysis and learning**.

**Acceptance Criteria:**

**Given** a selector that returns empty or null result
**When** the validation layer checks the result
**Then** a failure event is created
**And** the failure type is set to "empty_result"

**Given** a selector that throws an exception
**When** the exception is caught
**Then** a failure event is created
**And** the failure type is set to "exception" with error details

**Given** a selector that times out
**When** the timeout is detected
**Then** a failure event is created
**And** the failure type is set to "timeout"

**Given** any failure detection
**When** the event is captured
**Then** the event includes: selector_id, page_url, timestamp, failure_type, extractor_id

---

#### Story 3.2: Full Context Failure Logging

As a **developer**,
I want **to log failure events with full context**,
So that **I can debug issues and understand the root cause of failures**.

**Acceptance Criteria:**

**Given** a failure event with all required fields
**When** the event is logged
**Then** the log includes: selector_id, page_url, timestamp, failure_type, extractor_id
**And** attempted_fallbacks array is included (even if empty)

**Given** a failure event during fallback chain execution
**When** logging the event
**Then** the attempted_fallbacks array includes all selectors that were tried
**And** each fallback includes its result (success/failure)

**Given** a page context with additional metadata
**When** creating the failure event
**Then** the page_url includes full URL with any relevant parameters
**And** timestamp is in ISO8601 format

**Given** a failure event
**When** logging to structured logger
**Then** correlation ID is included for tracing
**And** log level is set appropriately (WARNING for single failure, ERROR for critical)

---

#### Story 3.3: Adaptive Module DB Submission

As a **scraper system**,
I want **to submit failure events to the adaptive module database**,
So that **the adaptive system can learn from failures and improve selector suggestions**.

**Acceptance Criteria:**

**Given** a captured failure event
**When** the sync failure capture is triggered
**Then** the event is submitted to the adaptive module DB
**And** the submission completes before continuing

**Given** a submission to the adaptive module
**When** the DB operation succeeds
**Then** the event is stored with all fields
**And** no error is raised to the caller

**Given** a submission to the adaptive module
**When** the DB operation fails
**Then** the error is logged
**And** the failure is handled gracefully (doesn't crash the scraper)

**Given** the adaptive module is unavailable
**When** submitting a failure event
**Then** the event is queued for later retry
**And** the scraper continues without blocking

---

#### Story 3.4: Sync Failure Capture (Immediate)

As a **scraper system**,
I want **to operate with sync failure capture (immediate)**,
So that **failures are captured and submitted right away during extraction**.

**Acceptance Criteria:**

**Given** a selector execution that returns empty
**When** the validation layer detects the failure
**Then** the failure event is captured synchronously
**And** the fallback chain is triggered immediately
**And** the total added latency is ≤ 5 seconds (NFR1)

**Given** a sync failure capture in progress
**When** the adaptive module DB is slow
**Then** the timeout is applied (default 30s per NFR4)
**And** the scraper continues with primary selectors if timeout occurs

**Given** high-volume scraping operations
**When** many failures occur in quick succession
**Then** each failure is captured and submitted
**And** the system handles the load without blocking

---

#### Story 3.5: Async Failure Capture (Learning) - Phase 2

As a **scraper system**,
I want **to operate with async failure capture (learning)**,
So that **failures are captured for learning without impacting extraction performance**.

**Acceptance Criteria:**

**Given** a selector execution that completes successfully
**When** the validation layer validates the result
**Then** a failure event (if any) is captured asynchronously
**And** submitted via fire-and-forget to the adaptive DB
**And** the extraction result is returned immediately without waiting

**Given** async failure capture
**When** the adaptive module DB is unavailable
**Then** events are queued locally
**And** retried when connection is restored
**And** no data is lost

**Given** learning-mode enabled
**When** successful extractions occur
**Then** success events are also captured
**And** submitted to the adaptive module
**And** used to update stability scores

---

### Epic 4: Graceful Degradation
**Goal:** Ensure the scraper continues operating with primary selectors when adaptive services are unavailable.

**FRs covered:** FR17, FR18 (Integration Architecture)

---

#### Story 4.1: Adaptive REST API Integration

As a **scraper system**,
I want **to call the adaptive REST API for alternative resolution**,
So that **I can get alternative selector suggestions when primary selectors fail**.

**Acceptance Criteria:**

**Given** a failed primary selector
**When** calling the adaptive REST API
**Then** a request is sent with selector_id and page_url
**And** alternative selectors are returned if available

**Given** a successful API call
**When** alternatives are received
**Then** the alternatives are used as fallbacks
**And** the fallback chain is extended with these alternatives

**Given** an API call with a selector that has no alternatives
**When** the API responds
**Then** an empty alternatives list is returned
**And** no error is raised

**Given** adaptive API integration
**When** configuring the API client
**Then** timeout is configurable (default 30s per NFR4)
**And** connection pooling is enabled (per NFR5)

---

#### Story 4.2: Service Unavailability Handling

As a **scraper system**,
I want **to handle adaptive service unavailability gracefully**,
So that **the scraper continues with primary selectors when the adaptive module is down**.

**Acceptance Criteria:**

**Given** the adaptive module is completely unavailable
**When** a selector fails and fallback is needed
**Then** the system detects the unavailability
**And** continues with primary selectors only
**And** logs a warning about adaptive service being unavailable

**Given** adaptive service timeout
**When** the API call exceeds the timeout
**Then** the timeout exception is caught
**And** fallback to primary selector continues
**And** the timeout is logged for diagnostics

**Given** intermittent adaptive service failures
**When** a request fails
**Then** retry logic is applied (configurable retries)
**And** if all retries fail, graceful degradation kicks in

**Given** recovery of adaptive service
**When** a new request is made after unavailability
**Then** the system detects the service is back
**And** normal adaptive integration resumes
**And** no manual restart is required

---

### Epic 5: Real-Time Notifications (Phase 2)
**Goal:** Provide WebSocket-based notifications for failures, confidence score updates, and selector health status.

**FRs covered:** FR11, FR12, FR13 (Real-Time Notifications)

---

#### Story 5.1: WebSocket Connection for Failure Notifications

As a **user**,
I want **to receive WebSocket notifications for failures**,
So that **I can be immediately aware when selector failures occur**.

**Acceptance Criteria:**

**Given** a WebSocket connection established
**When** a selector failure is captured
**Then** a failure notification is sent via WebSocket
**And** the notification includes: selector_id, page_url, timestamp, failure_type

**Given** a stable WebSocket connection
**When** the scraper runs
**Then** all failure events are streamed in real-time
**And** no failures are missed due to buffering

**Given** WebSocket connection loss
**When** the connection drops
**Then** automatic reconnection is attempted
**And** the reconnection follows exponential backoff
**And** the system continues to buffer failures during disconnection (per NFR2)

**Given** WebSocket reconnection
**When** the connection is restored
**Then** the system resumes streaming notifications
**And** no duplicate notifications are sent

---

#### Story 5.2: Confidence Score Updates via WebSocket

As a **user**,
I want **to receive confidence score updates**,
So that **I can track selector stability in real-time**.

**Acceptance Criteria:**

**Given** a selector's confidence score changes
**When** the adaptive module updates the score
**Then** a confidence update notification is sent via WebSocket
**And** the notification includes: selector_id, old_score, new_score, reason

**Given** periodic confidence score refresh
**When** scores are recalculated
**Then** updated scores are broadcast to all connected clients
**And** notifications include the recalculation timestamp

**Given** confidence score dropping below threshold
**When** the update is received
**Then** an alert notification is sent
**And** the alert indicates the selector needs attention

---

#### Story 5.3: Selector Health Status Streaming

As a **user**,
I want **to receive selector health status updates**,
So that **I can monitor which selectors are working vs degraded**.

**Acceptance Criteria:**

**Given** a selector health status change
**When** the status changes (healthy → degraded → failed)
**Then** a status update notification is sent via WebSocket
**And** the notification includes: selector_id, old_status, new_status, timestamp

**Given** periodic health check completion
**When** health status is evaluated
**Then** the current health snapshot is broadcast
**And** all connected clients receive the full status list

**Given** multiple selectors with different health states
**When** health status is streamed
**Then** each selector's status is individually updateable
**And** clients can subscribe to specific selectors if needed

---

### Epic 6: Health Monitoring & Blast Radius (Phase 2)
**Goal:** Enable querying of selector confidence scores, displaying health status, and calculating failure impact.

**FRs covered:** FR14, FR15, FR16 (Health & Monitoring)

---

#### Story 6.1: Confidence Score Query API

As a **developer**,
I want **to query the adaptive module for selector confidence scores**,
So that **I can understand which selectors are stable and which need attention**.

**Acceptance Criteria:**

**Given** a selector ID
**When** querying the confidence score API
**Then** the current confidence score (0.0-1.0) is returned
**And** the last updated timestamp is included

**Given** multiple selector IDs
**When** batch querying confidence scores
**Then** all requested scores are returned in a single response
**And** missing selectors return null or not found

**Given** no selector ID specified
**When** querying the API
**Then** all selector confidence scores are returned
**And** pagination is supported for large result sets

**Given** a selector with no historical data
**When** querying the score
**Then** a default score (e.g., 0.5) is returned
**And** a flag indicates the score is estimated

---

#### Story 6.2: Selector Health Status Display

As a **user**,
I want **to display selector health status**,
So that **I can quickly see which selectors are working, degraded, or failed**.

**Acceptance Criteria:**

**Given** a selector's performance history
**When** calculating health status
**Then** the status is one of: healthy (≥0.8), degraded (0.5-0.79), failed (<0.5)
**And** status is calculated based on recent success rate

**Given** a dashboard request
**When** displaying selector health
**Then** all selectors are grouped by status
**And** the display shows: selector_id, status, confidence_score, last_failure

**Given** a degraded selector
**When** displaying health
**Then** the recommended action is shown
**And** any available alternatives are suggested

**Given** real-time status updates
**When** WebSocket connection is active
**Then** health status changes are pushed immediately
**And** the dashboard auto-updates without refresh

---

#### Story 6.3: Blast Radius Calculation

As a **user**,
I want **to calculate blast radius for failures**,
So that **I can understand the impact of a selector failure on data quality**.

**Acceptance Criteria:**

**Given** a selector failure event
**When** calculating blast radius
**Then** the affected data fields are identified
**And** the count of affected records is returned

**Given** a failed selector that extracts "home_team"
**When** blast radius is calculated
**Then** the impact includes: which match records are affected
**And** the severity level (critical/major/minor)

**Given** multiple related selectors
**When** one fails and impacts others
**Then** the blast radius includes cascading effects
**And** all dependent data fields are marked as affected

**Given** a blast radius query
**When** presenting results
**Then** the output includes: failed_selector, affected_fields, affected_records, severity, recommended_actions
