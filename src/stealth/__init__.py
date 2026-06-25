"""
Stealth & Anti-Detection System for Scorewise Scraper

Masks automation indicators, emulates human behavior, rotates proxies,
handles consent dialogs, and normalizes browser fingerprints to bypass
advanced bot detection systems.

Module: src.stealth (v0.1.0)

Architecture:
    - Fingerprint Normalizer: Device property spoofing and consistency
    - Proxy Manager: Rotation and session management
    - Behavior Emulator: Human-like interaction patterns
    - Consent Handler: Cookie consent auto-acceptance
    - Anti-Detection Masker: Automation/bot detection evasion

Example Usage:
    ```python
    import asyncio
    from src.stealth import StealthSystem, get_config_by_name
    
    async def main():
        config = get_config_by_name("default")
        
        async with StealthSystem(config) as stealth:
            fingerprint = await stealth.get_browser_fingerprint()
            proxy = await stealth.get_proxy_session()
            # ... use in Playwright context
    
    asyncio.run(main())
    ```
"""

from .models import (
    ProxySession,
    BrowserFingerprint,
    StealthConfig,
    AntiDetectionEvent,
    # Enums
    ProxyStatus,
    EventType,
    EventSeverity,
    ProxyRotationStrategy,
    BehaviorIntensity,
    FingerprintConsistencyLevel,
)
from .events import (
    EventPublisher,
    EventBuilder,
    get_publisher,
    set_publisher,
)
from .coordinator import StealthSystem
from .config import (
    get_config_by_name,
    load_config_from_file,
    DEFAULT_CONFIG,
    DEVELOPMENT_CONFIG,
    CONSERVATIVE_CONFIG,
    AGGRESSIVE_CONFIG,
)
from .anti_detection import AntiDetectionMasker
from .proxy_manager import (
    ProxyManager,
    ProxyProvider,
    BrightDataProvider,
    OxyLabsProvider,
    MockProxyProvider,
)

__version__ = "0.1.0"
__all__ = [
    # Types
    "ProxySession",
    "BrowserFingerprint",
    "StealthConfig",
    "AntiDetectionEvent",
    # Enums
    "ProxyStatus",
    "EventType",
    "EventSeverity",
    "ProxyRotationStrategy",
    "BehaviorIntensity",
    "FingerprintConsistencyLevel",
    # Event logging
    "EventPublisher",
    "EventBuilder",
    "get_publisher",
    "set_publisher",
    # Coordinator
    "StealthSystem",
    # Configuration
    "get_config_by_name",
    "load_config_from_file",
    "DEFAULT_CONFIG",
    "DEVELOPMENT_CONFIG",
    "CONSERVATIVE_CONFIG",
    "AGGRESSIVE_CONFIG",
    # Anti-detection
    "AntiDetectionMasker",
    # Proxy management
    "ProxyManager",
    "ProxyProvider",
    "BrightDataProvider",
    "OxyLabsProvider",
    "MockProxyProvider",
]
