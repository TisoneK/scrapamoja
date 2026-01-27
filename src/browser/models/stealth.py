"""
Stealth Settings Entity

This module defines the StealthSettings entity for browser stealth configuration.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import structlog


class StealthLevel(Enum):
    """Stealth configuration levels."""
    MINIMAL = "minimal"
    STANDARD = "standard"
    HIGH = "high"
    MAXIMUM = "maximum"


class FingerprintType(Enum):
    """Types of browser fingerprinting to normalize."""
    USER_AGENT = "user_agent"
    SCREEN_RESOLUTION = "screen_resolution"
    TIMEZONE = "timezone"
    LANGUAGE = "language"
    PLATFORM = "platform"
    WEBGL = "webgl"
    CANVAS = "canvas"
    AUDIO_CONTEXT = "audio_context"
    WEBGL_VENDOR = "webgl_vendor"
    WEBGL_RENDERER = "webgl_renderer"
    PLUGINS = "plugins"
    FONTS = "fonts"
    CONNECTION_TYPE = "connection_type"


@dataclass
class StealthSettings:
    """Browser stealth configuration for anti-bot detection."""
    
    # Basic stealth settings
    stealth_level: StealthLevel = StealthLevel.STANDARD
    fingerprint_randomization: bool = True
    user_agent_rotation: bool = True
    viewport_randomization: bool = True
    
    # Behavior simulation
    mouse_movement_simulation: bool = True
    typing_simulation: bool = True
    scroll_simulation: bool = True
    click_delay_simulation: bool = True
    navigation_delay_simulation: bool = True
    
    # Timing randomization
    timing_randomization: bool = True
    min_delay_ms: float = 100.0
    max_delay_ms: float = 1000.0
    delay_variation_factor: float = 0.3
    
    # Fingerprint normalization
    normalize_user_agent: bool = True
    normalize_screen_resolution: bool = True
    normalize_timezone: bool = True
    normalize_language: bool = True
    normalize_platform: bool = True
    
    # Advanced stealth features
    canvas_fingerprint_protection: bool = True
    webgl_fingerprint_protection: bool = True
    audio_context_protection: bool = True
    webrtc_protection: bool = True
    font_fingerprint_protection: bool = True
    plugin_simulation: bool = True
    
    # Network stealth
    header_normalization: bool = True
    connection_type_normalization: bool = True
    accept_language_normalization: bool = True
    accept_encoding_normalization: bool = True
    
    # Behavioral patterns
    human_like_scrolling: bool = True
    random_mouse_movements: bool = True
    natural_typing_rhythm: bool = True
    page_interaction_simulation: bool = True
    
    # Configuration
    enabled_fingerprints: List[FingerprintType] = field(default_factory=lambda: list(FingerprintType))
    custom_user_agents: List[str] = field(default_factory=list)
    proxy_rotation: bool = False
    residential_ip_required: bool = False
    
    def __post_init__(self):
        """Initialize stealth settings."""
        self.logger = structlog.get_logger("browser.stealth")
        
        # Set default enabled fingerprints based on stealth level
        if not self.enabled_fingerprints:
            self.enabled_fingerprints = self._get_default_fingerprints()
            
    def _get_default_fingerprints(self) -> List[FingerprintType]:
        """Get default fingerprints based on stealth level."""
        if self.stealth_level == StealthLevel.MINIMAL:
            return [
                FingerprintType.USER_AGENT,
                FingerprintType.SCREEN_RESOLUTION
            ]
        elif self.stealth_level == StealthLevel.STANDARD:
            return [
                FingerprintType.USER_AGENT,
                FingerprintType.SCREEN_RESOLUTION,
                FingerprintType.TIMEZONE,
                FingerprintType.LANGUAGE,
                FingerprintType.PLATFORM
            ]
        elif self.stealth_level == StealthLevel.HIGH:
            return [
                FingerprintType.USER_AGENT,
                FingerprintType.SCREEN_RESOLUTION,
                FingerprintType.TIMEZONE,
                FingerprintType.LANGUAGE,
                FingerprintType.PLATFORM,
                FingerprintType.WEBGL,
                FingerprintType.CANVAS,
                FingerprintType.AUDIO_CONTEXT
            ]
        elif self.stealth_level == StealthLevel.MAXIMUM:
            return list(FingerprintType)
        else:
            return []
            
    def get_random_delay(self, base_delay: Optional[float] = None) -> float:
        """Get randomized delay within configured range."""
        if base_delay is None:
            base_delay = (self.min_delay_ms + self.max_delay_ms) / 2
            
        variation = base_delay * self.delay_variation_factor
        import random
        
        delay = base_delay + random.uniform(-variation, variation)
        return max(self.min_delay_ms, min(self.max_delay_ms, delay))
        
    def should_randomize_fingerprint(self, fingerprint_type: FingerprintType) -> bool:
        """Check if a fingerprint type should be randomized."""
        return (self.fingerprint_randomization and 
                fingerprint_type in self.enabled_fingerprints)
        
    def get_stealth_launch_args(self) -> List[str]:
        """Get stealth launch arguments for browser."""
        args = []
        
        if self.stealth_level in [StealthLevel.HIGH, StealthLevel.MAXIMUM]:
            args.extend([
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--disable-gpu",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding"
            ])
            
        if self.canvas_fingerprint_protection:
            args.extend([
                "--disable-2d-canvas-tiling",
                "--disable-accelerated-2d-canvas"
            ])
            
        if self.webgl_fingerprint_protection:
            args.extend([
                "--disable-webgl",
                "--disable-3d-apis"
            ])
            
        return args
        
    def get_user_agent_options(self) -> Dict[str, Any]:
        """Get user agent configuration options."""
        options = {}
        
        if self.normalize_user_agent:
            options["user_agent"] = self._get_randomized_user_agent()
            
        return options
        
    def _get_randomized_user_agent(self) -> str:
        """Get a randomized user agent."""
        if self.custom_user_agents:
            import random
            return random.choice(self.custom_user_agents)
            
        # Default user agents based on stealth level
        if self.stealth_level == StealthLevel.MINIMAL:
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        elif self.stealth_level == StealthLevel.STANDARD:
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        elif self.stealth_level == StealthLevel.HIGH:
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        else:  # MAXIMUM
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0"
            
    def get_viewport_options(self) -> Dict[str, Any]:
        """Get viewport configuration options."""
        options = {}
        
        if self.viewport_randomization:
            import random
            
            # Common viewport sizes
            viewports = [
                {"width": 1920, "height": 1080},
                {"width": 1366, "height": 768},
                {"width": 1440, "height": 900},
                {"width": 1536, "height": 864},
                {"width": 1280, "height": 720},
                {"width": 1600, "height": 900}
            ]
            
            viewport = random.choice(viewports)
            options["viewport"] = viewport
            
        return options
        
    def get_timezone_options(self) -> Dict[str, Any]:
        """Get timezone configuration options."""
        options = {}
        
        if self.normalize_timezone:
            import random
            
            # Common timezones
            timezones = [
                "America/New_York",
                "America/Los_Angeles",
                "America/Chicago",
                "Europe/London",
                "Europe/Paris",
                "Europe/Berlin",
                "Asia/Tokyo",
                "Asia/Shanghai",
                "Australia/Sydney",
                "UTC"
            ]
            
            options["timezone_id"] = random.choice(timezones)
            
        return options
        
    def get_locale_options(self) -> Dict[str, Any]:
        """Get locale configuration options."""
        options = {}
        
        if self.normalize_language:
            import random
            
            # Common locales
            locales = [
                "en-US",
                "en-GB",
                "en-CA",
                "es-ES",
                "fr-FR",
                "de-DE",
                "it-IT",
                "pt-BR",
                "ja-JP",
                "zh-CN",
                "ko-KR"
            ]
            
            options["locale"] = random.choice(locales)
            
        return options
        
    def get_extra_http_headers(self) -> Dict[str, str]:
        """Get extra HTTP headers for stealth."""
        headers = {}
        
        if self.header_normalization:
            headers.update({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            })
            
        return headers
        
    def simulate_mouse_movement(self, target_selector: str) -> Dict[str, Any]:
        """Get mouse movement simulation configuration."""
        if not self.mouse_movement_simulation:
            return {"enabled": False}
            
        import random
        
        return {
            "enabled": True,
            "target_selector": target_selector,
            "movement_type": random.choice(["bezier", "linear", "random"]),
            "duration_ms": random.uniform(100, 500),
            "delay_before_ms": self.get_random_delay(50),
            "delay_after_ms": self.get_random_delay(100)
        }
        
    def simulate_typing(self, selector: str, text: str) -> Dict[str, Any]:
        """Get typing simulation configuration."""
        if not self.typing_simulation:
            return {"enabled": False}
            
        return {
            "enabled": True,
            "selector": selector,
            "text": text,
            "min_char_delay_ms": 50,
            "max_char_delay_ms": 200,
            "variation_factor": 0.3,
            "mistake_probability": 0.05 if self.stealth_level == StealthLevel.MAXIMUM else 0.01
        }
        
    def simulate_scroll(self, direction: str = "down") -> Dict[str, Any]:
        """Get scroll simulation configuration."""
        if not self.scroll_simulation:
            return {"enabled": False}
            
        return {
            "enabled": True,
            "direction": direction,
            "scroll_distance": random.randint(100, 500),
            "scroll_duration_ms": random.uniform(200, 800),
            "delay_before_ms": self.get_random_delay(100),
            "human_like": self.human_like_scrolling
        }
        
    @property
    def human_like_scrolling(self) -> bool:
        """Check if human-like scrolling should be simulated."""
        return self.human_like_scrolling
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "stealth_level": self.stealth_level.value,
            "fingerprint_randomization": self.fingerprint_randomization,
            "user_agent_rotation": self.user_agent_rotation,
            "viewport_randomization": self.viewport_randomization,
            "mouse_movement_simulation": self.mouse_movement_simulation,
            "typing_simulation": self.typing_simulation,
            "scroll_simulation": self.scroll_simulation,
            "click_delay_simulation": self.click_delay_simulation,
            "navigation_delay_simulation": self.navigation_delay_simulation,
            "timing_randomization": self.timing_randomization,
            "min_delay_ms": self.min_delay_ms,
            "max_delay_ms": self.max_delay_ms,
            "delay_variation_factor": self.delay_variation_factor,
            "normalize_user_agent": self.normalize_user_agent,
            "normalize_screen_resolution": self.normalize_screen_resolution,
            "normalize_timezone": self.normalize_timezone,
            "normalize_language": self.normalize_language,
            "normalize_platform": self.normalize_platform,
            "canvas_fingerprint_protection": self.canvas_fingerprint_protection,
            "webgl_fingerprint_protection": self.webgl_fingerprint_protection,
            "audio_context_protection": self.audio_context_protection,
            "webrtc_protection": self.webrtc_protection,
            "font_fingerprint_protection": self.font_fingerprint_protection,
            "plugin_simulation": self.plugin_simulation,
            "header_normalization": self.header_normalization,
            "connection_type_normalization": self.connection_type_normalization,
            "accept_language_normalization": self.accept_language_normalization,
            "accept_encoding_normalization": self.accept_encoding_normalization,
            "human_like_scrolling": self.human_like_scrolling,
            "random_mouse_movements": self.random_mouse_movements,
            "natural_typing_rhythm": self.natural_typing_rhythm,
            "page_interaction_simulation": self.page_interaction_simulation,
            "enabled_fingerprints": [fp.value for fp in self.enabled_fingerprints],
            "custom_user_agents": self.custom_user_agents,
            "proxy_rotation": self.proxy_rotation,
            "residential_ip_required": self.residential_ip_required
        }
        
    def to_json(self) -> str:
        """Convert to JSON string."""
        import json
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StealthSettings":
        """Create StealthSettings from dictionary."""
        # Handle stealth level conversion
        stealth_level = data.get("stealth_level", "standard")
        if isinstance(stealth_level, str):
            stealth_level = StealthLevel(stealth_level)
            
        # Handle fingerprint types
        enabled_fingerprints = []
        for fp in data.get("enabled_fingerprints", []):
            if isinstance(fp, str):
                try:
                    enabled_fingerprints.append(FingerprintType(fp))
                except ValueError:
                    pass  # Skip invalid fingerprint types
                    
        return cls(
            stealth_level=stealth_level,
            fingerprint_randomization=data.get("fingerprint_randomization", True),
            user_agent_rotation=data.get("user_agent_rotation", True),
            viewport_randomization=data.get("viewport_randomization", True),
            mouse_movement_simulation=data.get("mouse_movement_simulation", True),
            typing_simulation=data.get("typing_simulation", True),
            scroll_simulation=data.get("scroll_simulation", True),
            click_delay_simulation=data.get("click_delay_simulation", True),
            navigation_delay_simulation=data.get("navigation_delay_simulation", True),
            timing_randomization=data.get("timing_randomization", True),
            min_delay_ms=data.get("min_delay_ms", 100.0),
            max_delay_ms=data.get("max_delay_ms", 1000.0),
            delay_variation_factor=data.get("delay_variation_factor", 0.3),
            normalize_user_agent=data.get("normalize_user_agent", True),
            normalize_screen_resolution=data.get("normalize_screen_resolution", True),
            normalize_timezone=data.get("normalize_timezone", True),
            normalize_language=data.get("normalize_language", True),
            normalize_platform=data.get("normalize_platform", True),
            canvas_fingerprint_protection=data.get("canvas_fingerprint_protection", True),
            webgl_fingerprint_protection=data.get("webgl_fingerprint_protection", True),
            audio_context_protection=data.get("audio_context_protection", True),
            webrtc_protection=data.get("webrtc_protection", True),
            font_fingerprint_protection=data.get("font_fingerprint_protection", True),
            plugin_simulation=data.get("plugin_simulation", True),
            header_normalization=data.get("header_normalization", True),
            connection_type_normalization=data.get("connection_type_normalization", True),
            accept_language_normalization=data.get("accept_language_normalization", True),
            accept_encoding_normalization=data.get("accept_encoding_normalization", True),
            human_like_scrolling=data.get("human_like_scrolling", True),
            random_mouse_movements=data.get("random_mouse_movements", True),
            natural_typing_rhythm=data.get("natural_typing_rhythm", True),
            page_interaction_simulation=data.get("page_interaction_simulation", True),
            enabled_fingerprints=enabled_fingerprints,
            custom_user_agents=data.get("custom_user_agents", []),
            proxy_rotation=data.get("proxy_rotation", False),
            residential_ip_required=data.get("residential_ip_required", False)
        )
        
    @classmethod
    def from_json(cls, json_str: str) -> "StealthSettings":
        """Create StealthSettings from JSON string."""
        import json
        data = json.loads(json_str)
        return cls.from_dict(data)
        
    @classmethod
    def get_stealth_presets(cls) -> Dict[str, "StealthSettings"]:
        """Get common stealth configuration presets."""
        return {
            "minimal": cls(
                stealth_level=StealthLevel.MINIMAL,
                fingerprint_randomization=True,
                user_agent_rotation=False,
                mouse_movement_simulation=False,
                typing_simulation=False,
                scroll_simulation=False
            ),
            "standard": cls(
                stealth_level=StealthLevel.STANDARD,
                fingerprint_randomization=True,
                user_agent_rotation=True,
                mouse_movement_simulation=True,
                typing_simulation=True,
                scroll_simulation=True,
                timing_randomization=True
            ),
            "high": cls(
                stealth_level=StealthLevel.HIGH,
                fingerprint_randomization=True,
                user_agent_rotation=True,
                mouse_movement_simulation=True,
                typing_simulation=True,
                scroll_simulation=True,
                canvas_fingerprint_protection=True,
                webgl_fingerprint_protection=True,
                timing_randomization=True
            ),
            "maximum": cls(
                stealth_level=StealthLevel.MAXIMUM,
                fingerprint_randomization=True,
                user_agent_rotation=True,
                mouse_movement_simulation=True,
                typing_simulation=True,
                scroll_simulation=True,
                canvas_fingerprint_protection=True,
                webgl_fingerprint_protection=True,
                audio_context_protection=True,
                webrtc_protection=True,
                font_fingerprint_protection=True,
                plugin_simulation=True,
                timing_randomization=True,
                residential_ip_required=True
            )
        }
        
    def __str__(self) -> str:
        """String representation."""
        return f"StealthSettings(level={self.stealth_level.value}, randomization={self.fingerprint_randomization})"
        
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"StealthSettings(stealth_level={self.stealth_level.value}, "
                f"fingerprint_randomization={self.fingerprint_randomization}, "
                f"user_agent_rotation={self.user_agent_rotation}, "
                f"mouse_simulation={self.mouse_movement_simulation}, "
                f"typing_simulation={self.typing_simulation}, "
                f"scroll_simulation={self.scroll_simulation}, "
                f"canvas_protection={self.canvas_fingerprint_protection})")
