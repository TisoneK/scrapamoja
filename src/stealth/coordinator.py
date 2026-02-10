"""
Central coordinator for the Stealth & Anti-Detection System.

StealthSystem orchestrates all stealth subsystems (fingerprinting, proxy rotation,
behavior emulation, consent handling, anti-detection masking) with a unified API.
"""

from __future__ import annotations

from typing import Optional, AsyncIterator
from dataclasses import dataclass
from contextlib import asynccontextmanager
import logging

from .models import (
    StealthConfig,
    BrowserFingerprint,
    ProxySession,
    AntiDetectionEvent,
)
from .events import EventPublisher, EventBuilder
from .anti_detection import AntiDetectionMasker
from .proxy_manager import ProxyManager
from .behavior import BehaviorEmulator
from .fingerprint import FingerprintNormalizer
from .consent_handler import ConsentHandler


logger = logging.getLogger(__name__)


@dataclass
class StealthSystemState:
    """Internal state of the StealthSystem."""
    
    config: StealthConfig
    fingerprint: Optional[BrowserFingerprint] = None
    current_proxy_session: Optional[ProxySession] = None
    event_builder: Optional[EventBuilder] = None
    anti_detection_masker: Optional[AntiDetectionMasker] = None
    proxy_manager: Optional[ProxyManager] = None
    behavior_emulator: Optional[BehaviorEmulator] = None
    fingerprint_normalizer: Optional[FingerprintNormalizer] = None
    consent_handler: Optional[ConsentHandler] = None
    is_active: bool = False


class StealthSystem:
    """
    Central coordinator for anti-detection and stealth operations.

    Manages five independent subsystems:
    - Fingerprint Normalizer: Device property spoofing and consistency
    - Proxy Manager: Rotation and session management
    - Behavior Emulator: Human-like interaction patterns
    - Consent Handler: Cookie consent auto-acceptance
    - Anti-Detection Masker: Automation/bot detection evasion
    """

    def __init__(
        self,
        config: StealthConfig,
        publisher: Optional[EventPublisher] = None,
    ):
        """Initialize StealthSystem.

        Args:
            config: StealthConfig instance with subsystem settings
            publisher: Optional EventPublisher for audit logging (uses default if None)
        """
        self._state = StealthSystemState(config=config)
        self._publisher = publisher
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate configuration on initialization."""
        valid, errors = self._state.config.validate()
        if not valid:
            msg = f"Invalid stealth config: {'; '.join(errors)}"
            logger.error(msg)
            if not self._state.config.graceful_degradation:
                raise ValueError(msg)

    async def __aenter__(self) -> "StealthSystem":
        """Context manager entry - initialize subsystems."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - cleanup resources."""
        await self.shutdown()

    async def initialize(self) -> None:
        """
        Initialize all enabled subsystems.
        """
        logger.info("Initializing StealthSystem")
        self._state.is_active = True

        # Initialize event builder for audit logging
        self._state.event_builder = EventBuilder(run_id="stealth-session")

        # Initialize anti-detection masker
        if self._state.config.anti_detection_enabled:
            self._state.anti_detection_masker = AntiDetectionMasker(
                config=self._state.config.__dict__,
                event_builder=self._state.event_builder,
            )
            logger.debug("Anti-detection masker initialized")

        # Initialize proxy manager
        if self._state.config.proxy_enabled:
            self._state.proxy_manager = ProxyManager(
                provider=self._state.config.proxy_provider,
                config=self._state.config.proxy_provider_config,
                event_builder=self._state.event_builder,
            )
            success = await self._state.proxy_manager.initialize()
            if not success:
                logger.error("Failed to initialize proxy manager")
                if not self._state.config.graceful_degradation:
                    raise RuntimeError("Proxy manager initialization failed")
            else:
                logger.debug("Proxy manager initialized")

        # Initialize behavior emulator
        if getattr(self._state.config, "behavior_emulation_enabled", False):
            self._state.behavior_emulator = BehaviorEmulator(
                intensity=getattr(self._state.config, "behavior_intensity", "moderate"),
                event_builder=self._state.event_builder,
            )
            logger.debug("Behavior emulator initialized")

        # Initialize fingerprint normalizer
        if getattr(self._state.config, "fingerprint_enabled", False):
            self._state.fingerprint_normalizer = FingerprintNormalizer(cache_fingerprints=True)
            logger.debug("Fingerprint normalizer initialized")

        # Initialize consent handler
        if getattr(self._state.config, "consent_handling_enabled", False):
            self._state.consent_handler = ConsentHandler(
                timeout_seconds=getattr(self._state.config, "consent_timeout_seconds", 5.0),
                event_builder=self._state.event_builder,
            )
            logger.debug("Consent handler initialized")

        logger.info("StealthSystem initialization complete")

    async def shutdown(self) -> None:
        """Shutdown all subsystems and cleanup resources."""
        logger.info("Shutting down StealthSystem")
        self._state.is_active = False

    async def get_browser_fingerprint(self) -> BrowserFingerprint:
        """Get or generate browser fingerprint.

        Raises:
            RuntimeError: If system not initialized or fingerprinting disabled
        """
        if not self._state.is_active:
            raise RuntimeError("StealthSystem not initialized")
        if not getattr(self._state.config, "fingerprint_enabled", False):
            raise RuntimeError("Fingerprint disabled in config")

        if not self._state.fingerprint_normalizer:
            logger.warning("Fingerprint normalizer not initialized")
            raise RuntimeError("Fingerprint normalizer not initialized")

        return self._state.fingerprint_normalizer.generate_fingerprint()

    async def get_proxy_session(self) -> Optional[ProxySession]:
        """Get or rotate proxy session."""
        if not self._state.is_active:
            raise RuntimeError("StealthSystem not initialized")

        if not self._state.config.proxy_enabled:
            logger.debug("Proxy disabled, returning None")
            return None

        if not self._state.proxy_manager:
            logger.warning("Proxy manager not initialized")
            return None

        match_id = f"match-{hash(id(self)) % 10000}"
        session = await self._state.proxy_manager.get_next_session(match_id)
        self._state.current_proxy_session = session

        logger.info(f"Got proxy session: {session.session_id}")
        return session

    async def emulate_click(self, page, selector: str, verify_success: bool = True) -> dict:
        """Click element with realistic hesitation."""
        if not self._state.is_active:
            raise RuntimeError("StealthSystem not initialized")

        if not getattr(self._state.config, "behavior_emulation_enabled", False):
            logger.debug("Behavior emulation disabled, clicking directly")
            await page.click(selector)
            return {"success": True, "hesitation_ms": 0}

        if not self._state.behavior_emulator:
            logger.warning("Behavior emulator not initialized")
            await page.click(selector)
            return {"success": True, "hesitation_ms": 0}

        return await self._state.behavior_emulator.click_with_delay(
            page, selector, verify_success=verify_success
        )

    async def emulate_scroll(self, page, direction: str, amount: float = 500) -> dict:
        """Scroll with natural timing and pauses."""
        if not self._state.is_active:
            raise RuntimeError("StealthSystem not initialized")

        if not getattr(self._state.config, "behavior_emulation_enabled", False):
            logger.debug("Behavior emulation disabled, scrolling directly")
            await page.evaluate(f"window.scrollBy(0, {amount if direction == 'down' else -amount})")
            return {"success": True, "segments": 1, "pauses_count": 0}

        if not self._state.behavior_emulator:
            logger.warning("Behavior emulator not initialized")
            await page.evaluate(f"window.scrollBy(0, {amount if direction == 'down' else -amount})")
            return {"success": True, "segments": 1, "pauses_count": 0}

        return await self._state.behavior_emulator.scroll_naturally(page, direction=direction, amount=amount)

    async def add_micro_delay(self) -> dict:
        """Add realistic micro-delay between rapid actions."""
        if not self._state.is_active:
            raise RuntimeError("StealthSystem not initialized")

        if not getattr(self._state.config, "behavior_emulation_enabled", False):
            logger.debug("Behavior emulation disabled, no delay")
            return {"success": True, "delay_ms": 0}

        if not self._state.behavior_emulator:
            logger.warning("Behavior emulator not initialized")
            return {"success": True, "delay_ms": 0}

        return await self._state.behavior_emulator.add_micro_delay()

    async def normalize_dom_tree(self, page) -> None:
        """Apply anti-detection measures to page DOM/CDP."""
        if not self._state.is_active:
            raise RuntimeError("StealthSystem not initialized")

        if not self._state.config.anti_detection_enabled:
            logger.debug("Anti-detection disabled")
            return

        if not self._state.anti_detection_masker:
            logger.warning("Anti-detection masker not initialized")
            return

        await self._state.anti_detection_masker.apply_masks(page)

    async def validate_stealth_measures(self, page) -> list[str]:
        """Validate that stealth measures are applied.
        
        Returns:
            List of warnings if any measures failed, empty list if all OK
        """
        warnings: list[str] = []

        if not self._state.is_active:
            warnings.append("StealthSystem not initialized")
            return warnings

        # Check webdriver property
        webdriver_hidden = await page.evaluate("() => navigator.webdriver === undefined")
        if not webdriver_hidden:
            warnings.append("navigator.webdriver is still visible")

        logger.info(f"Stealth validation complete: {len(warnings)} warnings")
        return warnings

    async def apply_fingerprint_to_browser(self, context) -> None:
        """Apply fingerprint to browser context via CDP.
        
        Args:
            context: Playwright BrowserContext
        """
        if not self._state.is_active:
            raise RuntimeError("StealthSystem not initialized")

        if not getattr(self._state.config, "fingerprint_enabled", False):
            logger.debug("Fingerprint disabled")
            return

        if not self._state.fingerprint_normalizer:
            logger.warning("Fingerprint normalizer not initialized")
            return

        fingerprint = self._state.fingerprint_normalizer.generate_fingerprint()
        await self._state.fingerprint_normalizer.apply_fingerprint_to_context(context, fingerprint)

    async def process_consent_dialog(self, page) -> bool:
        """Detect and process consent dialog.
        
        Args:
            page: Playwright Page object
            
        Returns:
            True if dialog processed (accepted or not present), False if error
        """
        if not self._state.is_active:
            raise RuntimeError("StealthSystem not initialized")

        if not getattr(self._state.config, "consent_handling_enabled", False):
            logger.debug("Consent handling disabled")
            return True

        if not self._state.consent_handler:
            logger.warning("Consent handler not initialized")
            return False

        success = await self._state.consent_handler.detect_and_accept(page)
        return success
