"""
Browser Lifecycle Management Interfaces

This module defines the core interfaces for browser lifecycle management,
following the API contracts specification.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .models.session import BrowserSession, BrowserConfiguration
    from .models.context import TabContext
    from .models.state import BrowserState
    from .models.metrics import ResourceMetrics
    from .models.enums import SessionStatus, AlertStatus, CleanupLevel


class IBrowserAuthority(ABC):
    """Central authority for browser instance management and lifecycle control."""
    
    @abstractmethod
    async def create_session(self, configuration: Optional["BrowserConfiguration"] = None) -> "BrowserSession":
        """Create a new browser session with optional configuration."""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional["BrowserSession"]:
        """Retrieve an existing browser session by ID."""
        pass
    
    @abstractmethod
    async def list_sessions(self, status_filter: Optional["SessionStatus"] = None) -> List["BrowserSession"]:
        """List all browser sessions, optionally filtered by status."""
        pass
    
    @abstractmethod
    async def terminate_session(self, session_id: str) -> bool:
        """Terminate a browser session gracefully."""
        pass
    
    @abstractmethod
    async def cleanup_resources(self, session_id: str) -> bool:
        """Force cleanup of session resources."""
        pass
    
    @abstractmethod
    async def get_system_metrics(self) -> "ResourceMetrics":
        """Get system-wide browser resource metrics."""
        pass
    
    @abstractmethod
    async def get_active_session_count(self) -> int:
        """Get count of active browser sessions."""
        pass
    
    @abstractmethod
    async def shutdown_all_sessions(self) -> Dict[str, bool]:
        """Shutdown all sessions, returning success status per session."""
        pass


class IBrowserSession(ABC):
    """Interface for individual browser session management."""
    
    @abstractmethod
    async def create_context(self, url: Optional[str] = None) -> "TabContext":
        """Create a new browser context/tab."""
        pass
    
    @abstractmethod
    async def get_context(self, context_id: str) -> Optional["TabContext"]:
        """Retrieve a specific context by ID."""
        pass
    
    @abstractmethod
    async def list_contexts(self) -> List["TabContext"]:
        """List all contexts in this session."""
        pass
    
    @abstractmethod
    async def switch_to_context(self, context_id: str) -> bool:
        """Switch to a specific context."""
        pass
    
    @abstractmethod
    async def close_context(self, context_id: str) -> bool:
        """Close a specific context."""
        pass
    
    @abstractmethod
    async def save_state(self, state_id: Optional[str] = None) -> "BrowserState":
        """Save the current browser state."""
        pass
    
    @abstractmethod
    async def restore_state(self, state: "BrowserState") -> bool:
        """Restore browser state from saved data."""
        pass
    
    @abstractmethod
    async def get_resource_metrics(self) -> "ResourceMetrics":
        """Get current resource usage metrics."""
        pass
    
    @abstractmethod
    async def take_screenshot(self, context_id: Optional[str] = None) -> bytes:
        """Take screenshot of session or specific context."""
        pass
    
    @abstractmethod
    async def get_dom_snapshot(self, context_id: Optional[str] = None) -> Dict[str, Any]:
        """Get DOM snapshot for debugging."""
        pass


class ITabContext(ABC):
    """Interface for browser tab/context management."""
    
    @abstractmethod
    async def navigate(self, url: str) -> bool:
        """Navigate to a URL."""
        pass
    
    @abstractmethod
    async def get_current_url(self) -> Optional[str]:
        """Get the current URL."""
        pass
    
    @abstractmethod
    async def get_page_title(self) -> Optional[str]:
        """Get the current page title."""
        pass
    
    @abstractmethod
    async def wait_for_load(self, timeout: int = 30000) -> bool:
        """Wait for page to load completely."""
        pass
    
    @abstractmethod
    async def take_screenshot(self, path: Optional[str] = None) -> bytes:
        """Take a screenshot of the current page."""
        pass
    
    @abstractmethod
    async def get_dom_snapshot(self) -> Dict[str, Any]:
        """Get DOM snapshot for debugging."""
        pass
    
    @abstractmethod
    async def execute_script(self, script: str, *args) -> Any:
        """Execute JavaScript in the context."""
        pass
    
    @abstractmethod
    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> bool:
        """Wait for selector to be available."""
        pass
    
    @abstractmethod
    async def click(self, selector: str) -> bool:
        """Click on element matching selector."""
        pass
    
    @abstractmethod
    async def type_text(self, selector: str, text: str) -> bool:
        """Type text into element matching selector."""
        pass
    
    @abstractmethod
    async def get_text(self, selector: str) -> Optional[str]:
        """Get text content of element matching selector."""
        pass
    
    @abstractmethod
    async def get_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """Get attribute value of element matching selector."""
        pass


class IResourceMonitor(ABC):
    """Interface for resource monitoring and cleanup."""
    
    @abstractmethod
    async def start_monitoring(self, session_id: str) -> None:
        """Start monitoring a specific session."""
        pass
    
    @abstractmethod
    async def stop_monitoring(self, session_id: str) -> None:
        """Stop monitoring a specific session."""
        pass
    
    @abstractmethod
    async def get_metrics(self, session_id: str) -> "ResourceMetrics":
        """Get current metrics for a session."""
        pass
    
    @abstractmethod
    async def check_thresholds(self, session_id: str) -> "AlertStatus":
        """Check if resource thresholds are exceeded."""
        pass
    
    @abstractmethod
    async def trigger_cleanup(self, session_id: str, level: "CleanupLevel") -> bool:
        """Trigger resource cleanup at specified level."""
        pass
    
    @abstractmethod
    async def set_thresholds(
        self,
        memory_mb: float,
        cpu_percent: float,
        disk_mb: float
    ) -> None:
        """Set resource monitoring thresholds."""
        pass
    
    @abstractmethod
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get status of all monitored sessions."""
        pass


class IStateManager(ABC):
    """Interface for browser state persistence."""
    
    @abstractmethod
    async def save_state(self, session: "BrowserSession", state_id: Optional[str] = None) -> str:
        """Save browser state to storage."""
        pass
    
    @abstractmethod
    async def load_state(self, state_id: str) -> Optional["BrowserState"]:
        """Load browser state from storage."""
        pass
    
    @abstractmethod
    async def list_states(self, session_id: Optional[str] = None) -> List[str]:
        """List saved state IDs, optionally filtered by session."""
        pass
    
    @abstractmethod
    async def delete_state(self, state_id: str) -> bool:
        """Delete a saved state."""
        pass
    
    @abstractmethod
    async def cleanup_expired_states(self) -> int:
        """Clean up expired states, returns count deleted."""
        pass
    
    @abstractmethod
    async def encrypt_state_data(self, data: Dict[str, Any]) -> bytes:
        """Encrypt state data for secure storage."""
        pass
    
    @abstractmethod
    async def decrypt_state_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        """Decrypt state data from secure storage."""
        pass


class IDOMContextProvider(ABC):
    """Provide DOM context to selector engine."""
    
    @abstractmethod
    async def get_dom_context(self, session_id: str, context_id: str) -> Dict[str, Any]:
        """Get DOM context for selector engine."""
        pass
    
    @abstractmethod
    async def execute_selector(self, session_id: str, context_id: str, selector: str) -> List[Dict[str, Any]]:
        """Execute selector in specific context."""
        pass


class IEventEmitter(ABC):
    """Emit browser lifecycle events."""
    
    @abstractmethod
    async def emit_event(self, event_type: str, session_id: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Emit a browser lifecycle event."""
        pass
    
    @abstractmethod
    async def subscribe(self, event_type: str, callback) -> str:
        """Subscribe to browser lifecycle events."""
        pass
    
    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from browser lifecycle events."""
        pass


class IMetricsCollector(ABC):
    """Collect browser metrics."""
    
    @abstractmethod
    async def record_metric(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Record a metric value."""
        pass
    
    @abstractmethod
    async def increment_counter(self, name: str, tags: Dict[str, str] = None) -> None:
        """Increment a counter metric."""
        pass
    
    @abstractmethod
    async def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Record a histogram metric."""
        pass
    
    @abstractmethod
    async def record_gauge(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Record a gauge metric."""
        pass
