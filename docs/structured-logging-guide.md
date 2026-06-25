# Developer Guide: Structured Logging

## Overview

This project uses unified JSON logging with automatic field inclusion. All structured data should be passed via the `extra=` parameter to ensure clean, queryable log output.

## Quick Start

```python
import logging
from src.core.logging_config import JsonLoggingConfigurator

# Initialize once at application start
JsonLoggingConfigurator.setup(verbose=True)

# Use in your modules
logger = logging.getLogger('your.module.name')
logger.info('operation_completed', extra={
    'operation': 'data_processing',
    'duration_ms': 1500,
    'records_processed': 42
})
```

## Key Principles

1. **No Manual JSON Serialization**: Never use `json.dumps()` in logging calls
2. **Use extra= Parameter**: All structured data goes in `extra={}`
3. **Descriptive Messages**: Message field should be a simple, readable description
4. **Consistent Field Names**: Use standard names like `event`, `correlation_id`, `session_id`

## Field Naming Conventions

| Field Name | Usage | Example |
|------------|-------|---------|
| `event` | Primary event identifier | `'user_login'` |
| `correlation_id` | Operation tracking | `'abc-123-def'` |
| `session_id` | User session tracking | `'sess-456'` |
| `operation` | Operation type | `'database_query'` |
| `duration_ms` | Timing information | `1500` |
| `error_type` | Error classification | `'ValidationError'` |
| `status` | Operation status | `'success'`, `'failed'` |

## Common Patterns

### User Actions
```python
logger.info('user_login_completed', extra={
    'event': 'user_login_completed',
    'user_id': user.id,
    'ip_address': request.remote_addr,
    'user_agent': request.headers.get('User-Agent')
})
```

### Database Operations
```python
logger.info('database_query_executed', extra={
    'event': 'database_query_executed',
    'query_type': 'SELECT',
    'table': 'users',
    'duration_ms': 45,
    'rows_affected': 1
})
```

### API Calls
```python
logger.info('api_request_completed', extra={
    'event': 'api_request_completed',
    'method': 'POST',
    'endpoint': '/api/v1/users',
    'status_code': 201,
    'response_time_ms': 120
})
```

### Error Handling
```python
logger.error('validation_failed', extra={
    'event': 'validation_failed',
    'error_type': 'ValidationError',
    'field': 'email',
    'error_message': 'Invalid email format',
    'user_id': user.id
})
```

## Integration with Existing Code

When migrating from double-encoded JSON:

### Before
```python
log_data = {'event': 'test', 'status': 'ok'}
logger.info(json.dumps(log_data))
```

### After
```python
logger.info('test', extra={'event': 'test', 'status': 'ok'})
```

## Testing Your Logging

Always verify your log output:

```bash
# Run with verbose to see all levels
python -m src.main your-command --verbose

# Check that output is clean JSON, not nested strings
```

## Troubleshooting

### Issue: Fields not appearing in output
**Cause**: Not using `extra=` parameter
**Fix**: Use `logger.info('message', extra={'field': 'value'})`

### Issue: Nested JSON in message field
**Cause**: Using `json.dumps()` manually
**Fix**: Remove `json.dumps()` and use `extra=` instead

### Issue: Missing correlation context
**Cause**: Not using the structured logger wrapper
**Fix**: Use `get_logger()` from observability module
