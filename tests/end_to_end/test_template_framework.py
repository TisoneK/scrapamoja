"""
End-to-end tests for the Site Template Integration Framework.

This module provides comprehensive end-to-end tests that validate the entire
template framework workflow from template creation to execution.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, MagicMock
import json
import yaml

# Import framework components
from src.sites.base.template.site_template import BaseSiteTemplate
from src.sites.base.template.site_registry import BaseSiteRegistry
from src.sites.base.template.validation import ValidationFramework
from src.sites.base.template.development import TemplateDeveloper, TemplateMetadata
from src.sites.base.template.migration import TemplateUpgrader
from src.sites.base.template.observability import ObservabilityManager


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""
    
    @pytest.fixture
    def temp_template_dir(self):
        """Create temporary template directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_components(self):
        """Create mock framework components."""
        page = Mock()
        page.url = "https://example.com"
        page.goto = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.query_selector = AsyncMock()
        page.click = AsyncMock()
        page.fill = AsyncMock()
        page.text_content = AsyncMock(return_value="Test Content")
        page.get_attribute = AsyncMock(return_value="test-value")
        
        selector_engine = Mock()
        selector_engine.find = AsyncMock(return_value=Mock())
        selector_engine.find_all = AsyncMock(return_value=[Mock(), Mock()])
        selector_engine.find_first = AsyncMock(return_value=Mock())
        selector_engine.register_selector = Mock()
        selector_engine.load_selectors = AsyncMock(return_value=True)
        
        extractor = Mock()
        extractor.extract = AsyncMock(return_value="extracted_value")
        
        return {
            "page": page,
            "selector_engine": selector_engine,
            "extractor": extractor
        }
    
    @pytest.mark.asyncio
    async def test_complete_template_creation_workflow(self, temp_template_dir, mock_components):
        """Test complete template creation workflow."""
        # Step 1: Create template metadata
        metadata = TemplateMetadata(
            name="test_site",
            version="1.0.0",
            description="Test site scraper",
            author="Test Author",
            site_domain="testsite.com",
            framework_version="1.0.0",
            capabilities=["scraping", "extraction"],
            dependencies=["selector_engine"],
            tags=["test", "scraping"]
        )
        
        # Step 2: Create template using developer tools
        developer = TemplateDeveloper()
        result = developer.create_template(
            "test_site", metadata, output_dir=temp_template_dir.parent
        )
        
        assert result["success"], f"Template creation failed: {result.get('error')}"
        assert Path(result["template_path"]).exists()
        
        # Step 3: Validate created template
        validation_result = result["validation"]
        assert validation_result["valid"], f"Template validation failed: {validation_result['errors']}"
        
        # Step 4: Test template initialization
        template_path = Path(result["template_path"])
        scraper_module = self._load_scraper_module(template_path)
        
        # Create scraper instance
        scraper = scraper_module.TestSiteScraper(
            mock_components["page"],
            mock_components["selector_engine"]
        )
        
        # Initialize scraper
        init_result = await scraper.initialize()
        assert init_result, "Scraper initialization failed"
        
        # Step 5: Test template execution
        scrape_result = await scraper.scrape("scrape_main_content", limit=5)
        assert scrape_result["success"], f"Scraping failed: {scrape_result.get('error')}"
        assert scrape_result["action"] == "scrape_main_content"
        
        # Step 6: Test health check
        health_result = await scraper.health_check()
        assert health_result["overall_health"] in ["healthy", "degraded"]
        
        # Step 7: Test performance metrics
        metrics = scraper.get_performance_metrics()
        assert "scrape_count" in metrics
        assert "success_rate" in metrics
    
    def _load_scraper_module(self, template_path: Path):
        """Load scraper module from template path."""
        import importlib.util
        import sys
        
        scraper_file = template_path / "scraper.py"
        if not scraper_file.exists():
            # Create a simple test scraper for testing
            self._create_test_scraper(template_path)
        
        spec = importlib.util.spec_from_file_location("test_scraper", scraper_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules["test_scraper"] = module
        spec.loader.exec_module(module)
        
        return module
    
    def _create_test_scraper(self, template_path: Path):
        """Create a test scraper for testing purposes."""
        scraper_content = '''
import logging
from src.sites.base.template import BaseSiteTemplate

logger = logging.getLogger(__name__)

class TestSiteScraper(BaseSiteTemplate):
    """Test site scraper for end-to-end testing."""
    
    def __init__(self, page, selector_engine):
        super().__init__(
            name="test_site",
            version="1.0.0",
            description="Test site scraper",
            author="Test Author",
            framework_version="1.0.0",
            site_domain="testsite.com"
        )
        
        self.capabilities = ["scraping", "extraction"]
        self.supported_domains = ["testsite.com"]
    
    async def _execute_scrape_logic(self, action: str, **kwargs):
        if action == "scrape_main_content":
            return await self._scrape_main_content(**kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _scrape_main_content(self, limit: int = 10):
        return {
            "action": "scrape_main_content",
            "success": True,
            "data": {"content": "test content"},
            "limit": limit
        }
'''
        (template_path / "scraper.py").write_text(scraper_content)
    
    @pytest.mark.asyncio
    async def test_template_registry_workflow(self, temp_template_dir, mock_components):
        """Test template registry workflow."""
        # Create a test template
        registry = BaseSiteRegistry()
        
        # Step 1: Register template
        template_path = temp_template_dir / "test_template"
        template_path.mkdir()
        
        # Create minimal template structure
        (template_path / "__init__.py").write_text("")
        (template_path / "scraper.py").write_text("""
from src.sites.base.template import BaseSiteTemplate

class TestTemplate(BaseSiteTemplate):
    def __init__(self, page, selector_engine):
        super().__init__("test", "1.0.0", "Test", "Test", "1.0.0", "test.com")
    
    async def _execute_scrape_logic(self, action, **kwargs):
        return {"action": action, "success": True}
""")
        
        (template_path / "metadata.json").write_text(json.dumps({
            "name": "test",
            "version": "1.0.0",
            "description": "Test template",
            "author": "Test",
            "site_domain": "test.com",
            "framework_version": "1.0.0",
            "capabilities": ["scraping"],
            "dependencies": [],
            "tags": ["test"]
        }))
        
        # Step 2: Discover templates
        discovered = await registry.discover_templates([str(temp_template_dir)])
        assert len(discovered) >= 1
        
        # Step 3: Load template
        scraper = await registry.load_template(
            template_name="test",
            page=mock_components["page"],
            selector_engine=mock_components["selector_engine"]
        )
        
        assert scraper is not None
        assert scraper.name == "test"
        
        # Step 4: Test template execution
        result = await scraper.scrape("test_action")
        assert result["success"]
    
    @pytest.mark.asyncio
    async def test_validation_framework_workflow(self, temp_template_dir):
        """Test validation framework workflow."""
        # Create test template
        template_path = temp_template_dir / "validation_test"
        template_path.mkdir()
        
        # Create template files
        self._create_validation_test_template(template_path)
        
        # Initialize validation framework
        validator = ValidationFramework()
        
        # Step 1: Validate template structure
        structure_result = await validator.validate_template_structure(str(template_path))
        assert structure_result.is_valid
        
        # Step 2: Validate selectors
        selectors_dir = template_path / "selectors"
        if selectors_dir.exists():
            selector_configs = self._load_selector_configs(selectors_dir)
            selector_result = await validator.validate_selectors(selector_configs)
            assert selector_result.is_valid
        
        # Step 3: Check framework compliance
        compliance_result = await validator.check_framework_compliance(str(template_path))
        assert compliance_result.is_compliant
        
        # Step 4: Get validation summary
        summary = await validator.get_validation_summary(str(template_path))
        assert summary["overall_valid"]
        assert summary["compliance_score"] >= 0.8
    
    def _create_validation_test_template(self, template_path: Path):
        """Create a template for validation testing."""
        # Create basic structure
        (template_path / "__init__.py").write_text("")
        (template_path / "scraper.py").write_text("""
from src.sites.base.template import BaseSiteTemplate

class ValidationTestScraper(BaseSiteTemplate):
    def __init__(self, page, selector_engine):
        super().__init__("validation_test", "1.0.0", "Test", "Test", "1.0.0", "test.com")
    
    async def _execute_scrape_logic(self, action, **kwargs):
        return {"action": action, "success": True}
""")
        
        (template_path / "config.py").write_text("""
# Configuration
SITE_CONFIG = {
    "name": "validation_test",
    "domain": "test.com"
}
""")
        
        (template_path / "metadata.json").write_text(json.dumps({
            "name": "validation_test",
            "version": "1.0.0",
            "description": "Validation test template",
            "author": "Test",
            "site_domain": "test.com",
            "framework_version": "1.0.0",
            "capabilities": ["scraping"],
            "dependencies": [],
            "tags": ["test"]
        }))
        
        # Create selectors
        selectors_dir = template_path / "selectors"
        selectors_dir.mkdir()
        
        (selectors_dir / "test_selector.yaml").write_text(yaml.dump({
            "name": "test_selector",
            "description": "Test selector",
            "selector": ".test-element",
            "strategies": [
                {
                    "name": "css",
                    "type": "css",
                    "priority": 1,
                    "confidence": 0.9
                }
            ],
            "validation": {
                "required": True,
                "exists": True
            },
            "metadata": {
                "category": "test",
                "version": "1.0.0"
            }
        }))
    
    def _load_selector_configs(self, selectors_dir: Path) -> list:
        """Load selector configurations from directory."""
        configs = []
        for yaml_file in selectors_dir.glob("*.yaml"):
            with open(yaml_file, 'r') as f:
                configs.append(yaml.safe_load(f))
        return configs
    
    @pytest.mark.asyncio
    async def test_migration_workflow(self, temp_template_dir):
        """Test template migration workflow."""
        # Create old version template
        old_template_path = temp_template_dir / "old_template"
        old_template_path.mkdir()
        
        self._create_old_version_template(old_template_path)
        
        # Initialize upgrader
        upgrader = TemplateUpgrader()
        
        # Step 1: Get current version
        current_version = upgrader._get_template_version(old_template_path)
        assert current_version == "1.0.0"
        
        # Step 2: Upgrade template
        upgrade_result = await upgrader.upgrade_template(
            old_template_path, "1.1.0"
        )
        
        assert upgrade_result["success"], f"Upgrade failed: {upgrade_result.get('error')}"
        assert upgrade_result["current_version"] == "1.0.0"
        assert upgrade_result["target_version"] == "1.1.0"
        
        # Step 3: Verify upgraded template
        new_version = upgrader._get_template_version(old_template_path)
        assert new_version == "1.1.0"
    
    def _create_old_version_template(self, template_path: Path):
        """Create an old version template for migration testing."""
        (template_path / "__init__.py").write_text("")
        
        # Create old-style scraper
        (template_path / "scraper.py").write_text("""
from src.sites.base import BaseSiteScraper

class OldTemplateScraper(BaseSiteScraper):
    def __init__(self, page, selector_engine):
        super().__init__(page, selector_engine)
        self.name = "old_template"
        self.version = "1.0.0"
""")
        
        (template_path / "metadata.json").write_text(json.dumps({
            "name": "old_template",
            "version": "1.0.0",
            "description": "Old version template",
            "author": "Test",
            "site_domain": "old.com",
            "framework_version": "1.0.0",
            "capabilities": ["scraping"],
            "dependencies": [],
            "tags": ["old"]
        }))
    
    @pytest.mark.asyncio
    async def test_observability_workflow(self, mock_components):
        """Test observability and monitoring workflow."""
        # Initialize observability manager
        obs_manager = ObservabilityManager()
        
        # Step 1: Start monitoring
        obs_manager.start_monitoring()
        
        # Step 2: Record metrics
        metrics_collector = obs_manager.metrics_collector
        metrics_collector.record_counter("template_executions", 1.0)
        metrics_collector.record_gauge("memory_usage", 512*1024*1024)
        metrics_collector.record_timer("scrape_duration", 2.5)
        metrics_collector.record_histogram("response_size", 1024)
        
        # Step 3: Check alerts
        alerts = obs_manager.alert_manager.check_alerts(metrics_collector)
        assert isinstance(alerts, list)
        
        # Step 4: Check health status
        health_status = obs_manager.health_monitor.get_health_status()
        assert health_status["overall_health"] in ["healthy", "degraded", "unhealthy"]
        
        # Step 5: Get observability status
        obs_status = obs_manager.get_observability_status()
        assert "metrics" in obs_status
        assert "alerts" in obs_status
        assert "health" in obs_status
        
        # Step 6: Stop monitoring
        obs_manager.stop_monitoring()
        obs_manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_quickstart_guide_validation(self, temp_template_dir, mock_components):
        """Test quickstart guide examples and workflows."""
        # This test validates that the quickstart guide examples work correctly
        
        # Step 1: Test template structure creation
        template_structure = [
            "__init__.py",
            "scraper.py",
            "flow.py",
            "config.py",
            "integration_bridge.py",
            "selector_loader.py",
            "extraction/__init__.py",
            "extraction/rules.py",
            "extraction/models.py",
            "selectors/search_input.yaml",
            "selectors/repository_list.yaml",
            "selectors/repository_details.yaml",
            "flows/search_flow.py",
            "flows/pagination_flow.py"
        ]
        
        template_path = temp_template_dir / "github_test"
        template_path.mkdir()
        
        # Create directory structure
        for item in template_structure:
            if "/" in item:
                (template_path / item).parent.mkdir(parents=True, exist_ok=True)
            (template_path / item).touch()
        
        # Step 2: Test YAML selector creation
        selector_config = {
            "name": "search_input",
            "description": "GitHub search input field",
            "strategies": [
                {
                    "type": "css",
                    "selector": "input[name='q']",
                    "priority": 1,
                    "confidence": 0.9
                }
            ],
            "validation": {
                "required": True,
                "exists": True
            },
            "metadata": {
                "category": "form",
                "version": "1.0.0"
            }
        }
        
        selector_file = template_path / "selectors" / "search_input.yaml"
        with open(selector_file, 'w') as f:
            yaml.dump(selector_config, f)
        
        # Validate YAML syntax
        with open(selector_file, 'r') as f:
            loaded_config = yaml.safe_load(f)
        assert loaded_config["name"] == "search_input"
        
        # Step 3: Test integration bridge creation
        bridge_content = '''
from src.sites.base.template.integration_bridge import FullIntegrationBridge

class GitHubIntegrationBridge(FullIntegrationBridge):
    def __init__(self, template_name, selector_engine, page):
        super().__init__(template_name, selector_engine, page)
'''
        
        (template_path / "integration_bridge.py").write_text(bridge_content)
        
        # Step 4: Test scraper creation
        scraper_content = '''
from src.sites.base.template import BaseSiteTemplate

class GitHubScraper(BaseSiteTemplate):
    def __init__(self, page, selector_engine):
        super().__init__(
            name="github",
            version="1.0.0",
            description="GitHub scraper",
            author="Test",
            framework_version="1.0.0",
            site_domain="github.com"
        )
    
    async def _execute_scrape_logic(self, action, **kwargs):
        if action == "scrape_repositories":
            return await self._scrape_repositories(**kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _scrape_repositories(self, query, **kwargs):
        return {
            "action": "scrape_repositories",
            "query": query,
            "repositories": [],
            "success": True
        }
'''
        
        (template_path / "scraper.py").write_text(scraper_content)
        
        # Step 5: Test template instantiation
        import importlib.util
        spec = importlib.util.spec_from_file_location("github_scraper", template_path / "scraper.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        scraper = module.GitHubScraper(
            mock_components["page"],
            mock_components["selector_engine"]
        )
        
        # Step 6: Test scraper initialization
        await scraper.initialize()
        assert scraper.name == "github"
        assert scraper.site_domain == "github.com"
        
        # Step 7: Test scraper execution
        result = await scraper.scrape("scrape_repositories", query="python")
        assert result["success"]
        assert result["query"] == "python"
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, mock_components):
        """Test error handling and recovery mechanisms."""
        # Create a scraper that will encounter errors
        class ErrorTestScraper(BaseSiteTemplate):
            def __init__(self, page, selector_engine):
                super().__init__(
                    name="error_test",
                    version="1.0.0",
                    description="Error test scraper",
                    author="Test",
                    framework_version="1.0.0",
                    site_domain="error.com"
                )
            
            async def _execute_scrape_logic(self, action, **kwargs):
                if action == "cause_error":
                    raise ValueError("Intentional error for testing")
                elif action == "cause_network_error":
                    raise ConnectionError("Network error simulation")
                else:
                    return {"action": action, "success": True}
        
        scraper = ErrorTestScraper(
            mock_components["page"],
            mock_components["selector_engine"]
        )
        
        await scraper.initialize()
        
        # Test 1: Handle ValueError
        with pytest.raises(ValueError):
            await scraper.scrape("cause_error")
        
        # Test 2: Handle ConnectionError
        with pytest.raises(ConnectionError):
            await scraper.scrape("cause_network_error")
        
        # Test 3: Verify scraper still works after errors
        result = await scraper.scrape("test_action")
        assert result["success"]
        
        # Test 4: Check error state capture
        error_state = scraper.get_error_state()
        assert "errors" in error_state
        assert len(error_state["errors"]) >= 2
    
    @pytest.mark.asyncio
    async def test_performance_optimization(self, mock_components):
        """Test performance optimization features."""
        # Create a performance test scraper
        class PerformanceTestScraper(BaseSiteTemplate):
            def __init__(self, page, selector_engine):
                super().__init__(
                    name="performance_test",
                    version="1.0.0",
                    description="Performance test scraper",
                    author="Test",
                    framework_version="1.0.0",
                    site_domain="performance.com"
                )
            
            async def _execute_scrape_logic(self, action, **kwargs):
                # Simulate some work
                await asyncio.sleep(0.1)
                return {"action": action, "success": True}
        
        scraper = PerformanceTestScraper(
            mock_components["page"],
            mock_components["selector_engine"]
        )
        
        await scraper.initialize()
        
        # Test 1: Measure performance
        import time
        start_time = time.time()
        
        # Execute multiple scrapes
        for i in range(5):
            await scraper.scrape("test_action", iteration=i)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Test 2: Check performance metrics
        metrics = scraper.get_performance_metrics()
        assert metrics["scrape_count"] == 5
        assert metrics["success_rate"] == 1.0
        assert "average_scrape_time" in metrics
        
        # Test 3: Verify performance is reasonable
        assert total_time < 2.0  # Should complete in under 2 seconds
        assert metrics["average_scrape_time"] < 0.5  # Average should be under 0.5s
    
    @pytest.mark.asyncio
    async def test_security_features(self, mock_components):
        """Test security features and safeguards."""
        # Test security validation
        from src.sites.base.template.security import SecurityManager
        
        security_manager = SecurityManager()
        
        # Test 1: Validate safe code
        safe_code = "print('hello world')"
        scan_result = security_manager.scan_code(safe_code, "test.py")
        assert scan_result["safe"]
        assert len(scan_result["violations"]) == 0
        
        # Test 2: Detect unsafe code
        unsafe_code = "eval('dangerous code')"
        scan_result = security_manager.scan_code(unsafe_code, "test.py")
        assert not scan_result["safe"]
        assert len(scan_result["violations"]) > 0
        
        # Test 3: Safe code execution
        result = await security_manager.execute_safe_code(
            "result = 2 + 2", {"result": None}
        )
        assert result["success"]
        assert result["result"] == 4
        
        # Test 4: Block unsafe execution
        result = await security_manager.execute_safe_code(
            "eval('dangerous')", {}
        )
        assert not result["success"]
        assert "security" in result["error"].lower()


class TestIntegrationScenarios:
    """Integration scenario tests."""
    
    @pytest.mark.asyncio
    async def test_multi_template_workflow(self, temp_template_dir, mock_components):
        """Test workflow with multiple templates."""
        # Create multiple templates
        templates = ["site1", "site2", "site3"]
        scrapers = []
        
        for template_name in templates:
            template_path = temp_template_dir / template_name
            template_path.mkdir()
            
            # Create simple scraper
            (template_path / "scraper.py").write_text(f'''
from src.sites.base.template import BaseSiteTemplate

class {template_name.title()}Scraper(BaseSiteTemplate):
    def __init__(self, page, selector_engine):
        super().__init__(
            name="{template_name}",
            version="1.0.0",
            description="{template_name} scraper",
            author="Test",
            framework_version="1.0.0",
            site_domain="{template_name}.com"
        )
    
    async def _execute_scrape_logic(self, action, **kwargs):
        return {{
            "action": action,
            "template": "{template_name}",
            "success": True
        }}
''')
            
            # Load and instantiate scraper
            import importlib.util
            spec = importlib.util.spec_from_file_location(template_name, template_path / "scraper.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            scraper_class = getattr(module, f"{template_name.title()}Scraper")
            scraper = scraper_class(
                mock_components["page"],
                mock_components["selector_engine"]
            )
            
            await scraper.initialize()
            scrapers.append(scraper)
        
        # Test all scrapers work
        for scraper in scrapers:
            result = await scraper.scrape("test_action")
            assert result["success"]
            assert "template" in result
        
        # Test concurrent execution
        tasks = [scraper.scrape("test_action") for scraper in scrapers]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == len(scrapers)
        assert all(result["success"] for result in results)
    
    @pytest.mark.asyncio
    async def test_template_lifecycle_management(self, mock_components):
        """Test complete template lifecycle management."""
        # Create scraper
        scraper = BaseSiteTemplate(
            name="lifecycle_test",
            version="1.0.0",
            description="Lifecycle test scraper",
            author="Test",
            framework_version="1.0.0",
            site_domain="lifecycle.com"
        )
        
        # Mock the abstract method
        async def mock_execute_logic(action, **kwargs):
            return {"action": action, "success": True}
        scraper._execute_scrape_logic = mock_execute_logic
        
        # Test 1: Initialization
        await scraper.initialize()
        assert scraper.initialized
        
        # Test 2: Multiple executions
        for i in range(3):
            result = await scraper.scrape("test_action", iteration=i)
            assert result["success"]
        
        # Test 3: Health monitoring
        health = await scraper.health_check()
        assert health["overall_health"] == "healthy"
        
        # Test 4: Performance tracking
        metrics = scraper.get_performance_metrics()
        assert metrics["scrape_count"] == 3
        assert metrics["success_rate"] == 1.0
        
        # Test 5: Cleanup
        await scraper.cleanup()
        assert not scraper.initialized


# Test runner
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
