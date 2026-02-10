# Quick Start Guide: Wikipedia Extractor Integration Fix

**Feature**: 016-wikipedia-extractor-fix  
**Date**: 2026-01-29  
**Purpose**: Quick start guide for implementing and using YAML selector loading

## Overview

This guide provides step-by-step instructions for implementing and using the YAML selector loading system to fix the Wikipedia extractor integration. The system enables automatic loading of YAML selector configurations into the selector engine, enabling real Wikipedia data extraction instead of fallback mock data.

## Prerequisites

### System Requirements

- Python 3.11 or higher
- Existing Playwright installation
- PyYAML library (`pip install pyyaml`)
- Existing selector engine infrastructure
- Wikipedia scraper codebase

### File Structure

Ensure your project has the following structure:

```
src/
├── sites/
│   └── wikipedia/
│       ├── selectors/           # YAML selector files
│       ├── flows/
│       └── scraper.py
├── selectors/
│   ├── engine.py               # Existing selector engine
│   ├── yaml_loader.py          # NEW: YAML selector loading
│   ├── validator.py            # NEW: Selector validation
│   └── registry.py             # NEW: Selector registry management
└── components/
    └── initializer.py          # NEW: Component context initialization
```

## Implementation Steps

### Step 1: Create YAML Selector Files

Create YAML selector files in `src/sites/wikipedia/selectors/`:

**Example: `article_title.yaml`**

```yaml
id: article_title
name: Wikipedia Article Title
description: Extracts the main article title from Wikipedia pages
selector_type: css
pattern: "h1#firstHeading"
strategies:
  - type: text_anchor
    priority: 1
    config:
      anchor_text: "firstHeading"
      case_sensitive: false
    confidence_threshold: 0.9
  - type: role_based
    priority: 2
    config:
      role: "heading"
      required_attributes: ["id"]
    confidence_threshold: 0.7
validation_rules:
  required_attributes: ["id"]
  min_confidence: 0.7
metadata:
  version: "1.0.0"
  created_at: "2026-01-29"
  tags: ["article", "title", "wikipedia"]
```

**Example: `article_content.yaml`**

```yaml
id: article_content
name: Wikipedia Article Content
description: Extracts the main article content from Wikipedia pages
selector_type: css
pattern: "div#mw-content-text"
strategies:
  - type: dom_relationship
    priority: 1
    config:
      relationship_type: "child"
      target_selector: "div#bodyContent"
      max_depth: 3
    confidence_threshold: 0.8
  - type: attribute_match
    priority: 2
    config:
      attribute: "id"
      value_pattern: "mw-content-text"
      exact_match: true
    confidence_threshold: 0.9
validation_rules:
  required_attributes: ["id"]
  min_confidence: 0.8
metadata:
  version: "1.0.0"
  created_at: "2026-01-29"
  tags: ["article", "content", "wikipedia"]
```

### Step 2: Implement YAML Selector Loader

Create `src/selectors/yaml_loader.py`:

```python
import yaml
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from .validator import SelectorValidator, ValidationResult
from .models import YAMLSelector, SelectorStrategy

logger = logging.getLogger(__name__)

@dataclass
class LoadResult:
    success: bool
    selectors_loaded: int
    selectors_failed: int
    errors: List[str]
    warnings: List[str]
    loading_time_ms: float

class YAMLSelectorLoader:
    def __init__(self, validator: SelectorValidator):
        self.validator = validator
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def load_selectors_from_directory(
        self, 
        directory_path: str, 
        recursive: bool = False
    ) -> LoadResult:
        """Load all YAML selector files from directory."""
        start_time = datetime.now()
        selectors_loaded = 0
        selectors_failed = 0
        errors = []
        warnings = []
        
        try:
            directory = Path(directory_path)
            if not directory.exists():
                raise FileNotFoundError(f"Directory not found: {directory_path}")
            
            pattern = "**/*.yaml" if recursive else "*.yaml"
            yaml_files = list(directory.glob(pattern))
            
            self.logger.info(f"Found {len(yaml_files)} YAML files in {directory_path}")
            
            for file_path in yaml_files:
                try:
                    selector = await self.load_selector_from_file(str(file_path))
                    if selector:
                        selectors_loaded += 1
                        self.logger.info(f"Loaded selector: {selector.id}")
                    else:
                        selectors_failed += 1
                        errors.append(f"Failed to load selector from {file_path}")
                except Exception as e:
                    selectors_failed += 1
                    error_msg = f"Error loading {file_path}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
        
        except Exception as e:
            errors.append(f"Directory loading error: {str(e)}")
            self.logger.error(f"Directory loading error: {str(e)}")
        
        loading_time = (datetime.now() - start_time).total_seconds() * 1000
        success = selectors_failed == 0
        
        return LoadResult(
            success=success,
            selectors_loaded=selectors_loaded,
            selectors_failed=selectors_failed,
            errors=errors,
            warnings=warnings,
            loading_time_ms=loading_time
        )
    
    async def load_selector_from_file(self, file_path: str) -> Optional[YAMLSelector]:
        """Load a single selector from YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
            
            if not data:
                raise ValueError("Empty YAML file")
            
            # Convert YAML data to YAMLSelector
            selector = self._yaml_to_selector(data, file_path)
            
            # Validate selector
            validation_result = self.validator.validate_selector(selector)
            if not validation_result.is_valid:
                error_messages = [error.error_message for error in validation_result.errors]
                raise ValueError(f"Validation failed: {'; '.join(error_messages)}")
            
            selector.loaded_at = datetime.now()
            return selector
        
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax: {str(e)}")
        except Exception as e:
            raise ValueError(f"Loading error: {str(e)}")
    
    def _yaml_to_selector(self, data: Dict[str, Any], file_path: str) -> YAMLSelector:
        """Convert YAML data to YAMLSelector object."""
        strategies = []
        for strategy_data in data.get('strategies', []):
            strategy = SelectorStrategy(
                type=StrategyType(strategy_data['type']),
                priority=strategy_data['priority'],
                config=strategy_data.get('config', {}),
                confidence_threshold=strategy_data.get('confidence_threshold', 0.8),
                enabled=strategy_data.get('enabled', True)
            )
            strategies.append(strategy)
        
        return YAMLSelector(
            id=data['id'],
            name=data['name'],
            description=data.get('description'),
            selector_type=SelectorType(data['selector_type']),
            pattern=data['pattern'],
            strategies=strategies,
            validation_rules=data.get('validation_rules'),
            metadata=data.get('metadata'),
            file_path=file_path,
            loaded_at=datetime.now(),  # Will be updated during loading
            version=data.get('metadata', {}).get('version', '1.0.0')
        )
```

### Step 3: Implement Selector Registry

Create `src/selectors/registry.py`:

```python
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .models import YAMLSelector
from .yaml_loader import YAMLSelectorLoader, LoadResult
from .validator import SelectorValidator

logger = logging.getLogger(__name__)

@dataclass
class RegistryStats:
    total_selectors: int = 0
    enabled_selectors: int = 0
    disabled_selectors: int = 0
    last_loaded: Optional[datetime] = None
    loading_time_ms: float = 0.0

class SelectorRegistry:
    def __init__(self, loader: YAMLSelectorLoader, validator: SelectorValidator):
        self.loader = loader
        self.validator = validator
        self.selectors: Dict[str, YAMLSelector] = {}
        self.stats = RegistryStats()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def load_selectors_from_directory(self, directory_path: str) -> LoadResult:
        """Load all selectors from directory and register them."""
        result = await self.loader.load_selectors_from_directory(directory_path)
        
        if result.success:
            # Clear existing selectors and reload
            self.selectors.clear()
            
            # Load each selector file individually to get selector objects
            import os
            from pathlib import Path
            
            directory = Path(directory_path)
            yaml_files = list(directory.glob("*.yaml"))
            
            for file_path in yaml_files:
                try:
                    selector = await self.loader.load_selector_from_file(str(file_path))
                    if selector:
                        self.register_selector(selector)
                except Exception as e:
                    self.logger.error(f"Failed to register selector from {file_path}: {str(e)}")
        
        # Update statistics
        self._update_stats()
        self.stats.loading_time_ms = result.loading_time_ms
        self.stats.last_loaded = datetime.now()
        
        return result
    
    def register_selector(self, selector: YAMLSelector) -> bool:
        """Register a selector in the registry."""
        try:
            # Validate selector before registration
            validation_result = self.validator.validate_selector(selector)
            if not validation_result.is_valid:
                error_messages = [error.error_message for error in validation_result.errors]
                self.logger.error(f"Validation failed for selector {selector.id}: {'; '.join(error_messages)}")
                return False
            
            # Check for conflicts
            if selector.id in self.selectors:
                self.logger.warning(f"Overriding existing selector: {selector.id}")
            
            self.selectors[selector.id] = selector
            self.logger.info(f"Registered selector: {selector.id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to register selector {selector.id}: {str(e)}")
            return False
    
    def get_selector(self, selector_id: str) -> Optional[YAMLSelector]:
        """Get selector by ID."""
        return self.selectors.get(selector_id)
    
    def list_selectors(self, include_disabled: bool = True) -> List[YAMLSelector]:
        """List all registered selectors."""
        selectors = list(self.selectors.values())
        if not include_disabled:
            selectors = [s for s in selectors if all(strategy.enabled for strategy in s.strategies)]
        return selectors
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_selectors": len(self.selectors),
            "enabled_selectors": len([s for s in self.selectors.values() 
                                    if any(strategy.enabled for strategy in s.strategies)]),
            "disabled_selectors": len([s for s in self.selectors.values() 
                                    if not any(strategy.enabled for strategy in s.strategies)]),
            "last_loaded": self.stats.last_loaded.isoformat() if self.stats.last_loaded else None,
            "loading_time_ms": self.stats.loading_time_ms,
            "selectors_by_type": self._get_selectors_by_type()
        }
    
    def _update_stats(self):
        """Update internal statistics."""
        self.stats.total_selectors = len(self.selectors)
        self.stats.enabled_selectors = len([s for s in self.selectors.values() 
                                           if any(strategy.enabled for strategy in s.strategies)])
        self.stats.disabled_selectors = self.stats.total_selectors - self.stats.enabled_selectors
    
    def _get_selectors_by_type(self) -> Dict[str, int]:
        """Get count of selectors by type."""
        type_counts = {}
        for selector in self.selectors.values():
            type_name = selector.selector_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        return type_counts
```

### Step 4: Integrate with Existing Selector Engine

Modify `src/selectors/engine.py` to integrate YAML selector loading:

```python
# Add to existing SelectorEngine class
class SelectorEngine:
    def __init__(self, ...):
        # Existing initialization
        self.yaml_registry: Optional[SelectorRegistry] = None
        self._yaml_initialized = False
    
    async def initialize_yaml_selectors(self, selectors_directory: str) -> bool:
        """Initialize YAML selector loading."""
        try:
            if self._yaml_initialized:
                self.logger.warning("YAML selectors already initialized")
                return True
            
            # Create validator and loader
            validator = SelectorValidator()
            loader = YAMLSelectorLoader(validator)
            
            # Create registry
            self.yaml_registry = SelectorRegistry(loader, validator)
            
            # Load selectors
            result = await self.yaml_registry.load_selectors_from_directory(selectors_directory)
            
            if result.success:
                self._yaml_initialized = True
                self.logger.info(f"Successfully loaded {result.selectors_loaded} YAML selectors")
                return True
            else:
                self.logger.error(f"Failed to load YAML selectors: {result.errors}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error initializing YAML selectors: {str(e)}")
            return False
    
    def resolve_with_yaml(self, selector_id: str, dom_context) -> Optional[SelectorResult]:
        """Resolve selector using YAML configuration."""
        if not self._yaml_initialized or not self.yaml_registry:
            self.logger.warning("YAML selectors not initialized")
            return None
        
        yaml_selector = self.yaml_registry.get_selector(selector_id)
        if not yaml_selector:
            self.logger.warning(f"YAML selector not found: {selector_id}")
            return None
        
        # Use YAML selector strategies for resolution
        return self._resolve_with_strategies(yaml_selector, dom_context)
    
    def get_yaml_statistics(self) -> Dict[str, Any]:
        """Get YAML selector statistics."""
        if not self.yaml_registry:
            return {"initialized": False}
        
        stats = self.yaml_registry.get_statistics()
        stats["initialized"] = True
        return stats
```

### Step 5: Update Wikipedia Scraper

Modify `src/sites/wikipedia/scraper.py` to initialize YAML selectors:

```python
class WikipediaScraper:
    def __init__(self, ...):
        # Existing initialization
        self.selector_engine = SelectorEngine(...)
        self._yaml_selectors_initialized = False
    
    async def initialize(self):
        """Initialize the scraper with YAML selectors."""
        # Existing initialization
        await self.browser_manager.initialize()
        
        # Initialize YAML selectors
        selectors_dir = os.path.join(
            os.path.dirname(__file__), 
            "selectors"
        )
        
        success = await self.selector_engine.initialize_yaml_selectors(selectors_dir)
        if success:
            self._yaml_selectors_initialized = True
            self.logger.info("YAML selectors initialized successfully")
        else:
            self.logger.error("Failed to initialize YAML selectors")
        
        return success
    
    async def extract_article(self, url: str) -> Dict[str, Any]:
        """Extract article using YAML selectors."""
        if not self._yaml_selectors_initialized:
            self.logger.warning("YAML selectors not initialized, using fallback")
            return await self._extract_with_fallback(url)
        
        try:
            # Navigate to page
            page = await self.browser_manager.navigate_to(url)
            
            # Create DOM context
            dom_context = DOMContext(
                page=page,
                tab_context="wikipedia_extraction",
                url=url,
                timestamp=datetime.utcnow()
            )
            
            # Extract using YAML selectors
            title_result = self.selector_engine.resolve_with_yaml("article_title", dom_context)
            content_result = self.selector_engine.resolve_with_yaml("article_content", dom_context)
            
            return {
                "title": title_result.element_info.text_content if title_result else None,
                "content": content_result.element_info.text_content if content_result else None,
                "url": url,
                "extracted_at": datetime.utcnow().isoformat(),
                "extraction_method": "yaml_selectors"
            }
        
        except Exception as e:
            self.logger.error(f"YAML extraction failed: {str(e)}")
            return await self._extract_with_fallback(url)
```

## Usage Examples

### Basic Usage

```python
import asyncio
from src.sites.wikipedia.scraper import WikipediaScraper

async def main():
    scraper = WikipediaScraper()
    
    # Initialize with YAML selectors
    await scraper.initialize()
    
    # Extract article
    url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
    result = await scraper.extract_article(url)
    
    print(f"Title: {result['title']}")
    print(f"Content length: {len(result['content']) if result['content'] else 0}")
    print(f"Extraction method: {result['extraction_method']}")

asyncio.run(main())
```

### Advanced Usage with Custom Configuration

```python
import asyncio
from src.sites.wikipedia.scraper import WikipediaScraper
from src.selectors.engine import SelectorEngine

async def main():
    # Create selector engine with custom configuration
    selector_engine = SelectorEngine(
        cache_enabled=True,
        performance_monitoring=True
    )
    
    # Create scraper with custom selector engine
    scraper = WikipediaScraper(selector_engine=selector_engine)
    
    # Initialize
    await scraper.initialize()
    
    # Get YAML selector statistics
    stats = selector_engine.get_yaml_statistics()
    print(f"Loaded selectors: {stats['total_selectors']}")
    print(f"Selector types: {stats['selectors_by_type']}")
    
    # Extract multiple articles
    urls = [
        "https://en.wikipedia.org/wiki/Python_(programming_language)",
        "https://en.wikipedia.org/wiki/Machine_learning",
        "https://en.wikipedia.org/wiki/Data_science"
    ]
    
    for url in urls:
        result = await scraper.extract_article(url)
        print(f"Extracted: {result['title']}")

asyncio.run(main())
```

## Testing

### Unit Tests

```python
import pytest
from src.selectors.yaml_loader import YAMLSelectorLoader
from src.selectors.validator import SelectorValidator

@pytest.mark.asyncio
async def test_yaml_selector_loading():
    validator = SelectorValidator()
    loader = YAMLSelectorLoader(validator)
    
    # Test loading from test directory
    result = await loader.load_selectors_from_directory("tests/fixtures/selectors")
    
    assert result.success
    assert result.selectors_loaded > 0
    assert result.selectors_failed == 0

@pytest.mark.asyncio
async def test_single_selector_loading():
    validator = SelectorValidator()
    loader = YAMLSelectorLoader(validator)
    
    # Test loading single file
    selector = await loader.load_selector_from_file("tests/fixtures/selectors/article_title.yaml")
    
    assert selector is not None
    assert selector.id == "article_title"
    assert selector.selector_type.value == "css"
```

### Integration Tests

```python
import pytest
from src.sites.wikipedia.scraper import WikipediaScraper

@pytest.mark.asyncio
async def test_wikipedia_extraction_with_yaml():
    scraper = WikipediaScraper()
    
    # Initialize
    success = await scraper.initialize()
    assert success
    
    # Test extraction
    result = await scraper.extract_article("https://en.wikipedia.org/wiki/Python")
    
    assert result is not None
    assert result['title'] is not None
    assert result['content'] is not None
    assert result['extraction_method'] == 'yaml_selectors'
```

## Troubleshooting

### Common Issues

**Issue**: YAML selectors not loading
```
Error: Directory not found: src/sites/wikipedia/selectors
```
**Solution**: Ensure the selectors directory exists and contains YAML files

**Issue**: Invalid YAML syntax
```
Error: Invalid YAML syntax: mapping values are not allowed here
```
**Solution**: Validate YAML syntax using online YAML validator or IDE plugin

**Issue**: Selector validation failed
```
Error: Validation failed: Missing required field: strategies
```
**Solution**: Ensure all required fields are present in YAML selector files

**Issue**: Selector not found during extraction
```
Warning: YAML selector not found: article_title
```
**Solution**: Check that selector ID matches filename and YAML content

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("src.selectors")
logger.setLevel(logging.DEBUG)
```

### Performance Monitoring

Monitor selector loading performance:

```python
# Get performance statistics
stats = selector_engine.get_yaml_statistics()
print(f"Loading time: {stats['loading_time_ms']}ms")
print(f"Total selectors: {stats['total_selectors']}")
```

## Next Steps

1. **Create YAML Selector Files**: Define selectors for all Wikipedia extraction needs
2. **Implement Validation Rules**: Add comprehensive validation for selector configurations
3. **Add Performance Monitoring**: Implement detailed performance tracking
4. **Create Test Suite**: Add comprehensive unit and integration tests
5. **Documentation**: Create detailed documentation for selector configuration
6. **Hot Reloading**: Implement hot-reloading for development workflow

## Support

For issues and questions:
- Check the troubleshooting section above
- Review the API documentation in `contracts/yaml-selector-api.md`
- Examine the data models in `data-model.md`
- Check the research findings in `research.md`
