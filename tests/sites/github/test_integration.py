"""
Integration tests for GitHub template with all framework features.

This module provides comprehensive integration tests for the GitHub template,
testing all framework component integrations including browser lifecycle,
resource monitoring, logging, and stealth features.
"""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.sites.github.scraper import GitHubScraper
from src.sites.github.flow import GitHubFlow
from src.sites.github.integration_bridge import GitHubIntegrationBridge
from src.sites.github.selector_loader import GitHubSelectorLoader
from src.sites.github.extraction.rules import GitHubExtractionRules


class MockPage:
    """Enhanced mock Playwright page for GitHub testing."""
    
    def __init__(self):
        self.url = "https://github.com"
        self._browser_type = "chromium"
        self._events = {}
        self._content = """
        <html>
        <head><title>GitHub</title></head>
        <body>
            <input name="q" type="search" placeholder="Search GitHub">
            <div class="repo-list">
                <div class="repo-list-item">
                    <h3><a href="/test/repo">test/repo</a></h3>
                    <p>Test repository description</p>
                    <div class="repo-stats">
                        <span>⭐ 100</span>
                        <span>🍴 20</span>
                        <span>🐛 5</span>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    async def screenshot(self, path=None, **kwargs):
        """Mock screenshot capture."""
        if path:
            Path(path).write_bytes(b"fake_github_screenshot_data")
        return path
    
    async def content(self):
        """Mock page content."""
        return self._content
    
    async def evaluate(self, script):
        """Mock JavaScript evaluation."""
        if "navigator.userAgent" in script:
            return "Mozilla/5.0 (Test Browser)"
        elif "window.innerWidth" in script:
            return {"width": 1920, "height": 1080}
        return {}
    
    async def wait_for_selector(self, selector, timeout=30000):
        """Mock wait for selector."""
        return Mock()
    
    async def goto(self, url):
        """Mock navigation."""
        self.url = url
        return Mock()
    
    def on(self, event, handler):
        """Mock event handler registration."""
        if event not in self._events:
            self._events[event] = []
        self._events[event].append(handler)
    
    def emit(self, event, data):
        """Mock event emission."""
        if event in self._events:
            for handler in self._events[event]:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(data))
                else:
                    handler(data)


class MockSelectorEngine:
    """Enhanced mock selector engine for GitHub testing."""
    
    def __init__(self):
        self.selectors = {}
        self.__version__ = "1.0.0"
        self._github_selectors = {
            "search_input": "input[name='q']",
            "repository_list": ".repo-list",
            "repository_list_item": ".repo-list-item",
            "repository_title": ".repo-list-item h3 a",
            "repository_description": ".repo-list-item p",
            "repository_stats": ".repo-stats"
        }
    
    def register_selector(self, name, selector_config):
        """Mock selector registration."""
        self.selectors[name] = selector_config
    
    async def find_all(self, element=None, selector_name=None):
        """Mock find all with GitHub-specific results."""
        if selector_name in self._github_selectors:
            return [Mock(text_content=lambda: f"Mock {selector_name} result")]
        return []
    
    def validate_selector(self, selector_config):
        """Mock selector validation."""
        return True
    
    def get_confidence_score(self, selector_config):
        """Mock confidence scoring."""
        return 0.9


class TestGitHubTemplateIntegration:
    """Test cases for GitHub template integration with all framework features."""
    
    @pytest.fixture
    def mock_page(self):
        """Create enhanced mock page for GitHub."""
        return MockPage()
    
    @pytest.fixture
    def mock_selector_engine(self):
        """Create enhanced mock selector engine for GitHub."""
        return MockSelectorEngine()
    
    @pytest.fixture
    def github_scraper(self, mock_page, mock_selector_engine):
        """Create GitHub scraper instance."""
        return GitHubScraper(mock_page, mock_selector_engine)
    
    @pytest.mark.asyncio
    async def test_github_scraper_initialization(self, github_scraper):
        """Test GitHub scraper initialization with all components."""
        with patch('src.sites.base.template.resource_monitoring.psutil'):
            result = await github_scraper.initialize()
            
            assert result is True
            assert github_scraper.initialized is True
            assert github_scraper.name == "github"
            assert github_scraper.version == "1.0.0"
            
            # Check that all integration components are initialized
            assert github_scraper.integration_bridge is not None
            assert github_scraper.flow is not None
            assert github_scraper.selector_loader is not None
            assert github_scraper.extraction_rules is not None
    
    @pytest.mark.asyncio
    async def test_github_capabilities(self, github_scraper):
        """Test GitHub template capabilities."""
        await github_scraper.initialize()
        
        capabilities = github_scraper.capabilities
        
        # Check core GitHub capabilities
        assert "repository_search" in capabilities
        assert "repository_details" in capabilities
        assert "user_profile" in capabilities
        assert "issue_tracking" in capabilities
        assert "pull_request_tracking" in capabilities
        
        # Check framework integration capabilities
        assert "screenshot_capture" in capabilities
        assert "html_capture" in capabilities
        assert "resource_monitoring" in capabilities
        assert "performance_logging" in capabilities
        assert "error_tracking" in capabilities
    
    @pytest.mark.asyncio
    async def test_browser_lifecycle_integration(self, github_scraper):
        """Test browser lifecycle integration."""
        with patch('src.sites.base.template.resource_monitoring.psutil'):
            await github_scraper.initialize()
            
            # Test screenshot capture
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                screenshot_result = await github_scraper.capture_github_screenshot(
                    context="test",
                    filename=tmp_path
                )
                
                assert screenshot_result is not None
                assert Path(screenshot_result).exists()
                
            finally:
                if Path(tmp_path).exists():
                    Path(tmp_path).unlink()
            
            # Test HTML capture
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                html_result = await github_scraper.capture_github_html(
                    context="test",
                    filename=tmp_path
                )
                
                assert html_result is not None
                assert Path(html_result).exists()
                
            finally:
                if Path(tmp_path).exists():
                    Path(tmp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_resource_monitoring_integration(self, github_scraper):
        """Test resource monitoring integration."""
        with patch('src.sites.base.template.resource_monitoring.psutil'):
            await github_scraper.initialize()
            
            # Check that resource monitoring is available
            assert github_scraper.resource_monitoring is not None
            
            # Test resource monitoring status
            status = github_scraper.resource_monitoring.get_monitoring_status()
            
            assert "template_name" in status
            assert status["template_name"] == "github"
            assert "features_available" in status
            assert "config" in status
    
    @pytest.mark.asyncio
    async def test_logging_integration(self, github_scraper):
        """Test logging integration."""
        with patch('src.sites.base.template.resource_monitoring.psutil'):
            await github_scraper.initialize()
            
            # Check that logging integration is available
            assert github_scraper.logging_integration is not None
            
            # Test logging status
            status = github_scraper.logging_integration.get_logging_status()
            
            assert "template_name" in status
            assert status["template_name"] == "github"
            assert "correlation_id" in status
            assert "session_id" in status
            
            # Test performance logging
            github_scraper.logging_integration.log_performance(
                "test_operation",
                1.5,
                {"component": "test"}
            )
            
            performance_log = github_scraper.logging_integration.get_performance_log()
            assert len(performance_log) == 1
            assert performance_log[0]["operation"] == "test_operation"
            assert performance_log[0]["duration"] == 1.5
            
            # Test error logging
            test_error = Exception("GitHub test error")
            github_scraper.logging_integration.log_error(
                test_error,
                {"context": "test"}
            )
            
            error_log = github_scraper.logging_integration.get_error_log()
            assert len(error_log) == 1
            assert error_log[0]["error_type"] == "Exception"
            assert error_log[0]["error_message"] == "GitHub test error"
    
    @pytest.mark.asyncio
    async def test_github_browser_info(self, github_scraper):
        """Test GitHub browser information."""
        with patch('src.sites.base.template.resource_monitoring.psutil'):
            await github_scraper.initialize()
            
            browser_info = github_scraper.get_github_browser_info()
            
            assert "template" in browser_info
            assert browser_info["template"] == "github"
            assert "browser_lifecycle_available" in browser_info
            
            if browser_info["browser_lifecycle_available"]:
                assert "session_info" in browser_info
                assert "feature_status" in browser_info
                assert "config" in browser_info
    
    @pytest.mark.asyncio
    async def test_github_error_state_capture(self, github_scraper):
        """Test GitHub error state capture."""
        with patch('src.sites.base.template.resource_monitoring.psutil'):
            await github_scraper.initialize()
            
            error_state = await github_scraper.capture_github_error_state(
                error_type="test_error",
                operation="test_operation"
            )
            
            assert "error_type" in error_state
            assert error_state["error_type"] == "test_error"
            assert "operation" in error_state
            assert error_state["operation"] == "test_operation"
            assert "timestamp" in error_state
    
    @pytest.mark.asyncio
    async def test_github_scrape_operations(self, github_scraper):
        """Test GitHub scrape operations with framework integration."""
        with patch('src.sites.base.template.resource_monitoring.psutil'):
            await github_scraper.initialize()
            
            # Test repository search
            search_result = await github_scraper.scrape(
                action="search_repositories",
                query="test",
                limit=10
            )
            
            assert "action" in search_result
            assert search_result["action"] == "search_repositories"
            assert "query" in search_result
            assert search_result["query"] == "test"
            assert "results" in search_result
            
            # Test repository details
            repo_result = await github_scraper.scrape(
                action="get_repository",
                identifier="test/repo"
            )
            
            assert "action" in repo_result
            assert repo_result["action"] == "get_repository"
            assert "identifier" in repo_result
            assert repo_result["identifier"] == "test/repo"
            
            # Test user profile
            user_result = await github_scraper.scrape(
                action="get_user",
                identifier="testuser"
            )
            
            assert "action" in user_result
            assert user_result["action"] == "get_user"
            assert "identifier" in user_result
            assert user_result["identifier"] == "testuser"
    
    @pytest.mark.asyncio
    async def test_framework_component_auto_configuration(self, github_scraper):
        """Test framework component auto-configuration."""
        with patch('src.sites.base.template.resource_monitoring.psutil'):
            await github_scraper.initialize()
            
            # Check that integration bridge has auto-configurations
            if github_scraper.integration_bridge:
                auto_configs = github_scraper.integration_bridge.get_auto_configurations()
                
                # Check for expected configurations
                expected_configs = [
                    "browser_lifecycle",
                    "resource_monitoring", 
                    "logging",
                    "stealth"
                ]
                
                for config_name in expected_configs:
                    if config_name in auto_configs:
                        assert isinstance(auto_configs[config_name], dict)
    
    @pytest.mark.asyncio
    async def test_github_template_health_check(self, github_scraper):
        """Test GitHub template health check."""
        with patch('src.sites.base.template.resource_monitoring.psutil'):
            await github_scraper.initialize()
            
            health_status = await github_scraper.health_check()
            
            assert "template_name" in health_status
            assert health_status["template_name"] == "github"
            assert "template_version" in health_status
            assert health_status["template_version"] == "1.0.0"
            assert "initialized" in health_status
            assert health_status["initialized"] is True
            assert "components" in health_status
            assert "overall_health" in health_status
    
    @pytest.mark.asyncio
    async def test_github_template_info(self, github_scraper):
        """Test GitHub template information."""
        with patch('src.sites.base.template.resource_monitoring.psutil'):
            await github_scraper.initialize()
            
            template_info = github_scraper.get_template_info()
            
            assert "name" in template_info
            assert template_info["name"] == "github"
            assert "version" in template_info
            assert template_info["version"] == "1.0.0"
            assert "description" in template_info
            assert "author" in template_info
            assert "capabilities" in template_info
            assert "dependencies" in template_info
            assert "initialized" in template_info
            assert template_info["initialized"] is True
            
            # Check browser features if available
            if github_scraper.browser_lifecycle:
                assert "browser_features" in template_info
                assert "browser_session" in template_info
    
    @pytest.mark.asyncio
    async def test_github_performance_metrics(self, github_scraper):
        """Test GitHub performance metrics."""
        with patch('src.sites.base.template.resource_monitoring.psutil'):
            await github_scraper.initialize()
            
            # Get initial performance metrics
            initial_metrics = github_scraper.get_performance_metrics()
            
            assert "scrape_count" in initial_metrics
            assert "total_scrape_time" in initial_metrics
            assert "average_scrape_time" in initial_metrics
            assert "error_count" in initial_metrics
            assert "success_count" in initial_metrics
            assert "success_rate" in initial_metrics
    
    @pytest.mark.asyncio
    async def test_github_error_handling(self, github_scraper):
        """Test GitHub error handling with framework integration."""
        with patch('src.sites.base.template.resource_monitoring.psutil'):
            await github_scraper.initialize()
            
            # Test error handling during scrape
            try:
                # This should trigger error handling
                await github_scraper.scrape(
                    action="invalid_action",
                    query="test"
                )
            except Exception as e:
                # Error should be handled and logged
                assert github_scraper.logging_integration is not None
                
                # Check that error was logged
                error_log = github_scraper.logging_integration.get_error_log()
                assert len(error_log) > 0
    
    @pytest.mark.asyncio
    async def test_complete_github_integration(self, github_scraper):
        """Test complete GitHub integration with all framework features."""
        with patch('src.sites.base.template.resource_monitoring.psutil'):
            # Initialize all components
            await github_scraper.initialize()
            
            # Verify all integrations are active
            assert github_scraper.integration_bridge is not None
            assert github_scraper.flow is not None
            assert github_scraper.selector_loader is not None
            assert github_scraper.extraction_rules is not None
            
            # Verify framework integrations
            if github_scraper.browser_lifecycle:
                assert github_scraper.browser_lifecycle.browser_session_id is not None
            
            if github_scraper.resource_monitoring:
                assert github_scraper.resource_monitoring.monitoring_session_id is not None
            
            if github_scraper.logging_integration:
                assert github_scraper.logging_integration.correlation_id is not None
                assert github_scraper.logging_integration.session_id is not None
            
            # Test a complete workflow
            # 1. Capture screenshot before operation
            screenshot_path = await github_scraper.capture_github_screenshot("before_search")
            
            # 2. Perform search operation
            search_result = await github_scraper.scrape(
                action="search_repositories",
                query="test",
                limit=5
            )
            
            # 3. Capture HTML after operation
            html_path = await github_scraper.capture_github_html("after_search")
            
            # 4. Check performance metrics
            performance_metrics = github_scraper.get_performance_metrics()
            
            # 5. Check health status
            health_status = await github_scraper.health_check()
            
            # Verify all components worked together
            assert search_result["action"] == "search_repositories"
            assert performance_metrics["scrape_count"] > 0
            assert health_status["overall_health"] in ["healthy", "degraded"]
            
            # Verify logs were created
            if github_scraper.logging_integration:
                performance_log = github_scraper.logging_integration.get_performance_log()
                assert len(performance_log) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
