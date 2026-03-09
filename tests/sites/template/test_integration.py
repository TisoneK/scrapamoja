"""
Integration tests for template framework components.

This module provides comprehensive integration tests for the template framework,
including browser lifecycle, resource monitoring, and logging integration.
"""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

from src.sites.base.template.integration_bridge import FullIntegrationBridge
from src.sites.base.template.browser_lifecycle import BrowserLifecycleIntegration
from src.sites.base.template.resource_monitoring import ResourceMonitoringIntegration
from src.sites.base.template.logging_integration import LoggingFrameworkIntegration


class MockPage:
    """Mock Playwright page for testing."""
    
    def __init__(self):
        self.url = "https://example.com"
        self._browser_type = "chromium"
        self._events = {}
        self._content = "<html><body>Test content</body></html>"
    
    async def screenshot(self, path=None, **kwargs):
        """Mock screenshot capture."""
        if path:
            Path(path).write_bytes(b"fake_screenshot_data")
        return path
    
    async def content(self):
        """Mock page content."""
        return self._content
    
    async def evaluate(self, script):
        """Mock JavaScript evaluation."""
        if "navigator.userAgent" in script:
            return "Mozilla/5.0 (Test Browser)"
        return {}
    
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
    """Mock selector engine for testing."""
    
    def __init__(self):
        self.selectors = {}
        self.__version__ = "1.0.0"
    
    def register_selector(self, name, selector_config):
        """Mock selector registration."""
        self.selectors[name] = selector_config
    
    async def find_all(self, element=None, selector_name=None):
        """Mock find all."""
        return []
    
    def validate_selector(self, selector_config):
        """Mock selector validation."""
        return True
    
    def get_confidence_score(self, selector_config):
        """Mock confidence scoring."""
        return 0.8


class TestIntegrationBridge:
    """Test cases for integration bridge."""
    
    @pytest.fixture
    def mock_page(self):
        """Create mock page."""
        return MockPage()
    
    @pytest.fixture
    def mock_selector_engine(self):
        """Create mock selector engine."""
        return MockSelectorEngine()
    
    @pytest.fixture
    def integration_bridge(self, mock_page, mock_selector_engine):
        """Create integration bridge."""
        return FullIntegrationBridge(
            template_name="test_template",
            page=mock_page,
            selector_engine=mock_selector_engine
        )
    
    @pytest.mark.asyncio
    async def test_bridge_initialization(self, integration_bridge):
        """Test bridge initialization."""
        result = await integration_bridge.initialize()
        
        assert result is True
        assert integration_bridge.initialized is True
        assert integration_bridge.template_name == "test_template"
    
    @pytest.mark.asyncio
    async def test_framework_component_detection(self, integration_bridge):
        """Test framework component detection."""
        result = await integration_bridge.initialize()
        
        assert result is True
        
        components = integration_bridge.get_available_components()
        
        # Check that core components are detected
        assert "selector_engine" in components
        assert "browser_lifecycle" in components
        assert "screenshot_capture" in components
        assert "html_capture" in components
        
        # Check component availability
        assert components["selector_engine"]["available"] is True
        assert components["browser_lifecycle"]["available"] is True
    
    @pytest.mark.asyncio
    async def test_component_availability_check(self, integration_bridge):
        """Test component availability checking."""
        await integration_bridge.initialize()
        
        # Test available component
        assert integration_bridge.is_component_available("selector_engine") is True
        
        # Test unavailable component
        assert integration_bridge.is_component_available("nonexistent") is False
    
    def test_bridge_status(self, integration_bridge):
        """Test bridge status reporting."""
        status = integration_bridge.get_integration_status()
        
        assert "template_name" in status
        assert "is_integrated" in status
        assert "components" in status
        assert status["template_name"] == "test_template"


class TestBrowserLifecycleIntegration:
    """Test cases for browser lifecycle integration."""
    
    @pytest.fixture
    def mock_page(self):
        """Create mock page."""
        return MockPage()
    
    @pytest.fixture
    def mock_integration_bridge(self, mock_page):
        """Create mock integration bridge."""
        bridge = Mock(FullIntegrationBridge)
        bridge.template_name = "test_template"
        bridge.page = mock_page
        bridge.get_available_components.return_value = {
            "browser_lifecycle": {"available": True},
            "screenshot_capture": {"available": True},
            "html_capture": {"available": True}
        }
        return bridge
    
    @pytest.fixture
    def browser_lifecycle(self, mock_integration_bridge):
        """Create browser lifecycle integration."""
        return BrowserLifecycleIntegration(mock_integration_bridge)
    
    @pytest.mark.asyncio
    async def test_browser_lifecycle_initialization(self, browser_lifecycle):
        """Test browser lifecycle initialization."""
        result = await browser_lifecycle.initialize_browser_integration()
        
        assert result is True
        assert browser_lifecycle.browser_session_id is not None
        assert len(browser_lifecycle.lifecycle_events) > 0
    
    @pytest.mark.asyncio
    async def test_screenshot_capture(self, browser_lifecycle):
        """Test screenshot capture."""
        await browser_lifecycle.initialize_browser_integration()
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            result = await browser_lifecycle.capture_screenshot(filename=tmp_path)
            
            assert result is not None
            assert Path(result).exists()
            assert len(browser_lifecycle.lifecycle_events) > 0
            
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_html_capture(self, browser_lifecycle):
        """Test HTML capture."""
        await browser_lifecycle.initialize_browser_integration()
        
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            result = await browser_lifecycle.capture_html(filename=tmp_path)
            
            assert result is not None
            assert Path(result).exists()
            assert len(browser_lifecycle.lifecycle_events) > 0
            
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_error_screenshot_capture(self, browser_lifecycle):
        """Test error screenshot capture."""
        await browser_lifecycle.initialize_browser_integration()
        
        result = await browser_lifecycle.capture_error_screenshot("test_error")
        
        assert result is not None
        assert "test_error" in result
    
    @pytest.mark.asyncio
    async def test_error_html_capture(self, browser_lifecycle):
        """Test error HTML capture."""
        await browser_lifecycle.initialize_browser_integration()
        
        result = await browser_lifecycle.capture_error_html("test_error")
        
        assert result is not None
        assert "test_error" in result
    
    def test_browser_session_info(self, browser_lifecycle):
        """Test browser session information."""
        session_info = browser_lifecycle.get_browser_session_info()
        
        assert "template_name" in session_info
        assert "session_id" in session_info
        assert "capabilities" in session_info
        assert "features_available" in session_info
    
    def test_lifecycle_events(self, browser_lifecycle):
        """Test lifecycle events."""
        # Add some test events
        browser_lifecycle.lifecycle_events = [
            {"type": "test_event", "timestamp": "2023-01-01T00:00:00"},
            {"type": "another_event", "timestamp": "2023-01-01T00:01:00"}
        ]
        
        events = browser_lifecycle.get_lifecycle_events()
        
        assert len(events) == 2
        assert events[0]["type"] == "test_event"
    
    def test_feature_status(self, browser_lifecycle):
        """Test feature status."""
        features = browser_lifecycle.get_feature_status()
        
        assert isinstance(features, dict)
        assert "screenshot_capture" in features
        assert "html_capture" in features


class TestResourceMonitoringIntegration:
    """Test cases for resource monitoring integration."""
    
    @pytest.fixture
    def mock_integration_bridge(self):
        """Create mock integration bridge."""
        bridge = Mock(FullIntegrationBridge)
        bridge.template_name = "test_template"
        bridge.get_available_components.return_value = {
            "resource_monitoring": {
                "available": True,
                "supports_memory_monitoring": True,
                "supports_cpu_monitoring": True,
                "supports_disk_monitoring": True,
                "supports_network_monitoring": True
            }
        }
        return bridge
    
    @pytest.fixture
    def resource_monitoring(self, mock_integration_bridge):
        """Create resource monitoring integration."""
        return ResourceMonitoringIntegration(mock_integration_bridge)
    
    @pytest.mark.asyncio
    async def test_resource_monitoring_initialization(self, resource_monitoring):
        """Test resource monitoring initialization."""
        with patch('src.sites.base.template.resource_monitoring.psutil'):
            result = await resource_monitoring.initialize_resource_monitoring()
            
            assert result is True
            assert resource_monitoring.monitoring_session_id is not None
    
    @pytest.mark.asyncio
    async def test_monitoring_start_stop(self, resource_monitoring):
        """Test monitoring start and stop."""
        with patch('src.sites.base.template.resource_monitoring.psutil'):
            await resource_monitoring.initialize_resource_monitoring()
            
            # Start monitoring
            start_result = await resource_monitoring.start_monitoring()
            assert start_result is True
            assert resource_monitoring.monitoring_active is True
            
            # Stop monitoring
            stop_result = await resource_monitoring.stop_monitoring()
            assert stop_result is True
            assert resource_monitoring.monitoring_active is False
    
    def test_monitoring_status(self, resource_monitoring):
        """Test monitoring status."""
        status = resource_monitoring.get_monitoring_status()
        
        assert "template_name" in status
        assert "monitoring_active" in status
        assert "features_available" in status
        assert "config" in status
        assert status["template_name"] == "test_template"
    
    def test_resource_history(self, resource_monitoring):
        """Test resource history."""
        # Add some test history
        resource_monitoring.resource_history = [
            {"timestamp": "2023-01-01T00:00:00", "cpu": 50.0},
            {"timestamp": "2023-01-01T00:01:00", "cpu": 60.0}
        ]
        
        history = resource_monitoring.get_resource_history()
        
        assert len(history) == 2
        assert history[0]["cpu"] == 50.0
    
    def test_threshold_alerts(self, resource_monitoring):
        """Test threshold alerts."""
        # Add some test alerts
        resource_monitoring.threshold_alerts = [
            {"type": "memory", "current": 85.0, "threshold": 80.0},
            {"type": "cpu", "current": 90.0, "threshold": 80.0}
        ]
        
        alerts = resource_monitoring.get_threshold_alerts()
        
        assert len(alerts) == 2
        assert alerts[0]["type"] == "memory"
    
    def test_config_update(self, resource_monitoring):
        """Test configuration update."""
        new_config = {"memory_threshold": 90.0, "cpu_threshold": 85.0}
        
        resource_monitoring.update_config(new_config)
        
        assert resource_monitoring.config["memory_threshold"] == 90.0
        assert resource_monitoring.config["cpu_threshold"] == 85.0


class TestLoggingFrameworkIntegration:
    """Test cases for logging framework integration."""
    
    @pytest.fixture
    def mock_integration_bridge(self):
        """Create mock integration bridge."""
        bridge = Mock(FullIntegrationBridge)
        bridge.template_name = "test_template"
        bridge.get_available_components.return_value = {
            "logging_framework": {
                "available": True,
                "supports_structured_logging": True,
                "supports_correlation_ids": True,
                "supports_performance_logging": True
            }
        }
        return bridge
    
    @pytest.fixture
    def logging_integration(self, mock_integration_bridge):
        """Create logging framework integration."""
        return LoggingFrameworkIntegration(mock_integration_bridge)
    
    @pytest.mark.asyncio
    async def test_logging_initialization(self, logging_integration):
        """Test logging framework initialization."""
        result = await logging_integration.initialize_logging_integration()
        
        assert result is True
        assert logging_integration.logging_active is True
        assert logging_integration.correlation_id is not None
        assert logging_integration.session_id is not None
    
    def test_logging_status(self, logging_integration):
        """Test logging status."""
        status = logging_integration.get_logging_status()
        
        assert "template_name" in status
        assert "logging_active" in status
        assert "correlation_id" in status
        assert "session_id" in status
        assert "features_available" in status
        assert status["template_name"] == "test_template"
    
    def test_performance_logging(self, logging_integration):
        """Test performance logging."""
        logging_integration.logging_active = True
        logging_integration.logger = Mock()
        logging_integration.logger.info = Mock()
        
        logging_integration.log_performance("test_operation", 1.5, {"extra": "data"})
        
        assert len(logging_integration.performance_log) == 1
        assert logging_integration.performance_log[0]["operation"] == "test_operation"
        assert logging_integration.performance_log[0]["duration"] == 1.5
    
    def test_error_logging(self, logging_integration):
        """Test error logging."""
        logging_integration.logging_active = True
        logging_integration.logger = Mock()
        logging_integration.logger.error = Mock()
        
        test_error = Exception("Test error")
        logging_integration.log_error(test_error, {"context": "test"})
        
        assert len(logging_integration.error_log) == 1
        assert logging_integration.error_log[0]["error_type"] == "Exception"
        assert logging_integration.error_log[0]["error_message"] == "Test error"
    
    def test_info_logging(self, logging_integration):
        """Test info logging."""
        logging_integration.logging_active = True
        logging_integration.logger = Mock()
        logging_integration.logger.info = Mock()
        
        logging_integration.log_info("Test message", key="value")
        
        logging_integration.logger.info.assert_called_once()
    
    def test_performance_log_retrieval(self, logging_integration):
        """Test performance log retrieval."""
        # Add some test performance logs
        logging_integration.performance_log = [
            {"operation": "op1", "duration": 1.0},
            {"operation": "op2", "duration": 2.0},
            {"operation": "op3", "duration": 3.0}
        ]
        
        history = logging_integration.get_performance_log(limit=2)
        
        assert len(history) == 2
        assert history[0]["operation"] == "op2"
        assert history[1]["operation"] == "op3"
    
    def test_error_log_retrieval(self, logging_integration):
        """Test error log retrieval."""
        # Add some test error logs
        logging_integration.error_log = [
            {"error_type": "Error1", "error_message": "Message 1"},
            {"error_type": "Error2", "error_message": "Message 2"}
        ]
        
        errors = logging_integration.get_error_log()
        
        assert len(errors) == 2
        assert errors[0]["error_type"] == "Error1"
        assert errors[1]["error_type"] == "Error2"
    
    def test_config_operations(self, logging_integration):
        """Test configuration operations."""
        new_config = {"log_level": "DEBUG", "log_to_file": True}
        
        logging_integration.update_config(new_config)
        
        config = logging_integration.get_config()
        
        assert config["log_level"] == "DEBUG"
        assert config["log_to_file"] is True


class TestIntegrationScenarios:
    """Test integration scenarios for the complete framework."""
    
    @pytest.fixture
    def mock_page(self):
        """Create mock page."""
        return MockPage()
    
    @pytest.fixture
    def mock_selector_engine(self):
        """Create mock selector engine."""
        return MockSelectorEngine()
    
    @pytest.fixture
    def integration_bridge(self, mock_page, mock_selector_engine):
        """Create integration bridge."""
        return FullIntegrationBridge(
            template_name="test_template",
            page=mock_page,
            selector_engine=mock_selector_engine
        )
    
    @pytest.mark.asyncio
    async def test_complete_integration(self, integration_bridge):
        """Test complete integration scenario."""
        # Initialize bridge
        result = await integration_bridge.initialize()
        assert result is True
        
        # Create browser lifecycle integration
        browser_lifecycle = BrowserLifecycleIntegration(integration_bridge)
        browser_result = await browser_lifecycle.initialize_browser_integration()
        assert browser_result is True
        
        # Create resource monitoring integration
        resource_monitoring = ResourceMonitoringIntegration(integration_bridge)
        with patch('src.sites.base.template.resource_monitoring.psutil'):
            resource_result = await resource_monitoring.initialize_resource_monitoring()
            assert resource_result is True
        
        # Create logging integration
        logging_integration = LoggingFrameworkIntegration(integration_bridge)
        logging_result = await logging_integration.initialize_logging_integration()
        assert logging_result is True
        
        # Test that all integrations are working together
        assert integration_bridge.initialized is True
        assert browser_lifecycle.browser_session_id is not None
        assert resource_monitoring.monitoring_session_id is not None
        assert logging_integration.correlation_id is not None
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, integration_bridge):
        """Test error handling across integrations."""
        await integration_bridge.initialize()
        
        # Create logging integration
        logging_integration = LoggingFrameworkIntegration(integration_bridge)
        await logging_integration.initialize_logging_integration()
        
        # Simulate an error
        test_error = Exception("Integration test error")
        logging_integration.log_error(test_error, {"integration": "test"})
        
        # Verify error was logged
        assert len(logging_integration.error_log) == 1
        assert logging_integration.error_log[0]["error_message"] == "Integration test error"
    
    @pytest.mark.asyncio
    async def test_performance_tracking_integration(self, integration_bridge):
        """Test performance tracking across integrations."""
        await integration_bridge.initialize()
        
        # Create logging integration
        logging_integration = LoggingFrameworkIntegration(integration_bridge)
        await logging_integration.initialize_logging_integration()
        
        # Simulate performance logging
        logging_integration.log_performance("test_operation", 0.5, {"component": "test"})
        
        # Verify performance was logged
        assert len(logging_integration.performance_log) == 1
        assert logging_integration.performance_log[0]["duration"] == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
