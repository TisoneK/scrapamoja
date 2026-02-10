# Browser Lifecycle Management Documentation

This section provides comprehensive documentation for the Browser Lifecycle Management feature.

## Overview

The Browser Lifecycle Management feature provides centralized browser instance creation, session isolation, resource monitoring, state persistence, and configuration management for the Scorewise scraper system.

## Quick Start

### Basic Usage

```python
from src.browser import BrowserAuthority, get_browser_authority

# Initialize the browser authority
authority = await get_browser_authority()
await authority.initialize()

# Create a browser session with default configuration
session = await authority.create_session()

# Create a session with custom configuration
from src.browser.models.session import BrowserConfiguration

config = BrowserConfiguration(
    config_id="custom_session",
    browser_type="chromium",
    headless=True,
    viewport_width=1366,
    viewport_height=768,
    stealth_settings=StealthSettings.get_stealth_presets()["high"]
)

session = await authority.create_session(config)

# Navigate to a page
tab = await session.create_context("https://example.com")
await tab.navigate("https://example.com/page")

# Take screenshot
screenshot = await tab.take_screenshot()
```

### Configuration Management

```python
from src.browser.models.proxy import ProxySettings
from src.browser.models.stealth import StealthSettings

# Create a configuration with proxy
proxy_settings = ProxySettings.create_residential_proxy(
    "residential.example.com",
    8080,
    "user123",
    "pass123"
)

# Create configuration with maximum stealth
stealth_settings = StealthSettings(
    stealth_level=StealthLevel.MAXIMUM,
    residential_ip_required=True
)

config = BrowserConfiguration(
    config_id="stealth_proxy_session",
    browser_type="chromium",
    headless=True,
    proxy_settings=proxy_settings,
    stealth_settings=stealth_settings
)

session = await authority.create_session(config)
```

### Resource Monitoring

```python
# Get current resource metrics
metrics = await authority.get_system_metrics()
print(f"Memory: {metrics.memory_usage_mb:.2f}MB")
print(f"CPU: {metrics.cpu_usage_percent:.1f}%")
print(f"Active sessions: {await authority.get_active_session_count()}")

# Get monitoring status
status = await authority.get_authority_status()
print(f"Monitoring {len(status['sessions'])} sessions")
```

### State Persistence

```python
# Save browser state
state = await session.save_state("session_backup_1")

# Restore browser state
restored_session = await session.restore_state(state)
```

### Resource Cleanup

```python
# Trigger cleanup when resources are high
await authority.cleanup_resources(session.session_id)

# Manual cleanup with specific level
from src.browser.models.enums import CleanupLevel

await authority.trigger_cleanup(session.session_id, CleanupLevel.MODERATE)
```

## Configuration Reference

### Browser Configuration

#### Core Fields
- `config_id`: Unique identifier for the configuration
- `browser_type`: Browser engine (chromium, firefox, webkit)
- `headless`: Run browser in headless mode
- `viewport_width`, `viewport_height`: Browser viewport dimensions
- `device_scale_factor`: Device pixel density
- `is_mobile`: Mobile device flag
- `has_touch`: Touch capability flag

#### Stealth Settings
- `stealth_level`: Stealth level (minimal, standard, high, maximum)
- `fingerprint_randomization`: Enable browser fingerprint randomization
- `mouse_movement_simulation`: Simulate human-like mouse movements
- `typing_simulation`: Simulate human typing patterns
- `scroll_simulation`: Simulate natural scrolling behavior
- `timing_randomization`: Add random delays to actions

#### Proxy Settings
- `proxy_type`: Proxy type (HTTP, HTTPS, SOCKS5)
- `server`: Proxy server address
- `port`: Proxy server port
- `username`, `password`: Authentication credentials
- `bypass_list`: Hostnames to bypass proxy
- `dns_servers`: Custom DNS servers

### Default Configurations

| Config ID | Browser | Headless | Viewport | Stealth Level | Description |
|---------|---------|---------|----------|---------------|-------------|
| `chromium_headless` | chromium | True | 1920x1080 | standard | Standard headless Chrome |
| `chromium_gui` | chromium | False | 1920x1080 | standard | Chrome with GUI |
| `firefox_headless` | firefox | True | 1920x1080 | standard | Standard headless Firefox |
| `mobile_chrome` | chromium | True | 375x667 | high | Mobile Chrome |
| `tablet_safari` | webkit | True | 768x1024 | high | Tablet Safari |
| `stealth_chromium` | chromium | True | 1366x768 | maximum | Maximum stealth |
| `residential_proxy` | chromium | True | 1920x1080 | high | Chrome with residential proxy |

## API Reference

### BrowserAuthority

#### Core Methods
- `initialize()`: Initialize the browser authority
- `create_session(configuration)`: Create a new browser session
- `get_session(session_id)`: Retrieve an existing session
- `list_sessions(status_filter)`: List sessions by status
- `terminate_session(session_id)`: Terminate a session
- `cleanup_resources(session_id) Force cleanup of resources
- `get_system_metrics()`: Get system-wide resource metrics
- `get_active_session_count()`: Get count of active sessions
- `shutdown_all_sessions()`: Shutdown all sessions
- `shutdown()`: Shutdown the browser authority

#### Configuration Methods
- `get_configuration(config_id)`: Get configuration by ID
- `create_configuration(config_id, browser_type, **kwargs)`: Create new configuration
- `update_configuration(config_id, **kwargs)`: Update existing configuration
- `delete_configuration(config_id)`: Delete configuration
- `list_configurations()`: List all configurations
- `validate_configuration(config)`: Validate configuration
- `clone_configuration(source_id, new_config_id)`: Clone configuration
- `export_configuration(config_id, file_path)`: Export configuration to file
- `import_configuration(file_path, config_id)`: Import configuration from file
- `get_default_configuration()`: Get default configuration

### Resource Monitoring

#### ResourceMonitor Methods
- `start_monitoring(session_id)`: Start monitoring a session
- `stop_monitoring(session_id)`: Stop monitoring a session
- `get_metrics(session_id)`: Get current metrics
- `check_thresholds(session_id)`: Check resource thresholds
- `trigger_cleanup(session_id, level)`: Trigger cleanup action
- `set_thresholds(memory_mb, cpu_percent, disk_mb)`: Set monitoring thresholds
- `get_monitoring_status()`: Get monitoring status
- `shutdown()`: Shutdown the monitor

### State Management

#### StateManager Methods
- `save_state(session, state_id)`: Save browser state
- `load_state(state_id)`: Load browser state
- `list_sessions(session_id)`: List saved states
- `delete_state(state_id)`: Delete saved state
- `cleanup_expired_states()`: Clean up expired states

### Error Handling

#### Error Types
- `BrowserError`: Base browser-related errors
- `SessionCreationError`: Session creation failures
- `ResourceExhaustionError`: Resource limit exceeded
- `ConfigurationError`: Configuration validation failures
- `MonitoringError`: Monitoring operation failures

#### Recovery Strategies
- **Retry**: Retry failed operations with exponential backoff
- **Fallback**: Use fallback metrics when collection fails
- **Skip**: Skip operations that are not critical
- **Escalate**: Escalate critical issues to alerts

## Best Practices

### Session Management
- Always terminate sessions when done to prevent resource leaks
- Use appropriate stealth levels for your use case
- Monitor resource usage and set appropriate thresholds
- Save state before critical operations
- Use configuration templates for consistent setup

### Configuration Management
- Use descriptive configuration IDs for easy identification
- Validate configurations before use
- Clone configurations for similar use cases
- Export/import configurations for team sharing
- Keep sensitive credentials secure (use environment variables)

### Resource Monitoring
- Set appropriate thresholds for your environment
- Monitor memory usage for browser instances
- Use automatic cleanup for resource management
- Track alert history for pattern analysis
- Monitor system-wide metrics for capacity planning

### Stealth Configuration
- Match stealth level to detection risk level
- Use residential proxies for high-risk operations
- Enable fingerprint protection for anti-bot detection
- Simulate human behavior patterns realistically
- Configure timing randomization appropriately

### Error Handling
- Validate configurations before use
- Implement proper error recovery strategies
- Log all errors with context
- Use fallback mechanisms when appropriate
- Monitor error patterns for optimization

## Troubleshooting

### Common Issues

**Session Creation Fails**
- Check Playwright installation: `playwright install`
- Verify configuration validation
- Check resource limits
- Review error logs for specific details

**Resource Exhaustion**
- Monitor system resource usage
- Adjust session limits in configuration
- Implement automatic cleanup
- Check for memory leaks

**Configuration Validation Errors**
- Review validation error messages
- Check field requirements
- Verify data types and ranges
- Follow configuration best practices

**Proxy Connection Issues**
- Test proxy server connectivity
- Verify credentials and permissions
- Check bypass list configuration
- Validate proxy type compatibility

**Stealth Detection**
- Increase stealth level if detected
- Review fingerprint randomization
- Check browser configuration
- Consider residential proxy usage

## Performance Optimization

### Session Management
- Reuse browser instances when possible
- Implement session pooling for frequent operations
- Clean up sessions promptly
- Optimize session lifecycle

### Resource Monitoring
- Adjust check intervals based on resource usage
- Use efficient metrics collection
- Limit history size
- Monitor only what's necessary

### Configuration Caching
- Cache frequently used configurations
- Use lazy loading for file-based configs
- Implement cache invalidation
- Clear cache when needed

## Security Considerations

### Credential Management
- Never hardcode credentials in configurations
- Use environment variables for sensitive data
- Rotate credentials regularly
- Use secure storage for configuration files
- Limit access to configuration files

### Proxy Security
- Use HTTPS for proxy connections when possible
- Validate proxy server certificates
- Implement credential rotation
- Monitor proxy usage patterns
- Use reputable proxy providers

### Stealth Configuration
- Keep stealth settings up to date
- Monitor for detection signatures
- Adjust levels based on feedback
- Test stealth effectiveness regularly
- Rotate fingerprint patterns

## Migration Guide

### From Default to Custom Configuration

1. Create a new configuration:
   ```python
   config = authority.get_default_configuration()
   authority.create_configuration("my_custom_config", "chromium", headless=True)
   ```

2. Customize as needed:
   ```python
   authority.update_configuration("my_custom_config", 
                              viewport_width=1366,
                              stealth_settings=StealthSettings.get_stealth_presets()["high"])
   ```

3. Save for reuse:
   ```python
   authority.export_configuration("my_custom_config", "/path/to/config.json")
   ```

### Import Existing Configuration

1. Import from file:
   ```python
   config = authority.import_configuration("/path/to/config.json", "imported_config")
   session = authority.create_session(config)
   ```

2. Clone and modify:
   ```python
   cloned_config = authority.clone_configuration("imported_config", "cloned_config")
   authority.update_configuration("cloned_config", viewport_width=1600)
   ```

## Support

For additional help:
- Check the API reference for detailed method documentation
- Review configuration examples in this guide
- Check error messages for specific issues
- Review integration tests for usage patterns
- Consult the configuration validation rules for best practices
