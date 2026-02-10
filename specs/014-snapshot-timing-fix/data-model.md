# Data Model: Snapshot Timing and Telemetry Fixes

**Purpose**: Data entities and relationships for snapshot timing fixes and telemetry resolution
**Created**: 2025-01-29
**Feature**: 014-snapshot-timing-fix

## Core Entities

### Snapshot

Represents a complete page snapshot with metadata, HTML content, and screenshot.

```python
@dataclass
class Snapshot:
    """Complete page snapshot with timing-aware metadata"""
    
    # Identification
    id: str
    timestamp: datetime
    
    # Content References
    url: str
    html_path: str
    screenshot_path: str
    json_path: str
    
    # Metadata
    title: str
    page_id: str
    session_id: str
    
    # Timing Information
    capture_duration_ms: int
    html_capture_time: datetime
    screenshot_capture_time: datetime
    json_persistence_time: datetime
    
    # Technical Details
    browser_type: str
    viewport: ViewportDimensions
    user_agent: str
    
    # Integrity
    checksum: str
    file_sizes: Dict[str, int]
    
    def is_json_available(self) -> bool:
        """Check if JSON metadata file exists and is accessible"""
        return os.path.exists(self.json_path) and os.path.getsize(self.json_path) > 0
    
    def capture_age_ms(self) -> int:
        """Get age of snapshot in milliseconds"""
        return int((datetime.now(timezone.utc) - self.timestamp).total_seconds() * 1000)
```

### ViewportDimensions

Browser viewport dimensions for screenshot capture.

```python
@dataclass
class ViewportDimensions:
    """Browser viewport dimensions"""
    width: int
    height: int
    
    def area(self) -> int:
        """Calculate viewport area"""
        return self.width * self.height
    
    def is_mobile_optimized(self) -> bool:
        """Check if viewport is mobile-optimized"""
        return self.width <= 768
```

### SnapshotCaptureResult

Result of a snapshot capture operation with timing details.

```python
@dataclass
class SnapshotCaptureResult:
    """Result of snapshot capture with timing information"""
    
    # Success Status
    success: bool
    snapshot: Optional[Snapshot]
    
    # Timing Breakdown
    total_duration_ms: int
    html_capture_ms: int
    screenshot_capture_ms: int
    json_persistence_ms: int
    
    # Error Information
    error_message: Optional[str]
    error_type: Optional[str]
    
    # Performance Metrics
    html_size_bytes: int
    screenshot_size_bytes: int
    json_size_bytes: int
    
    def persistence_overhead_ms(self) -> int:
        """Calculate JSON persistence overhead"""
        return self.json_persistence_ms
    
    def capture_efficiency(self) -> float:
        """Calculate capture efficiency (content_size / time)"""
        if self.total_duration_ms == 0:
            return 0.0
        total_bytes = self.html_size_bytes + self.screenshot_size_bytes + self.json_size_bytes
        return total_bytes / self.total_duration_ms
```

### TelemetryOperation

Represents a telemetry operation in the browser lifecycle example.

```python
@dataclass
class TelemetryOperation:
    """Telemetry operation data for browser lifecycle"""
    
    # Operation Identification
    operation_id: str
    operation_type: str
    timestamp: datetime
    
    # Performance Metrics
    duration_ms: int
    success: bool
    confidence_score: Optional[float]
    
    # Context Information
    element_purpose: str
    strategies_used: List[str]
    selected_strategy: str
    
    # Error Information
    error_message: Optional[str]
    retry_count: int
    
    def is_high_confidence(self) -> bool:
        """Check if operation had high confidence"""
        return self.confidence_score is not None and self.confidence_score > 0.8
    
    def is_slow_operation(self) -> bool:
        """Check if operation was slow (>1 second)"""
        return self.duration_ms > 1000
```

## Relationships

### Snapshot Lifecycle

```
BrowserLifecycleExample
    ├── captures Snapshot
    │   ├── creates HTML file
    │   ├── creates Screenshot file
    │   └── creates JSON file (timing fix)
    ├── uses Snapshot for offline replay
    └── uses Snapshot for integrity verification
```

### Telemetry Flow

```
BrowserLifecycleExample
    ├── performs TelemetryOperations
    │   ├── selector operations
    │   ├── element interactions
    │   └── navigation operations
    └── aggregates TelemetryOperation results
```

## Validation Rules

### Snapshot Validation

```python
class SnapshotValidator:
    """Validation rules for Snapshot entities"""
    
    @staticmethod
    def validate_snapshot(snapshot: Snapshot) -> ValidationResult:
        """Validate snapshot completeness and integrity"""
        errors = []
        
        # Required fields
        if not snapshot.id:
            errors.append("Snapshot ID is required")
        if not snapshot.html_path:
            errors.append("HTML path is required")
        if not snapshot.json_path:
            errors.append("JSON path is required")
        
        # File existence
        if not os.path.exists(snapshot.html_path):
            errors.append(f"HTML file not found: {snapshot.html_path}")
        if not os.path.exists(snapshot.json_path):
            errors.append(f"JSON file not found: {snapshot.json_path}")
        
        # Timing consistency
        if snapshot.json_persistence_time < snapshot.timestamp:
            errors.append("JSON persistence time cannot be before capture time")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=[]
        )
    
    @staticmethod
    def validate_timing_consistency(snapshot: Snapshot) -> ValidationResult:
        """Validate timing consistency across capture operations"""
        errors = []
        warnings = []
        
        # Check capture order
        if snapshot.html_capture_time > snapshot.screenshot_capture_time:
            warnings.append("Screenshot captured before HTML (unusual but not invalid)")
        
        if snapshot.screenshot_capture_time > snapshot.json_persistence_time:
            errors.append("JSON persisted before screenshot capture completed")
        
        # Check total duration
        total_capture_time = (
            snapshot.json_persistence_time - snapshot.timestamp
        ).total_seconds() * 1000
        
        if total_capture_time > snapshot.capture_duration_ms + 100:  # 100ms tolerance
            warnings.append("Reported capture duration doesn't match timing data")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
```

### Telemetry Validation

```python
class TelemetryValidator:
    """Validation rules for TelemetryOperation entities"""
    
    @staticmethod
    def validate_operation(operation: TelemetryOperation) -> ValidationResult:
        """Validate telemetry operation completeness"""
        errors = []
        
        # Required fields
        if not operation.operation_id:
            errors.append("Operation ID is required")
        if not operation.operation_type:
            errors.append("Operation type is required")
        if operation.duration_ms < 0:
            errors.append("Duration cannot be negative")
        
        # Confidence score validation
        if operation.confidence_score is not None:
            if not (0.0 <= operation.confidence_score <= 1.0):
                errors.append("Confidence score must be between 0.0 and 1.0")
        
        # Retry count validation
        if operation.retry_count < 0:
            errors.append("Retry count cannot be negative")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=[]
        )
```

## State Transitions

### Snapshot States

```
INITIALIZING → CAPTURING_HTML → CAPTURING_SCREENSHOT → PERSISTING_JSON → COMPLETE
     ↓               ↓                ↓                  ↓              ↓
   Error           Error            Error             Error         Success
```

### Telemetry Operation States

```
PENDING → EXECUTING → SUCCESS/FAILED
    ↓         ↓           ↓
  Error    Timeout     Complete
```

## Data Schema Evolution

### Version 1.0 (Current)
- Basic snapshot metadata
- Timing information
- File references

### Future Considerations
- Snapshot compression metadata
- Cross-session snapshot references
- Telemetry aggregation data
- Performance benchmarking data

## Integration Points

### Storage Integration
- JSON persistence via `src/storage/adapter.py`
- File system operations for HTML and screenshots
- Atomic write operations for data integrity

### Browser Integration
- Playwright page object for content capture
- Browser session metadata injection
- Viewport and user agent detection

### Selector Engine Integration
- Telemetry operation tracking
- Strategy performance metrics
- Confidence score collection
