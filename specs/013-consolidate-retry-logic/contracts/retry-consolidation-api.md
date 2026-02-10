# API Contracts: Retry Consolidation

**Feature**: [013-consolidate-retry-logic](spec.md)  
**Date**: 2026-01-29  
**Phase**: 1 - Design & Architecture

## Overview

This document defines API contracts for integrating subsystems (browser, navigation, telemetry) with the centralized retry module at `src/resilience/retry/`. These contracts ensure consistent integration patterns and enable subsystems to leverage centralized retry functionality.

## Core API Contracts

### 1. Retry Manager Interface

**Module**: `src.resilience.retry.retry_manager`

**Purpose**: Provides centralized retry functionality with configurable policies.

#### 1.1 Initialize

**Method**: `async def initialize() -> None`

**Description**: Initializes the retry manager with default policies.

**Parameters**: None

**Returns**: None

**Raises**: None

**Usage**:
```python
retry_manager = RetryManager()
await retry_manager.initialize()
```

**Contract**:
- Must be called before any other retry manager methods
- Registers default retry policies
- Can be called multiple times (idempotent)
- Logs initialization event with correlation ID

#### 1.2 Execute with Retry

**Method**: `async def execute_with_retry(operation: Callable, retry_policy_id: str, *args, **kwargs) -> Any`

**Description**: Executes an operation with retry logic based on specified policy.

**Parameters**:
- `operation` (Callable, required): The operation to execute
- `retry_policy_id` (str, required): ID of retry policy to use
- `*args`: Positional arguments to pass to operation
- `**kwargs`: Keyword arguments to pass to operation

**Returns**: Result of the operation

**Raises**:
- `MaxRetriesExceededError`: If all retry attempts fail
- `PermanentFailureError`: If failure is classified as permanent
- `RetryConfigurationError`: If retry policy is not found or disabled

**Usage**:
```python
result = await retry_manager.execute_with_retry(
    my_operation,
    retry_policy_id="default_exponential_backoff",
    arg1="value1",
    arg2="value2"
)
```

**Contract**:
- Must initialize retry manager if not already initialized
- Must validate retry policy exists and is enabled
- Must create retry session with unique ID
- Must execute operation with retry logic based on policy
- Must log all retry attempts with correlation ID
- Must publish retry events for monitoring
- Must clean up session after completion
- Must raise appropriate exceptions for failures

#### 1.3 Classify Failure

**Method**: `async def classify_failure(error: Exception) -> str`

**Description**: Classifies a failure as transient or permanent.

**Parameters**:
- `error` (Exception, required): The exception to classify

**Returns**: Classification result ("transient" or "permanent")

**Raises**: None

**Usage**:
```python
failure_type = await retry_manager.classify_failure(error)
if failure_type == "transient":
    # Retry the operation
else:
    # Handle permanent failure
```

**Contract**:
- Must use failure classifier module
- Must return "transient" for retryable errors
- Must return "permanent" for non-retryable errors
- Must handle all exception types gracefully

#### 1.4 Calculate Backoff Delay

**Method**: `async def calculate_backoff_delay(attempt: int, retry_policy_id: str) -> float`

**Description**: Calculates backoff delay for a retry attempt.

**Parameters**:
- `attempt` (int, required): Current attempt number (1-based)
- `retry_policy_id` (str, required): ID of retry policy to use

**Returns**: Delay in seconds before next retry

**Raises**: `RetryConfigurationError`: If retry policy is not found

**Usage**:
```python
delay = await retry_manager.calculate_backoff_delay(2, "default_exponential_backoff")
await asyncio.sleep(delay)
```

**Contract**:
- Must validate retry policy exists
- Must calculate delay based on policy's backoff type
- Must apply jitter if configured
- Must cap delay at policy's max_delay
- Must return delay in seconds

#### 1.5 Create Retry Policy

**Method**: `async def create_retry_policy(policy_config: Dict[str, Any]) -> str`

**Description**: Creates a new retry policy from configuration.

**Parameters**:
- `policy_config` (Dict[str, Any], required): Policy configuration parameters

**Returns**: ID of created policy

**Raises**: `RetryConfigurationError`: If configuration is invalid

**Usage**:
```python
policy_config = {
    "id": "my_custom_policy",
    "name": "My Custom Policy",
    "max_attempts": 5,
    "backoff_type": "exponential",
    "base_delay": 2.0,
    "max_delay": 60.0,
    "enabled": True
}
policy_id = await retry_manager.create_retry_policy(policy_config)
```

**Contract**:
- Must validate all required fields are present
- Must validate field values are within acceptable ranges
- Must create RetryPolicy object from configuration
- Must register policy in policies dictionary
- Must log policy creation event
- Must return policy ID

#### 1.6 Cancel Session

**Method**: `async def cancel_session(session_id: str) -> bool`

**Description**: Cancels an active retry session.

**Parameters**:
- `session_id` (str, required): Session identifier to cancel

**Returns**: True if session was cancelled, False if not found

**Raises**: None

**Usage**:
```python
cancelled = await retry_manager.cancel_session("session_123")
if cancelled:
    print("Session cancelled successfully")
```

**Contract**:
- Must check if session exists in active sessions
- Must set session end time to current time
- Must mark session as failed
- Must remove session from active sessions
- Must log session cancellation event
- Must return True if session was found and cancelled
- Must return False if session was not found

#### 1.7 Health Check

**Method**: `async def health_check() -> Dict[str, Any]`

**Description**: Performs health check and returns status.

**Parameters**: None

**Returns**: Dictionary with health status information

**Raises**: None

**Usage**:
```python
health = await retry_manager.health_check()
print(f"Status: {health['status']}")
print(f"Active sessions: {health['active_sessions']}")
```

**Contract**:
- Must return dictionary with status information
- Must include "status" field ("healthy" or "unhealthy")
- Must include "initialized" field (boolean)
- Must include "policies_count" field (integer)
- Must include "active_sessions" field (integer)
- Must include "circuit_breakers" field (integer)

#### 1.8 Shutdown

**Method**: `async def shutdown() -> None`

**Description**: Shuts down retry manager gracefully.

**Parameters**: None

**Returns**: None

**Raises**: None

**Usage**:
```python
await retry_manager.shutdown()
```

**Contract**:
- Must cancel all active sessions
- Must set initialized flag to False
- Must log shutdown event
- Must be idempotent (can be called multiple times)

## Subsystem Integration Contracts

### 2. Browser Subsystem Integration

**Module**: `src/browser/`

**Purpose**: Integrate centralized retry into browser operations.

#### 2.1 State Error Handler Integration

**File**: `src/browser/state_error_handler.py`

**Contract**:
- Must import `RetryManager` from `src.resilience.retry.retry_manager`
- Must initialize retry manager on startup
- Must replace `_retry_save()` with centralized retry
- Must replace `_retry_load()` with centralized retry
- Must replace `_retry_delete()` with centralized retry
- Must map error types to appropriate retry policies:
  - `StateErrorType.TIMEOUT` → `browser_state_timeout`
  - `StateErrorType.NETWORK_ERROR` → `browser_network_error`
  - `StateErrorType.DISK_FULL` → `browser_disk_full`
- Must handle `MaxRetriesExceededError` appropriately
- Must maintain backward compatibility during migration
- Must log retry events with correlation ID

**Example**:
```python
from src.resilience.retry.retry_manager import RetryManager
from src.resilience.exceptions import MaxRetriesExceededError

class StateErrorHandler:
    def __init__(self):
        self.retry_manager = RetryManager()
        asyncio.create_task(self.retry_manager.initialize())
        
        # Map error types to policies
        self.retry_policy_mappings = {
            StateErrorType.TIMEOUT: "browser_state_timeout",
            StateErrorType.NETWORK_ERROR: "browser_network_error",
            StateErrorType.DISK_FULL: "browser_disk_full"
        }
    
    async def _retry_save(self, error_context: StateErrorContext, state_data: Dict[str, Any]) -> bool:
        """Retry save operation with centralized retry."""
        policy_id = self.retry_policy_mappings.get(error_context.error_type)
        
        try:
            return await self.retry_manager.execute_with_retry(
                self._perform_save,
                retry_policy_id=policy_id,
                error_context=error_context,
                state_data=state_data
            )
        except MaxRetriesExceededError as e:
            self.logger.error(
                f"Failed to save state after {e.context['attempts']} attempts",
                state_id=error_context.state_id
            )
            return False
```

#### 2.2 Monitoring Error Handler Integration

**File**: `src/browser/monitoring_error_handler.py`

**Contract**:
- Must import `RetryManager` from `src.resilience.retry.retry_manager`
- Must initialize retry manager on startup
- Must replace `_retry_metrics_collection()` with centralized retry
- Must replace `_retry_cleanup()` with centralized retry
- Must map error types to appropriate retry policies:
  - `MonitoringErrorType.TIMEOUT` → `browser_monitoring_timeout`
  - `MonitoringErrorType.ACCESS_DENIED` → `browser_access_denied`
  - `MonitoringErrorType.PSUTIL_ERROR` → `browser_psutil_error`
- Must handle `MaxRetriesExceededError` appropriately
- Must maintain backward compatibility during migration
- Must log retry events with correlation ID

#### 2.3 Browser Manager Integration

**File**: `src/browser/manager.py`

**Contract**:
- Must import `RetryManager` from `src.resilience.retry.retry_manager`
- Must initialize retry manager on startup
- Must replace session initialization retry with centralized retry
- Must replace session closure retry with centralized retry
- Must use `default_exponential_backoff` policy for session operations
- Must handle `MaxRetriesExceededError` appropriately
- Must maintain backward compatibility during migration
- Must log retry events with correlation ID

### 3. Navigation Subsystem Integration

**Module**: `src/navigation/`

**Purpose**: Integrate centralized retry into navigation operations.

#### 3.1 Route Adaptation Integration

**File**: `src/navigation/route_adaptation.py`

**Contract**:
- Must import `RetryManager` from `src.resilience.retry.retry_manager`
- Must initialize retry manager on startup
- Must replace `_retry_with_delay()` with centralized retry
- Must use `navigation_retry_with_delay` policy for route adaptation
- Must maintain retry delay multiplier logic (if needed)
- Must handle `MaxRetriesExceededError` appropriately
- Must maintain backward compatibility during migration
- Must log retry events with correlation ID

**Example**:
```python
from src.resilience.retry.retry_manager import RetryManager
from src.resilience.exceptions import MaxRetriesExceededError

class RouteAdapter:
    def __init__(self):
        self.retry_manager = RetryManager()
        asyncio.create_task(self.retry_manager.initialize())
    
    async def _retry_with_delay(self, current_plan: PathPlan, obstacle_type: str) -> PathPlan:
        """Retry current plan with centralized retry."""
        try:
            return await self.retry_manager.execute_with_retry(
                self._perform_adaptation,
                retry_policy_id="navigation_retry_with_delay",
                current_plan=current_plan,
                obstacle_type=obstacle_type
            )
        except MaxRetriesExceededError as e:
            self.logger.error(
                f"Failed to retry plan after {e.context['attempts']} attempts",
                plan_id=current_plan.plan_id
            )
            raise NavigationExecutionError(
                f"Failed to retry plan {current_plan.plan_id}",
                "RETRY_DELAY_FAILED"
            )
```

#### 3.2 Navigation Config Integration

**File**: `src/navigation/config.py`

**Contract**:
- Must remove local retry configuration parameters
- Must reference centralized retry configuration
- Must validate configuration against centralized schema
- Must provide mapping to centralized retry policies
- Must maintain backward compatibility during migration

### 4. Telemetry Subsystem Integration

**Module**: `src/telemetry/`

**Purpose**: Integrate centralized retry into telemetry operations.

#### 4.1 Error Handling Integration

**File**: `src/telemetry/error_handling.py`

**Contract**:
- Must import `RetryManager` from `src.resilience.retry.retry_manager`
- Must initialize retry manager on startup
- Must replace `RetryStrategy` class with centralized retry
- Must replace retry logic in `recover()` method with centralized retry
- Must use `telemetry_error_handling` policy for error recovery
- Must handle `MaxRetriesExceededError` appropriately
- Must maintain backward compatibility during migration
- Must log retry events with correlation ID

#### 4.2 Batch Processor Integration

**File**: `src/telemetry/processor/batch_processor.py`

**Contract**:
- Must import `RetryManager` from `src.resilience.retry.retry_manager`
- Must initialize retry manager on startup
- Must replace retry logic in `_process_events_internal()` with centralized retry
- Must use `telemetry_batch_processing` policy for batch processing
- Must handle `MaxRetriesExceededError` appropriately
- Must maintain backward compatibility during migration
- Must log retry events with correlation ID

#### 4.3 Alert Notifier Integration

**File**: `src/telemetry/alerting/notifier.py`

**Contract**:
- Must import `RetryManager` from `src.resilience.retry.retry_manager`
- Must initialize retry manager on startup
- Must replace retry logic for notification delivery with centralized retry
- Must use `telemetry_alerting_notification` policy for notifications
- Must handle `MaxRetriesExceededError` appropriately
- Must maintain backward compatibility during migration
- Must log retry events with correlation ID

#### 4.4 Simple Retry Implementations

**Files**: Multiple files in `src/telemetry/`

**Contract**:
- Must identify all simple retry implementations (sleep + retry pattern)
- Must replace with centralized retry
- Must use appropriate retry policy for each use case
- Must handle `MaxRetriesExceededError` appropriately
- Must maintain backward compatibility during migration
- Must log retry events with correlation ID

**Files to Update**:
- `storage/retention_manager.py`
- `storage/monitoring.py`
- `reporting/scheduler.py`
- `processor/aggregator.py`
- `alerting/monitor.py`
- `alerting/management.py`
- `integration/alerting_integration.py`
- `collector/buffer.py`
- `collector/event_recorder.py`
- `processor/metrics_processor.py`

## Configuration API Contracts

### 5. Configuration Loading

**Module**: `src/resilience/config/retry_config`

**Purpose**: Manages centralized retry configuration.

#### 5.1 Load Configuration

**Method**: `async def load_config(config_path: str) -> Dict[str, Any]`

**Description**: Loads retry configuration from file.

**Parameters**:
- `config_path` (str, required): Path to configuration file

**Returns**: Configuration dictionary

**Raises**: `RetryConfigurationError`: If configuration is invalid or cannot be loaded

**Contract**:
- Must validate configuration file exists
- Must parse YAML configuration
- Must validate configuration against schema
- Must validate all policy configurations
- Must validate all subsystem mappings
- Must return validated configuration
- Must log configuration loading event

#### 5.2 Reload Configuration

**Method**: `async def reload_config() -> None`

**Description**: Reloads configuration from file.

**Parameters**: None

**Returns**: None

**Raises**: `RetryConfigurationError`: If configuration is invalid

**Contract**:
- Must reload configuration from file
- Must validate new configuration
- Must update retry manager with new policies
- Must notify subsystems of configuration changes
- Must log configuration reload event
- Must complete within 5 seconds (per specification)

#### 5.3 Watch Configuration

**Method**: `async def watch_config(config_path: str, callback: Callable) -> None`

**Description**: Watches configuration file for changes and triggers callback.

**Parameters**:
- `config_path` (str, required): Path to configuration file
- `callback` (Callable, required): Callback function to invoke on changes

**Returns**: None

**Raises**: `RetryConfigurationError`: If file watching cannot be started

**Contract**:
- Must start file watcher on configuration file
- Must invoke callback on file changes
- Must debounce rapid file changes (within 1 second)
- Must handle file watcher errors gracefully
- Must log file watcher events

## Event Publishing Contracts

### 6. Retry Event Publishing

**Module**: `src/resilience/events`

**Purpose**: Publishes retry events for monitoring and observability.

#### 6.1 Publish Retry Event

**Method**: `async def publish_retry_event(operation: str, attempt: int, max_attempts: int, delay: float, job_id: Optional[str], context: Dict[str, Any], component: str) -> None`

**Description**: Publishes a retry attempt event.

**Parameters**:
- `operation` (str, required): Name of operation being retried
- `attempt` (int, required): Current attempt number
- `max_attempts` (int, required): Maximum number of attempts
- `delay` (float, required): Delay before this attempt
- `job_id` (str, optional): Job identifier for correlation
- `context` (Dict[str, Any], required): Additional context
- `component` (str, required): Component that generated the event

**Returns**: None

**Raises**: None

**Contract**:
- Must generate unique event ID
- Must include correlation ID in event
- Must include timestamp in event
- Must publish event to event bus
- Must log event with structured logging
- Must handle event publishing errors gracefully

#### 6.2 Publish Failure Event

**Method**: `async def publish_failure_event(operation: str, error: Exception, context: Dict[str, Any], component: str) -> None`

**Description**: Publishes a failure event.

**Parameters**:
- `operation` (str, required): Name of operation that failed
- `error` (Exception, required): Exception that occurred
- `context` (Dict[str, Any], required): Additional context
- `component` (str, required): Component that generated the event

**Returns**: None

**Raises**: None

**Contract**:
- Must generate unique event ID
- Must include correlation ID in event
- Must include timestamp in event
- Must include error details in event
- Must publish event to event bus
- Must log event with structured logging
- Must handle event publishing errors gracefully

## Error Handling Contracts

### 7. Exception Types

**Module**: `src/resilience/exceptions`

**Purpose**: Defines exception types for retry operations.

#### 7.1 Max Retries Exceeded Error

**Class**: `MaxRetriesExceededError(Exception)`

**Description**: Raised when all retry attempts fail.

**Attributes**:
- `message` (str): Error message
- `context` (Dict[str, Any]): Additional context including:
  - `operation` (str): Name of operation
  - `attempts` (int): Number of attempts made
  - `max_attempts` (int): Maximum attempts allowed
  - `policy_id` (str): ID of retry policy
  - `last_error` (str): Last error that occurred

**Contract**:
- Must inherit from Exception
- Must accept message and context in constructor
- Must store context in attribute
- Must provide string representation

#### 7.2 Permanent Failure Error

**Class**: `PermanentFailureError(Exception)`

**Description**: Raised when failure is classified as permanent.

**Attributes**:
- `message` (str): Error message
- `context` (Dict[str, Any]): Additional context including:
  - `operation` (str): Name of operation
  - `attempt` (int): Attempt number
  - `failure_type` (str): Type of failure
  - `error` (str): Error that occurred

**Contract**:
- Must inherit from Exception
- Must accept message and context in constructor
- Must store context in attribute
- Must provide string representation

#### 7.3 Retry Configuration Error

**Class**: `RetryConfigurationError(Exception)`

**Description**: Raised when retry configuration is invalid or not found.

**Attributes**:
- `message` (str): Error message
- `context` (Dict[str, Any]): Additional context including:
  - `policy_id` (str): ID of policy (if applicable)
  - `reason` (str): Reason for error

**Contract**:
- Must inherit from Exception
- Must accept message and context in constructor
- Must store context in attribute
- Must provide string representation

## Testing Contracts

### 8. Test Requirements

**Purpose**: Ensure subsystems work correctly with centralized retry.

#### 8.1 Unit Tests

**Contract**:
- Must test all retry manager methods
- Must test retry policy creation and validation
- Must test retry execution with various scenarios
- Must test failure classification
- Must test backoff delay calculation
- Must test session cancellation
- Must test health check
- Must test error handling

#### 8.2 Integration Tests

**Contract**:
- Must test subsystem integration with centralized retry
- Must test retry behavior matches expectations
- Must test configuration loading and reloading
- Must test event publishing
- Must test cross-subsystem consistency
- Must test backward compatibility

#### 8.3 Performance Tests

**Contract**:
- Must benchmark retry performance
- Must compare with old implementations
- Must ensure no performance degradation
- Must test under load
- Must measure memory usage

## Migration Contracts

### 9. Migration Requirements

**Purpose**: Ensure smooth migration from local to centralized retry.

#### 9.1 Feature Flags

**Contract**:
- Must implement feature flags for each subsystem
- Must allow enabling/disabling centralized retry
- Must default to old implementation initially
- Must allow gradual rollout
- Must be configurable via environment variables

#### 9.2 Backward Compatibility

**Contract**:
- Must maintain old retry implementations during transition
- Must ensure old and new implementations coexist
- Must provide migration path for existing data
- Must not break existing functionality
- Must support rollback if issues arise

#### 9.3 Monitoring and Alerting

**Contract**:
- Must monitor retry behavior after migration
- Must alert on unexpected behavior
- Must track success rates
- Must track performance metrics
- Must provide visibility into retry operations

## Compliance Contracts

### 10. Constitution Compliance

**Purpose**: Ensure retry consolidation complies with project constitution.

#### 10.1 Principle VII - Production Fault Tolerance & Resilience

**Contract**:
- Must provide exponential backoff for transient failures
- Must handle network failures gracefully
- Must not crash system on retry failures
- Must provide graceful degradation
- Must support session persistence

#### 10.2 Principle VIII - Observability & Structured Logging

**Contract**:
- Must log all retry events with structured JSON
- Must include correlation ID in all logs
- Must include performance timers
- Must enable post-mortem debugging
- Must provide visibility into retry behavior

#### 10.3 Principle II - Deep Modularity with Single Responsibility

**Contract**:
- Must ensure retry module has single responsibility
- Must not mix retry logic with other concerns
- Must provide clear public API
- Must be independently testable
- Must have comprehensive documentation

## Versioning

### 11. API Versioning

**Current Version**: 1.0.0

**Versioning Strategy**:
- **MAJOR** (X.0.0): Breaking changes to API
- **MINOR** (0.X.0): New features, backward compatible
- **PATCH** (0.0.X): Bug fixes, backward compatible

### 11.1 Version 1.0.0

**Features**:
- Core retry manager API
- Retry policy management
- Failure classification
- Backoff strategies
- Circuit breaker functionality
- Session management
- Event publishing
- Health check
- Configuration loading and reloading

**Breaking Changes**: None (initial release)

**Deprecations**: None

### 11.2 Future Versions

**Version 1.1.0** (Planned):
- Hot-reload configuration support
- Custom failure classification rules
- Enhanced metrics aggregation

**Version 2.0.0** (Future):
- Breaking changes to API (if needed)
- New retry strategies
- Advanced circuit breaker features

## Support and Maintenance

### 12. API Support

**Documentation**:
- [Quickstart Guide](../quickstart.md)
- [Data Model Documentation](../data-model.md)
- [Research Document](../research.md)
- [Implementation Plan](../plan.md)
- [Feature Specification](../spec.md)

**Contact**:
- Development team for API questions
- Issue tracker for bug reports
- Documentation for usage examples

### 12.2 Maintenance

**Updates**:
- API changes must be documented
- Deprecations must be announced
- Breaking changes must be versioned
- Migration guides must be provided

**Testing**:
- All API changes must have tests
- Integration tests must pass
- Performance tests must pass
- Code review must be completed

## Conclusion

These API contracts define the integration points between subsystems and the centralized retry module. By following these contracts, subsystems can leverage centralized retry functionality while maintaining consistency, observability, and reliability across the entire system.

The contracts ensure that:
1. All subsystems use the same retry logic
2. Retry behavior is consistent across the system
3. All retry events are logged and observable
4. Configuration is centralized and manageable
5. Migration is smooth and backward compatible
6. The system complies with project constitution
