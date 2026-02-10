# API Contracts: Snapshot Timing and Telemetry Fixes

**Purpose**: API contracts and interfaces for snapshot timing fixes
**Created**: 2025-01-29
**Feature**: 014-snapshot-timing-fix

## Core Interfaces

### ISnapshotManager

Interface for snapshot management with timing-aware persistence.

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime

class ISnapshotManager(ABC):
    """Interface for snapshot management with timing guarantees"""
    
    @abstractmethod
    async def capture(
        self,
        page,
        snapshot_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Snapshot:
        """
        Capture a complete page snapshot with synchronous JSON persistence.
        
        Args:
            page: Playwright page object
            snapshot_id: Optional snapshot identifier
            config: Optional capture configuration
            
        Returns:
            Snapshot: Complete snapshot with guaranteed JSON availability
            
        Raises:
            SnapshotCaptureError: If capture fails
            PersistenceError: If JSON persistence fails
        """
        pass
    
    @abstractmethod
    async def persist(self, snapshot: Snapshot) -> bool:
        """
        Persist snapshot metadata to JSON file.
        
        Args:
            snapshot: Snapshot to persist
            
        Returns:
            bool: True if persistence successful
            
        Raises:
            PersistenceError: If persistence fails
        """
        pass
    
    @abstractmethod
    def is_persisted(self, snapshot: Snapshot) -> bool:
        """
        Check if snapshot JSON is persisted and accessible.
        
        Args:
            snapshot: Snapshot to check
            
        Returns:
            bool: True if JSON file exists and is readable
        """
        pass
    
    @abstractmethod
    async def load(self, snapshot_id: str) -> Optional[Snapshot]:
        """
        Load a snapshot from persisted JSON.
        
        Args:
            snapshot_id: ID of snapshot to load
            
        Returns:
            Optional[Snapshot]: Loaded snapshot or None if not found
        """
        pass
```

### IBrowserLifecycleExample

Interface for browser lifecycle example with telemetry support.

```python
class IBrowserLifecycleExample(ABC):
    """Interface for browser lifecycle example execution"""
    
    @abstractmethod
    async def run(self) -> bool:
        """
        Execute the complete browser lifecycle example.
        
        Returns:
            bool: True if execution successful
            
        Raises:
            BrowserLifecycleError: If execution fails
        """
        pass
    
    @abstractmethod
    def get_telemetry_summary(self) -> Dict[str, Any]:
        """
        Get telemetry summary for the execution.
        
        Returns:
            Dict[str, Any]: Telemetry summary data
        """
        pass
    
    @abstractmethod
    def has_telemetry_support(self) -> bool:
        """
        Check if telemetry display is supported.
        
        Returns:
            bool: True if telemetry display is available
        """
        pass
```

## Data Contracts

### Snapshot JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Snapshot Metadata",
  "description": "Snapshot metadata with timing information",
  "type": "object",
  "required": [
    "id",
    "timestamp",
    "url",
    "html_path",
    "screenshot_path",
    "json_path",
    "title",
    "page_id",
    "session_id",
    "capture_duration_ms",
    "html_capture_time",
    "screenshot_capture_time",
    "json_persistence_time",
    "browser_type",
    "viewport",
    "user_agent",
    "checksum",
    "file_sizes"
  ],
  "properties": {
    "id": {
      "type": "string",
      "description": "Unique snapshot identifier"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "Snapshot capture timestamp (UTC)"
    },
    "url": {
      "type": "string",
      "format": "uri",
      "description": "Page URL that was captured"
    },
    "html_path": {
      "type": "string",
      "description": "Path to HTML content file"
    },
    "screenshot_path": {
      "type": "string",
      "description": "Path to screenshot image file"
    },
    "json_path": {
      "type": "string",
      "description": "Path to JSON metadata file"
    },
    "title": {
      "type": "string",
      "description": "Page title"
    },
    "page_id": {
      "type": "string",
      "description": "Page identifier for tracking"
    },
    "session_id": {
      "type": "string",
      "description": "Browser session identifier"
    },
    "capture_duration_ms": {
      "type": "integer",
      "minimum": 0,
      "description": "Total capture duration in milliseconds"
    },
    "html_capture_time": {
      "type": "string",
      "format": "date-time",
      "description": "HTML capture completion time"
    },
    "screenshot_capture_time": {
      "type": "string",
      "format": "date-time",
      "description": "Screenshot capture completion time"
    },
    "json_persistence_time": {
      "type": "string",
      "format": "date-time",
      "description": "JSON persistence completion time"
    },
    "browser_type": {
      "type": "string",
      "enum": ["chromium", "firefox", "webkit"],
      "description": "Browser type used for capture"
    },
    "viewport": {
      "$ref": "#/definitions/ViewportDimensions"
    },
    "user_agent": {
      "type": "string",
      "description": "Browser user agent string"
    },
    "checksum": {
      "type": "string",
      "description": "Content checksum for integrity verification"
    },
    "file_sizes": {
      "type": "object",
      "required": ["html", "screenshot", "json"],
      "properties": {
        "html": {
          "type": "integer",
          "minimum": 0,
          "description": "HTML file size in bytes"
        },
        "screenshot": {
          "type": "integer",
          "minimum": 0,
          "description": "Screenshot file size in bytes"
        },
        "json": {
          "type": "integer",
          "minimum": 0,
          "description": "JSON file size in bytes"
        }
      }
    }
  },
  "definitions": {
    "ViewportDimensions": {
      "type": "object",
      "required": ["width", "height"],
      "properties": {
        "width": {
          "type": "integer",
          "minimum": 1,
          "description": "Viewport width in pixels"
        },
        "height": {
          "type": "integer",
          "minimum": 1,
          "description": "Viewport height in pixels"
        }
      }
    }
  }
}
```

### Telemetry Operation Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Telemetry Operation",
  "description": "Telemetry operation data for browser lifecycle",
  "type": "object",
  "required": [
    "operation_id",
    "operation_type",
    "timestamp",
    "duration_ms",
    "success",
    "element_purpose",
    "strategies_used",
    "selected_strategy",
    "retry_count"
  ],
  "properties": {
    "operation_id": {
      "type": "string",
      "description": "Unique operation identifier"
    },
    "operation_type": {
      "type": "string",
      "enum": ["locate_element", "interact_element", "navigate", "capture_snapshot"],
      "description": "Type of operation performed"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "Operation timestamp (UTC)"
    },
    "duration_ms": {
      "type": "integer",
      "minimum": 0,
      "description": "Operation duration in milliseconds"
    },
    "success": {
      "type": "boolean",
      "description": "Whether operation was successful"
    },
    "confidence_score": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Confidence score for selector operations"
    },
    "element_purpose": {
      "type": "string",
      "description": "Purpose of the element being operated on"
    },
    "strategies_used": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "List of strategies attempted"
    },
    "selected_strategy": {
      "type": "string",
      "description": "Strategy that succeeded"
    },
    "error_message": {
      "type": ["string", "null"],
      "description": "Error message if operation failed"
    },
    "retry_count": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of retry attempts"
    }
  }
}
```

## Error Contracts

### Snapshot Errors

```python
class SnapshotError(Exception):
    """Base exception for snapshot operations"""
    pass

class SnapshotCaptureError(SnapshotError):
    """Exception raised when snapshot capture fails"""
    
    def __init__(self, message: str, operation_id: str = None, duration_ms: int = None):
        super().__init__(message)
        self.operation_id = operation_id
        self.duration_ms = duration_ms

class PersistenceError(SnapshotError):
    """Exception raised when JSON persistence fails"""
    
    def __init__(self, message: str, snapshot_id: str = None, file_path: str = None):
        super().__init__(message)
        self.snapshot_id = snapshot_id
        self.file_path = file_path

class IntegrityError(SnapshotError):
    """Exception raised when snapshot integrity check fails"""
    
    def __init__(self, message: str, snapshot_id: str = None, checksum_mismatch: bool = False):
        super().__init__(message)
        self.snapshot_id = snapshot_id
        self.checksum_mismatch = checksum_mismatch
```

### Browser Lifecycle Errors

```python
class BrowserLifecycleError(Exception):
    """Base exception for browser lifecycle operations"""
    pass

class TelemetryError(BrowserLifecycleError):
    """Exception raised when telemetry operations fail"""
    
    def __init__(self, message: str, operation_type: str = None):
        super().__init__(message)
        self.operation_type = operation_type
```

## Service Level Agreements

### Snapshot Capture SLA

| Metric | Target | Measurement | Penalty |
|--------|--------|-------------|---------|
| Capture Success Rate | ≥ 99.5% | Successful captures / Total attempts | Alert on degradation |
| JSON Persistence Time | ≤ 50ms | Time from capture start to JSON file available | Performance monitoring |
| Total Capture Time | ≤ 5s | End-to-end capture duration | Timeout handling |
| File Integrity | 100% | Checksum validation passes | Error logging |

### Telemetry SLA

| Metric | Target | Measurement | Penalty |
|--------|--------|-------------|---------|
| Telemetry Availability | ≥ 99% | Successful telemetry collection | Graceful degradation |
| Operation Logging | ≤ 10ms overhead | Additional time for logging | Performance monitoring |
| Data Accuracy | 100% | Logged data matches actual operations | Validation checks |

## Integration Contracts

### Storage Backend Contract

```python
class IStorageBackend(ABC):
    """Contract for snapshot storage operations"""
    
    @abstractmethod
    async def write_json(self, file_path: str, data: Dict[str, Any]) -> bool:
        """Write data to JSON file atomically"""
        pass
    
    @abstractmethod
    async def read_json(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Read data from JSON file"""
        pass
    
    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """Check if file exists"""
        pass
    
    @abstractmethod
    async def get_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        pass
```

### Browser Integration Contract

```python
class IBrowserProvider(ABC):
    """Contract for browser operations"""
    
    @abstractmethod
    async def get_content(self, page) -> str:
        """Get page HTML content"""
        pass
    
    @abstractmethod
    async def get_screenshot(self, page, file_path: str) -> str:
        """Capture page screenshot"""
        pass
    
    @abstractmethod
    def get_viewport(self, page) -> ViewportDimensions:
        """Get current viewport dimensions"""
        pass
    
    @abstractmethod
    def get_user_agent(self, page) -> str:
        """Get browser user agent"""
        pass
```
