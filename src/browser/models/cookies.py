"""
Cookie Data Entity

This module defines the CookieData entity for browser cookie management.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
import structlog


@dataclass
class CookieData:
    """Browser cookie data with validation and conversion methods."""
    name: str
    value: str
    domain: str
    path: str = "/"
    expires: Optional[float] = None
    secure: bool = False
    http_only: bool = False
    same_site: str = "Lax"  # Lax, Strict, None
    
    def __post_init__(self):
        """Validate cookie data after initialization."""
        self.logger = structlog.get_logger("browser.cookies")
        
        # Validate required fields
        if not self.name:
            raise ValueError("Cookie name cannot be empty")
        if not self.domain:
            raise ValueError("Cookie domain cannot be empty")
            
        # Validate same_site value
        valid_same_site = ["Lax", "Strict", "None"]
        if self.same_site not in valid_same_site:
            self.logger.warning(
                "Invalid same_site value, defaulting to Lax",
                name=self.name,
                domain=self.domain,
                same_site=self.same_site
            )
            self.same_site = "Lax"
            
    def is_expired(self) -> bool:
        """Check if cookie has expired."""
        if self.expires is None:
            return False
        import time
        return time.time() > self.expires
        
    def is_valid_for_domain(self, target_domain: str) -> bool:
        """Check if cookie is valid for target domain."""
        # Exact match
        if self.domain == target_domain:
            return True
            
        # Subdomain match (cookie domain starts with .)
        if self.domain.startswith('.'):
            return target_domain.endswith(self.domain)
            
        # Partial match
        return target_domain == self.domain or target_domain.endswith('.' + self.domain)
        
    def is_valid_for_path(self, target_path: str) -> bool:
        """Check if cookie is valid for target path."""
        return target_path.startswith(self.path)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "domain": self.domain,
            "path": self.path,
            "expires": self.expires,
            "secure": self.secure,
            "http_only": self.http_only,
            "same_site": self.same_site
        }
        
    def to_json(self) -> str:
        """Convert to JSON string."""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False)
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CookieData":
        """Create CookieData from dictionary."""
        return cls(**data)
        
    @classmethod
    def from_json(cls, json_str: str) -> "CookieData":
        """Create CookieData from JSON string."""
        import json
        data = json.loads(json_str)
        return cls.from_dict(data)
        
    @classmethod
    def from_playwright_cookie(cls, cookie_data: Dict[str, Any]) -> "CookieData":
        """Create CookieData from Playwright cookie format."""
        return cls(
            name=cookie_data["name"],
            value=cookie_data["value"],
            domain=cookie_data["domain"],
            path=cookie_data.get("path", "/"),
            expires=cookie_data.get("expires"),
            secure=cookie_data.get("secure", False),
            http_only=cookie_data.get("httpOnly", False),
            same_site=cookie_data.get("sameSite", "Lax")
        )
        
    def to_playwright_format(self) -> Dict[str, Any]:
        """Convert to Playwright cookie format."""
        result = {
            "name": self.name,
            "value": self.value,
            "domain": self.domain,
            "path": self.path,
            "secure": self.secure,
            "httpOnly": self.http_only,
            "sameSite": self.same_site
        }
        
        # Only include expires if it exists
        if self.expires is not None:
            result["expires"] = self.expires
            
        return result
        
    def __str__(self) -> str:
        """String representation."""
        return f"CookieData(name={self.name}, domain={self.domain}, path={self.path})"
        
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"CookieData(name={self.name}, value={self.value[:20]}..., "
                f"domain={self.domain}, path={self.path}, "
                f"secure={self.secure}, http_only={self.http_only}, "
                f"same_site={self.same_site}, expires={self.expires})")
        
    def __eq__(self, other) -> bool:
        """Check equality based on name and domain."""
        if not isinstance(other, CookieData):
            return False
        return self.name == other.name and self.domain == other.domain
        
    def __hash__(self) -> int:
        """Hash based on name and domain."""
        return hash((self.name, self.domain))
