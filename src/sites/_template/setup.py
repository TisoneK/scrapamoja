"""
Template setup script for the modular site scraper template.

This script provides automated setup functionality for creating new site scrapers
from the template, including configuration, validation, and initialization.
"""

import os
import sys
import shutil
import argparse
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio
import json
from datetime import datetime

from .validation import TemplateValidator, validate_template


class TemplateSetup:
    """Automated template setup and configuration."""
    
    def __init__(self, template_path: str = None):
        """
        Initialize template setup.
        
        Args:
            template_path: Path to the template directory
        """
        self.template_path = Path(template_path) if template_path else Path(__file__).parent
        self.setup_log = []
        
        # Default configuration values
        self.default_config = {
            'site_id': '',
            'site_name': '',
            'site_url': '',
            'site_description': '',
            'author': '',
            'email': '',
            'license': 'MIT',
            'python_version': '3.11+',
            'create_selectors': True,
            'create_tests': True,
            'create_docs': True,
            'register_scraper': True,
            'pattern': 'standard',  # simple, standard, complex
            'interactive_mode': False,
            'complexity_assessment': True,
            'domains': [],  # Custom domain selection for complex pattern
            'exclude_domains': [],  # Domains to exclude
            'custom_flows': []  # Custom flows to include
        }
        
        # Pattern complexity definitions
        self.pattern_complexity = {
            'simple': {
                'description': 'Single flow.py file for basic sites',
                'suitable_for': ['Static sites', 'Simple navigation', 'Basic extraction'],
                'features': ['Basic navigation', 'Simple extraction', 'No authentication']
            },
            'standard': {
                'description': 'flow.py + flows/ for moderate complexity',
                'suitable_for': ['Dynamic sites', 'Moderate complexity', 'Mixed operations'],
                'features': ['Dynamic content', 'Authentication', 'Search functionality', 'Pagination']
            },
            'complex': {
                'description': 'Domain-separated flows for sophisticated sites',
                'suitable_for': ['SPAs', 'Complex navigation', 'Multi-domain operations'],
                'features': ['Real-time data', 'Domain separation', 'Advanced filtering', 'High scalability']
            }
        }
    
    async def setup_new_site(
        self,
        site_name: str,
        site_id: str = None,
        site_url: str = None,
        target_dir: str = None,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Set up a new site scraper from the template.
        
        Args:
            site_name: Name of the new site
            site_id: Site ID (defaults to sanitized site_name)
            site_url: Base URL of the site
            target_dir: Target directory (defaults to src/sites/{site_name})
            config: Additional configuration options
            
        Returns:
            Setup results
        """
        try:
            start_time = datetime.utcnow()
            
            # Validate inputs
            if not site_name:
                return {
                    'success': False,
                    'error': 'Site name is required'
                }
            
            # Set defaults
            site_id = site_id or self._sanitize_site_id(site_name)
            site_url = site_url or f"https://{site_name.lower().replace(' ', '')}.com"
            target_dir = target_dir or f"src/sites/{site_name.lower().replace(' ', '_')}"
            
            # Merge configuration
            setup_config = {**self.default_config, **(config or {})}
            setup_config.update({
                'site_name': site_name,
                'site_id': site_id,
                'site_url': site_url,
                'target_dir': target_dir
            })
            
            # Assess complexity if enabled
            if setup_config.get('complexity_assessment', True):
                if setup_config.get('interactive_mode', False):
                    # Interactive assessment
                    recommended_pattern = await self.assess_complexity_interactive(site_url)
                else:
                    # Use specified pattern or default
                    recommended_pattern = setup_config.get('pattern', 'standard')
                
                setup_config['pattern'] = recommended_pattern
                self._log(f"Recommended pattern: {recommended_pattern}")
            
            # Handle domain customization for complex pattern
            if setup_config['pattern'] == 'complex':
                if setup_config.get('interactive_mode', False):
                    # Interactive domain customization
                    domain_config = await self.customize_domains_interactive()
                    setup_config.update(domain_config)
                
                # Validate domain selection
                if setup_config.get('domains'):
                    validation_result = self.validate_domain_selection(
                        setup_config['domains'],
                        setup_config.get('exclude_domains', [])
                    )
                    
                    if not validation_result['valid']:
                        return {
                            'success': False,
                            'error': 'Domain validation failed',
                            'validation_errors': validation_result['errors']
                        }
                    
                    if validation_result['warnings']:
                        for warning in validation_result['warnings']:
                            self._log(warning, level='WARNING')
            
            # Validate pattern selection to prevent anti-patterns
            pattern_validation = self.validate_pattern_selection(
                setup_config['pattern'],
                setup_config.get('domains', []),
                setup_config.get('site_url')
            )
            
            if not pattern_validation['valid']:
                return {
                    'success': False,
                    'error': 'Pattern validation failed',
                    'validation_errors': pattern_validation['errors']
                }
            
            if pattern_validation['warnings']:
                for warning in pattern_validation['warnings']:
                    self._log(warning, level='WARNING')
            
            if pattern_validation['recommendations']:
                for recommendation in pattern_validation['recommendations']:
                    self._log(f"Recommendation: {recommendation}", level='INFO')
            
            self._log(f"Starting setup for {site_name} (ID: {site_id})")
            self._log(f"Using pattern: {setup_config['pattern']}")
            
            # Validate template first
            self._log("Validating template...")
            validation_result = await validate_template(str(self.template_path))
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': 'Template validation failed',
                    'validation_errors': validation_result['errors']
                }
            
            # Create target directory
            target_path = Path(target_dir)
            self._log(f"Creating target directory: {target_path}")
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Copy template files
            self._log("Copying template files...")
            await self._copy_template_files(target_path, setup_config)
            
            # Configure scraper
            self._log("Configuring scraper...")
            await self._configure_scraper(target_path, setup_config)
            
            # Create selector files
            if setup_config['create_selectors']:
                self._log("Creating selector files...")
                await self._create_selector_files(target_path, setup_config)
            
            # Create test files
            if setup_config['create_tests']:
                self._log("Creating test files...")
                await self._create_test_files(target_path, setup_config)
            
            # Create documentation
            if setup_config['create_docs']:
                self._log("Creating documentation...")
                await self._create_documentation(target_path, setup_config)
            
            # Register scraper
            if setup_config['register_scraper']:
                self._log("Registering scraper...")
                await self._register_scraper(target_path, setup_config)
            
            # Validate new site
            self._log("Validating new site...")
            validation_result = await validate_template(str(target_path))
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            result = {
                'success': True,
                'site_name': site_name,
                'site_id': site_id,
                'site_url': site_url,
                'target_directory': str(target_path),
                'execution_time_ms': execution_time,
                'setup_timestamp': start_time.isoformat(),
                'validation_result': validation_result,
                'setup_log': self.setup_log
            }
            
            self._log(f"Setup completed successfully in {execution_time:.2f}ms")
            return result
            
        except Exception as e:
            error_msg = f"Setup failed: {str(e)}"
            self._log(error_msg, level='ERROR')
            return {
                'success': False,
                'error': error_msg,
                'setup_log': self.setup_log
            }
    
    async def _copy_template_files(self, target_path: Path, config: Dict[str, Any]) -> None:
        """Copy template files to target directory based on pattern."""
        try:
            pattern = config.get('pattern', 'standard')
            
            # Copy all files except setup.py and validation.py (they're setup utilities)
            exclude_files = {'setup.py', 'validation.py', '__pycache__'}
            
            # Pattern-specific file handling
            if pattern == 'simple':
                # Copy only simple pattern files
                await self._copy_simple_pattern(target_path, config)
            elif pattern == 'standard':
                # Copy standard pattern files
                await self._copy_standard_pattern(target_path, config)
            elif pattern == 'complex':
                # Copy complex pattern files
                await self._copy_complex_pattern(target_path, config)
            else:
                # Default to standard pattern
                await self._copy_standard_pattern(target_path, config)
            
            # Copy common files (config, components, processors, etc.)
            await self._copy_common_files(target_path, config)
            
        except Exception as e:
            raise Exception(f"Failed to copy template files: {str(e)}")
    
    async def _copy_simple_pattern(self, target_path: Path, config: Dict[str, Any]) -> None:
        """Copy simple pattern template files."""
        simple_pattern_dir = self.template_path / 'patterns' / 'simple'
        
        if simple_pattern_dir.exists():
            # Copy flow.py from simple pattern
            source_flow = simple_pattern_dir / 'flow.py'
            target_flow = target_path / 'flow.py'
            
            if source_flow.exists():
                await self._copy_file_with_placeholders(source_flow, target_flow, config)
                self._log("Copied simple pattern flow.py")
        else:
            # Fallback to original flow.py
            source_flow = self.template_path / 'flow.py'
            target_flow = target_path / 'flow.py'
            
            if source_flow.exists():
                await self._copy_file_with_placeholders(source_flow, target_flow, config)
                self._log("Copied fallback flow.py for simple pattern")
    
    async def _copy_standard_pattern(self, target_path: Path, config: Dict[str, Any]) -> None:
        """Copy standard pattern template files."""
        standard_pattern_dir = self.template_path / 'patterns' / 'standard'
        
        if standard_pattern_dir.exists():
            # Copy flow.py from standard pattern
            source_flow = standard_pattern_dir / 'flow.py'
            target_flow = target_path / 'flow.py'
            
            if source_flow.exists():
                await self._copy_file_with_placeholders(source_flow, target_flow, config)
                self._log("Copied standard pattern flow.py")
            
            # Copy flows directory
            source_flows = standard_pattern_dir / 'flows'
            target_flows = target_path / 'flows'
            
            if source_flows.exists():
                await self._copy_directory(source_flows, target_flows, config)
                self._log("Copied standard pattern flows directory")
        else:
            # Fallback to original structure
            await self._copy_fallback_structure(target_path, config)
    
    async def _copy_complex_pattern(self, target_path: Path, config: Dict[str, Any]) -> None:
        """Copy complex pattern template files."""
        complex_pattern_dir = self.template_path / 'patterns' / 'complex'
        
        if complex_pattern_dir.exists():
            # Copy flows directory with domain subfolders
            source_flows = complex_pattern_dir / 'flows'
            target_flows = target_path / 'flows'
            
            if source_flows.exists():
                await self._copy_directory(source_flows, target_flows, config)
                self._log("Copied complex pattern flows directory")
        else:
            # Fallback to original structure
            await self._copy_fallback_structure(target_path, config)
    
    async def _copy_fallback_structure(self, target_path: Path, config: Dict[str, Any]) -> None:
        """Copy fallback template structure."""
        # Copy original flow.py
        source_flow = self.template_path / 'flow.py'
        target_flow = target_path / 'flow.py'
        
        if source_flow.exists():
            await self._copy_file_with_placeholders(source_flow, target_flow, config)
            self._log("Copied fallback flow.py")
        
        # Copy original flows directory
        source_flows = self.template_path / 'flows'
        target_flows = target_path / 'flows'
        
        if source_flows.exists():
            await self._copy_directory(source_flows, target_flows, config)
            self._log("Copied fallback flows directory")
    
    async def _copy_common_files(self, target_path: Path, config: Dict[str, Any]) -> None:
        """Copy common template files (config, components, etc.)."""
        common_dirs = ['config', 'components', 'processors', 'validators', 'selectors']
        common_files = ['scraper.py', 'models.py', 'validation.py']
        
        # Copy common directories
        for dir_name in common_dirs:
            source_dir = self.template_path / dir_name
            target_dir = target_path / dir_name
            
            if source_dir.exists():
                target_dir.mkdir(exist_ok=True)
                await self._copy_directory(source_dir, target_dir, config)
                self._log(f"Copied {dir_name} directory")
        
        # Copy common files
        for file_name in common_files:
            source_file = self.template_path / file_name
            target_file = target_path / file_name
            
            if source_file.exists():
                await self._copy_file_with_placeholders(source_file, target_file, config)
                self._log(f"Copied {file_name} file")
    
    async def _copy_directory(self, source_dir: Path, target_dir: Path, config: Dict[str, Any]) -> None:
        """Copy directory recursively with placeholder replacement."""
        try:
            for item in source_dir.iterdir():
                if item.name == '__pycache__':
                    continue
                
                if item.is_file():
                    await self._copy_file_with_placeholders(item, target_dir / item.name, config)
                elif item.is_dir():
                    new_target_dir = target_dir / item.name
                    new_target_dir.mkdir(exist_ok=True)
                    await self._copy_directory(item, new_target_dir, config)
        
        except Exception as e:
            raise Exception(f"Failed to copy directory {source_dir}: {str(e)}")
    
    async def _copy_file_with_placeholders(self, source_file: Path, target_file: Path, config: Dict[str, Any]) -> None:
        """Copy file and replace placeholders."""
        try:
            # Read source file
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace placeholders
            placeholders = {
                '{{SITE_ID}}': config['site_id'],
                '{{SITE_NAME}}': config['site_name'],
                '{{SITE_URL}}': config['site_url'],
                '{{SITE_DESCRIPTION}}': config.get('site_description', f'Scraper for {config["site_name"]}'),
                '{{AUTHOR}}': config.get('author', 'Developer'),
                '{{EMAIL}}': config.get('email', 'developer@example.com'),
                '{{LICENSE}}': config.get('license', 'MIT'),
                '{{PYTHON_VERSION}}': config.get('python_version', '3.11+'),
                '{{CREATION_DATE}}': datetime.utcnow().strftime('%Y-%m-%d'),
                '{{CLASS_NAME}}': self._to_pascal_case(config['site_name']),
                '{{MODULE_NAME}}': config['site_name'].lower().replace(' ', '_'),
                '{{PACKAGE_NAME}}': config['site_name'].lower().replace(' ', '-')
            }
            
            for placeholder, value in placeholders.items():
                content = content.replace(placeholder, value)
            
            # Write target file
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self._log(f"Copied: {source_file.name} -> {target_file.name}")
            
        except Exception as e:
            raise Exception(f"Failed to copy file {source_file}: {str(e)}")
    
    async def _configure_scraper(self, target_path: Path, config: Dict[str, Any]) -> None:
        """Configure the scraper with site-specific settings."""
        try:
            # Update scraper.py with site-specific configuration
            scraper_file = target_path / 'scraper.py'
            if scraper_file.exists():
                with open(scraper_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Add site-specific configuration
                site_config = f'''
# Site-specific configuration
SITE_CONFIG = {{
    "id": "{config['site_id']}",
    "name": "{config['site_name']}",
    "base_url": "{config['site_url']}",
    "description": "{config.get('site_description', f'Scraper for {config["site_name"]}')}",
    "author": "{config.get('author', 'Developer')}",
    "created_at": "{datetime.utcnow().isoformat()}",
    "selectors": {{
        # Add your site-specific selectors here
    }}
}}
'''
                
                # Find a good place to insert the configuration
                if 'SITE_CONFIG' not in content:
                    # Insert after imports
                    lines = content.split('\n')
                    insert_index = 0
                    for i, line in enumerate(lines):
                        if line.startswith('from ') or line.startswith('import '):
                            insert_index = i + 1
                        elif line.strip() == '' and insert_index > 0:
                            break
                    
                    lines.insert(insert_index, site_config)
                    content = '\n'.join(lines)
                    
                    with open(scraper_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                
                self._log("Configured scraper.py")
        
        except Exception as e:
            raise Exception(f"Failed to configure scraper: {str(e)}")
    
    async def _create_selector_files(self, target_path: Path, config: Dict[str, Any]) -> None:
        """Create basic selector files."""
        try:
            selectors_dir = target_path / 'selectors'
            selectors_dir.mkdir(exist_ok=True)
            
            # Create basic selector templates
            basic_selectors = {
                'search_input.yaml': f'''# Search input selector for {config['site_name']}
selector: "input[type='search'], #search, .search-input"
type: "input"
confidence_threshold: 0.8
attributes:
  - name: "placeholder"
    type: "string"
  - name: "name"
    type: "string"
description: "Main search input field on {config['site_name']}"
''',
                'search_button.yaml': f'''# Search button selector for {config['site_name']}
selector: "button[type='submit'], #search-btn, .search-button"
type: "button"
confidence_threshold: 0.8
attributes:
  - name: "text"
    type: "string"
description: "Search button on {config['site_name']}"
''',
                'results_container.yaml': f'''# Results container selector for {config['site_name']}
selector: ".results, .search-results, #results"
type: "container"
confidence_threshold: 0.7
description: "Container holding search results on {config['site_name']}"
''',
                'result_item.yaml': f'''# Result item selector for {config['site_name']}
selector: ".result, .item, .search-result"
type: "container"
confidence_threshold: 0.7
attributes:
  - name: "title"
    selector: ".title, h3, h4"
    type: "text"
  - name: "url"
    selector: "a"
    attribute: "href"
    type: "string"
  - name: "description"
    selector: ".description, .snippet, p"
    type: "text"
description: "Individual search result item on {config['site_name']}"
'''
            }
            
            for filename, content in basic_selectors.items():
                selector_file = selectors_dir / filename
                with open(selector_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            self._log(f"Created {len(basic_selectors)} selector files")
        
        except Exception as e:
            raise Exception(f"Failed to create selector files: {str(e)}")
    
    async def _create_test_files(self, target_path: Path, config: Dict[str, Any]) -> None:
        """Create basic test files."""
        try:
            tests_dir = target_path / 'tests'
            tests_dir.mkdir(exist_ok=True)
            
            # Create __init__.py
            init_file = tests_dir / '__init__.py'
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write('"""Tests for {site_name} scraper."""\n'.format(site_name=config['site_name']))
            
            # Create basic test file
            test_content = f'''"""
Tests for {config['site_name']} scraper.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

# Import your scraper class
# from src.sites.{config['site_name'].lower().replace(' ', '_')}.scraper import {self._to_pascal_case(config['site_name'])}Scraper


class Test{self._to_pascal_case(config['site_name'])}Scraper:
    """Test cases for {config['site_name']} scraper."""
    
    @pytest.fixture
    async def mock_page(self):
        """Create a mock Playwright page."""
        page = AsyncMock()
        page.goto = AsyncMock()
        page.title = AsyncMock(return_value=f"{config['site_name']} - Test Page")
        return page
    
    @pytest.fixture
    async def mock_selector_engine(self):
        """Create a mock selector engine."""
        engine = MagicMock()
        engine.find = AsyncMock()
        engine.find_all = AsyncMock(return_value=[])
        return engine
    
    @pytest.mark.asyncio
    async def test_scraper_initialization(self, mock_page, mock_selector_engine):
        """Test scraper initialization."""
        # Uncomment when scraper is implemented
        # scraper = {self._to_pascal_case(config['site_name'])}Scraper(mock_page, mock_selector_engine)
        # assert scraper.site_id == "{config['site_id']}"
        # assert scraper.site_name == "{config['site_name']}"
        # assert scraper.base_url == "{config['site_url']}"
        pass
    
    @pytest.mark.asyncio
    async def test_navigation(self, mock_page, mock_selector_engine):
        """Test navigation functionality."""
        # Uncomment when scraper is implemented
        # scraper = {self._to_pascal_case(config['site_name'])}Scraper(mock_page, mock_selector_engine)
        # await scraper.navigate()
        # mock_page.goto.assert_called_once_with("{config['site_url']}")
        pass
    
    @pytest.mark.asyncio
    async def test_search_functionality(self, mock_page, mock_selector_engine):
        """Test search functionality."""
        # Uncomment when scraper is implemented
        # scraper = {self._to_pascal_case(config['site_name'])}Scraper(mock_page, mock_selector_engine)
        # result = await scraper.scrape(query="test query")
        # assert result is not None
        # assert "type" in result
        pass


@pytest.mark.asyncio
async def test_full_scraping_flow():
    """Test full scraping flow integration."""
    # This test can be used for integration testing with real browser
    # Uncomment when ready for integration tests
    pass
'''
            
            test_file = tests_dir / f'test_{config["site_name"].lower().replace(" ", "_")}.py'
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(test_content)
            
            # Create pytest.ini
            pytest_ini = tests_dir / 'pytest.ini'
            with open(pytest_ini, 'w', encoding='utf-8') as f:
                f.write(f'''[tool:pytest]
testpaths = .
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
markers =
    asyncio: marks tests as async
    integration: marks tests as integration tests
''')
            
            self._log("Created test files")
        
        except Exception as e:
            raise Exception(f"Failed to create test files: {str(e)}")
    
    async def _create_documentation(self, target_path: Path, config: Dict[str, Any]) -> None:
        """Create documentation files."""
        try:
            docs_dir = target_path / 'docs'
            docs_dir.mkdir(exist_ok=True)
            
            # Create site-specific README
            readme_content = f'''# {config['site_name']} Scraper

{config.get('site_description', f'Scraper for {config["site_name"]}')}

## Overview

This scraper extracts data from {config['site_name']} ({config['site_url']}) using the modular scraper framework.

## Features

- **Modular Architecture**: Built with flows, processors, validators, and components
- **Async/Await**: Full async support for optimal performance
- **Configuration Management**: Multi-environment configuration
- **Error Handling**: Comprehensive error handling and resilience
- **Rate Limiting**: Built-in rate limiting to respect site policies
- **Stealth Mode**: Anti-bot detection avoidance

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/
```

## Usage

```python
from src.sites.{config['site_name'].lower().replace(' ', '_')} import {self._to_pascal_case(config['site_name'])}Scraper

# Initialize scraper
scraper = {self._to_pascal_case(config['site_name'])}Scraper(page, selector_engine)

# Navigate to site
await scraper.navigate()

# Perform search
results = await scraper.scrape(query="your search term")

# Normalize results
normalized = scraper.normalize(results)
```

## Configuration

Configuration is handled through the config module:

- `config/dev.py` - Development settings
- `config/prod.py` - Production settings
- `config/feature_flags.py` - Feature toggles

## Selectors

Selectors are defined in YAML files in the `selectors/` directory:

- `search_input.yaml` - Search input field
- `search_button.yaml` - Search button
- `results_container.yaml` - Results container
- `result_item.yaml` - Individual result items

## Testing

Run tests with:

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src/sites/{config['site_name'].lower().replace(' ', '_')}

# Run integration tests
pytest tests/ -m integration
```

## Contributing

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Ensure all tests pass

## License

{config.get('license', 'MIT')}

## Author

{config.get('author', 'Developer')} ({config.get('email', 'developer@example.com')})

## Created

{datetime.utcnow().strftime('%Y-%m-%d')}
'''
            
            readme_file = docs_dir / 'README.md'
            with open(readme_file, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            self._log("Created documentation")
        
        except Exception as e:
            raise Exception(f"Failed to create documentation: {str(e)}")
    
    async def _register_scraper(self, target_path: Path, config: Dict[str, Any]) -> None:
        """Register the scraper in the registry."""
        try:
            registry_file = Path('src/sites/registry.py')
            if not registry_file.exists():
                self._log("Registry file not found, skipping registration", level='WARNING')
                return
            
            # Read existing registry
            with open(registry_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add import statement
            import_line = f"from src.sites.{config['site_name'].lower().replace(' ', '_')}.scraper import {self._to_pascal_case(config['site_name'])}Scraper"
            if import_line not in content:
                # Find imports section and add
                lines = content.split('\n')
                import_index = 0
                for i, line in enumerate(lines):
                    if line.startswith('from src.sites.'):
                        import_index = i + 1
                
                lines.insert(import_index, import_line)
                content = '\n'.join(lines)
            
            # Add registration
            registration_line = f'registry.register("{config["site_id"]}", {self._to_pascal_case(config["site_name"])}Scraper)'
            if registration_line not in content:
                # Find registration section and add
                lines = content.split('\n')
                register_index = 0
                for i, line in enumerate(lines):
                    if 'registry.register(' in line:
                        register_index = i + 1
                
                lines.insert(register_index, registration_line)
                content = '\n'.join(lines)
            
            # Write updated registry
            with open(registry_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self._log("Registered scraper in registry")
        
        except Exception as e:
            self._log(f"Failed to register scraper: {str(e)}", level='WARNING')
    
    def _sanitize_site_id(self, site_name: str) -> str:
        """Sanitize site name to create valid site ID."""
        return site_name.lower().replace(' ', '_').replace('-', '_')
    
    def _to_pascal_case(self, text: str) -> str:
        """Convert text to PascalCase."""
        return ''.join(word.capitalize() for word in text.replace('-', ' ').replace('_', ' ').split())
    
    async def assess_complexity_interactive(self, site_url: str = None) -> str:
        """
        Interactive complexity assessment questionnaire.
        
        Args:
            site_url: Optional site URL for analysis
            
        Returns:
            Recommended pattern (simple, standard, complex)
        """
        print("\n" + "="*60)
        print("🎯 SITE COMPLEXITY ASSESSMENT")
        print("="*60)
        print("Answer the following questions to determine the best pattern for your site.\n")
        
        score = 0
        
        # Question 1: Site Architecture
        print("📋 Question 1: Site Architecture")
        print("What type of site are you scraping?")
        print("  A) Static content with basic navigation")
        print("  B) Dynamic content with moderate complexity")
        print("  C) Single Page Application (SPA) or highly interactive")
        
        answer = input("Your choice (A/B/C): ").upper().strip()
        if answer == 'A':
            score += 0
        elif answer == 'B':
            score += 3
        elif answer == 'C':
            score += 5
        
        # Question 2: Navigation Complexity
        print("\n📋 Question 2: Navigation Complexity")
        print("How complex is the site navigation?")
        print("  A) Basic page transitions (home, about, contact)")
        print("  B) Dynamic navigation with menus and tabs")
        print("  C) Complex multi-level navigation with breadcrumbs")
        
        answer = input("Your choice (A/B/C): ").upper().strip()
        if answer == 'A':
            score += 0
        elif answer == 'B':
            score += 2
        elif answer == 'C':
            score += 4
        
        # Question 3: Data Extraction Needs
        print("\n📋 Question 3: Data Extraction Needs")
        print("What kind of data extraction do you need?")
        print("  A) Basic text and link extraction")
        print("  B) Complex data structures (tables, forms, APIs)")
        print("  C) Real-time data extraction with updates")
        
        answer = input("Your choice (A/B/C): ").upper().strip()
        if answer == 'A':
            score += 0
        elif answer == 'B':
            score += 2
        elif answer == 'C':
            score += 5
        
        # Question 4: Authentication Requirements
        print("\n📋 Question 4: Authentication Requirements")
        print("Does the site require authentication?")
        print("  A) No authentication needed")
        print("  B) Simple username/password login")
        print("  C) OAuth, 2FA, or complex authentication")
        
        answer = input("Your choice (A/B/C): ").upper().strip()
        if answer == 'A':
            score += 0
        elif answer == 'B':
            score += 2
        elif answer == 'C':
            score += 4
        
        # Question 5: Real-time Features
        print("\n📋 Question 5: Real-time Features")
        print("Does the site have real-time features?")
        print("  A) No real-time features")
        print("  B) Some dynamic content updates")
        print("  C) Live data, WebSocket connections, frequent updates")
        
        answer = input("Your choice (A/B/C): ").upper().strip()
        if answer == 'A':
            score += 0
        elif answer == 'B':
            score += 2
        elif answer == 'C':
            score += 5
        
        # Question 6: Filtering Requirements
        print("\n📋 Question 6: Filtering Requirements")
        print("Do you need advanced filtering?")
        print("  A) No filtering needed")
        print("  B) Basic search and date filtering")
        print("  C) Multi-criteria filtering (date, sport, competition, etc.)")
        
        answer = input("Your choice (A/B/C): ").upper().strip()
        if answer == 'A':
            score += 0
        elif answer == 'B':
            score += 2
        elif answer == 'C':
            score += 4
        
        # Calculate recommendation
        if score <= 4:
            recommended = 'simple'
        elif score <= 12:
            recommended = 'standard'
        else:
            recommended = 'complex'
        
        # Show results
        print(f"\n📊 ASSESSMENT RESULTS")
        print(f"Score: {score}/24")
        print(f"Recommended Pattern: {recommended.upper()}")
        
        print(f"\n📋 PATTERN DETAILS:")
        pattern_info = self.pattern_complexity[recommended]
        print(f"Description: {pattern_info['description']}")
        print(f"Best for: {', '.join(pattern_info['suitable_for'])}")
        print(f"Features: {', '.join(pattern_info['features'])}")
        
        # Ask for confirmation
        confirm = input(f"\nUse {recommended} pattern? (Y/N): ").upper().strip()
        if confirm == 'Y':
            return recommended
        else:
            # Let user choose manually
            print("\nAvailable patterns:")
            print("  1) simple - Single flow.py file")
            print("  2) standard - flow.py + flows/")
            print("  3) complex - Domain-separated flows")
            
            choice = input("Choose pattern (1/2/3): ").strip()
            pattern_map = {'1': 'simple', '2': 'standard', '3': 'complex'}
            return pattern_map.get(choice, 'standard')
    
    async def assess_complexity_automated(self, site_url: str) -> str:
        """
        Automated complexity assessment by analyzing site.
        
        Args:
            site_url: URL of the site to analyze
            
        Returns:
            Recommended pattern (simple, standard, complex)
        """
        print(f"\n🔍 Analyzing site: {site_url}")
        print("This may take a moment...\n")
        
        try:
            # This would use Playwright to analyze the site
            # For now, implement a basic heuristic analysis
            
            analysis_results = {
                'javascript_usage': 0,
                'dynamic_content': 0,
                'authentication_required': 0,
                'real_time_features': 0,
                'filtering_complexity': 0,
                'navigation_complexity': 0
            }
            
            # Simulate site analysis (in real implementation, this would use Playwright)
            # For demonstration, we'll use URL-based heuristics
            
            # Check for common SPA indicators in URL
            spa_indicators = ['app.', 'spa.', '#/', 'react', 'angular', 'vue']
            for indicator in spa_indicators:
                if indicator in site_url.lower():
                    analysis_results['javascript_usage'] += 2
                    analysis_results['dynamic_content'] += 2
                    analysis_results['navigation_complexity'] += 2
            
            # Check for common dynamic site indicators
            dynamic_indicators = ['api.', 'json', 'ajax', 'dynamic']
            for indicator in dynamic_indicators:
                if indicator in site_url.lower():
                    analysis_results['dynamic_content'] += 1
                    analysis_results['javascript_usage'] += 1
            
            # Check for authentication indicators
            auth_indicators = ['login', 'account', 'auth', 'secure']
            for indicator in auth_indicators:
                if indicator in site_url.lower():
                    analysis_results['authentication_required'] += 2
            
            # Check for real-time indicators
            realtime_indicators = ['live', 'real-time', 'stream', 'websocket']
            for indicator in realtime_indicators:
                if indicator in site_url.lower():
                    analysis_results['real_time_features'] += 3
                    analysis_results['dynamic_content'] += 1
            
            # Check for filtering complexity
            filter_indicators = ['search', 'filter', 'category', 'browse']
            for indicator in filter_indicators:
                if indicator in site_url.lower():
                    analysis_results['filtering_complexity'] += 1
            
            # Calculate complexity score
            complexity_score = (
                analysis_results['javascript_usage'] * 2 +
                analysis_results['dynamic_content'] * 2 +
                analysis_results['authentication_required'] * 2 +
                analysis_results['real_time_features'] * 3 +
                analysis_results['filtering_complexity'] * 1 +
                analysis_results['navigation_complexity'] * 1
            )
            
            # Determine recommendation based on score
            if complexity_score <= 4:
                recommended = 'simple'
            elif complexity_score <= 12:
                recommended = 'standard'
            else:
                recommended = 'complex'
            
            # Display analysis results
            print("📊 Site Analysis Results:")
            print(f"- JavaScript usage: {'High' if analysis_results['javascript_usage'] >= 2 else 'Low'}")
            print(f"- Dynamic content: {'Yes' if analysis_results['dynamic_content'] >= 1 else 'No'}")
            print(f"- Authentication required: {'Yes' if analysis_results['authentication_required'] >= 1 else 'No'}")
            print(f"- Real-time features: {'Yes' if analysis_results['real_time_features'] >= 1 else 'No'}")
            print(f"- Filtering complexity: {'High' if analysis_results['filtering_complexity'] >= 2 else 'Low'}")
            print(f"- Navigation complexity: {'High' if analysis_results['navigation_complexity'] >= 2 else 'Low'}")
            print(f"\n📈 Complexity Score: {complexity_score}/24")
            print(f"🎯 Recommended Pattern: {recommended.upper()}")
            
            return recommended
            
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            print("Falling back to interactive assessment...")
            return await self.assess_complexity_interactive()
    
    async def analyze_site_with_playwright(self, site_url: str) -> dict:
        """
        Analyze site using Playwright for accurate complexity assessment.
        
        Args:
            site_url: URL of the site to analyze
            
        Returns:
            Analysis results dictionary
        """
        # This would be implemented with actual Playwright automation
        # For now, return placeholder results
        
        from playwright.async_api import async_playwright
        
        analysis_results = {
            'javascript_usage': 0,
            'dynamic_content': 0,
            'authentication_required': 0,
            'real_time_features': 0,
            'filtering_complexity': 0,
            'navigation_complexity': 0,
            'page_load_time': 0,
            'element_count': 0,
            'form_count': 0,
            'link_count': 0
        }
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            try:
                # Navigate to site
                start_time = time.time()
                await page.goto(site_url, wait_until='networkidle')
                page_load_time = time.time() - start_time
                
                # Analyze page content
                content = await page.content()
                
                # Check for JavaScript usage
                if 'script' in content.lower():
                    analysis_results['javascript_usage'] = len(await page.query_selector_all('script'))
                
                # Check for dynamic content indicators
                dynamic_indicators = [
                    'data-react', 'data-vue', 'ng-app', 'spa', 'ajax'
                ]
                for indicator in dynamic_indicators:
                    if indicator in content.lower():
                        analysis_results['dynamic_content'] += 1
                
                # Check for authentication forms
                forms = await page.query_selector_all('form')
                analysis_results['form_count'] = len(forms)
                
                for form in forms:
                    if await form.query_selector('input[type="password"]'):
                        analysis_results['authentication_required'] += 2
                        break
                
                # Check for real-time features
                realtime_indicators = [
                    'websocket', 'sse', 'live', 'real-time', 'stream'
                ]
                for indicator in realtime_indicators:
                    if indicator in content.lower():
                        analysis_results['real_time_features'] += 2
                
                # Check for filtering complexity
                search_forms = await page.query_selector_all('input[type="search"], input[placeholder*="search"]')
                select_elements = await page.query_selector_all('select')
                analysis_results['filtering_complexity'] = len(search_forms) + len(select_elements)
                
                # Check for navigation complexity
                nav_elements = await page.query_selector_all('nav, .nav, .navigation, .menu')
                links = await page.query_selector_all('a')
                analysis_results['navigation_complexity'] = len(nav_elements)
                analysis_results['link_count'] = len(links)
                
                # Count total elements
                all_elements = await page.query_selector_all('*')
                analysis_results['element_count'] = len(all_elements)
                
                analysis_results['page_load_time'] = page_load_time
                
            except Exception as e:
                print(f"Page analysis error: {e}")
            finally:
                await browser.close()
        
        return analysis_results
    
    async def customize_domains_interactive(self) -> Dict[str, Any]:
        """
        Interactive domain customization for complex pattern.
        
        Returns:
            Dictionary with domain customization options
        """
        print("\n" + "="*60)
        print("🎛️ DOMAIN CUSTOMIZATION")
        print("="*60)
        print("Customize which domains to include in your complex pattern setup.\n")
        
        # Available domains
        available_domains = {
            'navigation': {
                'description': 'Page navigation and movement through websites',
                'flows': ['match_nav', 'live_nav', 'competition_nav'],
                'required': True
            },
            'extraction': {
                'description': 'Data extraction and content processing',
                'flows': ['match_extract', 'odds_extract', 'stats_extract'],
                'required': True
            },
            'filtering': {
                'description': 'Content filtering and search refinement',
                'flows': ['date_filter', 'sport_filter', 'competition_filter'],
                'required': False
            },
            'authentication': {
                'description': 'User authentication and session management',
                'flows': ['login_flow', 'oauth_flow'],
                'required': False
            }
        }
        
        selected_domains = {}
        exclude_domains = []
        
        print("Available domains:")
        for domain_name, domain_info in available_domains.items():
            required = " (Required)" if domain_info['required'] else " (Optional)"
            print(f"  {domain_name}: {domain_info['description']}{required}")
        
        print("\nSelect domains to include (comma-separated):")
        print("Example: navigation,extraction,filtering")
        
        domain_input = input("Domains: ").strip().lower()
        
        if domain_input:
            selected_domain_names = [d.strip() for d in domain_input.split(',')]
            
            for domain_name in selected_domain_names:
                if domain_name in available_domains:
                    selected_domains[domain_name] = available_domains[domain_name]
                else:
                    print(f"⚠️ Unknown domain: {domain_name}")
        
        # Ask for exclusions
        print("\nDomains to exclude (comma-separated, or 'none'):")
        exclude_input = input("Exclude domains: ").strip().lower()
        
        if exclude_input and exclude_input != 'none':
            exclude_domain_names = [d.strip() for d in exclude_input.split(',')]
            for domain_name in exclude_domain_names:
                if domain_name in available_domains:
                    exclude_domains.append(domain_name)
                else:
                    print(f"⚠️ Unknown domain: {domain_name}")
        
        # Validate required domains
        for domain_name, domain_info in available_domains.items():
            if domain_info['required'] and domain_name not in selected_domains:
                if domain_name not in exclude_domains:
                    print(f"⚠️ Required domain {domain_name} not selected, adding automatically")
                    selected_domains[domain_name] = domain_info
        
        # Ask for custom flows
        print("\nCustom flows to include (comma-separated, or 'none'):")
        custom_input = input("Custom flows: ").strip()
        
        custom_flows = []
        if custom_input and custom_input != 'none':
            custom_flows = [f.strip() for f in custom_input.split(',')]
        
        return {
            'domains': list(selected_domains.keys()),
            'exclude_domains': exclude_domains,
            'custom_flows': custom_flows,
            'domain_details': selected_domains
        }
    
    async def customize_flows_interactive(self, domains: Dict[str, Any]) -> List[str]:
        """
        Interactive flow customization for selected domains.
        
        Args:
            domains: Selected domains information
            
        Returns:
            List of flows to include
        """
        selected_flows = []
        
        print("\n" + "="*60)
        print("🔧 FLOW CUSTOMIZATION")
        print("="*60)
        print("Select specific flows to include for each domain.\n")
        
        for domain_name, domain_info in domains.items():
            print(f"\n📁 {domain_name.upper()} DOMAIN:")
            print(f"Description: {domain_info['description']}")
            print(f"Available flows: {', '.join(domain_info['flows'])}")
            
            flow_input = input(f"Select flows for {domain_name} (comma-separated, or 'all'): ").strip()
            
            if flow_input.lower() == 'all':
                selected_flows.extend(domain_info['flows'])
            elif flow_input:
                selected_flow_names = [f.strip() for f in flow_input.split(',')]
                for flow_name in selected_flow_names:
                    if flow_name in domain_info['flows']:
                        selected_flows.append(flow_name)
                    else:
                        print(f"⚠️ Unknown flow: {flow_name}")
        
        return selected_flows
    
    def validate_domain_selection(self, domains: List[str], exclude_domains: List[str]) -> Dict[str, Any]:
        """
        Validate domain selection and return validation results.
        
        Args:
            domains: List of selected domains
            exclude_domains: List of excluded domains
            
        Returns:
            Validation results
        """
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        # Required domains
        required_domains = ['navigation', 'extraction']
        
        # Check if required domains are excluded
        for required_domain in required_domains:
            if required_domain in exclude_domains:
                validation_result['valid'] = False
                validation_result['errors'].append(
                    f"Required domain '{required_domain}' cannot be excluded"
                )
        
        # Check if required domains are missing
        for required_domain in required_domains:
            if required_domain not in domains and required_domain not in exclude_domains:
                validation_result['warnings'].append(
                    f"Required domain '{required_domain}' will be included automatically"
                )
        
        return validation_result
    
    def validate_pattern_selection(self, pattern: str, domains: List[str], site_url: str = None) -> Dict[str, Any]:
        """
        Validate pattern selection to prevent anti-patterns.
        
        Args:
            pattern: Selected pattern (simple, standard, complex)
            domains: List of selected domains (for complex pattern)
            site_url: Optional site URL for analysis
            
        Returns:
            Validation results with warnings and errors
        """
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        # Anti-pattern 1: Complex pattern without required domains
        if pattern == 'complex':
            required_domains = ['navigation', 'extraction']
            missing_required = [d for d in required_domains if d not in domains]
            
            if missing_required:
                validation_result['valid'] = False
                validation_result['errors'].append(
                    f"Complex pattern requires domains: {', '.join(missing_required)}"
                )
        
        # Anti-pattern 2: Simple pattern with complex features requested
        if pattern == 'simple' and site_url:
            complex_indicators = ['api', 'spa', 'dynamic', 'real-time', 'live']
            for indicator in complex_indicators:
                if indicator in site_url.lower():
                    validation_result['warnings'].append(
                        f"Site appears complex but simple pattern selected. Consider standard or complex pattern."
                    )
                    validation_result['recommendations'].append(
                        "Consider using standard pattern for dynamic content"
                    )
                    break
        
        # Anti-pattern 3: Standard pattern with minimal flows needed
        if pattern == 'standard':
            # Check if user might be better with simple pattern
            simple_indicators = ['static', 'basic', 'simple', 'blog', 'portfolio']
            if site_url:
                for indicator in simple_indicators:
                    if indicator in site_url.lower():
                        validation_result['recommendations'].append(
                            "Site appears simple - consider using simple pattern for better maintainability"
                        )
                        break
        
        # Anti-pattern 4: Complex pattern with too few domains
        if pattern == 'complex' and len(domains) < 2:
            validation_result['warnings'].append(
                f"Complex pattern with only {len(domains)} domains may be overkill. Consider standard pattern."
            )
        
        # Anti-pattern 5: Domain exclusion conflicts
        if pattern == 'complex':
            excluded_domains = ['navigation', 'extraction']  # These should never be excluded
            conflicts = [d for d in excluded_domains if d in domains]
            
            if conflicts:
                validation_result['valid'] = False
                validation_result['errors'].append(
                    f"Cannot exclude required domains: {', '.join(conflicts)}"
                )
        
        # Anti-pattern 6: Pattern mismatch with site characteristics
        if site_url:
            # Check for SPA indicators with simple pattern
            if pattern == 'simple':
                spa_indicators = ['react', 'angular', 'vue', 'spa', 'app.']
                for indicator in spa_indicators:
                    if indicator in site_url.lower():
                        validation_result['warnings'].append(
                            f"SPA detected with simple pattern. Consider complex pattern for better structure."
                        )
                        break
            
            # Check for authentication needs with simple pattern
            if pattern == 'simple':
                auth_indicators = ['login', 'account', 'auth', 'secure']
                for indicator in auth_indicators:
                    if indicator in site_url.lower():
                        validation_result['recommendations'].append(
                            "Authentication detected - consider standard pattern for login flows"
                        )
                        break
        
        return validation_result
    
    def validate_domain_configuration(self, domains: Dict[str, Any], custom_flows: List[str]) -> Dict[str, Any]:
        """
        Validate domain configuration for complex pattern.
        
        Args:
            domains: Selected domains with their details
            custom_flows: List of custom flows
            
        Returns:
            Validation results
        """
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        # Check for domain conflicts
        domain_names = list(domains.keys())
        if 'navigation' in domain_names and 'extraction' not in domain_names:
            validation_result['warnings'].append(
                "Navigation domain without extraction domain may limit functionality"
            )
        
        if 'extraction' in domain_names and 'navigation' not in domain_names:
            validation_result['warnings'].append(
                "Extraction domain without navigation domain may limit data access"
            )
        
        # Check for redundant custom flows
        existing_flows = []
        for domain_info in domains.values():
            if 'flows' in domain_info:
                existing_flows.extend(domain_info['flows'])
        
        redundant_flows = [f for f in custom_flows if f in existing_flows]
        if redundant_flows:
            validation_result['warnings'].append(
                f"Custom flows already exist: {', '.join(redundant_flows)}"
            )
        
        # Check for missing authentication with complex sites
        complex_indicators = ['api', 'spa', 'dynamic']
        if any(indicator in str(domains).lower() for indicator in complex_indicators):
            if 'authentication' not in domain_names:
                validation_result['recommendations'].append(
                    "Consider adding authentication domain for complex sites"
                )
        
        return validation_result
    
    def _log(self, message: str, level: str = 'INFO') -> None:
        """Log setup message."""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {level}: {message}"
        self.setup_log.append(log_entry)
        print(log_entry)


async def create_site(
    site_name: str,
    site_id: str = None,
    site_url: str = None,
    target_dir: str = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a new site scraper from the template.
    
    Args:
        site_name: Name of the new site
        site_id: Site ID (defaults to sanitized site_name)
        site_url: Base URL of the site
        target_dir: Target directory
        **kwargs: Additional configuration options
        
    Returns:
        Setup results
    """
    setup = TemplateSetup()
    return await setup.setup_new_site(site_name, site_id, site_url, target_dir, kwargs)


def main():
    """Main setup script entry point."""
    parser = argparse.ArgumentParser(
        description='Setup new site scraper from template',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup.py mysite
  python setup.py mysite --site-id my_site --site-url https://example.com
  python setup.py mysite --pattern complex
  python setup.py mysite --interactive
  python setup.py mysite --assess-complexity https://example.com
        """
    )
    
    parser.add_argument(
        'site_name',
        help='Name of the site to create'
    )
    
    parser.add_argument(
        '--site-id',
        help='Site ID (defaults to sanitized site name)'
    )
    
    parser.add_argument(
        '--site-url',
        help='Base URL of the site'
    )
    
    parser.add_argument(
        '--target-dir',
        help='Target directory (defaults to src/sites/{site_name})'
    )
    
    parser.add_argument(
        '--pattern',
        choices=['simple', 'standard', 'complex'],
        help='Architectural pattern to use'
    )
    
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run interactive complexity assessment'
    )
    
    parser.add_argument(
        '--assess-complexity',
        metavar='URL',
        help='Assess site complexity and recommend pattern'
    )
    
    parser.add_argument(
        '--domains',
        help='Comma-separated list of domains to include (for complex pattern)'
    )
    
    parser.add_argument(
        '--exclude-domains',
        help='Comma-separated list of domains to exclude (for complex pattern)'
    )
    
    parser.add_argument(
        '--custom-flows',
        help='Comma-separated list of custom flows to include'
    )
    
    parser.add_argument(
        '--config',
        help='JSON configuration file'
    )
    
    args = parser.parse_args()
    
    # Handle complexity assessment mode
    if args.assess_complexity:
        asyncio.run(assess_site_complexity(args.assess_complexity))
        return
    
    # Load configuration
    config = {}
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Set up configuration from arguments
    if args.site_id:
        config['site_id'] = args.site_id
    
    if args.site_url:
        config['site_url'] = args.site_url
    
    if args.target_dir:
        config['target_dir'] = args.target_dir
    
    if args.pattern:
        config['pattern'] = args.pattern
    
    if args.interactive:
        config['interactive_mode'] = True
    
    if args.domains:
        config['domains'] = [d.strip() for d in args.domains.split(',')]
    
    if args.exclude_domains:
        config['exclude_domains'] = [d.strip() for d in args.exclude_domains.split(',')]
    
    if args.custom_flows:
        config['custom_flows'] = [f.strip() for f in args.custom_flows.split(',')]
    
    # Run setup
    asyncio.run(setup_site(args.site_name, config))


async def assess_site_complexity(site_url: str):
    """Assess site complexity and recommend pattern."""
    setup = TemplateSetup()
    
    print(f"🔍 Assessing site complexity for: {site_url}")
    
    # Try automated assessment first
    try:
        recommended = await setup.assess_complexity_automated(site_url)
        print(f"\n✅ Automated assessment completed")
        print(f"Recommended pattern: {recommended}")
        
        confirm = input("\nRun interactive assessment for more detailed analysis? (Y/N): ").upper().strip()
        if confirm == 'Y':
            recommended = await setup.assess_complexity_interactive(site_url)
    except Exception as e:
        print(f"❌ Automated assessment failed: {e}")
        print("Falling back to interactive assessment...")
        recommended = await setup.assess_complexity_interactive(site_url)
    
    print(f"\n🎯 Final recommendation: {recommended}")
    print(f"\nTo create site with this pattern, run:")
    print(f"python setup.py your_site_name --pattern {recommended} --site-url {site_url}")


async def setup_site(site_name: str, config: Dict[str, Any]):
    """Set up a new site with the given configuration."""
    setup = TemplateSetup()
    result = await setup.setup_new_site(site_name, config=config)
    
    if result['success']:
        print(f"\n✅ Site '{site_name}' created successfully!")
        print(f"📁 Location: {result['target_dir']}")
        print(f"🏗️  Pattern: {result.get('pattern', 'standard')}")
        
        if result.get('next_steps'):
            print(f"\n📋 Next Steps:")
            for step in result['next_steps']:
                print(f"  • {step}")
    else:
        print(f"\n❌ Setup failed: {result.get('error', 'Unknown error')}")
        if result.get('validation_errors'):
            print("\nValidation errors:")
            for error in result['validation_errors']:
                print(f"  • {error}")
        
        sys.exit(1)


if __name__ == '__main__':
    main()
