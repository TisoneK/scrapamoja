# Smart Plan: Tackling Flashscore Skeleton Content Loading

## 🎯 Problem Analysis

### Current Issue:
- Flashscore loads skeleton content first, then dynamic content via JavaScript
- Browser waits for `domcontentloaded` which times out at 30 seconds
- Need to wait for **specific elements** instead of full page load
- Main content container loads but appears empty initially

### Root Cause:
Flashscore uses a progressive loading strategy:
1. **Skeleton HTML** loads immediately (fast)
2. **JavaScript** then populates content dynamically (slower)
3. **`domcontentloaded`** fires when skeleton is ready (too early)
4. **Main content** appears later via JS/AJAX calls

## 🚀 Smart Implementation Plan

### Strategy: Progressive Element Waiting
Instead of waiting for full page load, wait for specific elements in stages:

#### Stage 1: Navigate (No Wait)
```python
await self.page.goto("https://www.flashscore.com", wait_until=None)
```

#### Stage 2: Wait for Skeleton Container
```python
# Wait for main container (fast, appears quickly)
await self.page.wait_for_selector('.mainContent', timeout=5000)
```

#### Stage 3: Wait for Content Area
```python
# Wait for content area (medium wait)
await self.page.wait_for_selector('.sportName', timeout=10000)
```

#### Stage 4: Wait for Dynamic Content
```python
# Wait for actual match elements (short wait, specific)
await self.page.wait_for_selector('.event__match', timeout=8000)
```

#### Stage 5: Handle Cookie Consent
```python
# Handle cookie consent if present
await self._handle_cookie_consent()
```

## 🔧 Implementation Details

### Modified `open_home()` Method:
```python
async def open_home(self):
    """Navigate to Flashscore home page with progressive waiting."""
    from src.observability.logger import get_logger
    logger = get_logger("flashscore.flow")
    
    logger.info("Starting navigation to Flashscore home page...")
    
    try:
        # Stage 1: Navigate without waiting
        await self.page.goto("https://www.flashscore.com", wait_until=None)
        logger.info("Successfully navigated to Flashscore home page")
        
        # Stage 2: Wait for skeleton container (fast)
        logger.info("Waiting for main content container...")
        try:
            await self.page.wait_for_selector('.mainContent', timeout=5000)
            logger.info("Main container found")
        except Exception as e:
            logger.warning(f"Main container not found: {e}")
        
        # Stage 3: Wait for content area (medium)
        logger.info("Waiting for content area...")
        try:
            await self.page.wait_for_selector('.sportName', timeout=10000)
            logger.info("Content area found")
        except Exception as e:
            logger.warning(f"Content area not found: {e}")
        
        # Stage 4: Wait for dynamic content (short)
        logger.info("Waiting for dynamic content...")
        try:
            await self.page.wait_for_selector('.event__match', timeout=8000)
            logger.info("Dynamic content found")
        except Exception as e:
            logger.warning(f"Dynamic content not found: {e}")
        
        # Stage 5: Handle cookie consent
        logger.info("Proceeding to handle cookie consent...")
        await self._handle_cookie_consent()
        logger.info("Home page navigation completed")
        
    except Exception as e:
        logger.error(f"Failed to navigate to home page: {e}")
        raise
```

## 🎯 Benefits of This Approach

### ✅ Advantages:
1. **Breaks timeout into smaller chunks** (5s + 10s + 8s = 23s total vs 30s)
2. **More resilient** - can fail at specific stages and continue
3. **Better error handling** - know exactly which stage failed
4. **Faster detection** - don't wait for full page when skeleton is ready
5. **Handles Flashscore's pattern** - works with progressive loading

### ⚠️ Fallback Strategy:
If progressive waiting fails, implement fallback:
```python
# Fallback: Try original method with longer timeout
await self.page.goto("https://www.flashscore.com", wait_until="domcontentloaded")
```

## 🔄 Alternative Approaches

### Option 1: Network Interception
- Intercept network calls to detect when content API completes
- More complex but most accurate

### Option 2: Mutation Observer
- Use JavaScript to monitor DOM changes
- Wait for specific content to appear via observer

### Option 3: Simple Timeout Increase
- Increase from 30s to 60s (quickest fix)
- Less robust but simple

## 📋 Implementation Priority

1. **High Priority**: Progressive element waiting (recommended)
2. **Medium Priority**: Simple timeout increase (quick fix)
3. **Low Priority**: Network interception (complex)

## 🚀 Next Steps

1. **Implement progressive waiting** in `open_home()` method
2. **Add detailed logging** for each stage
3. **Test with multiple runs** to verify reliability
4. **Monitor success rates** and adjust timeouts as needed
5. **Document the approach** for future reference

## 📊 Success Metrics

Track these metrics to validate the approach:
- **Stage 1 success rate**: Navigation without wait
- **Stage 2 success rate**: Skeleton container detection
- **Stage 3 success rate**: Content area detection  
- **Stage 4 success rate**: Dynamic content detection
- **Overall success rate**: Complete page load
- **Average load time**: Total time for all stages

This plan addresses the core issue of Flashscore's progressive loading pattern while maintaining robustness and good error handling.
