# Quickstart Guide: Centralized Retry Module

**Feature**: [013-consolidate-retry-logic](spec.md)  
**Date**: 2026-01-29  
**Phase**: 1 - Design & Architecture

## Overview

This guide provides quick reference for using the centralized retry module at `src/resilience/retry/`. It covers common use cases, configuration, and integration patterns for subsystems migrating from local retry implementations.

## Getting Started

### 1. Import the Retry Manager

```python
from src.resilience.retry.retry_manager import RetryManager
from src.resilience.models.retry_policy import RetryPolicy, BackoffType
```

### 2. Initialize the Retry Manager

```python
# Create retry manager instance
retry_manager = RetryManager()

# Initialize with default policies
await retry_manager.initialize()
```

### 3. Execute an Operation with Retry

```python
async def my_operation(arg1, arg2):
    # Your operation logic here
    return result

# Execute with retry using a predefined policy
result = await retry_manager.execute_with_retry(
    my_operation,
    retry_policy_id="default_exponential_backoff",
    arg1="value1",
    arg2="value2"
)
```

## Common Use Cases

### Use Case 1: Simple Retry with Exponential Backoff

**Scenario**: Retry an operation that may timeout or fail temporarily.

```python
from src.resilience.retry.retry_manager import RetryManager

retry_manager = RetryManager()
await retry_manager.initialize()

async def fetch_data(url):
    # Simulate network operation
    response = await http_client.get(url)
    return response.json()

# Use default exponential backoff policy
data = await retry_manager.execute_with_retry(
    fetch_data,
    retry_policy_id="default_exponential_backoff",
    url="https://api.example.com/data"
)
```

### Use Case 2: Custom Retry Policy

**Scenario**: Create a custom retry policy for specific requirements.

```python
from src.resilience.retry.retry_manager import RetryManager
from src.resilience.models.retry_policy import RetryPolicy, BackoffType, JitterType

retry_manager = RetryManager()
await retry_manager.initialize()

# Create custom policy
policy_config = {
    "id": "my_custom_policy",
    "name": "My Custom Retry Policy",
    "max_attempts": 5,
    "backoff_type": "exponential",
    "base_delay": 2.0,
    "max_delay": 60.0,
    "jitter_type": "full",
    "jitter_amount": 0.2,
    "enable_circuit_breaker": True,
    "circuit_breaker_threshold": 10,
    "circuit_breaker_timeout": 120.0,
    "retryable_exceptions": ["TimeoutError", "ConnectionError"],
    "enabled": True
}

# Register custom policy
policy_id = await retry_manager.create_retry_policy(policy_config)

# Use custom policy
result = await retry_manager.execute_with_retry(
    my_operation,
    retry_policy_id=policy_id,
    arg1="value1"
)
```

### Use Case 3: Retry with Context

**Scenario**: Pass additional context for better logging and debugging.

```python
from src.resilience.retry.retry_manager import RetryManager

retry_manager = RetryManager()
await retry_manager.initialize()

async def save_state(state_id, data):
    # Save state to disk
    with open(f"{state_id}.json", "w") as f:
        json.dump(data, f)
    return True

# Execute with context
result = await retry_manager.execute_with_retry(
    save_state,
    retry_policy_id="default_exponential_backoff",
    state_id="session_123",
    data={"user": "john", "timestamp": "2026-01-29"}
)
```

### Use Case 4: Handle Retry Errors

**Scenario**: Handle specific retry errors appropriately.

```python
from src.resilience.retry.retry_manager import RetryManager
from src.resilience.exceptions import MaxRetriesExceededError, PermanentFailureError

retry_manager = RetryManager()
await retry_manager.initialize()

try:
    result = await retry_manager.execute_with_retry(
        my_operation,
        retry_policy_id="default_exponential_backoff"
    )
except MaxRetriesExceededError as e:
    # All retry attempts failed
    print(f"Operation failed after {e.context['attempts']} attempts")
    print(f"Last error: {e.context['last_error']}")
    # Handle failure (e.g., use fallback, log error, alert)
except PermanentFailureError as e:
    # Failure is permanent, no point in retrying
    print(f"Permanent failure: {e}")
    # Handle permanent failure (e.g., skip operation, alert)
except Exception as e:
    # Unexpected error
    print(f"Unexpected error: {e}")
    # Handle unexpected error
```

### Use Case 5: Cancel Retry Session

**Scenario**: Cancel an ongoing retry session.

```python
from src.resilience.retry.retry_manager import RetryManager

retry_manager = RetryManager()
await retry_manager.initialize()

# Start retry operation in background
import asyncio
task = asyncio.create_task(
    retry_manager.execute_with_retry(
        long_running_operation,
        retry_policy_id="default_exponential_backoff"
    )
)

# Cancel after some condition
if some_condition:
    # Get session ID from task (you'll need to track this)
    session_id = get_session_id_from_task(task)
    await retry_manager.cancel_session(session_id)
    print(f"Cancelled retry session: {session_id}")
```

## Configuration

### Predefined Policies

The retry manager comes with several predefined policies:

| Policy ID | Max Attempts | Backoff Type | Base Delay | Max Delay | Use Case |
|-------------|--------------|----------------|--------------|-------------|-----------|
| `default_exponential_backoff` | 3 | Exponential | 1.0s | 10.0s | General purpose retry |
| `aggressive_retry` | 5 | Exponential | 0.5s | 5.0s | Quick retries for transient failures |
| `conservative_retry` | 2 | Exponential | 2.0s | 20.0s | Careful retries for critical operations |
| `linear_retry` | 3 | Linear | 1.0s | 10.0s | Predictable retry delays |
| `fixed_retry` | 3 | Fixed | 1.0s | 1.0s | Constant retry delay |

### Backoff Strategies

#### Exponential Backoff

Delay increases exponentially with each retry attempt.

**Formula**: `delay = min(base_delay * (2 ^ (attempt - 1)), max_delay)`

**Example**:
- Attempt 1: 0s (no delay)
- Attempt 2: 1.0s
- Attempt 3: 2.0s
- Attempt 4: 4.0s
- Attempt 5: 8.0s

**Use Case**: Network operations, API calls, database queries

#### Linear Backoff

Delay increases linearly with each retry attempt.

**Formula**: `delay = min(base_delay * (attempt - 1), max_delay)`

**Example**:
- Attempt 1: 0s (no delay)
- Attempt 2: 1.0s
- Attempt 3: 2.0s
- Attempt 4: 3.0s
- Attempt 5: 4.0s

**Use Case**: Predictable retry behavior, rate-limited operations

#### Fixed Delay

Delay remains constant for all retry attempts.

**Formula**: `delay = base_delay`

**Example**:
- Attempt 1: 0s (no delay)
- Attempt 2: 1.0s
- Attempt 3: 1.0s
- Attempt 4: 1.0s
- Attempt 5: 1.0s

**Use Case**: Simple retry logic, testing scenarios

#### Immediate Retry

No delay between retry attempts.

**Formula**: `delay = 0`

**Example**:
- Attempt 1: 0s (no delay)
- Attempt 2: 0s
- Attempt 3: 0s
- Attempt 4: 0s
- Attempt 5: 0s

**Use Case**: Very fast retries, local operations

### Jitter Types

Jitter adds randomness to retry delays to prevent thundering herd problems.

#### No Jitter

No randomness added to delays.

**Use Case**: Predictable retry behavior, testing

#### Full Jitter

Delay is randomized between 0 and calculated delay.

**Formula**: `delay = random(0, calculated_delay)`

**Use Case**: Preventing synchronized retries, distributed systems

#### Decorrelated Jitter

Delay is randomized around calculated delay.

**Formula**: `delay = random(calculated_delay / 2, calculated_delay * 1.5)`

**Use Case**: Balancing predictability and randomness

#### Equal Jitter

Delay is randomized by a fixed percentage.

**Formula**: `delay = calculated_delay * (1 + random(-jitter_amount, jitter_amount))`

**Use Case**: Controlled randomness, fine-tuned systems

## Integration Patterns

### Pattern 1: Subsystem Integration

**Scenario**: Integrate centralized retry into a subsystem.

```python
# src/browser/state_manager.py
from src.resilience.retry.retry_manager import RetryManager
from src.resilience.exceptions import MaxRetriesExceededError

class StateManager:
    def __init__(self):
        self.retry_manager = RetryManager()
        # Initialize on startup
        asyncio.create_task(self.retry_manager.initialize())
    
    async def save_state(self, state_id: str, data: dict) -> bool:
        """Save state with retry logic."""
        try:
            return await self.retry_manager.execute_with_retry(
                self._perform_save,
                retry_policy_id="browser_state_timeout",
                state_id=state_id,
                data=data
            )
        except MaxRetriesExceededError as e:
            # Handle retry failure
            self.logger.error(
                f"Failed to save state after {e.context['attempts']} attempts",
                state_id=state_id,
                last_error=str(e.context['last_error'])
            )
            return False
    
    async def _perform_save(self, state_id: str, data: dict) -> bool:
        """Actual save operation."""
        # Implementation here
        pass
```

### Pattern 2: Configuration-Based Policy Selection

**Scenario**: Select retry policy based on configuration.

```python
# src/browser/config.py
from src.resilience.retry.retry_manager import RetryManager

class BrowserConfig:
    def __init__(self, config_data: dict):
        self.retry_manager = RetryManager()
        asyncio.create_task(self.retry_manager.initialize())
        
        # Map error types to policy IDs
        self.retry_policy_mappings = {
            "timeout": config_data.get("timeout_policy", "browser_state_timeout"),
            "network_error": config_data.get("network_error_policy", "browser_network_error"),
            "disk_full": config_data.get("disk_full_policy", "browser_disk_full")
        }
    
    def get_retry_policy(self, error_type: str) -> str:
        """Get retry policy ID for error type."""
        return self.retry_policy_mappings.get(error_type, "default_exponential_backoff")
```

### Pattern 3: Feature Flag Integration

**Scenario**: Enable/disable centralized retry with feature flags.

```python
# src/browser/feature_flags.py
from src.resilience.retry.retry_manager import RetryManager

class FeatureFlags:
    def __init__(self):
        self.use_centralized_retry = os.getenv("USE_CENTRALIZED_RETRY", "true").lower() == "true"
        self.retry_manager = RetryManager()
        
        if self.use_centralized_retry:
            asyncio.create_task(self.retry_manager.initialize())
    
    async def execute_with_retry(self, operation, policy_id: str, *args, **kwargs):
        """Execute with retry based on feature flag."""
        if self.use_centralized_retry:
            return await self.retry_manager.execute_with_retry(
                operation,
                retry_policy_id=policy_id,
                *args,
                **kwargs
            )
        else:
            # Use old retry implementation
            return await self._old_retry_implementation(operation, *args, **kwargs)
```

## Migration Guide

### Step 1: Identify Retry Points

Find all places in your code that implement retry logic:

```bash
# Search for retry patterns
grep -r "retry" src/your_subsystem/
grep -r "backoff" src/your_subsystem/
grep -r "attempt" src/your_subsystem/
```

### Step 2: Map to Centralized Policies

Create a mapping from your current retry configurations to centralized policies:

```python
# Old configuration
OLD_RETRY_CONFIG = {
    "max_attempts": 3,
    "strategy": "exponential_backoff",
    "base_delay": 1.0,
    "max_delay": 10.0
}

# New mapping
RETRY_POLICY_MAPPING = {
    "timeout": "browser_state_timeout",
    "network_error": "browser_network_error"
}
```

### Step 3: Replace Retry Logic

Replace your retry logic with centralized retry:

```python
# Old code
async def save_state(state_id, data):
    for attempt in range(OLD_RETRY_CONFIG["max_attempts"]):
        try:
            return await _perform_save(state_id, data)
        except Exception as e:
            if attempt == OLD_RETRY_CONFIG["max_attempts"] - 1:
                raise
            delay = calculate_delay(attempt)
            await asyncio.sleep(delay)

# New code
async def save_state(state_id, data):
    return await retry_manager.execute_with_retry(
        _perform_save,
        retry_policy_id="browser_state_timeout",
        state_id=state_id,
        data=data
    )
```

### Step 4: Update Tests

Update your tests to use centralized retry:

```python
# Old test
async def test_save_state_with_retry():
    # Test old retry logic
    pass

# New test
async def test_save_state_with_centralized_retry():
    # Test centralized retry logic
    with patch('src.resilience.retry.retry_manager.RetryManager.execute_with_retry') as mock_retry:
        mock_retry.return_value = True
        result = await state_manager.save_state("test_id", {"data": "test"})
        assert result is True
        mock_retry.assert_called_once()
```

### Step 5: Monitor and Validate

Monitor the system after migration:

1. Check logs for retry events
2. Verify retry behavior matches expectations
3. Monitor metrics for success rates
4. Validate performance is not degraded
5. Check for any unexpected errors

## Best Practices

### 1. Choose Appropriate Backoff Strategy

- **Exponential backoff**: Use for network operations, API calls
- **Linear backoff**: Use for predictable retry behavior
- **Fixed delay**: Use for simple retry logic
- **Immediate retry**: Use for very fast retries (rare)

### 2. Set Reasonable Retry Limits

- **Transient failures**: 3-5 attempts
- **Critical operations**: 2-3 attempts
- **Non-critical operations**: 5-10 attempts
- **Avoid**: Too many retries (wastes resources)

### 3. Use Jitter for Distributed Systems

- **Prevents**: Thundering herd problem
- **Recommended**: Full jitter for distributed systems
- **Avoid**: No jitter in distributed systems

### 4. Enable Circuit Breakers for Unstable Services

- **Use**: When calling external services
- **Threshold**: 5-10 failures before opening
- **Timeout**: 60-120 seconds before closing

### 5. Log Retry Context

- **Include**: Operation name, attempt number, error
- **Add**: Correlation ID for tracing
- **Use**: Structured logging for analysis

### 6. Handle Retry Errors Appropriately

- **MaxRetriesExceededError**: Use fallback, log error
- **PermanentFailureError**: Skip operation, alert
- **Other errors**: Log and handle appropriately

### 7. Test Retry Behavior

- **Unit tests**: Test retry logic with mocked failures
- **Integration tests**: Test retry with real failures
- **Chaos tests**: Test retry under failure conditions

## Troubleshooting

### Issue: Retries Not Working

**Symptoms**: Operations fail immediately without retrying

**Possible Causes**:
1. Retry policy not found
2. Retry policy disabled
3. Exception not retryable
4. Max attempts set to 1

**Solutions**:
1. Check policy ID is correct
2. Verify policy is enabled
3. Check exception is in retryable_exceptions
4. Verify max_attempts > 1

### Issue: Too Many Retries

**Symptoms**: Operations retry many times before failing

**Possible Causes**:
1. Max attempts too high
2. Base delay too low
3. All exceptions marked as retryable

**Solutions**:
1. Reduce max_attempts
2. Increase base_delay
3. Be selective about retryable exceptions

### Issue: Retries Too Slow

**Symptoms**: Operations take too long to complete

**Possible Causes**:
1. Max delay too high
2. Backoff strategy too conservative
3. Too many retry attempts

**Solutions**:
1. Reduce max_delay
2. Use more aggressive backoff
3. Reduce max_attempts

### Issue: Circuit Breaker Not Opening

**Symptoms**: Circuit breaker stays closed despite failures

**Possible Causes**:
1. Circuit breaker not enabled
2. Threshold too high
3. Failures not counted correctly

**Solutions**:
1. Enable circuit breaker in policy
2. Reduce threshold
3. Check failure counting logic

## Examples

### Example 1: Browser State Save with Retry

```python
from src.resilience.retry.retry_manager import RetryManager
from src.resilience.exceptions import MaxRetriesExceededError

class StateManager:
    def __init__(self):
        self.retry_manager = RetryManager()
        asyncio.create_task(self.retry_manager.initialize())
    
    async def save_state(self, state_id: str, data: dict) -> bool:
        """Save state with retry logic."""
        try:
            return await self.retry_manager.execute_with_retry(
                self._perform_save,
                retry_policy_id="browser_state_timeout",
                state_id=state_id,
                data=data
            )
        except MaxRetriesExceededError as e:
            self.logger.error(
                f"Failed to save state after {e.context['attempts']} attempts",
                state_id=state_id
            )
            return False
    
    async def _perform_save(self, state_id: str, data: dict) -> bool:
        """Actual save operation."""
        # Implementation here
        pass
```

### Example 2: Navigation Route Adaptation with Retry

```python
from src.resilience.retry.retry_manager import RetryManager

class RouteAdapter:
    def __init__(self):
        self.retry_manager = RetryManager()
        asyncio.create_task(self.retry_manager.initialize())
    
    async def adapt_route(self, plan: PathPlan, obstacle_type: str) -> PathPlan:
        """Adapt route with retry logic."""
        try:
            return await self.retry_manager.execute_with_retry(
                self._perform_adaptation,
                retry_policy_id="navigation_retry_with_delay",
                plan=plan,
                obstacle_type=obstacle_type
            )
        except Exception as e:
            self.logger.error(f"Route adaptation failed: {e}")
            raise
    
    async def _perform_adaptation(self, plan: PathPlan, obstacle_type: str) -> PathPlan:
        """Actual adaptation operation."""
        # Implementation here
        pass
```

### Example 3: Telemetry Batch Processing with Retry

```python
from src.resilience.retry.retry_manager import RetryManager

class BatchProcessor:
    def __init__(self):
        self.retry_manager = RetryManager()
        asyncio.create_task(self.retry_manager.initialize())
    
    async def process_batch(self, events: List[TelemetryEvent]) -> List[Dict]:
        """Process batch with retry logic."""
        try:
            return await self.retry_manager.execute_with_retry(
                self._perform_processing,
                retry_policy_id="telemetry_batch_processing",
                events=events
            )
        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}")
            raise
    
    async def _perform_processing(self, events: List[TelemetryEvent]) -> List[Dict]:
        """Actual processing operation."""
        # Implementation here
        pass
```

## Additional Resources

- [Retry Manager API Documentation](contracts/retry-consolidation-api.md)
- [Data Model Documentation](data-model.md)
- [Research Document](research.md)
- [Implementation Plan](plan.md)
- [Feature Specification](spec.md)

## Support

For questions or issues with the centralized retry module:

1. Check the documentation in `src/resilience/retry/`
2. Review the examples in this guide
3. Consult the data model documentation
4. Check the API contracts
5. Contact the development team

## Changelog

### Version 1.0.0 (2026-01-29)

- Initial release of centralized retry module
- Support for exponential, linear, fixed, and immediate backoff
- Support for jitter types (none, full, decorrelated, equal)
- Circuit breaker functionality
- Failure classification
- Session management
- Event publishing and logging
- Health check endpoint
