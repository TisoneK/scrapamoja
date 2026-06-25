# Pattern Upgrade Guidance

This guide helps you upgrade your site templates as they grow in complexity.

## When to Upgrade Patterns

### Simple → Standard
Consider upgrading from Simple to Standard pattern when:

- **Multiple Flow Classes**: You have 2-3 different flow classes
- **Separation of Concerns**: Flows handle different aspects (navigation + extraction)
- **Code Organization**: Your single `flow.py` file becomes difficult to maintain
- **Team Collaboration**: Multiple developers need to work on different flows

**Signs you need to upgrade:**
```python
# Your flow.py looks like this:
class LoginFlow:
    # 50+ lines of authentication logic
    
class NavigationFlow:
    # 80+ lines of navigation logic
    
class DataExtractionFlow:
    # 100+ lines of extraction logic
```

### Standard → Complex
Consider upgrading from Standard to Complex pattern when:

- **Domain Separation**: You have flows across multiple domains (navigation, extraction, filtering, authentication)
- **Advanced Features**: You need domain-specific utilities and configurations
- **Large Teams**: Different teams work on different domains
- **Scalability**: You need to organize flows for better maintainability

**Signs you need to upgrade:**
```
flows/
├── navigation_flow.py      # Navigation logic
├── extraction_flow.py      # Extraction logic  
├── filtering_flow.py       # Filtering logic
├── auth_flow.py           # Authentication logic
├── data_processing_flow.py # Data processing
└── utility_flow.py        # Utility functions
```

## Upgrade Paths

### Path 1: Simple → Standard

#### Step 1: Create Flows Directory
```bash
mkdir flows
touch flows/__init__.py
```

#### Step 2: Split Flow Classes
Move each flow class to its own file:

```python
# flows/navigation_flow.py
from ..base_flows import BaseNavigationFlow

class NavigationFlow(BaseNavigationFlow):
    # Your navigation logic
```

#### Step 3: Update Main Flow
Keep a simple `flow.py` for coordination:

```python
# flow.py
from .flows.navigation_flow import NavigationFlow
from .flows.extraction_flow import ExtractionFlow

def create_flows(page, selector_engine):
    return {
        'navigation': NavigationFlow(page, selector_engine),
        'extraction': ExtractionFlow(page, selector_engine)
    }
```

#### Step 4: Update Imports
Update any imports in your site files:

```python
# Before
from .flow import NavigationFlow

# After  
from .flows.navigation_flow import NavigationFlow
```

### Path 2: Standard → Complex

#### Step 1: Create Domain Directories
```bash
mkdir flows/navigation flows/extraction flows/filtering flows/authentication
touch flows/{navigation,extraction,filtering,authentication}/__init__.py
```

#### Step 2: Organize Flows by Domain
Move flows to appropriate domain directories:

```
flows/
├── navigation/
│   ├── __init__.py
│   ├── page_navigation.py
│   └── link_navigation.py
├── extraction/
│   ├── __init__.py
│   ├── data_extraction.py
│   └── content_extraction.py
├── filtering/
│   ├── __init__.py
│   └── data_filtering.py
└── authentication/
    ├── __init__.py
    └── login_flow.py
```

#### Step 3: Use Domain-Specific Base Classes
Update flows to inherit from domain-specific base classes:

```python
# flows/navigation/page_navigation.py
from ...base_flows import BaseNavigationFlow

class PageNavigationFlow(BaseNavigationFlow):
    # Enhanced navigation with domain utilities
```

#### Step 4: Create Domain Coordinators
Create coordinator classes for complex workflows:

```python
# flows/__init__.py
from .navigation.page_navigation import PageNavigationFlow
from .extraction.data_extraction import DataExtractionFlow
from .authentication.login_flow import LoginFlow

class SiteFlowCoordinator:
    def __init__(self, page, selector_engine):
        self.navigation = PageNavigationFlow(page, selector_engine)
        self.extraction = DataExtractionFlow(page, selector_engine)
        self.authentication = LoginFlow(page, selector_engine)
    
    async def full_scrape_workflow(self, url, credentials):
        # Coordinate multiple flows
        await self.authentication.authenticate(credentials)
        await self.navigation.navigate_to_url(url)
        return await self.extraction.extract_all_data()
```

## Automated Migration

### Using the Migration Tool

```python
from .migration_tool import migrate_site

# Simple migration with automatic pattern detection
result = migrate_site('/path/to/site')

# Custom migration with specific target pattern
result = migrate_site('/path/to/site', {
    'target_complexity': 'complex',
    'create_backup': True,
    'preserve_original': False
})

print(f"Migration successful: {result['success']}")
print(f"Target pattern: {result['target_pattern']}")
```

### Migration Configuration Options

```python
migration_config = {
    # Target pattern: 'simple', 'standard', 'complex', or 'auto'
    'target_complexity': 'auto',
    
    # Create backup before migration
    'create_backup': True,
    
    # Preserve original files
    'preserve_original': True,
    
    # Update import statements
    'update_imports': True,
    
    # Migrate flow implementations
    'migrate_flows': True
}
```

## Best Practices

### During Upgrades

1. **Always Create Backups**
   ```python
   # The migration tool does this automatically
   migration_config = {'create_backup': True}
   ```

2. **Test Incrementally**
   ```bash
   # Test after each major step
   python -m pytest tests/test_flows.py
   ```

3. **Update Documentation**
   ```markdown
   # Update your site README
   ## Architecture
   - Pattern: Complex
   - Domains: Navigation, Extraction, Filtering
   - Base Classes: BaseNavigationFlow, BaseExtractionFlow, etc.
   ```

### Post-Upgrade Optimization

1. **Use Domain-Specific Utilities**
   ```python
   # Leverage built-in domain utilities
   class MyExtractionFlow(BaseExtractionFlow):
       async def extract_with_validation(self, selectors, rules):
           # Use built-in error handling
           return await self._execute_with_error_handling(
               'extract_data', 10.0, selectors, rules
           )
   ```

2. **Implement Domain Coordinators**
   ```python
   # For complex workflows
   class ECommerceFlowCoordinator:
       def __init__(self, page, selector_engine):
           self.auth = LoginFlow(page, selector_engine)
           self.nav = ProductNavigationFlow(page, selector_engine)
           self.ext = ProductExtractionFlow(page, selector_engine)
           self.filt = ProductFilteringFlow(page, selector_engine)
   ```

3. **Add Flow Dependencies**
   ```python
   # Define execution order and dependencies
   workflow = [
       ('authentication', auth_flow.authenticate),
       ('navigation', nav_flow.to_product_page),
       ('extraction', ext_flow.extract_product_data),
       ('filtering', filt_flow.filter_products)
   ]
   ```

## Troubleshooting

### Common Issues

#### Import Errors After Migration
```python
# Error: ImportError: cannot import name 'BaseNavigationFlow'
# Solution: Update relative imports
from ..base_flows import BaseNavigationFlow  # Add .. for parent directory
```

#### Flow Not Found
```python
# Error: ModuleNotFoundError: No module named 'flows.navigation'
# Solution: Ensure __init__.py files exist in all directories
touch flows/navigation/__init__.py
```

#### Backup Conflicts
```python
# Error: Backup directory already exists
# Solution: Remove or rename existing backup
rm -rf site_backup/
```

### Validation Steps

1. **Check Structure**
   ```bash
   # Verify directory structure
   tree flows/
   ```

2. **Test Imports**
   ```python
   # Test all imports
   from flows.navigation.page_navigation import PageNavigationFlow
   from flows.extraction.data_extraction import DataExtractionFlow
   ```

3. **Run Tests**
   ```bash
   # Run full test suite
   python -m pytest tests/ -v
   ```

4. **Validate Functionality**
   ```python
   # Test basic functionality
   async def test_migration():
       flows = create_flows(page, selector_engine)
       result = await flows['navigation'].navigate_to_url('https://example.com')
       assert result.success
   ```

## Migration Examples

### Example 1: Simple Blog Scraper

**Before (Simple):**
```
blog_site/
└── flow.py  # 200 lines with BlogFlow class
```

**After (Standard):**
```
blog_site/
├── flow.py           # Coordinator (20 lines)
└── flows/
    ├── __init__.py
    ├── blog_navigation.py    # 80 lines
    └── blog_extraction.py    # 100 lines
```

### Example 2: E-commerce Platform

**Before (Standard):**
```
ecommerce_site/
├── flow.py
└── flows/
    ├── __init__.py
    ├── login_flow.py
    ├── navigation_flow.py
    ├── product_extraction.py
    ├── order_extraction.py
    └── filtering_flow.py
```

**After (Complex):**
```
ecommerce_site/
├── flow.py
└── flows/
    ├── __init__.py
    ├── authentication/
    │   ├── __init__.py
    │   └── login_flow.py
    ├── navigation/
    │   ├── __init__.py
    │   └── product_navigation.py
    ├── extraction/
    │   ├── __init__.py
    │   ├── product_extraction.py
    │   └── order_extraction.py
    └── filtering/
        ├── __init__.py
        └── product_filtering.py
```

## Next Steps

After upgrading your pattern:

1. **Review New Features**: Explore domain-specific utilities and base classes
2. **Optimize Flows**: Use new error handling and validation patterns
3. **Update Tests**: Add tests for new structure and functionality
4. **Document Changes**: Update team documentation and onboarding guides
5. **Monitor Performance**: Track improvements in maintainability and scalability

For specific upgrade assistance, use the migration tool or consult the template documentation.
