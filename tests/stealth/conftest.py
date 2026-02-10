"""
Test fixtures for stealth system testing.

Provides mock configurations, browser fingerprints, and proxy sessions
for unit and integration tests.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

from src.stealth.models import (
    StealthConfig,
    BrowserFingerprint,
    ProxySession,
    AntiDetectionEvent,
    EventType,
    EventSeverity,
    ProxyStatus,
)


@pytest.fixture
def stealth_config_default() -> StealthConfig:
    """Default stealth configuration for testing."""
    return StealthConfig(
        enabled=True,
        proxy_enabled=False,  # No proxy in tests
        behavior_enabled=True,
        consent_enabled=True,
        anti_detection_enabled=True,
        graceful_degradation=True,
        logging_level="debug",
    )


@pytest.fixture
def stealth_config_with_proxy() -> StealthConfig:
    """Stealth configuration with proxy enabled for testing."""
    return StealthConfig(
        enabled=True,
        proxy_enabled=True,
        proxy_provider="mock",
        behavior_enabled=True,
        consent_enabled=True,
        anti_detection_enabled=True,
        graceful_degradation=True,
    )


@pytest.fixture
def stealth_config_disabled() -> StealthConfig:
    """Disabled stealth configuration."""
    return StealthConfig(
        enabled=False,
        graceful_degradation=True,
    )


@pytest.fixture
def browser_fingerprint_chrome() -> BrowserFingerprint:
    """Mock Chrome browser fingerprint."""
    return BrowserFingerprint(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        browser="chrome",
        browser_version="120.0.0.0",
        platform="Win32",
        language="en-US",
        timezone="America/New_York",
        screen_width=1920,
        screen_height=1080,
        color_depth=24,
        device_pixel_ratio=1.0,
        plugins=["Flash", "Java"],
        media_devices={"videoinput": 1, "audioinput": 1},
        timestamp="2024-01-15T10:30:00Z",
        consistent=True,
    )


@pytest.fixture
def browser_fingerprint_firefox() -> BrowserFingerprint:
    """Mock Firefox browser fingerprint."""
    return BrowserFingerprint(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        browser="firefox",
        browser_version="121.0",
        platform="Win32",
        language="en-US",
        timezone="America/Los_Angeles",
        screen_width=1600,
        screen_height=900,
        color_depth=32,
        device_pixel_ratio=1.5,
        plugins=["Flash"],
        media_devices={"videoinput": 2, "audioinput": 2},
        timestamp="2024-01-15T10:30:00Z",
        consistent=True,
    )


@pytest.fixture
def proxy_session_active() -> ProxySession:
    """Mock active proxy session."""
    return ProxySession(
        session_id="proxy-sess-001",
        ip_address="192.168.1.100",
        port=8080,
        provider="bright_data",
        proxy_url="http://192.168.1.100:8080",
        cookies={},
        status=ProxyStatus.ACTIVE,
        ttl_seconds=3600,
        metadata={"datacenter": "US-East", "rotation_count": 5},
    )


@pytest.fixture
def proxy_session_expired() -> ProxySession:
    """Mock expired proxy session."""
    session = ProxySession(
        session_id="proxy-sess-002",
        ip_address="192.168.1.101",
        port=8080,
        provider="bright_data",
        proxy_url="http://192.168.1.101:8080",
        cookies={},
        status=ProxyStatus.EXPIRED,
        ttl_seconds=0,
        metadata={},
    )
    return session


@pytest.fixture
def proxy_session_failed() -> ProxySession:
    """Mock failed proxy session."""
    session = ProxySession(
        session_id="proxy-sess-003",
        ip_address="192.168.1.102",
        port=8080,
        provider="bright_data",
        proxy_url="http://192.168.1.102:8080",
        cookies={},
        status=ProxyStatus.FAILED,
        ttl_seconds=3600,
        metadata={"failure_reason": "connection_timeout", "failures": 3},
    )
    return session


@pytest.fixture
def anti_detection_event_masking() -> AntiDetectionEvent:
    """Mock anti-detection event for masking."""
    return AntiDetectionEvent(
        timestamp="2024-01-15T10:30:00Z",
        run_id="run-001",
        match_id="match-123",
        event_type=EventType.MASKING_APPLIED,
        subsystem="anti_detection",
        severity=EventSeverity.INFO,
        details={
            "masked_properties": ["navigator.webdriver", "navigator.__proto__.webdriver"],
            "indicators_removed": 2,
        },
        duration_ms=45,
        success=True,
    )


@pytest.fixture
def anti_detection_event_proxy_rotated() -> AntiDetectionEvent:
    """Mock anti-detection event for proxy rotation."""
    return AntiDetectionEvent(
        timestamp="2024-01-15T10:30:15Z",
        run_id="run-001",
        match_id="match-123",
        event_type=EventType.PROXY_ROTATED,
        subsystem="proxy",
        severity=EventSeverity.INFO,
        details={
            "old_ip": "192.168.1.100",
            "new_ip": "192.168.1.101",
            "provider": "bright_data",
        },
        duration_ms=230,
        success=True,
    )


@pytest.fixture
def anti_detection_event_consent_accepted() -> AntiDetectionEvent:
    """Mock anti-detection event for consent acceptance."""
    return AntiDetectionEvent(
        timestamp="2024-01-15T10:30:30Z",
        run_id="run-001",
        match_id="match-123",
        event_type=EventType.CONSENT_ACCEPTED,
        subsystem="consent",
        severity=EventSeverity.INFO,
        details={
            "dialog_type": "gdpr_banner",
            "buttons_clicked": ["accept_all", "save_preferences"],
        },
        duration_ms=150,
        success=True,
    )


@pytest.fixture
def mock_page():
    """Mock Playwright page object."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value="<html></html>")
    page.evaluate = AsyncMock(return_value=None)
    page.evaluate_handle = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.click = AsyncMock()
    page.fill = AsyncMock()
    return page


@pytest.fixture
def mock_browser():
    """Mock Playwright browser object."""
    browser = AsyncMock()
    browser.new_context = AsyncMock()
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def mock_event_publisher():
    """Mock event publisher."""
    publisher = Mock()
    publisher.publish = Mock()
    publisher.subscribe = Mock()
    publisher.unsubscribe = Mock()
    return publisher


# Parameterized fixtures for comprehensive testing

@pytest.fixture(
    params=[
        "chrome",
        "firefox",
        "safari",
    ]
)
def browser_type(request) -> str:
    """Parameterized fixture for different browser types."""
    return request.param


@pytest.fixture(
    params=[
        "default",
        "development",
        "conservative",
        "aggressive",
    ]
)
def config_preset_name(request) -> str:
    """Parameterized fixture for configuration presets."""
    return request.param


@pytest.fixture(
    params=[
        (1920, 1080),
        (1366, 768),
        (1440, 900),
        (2560, 1440),
    ]
)
def screen_dimensions(request) -> tuple:
    """Parameterized fixture for different screen dimensions."""
    return request.param
