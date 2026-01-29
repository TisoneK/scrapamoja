# Data Model: Fix Framework Bugs

**Date**: 2025-01-29  
**Purpose**: Entity definitions and data structures for framework bug fixes

## Entity Overview

This feature focuses on fixing existing entities rather than creating new ones. The following entities are modified:

### RetryConfig

**Purpose**: Configuration for retry operations with resilience patterns  
**Location**: `src/browser/resilience.py`  
**Modification**: Add `execute_with_retry` method

#### Fields (Existing)
- `max_attempts: int` - Maximum number of retry attempts
- `delay: float` - Base delay between attempts in seconds
- `backoff_factor: float` - Multiplier for exponential backoff
- `exceptions: Tuple[Type[Exception], ...]` - Exception types to retry on

#### Methods (Added)
```python
async def execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
    """
    Execute operation with retry configuration.
    
    Args:
        operation: Async callable to execute
        *args: Arguments to pass to operation
        **kwargs: Keyword arguments to pass to operation
        
    Returns:
        Result of successful operation execution
        
    Raises:
        Last exception if all attempts fail
    """
```

#### Validation Rules
- `max_attempts` must be >= 1
- `delay` must be >= 0
- `backoff_factor` must be >= 1.0

### BrowserSession

**Purpose**: Session management for browser instances  
**Location**: `src/browser/session.py`  
**Modification**: Fix session_id None handling in `__post_init__`

#### Fields (Existing)
- `session_id: str` - Unique identifier for the session (default_factory generates UUID)
- `configuration: BrowserConfiguration` - Browser configuration for this session
- `browser_instance: Optional[Browser]` - Playwright browser instance
- `context: Optional[BrowserContext]` - Browser context
- `created_at: datetime` - Session creation timestamp
- `last_activity: datetime` - Last activity timestamp

#### Methods (Modified)
```python
def __post_init__(self):
    """
    Initialize session after dataclass creation.
    Fixed to handle None session_id gracefully.
    """
    if self.session_id is None:
        self.session_id = str(uuid.uuid4())
    self._logger = get_logger(f"browser_session.{self.session_id[:8]}")
```

#### State Transitions
- `INITIALIZING` → `ACTIVE` → `CLOSING` → `CLOSED`
- Session ID generation happens during `INITIALIZING` state

#### Validation Rules
- `session_id` must be a valid UUID string (auto-generated if None)
- `configuration` must be a valid BrowserConfiguration instance

### FileSystemStorageAdapter

**Purpose**: File system implementation for storage operations  
**Location**: `src/storage/adapter.py`  
**Modification**: Add `list_files` method

#### Fields (Existing)
- `storage_path: str` - Base directory for file storage
- `encoding: str` - File encoding (default: utf-8)

#### Methods (Added)
```python
async def list_files(self, pattern: str = "*") -> List[str]:
    """
    List files matching pattern in storage directory.
    
    Args:
        pattern: Glob pattern for file matching (default: "*")
        
    Returns:
        List of relative file paths matching pattern
    """
```

#### Validation Rules
- `storage_path` must be a valid directory path
- `pattern` must be a valid glob pattern
- Returns empty list if storage directory doesn't exist

### CircuitBreaker

**Purpose**: Resilience pattern for handling failures  
**Location**: `src/browser/resilience.py`  
**Modification**: Ensure proper async usage

#### Fields (Existing)
- `failure_threshold: int` - Number of failures before opening circuit
- `recovery_timeout: float` - Seconds to wait before trying recovery
- `expected_exception: Type[Exception]` - Exception type that triggers circuit
- `state: CircuitState` - Current circuit state (CLOSED, OPEN, HALF_OPEN)

#### Methods (Existing - Usage Fix)
```python
async def call(self, operation: Callable, *args, **kwargs) -> Any:
    """
    Execute operation with circuit breaker protection.
    All calls must be properly awaited.
    """
```

#### State Transitions
- `CLOSED` → `OPEN` (when failure threshold reached)
- `OPEN` → `HALF_OPEN` (after recovery timeout)
- `HALF_OPEN` → `CLOSED` (on successful operation)
- `HALF_OPEN` → `OPEN` (on failed operation)

#### Validation Rules
- `failure_threshold` must be >= 1
- `recovery_timeout` must be >= 0
- State transitions must follow circuit breaker pattern

## Data Flow

### Session Creation Flow
1. BrowserManager.create_session() called
2. BrowserSession instantiated (session_id may be None)
3. BrowserSession.__post_init__() generates session_id if None
4. Session initialization continues with valid session_id

### Retry Operation Flow
1. execute_with_resilience() called with retry_config
2. retry_config.execute_with_retry() executes operation
3. Exponential backoff applied between attempts
4. Operation result returned or last exception raised

### Storage Operation Flow
1. BrowserManager initialization loads persisted sessions
2. FileSystemStorageAdapter.list_files() called with pattern
3. Matching session files returned for loading
4. Session state restored from files

### Circuit Breaker Flow
1. Protected operation called through CircuitBreaker.call()
2. Circuit state checked (CLOSED, OPEN, HALF_OPEN)
3. Operation executed if circuit allows
4. Circuit state updated based on result

## Error Handling

### RetryConfig Errors
- Invalid parameters raise ValueError during validation
- Operation exceptions are retried until max_attempts reached
- Last exception is re-raised if all attempts fail

### BrowserSession Errors
- None session_id handled gracefully with auto-generation
- Invalid configuration raises ValueError during initialization
- Logging errors use fallback logger if session_id unavailable

### FileSystemStorageAdapter Errors
- Invalid storage path raises FileNotFoundError
- Permission errors raise PermissionError
- Pattern errors raise ValueError for invalid glob patterns

### CircuitBreaker Errors
- Circuit open raises CircuitBreakerOpenError
- Recovery timeout errors handled internally
- Operation exceptions affect circuit state transitions

## Integration Points

### BrowserManager Integration
- Uses RetryConfig for session creation resilience
- Creates BrowserSession instances with proper session_id handling
- Loads persisted sessions via FileSystemStorageAdapter

### Session Persistence Integration
- FileSystemStorageAdapter provides file listing for session recovery
- Session files stored with session_id as filename
- JSON serialization for session state

### Resilience Integration
- CircuitBreaker protects critical operations
- RetryConfig provides retry logic for transient failures
- Both work together for comprehensive error handling

## Testing Considerations

### Unit Tests
- Test RetryConfig.execute_with_retry with various failure scenarios
- Test BrowserSession creation with None and explicit session_id
- Test FileSystemStorageAdapter.list_files with different patterns
- Test CircuitBreaker state transitions and async behavior

### Integration Tests
- Test complete session creation flow with all fixes
- Test browser lifecycle example execution
- Test session persistence and recovery
- Test resilience patterns under failure conditions

### Manual Validation
- Run browser lifecycle example to verify all fixes work together
- Monitor for RuntimeWarning messages (should be eliminated)
- Verify timing information displays correctly
- Check session cleanup completes without resource leaks
