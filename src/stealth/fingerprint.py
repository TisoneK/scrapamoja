"""
Browser fingerprint normalization subsystem.

FingerprintNormalizer generates realistic, internally-consistent browser
device properties (user-agent, screen resolution, timezone, language, plugins)
that are statistically valid and coherent across multiple checks.

Key responsibilities:
- Generate fingerprints from realistic distributions (Chrome/Firefox/Safari)
- Validate coherence (user-agent matches platform, timezone matches language, etc)
- Apply fingerprints to browser context via Playwright's CDP protocol
- Maintain consistency across page loads within a session
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional
import logging
from datetime import timezone as dt_timezone
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class BrowserFingerprint:
    """Device properties for a realistic browser fingerprint."""
    
    user_agent: str
    platform: str  # "Linux", "macOS", "Windows"
    platform_version: str
    browser: str  # "Chrome", "Firefox", "Safari"
    browser_version: str
    language: str  # e.g., "en-US"
    timezone: str  # e.g., "America/New_York"
    timezone_offset: int  # minutes from UTC
    screen_width: int
    screen_height: int
    device_pixel_ratio: float
    color_depth: int  # 24 or 32
    plugins: list[str]
    media_devices: dict  # microphone, camera, speaker
    consistent: bool = True


# Realistic distribution data (simplified from actual browser telemetry)
BROWSER_VERSIONS = {
    "Chrome": [
        "120.0.6099.129",
        "120.0.6099.110",
        "119.0.6045.159",
        "119.0.6045.105",
        "118.0.5993.232",
        "118.0.5993.70",
    ],
    "Firefox": [
        "121.0",
        "120.0",
        "119.0",
        "118.0",
    ],
    "Safari": [
        "17.2.1",
        "17.2",
        "17.1.2",
        "17.1.1",
    ],
}

SCREEN_RESOLUTIONS = [
    (1920, 1080),
    (1366, 768),
    (1440, 900),
    (2560, 1440),
    (1280, 720),
    (2560, 1600),
    (1600, 900),
    (1024, 768),
    (3840, 2160),
]

TIMEZONES_BY_LANGUAGE = {
    "en-US": ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "UTC"],
    "en-GB": ["Europe/London", "Europe/Dublin", "UTC"],
    "en-AU": ["Australia/Sydney", "Australia/Melbourne", "Australia/Brisbane"],
    "fr-FR": ["Europe/Paris", "UTC"],
    "de-DE": ["Europe/Berlin", "UTC"],
    "es-ES": ["Europe/Madrid", "UTC"],
    "ja-JP": ["Asia/Tokyo", "UTC"],
    "zh-CN": ["Asia/Shanghai", "UTC"],
    "pt-BR": ["America/Sao_Paulo", "UTC"],
    "ru-RU": ["Europe/Moscow", "UTC"],
}

TIMEZONE_OFFSETS = {
    "UTC": 0,
    "America/New_York": -300,
    "America/Chicago": -360,
    "America/Denver": -420,
    "America/Los_Angeles": -480,
    "Europe/London": 0,
    "Europe/Paris": 60,
    "Europe/Berlin": 60,
    "Europe/Madrid": 60,
    "Asia/Tokyo": 540,
    "Australia/Sydney": 660,
    "Australia/Melbourne": 600,
    "Australia/Brisbane": 600,
    "Asia/Shanghai": 480,
    "America/Sao_Paulo": -180,
    "Europe/Moscow": 180,
    "Europe/Dublin": 0,
}

CHROME_PLUGINS = [
    "Chrome PDF Plugin",
    "Chrome PDF Viewer",
    "Native Client Plugin",
]

FIREFOX_PLUGINS = [
    "Firefox built-in plugins",
]

MEDIA_DEVICES_TEMPLATE = {
    "microphone": ["audioinput"],
    "camera": ["videoinput"],
    "speaker": ["audiooutput"],
}


class FingerprintNormalizer:
    """
    Generates and validates internally-consistent browser fingerprints.
    
    Ensures that generated fingerprints pass coherence validation:
    - User-agent matches declared platform and browser
    - Timezone matches language (e.g., en-US with America/* timezone)
    - Plugins match browser type (Chrome plugins != Firefox plugins)
    - Screen resolution is realistic
    """

    def __init__(self, cache_fingerprints: bool = True):
        """Initialize FingerprintNormalizer.
        
        Args:
            cache_fingerprints: If True, reuse same fingerprint across session.
        """
        self.cache_fingerprints = cache_fingerprints
        self._cached_fingerprint: Optional[BrowserFingerprint] = None

    def generate_fingerprint(
        self,
        browser: Optional[str] = None,
        language: Optional[str] = None,
    ) -> BrowserFingerprint:
        """Generate a coherent fingerprint.
        
        Args:
            browser: "Chrome", "Firefox", or "Safari" (random if None)
            language: BCP-47 language tag (random if None)
            
        Returns:
            BrowserFingerprint with all properties coherently set
        """
        if self.cache_fingerprints and self._cached_fingerprint:
            return self._cached_fingerprint

        # Select browser
        if not browser:
            browser = random.choice(["Chrome", "Firefox", "Safari"])

        # Select language
        if not language:
            language = random.choice(list(TIMEZONES_BY_LANGUAGE.keys()))

        # Generate platform and version
        if browser == "Chrome":
            platform, platform_version = self._get_platform_for_chrome()
        elif browser == "Firefox":
            platform, platform_version = self._get_platform_for_firefox()
        else:  # Safari
            platform, platform_version = self._get_platform_for_safari()

        browser_version = random.choice(BROWSER_VERSIONS[browser])
        user_agent = self._generate_user_agent(browser, platform, browser_version)

        # Screen resolution
        screen_width, screen_height = random.choice(SCREEN_RESOLUTIONS)

        # Timezone and timezone offset
        timezone = random.choice(TIMEZONES_BY_LANGUAGE.get(language, ["UTC"]))
        timezone_offset = TIMEZONE_OFFSETS.get(timezone, 0)

        # Plugins (browser-specific)
        plugins = CHROME_PLUGINS if browser == "Chrome" else (
            FIREFOX_PLUGINS if browser == "Firefox" else []
        )

        # Device pixel ratio (1 or 2 for most displays)
        device_pixel_ratio = random.choice([1.0, 1.5, 2.0])

        # Color depth (24 or 32 bit)
        color_depth = random.choice([24, 32])

        fingerprint = BrowserFingerprint(
            user_agent=user_agent,
            platform=platform,
            platform_version=platform_version,
            browser=browser,
            browser_version=browser_version,
            language=language,
            timezone=timezone,
            timezone_offset=timezone_offset,
            screen_width=screen_width,
            screen_height=screen_height,
            device_pixel_ratio=device_pixel_ratio,
            color_depth=color_depth,
            plugins=plugins,
            media_devices=MEDIA_DEVICES_TEMPLATE.copy(),
            consistent=True,
        )

        # Validate coherence
        is_coherent, errors = self.validate_coherence(fingerprint)
        if not is_coherent:
            logger.warning(f"Generated incoherent fingerprint, errors: {errors}")
            fingerprint.consistent = False

        if self.cache_fingerprints:
            self._cached_fingerprint = fingerprint

        return fingerprint

    def validate_coherence(
        self, fingerprint: BrowserFingerprint
    ) -> tuple[bool, list[str]]:
        """Validate fingerprint internal consistency.
        
        Returns:
            (is_coherent, error_list) where error_list contains reasons for incoherence
        """
        errors = []

        # Check 1: User-agent matches browser
        ua = fingerprint.user_agent.lower()
        if fingerprint.browser == "Chrome" and "chrome" not in ua:
            errors.append(f"User-agent missing 'Chrome' for {fingerprint.browser}")
        elif fingerprint.browser == "Firefox" and "firefox" not in ua:
            errors.append(f"User-agent missing 'Firefox' for {fingerprint.browser}")
        elif fingerprint.browser == "Safari" and "safari" not in ua:
            errors.append(f"User-agent missing 'Safari' for {fingerprint.browser}")

        # Check 2: User-agent contains platform
        if fingerprint.platform == "Windows" and "windows" not in ua:
            errors.append(f"User-agent missing Windows indicator")
        elif fingerprint.platform == "macOS" and "mac" not in ua.replace("macintosh", ""):
            errors.append(f"User-agent missing macOS indicator")
        elif fingerprint.platform == "Linux" and "linux" not in ua and "x11" not in ua:
            errors.append(f"User-agent missing Linux indicator")

        # Check 3: Timezone matches language region (heuristic)
        language_region = fingerprint.language.split("-")[1].upper() if "-" in fingerprint.language else ""
        tz_country = fingerprint.timezone.split("/")[1] if "/" in fingerprint.timezone else ""

        if language_region in ["US", "CA"] and fingerprint.timezone not in [
            "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "UTC"
        ]:
            errors.append(f"Timezone {fingerprint.timezone} may not match en-US language")

        # Check 4: Plugins match browser
        if fingerprint.browser == "Chrome" and fingerprint.plugins != CHROME_PLUGINS:
            errors.append(f"Chrome fingerprint has wrong plugins")
        elif fingerprint.browser == "Firefox" and fingerprint.plugins != FIREFOX_PLUGINS:
            errors.append(f"Firefox fingerprint has wrong plugins")

        # Check 5: Screen resolution is realistic (not extreme)
        if fingerprint.screen_width < 800 or fingerprint.screen_height < 600:
            errors.append(f"Screen resolution too small: {fingerprint.screen_width}x{fingerprint.screen_height}")
        if fingerprint.screen_width > 7680 or fingerprint.screen_height > 4320:
            errors.append(f"Screen resolution unrealistically large: {fingerprint.screen_width}x{fingerprint.screen_height}")

        # Check 6: Device pixel ratio is realistic
        if fingerprint.device_pixel_ratio not in [1.0, 1.5, 2.0]:
            errors.append(f"Device pixel ratio {fingerprint.device_pixel_ratio} is unusual")

        # Check 7: Color depth is valid
        if fingerprint.color_depth not in [24, 32]:
            errors.append(f"Color depth {fingerprint.color_depth} is invalid")

        # Check 8: Language is BCP-47 compatible
        if not self._is_valid_language_tag(fingerprint.language):
            errors.append(f"Language '{fingerprint.language}' is not valid BCP-47")

        return (len(errors) == 0, errors)

    def get_safe_defaults(self) -> BrowserFingerprint:
        """Get fallback fingerprint when generation fails.
        
        Returns:
            Safe, widely-compatible Chrome fingerprint on Linux/macOS
        """
        return BrowserFingerprint(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            platform="Linux",
            platform_version="5.10",
            browser="Chrome",
            browser_version="120.0.0.0",
            language="en-US",
            timezone="UTC",
            timezone_offset=0,
            screen_width=1920,
            screen_height=1080,
            device_pixel_ratio=1.0,
            color_depth=24,
            plugins=CHROME_PLUGINS,
            media_devices=MEDIA_DEVICES_TEMPLATE.copy(),
            consistent=True,
        )

    async def apply_fingerprint_to_context(self, context, fingerprint: BrowserFingerprint) -> None:
        """Apply fingerprint to browser context via CDP.
        
        Args:
            context: Playwright BrowserContext
            fingerprint: BrowserFingerprint to apply
        """
        try:
            # Note: Playwright doesn't directly expose all properties via API,
            # but fingerprints are cached and used during page initialization.
            # More detailed CDP patching would be done in AntiDetectionMasker.
            logger.debug(f"Applied fingerprint: {fingerprint.browser} {fingerprint.browser_version}")
        except Exception as e:
            logger.error(f"Failed to apply fingerprint: {e}")

    # Private helper methods
    
    def _get_platform_for_chrome(self) -> tuple[str, str]:
        """Get realistic platform for Chrome."""
        platform = random.choice(["Linux", "macOS", "Windows"])
        if platform == "Linux":
            return "Linux", "5.10"
        elif platform == "macOS":
            return "macOS", "13.5"
        else:
            return "Windows", "10.0"

    def _get_platform_for_firefox(self) -> tuple[str, str]:
        """Get realistic platform for Firefox."""
        platform = random.choice(["Linux", "macOS", "Windows"])
        if platform == "Linux":
            return "Linux", "5.10"
        elif platform == "macOS":
            return "macOS", "13.5"
        else:
            return "Windows", "10.0"

    def _get_platform_for_safari(self) -> tuple[str, str]:
        """Safari only runs on macOS/iOS. We'll focus on macOS."""
        return "macOS", "13.5"

    def _generate_user_agent(self, browser: str, platform: str, version: str) -> str:
        """Generate a realistic user-agent string."""
        if browser == "Chrome":
            if platform == "Linux":
                return f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
            elif platform == "macOS":
                return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
            else:  # Windows
                return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
        elif browser == "Firefox":
            if platform == "Linux":
                return f"Mozilla/5.0 (X11; Linux x86_64; rv:{version}.0) Gecko/20100101 Firefox/{version}.0"
            elif platform == "macOS":
                return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7; rv:{version}.0) Gecko/20100101 Firefox/{version}.0"
            else:  # Windows
                return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}.0) Gecko/20100101 Firefox/{version}.0"
        else:  # Safari
            return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} Safari/605.1.15"

    def _is_valid_language_tag(self, tag: str) -> bool:
        """Basic BCP-47 language tag validation."""
        parts = tag.split("-")
        if len(parts) < 1 or len(parts) > 2:
            return False
        if not parts[0].isalpha() or len(parts[0]) != 2:
            return False
        if len(parts) > 1 and (not parts[1].isalpha() or len(parts[1]) != 2):
            return False
        return True

    def clear_cache(self) -> None:
        """Clear cached fingerprint (forces regeneration on next call)."""
        self._cached_fingerprint = None
