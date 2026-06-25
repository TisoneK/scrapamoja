"""
Unit tests for template framework core components.

This module provides comprehensive unit tests for the template framework,
including base classes, integration bridges, and utility functions.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile
import json

from src.sites.base.template.site_template import BaseSiteTemplate
from src.sites.base.template.integration_bridge import FullIntegrationBridge, BaseIntegrationBridge
from src.sites.base.template.selector_loader import FileSystemSelectorLoader
from src.sites.base.template.validation import YAMLSelectorValidator, ExtractionRuleValidator
from src.sites.base.template.site_registry import BaseSiteRegistry
from src.sites.base.template.error_handling import TemplateError, TemplateValidationError


class TestBaseSiteTemplate:
    """Test cases for BaseSiteTemplate."""
    
    @pytest.fixture
    def mock_page(self):
        """Create mock Playwright page."""
        page = Mock()
        page.url = "https://example.com"
        return page
    
    @pytest.fixture
    def mock_selector_engine(self):
        """Create mock selector engine."""
        engine = Mock()
        engine.register_selector = Mock()
        engine.find_all = AsyncMock(return_value=[])
        engine.validate_selector = Mock(return_value=True)
        engine.get_confidence_score = Mock(return_value=0.8)
        return engine
    
    @pytest.fixture
    def base_template(self, mock_page, mock_selector_engine):
        """Create BaseSiteTemplate instance."""
        return BaseSiteTemplate(
            name="test_template",
            version="1.0.0",
            description="Test template",
            author="Test Author",
            framework_version="1.0.0",
            site_domain="example.com"
        )
    
    def test_template_initialization(self, base_template):
        """Test template initialization."""
        assert base_template.name == "test_template"
        assert base_template.version == "1.0.0"
        assert base_template.description == "Test template"
        assert base_template.author == "Test Author"
        assert base_template.framework_version == "1.0.0"
        assert base_template.site_domain == "example.com"
        assert base_template.supported_domains == []
        assert base_template.capabilities == []
        assert base_template.dependencies == []
    
    def test_template_info(self, base_template):
        """Test template info retrieval."""
        info = base_template.get_template_info()
        
        assert info["name"] == "test_template"
        assert info["version"] == "1.0.0"
        assert info["description"] == "Test template"
        assert info["author"] == "Test Author"
        assert info["framework_version"] == "1.0.0"
        assert info["site_domain"] == "example.com"
        assert info["initialized"] is False
        assert "capabilities" in info
        assert "dependencies" in info
    
    def test_capabilities_addition(self, base_template):
        """Test adding capabilities."""
        base_template.capabilities = ["scraping", "extraction"]
        
        info = base_template.get_template_info()
        assert "scraping" in info["capabilities"]
        assert "extraction" in info["capabilities"]
    
    def test_dependencies_addition(self, base_template):
        """Test adding dependencies."""
        base_template.dependencies = ["selector_engine", "extractor"]
        
        info = base_template.get_template_info()
        assert "selector_engine" in info["dependencies"]
        assert "extractor" in info["dependencies"]
    
    @pytest.mark.asyncio
    async def test_health_check_uninitialized(self, base_template):
        """Test health check for uninitialized template."""
        health = await base_template.health_check()
        
        assert health["template_name"] == "test_template"
        assert health["template_version"] == "1.0.0"
        assert health["initialized"] is False
        assert "overall_health" in health
        assert "components" in health
    
    @pytest.mark.asyncio
    async def test_scrape_uninitialized(self, base_template):
        """Test scraping with uninitialized template."""
        with pytest.raises(TemplateError):
            await base_template.scrape("test_action")
    
    def test_performance_metrics(self, base_template):
        """Test performance metrics tracking."""
        metrics = base_template.get_performance_metrics()
        
        assert "scrape_count" in metrics
        assert "total_scrape_time" in metrics
        assert "average_scrape_time" in metrics
        assert "error_count" in metrics
        assert "success_count" in metrics
        assert "success_rate" in metrics


class TestIntegrationBridge:
    """Test cases for integration bridge."""
    
    @pytest.fixture
    def mock_selector_engine(self):
        """Create mock selector engine."""
        engine = Mock()
        engine.register_selector = Mock()
        engine.find_all = AsyncMock(return_value=[])
        engine.validate_selector = Mock(return_value=True)
        engine.get_confidence_score = Mock(return_value=0.8)
        return engine
    
    @pytest.fixture
    def mock_page(self):
        """Create mock Playwright page."""
        page = Mock()
        page.url = "https://example.com"
        return page
    
    @pytest.fixture
    def integration_bridge(self, mock_selector_engine, mock_page):
        """Create integration bridge."""
        return FullIntegrationBridge(
            template_name="test_template",
            selector_engine=mock_selector_engine,
            page=mock_page
        )
    
    @pytest.mark.asyncio
    async def test_bridge_initialization(self, integration_bridge):
        """Test bridge initialization."""
        result = await integration_bridge.initialize()
        
        assert result is True
        assert integration_bridge.initialized is True
        assert integration_bridge.template_name == "test_template"
    
    def test_component_availability_check(self, integration_bridge):
        """Test component availability checking."""
        # Test with available component
        assert integration_bridge.is_component_available("selector_engine") is True
        
        # Test with unavailable component
        assert integration_bridge.is_component_available("nonexistent") is False
    
    @pytest.mark.asyncio
    async def test_available_components(self, integration_bridge):
        """Test getting available components."""
        await integration_bridge.initialize()
        
        components = integration_bridge.get_available_components()
        
        assert "selector_engine" in components
        assert isinstance(components, dict)
    
    def test_bridge_status(self, integration_bridge):
        """Test bridge status reporting."""
        status = integration_bridge.get_integration_status()
        
        assert "template_name" in status
        assert status["template_name"] == "test_template"
        assert "is_integrated" in status
        assert "components" in status


class TestFileSystemSelectorLoader:
    """Test cases for FileSystemSelectorLoader."""
    
    @pytest.fixture
    def mock_selector_engine(self):
        """Create mock selector engine."""
        engine = Mock()
        engine.register_selector = Mock()
        engine.find_all = AsyncMock(return_value=[])
        engine.validate_selector = Mock(return_value=True)
        engine.get_confidence_score = Mock(return_value=0.8)
        return engine
    
    @pytest.fixture
    def temp_selectors_dir(self):
        """Create temporary selectors directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test YAML selector file
            selector_file = Path(temp_dir) / "test_selector.yaml"
            selector_file.write_text("""
name: test_selector
description: Test selector
selector: .test-class
strategies:
  - name: css
    type: css
    priority: 1
    confidence: 0.9
validation:
  required: true
  exists: true
""")
            yield temp_dir
    
    @pytest.fixture
    def selector_loader(self, mock_selector_engine, temp_selectors_dir):
        """Create selector loader."""
        return FileSystemSelectorLoader(
            template_name="test_template",
            selector_engine=mock_selector_engine,
            selectors_directory=temp_selectors_dir
        )
    
    @pytest.mark.asyncio
    async def test_selector_loading(self, selector_loader):
        """Test selector loading."""
        result = await selector_loader.load_selectors()
        
        assert result is True
        assert len(selector_loader.loaded_selectors) > 0
        assert "test_selector" in selector_loader.loaded_selectors
    
    def test_get_selector(self, selector_loader):
        """Test getting loaded selector."""
        # Mock loaded selectors
        selector_loader.loaded_selectors = {
            "test_selector": {
                "name": "test_selector",
                "selector": ".test-class"
            }
        }
        
        selector = selector_loader.get_selector("test_selector")
        assert selector is not None
        assert selector["name"] == "test_selector"
    
    def test_get_nonexistent_selector(self, selector_loader):
        """Test getting nonexistent selector."""
        selector = selector_loader.get_selector("nonexistent")
        assert selector is None


class TestYAMLSelectorValidator:
    """Test cases for YAML selector validator."""
    
    @pytest.fixture
    def validator(self):
        """Create YAML selector validator."""
        return YAMLSelectorValidator()
    
    @pytest.fixture
    def valid_selector_file(self):
        """Create valid selector file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
name: test_selector
description: Test selector
selector: .test-class
strategies:
  - name: css
    type: css
    priority: 1
    confidence: 0.9
validation:
  required: true
  exists: true
""")
            return Path(f.name)
    
    @pytest.fixture
    def invalid_selector_file(self):
        """Create invalid selector file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
name: test_selector
# Missing required fields
""")
            return Path(f.name)
    
    @pytest.mark.asyncio
    async def test_valid_selector_validation(self, validator, valid_selector_file):
        """Test validation of valid selector file."""
        result = await validator.validate_selector_file(valid_selector_file)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["selector_name"] == "test_selector"
        assert result["strategies_count"] == 1
    
    @pytest.mark.asyncio
    async def test_invalid_selector_validation(self, validator, invalid_selector_file):
        """Test validation of invalid selector file."""
        result = await validator.validate_selector_file(invalid_selector_file)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_nonexistent_file_validation(self, validator):
        """Test validation of nonexistent file."""
        result = await validator.validate_selector_file("nonexistent.yaml")
        
        assert result["valid"] is False
        assert "File not found" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_selector_directory_validation(self, validator, valid_selector_file):
        """Test validation of selector directory."""
        # Create directory with valid selector
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy valid selector to temp directory
            import shutil
            temp_selector = Path(temp_dir) / "test_selector.yaml"
            shutil.copy2(valid_selector_file, temp_selector)
            
            result = await validator.validate_selector_directory(temp_dir)
            
            assert result["valid"] is True
            assert result["file_count"] == 1
            assert result["valid_files"] == 1


class TestExtractionRuleValidator:
    """Test cases for extraction rule validator."""
    
    @pytest.fixture
    def validator(self):
        """Create extraction rule validator."""
        return ExtractionRuleValidator()
    
    @pytest.fixture
    def valid_extraction_rule(self):
        """Create valid extraction rule."""
        return {
            "name": "test_rule",
            "description": "Test extraction rule",
            "selector": ".test-element",
            "extraction_type": "text",
            "transformations": [
                {
                    "type": "trim",
                    "parameters": {}
                }
            ],
            "required": True,
            "multi_value": False
        }
    
    @pytest.fixture
    def invalid_extraction_rule(self):
        """Create invalid extraction rule."""
        return {
            "name": "test_rule",
            # Missing required fields
            "description": "Test extraction rule"
        }
    
    @pytest.mark.asyncio
    async def test_valid_rule_validation(self, validator, valid_extraction_rule):
        """Test validation of valid extraction rule."""
        result = await validator.validate_extraction_rule(valid_extraction_rule)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["rule_name"] == "test_rule"
        assert result["extraction_type"] == "text"
    
    @pytest.mark.asyncio
    async def test_invalid_rule_validation(self, validator, invalid_extraction_rule):
        """Test validation of invalid extraction rule."""
        result = await validator.validate_extraction_rule(invalid_extraction_rule)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0


class TestSiteRegistry:
    """Test cases for site registry."""
    
    @pytest.fixture
    def registry(self):
        """Create site registry."""
        return BaseSiteRegistry()
    
    @pytest.mark.asyncio
    async def test_registry_initialization(self, registry):
        """Test registry initialization."""
        result = await registry.initialize()
        
        assert result is True
        assert registry.status.value == "active"
    
    @pytest.mark.asyncio
    async def test_template_registration(self, registry):
        """Test template registration."""
        template_metadata = {
            "name": "test_template",
            "version": "1.0.0",
            "description": "Test template",
            "template_path": "src/sites/test",
            "module_path": "src/sites/test/scraper.py"
        }
        
        result = await registry.register_template(template_metadata)
        
        assert result is True
        assert "test_template" in registry.templates
    
    @pytest.mark.asyncio
    async def test_template_unregistration(self, registry):
        """Test template unregistration."""
        # First register a template
        template_metadata = {
            "name": "test_template",
            "version": "1.0.0",
            "description": "Test template",
            "template_path": "src/sites/test",
            "module_path": "src/sites/test/scraper.py"
        }
        await registry.register_template(template_metadata)
        
        # Then unregister it
        result = await registry.unregister_template("test_template")
        
        assert result is True
        assert "test_template" not in registry.templates
    
    @pytest.mark.asyncio
    async def test_template_unregistration_nonexistent(self, registry):
        """Test unregistration of nonexistent template."""
        result = await registry.unregister_template("nonexistent")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_template(self, registry):
        """Test getting template."""
        # Register a template first
        template_metadata = {
            "name": "test_template",
            "version": "1.0.0",
            "description": "Test template",
            "template_path": "src/sites/test",
            "module_path": "src/sites/test/scraper.py"
        }
        await registry.register_template(template_metadata)
        
        # Get the template
        template = await registry.get_template("test_template")
        
        assert template is not None
        assert template["name"] == "test_template"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_template(self, registry):
        """Test getting nonexistent template."""
        template = await registry.get_template("nonexistent")
        
        assert template is None
    
    @pytest.mark.asyncio
    async def test_list_templates(self, registry):
        """Test listing templates."""
        # Register some templates
        templates = [
            {
                "name": "template1",
                "version": "1.0.0",
                "description": "Template 1",
                "template_path": "src/sites/template1",
                "module_path": "src/sites/template1/scraper.py"
            },
            {
                "name": "template2",
                "version": "1.0.0",
                "description": "Template 2",
                "template_path": "src/sites/template2",
                "module_path": "src/sites/template2/scraper.py"
            }
        ]
        
        for template in templates:
            await registry.register_template(template)
        
        # List all templates
        all_templates = await registry.list_templates()
        assert len(all_templates) == 2
        
        # Filter templates
        filtered_templates = await registry.list_templates({"name": "template1"})
        assert len(filtered_templates) == 1
        assert filtered_templates[0]["name"] == "template1"
    
    @pytest.mark.asyncio
    async def test_search_templates(self, registry):
        """Test template search."""
        # Register templates
        templates = [
            {
                "name": "github",
                "version": "1.0.0",
                "description": "GitHub scraper",
                "template_path": "src/sites/github",
                "module_path": "src/sites/github/scraper.py",
                "capabilities": ["repository_search", "user_profile"],
                "site_domain": "github.com"
            },
            {
                "name": "twitter",
                "version": "1.0.0",
                "description": "Twitter scraper",
                "template_path": "src/sites/twitter",
                "module_path": "src/sites/twitter/scraper.py",
                "capabilities": ["tweet_search", "user_profile"],
                "site_domain": "twitter.com"
            }
        ]
        
        for template in templates:
            await registry.register_template(template)
        
        # Search by query
        results = await registry.search_templates(query="github")
        assert len(results) == 1
        assert results[0]["name"] == "github"
        
        # Search by capabilities
        results = await registry.search_templates(capabilities=["user_profile"])
        assert len(results) == 2
        
        # Search by domain
        results = await registry.search_templates(domain="github.com")
        assert len(results) == 1
        assert results[0]["name"] == "github"
    
    @pytest.mark.asyncio
    async def test_registry_health(self, registry):
        """Test registry health status."""
        health = await registry.get_registry_health()
        
        assert "registry_status" in health
        assert "total_templates" in health
        assert "overall_health" in health
        assert health["registry_status"] == "active"


class TestErrorHandling:
    """Test cases for error handling."""
    
    def test_template_error(self):
        """Test TemplateError."""
        error = TemplateError("Test error")
        assert str(error) == "Test error"
    
    def test_template_validation_error(self):
        """Test TemplateValidationError."""
        error = TemplateValidationError("Validation error", details={"field": "test"})
        assert str(error) == "Validation error"
        assert error.details == {"field": "test"}
    
    def test_error_inheritance(self):
        """Test error inheritance."""
        error = TemplateValidationError("Test error")
        assert isinstance(error, TemplateError)
        assert isinstance(error, Exception)


class TestConfiguration:
    """Test cases for configuration management."""
    
    def test_validator_config_update(self):
        """Test validator configuration update."""
        validator = YAMLSelectorValidator()
        
        original_config = validator.get_config()
        assert "strict_mode" in original_config
        
        new_config = {"strict_mode": False, "validate_strategies": False}
        validator.update_config(new_config)
        
        updated_config = validator.get_config()
        assert updated_config["strict_mode"] is False
        assert updated_config["validate_strategies"] is False
    
    def test_registry_config_update(self):
        """Test registry configuration update."""
        registry = BaseSiteRegistry()
        
        original_config = registry.get_config()
        assert "auto_discovery" in original_config
        
        new_config = {"auto_discovery": False, "cache_enabled": False}
        registry.update_config(new_config)
        
        updated_config = registry.get_config()
        assert updated_config["auto_discovery"] is False
        assert updated_config["cache_enabled"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
