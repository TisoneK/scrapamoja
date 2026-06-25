"""
Chromium headless browser configuration for testing.

This configuration provides a standard Chromium setup for automated
testing with basic stealth settings and conservative resource limits.
"""

from src.browser.config import BrowserConfiguration, BrowserType, StealthConfiguration, ResourceLimits

# Standard Chromium headless configuration
CHROMIUM_HEADLESS_CONFIG = BrowserConfiguration(
    browser_type=BrowserType.CHROMIUM,
    headless=True,
    stealth=StealthConfiguration(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone="America/New_York",
        permissions=["geolocation"],
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        },
        bypass_csp=True,
        ignore_https_errors=False
    ),
    resource_limits=ResourceLimits(
        max_memory_mb=512,
        max_cpu_percent=70.0,
        max_tab_count=5,
        session_timeout_minutes=15,
        cleanup_threshold_memory=0.7,
        cleanup_threshold_cpu=0.8
    ),
    launch_options={
        "args": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
            "--disable-ipc-flooding-protection"
        ]
    },
    context_options={
        "ignore_https_errors": False,
        "bypass_csp": True
    }
)
