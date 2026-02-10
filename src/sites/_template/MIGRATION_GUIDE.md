# Migration Guide

This guide helps you migrate between different architectural patterns as your site requirements evolve.

## 🔄 Migration Overview

As your scraping needs grow, you may need to upgrade from simpler to more complex patterns. This guide provides step-by-step migration paths for each transition.

## 📊 Migration Matrix

| From | To | Complexity | Time Required | Risk Level |
|------|-----|------------|---------------|------------|
| Simple → Standard | Low | 30-60 minutes | Low |
| Standard → Complex | Medium | 1-3 hours | Medium |
| Simple → Complex | High | 2-4 hours | High |

---

## 🚀 Simple → Standard Migration

### When to Migrate
- Adding search functionality
- Implementing authentication
- Handling dynamic content
- Processing complex data structures

### Migration Steps

#### Step 1: Backup Current Implementation
```bash
# Create backup of current implementation
cp -r src/sites/your_site src/sites/your_site_backup_$(date +%Y%m%d)
```

#### Step 2: Create Standard Pattern Structure
```bash
# Create flows directory
mkdir -p src/sites/your_site/flows

# Create __init__.py
touch src/sites/your_site/flows/__init__.py
```

#### Step 3: Extract Complex Logic to Specialized Flows

**Current (Simple):**
```python
# flow.py
class SimpleFlow(BaseFlow):
    async def perform_search(self, query: str):
        # Basic search logic
        search_input = await self.selector_engine.find(self.page, "search_input")
        if search_input:
            await search_input.clear()
            await search_input.type(query)
            await search_input.press('Enter')
            await self.page.wait_for_timeout(2000)
    
    async def handle_pagination(self):
        # Basic pagination
        next_button = await self.selector_engine.find(self.page, "next_button")
        if next_button:
            await next_button.click()
            await self.page.wait_for_timeout(2000)
    
    async def extract_data(self):
        # Basic extraction
        items = await self.page.query_selector_all(".item")
        return [await item.inner_text() for item in items]
```

**Migrated (Standard):**
```python
# flow.py (simplified)
class StandardFlow(BaseFlow):
    async def open_home(self):
        """Navigate to the home page."""
        await self.page.goto("https://example.com")
        await self.page.wait_for_load_state('networkidle')
    
    async def navigate_to_page(self, page_url: str):
        """Navigate to a specific page."""
        await self.page.goto(page_url)
        await self.page.wait_for_load_state('networkidle')

# flows/search_flow.py (new)
class SearchFlow(BaseFlow):
    async def perform_advanced_search(self, query: str, filters: dict = None):
        """Perform advanced search with filters."""
        await self.page.goto("https://example.com/search")
        await self.page.wait_for_load_state('networkidle')
        
        # Enter search query
        search_input = await self.selector_engine.find(self.page, "search_input")
        if search_input:
            await search_input.clear()
            await search_input.type(query)
        
        # Apply filters if provided
        if filters:
            await self._apply_search_filters(filters)
        
        # Submit search
        search_button = await self.selector_engine.find(self.page, "search_button")
        if search_button:
            await search_button.click()
            await self.page.wait_for_timeout(2000)
    
    async def _apply_search_filters(self, filters: dict):
        """Apply search filters."""
        for filter_name, filter_value in filters.items():
            filter_element = await self.selector_engine.find(
                self.page, f"filter_{filter_name}"
            )
            if filter_element:
                await filter_element.select_option(filter_value)

# flows/pagination_flow.py (new)
class PaginationFlow(BaseFlow):
    async def go_to_next_page(self):
        """Navigate to next page."""
        next_button = await self.selector_engine.find(self.page, "next_page_button")
        if next_button and await next_button.is_enabled():
            await next_button.click()
            await self.page.wait_for_load_state('networkidle')
            return True
        return False
    
    async def handle_infinite_scroll(self, max_scrolls: int = 10):
        """Handle infinite scroll pagination."""
        items_count = 0
        scrolls = 0
        
        while scrolls < max_scrolls:
            current_items = await self.page.query_selector_all(".item")
            if len(current_items) <= items_count:
                break
            
            items_count = len(current_items)
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.page.wait_for_timeout(2000)
            scrolls += 1
        
        return items_count

# flows/extraction_flow.py (new)
class ExtractionFlow(BaseFlow):
    async def extract_table_data(self, table_selector: str):
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

#### Step 4: Update Flow Registry
```python
# flows/__init__.py
from .search_flow import SearchFlow
from .pagination_flow import PaginationFlow
from .extraction_flow import ExtractionFlow

AVAILABLE_FLOWS = {
    'search': SearchFlow,
    'pagination': PaginationFlow,
    'extraction': ExtractionFlow,
}

def get_flow(flow_name: str):
    """Get a flow class by name."""
    return AVAILABLE_FLOWS.get(flow_name)
```

#### Step 5: Update Main Scraper
```python
# scraper.py
class YourSiteScraper(EnhancedSiteScraper):
    async def setup_components(self) -> None:
        """Register flows for standard pattern."""
        # Register main flow
        self.register_flow('main', StandardFlow)
        
        # Register specialized flows
        self.register_flow('search', SearchFlow)
        self.register_flow('pagination', PaginationFlow)
        self.register_flow('extraction', ExtractionFlow)
```

#### Step 6: Test Migration
```python
# Test the migrated implementation
async def test_migration():
    scraper = YourSiteScraper()
    await scraper.setup()
    
    # Test basic navigation
    await scraper.flows['main'].open_home()
    
    # Test search functionality
    await scraper.flows['search'].perform_advanced_search("test query")
    
    # Test extraction
    data = await scraper.flows['extraction'].extract_table_data("table")
    assert len(data) > 0
```

---

## ⚖️ Standard → Complex Migration

### When to Migrate
- Adding domain-specific operations
- Implementing real-time features
- Scaling to high-frequency operations
- Adding advanced filtering

### Migration Steps

#### Step 1: Create Domain Structure
```bash
# Create domain directories
mkdir -p src/sites/your_site/flows/navigation
mkdir -p src/sites/your_site/flows/extraction
mkdir -p src/sites/your_site/flows/filtering
mkdir -p src/sites/your_site/flows/authentication

# Create __init__.py files
touch src/sites/your_site/flows/navigation/__init__.py
touch src/sites/your_site/flows/extraction/__init__.py
touch src/sites/your_site/flows/filtering/__init__.py
touch src/sites/your_site/flows/authentication/__init__.py
```

#### Step 2: Categorize Existing Flows

**Current (Standard):**
```python
# flows/search_flow.py
class SearchFlow(BaseFlow):
    async def perform_advanced_search(self, query: str, filters: dict = None):
        # Combined search and filtering logic
        pass

# flows/extraction_flow.py
class ExtractionFlow(BaseFlow):
    async def extract_table_data(self, table_selector: str):
        # Combined extraction logic
        pass
```

**Migrated (Complex):**
```python
# flows/navigation/search_nav.py (new)
class SearchNavigationFlow(BaseFlow):
    """Handle search page navigation."""
    async def navigate_to_search(self):
        """Navigate to search page."""
        await self.page.goto("https://example.com/search")
        await self.page.wait_for_load_state('networkidle')
    
    async def navigate_to_advanced_search(self):
        """Navigate to advanced search page."""
        await self.page.goto("https://example.com/search/advanced")
        await self.page.wait_for_load_state('networkidle')

# flows/filtering/search_filter.py (new)
class SearchFilteringFlow(BaseFlow):
    """Handle search filtering logic."""
    async def apply_search_filters(self, filters: dict):
        """Apply search filters."""
        for filter_name, filter_value in filters.items():
            filter_element = await self.selector_engine.find(
                self.page, f"search_filter_{filter_name}"
            )
            if filter_element:
                await filter_element.select_option(filter_value)

# flows/extraction/search_extract.py (new)
class SearchExtractionFlow(BaseFlow):
    """Handle search results extraction."""
    async def extract_search_results(self):
        """Extract search results."""
        results = []
        result_elements = await self.page.query_selector_all(".search-result")
        
        for element in result_elements:
            result = await self._extract_result_data(element)
            results.append(result)
        
        return results
    
    async def _extract_result_data(self, element):
        """Extract data from a single search result."""
        title = await element.query_selector(".result-title")
        description = await element.query_selector(".result-description")
        url = await element.query_selector(".result-url")
        
        return {
            'title': await title.inner_text() if title else None,
            'description': await description.inner_text() if description else None,
            'url': await url.get_attribute('href') if url else None
        }
```

#### Step 3: Update Domain Registries
```python
# flows/navigation/__init__.py
from .search_nav import SearchNavigationFlow
from .browse_nav import BrowseNavigationFlow

NAVIGATION_FLOWS = {
    'search': SearchNavigationFlow,
    'browse': BrowseNavigationFlow,
}

# flows/filtering/__init__.py
from .search_filter import SearchFilteringFlow
from .date_filter import DateFilteringFlow

FILTERING_FLOWS = {
    'search': SearchFilteringFlow,
    'date': DateFilteringFlow,
}

# flows/extraction/__init__.py
from .search_extract import SearchExtractionFlow
from .table_extract import TableExtractionFlow

EXTRACTION_FLOWS = {
    'search': SearchExtractionFlow,
    'table': TableExtractionFlow,
}
```

#### Step 4: Update Main Registry
```python
# flows/__init__.py (updated)
# Navigation flows
from .navigation.search_nav import SearchNavigationFlow
from .navigation.browse_nav import BrowseNavigationFlow

# Extraction flows
from .extraction.search_extract import SearchExtractionFlow
from .extraction.table_extract import TableExtractionFlow

# Filtering flows
from .filtering.search_filter import SearchFilteringFlow
from .filtering.date_filter import DateFilteringFlow

# Authentication flows
from .authentication.login_flow import LoginAuthenticationFlow
from .authentication.oauth_flow import OAuthAuthenticationFlow

# Registry organized by domain
DOMAIN_FLOWS = {
    'navigation': {
        'search': SearchNavigationFlow,
        'browse': BrowseNavigationFlow,
    },
    'extraction': {
        'search': SearchExtractionFlow,
        'table': TableExtractionFlow,
    },
    'filtering': {
        'search': SearchFilteringFlow,
        'date': DateFilteringFlow,
    },
    'authentication': {
        'login': LoginAuthenticationFlow,
        'oauth': OAuthAuthenticationFlow,
    },
}

def get_flow(domain: str, flow_name: str):
    """Get a flow class by domain and name."""
    return DOMAIN_FLOWS.get(domain, {}).get(flow_name)
```

#### Step 5: Update Main Scraper
```python
# scraper.py (updated)
class YourSiteScraper(EnhancedSiteScraper):
    async def setup_components(self) -> None:
        """Register domain-separated flows."""
        # Register flows by domain
        for domain, flows in DOMAIN_FLOWS.items():
            for flow_name, flow_class in flows.items():
                self.register_flow(f"{domain}.{flow_name}", flow_class)
    
    async def perform_complex_search(self, query: str, filters: dict = None):
        """Example of coordinated domain flows."""
        # Navigate to search
        await self.flows['navigation.search'].navigate_to_search()
        
        # Apply filters
        if filters:
            await self.flows['filtering.search'].apply_search_filters(filters)
        
        # Extract results
        results = await self.flows['extraction.search'].extract_search_results()
        
        return results
```

---

## 🎯 Simple → Complex Direct Migration

### When to Use Direct Migration
- Skipping standard pattern
- High complexity requirements from start
- Real-time data needs
- Multiple operational domains

### Migration Steps

#### Step 1: Complete Complex Pattern Setup
```bash
# Create full complex structure
mkdir -p src/sites/your_site/flows/navigation
mkdir -p src/sites/your_site/flows/extraction
mkdir -p src/sites/your_site/flows/filtering
mkdir -p src/sites/your_site/flows/authentication

# Create all __init__.py files
touch src/sites/your_site/flows/__init__.py
touch src/sites/your_site/flows/navigation/__init__.py
touch src/sites/your_site/flows/extraction/__init__.py
touch src/sites/your_site/flows/filtering/__init__.py
touch src/sites/your_site/flows/authentication/__init__.py
```

#### Step 2: Extract and Categorize Logic

**Current (Simple):**
```python
# flow.py
class SimpleFlow(BaseFlow):
    async def perform_search_and_extract(self, query: str):
        # Combined search, navigation, and extraction
        await self.page.goto("https://example.com")
        
        # Search
        search_input = await self.selector_engine.find(self.page, "search_input")
        await search_input.type(query)
        await search_input.press('Enter')
        
        # Wait for results
        await self.page.wait_for_timeout(2000)
        
        # Extract data
        results = await self.page.query_selector_all(".result")
        return [await result.inner_text() for result in results]
```

**Migrated (Complex):**
```python
# flows/navigation/search_nav.py
class SearchNavigationFlow(BaseFlow):
    async def navigate_to_home(self):
        """Navigate to home page."""
        await self.page.goto("https://example.com")
        await self.page.wait_for_load_state('networkidle')
    
    async def navigate_to_search_results(self, query: str):
        """Navigate to search results page."""
        search_input = await self.selector_engine.find(self.page, "search_input")
        if search_input:
            await search_input.clear()
            await search_input.type(query)
            await search_input.press('Enter')
            await self.page.wait_for_timeout(2000)

# flows/extraction/search_extract.py
class SearchExtractionFlow(BaseFlow):
    async def extract_search_results(self):
        """Extract search results data."""
        results = []
        result_elements = await self.page.query_selector_all(".result")
        
        for element in result_elements:
            result_data = await self._extract_result_element(element)
            results.append(result_data)
        
        return results
    
    async def _extract_result_element(self, element):
        """Extract detailed data from result element."""
        title = await element.query_selector(".result-title")
        description = await element.query_selector(".result-description")
        url = await element.query_selector(".result-link")
        
        return {
            'title': await title.inner_text() if title else None,
            'description': await description.inner_text() if description else None,
            'url': await url.get_attribute('href') if url else None
        }

# Main scraper coordination
class YourSiteScraper(EnhancedSiteScraper):
    async def perform_search_and_extract(self, query: str):
        """Coordinated search and extraction using domain flows."""
        # Navigate to home
        await self.flows['navigation.search'].navigate_to_home()
        
        # Navigate to search results
        await self.flows['navigation.search'].navigate_to_search_results(query)
        
        # Extract results
        results = await self.flows['extraction.search'].extract_search_results()
        
        return results
```

---

## 🛠️ Migration Tools

### Automated Migration Script
```python
# migrate_pattern.py
import os
import shutil
from pathlib import Path

class PatternMigrator:
    def __init__(self, site_path: str, from_pattern: str, to_pattern: str):
        self.site_path = Path(site_path)
        self.from_pattern = from_pattern
        self.to_pattern = to_pattern
    
    async def migrate(self):
        """Perform migration from one pattern to another."""
        if self.from_pattern == "simple" and self.to_pattern == "standard":
            await self._migrate_simple_to_standard()
        elif self.from_pattern == "standard" and self.to_pattern == "complex":
            await self._migrate_standard_to_complex()
        elif self.from_pattern == "simple" and self.to_pattern == "complex":
            await self._migrate_simple_to_complex()
        else:
            raise ValueError(f"Unsupported migration: {self.from_pattern} → {self.to_pattern}")
    
    async def _migrate_simple_to_standard(self):
        """Migrate from simple to standard pattern."""
        # Create flows directory
        flows_dir = self.site_path / "flows"
        flows_dir.mkdir(exist_ok=True)
        
        # Create __init__.py
        (flows_dir / "__init__.py").touch()
        
        # Analyze existing flow.py and extract complex methods
        flow_py = self.site_path / "flow.py"
        if flow_py.exists():
            await self._extract_complex_methods(flow_py, flows_dir)
    
    async def _extract_complex_methods(self, flow_py: Path, flows_dir: Path):
        """Extract complex methods from flow.py into separate files."""
        # This would analyze the Python file and extract methods
        # that should be moved to specialized flows
        pass

# Usage example
migrator = PatternMigrator("src/sites/your_site", "simple", "standard")
await migrator.migrate()
```

### Validation Script
```python
# validate_migration.py
class MigrationValidator:
    def __init__(self, site_path: str, expected_pattern: str):
        self.site_path = Path(site_path)
        self.expected_pattern = expected_pattern
    
    def validate_structure(self) -> bool:
        """Validate that the site structure matches expected pattern."""
        if self.expected_pattern == "simple":
            return self._validate_simple_structure()
        elif self.expected_pattern == "standard":
            return self._validate_standard_structure()
        elif self.expected_pattern == "complex":
            return self._validate_complex_structure()
        return False
    
    def _validate_simple_structure(self) -> bool:
        """Validate simple pattern structure."""
        flow_py = self.site_path / "flow.py"
        flows_dir = self.site_path / "flows"
        
        return flow_py.exists() and not flows_dir.exists()
    
    def _validate_standard_structure(self) -> bool:
        """Validate standard pattern structure."""
        flow_py = self.site_path / "flow.py"
        flows_dir = self.site_path / "flows"
        flows_init = flows_dir / "__init__.py"
        
        return (flow_py.exists() and 
                flows_dir.exists() and 
                flows_init.exists())
    
    def _validate_complex_structure(self) -> bool:
        """Validate complex pattern structure."""
        flows_dir = self.site_path / "flows"
        domains = ["navigation", "extraction", "filtering", "authentication"]
        
        if not flows_dir.exists():
            return False
        
        for domain in domains:
            domain_dir = flows_dir / domain
            if not domain_dir.exists():
                return False
            
            domain_init = domain_dir / "__init__.py"
            if not domain_init.exists():
                return False
        
        return True

# Usage example
validator = MigrationValidator("src/sites/your_site", "complex")
is_valid = validator.validate_structure()
print(f"Migration valid: {is_valid}")
```

---

## 📋 Migration Checklist

### Pre-Migration Checklist
- [ ] Backup current implementation
- [ ] Document current functionality
- [ ] Identify complex logic to extract
- [ ] Plan migration timeline
- [ ] Prepare test cases

### Migration Checklist
- [ ] Create new directory structure
- [ ] Extract and categorize flows
- [ ] Update flow registries
- [ ] Update main scraper
- [ ] Test individual flows
- [ ] Test integrated functionality
- [ ] Update documentation
- [ ] Performance testing

### Post-Migration Checklist
- [ ] Verify all functionality works
- [ ] Performance benchmarking
- [ ] Update team documentation
- [ ] Remove old files (if safe)
- [ ] Update deployment scripts
- [ ] Team training on new structure

---

## 🚨 Common Migration Issues

### Issue 1: Import Errors
**Problem**: Import paths break after migration
**Solution**: Update all import statements to match new structure

```python
# Before
from flow import SimpleFlow

# After (standard)
from flow import StandardFlow
from flows.search_flow import SearchFlow

# After (complex)
from flows.navigation.search_nav import SearchNavigationFlow
```

### Issue 2: Flow Coordination
**Problem**: Flows don't work together after separation
**Solution**: Implement proper flow coordination in main scraper

```python
# Coordinated flow usage
async def complex_operation(self):
    # Navigate first
    await self.flows['navigation.search'].navigate_to_search()
    
    # Then filter
    await self.flows['filtering.search'].apply_filters(filters)
    
    # Finally extract
    return await self.flows['extraction.search'].extract_results()
```

### Issue 3: State Management
**Problem**: Shared state between flows is lost
**Solution**: Implement proper state management

```python
class StateManager:
    def __init__(self):
        self.shared_state = {}
    
    def set_state(self, key: str, value: any):
        self.shared_state[key] = value
    
    def get_state(self, key: str):
        return self.shared_state.get(key)
```

---

## 📚 Additional Resources

- [Pattern Selection Guide](PATTERN_SELECTION.md)
- [Real-World Examples](REAL_WORLD_EXAMPLES.md)
- [Domain Documentation](DOMAINS/)
- [Setup Instructions](README.md)
