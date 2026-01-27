"""
Viewport Settings Entity

This module defines the ViewportSettings entity for browser viewport configuration.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
import structlog


@dataclass
class ViewportSettings:
    """Browser viewport configuration with validation."""
    width: int = 1920
    height: int = 1080
    device_scale_factor: float = 1.0
    is_mobile: bool = False
    has_touch: bool = False
    
    def __post_init__(self):
        """Validate viewport settings after initialization."""
        self.logger = structlog.get_logger("browser.viewport")
        
        # Validate dimensions
        if self.width <= 0:
            self.logger.warning(
                "Invalid viewport width, using default",
                width=self.width,
                default_width=1920
            )
            self.width = 1920
            
        if self.height <= 0:
            self.logger.warning(
                "Invalid viewport height, using default",
                height=self.height,
                default_height=1080
            )
            self.height = 1080
            
        # Validate device scale factor
        if self.device_scale_factor <= 0:
            self.logger.warning(
                "Invalid device scale factor, using default",
                device_scale_factor=self.device_scale_factor,
                default_scale=1.0
            )
            self.device_scale_factor = 1.0
            
    def get_aspect_ratio(self) -> float:
        """Calculate aspect ratio."""
        return self.width / self.height if self.height > 0 else 1.0
        
    def get_pixel_count(self) -> int:
        """Get total pixel count."""
        return self.width * self.height
        
    def is_landscape(self) -> bool:
        """Check if viewport is landscape orientation."""
        return self.width > self.height
        
    def is_portrait(self) -> bool:
        """Check if viewport is portrait orientation."""
        return self.height > self.width
        
    def is_square(self) -> bool:
        """Check if viewport is approximately square."""
        ratio = self.get_aspect_ratio()
        return 0.9 <= ratio <= 1.1
        
    def scale_to_width(self, new_width: int) -> "ViewportSettings":
        """Scale viewport to new width maintaining aspect ratio."""
        if self.width <= 0:
            return ViewportSettings(width=new_width, height=self.height)
            
        scale_factor = new_width / self.width
        new_height = int(self.height * scale_factor)
        
        return ViewportSettings(
            width=new_width,
            height=new_height,
            device_scale_factor=self.device_scale_factor,
            is_mobile=self.is_mobile,
            has_touch=self.has_touch
        )
        
    def scale_to_height(self, new_height: int) -> "ViewportSettings":
        """Scale viewport to new height maintaining aspect ratio."""
        if self.height <= 0:
            return ViewportSettings(width=self.width, height=new_height)
            
        scale_factor = new_height / self.height
        new_width = int(self.width * scale_factor)
        
        return ViewportSettings(
            width=new_width,
            height=new_height,
            device_scale_factor=self.device_scale_factor,
            is_mobile=self.is_mobile,
            has_touch=self.has_touch
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "width": self.width,
            "height": self.height,
            "device_scale_factor": self.device_scale_factor,
            "is_mobile": self.is_mobile,
            "has_touch": self.has_touch,
            "aspect_ratio": self.get_aspect_ratio(),
            "pixel_count": self.get_pixel_count(),
            "orientation": "landscape" if self.is_landscape() else "portrait" if self.is_portrait() else "square"
        }
        
    def to_json(self) -> str:
        """Convert to JSON string."""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False)
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ViewportSettings":
        """Create ViewportSettings from dictionary."""
        # Remove derived fields that shouldn't be stored
        derived_fields = ["aspect_ratio", "pixel_count", "orientation"]
        clean_data = {k: v for k, v in data.items() if k not in derived_fields}
        
        return cls(**clean_data)
        
    @classmethod
    def from_json(cls, json_str: str) -> "ViewportSettings":
        """Create ViewportSettings from JSON string."""
        import json
        data = json.loads(json_str)
        return cls.from_dict(data)
        
    @classmethod
    def get_common_viewports(cls) -> Dict[str, "ViewportSettings"]:
        """Get common viewport presets."""
        return {
            "desktop_1920x1080": cls(width=1920, height=1080),
            "desktop_1366x768": cls(width=1366, height=768),
            "desktop_1440x900": cls(width=1440, height=900),
            "desktop_1280x720": cls(width=1280, height=720),
            "mobile_375x667": cls(width=375, height=667, is_mobile=True, has_touch=True),
            "mobile_414x736": cls(width=414, height=736, is_mobile=True, has_touch=True),
            "mobile_360x640": cls(width=360, height=640, is_mobile=True, has_touch=True),
            "tablet_768x1024": cls(width=768, height=1024, is_mobile=True, has_touch=True),
            "tablet_1024x768": cls(width=1024, height=768, is_mobile=True, has_touch=True)
        }
        
    @classmethod
    def get_desktop_viewport(cls, width: int = 1920, height: int = 1080) -> "ViewportSettings":
        """Get desktop viewport preset."""
        return cls(width=width, height=height, is_mobile=False, has_touch=False)
        
    @classmethod
    def get_mobile_viewport(cls, width: int = 375, height: int = 667) -> "ViewportSettings":
        """Get mobile viewport preset."""
        return cls(width=width, height=height, is_mobile=True, has_touch=True)
        
    @classmethod
    def get_tablet_viewport(cls, width: int = 768, height: int = 1024) -> "ViewportSettings":
        """Get tablet viewport preset."""
        return cls(width=width, height=height, is_mobile=True, has_touch=True)
        
    def __str__(self) -> str:
        """String representation."""
        return f"ViewportSettings({self.width}x{self.height}, mobile={self.is_mobile})"
        
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"ViewportSettings(width={self.width}, height={self.height}, "
                f"device_scale_factor={self.device_scale_factor}, "
                f"is_mobile={self.is_mobile}, has_touch={self.has_touch}, "
                f"aspect_ratio={self.get_aspect_ratio():.2f})")
        
    def __eq__(self, other) -> bool:
        """Check equality."""
        if not isinstance(other, ViewportSettings):
            return False
        return (self.width == other.width and 
                self.height == other.height and
                self.device_scale_factor == other.device_scale_factor and
                self.is_mobile == other.is_mobile and
                self.has_touch == other.has_touch)
        
    def __hash__(self) -> int:
        """Hash based on all attributes."""
        return hash((self.width, self.height, self.device_scale_factor, 
                    self.is_mobile, self.has_touch))
