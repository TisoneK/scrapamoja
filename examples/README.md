# Examples

This directory contains practical examples demonstrating core browser automation patterns and the complete browser manager lifecycle.

## Overview

These examples show:
- Browser initialization and configuration
- Navigation and page state management
- Action execution with selectors and form interaction
- **Selector engine integration with multi-strategy element location**
- Snapshot capture and storage
- Error handling and graceful degradation
- Resource cleanup and shutdown
- **Telemetry capture and debugging capabilities**

Each example is self-contained and designed to be educational—showing both successful execution paths and error handling strategies.

## Examples

### browser_lifecycle_example.py

A complete demonstration of the browser manager lifecycle from start to finish, **now enhanced with selector engine integration**.

**What it does:**
1. Initializes a browser instance with default configuration
2. Navigates to Wikipedia's homepage and waits for full page load
3. **Uses multi-strategy selector engine to locate and interact with page elements**
4. Executes a search query with robust element location and fallback patterns
5. Captures a snapshot of the search results page with selector operation metadata
6. **Collects comprehensive telemetry data on selector performance**
7. Gracefully closes the browser and releases all resources

**Selector Engine Features Demonstrated:**
- **Multi-strategy element location** (CSS, XPath, text-based selectors)
- **Confidence scoring** for element matching quality
- **Fallback patterns** when primary selectors fail
- **Error handling and retry logic** with exponential backoff
- **Telemetry collection** with strategy performance metrics
- **Debug mode** with detailed strategy attempt logging
- **Correlation IDs** for traceable operations

**Why it's useful:**
- Learn how the browser manager works end-to-end
- Understand initialization and cleanup patterns
- See real examples of navigation, action execution, and snapshot capture
- **Learn selector engine best practices and patterns**
- **Understand multi-strategy element location and confidence scoring**
- **See comprehensive error handling and fallback mechanisms**
- **Learn telemetry collection and performance monitoring**
- Validate your development environment is properly configured
- **Wikipedia is automation-friendly and has no bot detection**

**Running the example:**

```bash
# From the repository root:
python -m examples.browser_lifecycle_example

# Or directly:
python examples/browser_lifecycle_example.py

# With debug mode for detailed selector engine logging:
$env:DEBUG_SELECTOR=1
python -m examples.browser_lifecycle_example
```

**Expected output (with selector engine integration):**

```
============================================================
BROWSER LIFECYCLE EXAMPLE - Using BrowserManager
============================================================
Started: 2026-01-29 14:30:00

============================================================
STAGE 1: Initialize Browser Through BrowserManager
============================================================
  * Getting global BrowserManager singleton...
  * Creating BrowserConfiguration with stealth settings...
  * Creating browser session through manager...
  ✓ Browser initialized successfully in 2.15s
    - Session ID: 3887fc77-2e2e-4603-862b-f4e6c65899f4
    - Browser type: chromium
    - Headless: False

============================================================
STAGE 2: Navigate to Wikipedia
============================================================
  * Navigating to https://en.wikipedia.org...
  ✓ Navigation completed in 11.82s

🔍 Performing Wikipedia search for: 'Python programming'
Using selector engine with multi-strategy approach...
✅ Located search input using selector engine (Wikipedia search input field)
✅ Selector operation successful: Wikipedia search input field
   [selector_1234_5678] Strategy: css
   [selector_1234_5678] Confidence: 0.920
   [selector_1234_5678] Confidence Level: EXCELLENT
   [selector_1234_5678] 🎯 Excellent match - High confidence selector
   [selector_1234_5678] Duration: 45ms

✅ Located search results using selector engine (Wikipedia search result link)
✅ Selector operation successful: Wikipedia search result link
   [selector_1234_5678] Strategy: css
   [selector_1234_5678] Confidence: 0.880
   [selector_1234_5678] Confidence Level: GOOD
   [selector_1234_5678] ✅ Good match - Reliable selector
   [selector_1234_5678] Duration: 67ms

✅ Successfully completed Wikipedia search using selector engine

============================================================
STAGE 4: Capture Page Snapshot (using Core Module)
============================================================
  * Capturing rich snapshot using core module...
  ✓ Snapshot captured and saved in 0.02s
    - File: data/snapshots/wikipedia_search_20260129_143000.json

============================================================
LIFECYCLE COMPLETED SUCCESSFULLY
============================================================
Total execution time: 25.43s

📊 Selector Engine Telemetry:
  Total operations: 2
  Successful operations: 2
  Success rate: 100.00%
  Average confidence: 0.900
  Total duration: 112ms
  Average operation duration: 56.0ms
  Strategies used: css
  Fallback usage rate: 0.00%
  Correlation ID: selector_1234_5678

  Strategy Performance:
    CSS:
      Success rate: 100.00%
      Avg confidence: 0.900
      Avg duration: 56.0ms

📊 Telemetry data saved to: data/telemetry/selector_telemetry_3887fc77_20260129_143000.json
============================================================
```

## Selector Engine Integration

### Key Concepts

**Multi-Strategy Approach**: The selector engine tries multiple strategies in priority order:
1. **CSS Selectors** - Fast and precise for stable elements
2. **XPath Expressions** - Powerful for complex element relationships  
3. **Text-Based Matching** - Robust for dynamic content

**Confidence Scoring**: Each located element receives a confidence score (0.0-1.0) based on:
- Attribute matching accuracy
- Element visibility and interactivity
- Context relevance

**Fallback Patterns**: When primary strategies fail, the engine:
- Tries alternative selector configurations
- Implements exponential backoff retry logic
- Provides detailed error reporting
- Maintains workflow continuity

### Telemetry and Debugging

**Correlation IDs**: Each session gets a unique correlation ID for traceable operations.

**Performance Metrics**: Comprehensive tracking includes:
- Strategy success rates and timing
- Confidence score distributions
- Fallback usage patterns
- Operation duration analysis

**Debug Mode**: Enable with `$env:DEBUG_SELECTOR=1` for detailed:
- Strategy attempt logging
- Confidence score analysis
- Timing breakdown per strategy
- Error pattern identification

### Configuration Examples

**Basic Selector Configuration**:
```python
def get_search_config() -> SelectorConfiguration:
    strategies = [
        {
            "type": "css",
            "selector": "input#searchInput",
            "priority": 1,
            "expected_attributes": {"type": "search", "name": "search"}
        },
        {
            "type": "xpath", 
            "selector": "//input[@name='search']",
            "priority": 2,
            "expected_attributes": {"type": "search"}
        }
    ]
    return SelectorConfiguration("Search input field", strategies)
```

**Usage Pattern**:
```python
# Locate element with multi-strategy approach
search_input = await selector_integration.locate_element(
    page=page,
    config=get_search_config()
)

# Interact with error recovery
await selector_integration.interact_with_element(
    page=page,
    element=search_input,
    interaction_type="type",
    interaction_data={"text": "search term"}
)
```

**Expected output:**

```
============================================================
BROWSER LIFECYCLE EXAMPLE
============================================================
Started at: 2026-01-29 09:43:21

==================================================
STAGE 1: Initializing Browser
==================================================
  • Starting Playwright instance...
  • Launching browser with default configuration...
  • Creating browser context...
  • Creating new page...
  ✓ Browser initialized successfully in 0.75s
    - Browser type: Chromium (headless=True)
    - Page context created and ready for navigation

==================================================
STAGE 2: Navigating to Google
==================================================
  • Navigating to https://www.google.com...
  • Waiting for page elements to be available...
  ✓ Google homepage loaded successfully in 4.15s
    - Page title: Google
    - Current URL: https://www.google.com/
    - Search input element found and interactive

==================================================
STAGE 3: Executing Search Action
==================================================
  • Filling search input with query: 'Playwright browser automation'...
  • Submitting search form...
  • Waiting for search results to load...
  ✓ Search executed successfully in 15.09s
    - Search query: Playwright browser automation
    - Results page loaded and ready for snapshot

==================================================
STAGE 4: Capturing Page Snapshot
==================================================
  • Capturing page content...
  • Capturing page metadata...
  • Writing snapshot to data/snapshots/google_search_20260129_064341.json...
  ✓ Snapshot captured and saved in 0.02s
    - File: data/snapshots/google_search_20260129_064341.json
    - Page title: Playwright browser automation - Google
    - Content size: 88561 bytes

==================================================
STAGE 5: Cleaning Up
==================================================
  • Closing page...
  • Closing context...
  • Closing browser...
  • Stopping Playwright...
  ✓ Cleanup completed in 0.20s
    - All resources released
    - Browser process terminated

============================================================
EXAMPLE COMPLETED SUCCESSFULLY
============================================================
Total execution time: 20.21s

Stage timings:
  initialization    0.75s
  navigation        4.15s
  search           15.09s
  snapshot          0.02s
  cleanup           0.20s
  total            20.21s

Snapshot saved to: data/snapshots/google_search_20260129_064341.json
============================================================
```

## Quick Start

### Prerequisites

- Python 3.11+
- All project dependencies installed (see `requirements.txt`)
- Playwright browsers installed (`playwright install`)
- Network connectivity to access external sites

### Environment Setup

```bash
# 1. Ensure you're in the repository root
cd /path/to/scorewise/scraper

# 2. Install dependencies (if not already done)
pip install -r requirements.txt

# 3. Install Playwright browsers
playwright install

# 4. Run an example
python -m examples.browser_lifecycle_example
```

## Troubleshooting

### Timeout errors

**Problem**: Navigation or action execution times out  
**Cause**: Network connectivity issues, site load time, or page readiness condition  
**Solution**:
- Check network connectivity
- Verify the target site is accessible
- Check console output for detailed error messages
- Try running again (transient network issues)

### Element not found errors

**Problem**: Search element or input field not found  
**Cause**: Google's interface changed or page didn't fully load  
**Solution**:
- Verify Google's homepage is accessible and loads normally
- Check console output shows which selector failed
- Page structure may have changed—update selectors as needed

### Permission errors

**Problem**: Cannot write snapshot file (permission denied)  
**Cause**: No write access to `data/snapshots/` directory  
**Solution**:
- Verify `data/snapshots/` directory exists
- Check file permissions: `ls -la data/snapshots/`
- Ensure your user owns the directory: `chmod u+w data/snapshots/`

### Browser launch errors

**Problem**: Browser fails to launch  
**Cause**: Playwright browsers not installed  
**Solution**:
```bash
playwright install
```

### Dependency import errors

**Problem**: ModuleNotFoundError for project modules  
**Cause**: Python path not set correctly  
**Solution**:
```bash
# Run from repository root
cd /path/to/scorewise/scraper
python -m examples.browser_lifecycle_example
```

## API Reference

### Core APIs Used

The example demonstrates these core project APIs:

#### Browser Manager

```python
from src.browser.manager import BrowserManager

# Initialize browser with default config
browser = await BrowserManager.create()

# Cleanup and close
await browser.close()
```

#### Navigation

```python
# Navigate to a URL and wait for page load
await page.goto(url, wait_until="networkidle")
```

#### Action Execution

```python
# Execute an action on the page
await page.fill("input[name='q']", "search query")
await page.press("input[name='q']", "Enter")
```

#### Snapshot Capture

```python
# Capture page content and save snapshot
snapshot = await page.content()
snapshot_path = save_snapshot(snapshot)
```

## Next Steps

After running this example:

1. **Examine the code**: Read through `browser_lifecycle_example.py` to understand each step
2. **Modify it**: Try changing the search query or target URL
3. **Build on it**: Use patterns shown here in your own automation scripts
4. **Add features**: Extend the example with additional actions or error handling

## Learning Resources

- [Playwright documentation](https://playwright.dev/python/)
- Project browser manager API (see `src/browser/` module)
- Navigation patterns (see `src/navigation/` module)
- Selector engine (see `src/selectors/` module)
