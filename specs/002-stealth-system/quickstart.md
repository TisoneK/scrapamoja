# Quick Start: Stealth & Anti-Detection System

**Date**: 2026-01-27  
**Feature**: [002-stealth-system](spec.md)  
**Phase**: Phase 1 - Design

## Overview

The Stealth & Anti-Detection System masks automated browser control to prevent detection on protected websites like Flashscore. It integrates seamlessly with the Navigator module and provides production-ready anti-bot defenses out of the box.

**Key Components**:
1. **Fingerprint Normalizer** - Realistic device characteristics
2. **Proxy Manager** - Residential IP rotation with sticky sessions
3. **Behavior Emulator** - Human-like timing and interaction patterns
4. **Consent Handler** - Automatic GDPR/cookie consent processing
5. **Anti-Detection Masker** - Automation indicator removal

---

## Installation & Setup

### Python Version Requirement

```bash
python --version  # Must be 3.11 or later
```

### Dependencies

The stealth system has **zero external dependencies** beyond Playwright (which is already required):

```bash
pip install playwright>=1.40.0
```

### Enable Playwright Browsers

```bash
playwright install chromium
```

---

## Basic Usage

### 1. Initialize Stealth System

```python
from stealth import StealthSystem, StealthConfig
from playwright.async_api import async_playwright
import asyncio

async def scrape_with_stealth():
    # Create default stealth config (production-ready)
    config = StealthConfig(enabled=True)  # All stealth measures enabled by default
    
    # Initialize stealth system
    stealth = StealthSystem()
    await stealth.initialize(config)
    
    # Rest of your scraper...
    await stealth.shutdown()

asyncio.run(scrape_with_stealth())
```

### 2. Apply to Browser Context

```python
async def main():
    config = StealthConfig(enabled=True)
    stealth = StealthSystem()
    await stealth.initialize(config)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        
        # Apply stealth fingerprint to browser
        await stealth.apply_fingerprint_to_browser(context)
        
        page = await context.new_page()
        await page.goto("https://www.flashscore.com")
        
        # ... rest of scraping ...
        
        await context.close()
        await browser.close()
        await stealth.shutdown()
```

### 3. Handle Consent Dialogs

```python
# Auto-detect and accept consent dialogs
await page.goto("https://www.flashscore.com")

consent_handled = await stealth.process_consent_dialog(
    page, 
    match_id="flashscore-12345"
)

if consent_handled:
    print("GDPR consent processed successfully")
else:
    print("No consent dialog found (or already accepted)")
```

### 4. Manage Proxy Sessions

```python
# Create sticky proxy session for match
proxy_session = await stealth.create_proxy_session(match_id="match-123")
print(f"Using residential IP: {proxy_session.ip_address}")

# All requests within this session use same IP
await page.goto("https://www.flashscore.com/match/12345")
await page.goto("https://www.flashscore.com/match/12345/#summary")  # Same IP

# End session when match complete
await stealth.close_proxy_session(proxy_session.session_id)
# Next match will get different IP (after cooldown)
```

### 5. Emulate Human Behavior

```python
# Click with natural timing
await stealth.emulate_click(page, ".odds-button", match_id="match-123")

# Scroll naturally with pauses
await stealth.emulate_scroll(page, "down", amount=500, match_id="match-123")

# Random micro-delay between rapid actions
await stealth.add_micro_delay(match_id="match-123")
```

---

## Configuration

### Default Configuration (Production)

All stealth measures enabled with conservative settings:

```python
config = StealthConfig(
    enabled=True,  # Master switch
    
    # Fingerprinting
    fingerprint=None,  # Auto-generate realistic fingerprint
    fingerprint_consistency_level="moderate",  # Validate coherence
    
    # Proxy rotation
    proxy_enabled=True,
    proxy_rotation_strategy="per_match",  # Rotate per match
    proxy_cooldown_seconds=600,  # 10-minute cooldown
    proxy_provider="bright_data",  # Residential proxy provider
    
    # Human behavior
    behavior_enabled=True,
    behavior_intensity="moderate",
    click_hesitation_ms_range=(100, 500),
    scroll_variation=0.3,
    
    # Consent handling
    consent_enabled=True,
    consent_timeout_seconds=5,
    
    # Anti-detection
    anti_detection_enabled=True,
    mask_webdriver_property=True,
    mask_playwright_indicators=True,
    
    # Resilience
    graceful_degradation=True,
)
```

### YAML Configuration File

Create `config/stealth.yaml`:

```yaml
stealth:
  enabled: true
  
  fingerprint:
    consistency_level: "moderate"  # strict | moderate | relaxed
    # fingerprint properties auto-generated if not specified
  
  proxy:
    enabled: true
    rotation_strategy: "per_match"  # per_match | per_session
    cooldown_seconds: 600
    provider: "bright_data"
    bright_data:
      zone: "my_zone"
      country: "GB"  # 2-letter country code
  
  behavior:
    enabled: true
    intensity: "moderate"  # conservative | moderate | aggressive
    click_hesitation_range: [100, 500]  # min/max milliseconds
    scroll_variation: 0.3  # 0.0-1.0
    micro_delay_range: [10, 100]
  
  consent:
    enabled: true
    aggressive: false  # false=conservative, true=accept all
    timeout_seconds: 5
  
  anti_detection:
    enabled: true
    mask_webdriver: true
    mask_playwright: true
    mask_process: true
  
  graceful_degradation: true
  logging_level: "info"  # debug | info | warning
```

Load config:

```python
import yaml

with open("config/stealth.yaml") as f:
    config_dict = yaml.safe_load(f)

config = StealthConfig(**config_dict["stealth"])
stealth = StealthSystem()
await stealth.initialize(config)
```

### Behavior Intensity Profiles

**Conservative** - For high-risk targets:
```python
config = StealthConfig(
    behavior_intensity="conservative",
    click_hesitation_ms_range=(100, 500),  # Longer delays
    scroll_variation=0.5,
)
```

**Moderate** - Default (recommended):
```python
config = StealthConfig(behavior_intensity="moderate")
```

**Aggressive** - For low-risk scenarios:
```python
config = StealthConfig(
    behavior_intensity="aggressive",
    click_hesitation_ms_range=(50, 200),  # Shorter delays
)
```

### Disable Specific Measures

```python
# Disable proxy (useful for development without residential proxy)
config = StealthConfig(proxy_enabled=False)

# Disable behavior emulation (just use fingerprint + anti-detection)
config = StealthConfig(behavior_enabled=False)

# Disable consent handling (handle manually)
config = StealthConfig(consent_enabled=False)

# Minimal stealth (only anti-detection)
config = StealthConfig(
    proxy_enabled=False,
    behavior_enabled=False,
    consent_enabled=False,
)
```

---

## Development Without Residential Proxy

For development/testing without real residential proxy costs:

```python
config = StealthConfig(
    proxy_enabled=False,  # No proxy
    behavior_enabled=True,  # Still emulate behavior
    consent_enabled=True,  # Still handle consent
    anti_detection_enabled=True,  # Still mask automation
)

stealth = StealthSystem()
await stealth.initialize(config)
```

Or use mock provider:

```python
config = StealthConfig(
    proxy_provider="mock",  # Built-in mock provider
)
```

---

## Structured Logging

All stealth events are logged as JSON:

```
data/logs/stealth-{run_id}.json
```

Example log entries:

```json
{
  "timestamp": "2026-01-27T14:32:15.123Z",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "match_id": "flashscore-123456",
  "event_type": "fingerprint_initialized",
  "severity": "info",
  "subsystem": "fingerprint",
  "duration_ms": 45,
  "success": true,
  "details": {
    "browser": "chrome",
    "platform": "Windows",
    "consistency_check_passed": true
  }
}
```

Query logs for debugging:

```python
events = await stealth.get_event_log(run_id="550e8400...", match_id="flashscore-123456")

for event in events:
    if event.event_type == "proxy_rotated":
        print(f"IP rotated from {event.details['old_session_id']} to {event.details['new_session_id']}")
```

---

## Common Scenarios

### Scenario 1: Scrape Single Match with Full Stealth

```python
async def scrape_match(match_url: str) -> dict:
    config = StealthConfig(enabled=True)
    stealth = StealthSystem()
    await stealth.initialize(config)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        await stealth.apply_fingerprint_to_browser(context)
        page = await context.new_page()
        
        # Create sticky proxy session for this match
        session = await stealth.create_proxy_session(match_url.split("/")[-1])
        
        # Navigate with stealth
        await page.goto(match_url)
        
        # Handle consent
        await stealth.process_consent_dialog(page, match_id=match_url)
        
        # Emulate human navigation
        await stealth.emulate_click(page, "[data-test='summary-tab']", match_url)
        await stealth.add_micro_delay(match_url)
        
        # Extract data...
        summary = await page.locator(".summary-content").inner_html()
        
        # Cleanup
        await stealth.close_proxy_session(session.session_id)
        await context.close()
        await browser.close()
        await stealth.shutdown()
        
        return {"summary": summary}
```

### Scenario 2: Scrape Multiple Matches with IP Rotation

```python
async def scrape_matches(match_urls: list[str]):
    config = StealthConfig(enabled=True, proxy_rotation_strategy="per_match")
    stealth = StealthSystem()
    await stealth.initialize(config)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        await stealth.apply_fingerprint_to_browser(context)
        page = await context.new_page()
        
        results = []
        for match_url in match_urls:
            match_id = match_url.split("/")[-1]
            
            # New IP for each match
            session = await stealth.create_proxy_session(match_id)
            
            try:
                await page.goto(match_url)
                await stealth.process_consent_dialog(page, match_id)
                
                # Extract data...
                data = await extract_match_data(page, stealth, match_id)
                results.append(data)
            except Exception as e:
                print(f"Failed to scrape {match_id}: {e}")
            finally:
                await stealth.close_proxy_session(session.session_id)
        
        await context.close()
        await browser.close()
        await stealth.shutdown()
        
        return results
```

### Scenario 3: Development Mode Without Proxy

```python
async def develop_scraper():
    # No proxy, just test content extraction
    config = StealthConfig(
        proxy_enabled=False,
        consent_enabled=True,
        anti_detection_enabled=True,
    )
    stealth = StealthSystem()
    await stealth.initialize(config)
    
    # ... rest of scraping code ...
```

---

## Troubleshooting

### Issue: Proxy Connection Failed

**Symptoms**: `ProxyConnectionError: Proxy IP blocked after 3 retries`

**Solution**:
1. Check proxy provider credentials in config
2. Verify country/zone configuration
3. Check if IP is actually available
4. Review logs: `data/logs/stealth-{run_id}.json` for proxy_rotated events
5. Temporarily disable proxy for testing: `proxy_enabled: false`

### Issue: Consent Dialog Not Detected

**Symptoms**: Dialog visible but not closed automatically

**Solution**:
1. Increase timeout: `consent_timeout_seconds: 10`
2. Register custom pattern:
   ```python
   stealth.consent_handler.register_pattern(
       "custom_consent",
       ["[id='my-consent-modal']", "button:has-text('OK')"]
   )
   ```
3. Handle manually if consent detection fails (check `process_consent_dialog` return value)

### Issue: Stealth Measures Detected

**Symptoms**: Website blocks scraper despite stealth enabled

**Validate stealth measures**:
```python
warnings = await stealth.validate_stealth_measures(page, match_id="test")
if warnings:
    print(f"Stealth issues detected:")
    for w in warnings:
        print(f"  - {w}")
```

### Issue: Fingerprint Coherence Error

**Symptoms**: `FingerprintValidationError: Fingerprint is incoherent`

**Solution**:
1. Let system auto-generate: don't specify fingerprint properties manually
2. If providing custom fingerprint, ensure:
   - User-agent matches browser type
   - Platform matches OS in user-agent
   - Language is valid ISO code (e.g., en-US)
   - Timezone is valid IANA timezone
   - Screen resolution is realistic
3. Use safe defaults:
   ```python
   config.fingerprint = stealth.fingerprint_normalizer.get_safe_defaults()
   ```

### Issue: High Detection Rate

**Symptoms**: Scraper works briefly then gets blocked

**Increase stealth intensity**:
```python
config = StealthConfig(
    behavior_intensity="conservative",  # More realistic timing
    consent_aggressive=False,  # More conservative consent handling
    click_hesitation_ms_range=(200, 800),  # Longer delays
)
```

---

## Performance Notes

### Initialization Time

- Stealth initialization: ~50-200ms (proxy connection may add 500-2000ms)
- Per-click overhead: ~150-400ms (due to hesitation delay)
- Per-scroll overhead: variable (depends on scroll distance and pause)
- Per-consent-dialog: ~500-2000ms (detection + dialog handling)

### Resource Usage

- Memory: ~5-10MB (fingerprint data + session state)
- Network: Minimal (only stealth measurements add traffic, not data)
- CPU: Low (delays are sleep-based, not CPU-bound)

### Optimization Tips

1. **Minimize consent dialog processing**: Set `consent_timeout_seconds: 3` if dialogs always present
2. **Reduce micro-delays**: Use `aggressive` intensity for low-risk targets
3. **Disable unused measures**: If target doesn't fingerprint, disable that subsystem
4. **Pool browser instances**: Reuse contexts/pages across multiple matches within session

---

## Next Steps

1. **Review Data Model** - See [data-model.md](data-model.md) for entity definitions
2. **Review API Contracts** - See [contracts/stealth-system-api.md](contracts/stealth-system-api.md) for full interface
3. **Read Research** - See [research.md](research.md) for technical decisions and alternatives
4. **Integration** - Integrate with Navigator module after implementation
5. **Testing** - Validate against real Flashscore detection systems
