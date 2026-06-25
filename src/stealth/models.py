"""
Type definitions for the Stealth & Anti-Detection System.

Defines data structures for proxy sessions, browser fingerprints, configuration,
and event logging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Literal, Tuple


class ProxyStatus(str, Enum):
    """Status of a proxy session."""
    ACTIVE = "active"
    EXHAUSTED = "exhausted"
    FAILED = "failed"


class EventType(str, Enum):
    """Types of anti-detection events that can be logged."""
    FINGERPRINT_INITIALIZED = "fingerprint_initialized"
    PROXY_SESSION_CREATED = "proxy_session_created"
    PROXY_ROTATED = "proxy_rotated"
    BEHAVIOR_SIMULATED = "behavior_simulated"
    CONSENT_ACCEPTED = "consent_accepted"
    CONSENT_FAILED = "consent_failed"
    MASK_APPLIED = "mask_applied"
    MASK_FAILED = "mask_failed"
    ERROR = "error"


class EventSeverity(str, Enum):
    """Severity levels for logged events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ProxyRotationStrategy(str, Enum):
    """Strategy for rotating proxy sessions."""
    PER_MATCH = "per_match"
    PER_SESSION = "per_session"
    PER_TIMEOUT = "per_timeout"


class BehaviorIntensity(str, Enum):
    """Intensity profile for human behavior emulation."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class FingerprintConsistencyLevel(str, Enum):
    """How strictly to validate fingerprint coherence."""
    STRICT = "strict"
    MODERATE = "moderate"
    RELAXED = "relaxed"


@dataclass
class ProxySession:
    """
    Represents a sticky residential proxy session.
    
    All requests within a session use the same residential IP and maintain
    shared cookie state.
    """
    session_id: str
    ip_address: str
    port: int
    provider: str
    proxy_url: str
    cookies: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: int = 1800  # 30 minutes
    request_count: int = 0
    status: ProxyStatus = ProxyStatus.ACTIVE
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if session has exceeded its TTL."""
        elapsed = (datetime.utcnow() - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds
    
    def mark_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
        self.request_count += 1
    
    def mark_failed(self, reason: str) -> None:
        """Mark session as failed with error reason."""
        self.status = ProxyStatus.FAILED
        self.error_message = reason


@dataclass
class BrowserFingerprint:
    """
    Encapsulates all reported browser properties for a realistic device fingerprint.
    
    All properties must be internally consistent (user-agent matches browser type,
    platform matches OS, plugins match browser, etc).
    """
    user_agent: str
    browser: Literal["chrome", "firefox", "safari"]
    browser_version: str
    platform: Literal["Windows", "macOS", "Linux"]
    platform_version: str
    language: str
    timezone: str
    timezone_offset_minutes: int
    screen_width: int
    screen_height: int
    color_depth: int
    pixel_depth: int
    device_pixel_ratio: float
    plugins: List[str] = field(default_factory=list)
    media_devices: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    consistent: bool = False
    
    def __hash__(self) -> int:
        """Allow fingerprints to be used as dict keys."""
        return hash((self.user_agent, self.browser, self.platform))


@dataclass
class StealthConfig:
    """
    Configuration for the Stealth & Anti-Detection System.
    
    Controls which anti-detection measures are enabled and how they operate.
    """
    # Master switch
    enabled: bool = True
    
    # Fingerprinting
    fingerprint: Optional[BrowserFingerprint] = None
    fingerprint_consistency_level: FingerprintConsistencyLevel = FingerprintConsistencyLevel.MODERATE
    
    # Proxy rotation
    proxy_enabled: bool = True
    proxy_rotation_strategy: ProxyRotationStrategy = ProxyRotationStrategy.PER_MATCH
    proxy_cooldown_seconds: int = 600
    proxy_provider: str = "bright_data"
    proxy_provider_config: Dict[str, Any] = field(default_factory=dict)
    
    # Behavior emulation
    behavior_enabled: bool = True
    behavior_intensity: BehaviorIntensity = BehaviorIntensity.MODERATE
    click_hesitation_ms_range: Tuple[int, int] = (100, 500)
    scroll_variation: float = 0.3
    micro_delay_ms_range: Tuple[int, int] = (10, 100)
    
    # Consent handling
    consent_enabled: bool = True
    consent_aggressive: bool = False
    consent_timeout_seconds: int = 5
    
    # Anti-detection
    anti_detection_enabled: bool = True
    mask_webdriver_property: bool = True
    mask_playwright_indicators: bool = True
    mask_process_property: bool = True
    
    # Resilience
    graceful_degradation: bool = True
    logging_level: Literal["debug", "info", "warning"] = "info"
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate configuration consistency.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        if self.fingerprint and not self.fingerprint.consistent:
            errors.append("Fingerprint is incoherent (consistent=False)")
        
        if self.proxy_cooldown_seconds < 0:
            errors.append("proxy_cooldown_seconds must be >= 0")
        
        if not (0.0 <= self.scroll_variation <= 1.0):
            errors.append("scroll_variation must be between 0.0 and 1.0")
        
        if self.click_hesitation_ms_range[0] < 0 or self.click_hesitation_ms_range[1] < 0:
            errors.append("click_hesitation_ms_range values must be >= 0")
        
        if self.click_hesitation_ms_range[0] > self.click_hesitation_ms_range[1]:
            errors.append("click_hesitation_ms_range[0] must be <= [1]")
        
        if self.consent_timeout_seconds < 0:
            errors.append("consent_timeout_seconds must be >= 0")
        
        if not self.enabled and any([
            self.proxy_enabled,
            self.behavior_enabled,
            self.consent_enabled,
            self.anti_detection_enabled
        ]):
            # Master disabled but subsystems enabled - warn but allow
            pass
        
        return (len(errors) == 0, errors)


@dataclass
class AntiDetectionEvent:
    """
    Audit log entry documenting stealth measures applied.
    
    Enables post-mortem analysis and performance tracking.
    """
    timestamp: datetime
    run_id: str
    match_id: str
    event_type: EventType
    subsystem: Literal["fingerprint", "proxy_manager", "behavior", "consent_handler", "anti_detection", "coordinator"]
    severity: EventSeverity
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[int] = None
    success: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to JSON-serializable dictionary."""
        return {
            "timestamp": self.timestamp.isoformat() + "Z",
            "run_id": self.run_id,
            "match_id": self.match_id,
            "event_type": self.event_type.value,
            "subsystem": self.subsystem,
            "severity": self.severity.value,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "success": self.success,
        }
