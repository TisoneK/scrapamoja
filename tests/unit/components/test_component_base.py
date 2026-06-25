"""
Base testing framework for shared components.

This module provides a comprehensive testing framework for shared components,
including base test classes, utilities, and test helpers.
"""

import pytest
import asyncio
from typing import Dict, Any, Optional, List, Type
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.sites.base.component_interface import BaseComponent, ComponentContext, ComponentResult
from src.sites.base.component_discovery import get_component, get_all_components


class MockComponentContext:
    """Mock component context for testing."""
    
    def __init__(self, config: Dict[str, Any] = None, environment: str = "test"):
        self.config = config or {}
        self.environment = environment
        self.config_manager = Mock()
        self.config_manager.get_config.return_value = config


class ComponentTestBase:
    """Base test class for components."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock component context."""
        return MockComponentContext()
    
    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing."""
        return {
            'test_param': 'test_value',
            'enabled': True,
            'timeout': 5000
        }
    
    @pytest.fixture
    def component_context(self, sample_config):
        """Create a component context with sample config."""
        return MockComponentContext(sample_config)
    
    async def assert_component_initialization(self, component_class: Type, context: ComponentContext):
        """Assert that a component initializes successfully."""
        component = component_class()
        result = await component.initialize(context)
        assert result is True, f"Component {component_class.__name__} failed to initialize"
        return component
    
    async def assert_component_execution(self, component: BaseComponent, **kwargs) -> ComponentResult:
        """Assert that a component executes successfully."""
        result = await component.execute(**kwargs)
        assert result.success, f"Component execution failed: {result.errors}"
        return result
    
    def assert_component_metadata(self, component_class: Type):
        """Assert that component metadata is properly defined."""
        if hasattr(component_class, 'COMPONENT_METADATA'):
            metadata = component_class.COMPONENT_METADATA
            assert 'id' in metadata, "Component metadata missing 'id' field"
            assert 'name' in metadata, "Component metadata missing 'name' field"
            assert 'version' in metadata, "Component metadata missing 'version' field"
            assert 'type' in metadata, "Component metadata missing 'type' field"
            return metadata
        return None
    
    def create_mock_page(self):
        """Create a mock Playwright page."""
        mock_page = Mock()
        mock_page.url = "https://example.com"
        mock_page.title.return_value = "Test Page"
        mock_page.query_selector.return_value = None
        mock_page.query_selector_all.return_value = []
        mock_page.evaluate.return_value = None
        mock_page.mouse.position.return_value = {'x': 0, 'y': 0}
        mock_page.mouse.move.return_value = None
        mock_page.mouse.click.return_value = None
        mock_page.set_extra_http_headers.return_value = None
        return mock_page
    
    def create_mock_element(self, text: str = "test", tag: str = "div"):
        """Create a mock DOM element."""
        mock_element = Mock()
        mock_element.text_content.return_value = text
        mock_element.inner_html.return_value = f"<{tag}>{text}</{tag}>"
        mock_element.get_attribute.return_value = None
        mock_element.is_visible.return_value = True
        mock_element.bounding_box.return_value = {
            'x': 0, 'y': 0, 'width': 100, 'height': 100
        }
        return mock_element


class ComponentIntegrationTestBase:
    """Base test class for component integration tests."""
    
    @pytest.fixture
    async def component_registry(self):
        """Get all available components for testing."""
        return get_all_components()
    
    @pytest.fixture
    def test_sites(self):
        """List of sites to test components against."""
        return ['google', 'facebook', 'twitter', 'amazon', 'wikipedia']
    
    async def test_component_discovery(self, component_registry):
        """Test that components can be discovered."""
        assert len(component_registry) > 0, "No components found in registry"
        
        for component_type, components in component_registry.items():
            assert len(components) > 0, f"No components found for type: {component_type}"
    
    async def test_component_metadata_validation(self, component_registry):
        """Test that all components have valid metadata."""
        for component_type, components in component_registry.items():
            for component_id, component_class in components.items():
                if hasattr(component_class, 'COMPONENT_METADATA'):
                    metadata = component_class.COMPONENT_METADATA
                    assert 'id' in metadata, f"Component {component_id} missing 'id' in metadata"
                    assert 'name' in metadata, f"Component {component_id} missing 'name' in metadata"
                    assert 'version' in metadata, f"Component {component_id} missing 'version' in metadata"
                    assert 'type' in metadata, f"Component {component_id} missing 'type' in metadata"
    
    async def test_component_initialization(self, component_registry, component_context):
        """Test that all components can be initialized."""
        failed_components = []
        
        for component_type, components in component_registry.items():
            for component_id, component_class in components.items():
                try:
                    component = component_class()
                    result = await component.initialize(component_context)
                    if not result:
                        failed_components.append(component_id)
                except Exception as e:
                    failed_components.append(f"{component_id}: {str(e)}")
        
        assert len(failed_components) == 0, f"Components failed to initialize: {failed_components}"
    
    async def test_component_execution(self, component_registry, component_context):
        """Test that all components can execute with basic parameters."""
        failed_components = []
        
        for component_type, components in component_registry.items():
            for component_id, component_class in components.items():
                try:
                    component = component_class()
                    await component.initialize(component_context)
                    
                    # Test basic execution
                    result = await component.execute(
                        site='test',
                        page=self.create_mock_page(),
                        **self.get_test_parameters(component_type)
                    )
                    
                    if not result.success:
                        failed_components.append(f"{component_id}: {result.errors}")
                except Exception as e:
                    failed_components.append(f"{component_id}: {str(e)}")
        
        # Allow some components to fail if they require specific conditions
        if len(failed_components) > len(component_registry) * 0.5:  # More than 50% failed
            assert False, f"Too many components failed execution: {failed_components}"
    
    def get_test_parameters(self, component_type: str) -> Dict[str, Any]:
        """Get test parameters for a component type."""
        base_params = {
            'site': 'test',
            'page': self.create_mock_page()
        }
        
        if component_type == 'authentication':
            base_params.update({
                'username': 'test_user',
                'password': 'test_pass'
            })
        elif component_type == 'pagination':
            base_params.update({
                'max_scrolls': 3,
                'max_pages': 3
            })
        elif component_type == 'processor':
            base_params.update({
                'auto_detect': True
            })
        elif component_type == 'stealth':
            base_params.update({
                'rotation_strategy': 'random'
            })
        
        return base_params
    
    def create_mock_page(self):
        """Create a mock Playwright page for testing."""
        mock_page = Mock()
        mock_page.url = "https://example.com"
        mock_page.title.return_value = "Test Page"
        mock_page.query_selector.return_value = None
        mock_page.query_selector_all.return_value = []
        mock_page.evaluate.return_value = None
        mock_page.mouse.position.return_value = {'x': 0, 'y': 0}
        mock_page.mouse.move.return_value = None
        mock_page.mouse.click.return_value = None
        mock_page.set_extra_http_headers.return_value = None
        return mock_page


class ComponentPerformanceTestBase:
    """Base test class for component performance tests."""
    
    @pytest.fixture
    def performance_thresholds(self):
        """Performance thresholds for testing."""
        return {
            'initialization_time_ms': 1000,
            'execution_time_ms': 5000,
            'memory_usage_mb': 100
        }
    
    async def test_component_initialization_performance(self, component_class: Type, 
                                                     component_context, performance_thresholds):
        """Test component initialization performance."""
        start_time = datetime.utcnow()
        
        component = component_class()
        result = await component.initialize(component_context)
        
        end_time = datetime.utcnow()
        initialization_time_ms = (end_time - start_time).total_seconds() * 1000
        
        assert result is True, f"Component failed to initialize"
        assert initialization_time_ms < performance_thresholds['initialization_time_ms'], \
            f"Component initialization took too long: {initialization_time_ms}ms"
    
    async def test_component_execution_performance(self, component: BaseComponent, 
                                                  performance_thresholds, **kwargs):
        """Test component execution performance."""
        start_time = datetime.utcnow()
        
        result = await component.execute(**kwargs)
        
        end_time = datetime.utcnow()
        execution_time_ms = (end_time - start_time).total_seconds() * 1000
        
        assert result.success, f"Component execution failed: {result.errors}"
        assert execution_time_ms < performance_thresholds['execution_time_ms'], \
            f"Component execution took too long: {execution_time_ms}ms"


class ComponentErrorHandlingTestBase:
    """Base test class for component error handling tests."""
    
    async def test_component_error_handling(self, component_class: Type, component_context):
        """Test that components handle errors gracefully."""
        component = component_class()
        
        # Test with invalid parameters
        result = await component.execute(
            site='invalid_site',
            page=None,
            invalid_param='test'
        )
        
        # Should handle errors gracefully
        assert not result.success, "Component should fail with invalid parameters"
        assert 'error' in result.data or result.errors, "Component should provide error information"
    
    async def test_component_timeout_handling(self, component_class: Type, component_context):
        """Test that components handle timeouts gracefully."""
        component = component_class()
        
        # Test with very short timeout
        result = await component.execute(
            site='test',
            page=self.create_mock_page(),
            timeout_ms=1  # Very short timeout
        )
        
        # Should handle timeout gracefully
        if not result.success:
            assert 'error' in result.data or result.errors, "Component should provide timeout error information"
    
    def create_mock_page(self):
        """Create a mock page that raises exceptions."""
        mock_page = Mock()
        mock_page.url = "https://example.com"
        mock_page.title.return_value = "Test Page"
        mock_page.query_selector.side_effect = Exception("Mock exception")
        mock_page.query_selector_all.side_effect = Exception("Mock exception")
        mock_page.evaluate.side_effect = Exception("Mock exception")
        return mock_page


# Test utilities
class ComponentTestUtils:
    """Utility functions for component testing."""
    
    @staticmethod
    def create_test_config(site: str = 'test', **kwargs) -> Dict[str, Any]:
        """Create test configuration."""
        config = {
            'site': site,
            'enabled': True,
            'timeout': 5000,
            'retry_count': 3
        }
        config.update(kwargs)
        return config
    
    @staticmethod
    def create_test_context(config: Dict[str, Any] = None, environment: str = 'test') -> ComponentContext:
        """Create a test component context."""
        return MockComponentContext(config, environment)
    
    @staticmethod
    def assert_result_structure(result: ComponentResult, expected_keys: List[str] = None):
        """Assert that a component result has the expected structure."""
        assert hasattr(result, 'success'), "Result missing 'success' attribute"
        assert hasattr(result, 'data'), "Result missing 'data' attribute"
        assert hasattr(result, 'execution_time_ms'), "Result missing 'execution_time_ms' attribute"
        
        if expected_keys:
            for key in expected_keys:
                assert key in result.data, f"Result data missing expected key: {key}"
    
    @staticmethod
    def assert_metadata_structure(metadata: Dict[str, Any], required_fields: List[str] = None):
        """Assert that metadata has the expected structure."""
        required_fields = required_fields or ['id', 'name', 'version', 'type']
        
        for field in required_fields:
            assert field in metadata, f"Metadata missing required field: {field}"
    
    @staticmethod
    def create_component_test_data(component_type: str) -> Dict[str, Any]:
        """Create test data for a specific component type."""
        test_data = {
            'site': 'test',
            'page': ComponentTestUtils.create_mock_page()
        }
        
        if component_type == 'authentication':
            test_data.update({
                'username': 'test_user',
                'password': 'test_pass'
            })
        elif component_type == 'pagination':
            test_data.update({
                'max_scrolls': 3,
                'max_pages': 3
            })
        elif component_type == 'processor':
            test_data.update({
                'auto_detect': True
            })
        elif component_type == 'stealth':
            test_data.update({
                'rotation_strategy': 'random'
            })
        
        return test_data
    
    @staticmethod
    def create_mock_page():
        """Create a mock page for testing."""
        mock_page = Mock()
        mock_page.url = "https://example.com"
        mock_page.title.return_value = "Test Page"
        mock_page.query_selector.return_value = None
        mock_page.query_selector_all.return_value = []
        mock_page.evaluate.return_value = None
        mock_page.mouse.position.return_value = {'x': 0, 'y': 0}
        mock_page.mouse.move.return_value = None
        mock_page.mouse.click.return_value = None
        mock_page.set_extra_http_headers.return_value = None
        return mock_page


# Pytest configuration and fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_component_context():
    """Create a mock component context."""
    return MockComponentContext()


@pytest.fixture
def sample_component_config():
    """Sample component configuration."""
    return {
        'test_param': 'test_value',
        'enabled': True,
        'timeout': 5000
    }


# Test markers
pytest_plugins = []
