# Stealth System API Contracts

**Date**: 2026-01-27  
**Feature**: [002-stealth-system](spec.md)  
**Phase**: Phase 1 - Design

## Main Coordinator Interface

The `StealthSystem` class is the primary public API. All stealth functionality is accessed through this coordinator.

```python
from typing import Optional, Dict, Any, List
from datetime import datetime
from playwright.async_api import Page, BrowserContext
from .types import StealthConfig, ProxySession, BrowserFingerprint, AntiDetectionEvent

class StealthSystem:
    """Coordinates all stealth subsystems (fingerprint, proxy, behavior, consent, anti-detection)"""
    
    async def initialize(self, config: StealthConfig) -> None:
        """
        Initialize stealth system with configuration.
        
        Args:
            config: StealthConfig with all stealth settings
            
        Raises:
            FingerprintValidationError: If fingerprint is incoherent
            ProxyInitializationError: If proxy provider fails to initialize
            
        Side Effects:
            - Validates fingerprint coherence
            - Initializes proxy provider connection
            - Sets up behavior emulation profiles
            - Registers consent dialog patterns
            - Enables automation masking in CDP
            - Publishes 'fingerprint_initialized' event
        """
        
    async def shutdown(self) -> None:
        """
        Gracefully shutdown stealth system.
        
        Side Effects:
            - Closes all active proxy sessions
            - Flushes pending events
            - Cleans up resources
        """
    
    # Proxy session management
    
    async def create_proxy_session(self, match_id: str) -> ProxySession:
        """
        Create a new sticky proxy session for a match.
        
        Args:
            match_id: Identifier for the match being scraped
            
        Returns:
            ProxySession with active residential IP
            
        Raises:
            ProxyInitializationError: If proxy provider unavailable
            
        Guarantees:
            - Session IP remains constant for all requests within session
            - Cookies accumulated in session are preserved
            - Session timeout auto-closes after configured TTL
            
        Publishes:
            - 'proxy_session_created' event with session details
        """
    
    async def close_proxy_session(self, session_id: str) -> None:
        """
        Close a proxy session and mark IP for rotation.
        
        Args:
            session_id: Session to close
            
        Side Effects:
            - Flushes session cookies to disk
            - Marks IP for cooldown before reuse
            - Updates session status
            
        Publishes:
            - 'proxy_session_closed' event
        """
    
    async def get_proxy_session(self, session_id: str) -> Optional[ProxySession]:
        """Retrieve active session by ID (internal use)"""
    
    # Browser fingerprinting
    
    async def get_active_fingerprint(self) -> BrowserFingerprint:
        """
        Get current active browser fingerprint.
        
        Returns:
            BrowserFingerprint with all device properties
            
        Guarantees:
            - All properties are internally consistent
            - Matches user-agent string declared in config
            - Realistic for target platform/browser
        """
    
    async def apply_fingerprint_to_browser(self, context: BrowserContext) -> None:
        """
        Apply fingerprint properties to browser context via CDP.
        
        Args:
            context: Playwright BrowserContext to modify
            
        Side Effects:
            - Injects fingerprint via CDP deviceEmulationParameters
            - Sets navigator properties via init_script
            - Configures user-agent string
            - Sets timezone/language headers
            
        Publishes:
            - 'fingerprint_applied' event
        """
    
    # Behavior emulation
    
    async def emulate_click(self, page: Page, selector: str, match_id: str) -> None:
        """
        Click element with human-like timing and movement.
        
        Args:
            page: Playwright Page
            selector: CSS selector for element to click
            match_id: For event logging correlation
            
        Raises:
            ElementNotFoundError: If selector doesn't match
            
        Side Effects:
            - Moves mouse with natural Bézier curve
            - Applies random click hesitation delay (100-500ms default)
            - Performs click at target position
            - Logs behavior telemetry
            
        Publishes:
            - 'behavior_simulated' event with delay metrics
        """
    
    async def emulate_scroll(
        self,
        page: Page,
        direction: str,  # 'up' | 'down'
        amount: int,  # pixels
        match_id: str,
        include_pause: bool = True
    ) -> None:
        """
        Scroll page with natural speed variation and pauses.
        
        Args:
            page: Playwright Page
            direction: Scroll direction
            amount: Pixels to scroll
            match_id: For event logging
            include_pause: Whether to add natural dwell time
            
        Side Effects:
            - Scrolls page at variable speed (not linear)
            - May include pause/dwell at end of scroll
            - Logs scroll telemetry
            
        Publishes:
            - 'behavior_simulated' event
        """
    
    async def add_micro_delay(self, match_id: str) -> None:
        """
        Add small random delay between rapid actions.
        
        Typical use: Between clicking a tab and reading results.
        
        Args:
            match_id: For event logging
            
        Side Effects:
            - Sleeps for random duration (5-150ms default)
            - Logs delay metrics
            
        Publishes:
            - 'behavior_simulated' event
        """
    
    # Consent handling
    
    async def process_consent_dialog(self, page: Page, match_id: str) -> bool:
        """
        Detect and accept GDPR/cookie consent dialogs.
        
        Args:
            page: Playwright Page
            match_id: For event logging
            
        Returns:
            True if consent processed, False if no dialog found
            
        Side Effects:
            - Detects consent dialog patterns
            - Finds and clicks accept button
            - Verifies dialog closed
            - Logs consent action
            
        Publishes:
            - 'consent_accepted' event if successful
            - 'consent_failed' event if dialog found but not handled
            
        Guarantees:
            - If returns True, consent was accepted and dismissed
            - If returns False, either no dialog found OR dialog still present
            - Never crashes; logs failure and continues
        """
    
    # Validation
    
    async def validate_stealth_measures(self, page: Page, match_id: str) -> List[str]:
        """
        Validate stealth measures are working (detection test).
        
        Args:
            page: Playwright Page to test
            match_id: For logging
            
        Returns:
            List of warnings (empty if all checks pass)
            Examples: ["navigator.webdriver property detected", "Playwright console patch found"]
            
        Side Effects:
            - Injects detection test code
            - Checks for automation indicators
            - Logs validation results
            
        Publishes:
            - 'validation_completed' event with results
        """
    
    async def get_event_log(self, run_id: str, match_id: Optional[str] = None) -> List[AntiDetectionEvent]:
        """
        Retrieve logged stealth events for debugging.
        
        Args:
            run_id: Run identifier
            match_id: Optional filter by match
            
        Returns:
            List of AntiDetectionEvent entries
        """


# Error Types

class StealthError(Exception):
    """Base exception for stealth system"""
    pass

class FingerprintValidationError(StealthError):
    """Fingerprint attributes are incoherent"""
    pass

class ProxyInitializationError(StealthError):
    """Proxy provider failed to initialize"""
    pass

class ProxyConnectionError(StealthError):
    """Proxy IP is unreachable or blocked"""
    pass

class ConsentHandlingError(StealthError):
    """Consent dialog detection or handling failed"""
    pass
```

---

## Fingerprint Normalizer Subsystem Interface

```python
from .types import BrowserFingerprint

class FingerprintNormalizer:
    """Generates and validates realistic browser fingerprints"""
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Load device characteristic distributions"""
    
    def generate_fingerprint(
        self,
        browser: str = None,  # 'chrome' | 'firefox' | 'safari' or random
        platform: str = None,  # 'Windows' | 'macOS' | 'Linux' or random
        language: str = None,  # 'en-US' | 'en-GB' etc. or random
    ) -> BrowserFingerprint:
        """
        Generate realistic browser fingerprint.
        
        Returns:
            BrowserFingerprint with all coherent attributes
            
        Guarantees:
            - All properties are internally consistent
            - User-agent matches declared browser/version
            - Screen resolution is realistic for platform
            - Plugins match browser type
            - Timezone/language combination is plausible
        """
    
    def validate_coherence(self, fingerprint: BrowserFingerprint) -> tuple[bool, List[str]]:
        """
        Check if fingerprint attributes are coherent.
        
        Returns:
            (is_valid, list_of_conflicts)
            
        Example conflicts:
            - ["Chrome v120 reports Firefox plugins"]
            - ["4320x2160 is impossible for typical display"]
            - ["Timezone offset doesn't match timezone string"]
        """
    
    def get_safe_defaults(self) -> BrowserFingerprint:
        """
        Return maximally realistic default fingerprint.
        
        Used when fingerprint generation fails coherence check.
        """
```

---

## Proxy Manager Subsystem Interface

```python
from .types import ProxySession

class ProxyManager:
    """Manages residential IP rotation and sticky sessions"""
    
    async def initialize(self, provider: str, config: Dict[str, Any]) -> None:
        """
        Initialize proxy provider.
        
        Args:
            provider: 'bright_data' | 'oxylabs' | 'mock'
            config: Provider-specific configuration
            
        Raises:
            ProxyInitializationError: If provider unavailable
        """
    
    async def get_next_session(self, match_id: str) -> ProxySession:
        """
        Get next sticky proxy session for match.
        
        Returns:
            ProxySession with residential IP and proxy_url
            
        Guarantees:
            - Session will not rotate IP within match
            - Cookies accumulated in session are preserved
            - Session timeout is enforced
        """
    
    async def retire_session(self, session_id: str) -> None:
        """Mark session for rotation and apply cooldown"""
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check proxy provider health.
        
        Returns:
            {'status': 'healthy', 'available_proxies': 15, 'failed_proxies': 2, ...}
        """
```

---

## Behavior Emulator Subsystem Interface

```python
from playwright.async_api import Page

class BehaviorEmulator:
    """Simulates human interaction timing and patterns"""
    
    def set_intensity(self, intensity: str) -> None:
        """Set behavior profile: 'conservative' | 'moderate' | 'aggressive'"""
    
    async def click_with_delay(self, page: Page, selector: str) -> None:
        """Click with human-like hesitation and movement"""
    
    async def scroll_naturally(
        self,
        page: Page,
        direction: str,
        amount: int,
        include_pause: bool = True
    ) -> None:
        """Scroll with natural speed variation"""
    
    async def add_micro_delay(self) -> None:
        """Random small delay between actions"""
```

---

## Consent Handler Subsystem Interface

```python
from playwright.async_api import Page

class ConsentHandler:
    """Detects and handles GDPR/cookie consent workflows"""
    
    async def detect_dialog(self, page: Page) -> Optional[str]:
        """
        Detect consent dialog on page.
        
        Returns:
            Dialog selector if found, None otherwise
        """
    
    async def accept_consent(self, page: Page) -> bool:
        """
        Accept consent dialog.
        
        Returns:
            True if accepted, False if dialog not found/handled
        """
    
    def register_pattern(self, pattern_name: str, detectors: List[str]) -> None:
        """Register custom dialog detection pattern"""
```

---

## Anti-Detection Masker Subsystem Interface

```python
from playwright.async_api import BrowserContext

class AntiDetectionMasker:
    """Masks Playwright automation indicators"""
    
    async def apply_masks(self, context: BrowserContext) -> None:
        """Apply all anti-detection masks via CDP"""
    
    async def mask_webdriver_property(self, context: BrowserContext) -> None:
        """Remove navigator.webdriver property"""
    
    async def mask_playwright_indicators(self, context: BrowserContext) -> None:
        """Remove Playwright-specific console methods and properties"""
    
    async def mask_process_property(self, context: BrowserContext) -> None:
        """Remove process.version property"""
```

---

## Event Publishing Interface

```python
from .types import AntiDetectionEvent

class EventPublisher:
    """Publishes stealth system events for logging and monitoring"""
    
    def publish(self, event: AntiDetectionEvent) -> None:
        """Publish event to handlers"""
    
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to events of specific type"""
```

---

## Usage Example

```python
import asyncio
from playwright.async_api import async_playwright
from stealth import StealthSystem, StealthConfig, BrowserFingerprint

async def main():
    # Initialize
    config = StealthConfig(
        enabled=True,
        proxy_enabled=True,
        behavior_enabled=True,
        consent_enabled=True,
        anti_detection_enabled=True,
    )
    
    stealth = StealthSystem()
    await stealth.initialize(config)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        
        # Apply stealth measures
        await stealth.apply_fingerprint_to_browser(context)
        page = await context.new_page()
        
        # Navigate with stealth
        await page.goto("https://www.flashscore.com")
        
        # Handle consent
        if await stealth.process_consent_dialog(page, match_id="match-123"):
            print("Consent accepted")
        
        # Get proxy session
        proxy_session = await stealth.create_proxy_session("match-123")
        print(f"Using proxy: {proxy_session.ip_address}")
        
        # Human-like interactions
        await stealth.emulate_click(page, ".odds-button", "match-123")
        await stealth.add_micro_delay("match-123")
        await stealth.emulate_scroll(page, "down", 500, "match-123")
        
        # Validate stealth measures
        warnings = await stealth.validate_stealth_measures(page, "match-123")
        if warnings:
            print(f"Stealth warnings: {warnings}")
        
        # Cleanup
        await stealth.close_proxy_session(proxy_session.session_id)
        await context.close()
        await browser.close()
        await stealth.shutdown()

asyncio.run(main())
```
