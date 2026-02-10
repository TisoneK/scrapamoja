# Quickstart Guide: Browser Lifecycle Management

**Feature**: Browser Lifecycle Management  
**Date**: 2025-01-27  
**Phase**: 1 - Design & Contracts

## Overview

This guide provides a quick introduction to using the Browser Lifecycle Management feature in the Scorewise scraper system. It covers basic usage patterns, common scenarios, and integration with existing components.

## Prerequisites

- Python 3.11+ with asyncio
- Playwright installed and browsers downloaded
- Existing Scorewise scraper infrastructure
- Access to observability and logging systems

## Basic Usage

### 1. Creating a Browser Session

```python
from src.browser.authority import BrowserAuthority
from src.browser.configuration import BrowserConfiguration

# Initialize the browser authority
authority = BrowserAuthority()

# Create a session with default configuration
session = await authority.create_session()
print(f"Created session: {session.session_id}")

# Create a session with custom configuration
config = BrowserConfiguration(
    config_id="stealth_config",
    browser_type="chromium",
    headless=True,
    viewport=ViewportSettings(width=1920, height=1080),
    stealth_settings=StealthSettings(
        fingerprint_randomization=True,
        mouse_movement_simulation=True
    )
)
session = await authority.create_session(config)
```

### 2. Managing Browser Contexts (Tabs)

```python
# Create a new context/tab
context = await session.create_context("https://example.com")
print(f"Created context: {context.context_id}")

# Navigate to a URL
await context.navigate("https://example.com/login")

# Wait for page to load
await context.wait_for_load()

# Get page information
url = await context.get_current_url()
title = await context.get_page_title()
print(f"Current page: {title} at {url}")

# Create additional contexts
context2 = await session.create_context("https://example.com/dashboard")

# Switch between contexts
await session.switch_to_context(context.context_id)
await session.switch_to_context(context2.context_id)

# List all contexts
contexts = await session.list_contexts()
print(f"Active contexts: {[c.context_id for c in contexts]}")

# Close a context
await session.close_context(context.context_id)
```

### 3. State Persistence

```python
# Save browser state
state = await session.save_state()
print(f"Saved state: {state.state_id}")

# Save state with custom ID
state = await session.save_state("login_session")

# Later, restore state in a new session
new_session = await authority.create_session()
success = await new_session.restore_state(state)
if success:
    print("State restored successfully")

# List saved states
states = await state_manager.list_states()
print(f"Available states: {states}")
```

### 4. Resource Monitoring

```python
# Get current resource metrics
metrics = await session.get_resource_metrics()
print(f"Memory usage: {metrics.memory_usage_mb}MB")
print(f"CPU usage: {metrics.cpu_usage_percent}%")

# Check if thresholds are exceeded
alert_status = await resource_monitor.check_thresholds(session.session_id)
if alert_status == AlertStatus.WARNING:
    print("Resource usage approaching limits")
elif alert_status == AlertStatus.CRITICAL:
    print("Resource usage critical - cleanup needed")

# Trigger cleanup if needed
if alert_status == AlertStatus.CRITICAL:
    await resource_monitor.trigger_cleanup(session.session_id, CleanupLevel.AGGRESSIVE)
```

### 5. Session Cleanup

```python
# Graceful session termination
success = await authority.terminate_session(session.session_id)
if success:
    print("Session terminated gracefully")

# Force cleanup if graceful termination fails
if not success:
    await authority.cleanup_resources(session.session_id)
    print("Force cleanup completed")
```

## Common Scenarios

### Scenario 1: Multi-Tab Scraping

```python
async def multi_tab_scraping():
    authority = BrowserAuthority()
    session = await authority.create_session()
    
    try:
        # Open multiple tabs for different pages
        contexts = []
        urls = [
            "https://example.com/products",
            "https://example.com/categories", 
            "https://example.com/reviews"
        ]
        
        for url in urls:
            context = await session.create_context(url)
            contexts.append(context)
        
        # Process each tab
        results = []
        for context in contexts:
            await context.wait_for_load()
            title = await context.get_page_title()
            screenshot = await context.take_screenshot()
            results.append({
                "title": title,
                "screenshot": screenshot
            })
        
        return results
        
    finally:
        await authority.terminate_session(session.session_id)
```

### Scenario 2: Session Persistence

```python
async def persistent_session_workflow():
    authority = BrowserAuthority()
    state_manager = StateManager()
    
    # Try to restore existing session
    saved_states = await state_manager.list_states()
    if saved_states:
        state = await state_manager.load_state(saved_states[0])
        session = await authority.create_session()
        await session.restore_state(state)
        print("Restored existing session")
    else:
        # Create new session and login
        session = await authority.create_session()
        context = await session.create_context("https://example.com/login")
        
        # Perform login (implementation depends on site)
        await login_procedure(context)
        
        # Save state after login
        state = await session.save_state("authenticated_session")
        print("Created and saved new authenticated session")
    
    # Continue with authenticated operations
    # ...
    
    await authority.terminate_session(session.session_id)
```

### Scenario 3: Resource Management

```python
async def resource_managed_scraping():
    authority = BrowserAuthority()
    monitor = ResourceMonitor()
    
    # Configure resource thresholds
    monitor.set_thresholds(
        memory_mb_limit=500,
        cpu_percent_limit=80,
        disk_mb_limit=1000
    )
    
    sessions = []
    try:
        # Create sessions with monitoring
        for i in range(5):
            session = await authority.create_session()
            await monitor.start_monitoring(session.session_id)
            sessions.append(session)
        
        # Perform operations while monitoring resources
        for session in sessions:
            metrics = await session.get_resource_metrics()
            if metrics.alert_status == AlertStatus.CRITICAL:
                await monitor.trigger_cleanup(session.session_id, CleanupLevel.MODERATE)
            
            # Do work with the session
            # ...
            
    finally:
        # Cleanup all sessions
        for session in sessions:
            await monitor.stop_monitoring(session.session_id)
            await authority.terminate_session(session.session_id)
```

## Integration with Selector Engine

```python
from src.selectors.engine import SelectorEngine

async def selector_integration_example():
    authority = BrowserAuthority()
    selector_engine = SelectorEngine()
    
    session = await authority.create_session()
    context = await session.create_context("https://example.com")
    
    try:
        # Get DOM context for selector engine
        dom_context = await context.get_dom_snapshot()
        
        # Use selector engine to find elements
        results = await selector_engine.resolve_selectors(
            selectors=["button.submit", "input.email"],
            dom_context=dom_context
        )
        
        for selector_result in results:
            if selector_result.confidence > 0.8:
                print(f"Found element: {selector_result.element}")
                
    finally:
        await authority.terminate_session(session.session_id)
```

## Error Handling

```python
from src.browser.exceptions import (
    SessionCreationError,
    ResourceExhaustionError,
    StateCorruptionError
)

async def robust_browser_usage():
    authority = BrowserAuthority()
    
    try:
        session = await authority.create_session()
    except SessionCreationError as e:
        print(f"Failed to create session: {e}")
        return
    
    try:
        # Use session
        context = await session.create_context("https://example.com")
        
    except ResourceExhaustionError as e:
        print(f"Resources exhausted: {e}")
        await authority.cleanup_resources(session.session_id)
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        await authority.cleanup_resources(session.session_id)
        
    finally:
        try:
            await authority.terminate_session(session.session_id)
        except Exception as e:
            print(f"Cleanup error: {e}")
```

## Configuration Examples

### Stealth Configuration

```python
stealth_config = BrowserConfiguration(
    config_id="high_stealth",
    browser_type="chromium",
    headless=True,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    stealth_settings=StealthSettings(
        fingerprint_randomization=True,
        mouse_movement_simulation=True,
        typing_simulation=True,
        scroll_simulation=True,
        timing_randomization=True
    ),
    viewport=ViewportSettings(
        width=1366,
        height=768,
        device_scale_factor=1.0,
        is_mobile=False
    )
)
```

### Proxy Configuration

```python
proxy_config = BrowserConfiguration(
    config_id="proxy_config",
    proxy_settings=ProxySettings(
        server="http://proxy.example.com:8080",
        username="user123",
        password="pass456",
        bypass_list=["localhost", "127.0.0.1"]
    )
)
```

## Monitoring and Debugging

### Event Monitoring

```python
from src.browser.events import BrowserEventType, BrowserEvent

async def monitor_browser_events():
    authority = BrowserAuthority()
    
    # Subscribe to browser events
    async def handle_event(event: BrowserEvent):
        print(f"Event: {event.event_type.value} for session {event.session_id}")
        
        if event.event_type == BrowserEventType.RESOURCE_THRESHOLD_EXCEEDED:
            print(f"Resource alert: {event.data}")
            
    authority.event_emitter.subscribe(handle_event)
    
    # Use browser normally
    session = await authority.create_session()
    # ...
```

### Logging

```python
import logging

# Configure browser-specific logging
logger = logging.getLogger("browser.lifecycle")

async def logged_browser_usage():
    authority = BrowserAuthority()
    
    logger.info("Starting browser session")
    session = await authority.create_session()
    logger.info(f"Created session {session.session_id}")
    
    try:
        context = await session.create_context("https://example.com")
        logger.info(f"Created context {context.context_id}")
        
        # Monitor resources
        metrics = await session.get_resource_metrics()
        logger.info(f"Resource usage: {metrics.memory_usage_mb}MB memory")
        
    except Exception as e:
        logger.error(f"Browser operation failed: {e}")
        raise
        
    finally:
        await authority.terminate_session(session.session_id)
        logger.info("Session terminated")
```

## Performance Tips

1. **Reuse Sessions**: Create sessions once and reuse for multiple operations
2. **Context Pooling**: Keep contexts alive instead of recreating them
3. **Resource Monitoring**: Monitor resources proactively to avoid crashes
4. **State Caching**: Save state periodically to avoid losing progress
5. **Cleanup**: Always terminate sessions properly to prevent resource leaks

## Troubleshooting

### Common Issues

1. **Session Creation Fails**: Check Playwright installation and browser downloads
2. **Memory Leaks**: Ensure proper context and session cleanup
3. **State Corruption**: Validate state data before restoration
4. **Resource Exhaustion**: Monitor usage and implement cleanup strategies
5. **Proxy Issues**: Verify proxy configuration and connectivity

### Debug Commands

```python
# Enable debug logging
import logging
logging.getLogger("playwright").setLevel(logging.DEBUG)
logging.getLogger("browser").setLevel(logging.DEBUG)

# Take screenshot for debugging
screenshot = await context.take_screenshot()
with open("debug_screenshot.png", "wb") as f:
    f.write(screenshot)

# Get DOM snapshot for analysis
dom_snapshot = await context.get_dom_snapshot()
import json
with open("debug_dom.json", "w") as f:
    json.dump(dom_snapshot, f, indent=2)
```

## Next Steps

- Review the complete API documentation in `contracts/browser-lifecycle-api.md`
- Check the data model in `data-model.md`
- Implement specific use cases using the patterns shown above
- Integrate with existing selector engine and observability systems
- Configure production settings for stealth and resource management
