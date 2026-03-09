# Story 5.1: WebSocket Connection for Failure Notifications

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user**,
I want **to receive WebSocket notifications for failures**,
so that **I can be immediately aware when selector failures occur**.

## Acceptance Criteria

**AC1: WebSocket Connection Establishment**
- **Given** the system needs to send failure notifications
- **When** the WebSocket client initializes
- **Then** a WebSocket connection is established to the configured endpoint
- **And** the connection supports both text and binary messages
- **And** connection configuration includes: URL, protocols, headers (if needed)

**AC2: Failure Notification Sending**
- **Given** a WebSocket connection established
- **When** a selector failure is captured
- **Then** a failure notification is sent via WebSocket
- **And** the notification includes: selector_id, page_url, timestamp, failure_type
- **And** the message format is JSON

**AC3: Real-Time Streaming**
- **Given** a stable WebSocket connection
- **When** the scraper runs
- **Then** all failure events are streamed in real-time
- **And** no failures are missed due to buffering
- **And** latency from failure to notification is minimal (< 100ms target)

**AC4: Automatic Reconnection**
- **Given** WebSocket connection loss
- **When** the connection drops
- **Then** automatic reconnection is attempted
- **And** the reconnection follows exponential backoff
- **And** the system continues to buffer failures during disconnection (per NFR2)
- **And** reconnection config includes: max_retries, base_delay, max_delay

**AC5: No Duplicate Notifications**
- **Given** WebSocket reconnection
- **When** the connection is restored
- **Then** the system resumes streaming notifications
- **And** no duplicate notifications are sent
- **And** a unique message ID is included in each notification

## Tasks / Subtasks

- [x] Task 1: Create WebSocket client module (AC: 1, 4, 5)
  - [x] Subtask 1.1: Create `src/selectors/websocket/` directory with `__init__.py`
  - [x] Subtask 1.2: Create `client.py` with WebSocket client class
  - [x] Subtask 1.3: Implement connection establishment with configurable endpoint
  - [x] Subtask 1.4: Implement exponential backoff reconnection logic
  - [x] Subtask 1.5: Add message ID generation for deduplication

- [x] Task 2: Implement failure notification sending (AC: 2, 3)
  - [x] Subtask 2.1: Create notification message schema (JSON format)
  - [x] Subtask 2.2: Integrate with existing failure event capture (from Epic 3)
  - [x] Subtask 2.3: Implement real-time message dispatch
  - [x] Subtask 2.4: Ensure thread-safe/async-safe message queue

- [x] Task 3: Buffer failures during disconnection (AC: 4)
  - [x] Subtask 3.1: Implement local buffer for failures during disconnection
  - [x] Subtask 3.2: Flush buffer on reconnection
  - [x] Subtask 3.3: Handle buffer overflow gracefully (configurable max size)

- [x] Task 4: Write unit tests (AC: 1, 2, 3, 4, 5)
  - [x] Subtask 4.1: Test WebSocket connection establishment
  - [x] Subtask 4.2: Test failure notification message format
  - [x] Subtask 4.3: Test exponential backoff reconnection
  - [x] Subtask 4.4: Test no duplicate notifications
  - [x] Subtask 4.5: Test buffer flush on reconnection

## Dev Notes

### What This Story Implements

1. **WebSocket client module** - Create `src/selectors/websocket/` with client implementation
2. **Failure notification integration** - Wire WebSocket notifications into existing failure capture (Epic 3)
3. **Reconnection logic** - Implement exponential backoff with buffering
4. **Message deduplication** - Unique IDs to prevent duplicate notifications

### What This Story Does NOT Include

- Confidence score updates via WebSocket (Story 5-2)
- Selector health status streaming (Story 5-3)
- WebSocket server implementation (client-side only for this story)
- Authentication/authorization for WebSocket connection
- TLS/SSL configuration (assumed handled at infrastructure level)

### 🚨 Critical Anti-Patterns to Avoid

1. **DO NOT** use synchronous WebSocket libraries - MUST use async (websockets, aiohttp.wsgi, or FastAPI WebSocket)
2. **DO NOT** implement WebSocket server here - this is a CLIENT implementation
3. **DO NOT** block on connection failures - MUST be async with proper timeout handling
4. **DO NOT** use polling as fallback - WebSocket must be the primary transport
5. **DO NOT** hardcode WebSocket URL - MUST be configurable via settings/environment
6. **DO NOT** ignore NFR2 requirement - automatic reconnection with exponential backoff is MANDATORY

### Architecture Patterns

**Integration with Existing Systems:**

```
src/selectors/
├── websocket/           # NEW - WebSocket client for failure notifications
│   ├── __init__.py
│   ├── client.py       # WebSocketClient class
│   ├── config.py       # WebSocket configuration
│   └── models.py       # Notification message schemas
├── hooks/
│   └── post_extraction.py  # MODIFY - Add WebSocket notification call
└── fallback/
    └── chain.py        # MODIFY - Add notification on fallback failure
```

**Message Schema (JSON):**
```python
class FailureNotification(BaseModel):
    message_id: str  # UUID for deduplication
    selector_id: str
    page_url: str
    timestamp: datetime  # ISO8601
    failure_type: str  # empty_result, exception, timeout
    extractor_id: str
```

**Configuration (Pydantic):**
```python
class WebSocketConfig(BaseModel):
    url: str  # WebSocket endpoint URL
    max_retries: int = 5
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    buffer_size: int = 100
    message_timeout: float = 10.0
```

### Project Structure Notes

- Follow existing module structure from `src/selectors/`
- Use same patterns as `src/selectors/adaptive/` for configuration
- Leverage existing failure event models from `src/selectors/fallback/models.py`
- DO NOT create new exceptions - extend from `src/selectors/exceptions.py`

### Testing Requirements

- Unit tests in `tests/selectors/websocket/`
- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`
- Mock WebSocket server for unit tests
- Integration test with actual WebSocket echo server if available
- Test coverage target: 80%+ for new modules

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-5.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Deferred-Decisions]
- [Source: _bmad-output/project-context.md#Technology-Stack]
- [Source: _bmad-output/project-context.md#Framework-Specific-Rules]
- [NFR2: WebSocket Connection - Maintain stable connection for real-time notifications with automatic reconnection]

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- **Story 5-1 Implementation Complete** (2026-03-08):
  - Created WebSocket client module with async support
  - Implemented exponential backoff reconnection (AC4)
  - Integrated with existing failure event capture from Epic 3
  - Added message deduplication via unique IDs (AC5)
  - Implemented local buffer for failures during disconnection (Task 3)
  - Added unit tests for core functionality

### File List

**New Files:**
- `src/selectors/websocket/__init__.py`
- `src/selectors/websocket/client.py`
- `src/selectors/websocket/config.py`
- `src/selectors/websocket/models.py`
- `src/selectors/websocket/integration.py`
- `tests/selectors/websocket/__init__.py`
- `tests/selectors/websocket/test_client.py`

**Modified Files:**
- `src/selectors/hooks/post_extraction.py` - Add WebSocket notification call
