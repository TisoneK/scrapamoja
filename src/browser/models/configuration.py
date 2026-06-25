"""
Browser Configuration Entities

Defines configuration models for browser initialization and management.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class BrowserType(Enum):
    """Supported browser types."""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class ProxyType(Enum):
    """Supported proxy types."""
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"
    SOCKS4 = "socks4"


@dataclass
class ProxySettings:
    """Proxy configuration for browser."""
    
    enabled: bool = False
    proxy_type: ProxyType = ProxyType.HTTP
    host: str = ""
    port: int = 8080
    username: Optional[str] = None
    password: Optional[str] = None
    bypass_list: List[str] = field(default_factory=list)  # Domains to bypass proxy
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        if not self.enabled:
            return {}
        
        proxy_url = f"{self.proxy_type.value}://{self.host}:{self.port}"
        config = {"server": proxy_url}
        
        if self.username and self.password:
            config["username"] = self.username
            config["password"] = self.password
        
        if self.bypass_list:
            config["bypass"] = ",".join(self.bypass_list)
        
        return config
    
    def validate(self) -> List[str]:
        """Validate proxy settings."""
        issues = []
        
        if self.enabled:
            if not self.host:
                issues.append("Proxy host is required when enabled")
            if self.port <= 0 or self.port > 65535:
                issues.append(f"Invalid proxy port: {self.port}")
            if self.username and not self.password:
                issues.append("Password required when username is provided")
        
        return issues


@dataclass
class StealthSettings:
    """Stealth/anti-detection configuration."""
    
    enabled: bool = True
    hide_webdriver: bool = True
    hide_chrome_flag: bool = True
    emulate_human_behavior: bool = True
    randomize_fingerprint: bool = True
    disable_headless_mode: bool = False
    disable_blink_features: bool = True
    user_agent_override: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    geolocation_override: Optional[Dict[str, float]] = None  # {"latitude": x, "longitude": y}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "hide_webdriver": self.hide_webdriver,
            "hide_chrome_flag": self.hide_chrome_flag,
            "emulate_human_behavior": self.emulate_human_behavior,
            "randomize_fingerprint": self.randomize_fingerprint,
            "disable_headless_mode": self.disable_headless_mode,
            "disable_blink_features": self.disable_blink_features,
            "user_agent_override": self.user_agent_override,
            "language": self.language,
            "timezone": self.timezone,
            "geolocation_override": self.geolocation_override,
        }
    
    def validate(self) -> List[str]:
        """Validate stealth settings."""
        issues = []
        
        if self.geolocation_override:
            if "latitude" not in self.geolocation_override or "longitude" not in self.geolocation_override:
                issues.append("Geolocation must include latitude and longitude")
            lat = self.geolocation_override.get("latitude", 0)
            lon = self.geolocation_override.get("longitude", 0)
            if not (-90 <= lat <= 90):
                issues.append(f"Invalid latitude: {lat}")
            if not (-180 <= lon <= 180):
                issues.append(f"Invalid longitude: {lon}")
        
        return issues


@dataclass
class BrowserConfiguration:
    """Complete browser configuration."""
    
    # Browser type
    browser_type: BrowserType = BrowserType.CHROMIUM
    
    # Display settings
    headless: bool = True
    width: int = 1920
    height: int = 1080
    device_scale_factor: float = 1.0
    is_mobile: bool = False
    has_touch: bool = False
    
    # Timeout settings (in seconds)
    page_load_timeout: float = 30.0
    navigation_timeout: float = 30.0
    wait_for_navigation_timeout: float = 10.0
    
    # Resource limits
    max_concurrent_connections: int = 50
    max_memory_mb: Optional[int] = None
    
    # Proxy configuration
    proxy: ProxySettings = field(default_factory=ProxySettings)
    
    # Stealth configuration
    stealth: StealthSettings = field(default_factory=StealthSettings)
    
    # Additional launch options
    ignore_https_errors: bool = False
    offline_mode: bool = False
    slow_mo_ms: int = 0  # Milliseconds to slow down all operations
    accept_downloads: bool = True
    
    # Additional headers
    extra_http_headers: Dict[str, str] = field(default_factory=dict)
    
    # Chromium-specific options
    chromium_args: List[str] = field(default_factory=list)
    
    def validate(self) -> List[str]:
        """Validate configuration."""
        issues = []
        
        # Validate display settings
        if self.width <= 0:
            issues.append(f"Invalid width: {self.width}")
        if self.height <= 0:
            issues.append(f"Invalid height: {self.height}")
        if self.device_scale_factor <= 0:
            issues.append(f"Invalid device scale factor: {self.device_scale_factor}")
        
        # Validate timeouts
        if self.page_load_timeout < 0:
            issues.append(f"Invalid page load timeout: {self.page_load_timeout}")
        if self.navigation_timeout < 0:
            issues.append(f"Invalid navigation timeout: {self.navigation_timeout}")
        if self.wait_for_navigation_timeout < 0:
            issues.append(f"Invalid wait for navigation timeout: {self.wait_for_navigation_timeout}")
        
        # Validate resource limits
        if self.max_concurrent_connections <= 0:
            issues.append(f"Invalid max concurrent connections: {self.max_concurrent_connections}")
        if self.max_memory_mb is not None and self.max_memory_mb <= 0:
            issues.append(f"Invalid max memory: {self.max_memory_mb}")
        
        # Validate slow_mo
        if self.slow_mo_ms < 0:
            issues.append(f"Invalid slow_mo_ms: {self.slow_mo_ms}")
        
        # Validate proxy settings
        proxy_issues = self.proxy.validate()
        issues.extend(proxy_issues)
        
        # Validate stealth settings
        stealth_issues = self.stealth.validate()
        issues.extend(stealth_issues)
        
        return issues
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "browser_type": self.browser_type.value,
            "headless": self.headless,
            "width": self.width,
            "height": self.height,
            "device_scale_factor": self.device_scale_factor,
            "is_mobile": self.is_mobile,
            "has_touch": self.has_touch,
            "page_load_timeout": self.page_load_timeout,
            "navigation_timeout": self.navigation_timeout,
            "wait_for_navigation_timeout": self.wait_for_navigation_timeout,
            "max_concurrent_connections": self.max_concurrent_connections,
            "max_memory_mb": self.max_memory_mb,
            "proxy": self.proxy.to_dict(),
            "stealth": self.stealth.to_dict(),
            "ignore_https_errors": self.ignore_https_errors,
            "offline_mode": self.offline_mode,
            "slow_mo_ms": self.slow_mo_ms,
            "accept_downloads": self.accept_downloads,
            "extra_http_headers": self.extra_http_headers.copy(),
            "chromium_args": self.chromium_args.copy(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BrowserConfiguration":
        """Create from dictionary."""
        # Parse browser type
        browser_type = BrowserType(data.get("browser_type", "chromium"))
        
        # Parse proxy settings
        proxy_data = data.get("proxy", {})
        proxy_type = ProxyType(proxy_data.get("proxy_type", "http")) if "proxy_type" in proxy_data else ProxyType.HTTP
        proxy = ProxySettings(
            enabled=proxy_data.get("enabled", False),
            proxy_type=proxy_type,
            host=proxy_data.get("host", ""),
            port=proxy_data.get("port", 8080),
            username=proxy_data.get("username"),
            password=proxy_data.get("password"),
            bypass_list=proxy_data.get("bypass_list", []),
        )
        
        # Parse stealth settings
        stealth_data = data.get("stealth", {})
        stealth = StealthSettings(
            enabled=stealth_data.get("enabled", True),
            hide_webdriver=stealth_data.get("hide_webdriver", True),
            hide_chrome_flag=stealth_data.get("hide_chrome_flag", True),
            emulate_human_behavior=stealth_data.get("emulate_human_behavior", True),
            randomize_fingerprint=stealth_data.get("randomize_fingerprint", True),
            disable_headless_mode=stealth_data.get("disable_headless_mode", False),
            disable_blink_features=stealth_data.get("disable_blink_features", True),
            user_agent_override=stealth_data.get("user_agent_override"),
            language=stealth_data.get("language"),
            timezone=stealth_data.get("timezone"),
            geolocation_override=stealth_data.get("geolocation_override"),
        )
        
        return cls(
            browser_type=browser_type,
            headless=data.get("headless", True),
            width=data.get("width", 1920),
            height=data.get("height", 1080),
            device_scale_factor=data.get("device_scale_factor", 1.0),
            is_mobile=data.get("is_mobile", False),
            has_touch=data.get("has_touch", False),
            page_load_timeout=data.get("page_load_timeout", 30.0),
            navigation_timeout=data.get("navigation_timeout", 30.0),
            wait_for_navigation_timeout=data.get("wait_for_navigation_timeout", 10.0),
            max_concurrent_connections=data.get("max_concurrent_connections", 50),
            max_memory_mb=data.get("max_memory_mb"),
            proxy=proxy,
            stealth=stealth,
            ignore_https_errors=data.get("ignore_https_errors", False),
            offline_mode=data.get("offline_mode", False),
            slow_mo_ms=data.get("slow_mo_ms", 0),
            accept_downloads=data.get("accept_downloads", True),
            extra_http_headers=data.get("extra_http_headers", {}),
            chromium_args=data.get("chromium_args", []),
        )
    
    def get_defaults_for_browser(self) -> "BrowserConfiguration":
        """Get sensible defaults for the selected browser type."""
        if self.browser_type == BrowserType.FIREFOX:
            self.chromium_args = []  # Firefox doesn't use chromium args
        elif self.browser_type == BrowserType.WEBKIT:
            self.chromium_args = []  # WebKit doesn't use chromium args
        
        return self
