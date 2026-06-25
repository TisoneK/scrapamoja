"""
Consent dialog handling subsystem.

ConsentHandler automatically detects and accepts GDPR/cookie consent dialogs
on websites to enable automated scraping without manual intervention.

Key responsibilities:
- Detect consent dialogs using DOM pattern matching and text heuristics
- Find and click accept buttons with fallback strategies
- Validate dialog dismissal before continuing
- Support site-specific custom patterns
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, Callable, Any
from enum import Enum

logger = logging.getLogger(__name__)


class DialogType(str, Enum):
    """Types of consent dialogs recognized."""
    COOKIE_BANNER = "cookie_banner"
    GDPR_MODAL = "gdpr_modal"
    GENERIC_MODAL = "generic_modal"
    UNKNOWN = "unknown"


class ConsentPattern:
    """Pattern matcher for consent dialog detection."""

    def __init__(
        self,
        name: str,
        dialog_selector: str,
        accept_button_selector: str,
        text_heuristics: Optional[list[str]] = None,
    ):
        """Initialize ConsentPattern.
        
        Args:
            name: Pattern name (e.g., "cookie_banner_standard")
            dialog_selector: CSS selector for dialog container
            accept_button_selector: CSS selector for accept button
            text_heuristics: Optional list of keywords to match in dialog text
        """
        self.name = name
        self.dialog_selector = dialog_selector
        self.accept_button_selector = accept_button_selector
        self.text_heuristics = text_heuristics or []

    async def matches(self, page) -> bool:
        """Check if dialog matches this pattern.
        
        Args:
            page: Playwright Page object
            
        Returns:
            True if pattern matches, False otherwise
        """
        try:
            # Check if dialog element exists
            dialog_exists = await page.query_selector(self.dialog_selector) is not None
            if not dialog_exists:
                return False

            # Check text heuristics if provided
            if self.text_heuristics:
                page_text = await page.content()
                text_matches = any(keyword.lower() in page_text.lower() for keyword in self.text_heuristics)
                return text_matches

            return True
        except Exception as e:
            logger.debug(f"Pattern matching error: {e}")
            return False

    async def find_accept_button(self, page) -> Optional[Any]:
        """Find accept button element.
        
        Args:
            page: Playwright Page object
            
        Returns:
            Handle to button element, or None if not found
        """
        try:
            button = await page.query_selector(self.accept_button_selector)
            return button
        except Exception as e:
            logger.debug(f"Button finding error: {e}")
            return None


# Standard consent dialog patterns
STANDARD_PATTERNS = [
    ConsentPattern(
        name="cookie_banner_standard",
        dialog_selector="[role='dialog'], .cookie-banner, .cookie-consent, .consent-banner",
        accept_button_selector="button:has-text('Accept'), button:has-text('Accept All'), button:has-text('I Agree')",
        text_heuristics=["cookie", "consent", "accept"],
    ),
    ConsentPattern(
        name="gdpr_modal_standard",
        dialog_selector="[role='dialog'][aria-label*='consent'], .gdpr-modal, .gdpr-notice",
        accept_button_selector="button:has-text('Accept'), button:has-text('Agree'), [data-testid='accept-button']",
        text_heuristics=["GDPR", "gdpr", "personal data", "consent"],
    ),
    ConsentPattern(
        name="generic_modal_pattern",
        dialog_selector="[role='dialog'], .modal, .popup",
        accept_button_selector="button:has-text('OK'), button:has-text('Agree'), button:has-text('Accept')",
        text_heuristics=["cookie", "consent", "agree"],
    ),
]


class ConsentHandler:
    """
    Detects and accepts consent dialogs on websites.
    
    Supports:
    - Standard GDPR/cookie consent patterns
    - Custom site-specific patterns
    - Text-based dialog detection heuristics
    - Fallback strategies for finding accept buttons
    - Timeout handling with graceful degradation
    """

    def __init__(
        self,
        timeout_seconds: float = 5.0,
        event_builder: Optional[Any] = None,
    ):
        """Initialize ConsentHandler.
        
        Args:
            timeout_seconds: Timeout for dialog detection and acceptance
            event_builder: Optional EventBuilder for audit logging
        """
        self.timeout_seconds = timeout_seconds
        self.event_builder = event_builder
        self.custom_patterns: list[ConsentPattern] = []
        self._logger = logging.getLogger(__name__)

    def register_pattern(self, pattern: ConsentPattern) -> None:
        """Register a custom consent dialog pattern.
        
        Args:
            pattern: ConsentPattern instance
        """
        self.custom_patterns.append(pattern)
        logger.info(f"Registered custom consent pattern: {pattern.name}")

    async def detect_dialog(self, page) -> tuple[bool, Optional[DialogType], Optional[str]]:
        """Detect if a consent dialog is present.
        
        Args:
            page: Playwright Page object
            
        Returns:
            (dialog_found, dialog_type, pattern_name)
        """
        try:
            # Check custom patterns first
            for pattern in self.custom_patterns:
                if await pattern.matches(page):
                    logger.debug(f"Detected consent dialog via custom pattern: {pattern.name}")
                    return (True, DialogType.UNKNOWN, pattern.name)

            # Check standard patterns
            for pattern in STANDARD_PATTERNS:
                if await pattern.matches(page):
                    logger.debug(f"Detected consent dialog via standard pattern: {pattern.name}")
                    dialog_type = self._infer_dialog_type(pattern.name)
                    return (True, dialog_type, pattern.name)

            return (False, None, None)
        except Exception as e:
            logger.warning(f"Error detecting consent dialog: {e}")
            return (False, None, None)

    async def accept_consent(
        self,
        page,
        pattern: Optional[ConsentPattern] = None,
        verify_dismissed: bool = True,
    ) -> bool:
        """Accept consent dialog.
        
        Args:
            page: Playwright Page object
            pattern: Optional ConsentPattern (auto-detect if None)
            verify_dismissed: Whether to verify dialog was dismissed
            
        Returns:
            True if dialog accepted and dismissed, False otherwise
        """
        try:
            # Auto-detect if no pattern provided
            if not pattern:
                dialog_found, _, pattern_name = await self.detect_dialog(page)
                if not dialog_found:
                    logger.debug("No consent dialog detected")
                    return False

                # Reconstruct pattern from name
                pattern = self._get_pattern_by_name(pattern_name)
                if not pattern:
                    logger.warning(f"Could not reconstruct pattern: {pattern_name}")
                    return False

            # Find and click accept button
            button = await pattern.find_accept_button(page)
            if not button:
                logger.warning(f"Could not find accept button for pattern: {pattern.name}")
                return False

            await button.click()
            logger.info(f"Clicked accept button for pattern: {pattern.name}")

            # Verify dialog is dismissed
            if verify_dismissed:
                await asyncio.sleep(0.5)  # Wait for dialog animation
                dialog_still_visible = await page.query_selector(pattern.dialog_selector) is not None
                if dialog_still_visible:
                    logger.warning(f"Consent dialog still visible after accepting")
                    return False

            logger.info(f"Consent dialog accepted and dismissed")
            return True

        except Exception as e:
            logger.error(f"Error accepting consent dialog: {e}")
            return False

    async def detect_and_accept(
        self,
        page,
        timeout_override: Optional[float] = None,
    ) -> bool:
        """Detect and accept consent dialog in one operation.
        
        Args:
            page: Playwright Page object
            timeout_override: Optional timeout override (uses instance default if None)
            
        Returns:
            True if dialog detected and accepted, False otherwise
        """
        timeout = timeout_override or self.timeout_seconds

        try:
            async with asyncio.timeout(timeout):
                dialog_found, dialog_type, pattern_name = await self.detect_dialog(page)
                if not dialog_found:
                    logger.debug("No consent dialog found")
                    return False

                pattern = self._get_pattern_by_name(pattern_name)
                if not pattern:
                    logger.warning(f"Could not find pattern for: {pattern_name}")
                    return False

                success = await self.accept_consent(page, pattern=pattern)
                if success:
                    logger.info(f"Consent dialog handled: {dialog_type}")
                    if self.event_builder:
                        self.event_builder.add_event(
                            event_type="consent_accepted",
                            subsystem="consent_handler",
                            details={"dialog_type": dialog_type, "pattern": pattern.name},
                        )

                return success

        except asyncio.TimeoutError:
            logger.warning(f"Consent dialog detection timeout after {timeout}s")
            return False
        except Exception as e:
            logger.error(f"Error in detect_and_accept: {e}")
            return False

    async def wait_for_dialog_dismiss(
        self,
        page,
        pattern: ConsentPattern,
        max_wait_ms: int = 5000,
    ) -> bool:
        """Wait for dialog to be dismissed from the page.
        
        Args:
            page: Playwright Page object
            pattern: ConsentPattern for the dialog
            max_wait_ms: Maximum time to wait
            
        Returns:
            True if dialog dismissed, False if timeout
        """
        try:
            # Wait for dialog selector to be hidden or removed
            await page.wait_for_selector(
                pattern.dialog_selector,
                state="hidden",
                timeout=max_wait_ms,
            )
            return True
        except Exception:
            # Dialog may have been removed from DOM entirely
            try:
                await asyncio.sleep(0.1)
                still_exists = await page.query_selector(pattern.dialog_selector) is not None
                return not still_exists
            except Exception:
                return False

    # Private helper methods

    def _infer_dialog_type(self, pattern_name: str) -> DialogType:
        """Infer dialog type from pattern name."""
        if "cookie" in pattern_name.lower():
            return DialogType.COOKIE_BANNER
        elif "gdpr" in pattern_name.lower():
            return DialogType.GDPR_MODAL
        else:
            return DialogType.GENERIC_MODAL

    def _get_pattern_by_name(self, pattern_name: str) -> Optional[ConsentPattern]:
        """Get pattern by name from custom or standard patterns."""
        # Check custom patterns first
        for pattern in self.custom_patterns:
            if pattern.name == pattern_name:
                return pattern

        # Check standard patterns
        for pattern in STANDARD_PATTERNS:
            if pattern.name == pattern_name:
                return pattern

        return None

    def get_available_patterns(self) -> list[str]:
        """Get list of all available pattern names."""
        names = [p.name for p in STANDARD_PATTERNS]
        names.extend([p.name for p in self.custom_patterns])
        return names

    async def validate_no_dialog(self, page) -> bool:
        """Verify no consent dialog is present on page.
        
        Useful for verification after acceptance.
        
        Args:
            page: Playwright Page object
            
        Returns:
            True if no dialog present, False if dialog detected
        """
        dialog_found, _, _ = await self.detect_dialog(page)
        return not dialog_found
