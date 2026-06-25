# Stealth & Anti-Detection System

Anti-detection and evasion subsystem for the Scorewise scraper. Masks automation indicators, emulates human behavior, rotates proxies, handles consent dialogs, and normalizes browser fingerprints to bypass advanced bot detection systems.

## Architecture

The system consists of 5 independent subsystems coordinated by the `StealthSystem` class:

### 1. Fingerprint Normalizer
Spoofs and maintains consistent browser fingerprints across requests.

**Responsibilities:**
- Generate realistic browser fingerprints (user agent, platform, plugins, screen size)
- Maintain consistency level (strict, moderate, random) to avoid detection
- Apply fingerprint to Playwright browser context
- Log fingerprint changes for audit trail

**Key Classes:**
- `BrowserFingerprint`: Device property data structure
- `FingerprintNormalizer`: Generation and application logic

### 2. Proxy Manager
Handles proxy rotation and session management.

**Responsibilities:**
- Rotate proxies per match, per session, or on-demand
- Manage proxy sessions with TTL and failure tracking
- Apply proxy settings to browser context
- Gracefully degrade if proxy provider unavailable

**Key Classes:**
- `ProxySession`: Proxy session state with timing and failure tracking
- `ProxyManager`: Rotation and session management

### 3. Behavior Emulator
Simulates natural human interaction patterns.

**Responsibilities:**
- Add hesitation to clicks and form submissions
- Vary scroll speed and direction patterns
- Add micro-delays between operations
- Simulate natural mouse movements

**Key Classes:**
- `BehaviorEmulator`: Interaction emulation logic
- `BehaviorIntensity`: Conservative, moderate, aggressive settings

### 4. Consent Handler
Auto-detects and accepts cookie consent dialogs.

**Responsibilities:**
- Detect common consent dialog patterns (iframes, modals, buttons)
- Accept consent with configurable aggressiveness
- Handle regional consent variations (GDPR, CCPA)
- Log accepted consent metadata

**Key Classes:**
- `ConsentHandler`: Detection and acceptance logic

### 5. Anti-Detection Masker
Masks webdriver and automation indicators.

**Responsibilities:**
- Mask `navigator.webdriver` property
- Remove Playwright-specific indicators from CDP
- Hide Chrome DevTools Protocol exposure
- Override `navigator.plugins` and `navigator.languages`

**Key Classes:**
- `AntiDetectionMasker`: Masking logic

## Configuration

Configuration is managed through `StealthConfig` dataclass with 25+ settings covering all subsystems.

### Predefined Configurations

```python
from src.stealth.config import get_config_by_name

# Production configuration (balanced)
config = get_config_by_name("default")

# Development (no proxy, debug logging)
config = get_config_by_name("development")

# High-risk targets (strict fingerprints, long cooldowns)
config = get_config_by_name("conservative")

# Low-risk targets (skip masking, aggressive consent)
config = get_config_by_name("aggressive")
```

### Custom Configuration

```python
from src.stealth.types import StealthConfig, BehaviorIntensity

config = StealthConfig(
    enabled=True,
    proxy_enabled=True,
    proxy_cooldown_seconds=1200,
    behavior_intensity=BehaviorIntensity.CONSERVATIVE,
    consent_aggressive=False,
    anti_detection_enabled=True,
)

# Validate before use
valid, errors = config.validate()
if not valid:
    print(f"Invalid config: {errors}")
```

## Usage

### Basic Usage

```python
import asyncio
from src.stealth.coordinator import StealthSystem
from src.stealth.config import get_config_by_name

async def scrape_with_stealth():
    config = get_config_by_name("default")
    
    async with StealthSystem(config) as stealth:
        # Get fingerprint and proxy
        fingerprint = await stealth.get_browser_fingerprint()
        proxy = await stealth.get_proxy_session()
        
        # Create Playwright browser with stealth settings
        browser = await p.chromium.launch(
            proxy=proxy.proxy_url if proxy else None,
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        # Apply stealth measures to page
        await stealth.normalize_dom_tree(page)
        await stealth.normalize_network_behavior(page)
        
        # Navigate and handle consent
        await page.goto("https://target.com")
        await stealth.handle_consent_dialogs(page)
        
        # Check bot detection risk before scraping
        risk = await stealth.check_bot_detection_status(page)
        if risk["detection_risk"] < 50:
            # Proceed with scraping
            pass
        else:
            # Log and degrade gracefully
            await stealth.emit_event(
                "high_detection_risk",
                severity="warning",
                details=risk,
            )
        
        await browser.close()

asyncio.run(scrape_with_stealth())
```

### With Context Manager

The `StealthSystem` supports async context manager protocol for automatic initialization and cleanup:

```python
async with StealthSystem(config) as stealth:
    # System initialized here
    fingerprint = await stealth.get_browser_fingerprint()
    # System cleaned up on exit
```

## Event Logging

All stealth operations emit structured events for audit trails and debugging.

```python
from src.stealth.events import EventBuilder

# Get event builder
builder = EventBuilder(run_id="run-123")

# Create events
event = builder.create_event(
    event_type="proxy_rotated",
    severity="info",
    details={"old_ip": "1.2.3.4", "new_ip": "5.6.7.8"},
)

# Publish to subscribers
stealth.publisher.publish(event)
```

## Testing

### Unit Tests

Test individual subsystems in isolation:

```bash
pytest tests/unit/stealth/ -v
```

### Integration Tests

Test stealth measures against real target websites:

```bash
pytest tests/integration/stealth/ -v -k "flashscore"
```

Note: Integration tests require real proxy provider credentials and network access.

## Troubleshooting

### Issue: "High detection risk" warnings
**Cause:** Fingerprint inconsistencies or missing anti-detection measures
**Solution:** 
- Set `fingerprint_consistency_level` to "strict"
- Ensure `anti_detection_enabled=True`
- Check proxy is rotating correctly

### Issue: Consent dialogs not being accepted
**Cause:** Non-standard dialog patterns or aggressive website
**Solution:**
- Set `consent_aggressive=True` for aggressive sites
- Increase `consent_timeout_seconds` for slow-loading dialogs
- Review consent logs to identify pattern

### Issue: Proxy connection errors
**Cause:** Provider credentials invalid or IP not whitelisted
**Solution:**
- Check `proxy_provider_config` has correct credentials
- Verify proxy provider whitelist includes your IP
- Fall back to development config without proxy

## Dependencies

- `playwright`: Async browser automation
- `pyyaml`: Configuration file parsing
- `dataclasses`: Type-safe configuration (Python 3.10+)

## Related Files

- [Data Model](../specs/001-selector-engine/data-model.md): Entity definitions
- [API Contract](../specs/001-selector-engine/contracts/stealth-system-api.md): Public interface
- [Configuration](config.py): Default and custom configurations
- [Event Logging](events.py): Audit trail and observability
