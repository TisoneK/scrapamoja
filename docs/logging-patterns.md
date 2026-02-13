# Logging Patterns Guide

## Correct Usage ✅

### Basic Structured Logging
```python
import logging
from src.core.logging_config import JsonLoggingConfigurator

# Initialize logging
JsonLoggingConfigurator.setup(verbose=True)

# Use extra= parameter for structured data
logger = logging.getLogger('module.name')
logger.info(
    'user_action_completed',
    extra={
        'event': 'user_action_completed',
        'user_id': '12345',
        'action': 'login',
        'timestamp': '2026-02-12T20:00:00Z'
    }
)
```

### Output
```json
{
  "message": "user_action_completed",
  "event": "user_action_completed",
  "user_id": "12345",
  "action": "login",
  "timestamp": "2026-02-12T20:00:00Z",
  "logger": "module.name",
  "level": "INFO",
  "timestamp": "2026-02-12T20:00:00,123"
}
```

## Incorrect Usage ❌

### Double JSON Encoding
```python
import json
import logging

# NEVER do this - creates double JSON encoding
logger.info(json.dumps({
    'event': 'user_action_completed',
    'user_id': '12345'
}))
```

### Output (WRONG)
```json
{
  "message": "{\"event\": \"user_action_completed\", \"user_id\": \"12345\"}"
}
```

### Dictionary Arguments
```python
# NEVER do this - kwargs don't become structured fields
logger.info('message', event='test', user_id='123')
```

## Best Practices

1. **Always use `extra=` parameter** for structured data
2. **Keep message field descriptive but simple** - it's the primary identifier
3. **Use consistent field names** across your application
4. **Don't manually serialize to JSON** - let the formatter handle it
5. **Use correlation IDs** for tracking operations across modules

## Migration Examples

### Before (Double JSON Encoding)
```python
log_data = {'event': 'test', 'user_id': '123'}
logger.info(json.dumps(log_data))
```

### After (Clean Structured Logging)
```python
logger.info('test', extra={'event': 'test', 'user_id': '123'})
```
