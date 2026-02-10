# Resilience API Contracts

**Feature**: 005-production-resilience  
**Date**: 2025-01-27  
**Version**: 1.0.0

## Overview

This document defines the API contracts for the Production Resilience & Reliability feature. The contracts follow deep modularity principles with clear interfaces between components.

## Core Interfaces

### ICheckpointManager

Manages checkpoint creation, validation, and recovery operations.

```python
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime

class ICheckpointManager(ABC):
    
    @abstractmethod
    async def create_checkpoint(
        self,
        job_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new checkpoint for the specified job.
        
        Args:
            job_id: Unique identifier for the scraping job
            data: Job state data to checkpoint
            metadata: Optional metadata about the checkpoint
            
        Returns:
            Checkpoint ID if successful
            
        Raises:
            CheckpointCreationError: If checkpoint creation fails
            ValidationError: If data is invalid
        """
        pass
    
    @abstractmethod
    async def load_checkpoint(
        self,
        checkpoint_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint data by ID.
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            
        Returns:
            Checkpoint data if found, None otherwise
            
        Raises:
            CheckpointCorruptionError: If checkpoint is corrupted
            ValidationError: If checkpoint format is invalid
        """
        pass
    
    @abstractmethod
    async def list_checkpoints(
        self,
        job_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List checkpoints for a job.
        
        Args:
            job_id: Unique identifier for the scraping job
            limit: Maximum number of checkpoints to return
            
        Returns:
            List of checkpoint metadata
        """
        pass
    
    @abstractmethod
    async def delete_checkpoint(
        self,
        checkpoint_id: str
    ) -> bool:
        """
        Delete a checkpoint.
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def validate_checkpoint(
        self,
        checkpoint_id: str
    ) -> bool:
        """
        Validate checkpoint integrity.
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            
        Returns:
            True if valid, False otherwise
        """
        pass
```

### IRetryManager

Handles retry logic with configurable policies and backoff strategies.

```python
class IRetryManager(ABC):
    
    @abstractmethod
    async def execute_with_retry(
        self,
        operation: callable,
        retry_policy_id: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute an operation with retry logic.
        
        Args:
            operation: The operation to execute
            retry_policy_id: ID of retry policy to use
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Result of the operation
            
        Raises:
            MaxRetriesExceededError: If all retry attempts fail
            PermanentFailureError: If failure is classified as permanent
        """
        pass
    
    @abstractmethod
    async def classify_failure(
        self,
        error: Exception
    ) -> str:
        """
        Classify a failure as transient or permanent.
        
        Args:
            error: The exception to classify
            
        Returns:
            Classification result ("transient" or "permanent")
        """
        pass
    
    @abstractmethod
    async def calculate_backoff_delay(
        self,
        attempt: int,
        retry_policy_id: str
    ) -> float:
        """
        Calculate backoff delay for retry attempt.
        
        Args:
            attempt: Current attempt number (1-based)
            retry_policy_id: ID of retry policy to use
            
        Returns:
            Delay in seconds before next retry
        """
        pass
    
    @abstractmethod
    async def create_retry_policy(
        self,
        policy_config: Dict[str, Any]
    ) -> str:
        """
        Create a new retry policy.
        
        Args:
            policy_config: Policy configuration parameters
            
        Returns:
            ID of created policy
        """
        pass
```

### IResourceMonitor

Monitors system resources and enforces configurable thresholds.

```python
class IResourceMonitor(ABC):
    
    @abstractmethod
    async def start_monitoring(
        self,
        threshold_id: str,
        callback: callable
    ) -> str:
        """
        Start resource monitoring with specified thresholds.
        
        Args:
            threshold_id: ID of resource threshold configuration
            callback: Callback function to invoke on threshold breach
            
        Returns:
            Monitoring session ID
        """
        pass
    
    @abstractmethod
    async def stop_monitoring(
        self,
        session_id: str
    ) -> bool:
        """
        Stop resource monitoring session.
        
        Args:
            session_id: Monitoring session ID
            
        Returns:
            True if stopped successfully
        """
        pass
    
    @abstractmethod
    async def get_current_metrics(
        self
    ) -> Dict[str, Any]:
        """
        Get current system resource metrics.
        
        Returns:
            Dictionary containing current metrics
        """
        pass
    
    @abstractmethod
    async def check_thresholds(
        self,
        threshold_id: str
    ) -> Dict[str, bool]:
        """
        Check if current metrics exceed specified thresholds.
        
        Args:
            threshold_id: ID of threshold configuration
            
        Returns:
            Dictionary mapping threshold names to breach status
        """
        pass
    
    @abstractmethod
    async def create_resource_threshold(
        self,
        threshold_config: Dict[str, Any]
    ) -> str:
        """
        Create a new resource threshold configuration.
        
        Args:
            threshold_config: Threshold configuration parameters
            
        Returns:
            ID of created threshold
        """
        pass
```

### IAbortManager

Manages abort policies and intelligent failure detection.

```python
class IAbortManager(ABC):
    
    @abstractmethod
    async def evaluate_abort_conditions(
        self,
        job_id: str,
        abort_policy_id: str
    ) -> Dict[str, Any]:
        """
        Evaluate abort conditions for a job.
        
        Args:
            job_id: Unique identifier for the scraping job
            abort_policy_id: ID of abort policy to use
            
        Returns:
            Evaluation result with abort decision and reasoning
        """
        pass
    
    @abstractmethod
    async def record_failure(
        self,
        job_id: str,
        failure_event: Dict[str, Any]
    ) -> None:
        """
        Record a failure event for abort evaluation.
        
        Args:
            job_id: Unique identifier for the scraping job
            failure_event: Failure event details
        """
        pass
    
    @abstractmethod
    async def execute_abort_actions(
        self,
        job_id: str,
        abort_reason: str
    ) -> bool:
        """
        Execute abort actions for a job.
        
        Args:
            job_id: Unique identifier for the scraping job
            abort_reason: Reason for abort
            
        Returns:
            True if abort actions executed successfully
        """
        pass
    
    @abstractmethod
    async def create_abort_policy(
        self,
        policy_config: Dict[str, Any]
    ) -> str:
        """
        Create a new abort policy.
        
        Args:
            policy_config: Policy configuration parameters
            
        Returns:
            ID of created policy
        """
        pass
    
    @abstractmethod
    async def get_failure_analysis(
        self,
        job_id: str,
        time_window: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get failure analysis for a job.
        
        Args:
            job_id: Unique identifier for the scraping job
            time_window: Time window in seconds (optional)
            
        Returns:
            Failure analysis results
        """
        pass
```

### IFailureHandler

Coordinates failure handling across all resilience components.

```python
class IFailureHandler(ABC):
    
    @abstractmethod
    async def handle_failure(
        self,
        failure_event: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle a failure event with appropriate recovery actions.
        
        Args:
            failure_event: Failure event details
            context: Additional context information
            
        Returns:
            Handling result with recovery actions taken
        """
        pass
    
    @abstractmethod
    async def register_failure_handler(
        self,
        failure_type: str,
        handler: callable
    ) -> None:
        """
        Register a handler for specific failure types.
        
        Args:
            failure_type: Type of failure to handle
            handler: Handler function
        """
        pass
    
    @abstractmethod
    async def get_failure_statistics(
        self,
        job_id: Optional[str] = None,
        time_range: Optional[Dict[str, datetime]] = None
    ) -> Dict[str, Any]:
        """
        Get failure statistics.
        
        Args:
            job_id: Optional job identifier filter
            time_range: Optional time range filter
            
        Returns:
            Failure statistics
        """
        pass
```

## Event Contracts

### ResilienceEvent

Base event structure for all resilience-related events.

```python
class ResilienceEvent:
    event_type: str           # Type of event
    timestamp: datetime       # Event timestamp
    job_id: str              # Associated job ID
    component: str           # Component that generated the event
    severity: str           # Event severity (info, warning, error, critical)
    data: Dict[str, Any]    # Event-specific data
    correlation_id: str      # Correlation ID for tracing
```

### Event Types

#### Checkpoint Events
- `checkpoint_created`: Checkpoint successfully created
- `checkpoint_loaded`: Checkpoint successfully loaded
- `checkpoint_corrupted`: Checkpoint corruption detected
- `checkpoint_deleted`: Checkpoint deleted

#### Retry Events
- `retry_attempted`: Retry attempt initiated
- `retry_succeeded`: Retry attempt succeeded
- `retry_exhausted`: All retry attempts exhausted
- `permanent_failure`: Permanent failure detected

#### Resource Events
- `threshold_breached`: Resource threshold breached
- `threshold_recovered`: Resource usage returned to normal
- `cleanup_initiated`: Resource cleanup initiated
- `browser_restarted`: Browser restarted due to resource issues

#### Abort Events
- `abort_evaluated`: Abort conditions evaluated
- `abort_triggered`: Abort conditions triggered
- `abort_executed`: Abort actions executed
- `failure_pattern_detected`: Failure pattern detected

## Configuration Contracts

### ResilienceConfiguration

Main configuration structure for resilience features.

```python
class ResilienceConfiguration:
    checkpoint: CheckpointConfiguration
    retry: RetryConfiguration
    resource: ResourceConfiguration
    abort: AbortConfiguration
    logging: LoggingConfiguration
```

### CheckpointConfiguration
```python
class CheckpointConfiguration:
    enabled: bool
    interval: int                    # Checkpoint interval in seconds
    retention_count: int            # Number of checkpoints to retain
    compression_enabled: bool       # Enable gzip compression
    encryption_enabled: bool        # Enable encryption for sensitive data
    storage_path: str              # Checkpoint storage directory
    validation_enabled: bool       # Enable checksum validation
```

### RetryConfiguration
```python
class RetryConfiguration:
    enabled: bool
    default_policy: str            # Default retry policy ID
    max_concurrent_retries: int     # Maximum concurrent retry operations
    jitter_enabled: bool           # Enable jitter in backoff calculations
    failure_classification_enabled: bool  # Enable failure classification
```

### ResourceConfiguration
```python
class ResourceConfiguration:
    enabled: bool
    monitoring_interval: int        # Monitoring interval in seconds
    default_threshold: str         # Default resource threshold ID
    auto_cleanup_enabled: bool      # Enable automatic cleanup
    browser_restart_enabled: bool  # Enable automatic browser restart
    memory_limit_mb: int          # Memory limit in MB
    cpu_limit_percent: float       # CPU limit percentage
```

### AbortConfiguration
```python
class AbortConfiguration:
    enabled: bool
    default_policy: str           # Default abort policy ID
    evaluation_interval: int       # Evaluation interval in seconds
    min_operations_before_eval: int  # Minimum operations before evaluation
    abort_notification_enabled: bool  # Enable abort notifications
```

## Error Contracts

### ResilienceException

Base exception for all resilience-related errors.

```python
class ResilienceException(Exception):
    error_code: str
    message: str
    context: Dict[str, Any]
    timestamp: datetime
    correlation_id: str
```

### Specific Exceptions

#### Checkpoint Exceptions
- `CheckpointCreationError`: Checkpoint creation failed
- `CheckpointCorruptionError`: Checkpoint corruption detected
- `CheckpointNotFoundError`: Checkpoint not found
- `CheckpointValidationError`: Checkpoint validation failed

#### Retry Exceptions
- `MaxRetriesExceededError`: Maximum retry attempts exceeded
- `PermanentFailureError`: Permanent failure detected
- `RetryPolicyNotFoundError`: Retry policy not found
- `RetryConfigurationError`: Retry configuration error

#### Resource Exceptions
- `ResourceThresholdExceededError`: Resource threshold exceeded
- `ResourceMonitoringError`: Resource monitoring failed
- `ResourceCleanupError`: Resource cleanup failed
- `ResourceThresholdNotFoundError`: Resource threshold not found

#### Abort Exceptions
- `AbortPolicyNotFoundError`: Abort policy not found
- `AbortExecutionError`: Abort execution failed
- `AbortConfigurationError`: Abort configuration error

## Integration Contracts

### BrowserLifecycleIntegration

Integration points with existing browser lifecycle management.

```python
class IBrowserLifecycleIntegration:
    
    @abstractmethod
    async def on_browser_restart_required(
        self,
        reason: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Handle browser restart request from resilience system.
        
        Args:
            reason: Reason for restart request
            context: Additional context information
            
        Returns:
            True if restart initiated successfully
        """
        pass
    
    @abstractmethod
    async def get_browser_state(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Get current browser state for checkpointing.
        
        Args:
            session_id: Browser session ID
            
        Returns:
            Browser state data
        """
        pass
    
    @abstractmethod
    async def restore_browser_state(
        self,
        session_id: str,
        state: Dict[str, Any]
    ) -> bool:
        """
        Restore browser state from checkpoint.
        
        Args:
            session_id: Browser session ID
            state: Browser state data
            
        Returns:
            True if state restored successfully
        """
        pass
```

### LoggingIntegration

Integration points with existing structured logging system.

```python
class ILoggingIntegration:
    
    @abstractmethod
    async def log_resilience_event(
        self,
        event: ResilienceEvent
    ) -> None:
        """
        Log a resilience event with correlation ID.
        
        Args:
            event: Resilience event to log
        """
        pass
    
    @abstractmethod
    async def log_failure_event(
        self,
        failure_event: Dict[str, Any]
    ) -> None:
        """
        Log a failure event with detailed context.
        
        Args:
            failure_event: Failure event details
        """
        pass
    
    @abstractmethod
    async def log_recovery_event(
        self,
        recovery_event: Dict[str, Any]
    ) -> None:
        """
        Log a recovery event.
        
        Args:
            recovery_event: Recovery event details
        """
        pass
```

These contracts provide clear interfaces for implementing all resilience features while maintaining deep modularity and enabling independent testing of components.
