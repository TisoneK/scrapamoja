# Quickstart Guide: Site Template Integration Framework

**Feature**: 017-site-template-integration  
**Version**: 1.0  
**Date**: 2025-01-29

## Overview

The Site Template Integration Framework enables rapid development of site scrapers by leveraging existing Scorewise framework components. This guide will help you create your first site scraper using the template framework.

## Prerequisites

- Python 3.11+ installed
- Scorewise framework setup completed
- Existing framework components available:
  - `BaseSiteScraper` from `src.sites.base.site_scraper`
  - `BaseFlow` from `src.sites.base.flow`
  - Selector engine and extractor module
  - Browser lifecycle management

## Quick Start: Creating a GitHub Scraper

### Step 1: Create Template Structure

Create the template directory structure:

```bash
mkdir -p src/sites/github/{extraction,selectors,flows}
touch src/sites/github/{__init__.py,scraper.py,flow.py,config.py,integration_bridge.py,selector_loader.py}
touch src/sites/github/extraction/{__init__.py,rules.py,models.py}
touch src/sites/github/selectors/{search_input.yaml,repository_list.yaml,repository_details.yaml}
touch src/sites/github/flows/{search_flow.py,pagination_flow.py}
```

### Step 2: Define YAML Selectors

Create selectors for GitHub elements:

```yaml
# src/sites/github/selectors/search_input.yaml
name: search_input
description: "GitHub search input field"
strategies:
  - type: semantic
    selector: "input[placeholder*='Search' i]"
    weight: 0.9
  - type: attribute
    selector: "input[name='q']"
    weight: 0.8
  - type: text_anchor
    text: "Search"
    element_type: input
    weight: 0.7
confidence_threshold: 0.7
validation_rules:
  - type: element_exists
  - type: input_field
```

```yaml
# src/sites/github/selectors/repository_list.yaml
name: repository_list
description: "List of GitHub repositories in search results"
strategies:
  - type: semantic
    selector: "div[data-testid='results-list'] li"
    weight: 0.9
  - type: structural
    selector: "ul.repo-list li"
    weight: 0.8
  - type: css_class
    selector: ".repo-list-item"
    weight: 0.7
confidence_threshold: 0.7
validation_rules:
  - type: list_element
  - type: contains_link
```

### Step 3: Create Integration Bridge

```python
# src/sites/github/integration_bridge.py
from typing import Any, Dict
from src.sites.base.template.integration_bridge import IIntegrationBridge
from src.models.selector_models import SemanticSelector
from src.extractor import ExtractionRule, ExtractionType, DataType, TransformationType

class GitHubIntegrationBridge(IIntegrationBridge):
    def __init__(self, selector_engine: Any):
        self.selector_engine = selector_engine
        self.yaml_integration = GitHubSelectorIntegration(selector_engine)
    
    async def initialize_complete_integration(self) -> bool:
        """Initialize complete framework integration."""
        yaml_success = await self.yaml_integration.load_github_selectors()
        
        if yaml_success:
            self._create_dom_context_bridge()
            return True
        return False
    
    def _create_dom_context_bridge(self) -> None:
        """Create DOM context bridge using existing framework."""
        # DOM context bridge automatically handled by BaseSiteScraper
        pass
    
    async def load_selectors(self) -> bool:
        """Load YAML selectors into existing selector engine."""
        return await self.yaml_integration.load_github_selectors()
    
    async def setup_extraction_rules(self) -> bool:
        """Setup extraction rules using existing extractor module."""
        # Extraction rules automatically loaded by GitHubExtractionRules
        return True
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get current integration status and health."""
        return {
            "bridge_type": "GitHubIntegrationBridge",
            "selector_engine_connected": True,
            "selectors_loaded": len(self.yaml_integration.get_loaded_selectors()),
            "extraction_rules_ready": True,
            "integration_complete": True
        }
```

### Step 4: Create Selector Loader

```python
# src/sites/github/selector_loader.py
import yaml
from pathlib import Path
from typing import Any, Dict, List
from src.sites.base.template.selector_loader import ISelectorLoader

class GitHubSelectorIntegration(ISelectorLoader):
    def __init__(self, selector_engine: Any):
        self.selector_engine = selector_engine
        self.loaded_selectors: List[str] = []
    
    async def load_github_selectors(self) -> bool:
        """Load GitHub selectors into existing selector engine."""
        selectors_dir = Path(__file__).parent / "selectors"
        
        for yaml_file in selectors_dir.glob("*.yaml"):
            success = await self._load_selector_from_file(yaml_file)
            if success:
                self.loaded_selectors.append(yaml_file.stem)
        
        return len(self.loaded_selectors) > 0
    
    async def _load_selector_from_file(self, yaml_file: Path) -> bool:
        """Load selector from YAML file."""
        try:
            with open(yaml_file, 'r') as f:
                config = yaml.safe_load(f)
            
            return await self.register_selector(config['name'], config)
        except Exception as e:
            print(f"Failed to load selector {yaml_file}: {e}")
            return False
    
    async def register_selector(self, selector_name: str, selector_config: Dict[str, Any]) -> bool:
        """Register selector with existing selector engine."""
        if hasattr(self.selector_engine, 'register_selector'):
            from src.models.selector_models import SemanticSelector
            
            selector = SemanticSelector(
                name=selector_name,
                strategies=selector_config['strategies'],
                confidence_threshold=selector_config.get('confidence_threshold', 0.7),
                validation_rules=selector_config.get('validation_rules', [])
            )
            
            self.selector_engine.register_selector(selector_name, selector)
            return True
        return False
    
    def get_loaded_selectors(self) -> List[str]:
        """Get list of loaded selector names."""
        return self.loaded_selectors
```

### Step 5: Create Extraction Rules

```python
# src/sites/github/extraction/rules.py
from typing import Dict, Any
from src.extractor import ExtractionRule, ExtractionType, DataType, TransformationType

class GitHubExtractionRules:
    def get_repository_rules(self) -> Dict[str, ExtractionRule]:
        """Get extraction rules for repository data."""
        return {
            "repo_name": ExtractionRule(
                selector="repository_list",
                extraction_type=ExtractionType.TEXT,
                data_type=DataType.STRING,
                transformations=[TransformationType.TRIM, TransformationType.CLEAN],
                required=True
            ),
            "repo_url": ExtractionRule(
                selector="repository_list",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.STRING,
                attribute_name="href",
                transformations=[TransformationType.TRIM],
                required=True
            ),
            "repo_description": ExtractionRule(
                selector="repository_list",
                extraction_type=ExtractionType.TEXT,
                data_type=DataType.STRING,
                transformations=[TransformationType.TRIM, TransformationType.CLEAN],
                required=False
            ),
            "stars_count": ExtractionRule(
                selector="repository_list",
                extraction_type=ExtractionType.TEXT,
                data_type=DataType.INTEGER,
                transformations=[TransformationType.EXTRACT_NUMBERS],
                required=False
            ),
            "language": ExtractionRule(
                selector="repository_list",
                extraction_type=ExtractionType.TEXT,
                data_type=DataType.STRING,
                transformations=[TransformationType.TRIM],
                required=False
            )
        }
    
    def get_search_rules(self) -> Dict[str, ExtractionRule]:
        """Get extraction rules for search functionality."""
        return {
            "search_query": ExtractionRule(
                selector="search_input",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.STRING,
                attribute_name="value",
                transformations=[TransformationType.TRIM],
                required=True
            )
        }
```

### Step 6: Create Main Scraper

```python
# src/sites/github/scraper.py
from typing import Any, Dict
from src.sites.base.site_scraper import BaseSiteScraper
from .flow import GitHubFlow
from .integration_bridge import GitHubIntegrationBridge
from .extraction.rules import GitHubExtractionRules

class GitHubScraper(BaseSiteScraper):
    """GitHub scraper using template framework."""
    
    def __init__(self, page: Any, selector_engine: Any):
        super().__init__(page, selector_engine)
        
        # GitHub-specific components
        self.flow = GitHubFlow(page, selector_engine)
        self.integration_bridge = GitHubIntegrationBridge(selector_engine)
        self.extraction_rules = GitHubExtractionRules()
    
    async def initialize(self) -> bool:
        """Initialize GitHub scraper with framework integration."""
        return await self.integration_bridge.initialize_complete_integration()
    
    async def scrape_repositories(self, query: str, **kwargs) -> Dict[str, Any]:
        """Scrape GitHub repositories for given query."""
        # Initialize framework integration
        await self.integration_bridge.initialize_complete_integration()
        
        # Perform search
        await self.flow.search_repositories(query)
        
        # Extract repository data
        repos = await self.selector_engine.find_all(self.page, "repository_list")
        
        results = []
        for repo in repos:
            repo_data = await self._extract_repository_data(repo)
            results.append(repo_data)
        
        return {
            "query": query,
            "repositories": results,
            "total_count": len(results),
            "scraping_metadata": {
                "selectors_used": self.integration_bridge.get_integration_status()["selectors_loaded"],
                "extraction_rules_applied": len(self.extraction_rules.get_repository_rules())
            }
        }
    
    async def _extract_repository_data(self, repo_element: Any) -> Dict[str, Any]:
        """Extract data from a single repository element."""
        rules = self.extraction_rules.get_repository_rules()
        repo_data = {}
        
        for field_name, rule in rules.items():
            try:
                # Use existing extractor module
                extracted_value = await self.extractor.extract(
                    repo_element, 
                    rule.selector,
                    extraction_type=rule.extraction_type,
                    transformations=rule.transformations
                )
                repo_data[field_name] = extracted_value
            except Exception as e:
                if rule.required:
                    raise
                repo_data[field_name] = None
        
        return repo_data
```

### Step 7: Create Flow Component

```python
# src/sites/github/flow.py
from typing import Any
from src.sites.base.flow import BaseFlow

class GitHubFlow(BaseFlow):
    """GitHub-specific flow operations."""
    
    def __init__(self, page: Any, selector_engine: Any):
        super().__init__(page, selector_engine)
    
    async def search_repositories(self, query: str) -> bool:
        """Search for repositories on GitHub."""
        try:
            # Navigate to GitHub
            await self.page.goto("https://github.com")
            
            # Find search input using selector engine
            search_input = await self.selector_engine.find(self.page, "search_input")
            
            if search_input:
                # Fill search input
                await search_input.fill(query)
                
                # Submit search (GitHub automatically searches on input)
                await self.page.wait_for_timeout(1000)
                
                # Wait for results
                await self.page.wait_for_selector("div[data-testid='results-list']", timeout=10000)
                
                return True
            else:
                print("Search input not found")
                return False
                
        except Exception as e:
            print(f"Search failed: {e}")
            return False
    
    async def navigate_to_next_page(self) -> bool:
        """Navigate to next page of results."""
        try:
            next_button = await self.page.query_selector("a[rel='next']")
            if next_button:
                await next_button.click()
                await self.page.wait_for_timeout(2000)
                return True
            return False
        except Exception as e:
            print(f"Navigation failed: {e}")
            return False
```

### Step 8: Create Configuration

```python
# src/sites/github/config.py
from typing import Dict, Any

class GitHubConfig:
    """GitHub scraper configuration."""
    
    # Site-specific settings
    SITE_DOMAIN = "github.com"
    SUPPORTED_DOMAINS = ["github.com", "api.github.com"]
    
    # Selector settings
    CONFIDENCE_THRESHOLD = 0.7
    SELECTOR_TIMEOUT = 10000
    
    # Extraction settings
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    
    # Performance settings
    MAX_CONCURRENT_REQUESTS = 1
    REQUEST_DELAY = 2.0
    
    @classmethod
    def get_template_config(cls) -> Dict[str, Any]:
        """Get template configuration for registry."""
        return {
            "name": "github",
            "version": "1.0.0",
            "description": "GitHub repository scraper",
            "site_domain": cls.SITE_DOMAIN,
            "supported_domains": cls.SUPPORTED_DOMAINS,
            "capabilities": ["repository_extraction", "search", "pagination"],
            "configuration_schema": {
                "type": "object",
                "properties": {
                    "confidence_threshold": {
                        "type": "number",
                        "default": cls.CONFIDENCE_THRESHOLD,
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "max_retries": {
                        "type": "integer",
                        "default": cls.MAX_RETRIES,
                        "minimum": 0,
                        "maximum": 10
                    }
                }
            }
        }
```

### Step 9: Use the Scraper

```python
# Example usage
import asyncio
from playwright.async_api import async_playwright
from src.sites.github.scraper import GitHubScraper
from src.selectors.engine import SelectorEngine

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Initialize selector engine (existing framework component)
        selector_engine = SelectorEngine()
        
        # Create GitHub scraper using template
        github_scraper = GitHubScraper(page, selector_engine)
        
        # Initialize scraper
        await github_scraper.initialize()
        
        # Scrape repositories
        results = await github_scraper.scrape_repositories("python web scraping")
        
        print(f"Found {len(results['repositories'])} repositories")
        for repo in results['repositories'][:3]:
            print(f"- {repo['repo_name']}: {repo.get('repo_description', 'No description')}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Template Registry Usage

### Register Template

```python
from src.sites.base.template.site_registry import SiteRegistry

async def register_github_template():
    registry = SiteRegistry()
    
    # Register GitHub template
    success = await registry.register_template(
        template_name="github",
        template_path="/src/sites/github"
    )
    
    if success:
        print("GitHub template registered successfully")
    else:
        print("Failed to register GitHub template")
```

### Discover Templates

```python
async def discover_templates():
    registry = SiteRegistry()
    
    # Discover all templates
    templates = await registry.discover_templates(["/src/sites"])
    
    print(f"Discovered {len(templates)} templates:")
    for template in templates:
        print(f"- {template['name']}: {template['description']}")
```

### Load Template by Name

```python
async def load_template_by_name():
    registry = SiteRegistry()
    
    # Load GitHub template
    github_scraper = await registry.load_template(
        template_name="github",
        page=page,
        selector_engine=selector_engine
    )
    
    if github_scraper:
        results = await github_scraper.scrape_repositories("python")
        print(f"Scraped {len(results['repositories'])} repositories")
```

## Validation and Testing

### Validate Template

```python
from src.sites.base.template.validation import ValidationFramework

async def validate_github_template():
    validator = ValidationFramework()
    
    # Validate GitHub template
    result = await validator.validate_template("/src/sites/github")
    
    if result.is_valid:
        print("Template validation passed")
        print(f"Compliance score: {result.compliance_score}")
    else:
        print("Template validation failed:")
        for error in result.errors:
            print(f"  - {error}")
```

### Check Framework Compliance

```python
async def check_compliance():
    validator = ValidationFramework()
    
    # Check constitutional compliance
    compliance = await validator.check_framework_compliance("/src/sites/github")
    
    if compliance.is_compliant:
        print("Template is constitutionally compliant")
    else:
        print("Compliance violations:")
        for violation in compliance.violations:
            print(f"  - {violation}")
```

## Best Practices

### 1. Follow Template Structure

Always use the standard template structure to ensure compatibility:
```
src/sites/{site_name}/
├── __init__.py
├── scraper.py
├── flow.py
├── config.py
├── integration_bridge.py
├── selector_loader.py
├── extraction/
├── selectors/
└── flows/
```

### 2. Use Existing Framework Components

Leverage existing components instead of reinventing:
- Extend `BaseSiteScraper` for main scraper
- Use existing selector engine for element location
- Utilize extractor module for data transformation
- Inherit browser lifecycle management automatically

### 3. Define Comprehensive Selectors

Create multi-strategy selectors with fallbacks:
```yaml
strategies:
  - type: semantic
    selector: "semantic selector"
    weight: 0.9
  - type: attribute
    selector: "attribute selector"
    weight: 0.8
  - type: text_anchor
    text: "anchor text"
    weight: 0.7
```

### 4. Implement Error Handling

Add proper error handling and graceful degradation:
```python
try:
    element = await self.selector_engine.find(self.page, "selector")
    if element:
        # Process element
        pass
    else:
        # Handle element not found
        logger.warning("Element not found")
except Exception as e:
    # Handle exceptions
    logger.error(f"Error: {e}")
```

### 5. Validate Templates

Always validate templates before deployment:
```python
# Validate structure
await validator.validate_template_structure("/src/sites/github")

# Validate selectors
await validator.validate_selectors(selector_configs)

# Check compliance
await validator.check_framework_compliance("/src/sites/github")
```

## Troubleshooting

### Common Issues

1. **Selectors not loading**: Check YAML syntax and selector engine integration
2. **Extraction rules failing**: Verify rule definitions and element availability
3. **Framework integration issues**: Ensure bridge components are properly initialized
4. **Validation failures**: Review template structure and compliance requirements

### Debug Mode

Enable debug mode for detailed logging:
```python
# In config.py
DEBUG_MODE = True
LOG_LEVEL = "DEBUG"

# Enable detailed selector engine logging
SELECTOR_ENGINE_DEBUG = True
```

### Performance Monitoring

Monitor template performance:
```python
# Get integration status
status = await integration_bridge.get_integration_status()
print(f"Load time: {status['load_time']}ms")
print(f"Selectors loaded: {status['selectors_loaded']}")

# Monitor extraction performance
start_time = time.time()
results = await scraper.scrape_repositories("python")
extraction_time = time.time() - start_time
print(f"Extraction time: {extraction_time}s")
```

## Next Steps

1. **Create more templates**: Apply the same pattern to other sites
2. **Extend functionality**: Add advanced features like pagination, authentication
3. **Optimize performance**: Implement caching, parallel processing
4. **Share templates**: Contribute templates to the community registry
5. **Monitor usage**: Track template performance and usage metrics

## Support

For additional help:
- Check the existing Wikipedia implementation as reference
- Review framework documentation in `docs/`
- Consult the constitution in `.specify/memory/constitution.md`
- Use validation tools to debug template issues
