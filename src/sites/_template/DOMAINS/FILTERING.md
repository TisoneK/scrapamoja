# Filtering Domain Documentation

The Filtering domain handles all aspects of content filtering, search refinement, and data filtering operations, from simple date filtering to complex multi-criteria filtering.

## 🎯 Purpose

Filtering flows are responsible for:
- Date and time filtering
- Category and sport filtering
- Search refinement and advanced filtering
- Multi-criteria filtering
- Filter state management

## 📁 Domain Structure

```
flows/filtering/
├── __init__.py              # Domain registry
├── date_filter.py          # Date filtering logic
├── sport_filter.py         # Sport filtering logic
└── competition_filter.py   # Competition filtering
```

## 🔧 Core Concepts

### Base Filtering Flow
All filtering flows extend the base filtering functionality:

```python
from src.sites.base.flow import BaseFlow

class FilteringFlow(BaseFlow):
    async def apply_filter(self, filter_name: str, filter_value: str):
        """Apply a single filter."""
        filter_element = await self.selector_engine.find(
            self.page, f"filter_{filter_name}"
        )
        
        if filter_element:
            await filter_element.select_option(filter_value)
            await self.page.wait_for_timeout(2000)
            return True
        return False
    
    async def clear_all_filters(self):
        """Clear all active filters."""
        clear_button = await self.selector_engine.find(
            self.page, "clear_filters_button"
        )
        
        if clear_button:
            await clear_button.click()
            await self.page.wait_for_timeout(2000)
```

### Filter State Management
Track and manage filter states:

```python
class FilterState:
    def __init__(self):
        self.active_filters = {}
        self.filter_history = []
    
    def add_filter(self, filter_name: str, filter_value: str):
        """Add a filter to the state."""
        self.active_filters[filter_name] = filter_value
        self.filter_history.append({
            'action': 'add',
            'filter': filter_name,
            'value': filter_value,
            'timestamp': datetime.now()
        })
    
    def remove_filter(self, filter_name: str):
        """Remove a filter from the state."""
        if filter_name in self.active_filters:
            del self.active_filters[filter_name]
            self.filter_history.append({
                'action': 'remove',
                'filter': filter_name,
                'timestamp': datetime.now()
            })
```

## 📋 Filtering Patterns

### 1. Date Filtering
Filter content by date ranges and specific dates:

```python
class DateFilteringFlow(FilteringFlow):
    async def filter_by_date_range(self, start_date: str, end_date: str):
        """Filter content by date range."""
        # Open date filter
        date_filter_button = await self.selector_engine.find(
            self.page, "date_filter_button"
        )
        
        if date_filter_button:
            await date_filter_button.click()
            await self.page.wait_for_timeout(1000)
        
        # Set start date
        start_date_input = await self.selector_engine.find(
            self.page, "start_date_input"
        )
        
        if start_date_input:
            await start_date_input.clear()
            await start_date_input.type(start_date)
        
        # Set end date
        end_date_input = await self.selector_engine.find(
            self.page, "end_date_input"
        )
        
        if end_date_input:
            await end_date_input.clear()
            await end_date_input.type(end_date)
        
        # Apply filter
        apply_button = await self.selector_engine.find(
            self.page, "apply_date_filter"
        )
        
        if apply_button:
            await apply_button.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_relative_date(self, relative_option: str):
        """Filter by relative date (today, yesterday, this week, etc.)."""
        relative_date_button = await self.selector_engine.find(
            self.page, f"relative_date_{relative_option}"
        )
        
        if relative_date_button:
            await relative_date_button.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_last_n_days(self, days: int):
        """Filter content for the last N days."""
        # Open date filter
        date_filter_button = await self.selector_engine.find(
            self.page, "date_filter_button"
        )
        
        if date_filter_button:
            await date_filter_button.click()
            await self.page.wait_for_timeout(1000)
        
        # Select last N days option
        last_days_radio = await self.selector_engine.find(
            self.page, "last_days_radio"
        )
        
        if last_days_radio:
            await last_days_radio.click()
        
        # Set number of days
        days_input = await self.selector_engine.find(
            self.page, "last_days_input"
        )
        
        if days_input:
            await days_input.clear()
            await days_input.type(str(days))
        
        # Apply filter
        apply_button = await self.selector_engine.find(
            self.page, "apply_date_filter"
        )
        
        if apply_button:
            await apply_button.click()
            await self.page.wait_for_timeout(2000)
```

### 2. Category/Sport Filtering
Filter content by categories or sports:

```python
class SportFilteringFlow(FilteringFlow):
    async def filter_by_sport(self, sport_name: str):
        """Filter content by a specific sport."""
        sport_filter = await self.selector_engine.find(
            self.page, f"sport_filter_{sport_name.lower()}"
        )
        
        if sport_filter:
            await sport_filter.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_multiple_sports(self, sport_list: list):
        """Filter content by multiple sports."""
        # Open multi-sport filter
        multi_sport_button = await self.selector_engine.find(
            self.page, "multi_sport_filter"
        )
        
        if multi_sport_button:
            await multi_sport_button.click()
            await self.page.wait_for_timeout(1000)
        
        # Select each sport
        for sport in sport_list:
            sport_checkbox = await self.selector_engine.find(
                self.page, f"sport_checkbox_{sport.lower()}"
            )
            
            if sport_checkbox:
                await sport_checkbox.check()
        
        # Apply filter
        apply_button = await self.selector_engine.find(
            self.page, "apply_sport_filter"
        )
        
        if apply_button:
            await apply_button.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_sport_category(self, category: str):
        """Filter by sport category (team sports, individual sports, etc.)."""
        category_filter = await self.selector_engine.find(
            self.page, f"sport_category_{category.lower()}"
        )
        
        if category_filter:
            await category_filter.click()
            await self.page.wait_for_timeout(2000)
    
    async def exclude_sport(self, sport_name: str):
        """Exclude a specific sport from results."""
        # Open exclude options
        exclude_button = await self.selector_engine.find(
            self.page, "exclude_sports_button"
        )
        
        if exclude_button:
            await exclude_button.click()
            await self.page.wait_for_timeout(1000)
        
        # Select sport to exclude
        exclude_checkbox = await self.selector_engine.find(
            self.page, f"exclude_sport_{sport_name.lower()}"
        )
        
        if exclude_checkbox:
            await exclude_checkbox.check()
        
        # Apply exclusion
        apply_button = await self.selector_engine.find(
            self.page, "apply_exclude_filter"
        )
        
        if apply_button:
            await apply_button.click()
            await self.page.wait_for_timeout(2000)
```

### 3. Competition Filtering
Filter content by competitions and leagues:

```python
class CompetitionFilteringFlow(FilteringFlow):
    async def filter_by_competition(self, competition_id: str):
        """Filter content by a specific competition."""
        competition_filter = await self.selector_engine.find(
            self.page, f"competition_filter_{competition_id}"
        )
        
        if competition_filter:
            await competition_filter.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_competition_type(self, comp_type: str):
        """Filter by competition type (league, cup, tournament)."""
        type_filter = await self.selector_engine.find(
            self.page, f"competition_type_{comp_type.lower()}"
        )
        
        if type_filter:
            await type_filter.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_country(self, country_name: str):
        """Filter competitions by country."""
        country_filter = await self.selector_engine.find(
            self.page, f"country_filter_{country_name.lower()}"
        )
        
        if country_filter:
            await country_filter.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_popular_competitions(self):
        """Filter to show only popular competitions."""
        popular_filter = await self.selector_engine.find(
            self.page, "popular_competitions_filter"
        )
        
        if popular_filter:
            await popular_filter.click()
            await self.page.wait_for_timeout(2000)
```

### 4. Multi-Criteria Filtering
Apply multiple filters simultaneously:

```python
class MultiCriteriaFilteringFlow(FilteringFlow):
    async def apply_complex_filter(self, filters: dict):
        """Apply multiple filters at once."""
        for filter_name, filter_value in filters.items():
            await self.apply_filter(filter_name, filter_value)
        
        # Apply all filters
        apply_button = await self.selector_engine.find(
            self.page, "apply_all_filters"
        )
        
        if apply_button:
            await apply_button.click()
            await self.page.wait_for_timeout(3000)
    
    async def save_filter_preset(self, preset_name: str, filters: dict):
        """Save a filter preset for later use."""
        preset_data = {
            'name': preset_name,
            'filters': filters,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store preset (implementation depends on storage method)
        await self.store_filter_preset(preset_data)
    
    async def load_filter_preset(self, preset_name: str):
        """Load and apply a saved filter preset."""
        preset_data = await self.get_filter_preset(preset_name)
        
        if preset_data:
            await self.apply_complex_filter(preset_data['filters'])
            return True
        
        return False
```

## 🎯 Use Cases

### Sports Site Filtering (Flashscore Example)
```python
class SportsFilteringFlow(DateFilteringFlow, SportFilteringFlow, CompetitionFilteringFlow):
    async def filter_live_matches(self, sport: str = None, competition: str = None):
        """Filter live matches by sport and competition."""
        # Navigate to live section
        await self.page.goto("https://flashscore.com/live")
        
        # Apply sport filter if specified
        if sport:
            await self.filter_by_sport(sport)
        
        # Apply competition filter if specified
        if competition:
            await self.filter_by_competition(competition)
        
        # Wait for filtered results
        await self.page.wait_for_selector(".live-matches", timeout=10000)
    
    async def filter_matches_by_date_and_sport(self, date_range: dict, sports: list):
        """Filter matches by date range and multiple sports."""
        # Apply date range filter
        await self.filter_by_date_range(
            date_range['start_date'],
            date_range['end_date']
        )
        
        # Apply sport filters
        await self.filter_by_multiple_sports(sports)
        
        # Wait for results
        await self.page.wait_for_selector(".match-list", timeout=10000)
```

### E-commerce Filtering
```python
class ProductFilteringFlow(FilteringFlow):
    async def filter_products(self, filters: dict):
        """Filter products by multiple criteria."""
        # Price range filter
        if 'price_range' in filters:
            await self.filter_by_price_range(filters['price_range'])
        
        # Category filter
        if 'category' in filters:
            await self.filter_by_category(filters['category'])
        
        # Brand filter
        if 'brand' in filters:
            await self.filter_by_brand(filters['brand'])
        
        # Rating filter
        if 'min_rating' in filters:
            await self.filter_by_rating(filters['min_rating'])
        
        # Apply all filters
        await self.apply_all_filters()
    
    async def filter_by_price_range(self, price_range: dict):
        """Filter products by price range."""
        min_price_input = await self.selector_engine.find(
            self.page, "min_price_input"
        )
        max_price_input = await self.selector_engine.find(
            self.page, "max_price_input"
        )
        
        if min_price_input:
            await min_price_input.clear()
            await min_price_input.type(str(price_range['min']))
        
        if max_price_input:
            await max_price_input.clear()
            await max_price_input.type(str(price_range['max']))
```

## ⚡ Performance Optimization

### 1. Batch Filter Application
Apply multiple filters efficiently:

```python
async def apply_filters_batch(self, filters: dict):
    """Apply multiple filters in a single operation."""
    # Build filter data structure
    filter_data = []
    
    for filter_name, filter_value in filters.items():
        filter_element = await self.selector_engine.find(
            self.page, f"filter_{filter_name}"
        )
        
        if filter_element:
            filter_data.append({
                'element': filter_element,
                'value': filter_value
            })
    
    # Apply all filters at once
    for filter_item in filter_data:
        await filter_item['element'].select_option(filter_item['value'])
    
    # Single wait for all filters to apply
    await self.page.wait_for_timeout(3000)
```

### 2. Smart Filter Detection
Detect available filters dynamically:

```python
async def detect_available_filters(self) -> dict:
    """Detect all available filters on the page."""
    available_filters = {}
    
    # Find all filter elements
    filter_elements = await self.page.query_selector_all("[data-filter]")
    
    for element in filter_elements:
        filter_name = await element.get_attribute('data-filter')
        filter_type = await element.get_attribute('data-filter-type')
        
        if filter_name:
            available_filters[filter_name] = {
                'type': filter_type,
                'element': element
            }
    
    return available_filters
```

## 🛡️ Error Handling

### Filter Application Error Recovery
```python
async def safe_apply_filter(self, filter_name: str, filter_value: str, retries: int = 3):
    """Apply filter with retry logic."""
    for attempt in range(retries):
        try:
            result = await self.apply_filter(filter_name, filter_value)
            if result:
                return True
        except Exception as e:
            self.logger.warning(f"Filter application failed (attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                await self.page.wait_for_timeout(1000)
    
    return False
```

### Filter State Validation
```python
async def validate_filter_applied(self, filter_name: str, expected_value: str) -> bool:
    """Validate that a filter was applied correctly."""
    active_filter = await self.selector_engine.find(
        self.page, f"active_filter_{filter_name}"
    )
    
    if active_filter:
        actual_value = await active_filter.inner_text()
        return expected_value in actual_value
    
    return False
```

## 📊 Best Practices

### 1. Filter Management
- Track filter states for debugging
- Implement filter presets for common combinations
- Provide clear filter removal options

### 2. Performance
- Apply filters in batches when possible
- Use smart waiting strategies
- Cache filter detection results

### 3. Error Handling
- Implement retry logic for failed filter applications
- Validate filter states after application
- Provide fallback filter methods

### 4. User Experience
- Show filter loading states
- Provide clear filter feedback
- Allow easy filter modification

## 🔍 Testing Filtering Flows

### Unit Tests
```python
async def test_date_filtering():
    """Test date filtering functionality."""
    flow = DateFilteringFlow()
    await flow.setup()
    
    # Mock date filter elements
    await flow.page.set_content("""
        <div>
            <button id="date_filter_button">Date Filter</button>
            <input id="start_date_input" type="date">
            <input id="end_date_input" type="date">
            <button id="apply_date_filter">Apply</button>
        </div>
    """)
    
    # Apply date range filter
    await flow.filter_by_date_range("2024-01-01", "2024-01-31")
    
    # Verify filter was applied
    start_input = await flow.page.query_selector("#start_date_input")
    start_value = await start_input.get_attribute('value')
    
    assert start_value == "2024-01-01"
```

### Integration Tests
```python
async def test_multi_criteria_filtering():
    """Test multi-criteria filtering."""
    flow = MultiCriteriaFilteringFlow()
    await flow.setup()
    
    # Navigate to page with filters
    await flow.page.goto("https://example.com/search")
    
    # Apply multiple filters
    filters = {
        'category': 'electronics',
        'price_range': {'min': 100, 'max': 500},
        'brand': 'samsung'
    }
    
    await flow.apply_complex_filter(filters)
    
    # Verify results are filtered
    results = await flow.page.query_selector_all(".search-result")
    assert len(results) > 0  # Should have filtered results
```

## 📚 Additional Resources

- [Navigation Domain](./NAVIGATION.md)
- [Extraction Domain](./EXTRACTION.md)
- [Authentication Domain](./AUTHENTICATION.md)
- [Real-World Examples](../REAL_WORLD_EXAMPLES.md)
