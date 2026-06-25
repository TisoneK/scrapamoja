"""
Firefox stealth browser configuration for testing.

This configuration provides a Firefox setup with enhanced stealth
features for anti-bot detection avoidance.
"""

from src.browser.config import BrowserConfiguration, BrowserType, StealthConfiguration, ResourceLimits

# Firefox stealth configuration
FIREFOX_STEALTH_CONFIG = BrowserConfiguration(
    browser_type=BrowserType.FIREFOX,
    headless=True,
    stealth=StealthConfiguration(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        viewport={"width": 1366, "height": 768},
        locale="en-US",
        timezone="America/New_York",
        geolocation={"latitude": 40.7128, "longitude": -74.0060},
        permissions=["geolocation", "notifications"],
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "DNT": "1",
            "Sec-GPC": "1"
        },
        bypass_csp=True,
        ignore_https_errors=False
    ),
    resource_limits=ResourceLimits(
        max_memory_mb=768,
        max_cpu_percent=75.0,
        max_tab_count=8,
        session_timeout_minutes=20,
        cleanup_threshold_memory=0.75,
        cleanup_threshold_cpu=0.85
    ),
    launch_options={
        "firefox_user_prefs": {
            "privacy.trackingprotection.enabled": True,
            "privacy.trackingprotection.socialtracking.enabled": True,
            "privacy.donottrackheader.enabled": True,
            "geo.enabled": True,
            "geo.provider.use_geoclue": False,
            "browser.cache.disk.enable": False,
            "browser.cache.memory.enable": True,
            "browser.cache.disk.capacity": 0,
            "media.peerconnection.enabled": False,
            "dom.webdriver.enabled": False,
            "useAutomationExtension": False
        }
    },
    context_options={
        "ignore_https_errors": False,
        "bypass_csp": True,
        "geolocation": {"latitude": 40.7128, "longitude": -74.0060},
        "permissions": ["geolocation", "notifications"]
    }
)
