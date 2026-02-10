# Navigation Domain Documentation

The Navigation domain handles all aspects of moving through websites, from simple page transitions to complex SPA navigation patterns.

## 🎯 Purpose

Navigation flows are responsible for:
- Page transitions and routing
- Menu interactions and tab switching
- Complex navigation patterns (breadcrumbs, pagination)
- SPA navigation handling
- Loading state management

## 📁 Domain Structure

```
flows/navigation/
├── __init__.py              # Domain registry
├── match_nav.py            # Match page navigation
├── live_nav.py             # Live matches navigation
└── competition_nav.py      # Competition navigation
```

## 🔧 Core Concepts

### Base Navigation Flow
All navigation flows extend the base navigation functionality:

```python
from src.sites.base.flow import BaseFlow

class NavigationFlow(BaseFlow):
    async def navigate_to_page(self, url: str):
        """Navigate to a specific page with error handling."""
        try:
            await self.page.goto(url)
            await self.page.wait_for_load_state('networkidle')
            return True
        except Exception as e:
            self.logger.error(f"Navigation failed: {e}")
            return False
```

### Loading State Management
Handle different loading scenarios:

```python
async def wait_for_content_load(self, selector: str, timeout: int = 10000):
    """Wait for specific content to load."""
    try:
        await self.page.wait_for_selector(selector, timeout=timeout)
        return True
    except TimeoutError:
        self.logger.warning(f"Content not loaded: {selector}")
        return False
```

## 📋 Navigation Patterns

### 1. Simple Page Navigation
Best for static sites and basic navigation:

```python
async def navigate_to_home(self):
    """Navigate to home page."""
    await self.page.goto("https://example.com")
    await self.page.wait_for_load_state('networkidle')

async def navigate_to_section(self, section: str):
    """Navigate to a specific section."""
    url = f"https://example.com/{section}"
    await self.navigate_to_page(url)
```

### 2. Menu and Tab Navigation
Handle dropdown menus and tab switching:

```python
async def navigate_via_menu(self, menu_item: str):
    """Navigate using menu interaction."""
    # Open menu
    menu_button = await self.selector_engine.find(self.page, "main_menu")
    await menu_button.click()
    
    # Wait for menu items to appear
    await self.page.wait_for_selector(".menu-item", timeout=5000)
    
    # Click specific menu item
    menu_item_element = await self.selector_engine.find(
        self.page, f"menu_item_{menu_item}"
    )
    await menu_item_element.click()
    
    # Wait for navigation to complete
    await self.page.wait_for_load_state('networkidle')

async def switch_tab(self, tab_name: str):
    """Switch to a specific tab."""
    tab_element = await self.selector_engine.find(
        self.page, f"tab_{tab_name}"
    )
    await tab_element.click()
    
    # Wait for tab content to load
    await self.page.wait_for_selector(f".tab-content-{tab_name}")
```

### 3. SPA Navigation
Handle Single Page Application navigation:

```python
async def spa_navigate(self, route: str):
    """Navigate within SPA using routing."""
    # SPA navigation often requires JavaScript execution
    await self.page.evaluate(f"window.router.push('{route}')")
    
    # Wait for SPA content to update
    await self.page.wait_for_timeout(2000)
    
    # Verify navigation was successful
    current_route = await self.page.evaluate("window.router.currentRoute")
    return current_route == route

async def handle_spa_loading(self):
    """Handle SPA loading indicators."""
    # Wait for loading indicator to disappear
    await self.page.wait_for_function(
        "() => !document.querySelector('.loading-indicator')",
        timeout=15000
    )
```

### 4. Breadcrumb Navigation
Navigate using breadcrumb trails:

```python
async def navigate_breadcrumb(self, breadcrumb_path: list):
    """Navigate using breadcrumb trail."""
    for crumb in breadcrumb_path:
        breadcrumb_element = await self.selector_engine.find(
            self.page, f"breadcrumb_{crumb}"
        )
        await breadcrumb_element.click()
        await self.page.wait_for_timeout(1000)
```

## 🎯 Use Cases

### Sports Sites (Flashscore Example)
```python
class MatchNavigationFlow(NavigationFlow):
    async def navigate_to_match(self, match_id: str):
        """Navigate to specific match page."""
        await self.page.goto(f"https://flashscore.com/match/{match_id}")
        await self.wait_for_content_load(".match-content")
    
    async def navigate_to_live_match(self, match_id: str):
        """Navigate to live match with real-time data."""
        await self.page.goto(f"https://flashscore.com/live/match/{match_id}")
        await self.wait_for_content_load(".live-score")
```

### E-commerce Sites
```python
class ProductNavigationFlow(NavigationFlow):
    async def navigate_to_category(self, category: str):
        """Navigate to product category."""
        await self.navigate_via_menu(category)
        await self.wait_for_content_load(".product-grid")
    
    async def navigate_to_product(self, product_id: str):
        """Navigate to specific product page."""
        await self.page.goto(f"https://shop.com/product/{product_id}")
        await self.wait_for_content_load(".product-details")
```

### News Sites
```python
class ArticleNavigationFlow(NavigationFlow):
    async def navigate_to_article(self, article_id: str):
        """Navigate to news article."""
        await self.page.goto(f"https://news.com/article/{article_id}")
        await self.wait_for_content_load(".article-content")
    
    async def navigate_to_category(self, category: str):
        """Navigate to news category."""
        await self.page.goto(f"https://news.com/category/{category}")
        await self.wait_for_content_load(".article-list")
```

## ⚡ Performance Optimization

### 1. Parallel Navigation
Navigate to multiple pages concurrently:

```python
async def navigate_to_multiple_pages(self, urls: list):
    """Navigate to multiple pages in parallel."""
    tasks = [self.navigate_to_page(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### 2. Smart Waiting
Use intelligent waiting strategies:

```python
async def smart_wait(self, condition_type: str, target: str):
    """Wait using the most appropriate method."""
    if condition_type == "selector":
        await self.page.wait_for_selector(target)
    elif condition_type == "url":
        await self.page.wait_for_url(f"*{target}*")
    elif condition_type == "function":
        await self.page.wait_for_function(target)
```

## 🛡️ Error Handling

### Common Navigation Errors
```python
async def safe_navigate(self, url: str, max_retries: int = 3):
    """Navigate with retry logic."""
    for attempt in range(max_retries):
        try:
            await self.page.goto(url)
            await self.page.wait_for_load_state('networkidle')
            return True
        except TimeoutError:
            if attempt == max_retries - 1:
                raise
            await self.page.wait_for_timeout(2000)
        except Exception as e:
            self.logger.error(f"Navigation error: {e}")
            raise
```

### Navigation Validation
```python
async def validate_navigation(self, expected_url_pattern: str):
    """Validate that navigation was successful."""
    current_url = self.page.url
    if expected_url_pattern not in current_url:
        raise NavigationError(
            f"Expected URL pattern '{expected_url_pattern}' not found in '{current_url}'"
        )
```

## 📊 Best Practices

### 1. Loading State Handling
- Always wait for content to load before proceeding
- Handle loading indicators and spinners
- Implement timeout handling

### 2. Error Recovery
- Implement retry logic for failed navigation
- Log navigation errors for debugging
- Provide fallback navigation methods

### 3. Performance
- Use efficient waiting strategies
- Avoid unnecessary page reloads
- Implement parallel navigation when possible

### 4. Maintainability
- Use descriptive method names
- Document navigation flows
- Separate complex navigation into smaller methods

## 🔍 Testing Navigation Flows

### Unit Tests
```python
async def test_navigate_to_match():
    """Test match navigation flow."""
    flow = MatchNavigationFlow()
    await flow.setup()
    
    result = await flow.navigate_to_match("12345")
    assert result is True
    assert "match/12345" in flow.page.url
```

### Integration Tests
```python
async def test_full_navigation_workflow():
    """Test complete navigation workflow."""
    flow = MatchNavigationFlow()
    await flow.setup()
    
    # Navigate to match
    await flow.navigate_to_match("12345")
    
    # Navigate to live view
    await flow.navigate_to_live_match("12345")
    
    # Verify final state
    assert "live" in flow.page.url
```

## 📚 Additional Resources

- [Extraction Domain](./EXTRACTION.md)
- [Filtering Domain](./FILTERING.md)
- [Authentication Domain](./AUTHENTICATION.md)
- [Real-World Examples](../REAL_WORLD_EXAMPLES.md)
