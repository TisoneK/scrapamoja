# API Contracts: Fix Framework Bugs

**Date**: 2025-01-29  
**Purpose**: Interface definitions for modified components

## RetryConfig Interface

### execute_with_retry Method

```python
async def execute_with_retry(
    self, 
    operation: Callable[..., Awaitable[Any]], 
    *args, 
    **kwargs
) -> Any:
    """
    Execute an async operation with retry logic.
    
    Args:
        operation: Async callable to execute
        *args: Positional arguments for the operation
        **kwargs: Keyword arguments for the operation
        
    Returns:
        The result of the successful operation execution
        
    Raises:
        Exception: The last exception if all retry attempts fail
        ValueError: If retry configuration is invalid
    """
```

### Usage Example

```python
retry_config = RetryConfig(
    max_attempts=3,
    delay=1.0,
    backoff_factor=2.0,
    exceptions=(TimeoutError, ConnectionError)
)

result = await retry_config.execute_with_retry(
    some_browser_operation, 
    url="https://example.com"
)
```

## BrowserSession Interface

### Constructor Behavior

```python
@dataclass
class BrowserSession:
    session_id: Optional[str] = None  # Auto-generated if None
    configuration: BrowserConfiguration = field(default_factory=BrowserConfiguration)
    # ... other fields
    
    def __post_init__(self):
        """
        Post-initialization hook.
        Generates session_id if None, initializes logging.
        """
```

### Session ID Generation

- If `session_id` is provided: Use as-is
- If `session_id` is None: Generate UUID v4 string
- Format: 8-4-4-4-12 hexadecimal characters (standard UUID)

### Usage Example

```python
# With auto-generated session_id
session = BrowserSession()
print(session.session_id)  # e.g., "550e8400-e29b-41d4-a716-446655440000"

# With explicit session_id
session = BrowserSession(session_id="custom-session-123")
print(session.session_id)  # "custom-session-123"
```

## FileSystemStorageAdapter Interface

### list_files Method

```python
async def list_files(self, pattern: str = "*") -> List[str]:
    """
    List files in storage directory matching a glob pattern.
    
    Args:
        pattern: Glob pattern for file matching (default: "*")
        
    Returns:
        List of relative file paths from storage directory
        
    Raises:
        ValueError: If pattern is invalid
        PermissionError: If lacking read permissions
        FileNotFoundError: If storage directory doesn't exist (returns empty list)
    """
```

### Pattern Examples

```python
adapter = FileSystemStorageAdapter("./sessions")

# List all files
all_files = await adapter.list_files()

# List JSON files only
json_files = await adapter.list_files("*.json")

# List session files with specific prefix
session_files = await adapter.list_files("session_*.json")
```

### Return Format

- Returns list of strings representing relative file paths
- Paths are relative to the storage_path directory
- Empty list if no files match or directory doesn't exist
- Order is not guaranteed (filesystem dependent)

## CircuitBreaker Interface

### call Method Usage

```python
async def call(
    self, 
    operation: Callable[..., Awaitable[Any]], 
    *args, 
    **kwargs
) -> Any:
    """
    Execute operation through circuit breaker protection.
    
    Args:
        operation: Async callable to execute
        *args: Positional arguments for the operation
        **kwargs: Keyword arguments for the operation
        
    Returns:
        The result of the operation execution
        
    Raises:
        CircuitBreakerOpenError: If circuit is open
        Exception: The operation exception if it fails
    """
```

### Proper Usage Pattern

```python
# Correct - properly awaited
try:
    result = await circuit_breaker.call(risky_operation, param1, param2)
except CircuitBreakerOpenError:
    # Handle circuit open state
    fallback_result = await fallback_operation()
except Exception as e:
    # Handle operation failure
    log_error(e)

# Incorrect - causes RuntimeWarning
result = circuit_breaker.call(risky_operation, param1, param2)  # Don't do this!
```

## Error Handling Contracts

### RetryConfig Error Types

```python
class RetryConfigError(Exception):
    """Base exception for retry configuration errors."""
    pass

class InvalidRetryConfigurationError(RetryConfigError):
    """Raised when retry parameters are invalid."""
    pass
```

### BrowserSession Error Types

```python
class BrowserSessionError(Exception):
    """Base exception for session errors."""
    pass

class SessionInitializationError(BrowserSessionError):
    """Raised when session initialization fails."""
    pass
```

### FileSystemStorageAdapter Error Types

```python
class StorageAdapterError(Exception):
    """Base exception for storage adapter errors."""
    pass

class FileNotFoundError(StorageAdapterError):
    """Raised when storage directory doesn't exist."""
    pass

class PermissionError(StorageAdapterError):
    """Raised when lacking file permissions."""
    pass
```

### CircuitBreaker Error Types

```python
class CircuitBreakerError(Exception):
    """Base exception for circuit breaker errors."""
    pass

class CircuitBreakerOpenError(CircuitBreakerError):
    """Raised when circuit is open and blocking operations."""
    pass
```

## Integration Contracts

### BrowserManager Integration

```python
class BrowserManager:
    async def create_session(
        self, 
        session_id: Optional[str] = None,
        configuration: Optional[BrowserConfiguration] = None
    ) -> BrowserSession:
        """
        Create a new browser session with proper error handling.
        
        Args:
            session_id: Optional session identifier
            configuration: Optional browser configuration
            
        Returns:
            Configured BrowserSession instance
            
        Raises:
            BrowserSessionError: If session creation fails
            RetryConfigError: If retry logic fails
        """
```

### Session Persistence Integration

```python
class SessionPersistenceManager:
    async def save_session(self, session: BrowserSession) -> bool:
        """Save session state to persistent storage."""
        
    async def load_sessions(self) -> List[BrowserSession]:
        """Load all persisted sessions from storage."""
        
    async def list_session_files(self) -> List[str]:
        """List all session files in storage."""
```

## Performance Contracts

### RetryConfig Performance

- Maximum retry attempts: 10 (configurable)
- Maximum delay between attempts: 60 seconds (configurable)
- Memory overhead: Minimal (stores only configuration)

### BrowserSession Performance

- Session ID generation: < 1ms
- Logging initialization: < 5ms
- Memory overhead: Session data + logging overhead

### FileSystemStorageAdapter Performance

- File listing: O(n) where n is number of files in directory
- Pattern matching: Uses built-in glob patterns (optimized)
- Memory overhead: List of file paths only

### CircuitBreaker Performance

- Circuit state check: O(1)
- Operation execution: No additional overhead
- Memory overhead: State tracking + failure history

## Testing Contracts

### Unit Test Requirements

```python
# RetryConfig tests
async def test_retry_config_success():
    """Test successful operation execution."""
    
async def test_retry_config_with_retries():
    """Test retry behavior on failures."""
    
async def test_retry_config_max_attempts():
    """Test behavior when max attempts exceeded."""

# BrowserSession tests
def test_browser_session_auto_id():
    """Test automatic session ID generation."""
    
def test_browser_session_explicit_id():
    """Test explicit session ID usage."""
    
def test_browser_session_logging():
    """Test logging initialization."""

# FileSystemStorageAdapter tests
async def test_list_files_all():
    """Test listing all files."""
    
async def test_list_files_pattern():
    """Test listing files with pattern."""
    
async def test_list_files_empty_directory():
    """Test listing files in empty directory."""

# CircuitBreaker tests
async def test_circuit_breaker_success():
    """Test successful operation through circuit breaker."""
    
async def test_circuit_breaker_failure():
    """Test circuit breaker on operation failure."""
    
async def test_circuit_breaker_open_state():
    """Test behavior when circuit is open."""
```

### Integration Test Requirements

```python
async def test_browser_lifecycle_example():
    """Test complete browser lifecycle example execution."""
    
async def test_session_persistence_flow():
    """Test session save and restore functionality."""
    
async def test_resilience_integration():
    """Test retry and circuit breaker integration."""
```

## Version Compatibility

### Backward Compatibility

- All existing public APIs remain unchanged
- New methods are additive (no breaking changes)
- Default behaviors preserved
- Configuration options extended, not replaced

### Migration Guide

No migration required for existing code. The fixes are transparent to existing users of the framework.
