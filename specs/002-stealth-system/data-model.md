# Data Model: Stealth & Anti-Detection System

**Date**: 2026-01-27  
**Feature**: [002-stealth-system](spec.md)  
**Phase**: Phase 1 - Design

## Entity Definitions

### ProxySession

Represents a single residential IP session used during one match scrape. Maintains sticky session state (cookies, authentication) for all requests within the session.

**Attributes**:
- `session_id: str` - Unique identifier (UUID)
- `ip_address: str` - Residential IP assigned (e.g., "203.0.113.42")
- `port: int` - Proxy port (typically 80, 8080, 22225, provider-specific)
- `provider: str` - Provider name (e.g., "bright_data", "oxylabs", "mock")
- `proxy_url: str` - Full proxy endpoint URL with authentication
- `cookies: dict[str, str]` - Session cookies, persisted across requests
- `created_at: datetime` - When session was established
- `last_activity: datetime` - Last request timestamp
- `ttl_seconds: int` - Time-to-live for session; auto-close after timeout
- `request_count: int` - Number of requests through this session
- `status: Literal['active', 'exhausted', 'failed']` - Session state
- `error_message: Optional[str]` - If status='failed', reason for failure
- `metadata: dict` - Provider-specific metadata (zone, country, etc.)

**Relationships**:
- Belongs to: One match scrape operation
- Contains: Session cookies and authentication state
- Referenced by: Proxy requests during extraction

**Lifecycle**:
1. Created when match scrape begins → status='active'
2. Active during all requests within match → cookies accumulated
3. On exhaustion (timeout/max-requests) or failure (IP blocked) → status changes
4. Closed at end of match scrape
5. Available for reuse after cooldown period (if status='exhausted' with health checks)

**Schema Version**: 1.0

---

### BrowserFingerprint

Encapsulates all reported browser properties that must be internally consistent. A device fingerprint is a set of attributes that together represent a realistic device/browser combination.

**Attributes**:
- `user_agent: str` - Full user-agent string (e.g., "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...")
- `browser: Literal['chrome', 'firefox', 'safari']` - Inferred browser type
- `browser_version: str` - Version (e.g., "120.0.6099.129")
- `platform: Literal['Windows', 'macOS', 'Linux']` - Operating system
- `platform_version: str` - OS version (e.g., "10.0", "14.1", "5.15")
- `language: str` - Accept-Language header (e.g., "en-US")
- `timezone: str` - Timezone identifier (e.g., "America/New_York", "UTC")
- `timezone_offset_minutes: int` - Offset from UTC (-480 to 840)
- `screen_width: int` - Display width in pixels (e.g., 1920)
- `screen_height: int` - Display height in pixels (e.g., 1080)
- `color_depth: int` - Bit depth (8, 16, 24, 32)
- `pixel_depth: int` - Same as color_depth (browser compatibility)
- `device_pixel_ratio: float` - Retina/DPI scaling (1.0, 1.5, 2.0)
- `plugins: list[str]` - Browser extensions (e.g., ["Chrome PDF Plugin", "Chrome PDF Viewer"])
- `media_devices: dict` - Audio/video device info
- `timestamp: datetime` - When fingerprint was generated
- `consistent: bool` - Validation flag; True if all attributes are coherent

**Coherence Rules** (validated on creation):
- User-agent browser type matches declared browser ✓
- Platform matches user-agent OS ✓
- Language is valid ISO-639-1 code (e.g., "en") + valid ISO-3166 region (e.g., "US") ✓
- Timezone is valid IANA timezone ✓
- Screen resolution is achievable for declared platform (no 3840x2160 on Windows 95) ✓
- Color depth is valid (8, 16, 24, or 32) ✓
- Plugins match browser type (Safari uses different plugins than Chrome) ✓
- All attributes together represent a statistically plausible device ✓

**Relationships**:
- Used by: StealthSystem on every page load
- Validated by: FingerprintNormalizer coherence checks
- Logged by: AntiDetectionEvent on fingerprint initialization

**Schema Version**: 1.0

---

### StealthConfig

Configuration object controlling which anti-detection measures are applied and how. Acts as primary interface between caller and stealth subsystems.

**Attributes**:
- `enabled: bool` - Master switch; False disables all stealth (default: True)
- `fingerprint: BrowserFingerprint` - Device fingerprint to report (generated if not provided)
- `fingerprint_consistency_level: Literal['strict', 'moderate', 'relaxed']` - How strictly to validate coherence (default: 'moderate')
- `proxy_enabled: bool` - Whether to use residential proxy (default: True)
- `proxy_rotation_strategy: Literal['per_match', 'per_session', 'per_timeout']` - When to rotate IPs (default: 'per_match')
- `proxy_cooldown_seconds: int` - How long before an IP can be reused (default: 600)
- `proxy_provider: str` - Provider name ('bright_data', 'oxylabs', 'mock')
- `proxy_provider_config: dict` - Provider-specific settings (auth, zone, country)
- `behavior_enabled: bool` - Whether to emulate human behavior (default: True)
- `behavior_intensity: Literal['conservative', 'moderate', 'aggressive']` - Timing variance level (default: 'moderate')
- `click_hesitation_ms_range: tuple[int, int]` - Min/max ms before click execution (default: (50, 400))
- `scroll_variation: float` - Scroll speed variance 0.0-1.0 (default: 0.3)
- `micro_delay_ms_range: tuple[int, int]` - Delay between rapid actions (default: (5, 100))
- `consent_enabled: bool` - Whether to auto-handle consent dialogs (default: True)
- `consent_aggressive: bool` - Accept all cookies vs conservative accept (default: False)
- `consent_timeout_seconds: int` - How long to look for dialog (default: 5)
- `anti_detection_enabled: bool` - Whether to mask automation indicators (default: True)
- `mask_webdriver_property: bool` - Remove navigator.webdriver (default: True)
- `mask_playwright_indicators: bool` - Remove Playwright-specific markers (default: True)
- `mask_process_property: bool` - Remove process.version (default: True)
- `graceful_degradation: bool` - Continue on stealth component failure (default: True)
- `logging_level: Literal['debug', 'info', 'warning']` - Verbosity (default: 'info')

**Validation**:
- fingerprint.consistent must be True after initialization
- proxy_cooldown_seconds >= 0
- behavior_intensity matches one of allowed values
- proxy_provider supported by system
- At least one stealth measure enabled if enabled=True

**Relationships**:
- Passed to: StealthSystem.initialize()
- Used by: All five stealth subsystems
- Referenced by: Configuration loader (from YAML)

**Default Production Configuration**:
```yaml
stealth:
  enabled: true
  fingerprint_consistency_level: "moderate"
  proxy_enabled: true
  proxy_rotation_strategy: "per_match"
  proxy_cooldown_seconds: 600
  behavior_enabled: true
  behavior_intensity: "moderate"
  consent_enabled: true
  consent_timeout_seconds: 5
  anti_detection_enabled: true
  graceful_degradation: true
  logging_level: "info"
```

**Schema Version**: 1.0

---

### AntiDetectionEvent

Audit log entry documenting stealth measures applied during execution. Enables post-mortem analysis and performance tracking.

**Attributes**:
- `timestamp: datetime` - When event occurred (UTC)
- `run_id: str` - Unique identifier for entire scraper run (UUID)
- `match_id: str` - Match being scraped when event occurred
- `event_type: Literal['fingerprint_initialized', 'proxy_session_created', 'proxy_rotated', 'behavior_simulated', 'consent_accepted', 'consent_failed', 'mask_applied', 'mask_failed', 'error']` - What happened
- `subsystem: Literal['fingerprint', 'proxy_manager', 'behavior', 'consent_handler', 'anti_detection', 'coordinator']` - Which subsystem generated event
- `severity: Literal['debug', 'info', 'warning', 'error']` - Event importance
- `details: dict` - Event-specific data (see subsystem details below)
- `duration_ms: Optional[int]` - How long operation took
- `success: bool` - Whether operation succeeded

**Event Types & Details**:

**fingerprint_initialized**
```python
{
    "user_agent": "Mozilla/5.0 ...",
    "browser": "chrome",
    "platform": "Windows",
    "consistency_check_passed": True,
    "duration_ms": 45
}
```

**proxy_session_created**
```python
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "ip_address": "203.0.113.42",
    "provider": "bright_data",
    "duration_ms": 120
}
```

**proxy_rotated**
```python
{
    "old_session_id": "...",
    "new_session_id": "...",
    "reason": "match_completed|timeout|exhausted",
    "ip_reuse_available": False
}
```

**behavior_simulated**
```python
{
    "behavior_type": "click|scroll|micro_delay",
    "element_selector": ".odds-button",
    "delay_ms": 245,
    "intensity": "moderate"
}
```

**consent_accepted**
```python
{
    "dialog_type": "cookie_banner|gdpr_modal|generic_modal",
    "dialog_selector": "[role='dialog']",
    "button_found": True,
    "button_selector": "button:has-text('Accept')",
    "duration_ms": 680
}
```

**consent_failed**
```python
{
    "reason": "dialog_not_found|button_not_found|click_failed|timeout",
    "dialog_detected": False,
    "timeout_seconds": 5,
    "duration_ms": 5100
}
```

**mask_applied**
```python
{
    "mask_type": "navigator.webdriver|playwright_indicators|process.version",
    "duration_ms": 15,
    "verification": "applied"  # Did we verify it worked?
}
```

**error**
```python
{
    "error_type": "ProxyConnectionError|ConsentTimeoutError|FingerprintValidationError",
    "error_message": "Proxy IP blocked after 3 retries",
    "graceful_degradation_enabled": True
}
```

**Relationships**:
- Published by: All stealth subsystems
- Consumed by: Structured logging system
- Queried for: Performance analysis, debugging, compliance auditing

**Retention**: Events logged to structured JSON, searchable by run_id/match_id for entire scraper execution

**Schema Version**: 1.0

---

## Entity Relationships

```
StealthConfig
├── BrowserFingerprint (one-to-one)
│   └── Used in StealthSystem.initialize()
│
├── ProxySession (one-to-many)
│   ├── Created by ProxyManager per match
│   ├── Updated with cookies during navigation
│   └── Closed when match completes
│
└── AntiDetectionEvent (one-to-many)
    ├── Generated by all subsystems
    ├── Grouped by run_id/match_id
    └── Logged to JSON structure
```

---

## Storage & Persistence

### Configuration Storage (YAML)

StealthConfig loaded from `config/stealth.yaml`:
```yaml
stealth:
  fingerprint:
    consistency_level: "moderate"
    # fingerprint auto-generated unless specified
  proxy:
    enabled: true
    rotation_strategy: "per_match"
    cooldown_seconds: 600
    provider: "bright_data"
    bright_data:
      zone: "my_zone"
      country: "US"
  behavior:
    enabled: true
    intensity: "moderate"
    click_hesitation_range: [50, 400]
    scroll_variation: 0.3
  consent:
    enabled: true
    aggressive: false
    timeout_seconds: 5
  anti_detection:
    enabled: true
    mask_webdriver: true
    mask_playwright: true
    mask_process: true
  graceful_degradation: true
```

### Event Logging (JSON)

AntiDetectionEvent entries logged to `data/logs/stealth-{run_id}.json`:
```json
[
  {
    "timestamp": "2026-01-27T14:32:15.123Z",
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "match_id": "flashscore-123456",
    "event_type": "fingerprint_initialized",
    "subsystem": "fingerprint",
    "severity": "info",
    "success": true,
    "details": {...},
    "duration_ms": 45
  },
  ...
]
```

### Session State (Pickle/JSON)

ProxySession state persisted to `data/storage/proxy-sessions/{run_id}.json`:
```json
{
  "550e8400-e29b-41d4-a716-446655440000": {
    "session_id": "...",
    "ip_address": "203.0.113.42",
    "cookies": {"session_id": "abc123", ...},
    "status": "active",
    "created_at": "2026-01-27T14:32:20Z",
    ...
  }
}
```

---

## Schema Versioning

**Current Schema Version**: 1.0

**Backward Compatibility**: 
- BrowserFingerprint v1.0 → v1.1: Add new optional fields with defaults
- ProxySession v1.0 → v1.1: Add new fields to metadata dict
- StealthConfig v1.0 → v1.1: Add new config keys with sensible defaults
- AntiDetectionEvent v1.0 → v1.1: Add new event_type values, extend details dict

**Migration Policy**:
- Config loader handles version detection
- Old config files loaded with auto-upgrade to latest schema
- Events use type union for backward compatibility (old_event_type | new_event_type)
