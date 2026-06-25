"""
WebKit mobile browser configuration for testing.

This configuration provides a WebKit setup with mobile device emulation
for testing responsive design and mobile-specific features.
"""

from src.browser.config import BrowserConfiguration, BrowserType, StealthConfiguration, ResourceLimits

# WebKit mobile configuration
WEBKIT_MOBILE_CONFIG = BrowserConfiguration(
    browser_type=BrowserType.WEBKIT,
    headless=True,
    stealth=StealthConfiguration(
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        viewport={"width": 390, "height": 844},
        locale="en-US",
        timezone="America/New_York",
        geolocation={"latitude": 37.7749, "longitude": -122.4194},
        permissions=["geolocation"],
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        },
        bypass_csp=True,
        ignore_https_errors=False
    ),
    resource_limits=ResourceLimits(
        max_memory_mb=256,
        max_cpu_percent=60.0,
        max_tab_count=3,
        session_timeout_minutes=10,
        cleanup_threshold_memory=0.6,
        cleanup_threshold_cpu=0.7
    ),
    launch_options={
        "args": [
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor"
        ]
    },
    context_options={
        "ignore_https_errors": False,
        "bypass_csp": True,
        "viewport": {"width": 390, "height": 844},
        "device_scale_factor": 3,
        "is_mobile": True,
        "has_touch": True,
        "geolocation": {"latitude": 37.7749, "longitude": -122.4194},
        "permissions": ["geolocation"]
    }
)
