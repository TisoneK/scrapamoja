# Data Model: Consolidate Retry Logic

**Feature**: [013-consolidate-retry-logic](spec.md)  
**Date**: 2026-01-29  
**Phase**: 1 - Design & Architecture

## Overview

This document defines the data models for retry policies, configurations, and events used in the centralized retry consolidation. The models are designed to be technology-agnostic, focusing on the data structures and relationships rather than implementation details.

## Core Data Models

### 1. Retry Policy

**Purpose**: Defines retry behavior for a specific operation or subsystem.

**Fields**:
- `id` (string, required): Unique identifier for the retry policy
- `name` (string, required): Human-readable name for the policy
- `description` (string, optional): Description of when and why to use this policy
- `max_attempts` (integer, required): Maximum number of retry attempts (including initial attempt)
- `backoff_type` (enum, required): Type of backoff strategy to use
  - Values: `exponential`, `linear`, `fixed`, `immediate`
- `base_delay` (float, required): Base delay in seconds before first retry
- `max_delay` (float, required): Maximum delay in seconds (caps backoff calculation)
- `jitter_type` (enum, optional): Type of jitter to apply to delays
  - Values: `none`, `full`, `decorrelated`, `equal`
  - Default: `none`
- `jitter_amount` (float, optional): Amount of jitter to apply (0.0-1.0)
  - Default: `0.1`
- `enable_circuit_breaker` (boolean, optional): Whether to enable circuit breaker
  - Default: `false`
- `circuit_breaker_threshold` (integer, optional): Number of failures before opening circuit
  - Default: `5`
- `circuit_breaker_timeout` (float, optional): Time in seconds before attempting to close circuit
  - Default: `60.0`
- `retryable_exceptions` (array of strings, optional): List of exception types that should trigger retry
  - Default: All transient exceptions
- `enabled` (boolean, required): Whether the policy is active
  - Default: `true`

**Example**:
```json
{
  "id": "browser_state_timeout",
  "name": "Browser State Timeout Retry",
  "description": "Retry state operations that timeout",
  "max_attempts": 3,
  "backoff_type": "exponential",
  "base_delay": 1.0,
  "max_delay": 10.0,
  "jitter_type": "full",
  "jitter_amount": 0.1,
  "enable_circuit_breaker": false,
  "retryable_exceptions": ["TimeoutError", "ConnectionError"],
  "enabled": true
}
```

### 2. Retry Configuration

**Purpose**: Top-level configuration containing all retry policies for the system.

**Fields**:
- `version` (string, required): Configuration schema version
- `policies` (object, required): Map of policy IDs to retry policies
- `subsystem_mappings` (object, required): Maps subsystem operations to policy IDs
- `global_defaults` (object, optional): Default values for all policies

**Example**:
```json
{
  "version": "1.0.0",
  "policies": {
    "browser_state_timeout": { ... },
    "browser_network_error": { ... },
    "navigation_retry_with_delay": { ... }
  },
  "subsystem_mappings": {
    "browser": {
      "state_operations": {
        "timeout": "browser_state_timeout",
        "network_error": "browser_network_error"
      }
    },
    "navigation": {
      "route_adaptation": {
        "retry_with_delay": "navigation_retry_with_delay"
      }
    }
  },
  "global_defaults": {
    "jitter_type": "full",
    "jitter_amount": 0.1,
    "enable_circuit_breaker": false
  }
}
```

### 3. Retry Attempt

**Purpose**: Represents a single retry attempt within a retry session.

**Fields**:
- `attempt_number` (integer, required): Sequential number of the attempt (1-based)
- `timestamp` (datetime, required): When the attempt was made
- `delay` (float, required): Delay in seconds before this attempt (0 for first attempt)
- `error` (object, optional): Error that occurred during this attempt
  - `type` (string): Exception type
  - `message` (string): Error message
  - `stack_trace` (string, optional): Stack trace
- `success` (boolean, required): Whether the attempt succeeded
- `duration` (float, required): Duration of the attempt in seconds
- `context` (object, optional): Additional context about the attempt

**Example**:
```json
{
  "attempt_number": 2,
  "timestamp": "2026-01-29T12:00:00.000Z",
  "delay": 1.5,
  "error": {
    "type": "TimeoutError",
    "message": "Operation timed out after 30 seconds"
  },
  "success": false,
  "duration": 30.5,
  "context": {
    "operation": "save_state",
    "state_id": "abc123"
  }
}
```

### 4. Retry Session

**Purpose**: Represents a complete retry session with all attempts.

**Fields**:
- `session_id` (string, required): Unique identifier for the session
- `policy_id` (string, required): ID of the retry policy used
- `operation` (string, required): Name of the operation being retried
- `start_time` (datetime, required): When the session started
- `end_time` (datetime, optional): When the session ended
- `attempts` (array of RetryAttempt, required): All retry attempts
- `final_result` (any, optional): Final result if successful
- `final_error` (object, optional): Final error if all attempts failed
- `success` (boolean, required): Whether the session succeeded
- `context` (object, optional): Additional context about the session

**Derived Fields**:
- `total_attempts` (integer): Total number of attempts (length of attempts array)
- `total_duration` (float): Total duration of the session in seconds
- `retry_count` (integer): Number of retry attempts (total_attempts - 1)

**Example**:
```json
{
  "session_id": "browser_state_timeout_1706534400000",
  "policy_id": "browser_state_timeout",
  "operation": "save_state",
  "start_time": "2026-01-29T12:00:00.000Z",
  "end_time": "2026-01-29T12:00:35.500Z",
  "attempts": [
    {
      "attempt_number": 1,
      "timestamp": "2026-01-29T12:00:00.000Z",
      "delay": 0.0,
      "error": {
        "type": "TimeoutError",
        "message": "Operation timed out after 30 seconds"
      },
      "success": false,
      "duration": 30.5
    },
    {
      "attempt_number": 2,
      "timestamp": "2026-01-29T12:00:32.000Z",
      "delay": 1.5,
      "success": true,
      "duration": 3.5
    }
  ],
  "final_result": {
    "state_id": "abc123",
    "saved": true
  },
  "success": true,
  "context": {
    "state_id": "abc123",
    "user_id": "user123"
  }
}
```

### 5. Retry Event

**Purpose**: Event published when a retry occurs, for monitoring and observability.

**Fields**:
- `event_id` (string, required): Unique identifier for the event
- `event_type` (string, required): Type of event
  - Values: `retry_attempt`, `retry_success`, `retry_failure`, `circuit_breaker_opened`, `circuit_breaker_closed`
- `timestamp` (datetime, required): When the event occurred
- `correlation_id` (string, required): Correlation ID for tracing
- `session_id` (string, required): ID of the retry session
- `policy_id` (string, required): ID of the retry policy
- `operation` (string, required): Name of the operation
- `attempt` (integer, optional): Attempt number (for retry_attempt events)
- `max_attempts` (integer, optional): Maximum attempts (for retry_attempt events)
- `delay` (float, optional): Delay before this attempt (for retry_attempt events)
- `error` (object, optional): Error that occurred (for retry_failure events)
- `component` (string, required): Component that generated the event
- `context` (object, optional): Additional context

**Example**:
```json
{
  "event_id": "evt_1706534400000_abc123",
  "event_type": "retry_attempt",
  "timestamp": "2026-01-29T12:00:32.000Z",
  "correlation_id": "corr_abc123",
  "session_id": "browser_state_timeout_1706534400000",
  "policy_id": "browser_state_timeout",
  "operation": "save_state",
  "attempt": 2,
  "max_attempts": 3,
  "delay": 1.5,
  "component": "retry_manager",
  "context": {
    "state_id": "abc123",
    "last_error": "TimeoutError: Operation timed out after 30 seconds"
  }
}
```

### 6. Circuit Breaker State

**Purpose**: Represents the state of a circuit breaker for a specific policy.

**Fields**:
- `policy_id` (string, required): ID of the retry policy
- `state` (enum, required): Current state of the circuit breaker
  - Values: `closed`, `open`, `half_open`
- `failure_count` (integer, required): Number of failures since last reset
- `last_failure_time` (datetime, optional): Time of the last failure
- `threshold` (integer, required): Number of failures before opening circuit
- `timeout` (float, required): Time in seconds before attempting to close circuit
- `last_state_change` (datetime, required): When the state last changed

**Example**:
```json
{
  "policy_id": "browser_state_timeout",
  "state": "closed",
  "failure_count": 2,
  "last_failure_time": "2026-01-29T12:00:00.000Z",
  "threshold": 5,
  "timeout": 60.0,
  "last_state_change": "2026-01-29T12:00:00.000Z"
}
```

### 7. Retry Metrics

**Purpose**: Aggregated metrics about retry behavior across the system.

**Fields**:
- `time_window_start` (datetime, required): Start of the time window
- `time_window_end` (datetime, required): End of the time window
- `total_sessions` (integer, required): Total number of retry sessions
- `successful_sessions` (integer, required): Number of successful sessions
- `failed_sessions` (integer, required): Number of failed sessions
- `total_attempts` (integer, required): Total number of retry attempts
- `average_attempts_per_session` (float, required): Average attempts per session
- `max_attempts_in_session` (integer, required): Maximum attempts in any session
- `total_duration` (float, required): Total duration of all sessions in seconds
- `average_duration_per_session` (float, required): Average duration per session
- `by_policy` (object, required): Metrics broken down by policy ID
  - `policy_id` (object):
    - `sessions` (integer): Number of sessions
    - `success_rate` (float): Success rate (0.0-1.0)
    - `average_attempts` (float): Average attempts per session
- `by_subsystem` (object, required): Metrics broken down by subsystem
  - `subsystem_name` (object):
    - `sessions` (integer): Number of sessions
    - `success_rate` (float): Success rate (0.0-1.0)
    - `average_attempts` (float): Average attempts per session

**Example**:
```json
{
  "time_window_start": "2026-01-29T00:00:00.000Z",
  "time_window_end": "2026-01-29T23:59:59.999Z",
  "total_sessions": 1000,
  "successful_sessions": 950,
  "failed_sessions": 50,
  "total_attempts": 1200,
  "average_attempts_per_session": 1.2,
  "max_attempts_in_session": 3,
  "total_duration": 3600.0,
  "average_duration_per_session": 3.6,
  "by_policy": {
    "browser_state_timeout": {
      "sessions": 500,
      "success_rate": 0.95,
      "average_attempts": 1.1
    },
    "navigation_retry_with_delay": {
      "sessions": 300,
      "success_rate": 0.97,
      "average_attempts": 1.3
    }
  },
  "by_subsystem": {
    "browser": {
      "sessions": 600,
      "success_rate": 0.96,
      "average_attempts": 1.15
    },
    "navigation": {
      "sessions": 300,
      "success_rate": 0.97,
      "average_attempts": 1.3
    },
    "telemetry": {
      "sessions": 100,
      "success_rate": 0.90,
      "average_attempts": 1.4
    }
  }
}
```

## Configuration Schema

### Retry Configuration File Schema

**File**: `src/config/retry_config.yaml`

**Schema Version**: 1.0.0

**Structure**:
```yaml
version: "1.0.0"

# Global defaults applied to all policies
global_defaults:
  jitter_type: "full"
  jitter_amount: 0.1
  enable_circuit_breaker: false

# Retry policies
policies:
  browser_state_timeout:
    name: "Browser State Timeout Retry"
    description: "Retry state operations that timeout"
    max_attempts: 3
    backoff_type: "exponential"
    base_delay: 1.0
    max_delay: 10.0
    retryable_exceptions:
      - "TimeoutError"
      - "ConnectionError"
    enabled: true

  browser_network_error:
    name: "Browser Network Error Retry"
    description: "Retry state operations with network errors"
    max_attempts: 5
    backoff_type: "exponential"
    base_delay: 2.0
    max_delay: 30.0
    retryable_exceptions:
      - "ConnectionError"
      - "NetworkError"
    enabled: true

  navigation_retry_with_delay:
    name: "Navigation Retry With Delay"
    description: "Retry route adaptation with delay"
    max_attempts: 3
    backoff_type: "exponential"
    base_delay: 2.0
    max_delay: 30.0
    enabled: true

  telemetry_error_handling:
    name: "Telemetry Error Handling Retry"
    description: "Retry telemetry operations with errors"
    max_attempts: 3
    backoff_type: "exponential"
    base_delay: 1.0
    max_delay: 60.0
    enabled: true

# Subsystem mappings
subsystem_mappings:
  browser:
    state_operations:
      timeout: "browser_state_timeout"
      network_error: "browser_network_error"
      disk_full: "browser_disk_full"
    monitoring_operations:
      timeout: "browser_monitoring_timeout"
      access_denied: "browser_access_denied"
      psutil_error: "browser_psutil_error"
    session_operations:
      default: "browser_session_default"

  navigation:
    route_adaptation:
      retry_with_delay: "navigation_retry_with_delay"

  telemetry:
    error_handling:
      default: "telemetry_error_handling"
    batch_processing:
      default: "telemetry_batch_processing"
    alerting:
      notification: "telemetry_alerting_notification"
    simple_retries:
      default: "telemetry_simple_retries"
```

## Data Relationships

### Entity Relationship Diagram

```
RetryConfiguration
├── contains → RetryPolicy (1..n)
│   ├── used by → RetrySession (1..n)
│   │   ├── contains → RetryAttempt (1..n)
│   │   └── generates → RetryEvent (1..n)
│   └── has → CircuitBreakerState (0..1)
└── maps → SubsystemMapping (1..n)
    └── maps to → RetryPolicy (1..n)

RetryMetrics
├── aggregates → RetrySession (0..n)
├── breaks down by → RetryPolicy (1..n)
└── breaks down by → Subsystem (1..n)
```

### Key Relationships

1. **RetryConfiguration → RetryPolicy**: One-to-many (configuration contains multiple policies)
2. **RetryPolicy → RetrySession**: One-to-many (policy used in multiple sessions)
3. **RetrySession → RetryAttempt**: One-to-many (session contains multiple attempts)
4. **RetrySession → RetryEvent**: One-to-many (session generates multiple events)
5. **RetryPolicy → CircuitBreakerState**: One-to-one (policy has optional circuit breaker)
6. **RetryMetrics → RetrySession**: One-to-many (metrics aggregate multiple sessions)
7. **SubsystemMapping → RetryPolicy**: Many-to-one (mapping points to policy)

## Data Validation Rules

### Retry Policy Validation

1. **max_attempts**: Must be >= 1
2. **base_delay**: Must be >= 0
3. **max_delay**: Must be >= base_delay
4. **jitter_amount**: Must be between 0.0 and 1.0
5. **circuit_breaker_threshold**: Must be >= 1 if circuit breaker enabled
6. **circuit_breaker_timeout**: Must be > 0 if circuit breaker enabled
7. **retryable_exceptions**: Must be valid exception type names
8. **enabled**: Must be boolean

### Retry Session Validation

1. **attempt_number**: Must be >= 1
2. **delay**: Must be >= 0
3. **duration**: Must be >= 0
4. **success**: Must be boolean
5. **attempts**: Must be non-empty array
6. **total_attempts**: Must equal length of attempts array
7. **retry_count**: Must equal total_attempts - 1

### Retry Event Validation

1. **event_type**: Must be one of valid event types
2. **timestamp**: Must be valid ISO 8601 datetime
3. **correlation_id**: Must be non-empty string
4. **attempt**: Must be >= 1 if present
5. **max_attempts**: Must be >= attempt if present
6. **delay**: Must be >= 0 if present

## Data Migration Strategy

### Phase 1: Configuration Migration

1. Create centralized retry configuration file
2. Map existing retry configurations to new schema
3. Validate configuration against schema
4. Test configuration loading

### Phase 2: Runtime Migration

1. Initialize centralized retry manager
2. Register all retry policies from configuration
3. Update subsystems to use centralized retry
4. Maintain old implementations during transition

### Phase 3: Data Migration

1. Migrate existing retry sessions to new format
2. Migrate retry events to new format
3. Migrate retry metrics to new format
4. Validate data integrity

### Phase 4: Cleanup

1. Remove old retry implementations
2. Remove deprecated configuration files
3. Update documentation
4. Archive old data

## Backward Compatibility

### Versioning

- Configuration schema version: `1.0.0`
- Data model version: `1.0.0`
- API version: `1.0.0`

### Migration Path

1. **Version 1.0.0**: Initial consolidation
2. **Version 1.1.0**: Add hot-reload support
3. **Version 2.0.0**: Breaking changes (if needed)

### Compatibility Guarantees

- Configuration files from version 1.0.0 will be supported in version 1.1.0
- Data models from version 1.0.0 will be supported in version 1.1.0
- API from version 1.0.0 will be supported in version 1.1.0

## Performance Considerations

### Data Size Estimates

- **RetryPolicy**: ~500 bytes per policy
- **RetryAttempt**: ~200 bytes per attempt
- **RetrySession**: ~1 KB per session (average 2 attempts)
- **RetryEvent**: ~300 bytes per event
- **RetryMetrics**: ~5 KB per time window

### Storage Requirements

- **Configuration**: ~10 KB (20 policies)
- **Active Sessions**: ~100 KB (100 concurrent sessions)
- **Event Log**: ~1 MB per day (10,000 events)
- **Metrics**: ~5 KB per hour (aggregated)

### Optimization Strategies

1. **Lazy Loading**: Load retry policies on demand
2. **Caching**: Cache frequently used policies
3. **Batch Processing**: Batch retry events for logging
4. **Compression**: Compress historical retry data
5. **TTL**: Set time-to-live for old sessions and events

## Security Considerations

### Data Protection

1. **Sensitive Data**: Do not log sensitive data in retry context
2. **Error Messages**: Sanitize error messages before logging
3. **Stack Traces**: Only include stack traces in debug mode
4. **Access Control**: Restrict access to retry configuration

### Audit Trail

1. **Configuration Changes**: Log all configuration changes
2. **Policy Updates**: Track who updated policies and when
3. **Session Access**: Log access to retry sessions
4. **Metrics Access**: Log access to retry metrics

## Conclusion

This data model provides a comprehensive foundation for consolidating retry logic across the browser, navigation, and telemetry subsystems. The models are designed to be flexible, extensible, and maintainable while ensuring consistency and observability across the system.

The centralized configuration approach allows for easy management of retry policies, while the detailed event and session models provide the observability needed for debugging and monitoring. The metrics model enables aggregation and analysis of retry behavior across the entire system.
