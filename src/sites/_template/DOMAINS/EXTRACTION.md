# Extraction Domain Documentation

The Extraction domain handles all aspects of data extraction and content processing from web pages, from simple text extraction to complex real-time data parsing.

## 🎯 Purpose

Extraction flows are responsible for:
- Content parsing and element extraction
- Data structure extraction (tables, lists, forms)
- Real-time data extraction
- Error handling and data validation
- Data transformation and normalization

## 📁 Domain Structure

```
flows/extraction/
├── __init__.py              # Domain registry
├── match_extract.py        # Match data extraction
├── odds_extract.py         # Betting odds extraction
└── stats_extract.py        # Statistics extraction
```

## 🔧 Core Concepts

### Base Extraction Flow
All extraction flows extend the base extraction functionality:

```python
from src.sites.base.flow import BaseFlow

class ExtractionFlow(BaseFlow):
    async def extract_text_content(self, selector: str) -> str:
        """Extract text content from an element."""
        element = await self.selector_engine.find(self.page, selector)
        if element:
            return await element.inner_text()
        return None
    
    async def extract_attribute(self, selector: str, attribute: str) -> str:
        """Extract attribute value from an element."""
        element = await self.selector_engine.find(self.page, selector)
        if element:
            return await element.get_attribute(attribute)
        return None
```

### Data Validation
Validate extracted data structure:

```python
async def validate_extracted_data(self, data: dict, required_fields: list) -> bool:
    """Validate that required fields are present in extracted data."""
    for field in required_fields:
        if field not in data or data[field] is None:
            self.logger.warning(f"Missing required field: {field}")
            return False
    return True
```

## 📋 Extraction Patterns

### 1. Simple Text Extraction
Extract basic text content:

```python
async def extract_article_title(self) -> str:
    """Extract article title."""
    title_element = await self.selector_engine.find(self.page, "article_title")
    return await title_element.inner_text() if title_element else None

async def extract_article_content(self) -> str:
    """Extract article body content."""
    content_element = await self.selector_engine.find(self.page, "article_content")
    return await content_element.inner_text() if content_element else None
```

### 2. Table Data Extraction
Extract structured data from tables:

```python
async def extract_table_data(self, table_selector: str) -> list:
    """Extract data from HTML table."""
    table = await self.selector_engine.find(self.page, table_selector)
    if not table:
        return []
    
    # Extract headers
    headers = []
    header_elements = await table.query_selector_all("thead th")
    for header in header_elements:
        headers.append(await header.inner_text())
    
    # Extract rows
    rows_data = []
    row_elements = await table.query_selector_all("tbody tr")
    
    for row in row_elements:
        row_data = {}
        cell_elements = await row.query_selector_all("td")
        
        for i, cell in enumerate(cell_elements):
            if i < len(headers):
                row_data[headers[i]] = await cell.inner_text()
        
        rows_data.append(row_data)
    
    return rows_data
```

### 3. List Data Extraction
Extract data from lists:

```python
async def extract_list_data(self, list_selector: str) -> list:
    """Extract data from ordered/unordered lists."""
    list_element = await self.selector_engine.find(self.page, list_selector)
    if not list_element:
        return []
    
    items = []
    item_elements = await list_element.query_selector_all("li")
    
    for item in item_elements:
        item_text = await item.inner_text()
        items.append(item_text.strip())
    
    return items
```

### 4. Form Data Extraction
Extract form field information:

```python
async def extract_form_data(self, form_selector: str) -> dict:
    """Extract form field information."""
    form = await self.selector_engine.find(self.page, form_selector)
    if not form:
        return {}
    
    form_data = {}
    
    # Extract input fields
    inputs = await form.query_selector_all("input")
    for input_field in inputs:
        name = await input_field.get_attribute('name')
        field_type = await input_field.get_attribute('type')
        value = await input_field.input_value()
        
        if name:
            form_data[name] = {
                'type': field_type or 'text',
                'value': value
            }
    
    return form_data
```

### 5. Real-time Data Extraction
Handle dynamic, real-time data:

```python
async def extract_live_data(self, data_selector: str) -> dict:
    """Extract real-time data with updates."""
    live_data = {}
    
    # Extract current data
    data_element = await self.selector_engine.find(self.page, data_selector)
    if data_element:
        live_data['current'] = await data_element.inner_text()
        live_data['timestamp'] = datetime.now().isoformat()
    
    # Set up observer for changes (if needed)
    await self.page.evaluate(f"""
        const observer = new MutationObserver((mutations) => {{
            mutations.forEach((mutation) => {{
                window.liveDataUpdated = true;
            }});
        }});
        
        const element = document.querySelector('{data_selector}');
        if (element) {{
            observer.observe(element, {{ childList: true, subtree: true }});
        }}
    """)
    
    return live_data
```

## 🎯 Use Cases

### Sports Data Extraction (Flashscore Example)
```python
class MatchExtractionFlow(ExtractionFlow):
    async def extract_match_basic_info(self) -> dict:
        """Extract basic match information."""
        match_info = {}
        
        # Extract teams
        home_team = await self.extract_text_content("home_team_name")
        away_team = await self.extract_text_content("away_team_name")
        
        # Extract score
        home_score = await self.extract_text_content("home_team_score")
        away_score = await self.extract_text_content("away_team_score")
        
        # Extract match time
        match_time = await self.extract_text_content("match_time")
        
        match_info = {
            'home_team': home_team,
            'away_team': away_team,
            'home_score': home_score,
            'away_score': away_score,
            'match_time': match_time
        }
        
        # Validate data
        required_fields = ['home_team', 'away_team', 'home_score', 'away_score']
        if self.validate_extracted_data(match_info, required_fields):
            return match_info
        
        return None
```

### E-commerce Product Extraction
```python
class ProductExtractionFlow(ExtractionFlow):
    async def extract_product_details(self) -> dict:
        """Extract product information."""
        product = {}
        
        # Basic info
        product['title'] = await self.extract_text_content("product_title")
        product['price'] = await self.extract_text_content("product_price")
        product['description'] = await self.extract_text_content("product_description")
        
        # Images
        images = await self.page.query_selector_all(".product-image")
        product['images'] = [
            await img.get_attribute('src') for img in images
        ]
        
        # Specifications
        specs_table = await self.extract_table_data("product_specifications")
        product['specifications'] = specs_table
        
        return product
```

### News Article Extraction
```python
class ArticleExtractionFlow(ExtractionFlow):
    async def extract_article_data(self) -> dict:
        """Extract news article data."""
        article = {}
        
        # Metadata
        article['title'] = await self.extract_text_content("article_title")
        article['author'] = await self.extract_text_content("article_author")
        article['publish_date'] = await self.extract_text_content("article_date")
        
        # Content
        article['content'] = await self.extract_text_content("article_content")
        
        # Categories/tags
        tags = await self.page.query_selector_all(".article-tag")
        article['tags'] = [
            await tag.inner_text() for tag in tags
        ]
        
        return article
```

## ⚡ Performance Optimization

### 1. Parallel Extraction
Extract multiple data points concurrently:

```python
async def extract_multiple_data_points(self, selectors: dict) -> dict:
    """Extract multiple data points in parallel."""
    tasks = []
    for key, selector in selectors.items():
        task = self.extract_text_content(selector)
        tasks.append((key, task))
    
    results = {}
    for key, task in tasks:
        try:
            results[key] = await task
        except Exception as e:
            self.logger.error(f"Failed to extract {key}: {e}")
            results[key] = None
    
    return results
```

### 2. Smart Waiting
Wait efficiently for dynamic content:

```python
async def wait_for_data_load(self, selector: str, timeout: int = 10000):
    """Wait for data to be available."""
    try:
        await self.page.wait_for_function(
            f"() => document.querySelector('{selector}') && "
            f"document.querySelector('{selector}').textContent.trim() !== ''",
            timeout=timeout
        )
        return True
    except TimeoutError:
        return False
```

## 🛡️ Error Handling

### Extraction Error Recovery
```python
async def safe_extract(self, selector: str, fallback_selector: str = None) -> str:
    """Extract with fallback selectors."""
    try:
        result = await self.extract_text_content(selector)
        if result:
            return result
    except Exception as e:
        self.logger.warning(f"Primary extraction failed: {e}")
    
    # Try fallback selector
    if fallback_selector:
        try:
            result = await self.extract_text_content(fallback_selector)
            if result:
                return result
        except Exception as e:
            self.logger.warning(f"Fallback extraction failed: {e}")
    
    return None
```

### Data Validation
```python
async def extract_with_validation(self, selector: str, validator_func=None) -> str:
    """Extract data with validation."""
    data = await self.extract_text_content(selector)
    
    if data and validator_func:
        if validator_func(data):
            return data
        else:
            self.logger.warning(f"Data validation failed for {selector}")
            return None
    
    return data
```

## 📊 Best Practices

### 1. Data Quality
- Always validate extracted data
- Handle missing or malformed data gracefully
- Implement data cleaning and normalization

### 2. Performance
- Use parallel extraction when possible
- Implement smart waiting strategies
- Cache frequently accessed data

### 3. Error Handling
- Provide fallback selectors
- Log extraction errors for debugging
- Implement retry logic for failed extractions

### 4. Maintainability
- Use descriptive method names
- Document extraction logic
- Separate complex extraction into smaller methods

## 🔍 Testing Extraction Flows

### Unit Tests
```python
async def test_extract_match_info():
    """Test match information extraction."""
    flow = MatchExtractionFlow()
    await flow.setup()
    
    # Mock page content
    await flow.page.set_content("""
        <div>
            <span id="home_team_name">Team A</span>
            <span id="away_team_name">Team B</span>
            <span id="home_team_score">2</span>
            <span id="away_team_score">1</span>
        </div>
    """)
    
    result = await flow.extract_match_basic_info()
    
    assert result['home_team'] == 'Team A'
    assert result['away_team'] == 'Team B'
    assert result['home_score'] == '2'
    assert result['away_score'] == '1'
```

### Integration Tests
```python
async def test_full_extraction_workflow():
    """Test complete extraction workflow."""
    flow = MatchExtractionFlow()
    await flow.setup()
    
    # Navigate to match page
    await flow.page.goto("https://example.com/match/12345")
    
    # Extract match data
    match_data = await flow.extract_match_basic_info()
    
    # Validate extracted data
    assert match_data is not None
    assert 'home_team' in match_data
    assert 'away_team' in match_data
```

## 📚 Additional Resources

- [Navigation Domain](./NAVIGATION.md)
- [Filtering Domain](./FILTERING.md)
- [Authentication Domain](./AUTHENTICATION.md)
- [Real-World Examples](../REAL_WORLD_EXAMPLES.md)
