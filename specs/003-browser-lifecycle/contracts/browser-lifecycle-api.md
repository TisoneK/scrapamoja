# Browser Lifecycle Management API Contracts

**Feature**: Browser Lifecycle Management  
**Date**: 2025-01-27  
**Phase**: 1 - Design & Contracts

## API Overview

This document defines the internal API contracts for the Browser Lifecycle Management feature. These contracts define the interfaces between browser management components and the rest of the Scorewise scraper system.

## Core Interfaces

### IBrowserAuthority

Central authority for browser instance management and lifecycle control.

```python
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime

class IBrowserAuthority(ABC):
    """Central browser management authority."""
    
    @abstractmethod
    async def create_session(
        self, 
        configuration: Optional[BrowserConfiguration] = None
    ) -> BrowserSession:
        """Create a new browser session with optional configuration."""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[BrowserSession]:
        """Retrieve an existing browser session by ID."""
        pass
    
    @abstractmethod
    async def list_sessions(self, status_filter: Optional[SessionStatus] = None) -> List[BrowserSession]:
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
    async def get_system_metrics(self) -> ResourceMetrics:
        """Get system-wide browser resource metrics."""
        pass
```

### IBrowserSession

Interface for individual browser session management.

```python
class IBrowserSession(ABC):
    """Individual browser session interface."""
    
    @abstractmethod
    async def create_context(self, url: Optional[str] = None) -> TabContext:
        """Create a new browser context/tab."""
        pass
    
    @abstractmethod
    async def get_context(self, context_id: str) -> Optional[TabContext]:
        """Retrieve a specific context by ID."""
        pass
    
    @abstractmethod
    async def list_contexts(self) -> List[TabContext]:
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
    async def save_state(self, state_id: Optional[str] = None) -> BrowserState:
        """Save the current browser state."""
        pass
    
    @abstractmethod
    async def restore_state(self, state: BrowserState) -> bool:
        """Restore browser state from saved data."""
        pass
    
    @abstractmethod
    async def get_resource_metrics(self) -> ResourceMetrics:
        """Get current resource usage metrics."""
        pass
```

### ITabContext

Interface for browser tab/context management.

```python
class ITabContext(ABC):
    """Browser tab/context interface."""
    
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
```

### IResourceMonitor

Interface for resource monitoring and cleanup.

```python
class IResourceMonitor(ABC):
    """Resource monitoring interface."""
    
    @abstractmethod
    async def start_monitoring(self, session_id: str) -> None:
        """Start monitoring a specific session."""
        pass
    
    @abstractmethod
    async def stop_monitoring(self, session_id: str) -> None:
        """Stop monitoring a specific session."""
        pass
    
    @abstractmethod
    async def get_metrics(self, session_id: str) -> ResourceMetrics:
        """Get current metrics for a session."""
        pass
    
    @abstractmethod
    async def check_thresholds(self, session_id: str) -> AlertStatus:
        """Check if resource thresholds are exceeded."""
        pass
    
    @abstractmethod
    async def trigger_cleanup(self, session_id: str, level: CleanupLevel) -> bool:
        """Trigger resource cleanup at specified level."""
        pass
```

### IStateManager

Interface for browser state persistence.

```python
class IStateManager(ABC):
    """Browser state management interface."""
    
    @abstractmethod
    async def save_state(self, session: BrowserSession, state_id: Optional[str] = None) -> str:
        """Save browser state to storage."""
        pass
    
    @abstractmethod
    async def load_state(self, state_id: str) -> Optional[BrowserState]:
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
```

## Event Contracts

### Browser Lifecycle Events

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any

class BrowserEventType(Enum):
    SESSION_CREATED = "session_created"
    SESSION_TERMINATED = "session_terminated"
    CONTEXT_CREATED = "context_created"
    CONTEXT_CLOSED = "context_closed"
    RESOURCE_THRESHOLD_EXCEEDED = "resource_threshold_exceeded"
    CLEANUP_TRIGGERED = "cleanup_triggered"
    STATE_SAVED = "state_saved"
    STATE_RESTORED = "state_restored"
    ERROR_OCCURRED = "error_occurred"

@dataclass
class BrowserEvent:
    """Browser lifecycle event."""
    event_type: BrowserEventType
    session_id: str
    context_id: Optional[str] = None
    timestamp: datetime = None
    data: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
```

## Configuration Contracts

### Browser Configuration Schema

```python
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

@dataclass
class ViewportSettings:
    width: int = 1920
    height: int = 1080
    device_scale_factor: float = 1.0
    is_mobile: bool = False
    has_touch: bool = False

@dataclass
class ProxySettings:
    server: str
    username: Optional[str] = None
    password: Optional[str] = None
    bypass_list: List[str] = None

@dataclass
class StealthSettings:
    fingerprint_randomization: bool = True
    mouse_movement_simulation: bool = True
    typing_simulation: bool = True
    scroll_simulation: bool = True
    timing_randomization: bool = True

@dataclass
class BrowserConfiguration:
    config_id: str
    browser_type: str = "chromium"
    headless: bool = True
    viewport: ViewportSettings = None
    user_agent: Optional[str] = None
    proxy_settings: Optional[ProxySettings] = None
    stealth_settings: StealthSettings = None
    permissions: List[str] = None
    ignore_https_errors: bool = False
    locale: str = "en-US"
    timezone: str = "America/New_York"
```

## Error Handling Contracts

### Exception Hierarchy

```python
class BrowserLifecycleError(Exception):
    """Base exception for browser lifecycle errors."""
    pass

class SessionCreationError(BrowserLifecycleError):
    """Failed to create browser session."""
    pass

class ContextCreationError(BrowserLifecycleError):
    """Failed to create browser context."""
    pass

class ResourceExhaustionError(BrowserLifecycleError):
    """System resources exhausted."""
    pass

class StateCorruptionError(BrowserLifecycleError):
    """Browser state data corrupted."""
    pass

class ConfigurationError(BrowserLifecycleError):
    """Invalid browser configuration."""
    pass

class CleanupError(BrowserLifecycleError):
    """Failed to cleanup resources."""
    pass
```

## Integration Contracts

### Selector Engine Integration

```python
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
```

### Observability Integration

```python
class IEventEmitter(ABC):
    """Emit browser lifecycle events."""
    
    @abstractmethod
    async def emit_event(self, event: BrowserEvent) -> None:
        """Emit a browser lifecycle event."""
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
```

## OpenAPI Specification

### REST API Endpoints (Optional - for external management)

```yaml
openapi: 3.0.0
info:
  title: Browser Lifecycle Management API
  version: 1.0.0
  description: Internal API for browser session management

paths:
  /sessions:
    post:
      summary: Create a new browser session
      requestBody:
        required: false
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/BrowserConfiguration'
      responses:
        '201':
          description: Session created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BrowserSession'
    
    get:
      summary: List browser sessions
      parameters:
        - name: status
          in: query
          schema:
            type: string
            enum: [initializing, active, closing, terminated, failed]
      responses:
        '200':
          description: List of sessions
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/BrowserSession'

  /sessions/{session_id}:
    get:
      summary: Get specific session
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Session details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BrowserSession'
        '404':
          description: Session not found
    
    delete:
      summary: Terminate session
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Session terminated
        '404':
          description: Session not found

components:
  schemas:
    BrowserSession:
      type: object
      properties:
        session_id:
          type: string
        browser_type:
          type: string
        status:
          type: string
          enum: [initializing, active, closing, terminated, failed]
        created_at:
          type: string
          format: date-time
        last_activity:
          type: string
          format: date-time
        resource_metrics:
          $ref: '#/components/schemas/ResourceMetrics'
    
    ResourceMetrics:
      type: object
      properties:
        memory_usage_mb:
          type: number
        cpu_usage_percent:
          type: number
        disk_usage_mb:
          type: number
        alert_status:
          type: string
          enum: [normal, warning, critical]
```

## Contract Validation

All interfaces include:
- Type hints for static analysis
- Comprehensive docstrings
- Error handling specifications
- Performance expectations
- Thread safety guarantees

## Versioning Strategy

- Interface versioning through namespace separation
- Backward compatibility maintained for minor versions
- Breaking changes require major version increment
- Migration guides provided for interface changes
