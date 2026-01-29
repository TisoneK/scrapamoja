# Examples

This directory contains practical examples demonstrating core browser automation patterns and the complete browser manager lifecycle.

## Overview

These examples show:
- Browser initialization and configuration
- Navigation and page state management
- Action execution with selectors and form interaction
- Snapshot capture and storage
- Error handling and graceful degradation
- Resource cleanup and shutdown

Each example is self-contained and designed to be educational—showing both successful execution paths and error handling strategies.

## Examples

### browser_lifecycle_example.py

A complete demonstration of the browser manager lifecycle from start to finish.

**What it does:**
1. Initializes a browser instance with default configuration
2. Navigates to Google's homepage and waits for full page load
3. Executes a search query by interacting with the search form
4. Captures a snapshot of the search results page
5. Gracefully closes the browser and releases all resources

**Why it's useful:**
- Learn how the browser manager works end-to-end
- Understand initialization and cleanup patterns
- See real examples of navigation, action execution, and snapshot capture
- Validate your development environment is properly configured

**Running the example:**

```bash
# From the repository root:
python -m examples.browser_lifecycle_example

# Or directly:
python examples/browser_lifecycle_example.py
```

**Expected output:**

```
Browser Lifecycle Example
=========================

Initializing browser...
  ✓ Browser initialized in 2.1s
  
Navigating to Google...
  ✓ Google homepage loaded in 1.5s
  
Executing search...
  ✓ Search submitted in 0.8s
  ✓ Results loaded in 2.3s
  
Capturing snapshot...
  ✓ Snapshot saved to data/snapshots/[timestamp].json
  
Cleaning up...
  ✓ Browser closed and resources released

Completed in 6.7s
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
