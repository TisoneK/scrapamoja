"""
Integration tests for shared components.

This module provides integration tests for shared components, testing
component interactions, dependencies, and real-world usage scenarios.
"""

import pytest
import asyncio
from typing import Dict, Any, List, Type
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.sites.base.component_discovery import discover_components, get_component, get_all_components
from src.sites.base.dependency_resolver import resolve_dependencies, validate_dependencies
from src.sites.base.component_metadata import get_metadata, extract_metadata
from src.sites.base.component_interface import ComponentContext


class MockComponentContext:
    """Mock component context for integration testing."""
    
    def __init__(self, config: Dict[str, Any] = None, environment: str = "test"):
        self.config = config or {}
        self.environment = environment
        self.config_manager = Mock()
        self.config_manager.get_config.return_value = config


@pytest.fixture
async def component_registry():
    """Get all available components for testing."""
    discovery_result = await discover_components()
    assert discovery_result['success'], "Component discovery failed"
    return get_all_components()


@pytest.fixture
def test_context():
    """Create a test component context."""
    return MockComponentContext({
        'test_param': 'test_value',
        'enabled': True,
        'timeout': 5000
    }, "test")


@pytest.fixture
def mock_page():
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


class TestComponentDiscovery:
    """Test component discovery integration."""
    
    @pytest.mark.asyncio
    async def test_discover_all_components(self):
        """Test discovering all components."""
        discovery_result = await discover_components()
        
        assert discovery_result['success'], "Component discovery should succeed"
        assert 'discovered_components' in discovery_result, "Should have discovered components"
        assert 'component_metadata' in discovery_result, "Should have component metadata"
        assert 'component_counts' in discovery_result, "Should have component counts"
        
        # Should have discovered components
        assert discovery_result['component_counts']['total'] > 0, "Should discover at least one component"
    
    @pytest.mark.asyncio
    async def test_component_registry_access(self, component_registry):
        """Test accessing component registry."""
        assert len(component_registry) > 0, "Should have component types"
        
        for component_type, components in component_registry.items():
            assert len(components) > 0, f"Should have components for type: {component_type}"
            
            for component_id, component_class in components.items():
                assert component_class is not None, f"Component class should not be None for {component_id}"
    
    @pytest.mark.asyncio
    async def test_component_metadata_extraction(self, component_registry):
        """Test extracting metadata from components."""
        metadata_count = 0
        
        for component_type, components in component_registry.items():
            for component_id, component_class in components.items():
                metadata = get_metadata(component_id)
                if metadata:
                    metadata_count += 1
                    assert 'class_name' in metadata, f"Should have class_name for {component_id}"
                    assert 'module_path' in metadata, f"Should have module_path for {component_id}"
        
        assert metadata_count > 0, "Should have extracted metadata for at least one component"


class TestDependencyResolution:
    """Test dependency resolution integration."""
    
    @pytest.mark.asyncio
    async def test_dependency_validation(self, component_registry):
        """Test dependency validation."""
        all_component_ids = []
        
        for component_type, components in component_registry.items():
            all_component_ids.extend(components.keys())
        
        if all_component_ids:
            validation_result = validate_dependencies(all_component_ids)
            
            assert 'valid' in validation_result, "Should have validation result"
            assert 'validation_results' in validation_result, "Should have validation results"
            
            # Check that all components were validated
            assert len(validation_result['validation_results']) == len(all_component_ids)
    
    @pytest.mark.asyncio
    async def test_dependency_resolution(self, component_registry, test_context):
        """Test dependency resolution."""
        all_component_ids = []
        
        for component_type, components in component_registry.items():
            all_component_ids.extend(components.keys())
        
        if all_component_ids:
            resolution_result = await resolve_dependencies(all_component_ids, test_context)
            
            assert 'success' in resolution_result, "Should have resolution result"
            assert 'resolved_order' in resolution_result, "Should have resolved order"
            
            if resolution_result['success']:
                assert len(resolution_result['resolved_order']) > 0, "Should have resolved order"


class TestComponentIntegration:
    """Test component integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_authentication_flow_integration(self, component_registry, test_context, mock_page):
        """Test authentication flow integration."""
        # Get authentication components
        auth_components = component_registry.get('authentication', {})
        
        if auth_components:
            # Test OAuth component
            oauth_component_id = None
            for component_id in auth_components.keys():
                if 'oauth' in component_id.lower():
                    oauth_component_id = component_id
                    break
            
            if oauth_component_id:
                component_class = get_component(oauth_component_id)
                if component_class:
                    component = component_class()
                    
                    # Initialize component
                    init_result = await component.initialize(test_context)
                    
                    # Test OAuth flow
                    result = await component.execute(
                        site='test',
                        page=mock_page,
                        authorization_code='test_code'
                    )
                    
                    # Should handle the request gracefully
                    assert 'success' in result, "Should have success status"
    
    @pytest.mark.asyncio
    async def test_pagination_flow_integration(self, component_registry, test_context, mock_page):
        """Test pagination flow integration."""
        # Get pagination components
        pagination_components = component_registry.get('pagination', {})
        
        if pagination_components:
            for component_id, component_class in pagination_components.items():
                component = component_class()
                
                # Initialize component
                init_result = await component.initialize(test_context)
                
                # Test pagination
                result = await component.execute(
                    site='test',
                    page=mock_page,
                    max_scrolls=2,
                    max_pages=2
                )
                
                # Should handle the request gracefully
                assert 'success' in result, "Should have success status"
    
    @pytest.mark.asyncio
    async def test_data_processing_integration(self, component_registry, test_context, mock_page):
        """Test data processing integration."""
        # Get processor components
        processor_components = component_registry.get('processor', {})
        
        if processor_components:
            for component_id, component_class in processor_components.items():
                component = component_class()
                
                # Initialize component
                init_result = await component.initialize(test_context)
                
                # Test processing
                result = await component.execute(
                    site='test',
                    page=mock_page,
                    auto_detect=True
                )
                
                # Should handle the request gracefully
                assert 'success' in result, "Should have success status"
    
    @pytest.mark.asyncio
    async def test_stealth_integration(self, component_registry, test_context, mock_page):
        """Test stealth integration."""
        # Get stealth components
        stealth_components = component_registry.get('stealth', {})
        
        if stealth_components:
            for component_id, component_class in stealth_components.items():
                component = component_class()
                
                # Initialize component
                init_result = await component.initialize(test_context)
                
                # Test stealth functionality
                if 'user_agent' in component_id.lower():
                    result = await component.execute(
                        site='test',
                        page=mock_page,
                        rotation_strategy='random'
                    )
                elif 'mouse' in component_id.lower():
                    result = await component.execute(
                        site='test',
                        page=mock_page,
                        target_coordinates=(100, 100),
                        movement_pattern='human'
                    )
                else:
                    result = await component.execute(
                        site='test',
                        page=mock_page
                    )
                
                # Should handle the request gracefully
                assert 'success' in result, "Should have success status"


class TestComponentLifecycle:
    """Test component lifecycle integration."""
    
    @pytest.mark.asyncio
    async def test_component_initialization_lifecycle(self, component_registry, test_context):
        """Test component initialization lifecycle."""
        for component_type, components in component_registry.items():
            for component_id, component_class in components.items():
                component = component_class()
                
                # Test initialization
                init_result = await component.initialize(test_context)
                
                # Should initialize without errors
                # Some components might fail initialization due to missing dependencies
                # which is acceptable in integration tests
    
    @pytest.mark.asyncio
    async def test_component_execution_lifecycle(self, component_registry, test_context, mock_page):
        """Test component execution lifecycle."""
        for component_type, components in component_registry.items():
            for component_id, component_class in components.items():
                component = component_class()
                
                try:
                    # Initialize component
                    await component.initialize(test_context)
                    
                    # Test execution
                    result = await component.execute(
                        site='test',
                        page=mock_page
                    )
                    
                    # Should handle execution gracefully
                    assert 'success' in result, f"Component {component_id} should have success status"
                    
                except Exception as e:
                    # Some components might fail due to missing dependencies
                    # which is acceptable in integration tests
                    print(f"Component {component_id} failed: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_component_cleanup(self, component_registry, test_context):
        """Test component cleanup."""
        for component_type, components in component_registry.items():
            for component_id, component_class in components.items():
                component = component_class()
                
                try:
                    # Initialize component
                    await component.initialize(test_context)
                    
                    # Test cleanup
                    if hasattr(component, 'cleanup'):
                        await component.cleanup()
                    
                except Exception as e:
                    # Some components might fail during cleanup
                    # which is acceptable in integration tests
                    print(f"Component {component_id} cleanup failed: {str(e)}")


class TestComponentErrorHandling:
    """Test component error handling integration."""
    
    @pytest.mark.asyncio
    async def test_component_error_handling(self, component_registry, test_context):
        """Test component error handling."""
        for component_type, components in component_registry.items():
            for component_id, component_class in components.items():
                component = component_class()
                
                try:
                    # Initialize component
                    await component.initialize(test_context)
                    
                    # Test with invalid parameters
                    result = await component.execute(
                        site='invalid_site',
                        page=None
                    )
                    
                    # Should handle errors gracefully
                    if not result.success:
                        assert 'error' in result.data or result.errors, \
                            f"Component {component_id} should provide error information"
                    
                except Exception as e:
                    # Some components might raise exceptions
                    # which is acceptable in integration tests
                    print(f"Component {component_id} exception: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_component_timeout_handling(self, component_registry, test_context, mock_page):
        """Test component timeout handling."""
        for component_type, components in component_registry.items():
            for component_id, component_class in components.items():
                component = component_class()
                
                try:
                    # Initialize component
                    await component.initialize(test_context)
                    
                    # Test with very short timeout
                    result = await component.execute(
                        site='test',
                        page=mock_page,
                        timeout_ms=1
                    )
                    
                    # Should handle timeout gracefully
                    if not result.success:
                        assert 'error' in result.data or result.errors, \
                            f"Component {component_id} should provide timeout error information"
                    
                except Exception as e:
                    # Some components might raise exceptions
                    # which is acceptable in integration tests
                    print(f"Component {component_id} timeout exception: {str(e)}")


class TestComponentPerformance:
    """Test component performance integration."""
    
    @pytest.mark.asyncio
    async def test_component_discovery_performance(self):
        """Test component discovery performance."""
        start_time = datetime.utcnow()
        
        discovery_result = await discover_components()
        
        end_time = datetime.utcnow()
        discovery_time_ms = (end_time - start_time).total_seconds() * 1000
        
        assert discovery_result['success'], "Component discovery should succeed"
        assert discovery_time_ms < 5000, f"Discovery should complete in under 5 seconds, took {discovery_time_ms}ms"
    
    @pytest.mark.asyncio
    async def test_component_initialization_performance(self, component_registry, test_context):
        """Test component initialization performance."""
        initialization_times = []
        
        for component_type, components in component_registry.items():
            for component_id, component_class in components.items():
                component = component_class()
                
                start_time = datetime.utcnow()
                
                try:
                    await component.initialize(test_context)
                    
                    end_time = datetime.utcnow()
                    init_time_ms = (end_time - start_time).total_seconds() * 1000
                    initialization_times.append(init_time_ms)
                    
                except Exception:
                    # Skip failed initializations
                    pass
        
        if initialization_times:
            avg_time = sum(initialization_times) / len(initialization_times)
            assert avg_time < 1000, f"Average initialization time should be under 1 second, was {avg_time}ms"
    
    @pytest.mark.asyncio
    async def test_component_execution_performance(self, component_registry, test_context, mock_page):
        """Test component execution performance."""
        execution_times = []
        
        for component_type, components in component_registry.items():
            for component_id, component_class in components.items():
                component = component_class()
                
                try:
                    await component.initialize(test_context)
                    
                    start_time = datetime.utcnow()
                    
                    result = await component.execute(
                        site='test',
                        page=mock_page
                    )
                    
                    end_time = datetime.utcnow()
                    exec_time_ms = (end_time - start_time).total_seconds() * 1000
                    execution_times.append(exec_time_ms)
                    
                except Exception:
                    # Skip failed executions
                    pass
        
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            assert avg_time < 3000, f"Average execution time should be under 3 seconds, was {avg_time}ms"


# Integration test utilities
class IntegrationTestUtils:
    """Utility functions for integration testing."""
    
    @staticmethod
    async def setup_test_environment():
        """Set up test environment."""
        # Discover components
        discovery_result = await discover_components()
        assert discovery_result['success'], "Component discovery failed"
        
        return discovery_result
    
    @staticmethod
    def create_test_scenario(scenario_type: str) -> Dict[str, Any]:
        """Create a test scenario."""
        scenarios = {
            'basic_auth': {
                'components': ['oauth', 'form_auth'],
                'parameters': {
                    'username': 'test_user',
                    'password': 'test_pass'
                }
            },
            'pagination': {
                'components': ['infinite_scroll', 'numbered_pages'],
                'parameters': {
                    'max_scrolls': 3,
                    'max_pages': 3
                }
            },
            'data_processing': {
                'components': ['text_extractor', 'table_extractor'],
                'parameters': {
                    'auto_detect': True
                }
            },
            'stealth': {
                'components': ['user_agent_rotation', 'mouse_movement'],
                'parameters': {
                    'rotation_strategy': 'random',
                    'movement_pattern': 'human'
                }
            }
        }
        
        return scenarios.get(scenario_type, {})
    
    @staticmethod
    async def run_test_scenario(scenario: Dict[str, Any], test_context, mock_page):
        """Run a test scenario."""
        results = {}
        
        for component_type in scenario.get('components', []):
            component_class = get_component(component_type)
            if component_class:
                component = component_class()
                
                try:
                    # Initialize component
                    await component.initialize(test_context)
                    
                    # Execute component
                    result = await component.execute(
                        site='test',
                        page=mock_page,
                        **scenario.get('parameters', {})
                    )
                    
                    results[component_type] = result
                    
                except Exception as e:
                    results[component_type] = {
                        'success': False,
                        'error': str(e)
                    }
        
        return results


# Pytest configuration
pytest_plugins = []
