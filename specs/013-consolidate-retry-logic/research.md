# Research: Consolidate Retry Logic

**Feature**: [013-consolidate-retry-logic](spec.md)  
**Date**: 2026-01-29  
**Phase**: 0 - Research & Analysis

## Executive Summary

This research document catalogs all retry implementations across the browser, navigation, and telemetry subsystems, analyzes the centralized retry module capabilities, and identifies migration requirements. The analysis reveals significant code duplication with approximately 15-20 retry implementations that can be consolidated into the centralized `src/resilience/retry/` module.

## Current Retry Implementations

### 1. Browser Subsystem (`src/browser/`)

#### 1.1 Local Retry Module (`src/browser/resilience.py`)

**Purpose**: Provides retry logic, circuit breaker patterns, and graceful failure handling for browser operations.

**Components**:
- `RetryStrategy` enum: Defines retry strategies (EXPONENTIAL_BACKOFF, FIXED_DELAY, LINEAR_BACKOFF, IMMEDIATE)
- `RetryConfig` class: Configuration for retry logic with max_attempts, strategy, base_delay, max_delay, jitter, retryable_exceptions
- `RetryHandler` class: Handles retry logic with various strategies
- `ResilienceManager` class: Manages retry and circuit breaker strategies

**Usage**:
- Used in `state_error_handler.py` for state save/load/delete operations
- Used in `monitoring_error_handler.py` for metrics collection and cleanup operations
- Used in `manager.py` for session initialization and closure

**Retry Configurations**:
```python
# State Error Handler
StateErrorType.TIMEOUT: RetryConfig(max_attempts=3, strategy=EXPONENTIAL_BACKOFF, base_delay=1.0, max_delay=10.0)
StateErrorType.NETWORK_ERROR: RetryConfig(max_attempts=5, strategy=EXPONENTIAL_BACKOFF, base_delay=2.0, max_delay=30.0)
StateErrorType.DISK_FULL: RetryConfig(max_attempts=2, strategy=LINEAR_BACKOFF, base_delay=5.0, max_delay=15.0)

# Monitoring Error Handler
MonitoringErrorType.TIMEOUT: RetryConfig(max_attempts=3, strategy=EXPONENTIAL_BACKOFF, base_delay=1.0, max_delay=10.0)
MonitoringErrorType.ACCESS_DENIED: RetryConfig(max_attempts=2, strategy=LINEAR_BACKOFF, base_delay=5.0, max_delay=15.0)
MonitoringErrorType.PSUTIL_ERROR: RetryConfig(max_attempts=3, strategy=EXPONENTIAL_BACKOFF, base_delay=2.0, max_delay=20.0)

# Default Configuration
DEFAULT_RETRY_CONFIG: RetryConfig(max_attempts=3, strategy=EXPONENTIAL_BACKOFF, base_delay=1.0, max_delay=10.0)
```

**Lines of Code**: ~330 lines

**Dependencies**: structlog, asyncio

**Integration Points**:
- `state_error_handler.py`: Lines 16, 82-96, 367-417
- `monitoring_error_handler.py`: Lines 17, 74-89, 364-405
- `manager.py`: Lines 103-105, 175-177

#### 1.2 State Error Handler (`src/browser/state_error_handler.py`)

**Retry Usage**:
- `_retry_save()`: Retries state save operations with exponential backoff
- `_retry_load()`: Retries state load operations with exponential backoff
- `_retry_delete()`: Retries state delete operations

**Error Types Handled**:
- TIMEOUT: Network timeouts during state operations
- NETWORK_ERROR: Network connectivity issues
- DISK_FULL: Disk space issues

**Lines of Code**: ~50 lines of retry-specific code

#### 1.3 Monitoring Error Handler (`src/browser/monitoring_error_handler.py`)

**Retry Usage**:
- `_retry_metrics_collection()`: Retries metrics collection with exponential backoff
- `_retry_cleanup()`: Retries cleanup operations

**Error Types Handled**:
- TIMEOUT: Monitoring operation timeouts
- ACCESS_DENIED: Permission issues
- PSUTIL_ERROR: System monitoring library errors

**Lines of Code**: ~40 lines of retry-specific code

#### 1.4 Browser Manager (`src/browser/manager.py`)

**Retry Usage**:
- Session initialization with retry_config="default"
- Session closure with retry_config="default"

**Lines of Code**: ~10 lines of retry-specific code

### 2. Navigation Subsystem (`src/navigation/`)

#### 2.1 Route Adaptation (`src/navigation/route_adaptation.py`)

**Purpose**: Handles route adaptation strategies including retry with delay.

**Components**:
- `Adaptation` enum: Defines adaptation strategies (RETRY_WITH_DELAY, ALTERNATIVE_PATH, STEALTH_ENHANCEMENT, etc.)
- Custom retry logic with configurable parameters

**Retry Configuration**:
```python
max_retry_attempts = 3
retry_delay_base = 2.0
retry_delay_multiplier = 1.5
max_retry_delay = 30.0
```

**Retry Logic**:
- `_retry_with_delay()`: Implements retry with exponential backoff
- Calculates delay: `delay = retry_delay_base * (retry_delay_multiplier ** retry_count)`
- Caps delay at 30 seconds
- Resets current step for retry

**Usage**:
- Called when `Adaptation.RETRY_WITH_DELAY` strategy is selected
- Records retry events in adaptation history

**Lines of Code**: ~60 lines of retry-specific code

**Dependencies**: asyncio

**Integration Points**:
- `route_adaptation.py`: Lines 23, 51-53, 152-153, 484-540

#### 2.2 Navigation Config (`src/navigation/config.py`)

**Retry Configuration**:
```python
enable_retry_with_delay: bool = True
retry_delay_base: float = 1.0
retry_delay_multiplier: float = 1.5
max_retry_delay: float = 30.0
```

**Validation**:
- Ensures retry_delay_base > 0
- Ensures retry_delay_multiplier > 0
- Ensures max_retry_delay > 0

**Lines of Code**: ~10 lines of retry-specific code

### 3. Telemetry Subsystem (`src/telemetry/`)

#### 3.1 Error Handling (`src/telemetry/error_handling.py`)

**Purpose**: Provides error recovery strategies including retry with exponential backoff.

**Components**:
- `RetryStrategy` class: Retry recovery strategy with exponential backoff
- `ErrorContext` dataclass: Context for error handling
- `RecoveryStrategy` base class: Base for recovery strategies
- `FallbackStrategy` class: Fallback recovery strategy
- `ErrorHandler` class: Manages error handling with recovery strategies

**Retry Configuration**:
```python
class RetryStrategy(RecoveryStrategy):
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        super().__init__("retry", max_attempts)
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    async def recover(self, error: Exception, context: ErrorContext) -> bool:
        delay = min(self.base_delay * (2 ** context.retry_count), self.max_delay)
        await asyncio.sleep(delay)
        return True
```

**Retry Logic**:
- Retries for transient errors (network, connection, timeout)
- Does not retry configuration or validation errors
- Uses exponential backoff: `delay = base_delay * (2 ** retry_count)`
- Caps delay at max_delay (60 seconds)

**Usage**:
- Default recovery strategy in ErrorHandler
- Used for telemetry storage, processing, and alerting operations

**Lines of Code**: ~80 lines of retry-specific code

**Dependencies**: asyncio

**Integration Points**:
- `error_handling.py`: Lines 92-112, 162, 177-187, 272-274, 384-387

#### 3.2 Batch Processor (`src/telemetry/processor/batch_processor.py`)

**Purpose**: Processes telemetry events in batches with retry logic.

**Retry Configuration**:
```python
retry_attempts: int = 3
retry_delay: timedelta = timedelta(seconds=1)
```

**Retry Logic**:
- `_process_events_internal()`: Processes events with retry loop
- Retries up to `retry_attempts` times
- Waits `retry_delay` between attempts
- Tracks retry count in statistics

**Usage**:
- Processes telemetry events in batches
- Handles transient failures during event processing

**Lines of Code**: ~30 lines of retry-specific code

**Dependencies**: asyncio, datetime

**Integration Points**:
- `batch_processor.py`: Lines 30-31, 72, 174, 759, 924-952

#### 3.3 Alert Notifier (`src/telemetry/alerting/notifier.py`)

**Purpose**: Sends alert notifications with retry logic.

**Retry Configuration**:
```python
retry_attempts: int = 3
retry_delay_seconds: int = 60
rate_limit_per_hour: int = 10
```

**Retry Logic**:
- Simple retry mechanism for failed notifications
- Waits 60 seconds between retry attempts
- Tracks retry count in notification status

**Usage**:
- Sends alert notifications to configured channels
- Handles transient failures during notification delivery

**Lines of Code**: ~20 lines of retry-specific code

**Dependencies**: asyncio

**Integration Points**:
- `notifier.py`: Lines 44, 57-58, 86, 125, 627-628

#### 3.4 Other Retry Implementations

The telemetry subsystem has numerous simple retry implementations throughout:
- `storage/retention_manager.py`: Line 448 - Simple retry with 5-minute delay
- `storage/monitoring.py`: Line 491 - Simple retry with 10-second delay
- `reporting/scheduler.py`: Line 327 - Simple retry with 10-second delay
- `processor/aggregator.py`: Line 658 - Simple retry with 10-second delay
- `alerting/monitor.py`: Line 443 - Simple retry with 10-second delay
- `alerting/management.py`: Line 708 - Simple retry with 10-second delay
- `integration/alerting_integration.py`: Line 707 - Simple retry with 5-second delay
- `collector/buffer.py`: Line 490 - Simple retry with 1-second delay
- `collector/event_recorder.py`: Line 346 - Simple retry with 1-second delay
- `processor/metrics_processor.py`: Line 759 - Simple retry with 10-second delay

**Total Simple Retry Implementations**: ~10

**Lines of Code**: ~50 lines of retry-specific code

## Centralized Retry Module Analysis

### Module Structure (`src/resilience/retry/`)

**Components**:
- `retry_manager.py`: Main retry manager with comprehensive functionality
- `backoff_strategies.py`: Backoff strategy implementations
- `failure_classifier.py`: Failure classification logic
- `jitter.py`: Jitter calculations for retry delays
- `rate_limiter.py`: Rate limiting for retry operations

### Retry Manager Capabilities (`src/resilience/retry/retry_manager.py`)

**Core Features**:
1. **Configurable Retry Policies**:
   - Multiple predefined policies (DEFAULT_EXPONENTIAL_BACKOFF, AGGRESSIVE_RETRY, CONSERVATIVE_RETRY, LINEAR_RETRY, FIXED_RETRY)
   - Custom policy creation via `create_retry_policy()`
   - Policy management (register, retrieve, update)

2. **Backoff Strategies**:
   - Exponential backoff
   - Linear backoff
   - Fixed delay
   - Immediate retry
   - Configurable jitter

3. **Failure Classification**:
   - Automatic classification of failures as transient or permanent
   - Configurable retryable error types
   - Integration with failure classifier module

4. **Circuit Breaker**:
   - Automatic circuit breaker for failing operations
   - Configurable threshold and timeout
   - State management (closed, open, half-open)

5. **Session Management**:
   - Retry session tracking
   - Attempt-level logging
   - Session cancellation support

6. **Observability**:
   - Structured logging with correlation IDs
   - Event publishing for retry attempts
   - Health check endpoint
   - Comprehensive metrics

**API**:
```python
class RetryManager:
    async def execute_with_retry(operation, retry_policy_id, *args, **kwargs) -> Any
    async def classify_failure(error: Exception) -> str
    async def calculate_backoff_delay(attempt: int, retry_policy_id: str) -> float
    async def create_retry_policy(policy_config: Dict[str, Any]) -> str
    async def cancel_session(session_id: str) -> bool
    async def health_check() -> Dict[str, Any]
```

**Lines of Code**: ~620 lines

**Dependencies**: asyncio, time, datetime, dataclasses, structlog

### Retry Policy Model (`src/resilience/models/retry_policy.py`)

**Components**:
- `RetryPolicy` dataclass: Comprehensive retry policy configuration
- `BackoffType` enum: Backoff strategy types
- `JitterType` enum: Jitter calculation types

**Policy Configuration**:
```python
@dataclass
class RetryPolicy:
    id: str
    name: str
    max_attempts: int
    backoff_type: BackoffType
    base_delay: float
    max_delay: float
    jitter_type: JitterType
    jitter_amount: float
    enable_circuit_breaker: bool
    circuit_breaker_threshold: int
    circuit_breaker_timeout: float
    retryable_exceptions: List[Type[Exception]]
    enabled: bool
```

**Predefined Policies**:
- `DEFAULT_EXPONENTIAL_BACKOFF`: 3 attempts, exponential backoff, 1-10s delay
- `AGGRESSIVE_RETRY`: 5 attempts, exponential backoff, 0.5-5s delay
- `CONSERVATIVE_RETRY`: 2 attempts, exponential backoff, 2-20s delay
- `LINEAR_RETRY`: 3 attempts, linear backoff, 1-10s delay
- `FIXED_RETRY`: 3 attempts, fixed delay, 1s delay

**Lines of Code**: ~200 lines

### Backoff Strategies (`src/resilience/retry/backoff_strategies.py`)

**Strategies**:
- Exponential backoff with jitter
- Linear backoff with jitter
- Fixed delay with jitter
- Immediate retry

**Features**:
- Configurable base delay and max delay
- Jitter calculation to prevent thundering herd
- Strategy factory for creating strategies

**Lines of Code**: ~150 lines

### Failure Classifier (`src/resilience/failure_classifier.py`)

**Purpose**: Classifies failures as transient or permanent.

**Classification Rules**:
- Transient: TimeoutError, ConnectionError, network-related errors
- Permanent: ValueError, TypeError, configuration errors
- Configurable classification rules

**Lines of Code**: ~100 lines

## Gap Analysis

### Centralized Module Capabilities vs. Subsystem Requirements

| Requirement | Centralized Module | Subsystem Needs | Gap |
|-------------|-------------------|------------------|------|
| Exponential backoff | ✅ Supported | ✅ Required | None |
| Linear backoff | ✅ Supported | ✅ Required | None |
| Fixed delay | ✅ Supported | ✅ Required | None |
| Configurable max attempts | ✅ Supported | ✅ Required | None |
| Configurable delays | ✅ Supported | ✅ Required | None |
| Jitter | ✅ Supported | ⚠️ Not used | Optional |
| Circuit breaker | ✅ Supported | ❌ Not used | Optional |
| Failure classification | ✅ Supported | ⚠️ Partial | Minor |
| Session management | ✅ Supported | ❌ Not used | Optional |
| Event publishing | ✅ Supported | ❌ Not used | Optional |
| Health check | ✅ Supported | ❌ Not used | Optional |
| Custom retryable exceptions | ✅ Supported | ✅ Required | None |
| Hot-reload configuration | ❌ Not supported | ✅ Required | **Gap** |

### Identified Gaps

1. **Hot-Reload Configuration**: The centralized retry module does not support hot-reload of configuration changes. This is required by the specification (FR-011: "System MUST handle configuration updates without requiring subsystem restarts").

   **Solution**: Implement configuration file watching and hot-reload mechanism in the centralized retry module.

2. **Failure Classification**: Some subsystems have custom failure classification logic that may not align with the centralized module's classifier.

   **Solution**: Extend the centralized failure classifier to support custom classification rules per subsystem.

## Migration Requirements

### Backward Compatibility

**Requirements**:
1. Existing retry behavior must be preserved during migration
2. No breaking changes to subsystem APIs
3. Gradual migration with feature flags
4. Ability to rollback if issues arise

**Approach**:
1. Implement feature flags to enable/disable centralized retry per subsystem
2. Maintain old retry implementations during transition period
3. A/B testing with gradual rollout
4. Comprehensive monitoring and alerting

### Configuration Mapping

**Browser Subsystem**:
```yaml
browser:
  state_operations:
    timeout:
      max_attempts: 3
      backoff_type: exponential
      base_delay: 1.0
      max_delay: 10.0
    network_error:
      max_attempts: 5
      backoff_type: exponential
      base_delay: 2.0
      max_delay: 30.0
    disk_full:
      max_attempts: 2
      backoff_type: linear
      base_delay: 5.0
      max_delay: 15.0
  monitoring_operations:
    timeout:
      max_attempts: 3
      backoff_type: exponential
      base_delay: 1.0
      max_delay: 10.0
    access_denied:
      max_attempts: 2
      backoff_type: linear
      base_delay: 5.0
      max_delay: 15.0
    psutil_error:
      max_attempts: 3
      backoff_type: exponential
      base_delay: 2.0
      max_delay: 20.0
  session_operations:
    default:
      max_attempts: 3
      backoff_type: exponential
      base_delay: 1.0
      max_delay: 10.0
```

**Navigation Subsystem**:
```yaml
navigation:
  route_adaptation:
    retry_with_delay:
      max_attempts: 3
      backoff_type: exponential
      base_delay: 2.0
      max_delay: 30.0
      multiplier: 1.5
```

**Telemetry Subsystem**:
```yaml
telemetry:
  error_handling:
    default:
      max_attempts: 3
      backoff_type: exponential
      base_delay: 1.0
      max_delay: 60.0
  batch_processing:
    default:
      max_attempts: 3
      backoff_type: fixed
      base_delay: 1.0
      max_delay: 1.0
  alerting:
    notification:
      max_attempts: 3
      backoff_type: fixed
      base_delay: 60.0
      max_delay: 60.0
  simple_retries:
    default:
      max_attempts: 3
      backoff_type: fixed
      base_delay: 10.0
      max_delay: 10.0
```

### Dependencies and Integration Points

**Browser Subsystem**:
- `state_error_handler.py`: 3 integration points
- `monitoring_error_handler.py`: 3 integration points
- `manager.py`: 2 integration points
- Total: 8 integration points

**Navigation Subsystem**:
- `route_adaptation.py`: 4 integration points
- `config.py`: 4 integration points
- Total: 8 integration points

**Telemetry Subsystem**:
- `error_handling.py`: 6 integration points
- `batch_processor.py`: 5 integration points
- `notifier.py`: 5 integration points
- 10 simple retry implementations
- Total: 26 integration points

**Grand Total**: 42 integration points across 3 subsystems

## Code Duplication Analysis

### Lines of Code Analysis

| Subsystem | Local Retry Implementation | Lines of Code |
|-----------|-------------------------|----------------|
| Browser | `resilience.py` + handlers | ~420 lines |
| Navigation | `route_adaptation.py` + config | ~70 lines |
| Telemetry | `error_handling.py` + processors | ~180 lines |
| **Total** | | **~670 lines** |

### Duplication Percentage

- **Total retry-related code**: ~670 lines
- **Centralized module code**: ~1070 lines (including all components)
- **Code duplication**: ~670 lines (63% of total retry code)
- **Expected reduction**: ~536 lines (80% reduction target)

### Functional Overlap

| Feature | Browser | Navigation | Telemetry | Centralized |
|---------|----------|-------------|------------|-------------|
| Exponential backoff | ✅ | ✅ | ✅ | ✅ |
| Linear backoff | ✅ | ❌ | ❌ | ✅ |
| Fixed delay | ✅ | ❌ | ✅ | ✅ |
| Configurable attempts | ✅ | ✅ | ✅ | ✅ |
| Configurable delays | ✅ | ✅ | ✅ | ✅ |
| Jitter | ✅ | ❌ | ❌ | ✅ |
| Circuit breaker | ✅ | ❌ | ❌ | ✅ |
| Failure classification | ⚠️ | ❌ | ⚠️ | ✅ |
| Session management | ❌ | ❌ | ❌ | ✅ |
| Event publishing | ❌ | ❌ | ❌ | ✅ |
| Health check | ❌ | ❌ | ❌ | ✅ |

## Recommendations

### 1. Implement Hot-Reload Configuration

**Priority**: High (Required by specification)

**Approach**:
- Use `watchdog` library to monitor configuration file changes
- Implement configuration reload in `RetryManager`
- Validate new configuration before applying
- Notify subsystems of configuration changes

**Estimated Effort**: 2-3 days

### 2. Extend Failure Classifier

**Priority**: Medium (Improves alignment)

**Approach**:
- Add custom classification rules per subsystem
- Allow subsystems to register custom classifiers
- Maintain backward compatibility with existing classifier

**Estimated Effort**: 1-2 days

### 3. Gradual Migration Strategy

**Priority**: High (Ensures stability)

**Approach**:
1. Implement feature flags for each subsystem
2. Start with telemetry subsystem (lowest risk)
3. Move to navigation subsystem (medium risk)
4. Finally migrate browser subsystem (highest risk)
5. Monitor metrics and rollback if issues arise

**Estimated Effort**: 1-2 weeks

### 4. Comprehensive Testing

**Priority**: High (Ensures correctness)

**Approach**:
- Unit tests for each migration
- Integration tests for cross-subsystem consistency
- Property-based tests for retry behavior
- Performance benchmarks
- Chaos engineering tests

**Estimated Effort**: 1 week

## Conclusion

The centralized retry module at `src/resilience/retry/` is comprehensive and capable of handling all retry scenarios currently implemented in the browser, navigation, and telemetry subsystems. The primary gap is the lack of hot-reload configuration support, which must be implemented to meet the specification requirements.

The consolidation will eliminate approximately 670 lines of duplicated code (80% reduction target), ensure consistent retry behavior across all subsystems, and significantly reduce maintenance overhead. The migration should be performed gradually with feature flags and comprehensive testing to ensure stability.

## Next Steps

1. Implement hot-reload configuration mechanism in centralized retry module
2. Create centralized retry configuration file structure
3. Design migration strategy with feature flags
4. Begin gradual migration starting with telemetry subsystem
5. Monitor metrics and adjust approach as needed
