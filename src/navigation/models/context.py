"""
NavigationContext entity

Current state information including page data, session state, and navigation history.
Conforms to Constitution Principle III - Deep Modularity.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import json


class NavigationOutcome(Enum):
    """Possible outcomes of navigation actions"""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    DETECTED = "detected"
    REDIRECTED = "redirected"


@dataclass
class PageState:
    """Current page information"""
    
    url: str
    title: str = ""
    page_type: str = "unknown"  # standard, spa, form, etc.
    load_time: float = 0.0
    dom_elements_count: int = 0
    has_dynamic_content: bool = False
    requires_authentication: bool = False
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert page state to dictionary"""
        return {
            'url': self.url,
            'title': self.title,
            'page_type': self.page_type,
            'load_time': self.load_time,
            'dom_elements_count': self.dom_elements_count,
            'has_dynamic_content': self.has_dynamic_content,
            'requires_authentication': self.requires_authentication,
            'last_accessed': self.last_accessed.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PageState':
        """Create page state from dictionary"""
        page_state = cls(
            url=data['url'],
            title=data.get('title', ''),
            page_type=data.get('page_type', 'unknown'),
            load_time=data.get('load_time', 0.0),
            dom_elements_count=data.get('dom_elements_count', 0),
            has_dynamic_content=data.get('has_dynamic_content', False),
            requires_authentication=data.get('requires_authentication', False)
        )
        
        if 'last_accessed' in data:
            page_state.last_accessed = datetime.fromisoformat(data['last_accessed'])
        
        return page_state


@dataclass
class AuthenticationState:
    """Current authentication status"""
    
    is_authenticated: bool = False
    auth_method: str = ""  # cookie, token, basic, etc.
    auth_domain: str = ""
    session_id: Optional[str] = None
    user_agent: str = ""
    expires_at: Optional[datetime] = None
    permissions: List[str] = field(default_factory=list)
    
    def is_valid(self) -> bool:
        """Check if authentication is still valid"""
        if not self.is_authenticated:
            return False
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert auth state to dictionary"""
        return {
            'is_authenticated': self.is_authenticated,
            'auth_method': self.auth_method,
            'auth_domain': self.auth_domain,
            'session_id': self.session_id,
            'user_agent': self.user_agent,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'permissions': self.permissions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuthenticationState':
        """Create auth state from dictionary"""
        auth_state = cls(
            is_authenticated=data.get('is_authenticated', False),
            auth_method=data.get('auth_method', ''),
            auth_domain=data.get('auth_domain', ''),
            session_id=data.get('session_id'),
            user_agent=data.get('user_agent', ''),
            permissions=data.get('permissions', [])
        )
        
        if 'expires_at' in data and data['expires_at']:
            auth_state.expires_at = datetime.fromisoformat(data['expires_at'])
        
        return auth_state


@dataclass
class NavigationContext:
    """Current state information for navigation session"""
    
    # Core identification
    context_id: str
    session_id: str
    
    # Current state
    current_page: PageState
    
    # Navigation history
    navigation_history: List[str] = field(default_factory=list)  # Event IDs
    
    # Session data
    session_data: Dict[str, Any] = field(default_factory=dict)
    
    # Authentication state
    authentication_state: AuthenticationState = field(default_factory=AuthenticationState)
    
    # Tracking
    correlation_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    # Performance metrics
    pages_visited: int = 0
    total_navigation_time: float = 0.0
    successful_navigations: int = 0
    failed_navigations: int = 0
    
    def __post_init__(self) -> None:
        """Initialize context after dataclass creation"""
        if not self.context_id:
            raise ValueError("Context ID cannot be empty")
        
        if not self.session_id:
            raise ValueError("Session ID cannot be empty")
        
        if not self.correlation_id:
            self.correlation_id = self.context_id
    
    def update_page(self, new_page: PageState) -> None:
        """Update current page state"""
        self.current_page = new_page
        self.pages_visited += 1
        self.last_updated = datetime.utcnow()
    
    def add_navigation_event(self, event_id: str) -> None:
        """Add navigation event to history"""
        self.navigation_history.append(event_id)
        self.last_updated = datetime.utcnow()
    
    def update_session_data(self, key: str, value: Any) -> None:
        """Update session data"""
        self.session_data[key] = value
        self.last_updated = datetime.utcnow()
    
    def get_session_data(self, key: str, default: Any = None) -> Any:
        """Get session data value"""
        return self.session_data.get(key, default)
    
    def update_authentication(self, auth_state: AuthenticationState) -> None:
        """Update authentication state"""
        self.authentication_state = auth_state
        self.last_updated = datetime.utcnow()
    
    def record_navigation_success(self, duration: float) -> None:
        """Record successful navigation"""
        self.successful_navigations += 1
        self.total_navigation_time += duration
        self.last_updated = datetime.utcnow()
    
    def record_navigation_failure(self, duration: float) -> None:
        """Record failed navigation"""
        self.failed_navigations += 1
        self.total_navigation_time += duration
        self.last_updated = datetime.utcnow()
    
    def get_success_rate(self) -> float:
        """Calculate navigation success rate"""
        total_navigations = self.successful_navigations + self.failed_navigations
        if total_navigations == 0:
            return 0.0
        return self.successful_navigations / total_navigations
    
    def get_average_navigation_time(self) -> float:
        """Calculate average navigation time"""
        total_navigations = self.successful_navigations + self.failed_navigations
        if total_navigations == 0:
            return 0.0
        return self.total_navigation_time / total_navigations
    
    def is_authenticated(self) -> bool:
        """Check if context has valid authentication"""
        return self.authentication_state.is_valid()
    
    def requires_authentication(self) -> bool:
        """Check if current page requires authentication"""
        return self.current_page.requires_authentication
    
    def get_navigation_summary(self) -> Dict[str, Any]:
        """Get summary of navigation context"""
        return {
            'context_id': self.context_id,
            'session_id': self.session_id,
            'current_url': self.current_page.url,
            'pages_visited': self.pages_visited,
            'success_rate': self.get_success_rate(),
            'average_navigation_time': self.get_average_navigation_time(),
            'is_authenticated': self.is_authenticated(),
            'total_navigation_time': self.total_navigation_time,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary representation"""
        return {
            'context_id': self.context_id,
            'session_id': self.session_id,
            'current_page': self.current_page.to_dict(),
            'navigation_history': self.navigation_history,
            'session_data': self.session_data,
            'authentication_state': self.authentication_state.to_dict(),
            'correlation_id': self.correlation_id,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'pages_visited': self.pages_visited,
            'total_navigation_time': self.total_navigation_time,
            'successful_navigations': self.successful_navigations,
            'failed_navigations': self.failed_navigations
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NavigationContext':
        """Create context from dictionary representation"""
        context = cls(
            context_id=data['context_id'],
            session_id=data['session_id'],
            current_page=PageState.from_dict(data['current_page']),
            navigation_history=data.get('navigation_history', []),
            session_data=data.get('session_data', {}),
            authentication_state=AuthenticationState.from_dict(data.get('authentication_state', {})),
            correlation_id=data.get('correlation_id', ''),
            pages_visited=data.get('pages_visited', 0),
            total_navigation_time=data.get('total_navigation_time', 0.0),
            successful_navigations=data.get('successful_navigations', 0),
            failed_navigations=data.get('failed_navigations', 0)
        )
        
        # Set timestamps
        if 'created_at' in data:
            context.created_at = datetime.fromisoformat(data['created_at'])
        if 'last_updated' in data:
            context.last_updated = datetime.fromisoformat(data['last_updated'])
        
        return context
    
    def to_json(self) -> str:
        """Convert context to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'NavigationContext':
        """Create context from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
