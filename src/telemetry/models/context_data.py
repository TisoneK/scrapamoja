"""
Context Data Model

Execution context information for selector operations
following the data model specification.
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field, validator
from urllib.parse import urlparse


class ViewportSize(BaseModel):
    """Browser viewport dimensions."""
    width: int = Field(..., description="Viewport width in pixels")
    height: int = Field(..., description="Viewport height in pixels")
    
    @validator('width')
    def validate_width(cls, v):
        """Validate width is positive."""
        if v <= 0:
            raise ValueError("width must be positive")
        return v
    
    @validator('height')
    def validate_height(cls, v):
        """Validate height is positive."""
        if v <= 0:
            raise ValueError("height must be positive")
        return v


class ContextData(BaseModel):
    """
    Execution context information for selector operations.
    
    Contains comprehensive context data including browser session,
    tab context, page information, and viewport details.
    """
    
    browser_session_id: str = Field(..., description="Identifier for browser session")
    tab_context_id: str = Field(..., description="Identifier for tab context")
    page_url: Optional[str] = Field(None, description="URL of the page where selector was used")
    page_title: Optional[str] = Field(None, description="Title of the page")
    user_agent: Optional[str] = Field(None, description="Browser user agent")
    viewport_size: Optional[ViewportSize] = Field(None, description="Viewport dimensions")
    timestamp_context: Optional[str] = Field(None, description="Context timestamp for correlation")
    
    @validator('browser_session_id')
    def validate_browser_session_id(cls, v):
        """Validate browser session ID is not empty."""
        if not v or not v.strip():
            raise ValueError("browser_session_id must be a non-empty string")
        return v.strip()
    
    @validator('tab_context_id')
    def validate_tab_context_id(cls, v):
        """Validate tab context ID is not empty."""
        if not v or not v.strip():
            raise ValueError("tab_context_id must be a non-empty string")
        return v.strip()
    
    @validator('page_url')
    def validate_page_url(cls, v):
        """Validate page URL format if provided."""
        if v is not None and v.strip():
            try:
                parsed = urlparse(v.strip())
                if not parsed.scheme or not parsed.netloc:
                    raise ValueError("page_url must be a valid URL")
                return v.strip()
            except Exception:
                raise ValueError("page_url must be a valid URL")
        return v
    
    @validator('page_title')
    def validate_page_title(cls, v):
        """Validate page title."""
        if v is not None:
            return v.strip() if v.strip() else None
        return v
    
    @validator('user_agent')
    def validate_user_agent(cls, v):
        """Validate user agent."""
        if v is not None:
            return v.strip() if v.strip() else None
        return v
    
    @validator('timestamp_context')
    def validate_timestamp_context(cls, v):
        """Validate timestamp context."""
        if v is not None:
            return v.strip() if v.strip() else None
        return v
    
    def get_domain(self) -> Optional[str]:
        """
        Extract domain from page URL.
        
        Returns:
            Domain name or None if no URL
        """
        if not self.page_url:
            return None
        
        try:
            parsed = urlparse(self.page_url)
            return parsed.netloc
        except Exception:
            return None
    
    def get_url_scheme(self) -> Optional[str]:
        """
        Extract URL scheme.
        
        Returns:
            URL scheme (http, https) or None if no URL
        """
        if not self.page_url:
            return None
        
        try:
            parsed = urlparse(self.page_url)
            return parsed.scheme
        except Exception:
            return None
    
    def is_secure_page(self) -> bool:
        """
        Check if page is using HTTPS.
        
        Returns:
            True if page uses HTTPS
        """
        return self.get_url_scheme() == "https"
    
    def has_viewport_info(self) -> bool:
        """
        Check if viewport information is available.
        
        Returns:
            True if viewport size is available
        """
        return self.viewport_size is not None
    
    def get_viewport_area(self) -> Optional[int]:
        """
        Calculate viewport area.
        
        Returns:
            Viewport area in pixels or None if not available
        """
        if not self.viewport_size:
            return None
        
        return self.viewport_size.width * self.viewport_size.height
    
    def is_mobile_viewport(self) -> Optional[bool]:
        """
        Determine if viewport is mobile-sized.
        
        Returns:
            True if mobile viewport, False if desktop, None if unknown
        """
        if not self.viewport_size:
            return None
        
        # Common mobile viewport width threshold
        return self.viewport_size.width <= 768
    
    def is_tablet_viewport(self) -> Optional[bool]:
        """
        Determine if viewport is tablet-sized.
        
        Returns:
            True if tablet viewport, False if other, None if unknown
        """
        if not self.viewport_size:
            return None
        
        width = self.viewport_size.width
        return 768 < width <= 1024
    
    def is_desktop_viewport(self) -> Optional[bool]:
        """
        Determine if viewport is desktop-sized.
        
        Returns:
            True if desktop viewport, False if other, None if unknown
        """
        if not self.viewport_size:
            return None
        
        return self.viewport_size.width > 1024
    
    def get_context_fingerprint(self) -> str:
        """
        Generate a fingerprint for the context.
        
        Returns:
            Context fingerprint string
        """
        components = [
            self.browser_session_id,
            self.tab_context_id,
            self.get_domain() or "",
            str(self.get_viewport_area()) if self.viewport_size else ""
        ]
        
        return "|".join(filter(None, components))
    
    def is_same_domain(self, other_url: str) -> bool:
        """
        Check if another URL is from the same domain.
        
        Args:
            other_url: URL to compare
            
        Returns:
            True if same domain
        """
        if not self.page_url or not other_url:
            return False
        
        try:
            current_domain = urlparse(self.page_url).netloc
            other_domain = urlparse(other_url).netloc
            return current_domain == other_domain
        except Exception:
            return False
    
    def has_user_agent(self) -> bool:
        """
        Check if user agent information is available.
        
        Returns:
            True if user agent is available
        """
        return bool(self.user_agent)
    
    def is_chrome_browser(self) -> Optional[bool]:
        """
        Check if browser is Chrome.
        
        Returns:
            True if Chrome, False if not, None if unknown
        """
        if not self.user_agent:
            return None
        
        return "chrome" in self.user_agent.lower()
    
    def is_firefox_browser(self) -> Optional[bool]:
        """
        Check if browser is Firefox.
        
        Returns:
            True if Firefox, False if not, None if unknown
        """
        if not self.user_agent:
            return None
        
        return "firefox" in self.user_agent.lower()
    
    def is_safari_browser(self) -> Optional[bool]:
        """
        Check if browser is Safari.
        
        Returns:
            True if Safari, False if not, None if unknown
        """
        if not self.user_agent:
            return None
        
        ua_lower = self.user_agent.lower()
        return "safari" in ua_lower and "chrome" not in ua_lower
    
    def to_dict(self) -> dict:
        """Convert to dictionary with all fields."""
        result = {
            "browser_session_id": self.browser_session_id,
            "tab_context_id": self.tab_context_id,
            "page_url": self.page_url,
            "page_title": self.page_title,
            "user_agent": self.user_agent,
            "timestamp_context": self.timestamp_context
        }
        
        if self.viewport_size:
            result["viewport_size"] = {
                "width": self.viewport_size.width,
                "height": self.viewport_size.height
            }
        
        return result
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
