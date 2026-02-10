"""
Browser State Entity

This module defines the BrowserState entity for browser state persistence.
"""

import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import structlog

from .enums import StateStatus


@dataclass
class CookieData:
    """Browser cookie data."""
    name: str
    value: str
    domain: str
    path: str = "/"
    expires: Optional[float] = None
    secure: bool = False
    http_only: bool = False
    same_site: str = "Lax"  # Lax, Strict, None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
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
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CookieData":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ViewportSettings:
    """Browser viewport configuration."""
    width: int = 1920
    height: int = 1080
    device_scale_factor: float = 1.0
    is_mobile: bool = False
    has_touch: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "width": self.width,
            "height": self.height,
            "device_scale_factor": self.device_scale_factor,
            "is_mobile": self.is_mobile,
            "has_touch": self.has_touch
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ViewportSettings":
        """Create from dictionary."""
        return cls(**data)


class BrowserState:
    """Serializable collection of cookies, storage, and authentication data."""
    
    def __init__(
        self,
        state_id: str,
        session_id: str,
        cookies: Optional[List[CookieData]] = None,
        local_storage: Optional[Dict[str, str]] = None,
        session_storage: Optional[Dict[str, str]] = None,
        authentication_tokens: Optional[Dict[str, Any]] = None,
        user_agent: Optional[str] = None,
        viewport: Optional[ViewportSettings] = None,
        created_at: Optional[float] = None,
        expires_at: Optional[float] = None,
        schema_version: str = "1.0.0"
    ):
        self.state_id = state_id
        self.session_id = session_id
        self.cookies = cookies or []
        self.local_storage = local_storage or {}
        self.session_storage = session_storage or {}
        self.authentication_tokens = authentication_tokens or {}
        self.user_agent = user_agent
        self.viewport = viewport or ViewportSettings()
        self.created_at = created_at or time.time()
        self.expires_at = expires_at
        self.schema_version = schema_version
        self.status = StateStatus.SAVED
        
        self.logger = structlog.get_logger("browser.state")
        
    def add_cookie(self, cookie: CookieData) -> None:
        """Add a cookie to the state."""
        # Remove existing cookie with same name/domain
        self.cookies = [c for c in self.cookies 
                       if not (c.name == cookie.name and c.domain == cookie.domain)]
        self.cookies.append(cookie)
        
    def remove_cookie(self, name: str, domain: str) -> bool:
        """Remove a cookie by name and domain."""
        original_count = len(self.cookies)
        self.cookies = [c for c in self.cookies 
                       if not (c.name == name and c.domain == cookie.domain)]
        return len(self.cookies) < original_count
        
    def get_cookie(self, name: str, domain: str) -> Optional[CookieData]:
        """Get a cookie by name and domain."""
        for cookie in self.cookies:
            if cookie.name == name and cookie.domain == domain:
                return cookie
        return None
        
    def set_local_storage(self, key: str, value: str) -> None:
        """Set a local storage item."""
        self.local_storage[key] = value
        
    def get_local_storage(self, key: str) -> Optional[str]:
        """Get a local storage item."""
        return self.local_storage.get(key)
        
    def remove_local_storage(self, key: str) -> bool:
        """Remove a local storage item."""
        return self.local_storage.pop(key, None) is not None
        
    def set_session_storage(self, key: str, value: str) -> None:
        """Set a session storage item."""
        self.session_storage[key] = value
        
    def get_session_storage(self, key: str) -> Optional[str]:
        """Get a session storage item."""
        return self.session_storage.get(key)
        
    def remove_session_storage(self, key: str) -> bool:
        """Remove a session storage item."""
        return self.session_storage.pop(key, None) is not None
        
    def set_auth_token(self, token_type: str, token_data: Any) -> None:
        """Set an authentication token."""
        self.authentication_tokens[token_type] = token_data
        
    def get_auth_token(self, token_type: str) -> Optional[Any]:
        """Get an authentication token."""
        return self.authentication_tokens.get(token_type)
        
    def remove_auth_token(self, token_type: str) -> bool:
        """Remove an authentication token."""
        return self.authentication_tokens.pop(token_type, None) is not None
        
    def is_expired(self) -> bool:
        """Check if the state has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
        
    def get_age_seconds(self) -> float:
        """Get state age in seconds."""
        return time.time() - self.created_at
        
    def get_size_bytes(self) -> int:
        """Get approximate size in bytes."""
        # Create a minimal dict without size_bytes to avoid recursion
        minimal_dict = {
            "state_id": self.state_id,
            "session_id": self.session_id,
            "cookies": [cookie.to_dict() for cookie in self.cookies],
            "local_storage": self.local_storage.copy(),
            "session_storage": self.session_storage.copy(),
            "authentication_tokens": self.authentication_tokens.copy(),
            "user_agent": self.user_agent,
            "viewport": self.viewport.to_dict(),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "schema_version": self.schema_version,
            "status": self.status.value
        }
        return len(json.dumps(minimal_dict).encode('utf-8'))
        
    def validate(self) -> List[str]:
        """Validate state and return list of issues."""
        issues = []
        
        # Validate schema version
        if not self.schema_version:
            issues.append("Missing schema version")
            
        # Validate cookies
        for cookie in self.cookies:
            if not cookie.name or not cookie.domain:
                issues.append(f"Invalid cookie: {cookie}")
                
        # Validate storage data is JSON serializable
        try:
            json.dumps(self.local_storage)
            json.dumps(self.session_storage)
            json.dumps(self.authentication_tokens)
        except (TypeError, ValueError) as e:
            issues.append(f"Storage data not serializable: {e}")
            
        return issues
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "state_id": self.state_id,
            "session_id": self.session_id,
            "cookies": [cookie.to_dict() for cookie in self.cookies],
            "local_storage": self.local_storage.copy(),
            "session_storage": self.session_storage.copy(),
            "authentication_tokens": self.authentication_tokens.copy(),
            "user_agent": self.user_agent,
            "viewport": self.viewport.to_dict(),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "age_seconds": self.get_age_seconds(),
            "size_bytes": self.get_size_bytes(),
            "is_expired": self.is_expired()
        }
        
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BrowserState":
        """Create BrowserState from dictionary."""
        # Convert cookies back to CookieData objects
        cookies = [CookieData.from_dict(cookie_data) 
                  for cookie_data in data.get("cookies", [])]
        
        # Convert viewport back to ViewportSettings
        viewport_data = data.get("viewport", {})
        viewport = ViewportSettings(**viewport_data)
        
        # Convert status back to enum
        status_str = data.get("status", StateStatus.SAVED.value)
        status = StateStatus(status_str)
        
        state = cls(
            state_id=data["state_id"],
            session_id=data["session_id"],
            cookies=cookies,
            local_storage=data.get("local_storage", {}),
            session_storage=data.get("session_storage", {}),
            authentication_tokens=data.get("authentication_tokens", {}),
            user_agent=data.get("user_agent"),
            viewport=viewport,
            created_at=data.get("created_at"),
            expires_at=data.get("expires_at"),
            schema_version=data.get("schema_version", "1.0.0")
        )
        state.status = status
        
        return state
        
    @classmethod
    def from_json(cls, json_str: str) -> "BrowserState":
        """Create BrowserState from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
        
    def __str__(self) -> str:
        """String representation."""
        return (f"BrowserState(id={self.state_id}, "
                f"session={self.session_id}, "
                f"cookies={len(self.cookies)}, "
                f"status={self.status.value})")
        
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"BrowserState(state_id={self.state_id}, "
                f"session_id={self.session_id}, "
                f"cookies={len(self.cookies)}, "
                f"local_storage_items={len(self.local_storage)}, "
                f"session_storage_items={len(self.session_storage)}, "
                f"auth_tokens={len(self.authentication_tokens)}, "
                f"schema_version={self.schema_version}, "
                f"status={self.status.value}, "
                f"created={datetime.fromtimestamp(self.created_at).isoformat()})")
