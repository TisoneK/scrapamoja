# Data Model: Production Resilience & Reliability

**Feature**: 005-production-resilience  
**Date**: 2025-01-27  
**Status**: Complete

## Overview

This document defines the core data entities for the Production Resilience & Reliability feature. All entities follow deep modularity principles with single responsibilities and clear validation rules.

## Core Entities

### Checkpoint

Represents a saved state of scraping progress with metadata, timestamps, and completion status.

```python
class Checkpoint:
    id: str                    # Unique checkpoint identifier (UUID)
    job_id: str               # Associated scraping job identifier
    timestamp: datetime       # Checkpoint creation timestamp
    sequence_number: int      # Sequential checkpoint number for job
    status: CheckpointStatus  # Current checkpoint status
    metadata: CheckpointMetadata  # Additional metadata
    data: CheckpointData      # Actual checkpoint data
    checksum: str            # SHA-256 checksum for integrity
    version: str             # Schema version for compatibility
```

#### CheckpointStatus Enum
- `ACTIVE`: Currently being used for recovery
- `COMPLETED`: Successfully created and validated
- `CORRUPTED`: Failed integrity validation
- `EXPIRED`: Past retention period

#### CheckpointMetadata
```python
class CheckpointMetadata:
    total_items: int         # Total items in scraping job
    completed_items: int     # Number of completed items
    failed_items: int        # Number of failed items
    processing_time: float   # Total processing time in seconds
    browser_sessions: List[str]  # Active browser session IDs
    system_resources: ResourceSnapshot  # Resource usage at checkpoint
```

#### CheckpointData
```python
class CheckpointData:
    job_state: Dict[str, Any]      # Job-specific state data
    browser_state: Dict[str, Any]  # Browser session state
    progress: ProgressState       # Detailed progress information
    errors: List[ErrorRecord]     # Error history since last checkpoint
```

### RetryPolicy

Defines retry behavior including max attempts, backoff strategy, and failure classification.

```python
class RetryPolicy:
    id: str                   # Unique policy identifier
    name: str                # Human-readable policy name
    max_attempts: int        # Maximum retry attempts
    base_delay: float        # Base delay in seconds
    multiplier: float        # Backoff multiplier
    max_delay: float         # Maximum delay in seconds
    jitter_factor: float     # Jitter variation factor (0.0-1.0)
    failure_classifier: FailureClassifier  # Failure classification rules
    created_at: datetime     # Policy creation timestamp
    updated_at: datetime     # Last update timestamp
```

#### FailureClassifier
```python
class FailureClassifier:
    transient_patterns: List[str]     # Regex patterns for transient failures
    permanent_patterns: List[str]    # Regex patterns for permanent failures
    retryable_status_codes: List[int]  # HTTP status codes to retry
    non_retryable_status_codes: List[int]  # HTTP status codes to not retry
```

### ResourceThreshold

Configurable limits for memory usage, browser lifetime, and failure rates.

```python
class ResourceThreshold:
    id: str                   # Unique threshold identifier
    name: str                # Human-readable threshold name
    memory_percent: float    # Memory usage percentage threshold
    memory_absolute: int     # Memory usage absolute threshold (MB)
    cpu_percent: float       # CPU usage percentage threshold
    browser_lifetime: int    # Maximum browser lifetime (seconds)
    disk_space: int          # Minimum required disk space (MB)
    network_connections: int # Maximum network connections
    created_at: datetime     # Threshold creation timestamp
    is_active: bool          # Whether threshold is currently active
```

### FailureEvent

Captures detailed information about failures including context, stack traces, and recovery actions.

```python
class FailureEvent:
    id: str                   # Unique event identifier
    timestamp: datetime      # Failure occurrence timestamp
    severity: FailureSeverity  # Event severity level
    category: FailureCategory   # Type of failure
    source: str             # Source component or module
    message: str            # Human-readable error message
    context: Dict[str, Any] # Additional context information
    stack_trace: str        # Stack trace (if applicable)
    recovery_action: RecoveryAction  # Recovery action taken
    resolution_time: float  # Time to resolution (seconds)
    correlation_id: str     # Correlation ID for tracing
```

#### FailureSeverity Enum
- `LOW`: Minor issue with minimal impact
- `MEDIUM`: Significant issue affecting partial functionality
- `HIGH`: Critical issue affecting major functionality
- `CRITICAL`: System-wide failure requiring immediate attention

#### FailureCategory Enum
- `NETWORK`: Network-related failures
- `BROWSER`: Browser automation failures
- `SYSTEM`: System resource failures
- `APPLICATION`: Application logic failures
- `EXTERNAL`: External service failures

#### RecoveryAction Enum
- `RETRY`: Automatic retry attempt
- `RESTART`: Component restart
- `SKIP': Skip failed operation
- `ABORT`: Abort entire operation
- `MANUAL`: Requires manual intervention

### AbortPolicy

Defines conditions and logic for automatic job termination based on failure patterns.

```python
class AbortPolicy:
    id: str                   # Unique policy identifier
    name: str                # Human-readable policy name
    failure_rate_threshold: float  # Failure rate percentage threshold
    window_size: int         # Sliding window size for analysis
    window_duration: int     # Time window duration (seconds)
    consecutive_crashes: int  # Maximum consecutive crashes
    min_operations: int      # Minimum operations before evaluation
    abort_actions: List[AbortAction]  # Actions to take on abort
    created_at: datetime     # Policy creation timestamp
    is_active: bool          # Whether policy is currently active
```

#### AbortAction
```python
class AbortAction:
    action_type: AbortActionType  # Type of abort action
    target: str              # Target component or system
    parameters: Dict[str, Any]  # Action-specific parameters
    timeout: int            # Action timeout (seconds)
```

#### AbortActionType Enum
- `SHUTDOWN`: Graceful system shutdown
- `NOTIFY`: Send notification
- `CLEANUP`: Perform cleanup operations
- `SAVE_STATE`: Save final state
- `LOG_EVENT`: Log abort event

## Supporting Entities

### ProgressState
```python
class ProgressState:
    current_item: str       # Currently processing item identifier
    completed_items: List[str]  # List of completed item identifiers
    failed_items: List[str]     # List of failed item identifiers
    pending_items: List[str]    # List of pending item identifiers
    total_count: int        # Total number of items
    completion_percentage: float  # Completion percentage
```

### ResourceSnapshot
```python
class ResourceSnapshot:
    timestamp: datetime     # Snapshot timestamp
    memory_usage: int       # Memory usage in MB
    cpu_usage: float        # CPU usage percentage
    disk_usage: int         # Disk usage in MB
    network_connections: int  # Number of network connections
    process_count: int     # Number of active processes
```

### ErrorRecord
```python
class ErrorRecord:
    timestamp: datetime     # Error occurrence timestamp
    item_id: str           # Associated item identifier
    error_type: str        # Error type or category
    error_message: str     # Error message
    retry_count: int       # Number of retry attempts
    resolved: bool         # Whether error was resolved
```

## Entity Relationships

```
Checkpoint (1) -> (1) CheckpointMetadata
Checkpoint (1) -> (1) CheckpointData
CheckpointData (1) -> (*) ErrorRecord
RetryPolicy (1) -> (1) FailureClassifier
FailureEvent (1) -> (1) RecoveryAction
AbortPolicy (1) -> (*) AbortAction
ResourceThreshold (1) -> (*) ResourceSnapshot
```

## Validation Rules

### Checkpoint Validation
- ID must be valid UUID
- Sequence number must be positive integer
- Checksum must be valid SHA-256 hash
- Version must follow semantic versioning
- Timestamp must be within reasonable range

### RetryPolicy Validation
- Max attempts must be between 1 and 100
- Base delay must be between 0.1 and 60 seconds
- Multiplier must be between 1.0 and 10.0
- Jitter factor must be between 0.0 and 1.0

### ResourceThreshold Validation
- Memory percentage must be between 1 and 100
- CPU percentage must be between 1 and 100
- Browser lifetime must be between 60 and 86400 seconds
- All absolute values must be positive integers

### FailureEvent Validation
- ID must be valid UUID
- Severity must be valid enum value
- Category must be valid enum value
- Resolution time must be non-negative

## State Transitions

### Checkpoint Lifecycle
```
CREATED -> VALIDATING -> COMPLETED
CREATED -> VALIDATING -> CORRUPTED
COMPLETED -> ACTIVE -> EXPIRED
CORRUPTED -> ACTIVE (fallback) -> COMPLETED
```

### FailureEvent Lifecycle
```
DETECTED -> ANALYZING -> RECOVERING
DETECTED -> ANALYZING -> ABORTED
RECOVERING -> RESOLVED
RECOVERING -> FAILED -> MANUAL_INTERVENTION
```

## Data Serialization

### JSON Schema Versioning
- Version format: "major.minor.patch"
- Backward compatibility maintained for minor version changes
- Breaking changes require major version increment
- Migration scripts provided for major version transitions

### Checkpoint File Format
```json
{
  "version": "1.0.0",
  "id": "uuid",
  "job_id": "job-identifier",
  "timestamp": "2025-01-27T15:30:00Z",
  "sequence_number": 1,
  "status": "completed",
  "metadata": { ... },
  "data": { ... },
  "checksum": "sha256-hash"
}
```

## Performance Considerations

### Memory Usage
- Checkpoint objects: <1MB per checkpoint
- Failure events: <10KB per event
- Resource snapshots: <1KB per snapshot

### I/O Operations
- Checkpoint write: <100ms for typical checkpoint
- Checkpoint read: <50ms for typical checkpoint
- Checksum validation: <10ms for typical checkpoint

### Storage Requirements
- Checkpoint retention: 10 checkpoints per job (configurable)
- Failure event retention: 1000 events per job (configurable)
- Compression: Optional gzip for large checkpoints

This data model provides the foundation for implementing all resilience features while maintaining deep modularity and clear separation of concerns.
