"""
Unit tests for the plugin system base components.

This module provides comprehensive unit tests for the plugin interface,
registry, and core functionality.
"""

import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any

from src.sites.base.plugin_interface import (
    IPlugin, BasePlugin, PluginMetadata, PluginType, PluginStatus,
    HookType, PluginContext, PluginResult, PluginRegistry,
    register_plugin, get_plugin_registry
)
from src.sites.base.plugin_lifecycle import PluginLifecycleManager
from src.sites.base.plugin_hooks import HookManager, HookExecutionMode


class MockPlugin(BasePlugin):
    """Mock plugin for testing."""
    
    def __init__(self, plugin_id="test_plugin", plugin_type=PluginType.CUSTOM):
        """Initialize mock plugin."""
        super().__init__()
        self._plugin_id = plugin_id
        self._plugin_type = plugin_type
        self._initialized = False
        self._execute_count = 0
        self._execute_results = []
    
    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            id=self._plugin_id,
            name=f"Test Plugin {self._plugin_id}",
            version="1.0.0",
            description="A test plugin for unit testing",
            author="Test Team",
            plugin_type=self._plugin_type,
            hooks=[HookType.BEFORE_SCRAPE, HookType.AFTER_SCRAPE]
        )
    
    async def _on_initialize(self, context: PluginContext) -> bool:
        """Initialize the mock plugin."""
        self._initialized = True
        return True
    
    async def _on_execute(self, context: PluginContext, hook_type: HookType, **kwargs) -> PluginResult:
        """Execute the mock plugin."""
        self._execute_count += 1
        result = PluginResult(
            success=True,
            plugin_id=self._plugin_id,
            hook_type=hook_type,
            data={"execute_count": self._execute_count}
        )
        self._execute_results.append(result)
        return result
    
    async def _on_cleanup(self, context: PluginContext) -> bool:
        """Clean up the mock plugin."""
        self._initialized = False
        return True


class TestPluginMetadata(unittest.TestCase):
    """Test cases for PluginMetadata."""
    
    def test_plugin_metadata_creation(self):
        """Test plugin metadata creation."""
        metadata = PluginMetadata(
            id="test_plugin",
            name="Test Plugin",
            version="1.0.0",
            description="A test plugin",
            author="Test Author",
            plugin_type=PluginType.CUSTOM
        )
        
        self.assertEqual(metadata.id, "test_plugin")
        self.assertEqual(metadata.name, "Test Plugin")
        self.assertEqual(metadata.version, "1.0.0")
        self.assertEqual(metadata.description, "A test plugin")
        self.assertEqual(metadata.author, "Test Author")
        self.assertEqual(metadata.plugin_type, PluginType.CUSTOM)
        self.assertIsInstance(metadata.created_at, datetime)
        self.assertIsInstance(metadata.updated_at, datetime)
    
    def test_plugin_metadata_validation(self):
        """Test plugin metadata validation."""
        # Test missing required fields
        with self.assertRaises(ValueError):
            PluginMetadata(
                id="",  # Empty ID should fail
                name="Test Plugin",
                version="1.0.0",
                author="Test Author",
                plugin_type=PluginType.CUSTOM
            )
        
        with self.assertRaises(ValueError):
            PluginMetadata(
                id="test_plugin",
                name="",  # Empty name should fail
                version="1.0.0",
                author="Test Author",
                plugin_type=PluginType.CUSTOM
            )
        
        with self.assertRaises(ValueError):
            PluginMetadata(
                id="test_plugin",
                name="Test Plugin",
                version="",  # Empty version should fail
                author="Test Author",
                plugin_type=PluginType.CUSTOM
            )
        
        with self.assertRaises(ValueError):
            PluginMetadata(
                id="test_plugin",
                name="Test Plugin",
                version="1.0.0",
                author="",  # Empty author should fail
                plugin_type=PluginType.CUSTOM
            )


class TestPluginContext(unittest.TestCase):
    """Test cases for PluginContext."""
    
    def test_plugin_context_creation(self):
        """Test plugin context creation."""
        context = PluginContext(
            plugin_id="test_plugin",
            plugin_metadata=Mock(),
            framework_context=None,
            configuration={"test": "value"}
        )
        
        self.assertEqual(context.plugin_id, "test_plugin")
        self.assertIsNotNone(context.plugin_metadata)
        self.assertEqual(context.configuration, {"test": "value"})
        self.assertIsInstance(context.execution_id, str)
        self.assertIsInstance(context.start_time, datetime)
    
    def test_plugin_context_metadata(self):
        """Test plugin context metadata operations."""
        context = PluginContext(
            plugin_id="test_plugin",
            plugin_metadata=Mock(),
            framework_context=None
        )
        
        # Test adding metadata
        context.metadata["test_key"] = "test_value"
        self.assertEqual(context.metadata["test_key"], "test_value")
        
        # Test updating metadata
        context.metadata.update({"key1": "value1", "key2": "value2"})
        self.assertEqual(context.metadata["key1"], "value1")
        self.assertEqual(context.metadata["key2"], "value2")


class TestPluginResult(unittest.TestCase):
    """Test cases for PluginResult."""
    
    def test_plugin_result_creation(self):
        """Test plugin result creation."""
        result = PluginResult(
            success=True,
            plugin_id="test_plugin",
            hook_type=HookType.BEFORE_SCRAPE,
            data={"test": "data"}
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.plugin_id, "test_plugin")
        self.assertEqual(result.hook_type, HookType.BEFORE_SCRAPE)
        self.assertEqual(result.data, {"test": "data"})
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.execution_time_ms, 0.0)
        self.assertIsInstance(result.timestamp, str)
    
    def test_plugin_result_with_errors(self):
        """Test plugin result with errors."""
        result = PluginResult(
            success=False,
            plugin_id="test_plugin",
            hook_type=HookType.AFTER_SCRAPE,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"]
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.errors, ["Error 1", "Error 2"])
        self.assertEqual(result.warnings, ["Warning 1"])


class TestBasePlugin(unittest.TestCase):
    """Test cases for BasePlugin."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.plugin = MockPlugin()
        self.context = PluginContext(
            plugin_id="test_plugin",
            plugin_metadata=self.plugin.metadata,
            framework_context=None
        )
    
    def test_base_plugin_initialization(self):
        """Test base plugin initialization."""
        self.assertFalse(self.plugin._initialized)
        self.assertEqual(self.plugin._execute_count, 0)
        self.assertEqual(len(self.plugin._execute_results), 0)
    
    def test_base_plugin_metadata(self):
        """Test base plugin metadata."""
        metadata = self.plugin.metadata
        self.assertEqual(metadata.id, "test_plugin")
        self.assertEqual(metadata.plugin_type, PluginType.CUSTOM)
        self.assertIn(HookType.BEFORE_SCRAPE, metadata.hooks)
        self.assertIn(HookType.AFTER_SCRAPE, metadata.hooks)
    
    def test_base_plugin_initialize(self):
        """Test base plugin initialization."""
        # Test successful initialization
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self.plugin.initialize(self.context)
            )
            self.assertTrue(result)
            self.assertTrue(self.plugin._initialized)
        finally:
            loop.close()
    
    def test_base_plugin_execute(self):
        """Test base plugin execution."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Initialize plugin first
            loop.run_until_complete(self.plugin.initialize(self.context))
            
            # Test execution
            result = loop.run_until_complete(
                self.plugin.execute(self.context, HookType.BEFORE_SCRAPE)
            )
            
            self.assertTrue(result.success)
            self.assertEqual(result.plugin_id, "test_plugin")
            self.assertEqual(result.hook_type, HookType.BEFORE_SCRAPE)
            self.assertEqual(self.plugin._execute_count, 1)
            self.assertEqual(len(self.plugin._execute_results), 1)
        finally:
            loop.close()
    
    def test_base_plugin_cleanup(self):
        """Test base plugin cleanup."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Initialize plugin first
            loop.run_until_complete(self.plugin.initialize(self.context))
            self.assertTrue(self.plugin._initialized)
            
            # Test cleanup
            result = loop.run_until_complete(
                self.plugin.cleanup(self.context)
            )
            
            self.assertTrue(result)
            self.assertFalse(self.plugin._initialized)
        finally:
            loop.close()
    
    def test_base_plugin_hooks(self):
        """Test base plugin hook management."""
        # Test adding hooks
        def test_callback(context, **kwargs):
            return PluginResult(success=True)
        
        self.plugin.add_hook(HookType.BEFORE_SCRAPE, test_callback)
        hooks = self.plugin.get_hooks()
        self.assertEqual(len(hooks), 2)  # One from metadata, one added
        
        # Test removing hooks
        removed = self.plugin.remove_hook(HookType.BEFORE_SCRAPE, test_callback)
        self.assertTrue(removed)
        hooks = self.plugin.get_hooks()
        self.assertEqual(len(hooks), 1)  # Only the one from metadata
    
    def test_base_plugin_telemetry(self):
        """Test base plugin telemetry."""
        telemetry = self.plugin.get_telemetry()
        
        self.assertIn('plugin_id', telemetry)
        self.assertIn('plugin_name', telemetry)
        self.assertIn('plugin_version', telemetry)
        self.assertIn('plugin_type', telemetry)
        self.assertIn('status', telemetry)
        self.assertIn('initialized', telemetry)
        self.assertIn('execution_count', telemetry)
        self.assertIn('total_execution_time_ms', telemetry)
        self.assertIn('error_count', telemetry)
        self.assertIn('hook_count', telemetry)


class TestPluginRegistry(unittest.TestCase):
    """Test cases for PluginRegistry."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = PluginRegistry()
        self.plugin = MockPlugin()
    
    def test_plugin_registry_creation(self):
        """Test plugin registry creation."""
        self.assertEqual(len(self.registry.get_plugins()), 0)
        self.assertEqual(len(self.registry.get_all_metadata()), 0)
    
    def test_plugin_registration(self):
        """Test plugin registration."""
        # Test successful registration
        result = self.registry.register_plugin(self.plugin)
        self.assertTrue(result)
        
        # Check plugin is registered
        registered_plugin = self.registry.get_plugin("test_plugin")
        self.assertIsNotNone(registered_plugin)
        self.assertEqual(registered_plugin.metadata.id, "test_plugin")
        
        # Check metadata is registered
        metadata = self.registry.get_plugin_metadata("test_plugin")
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.id, "test_plugin")
        
        # Test duplicate registration
        result = self.registry.register_plugin(self.plugin)
        self.assertFalse(result)
    
    def test_plugin_unregistration(self):
        """Test plugin unregistration."""
        # Register plugin first
        self.registry.register_plugin(self.plugin)
        
        # Test successful unregistration
        result = self.registry.unregister_plugin("test_plugin")
        self.assertTrue(result)
        
        # Check plugin is unregistered
        registered_plugin = self.registry.get_plugin("test_plugin")
        self.assertIsNone(registered_plugin)
        
        # Check metadata is unregistered
        metadata = self.registry.get_plugin_metadata("test_plugin")
        self.assertIsNone(metadata)
        
        # Test unregistration of non-existent plugin
        result = self.registry.unregister_plugin("non_existent")
        self.assertFalse(result)
    
    def test_plugin_registry_filtering(self):
        """Test plugin registry filtering."""
        # Register plugins of different types
        plugin1 = MockPlugin("plugin1", PluginType.VALIDATION)
        plugin2 = MockPlugin("plugin2", PluginType.MONITORING)
        plugin3 = MockPlugin("plugin3", PluginType.VALIDATION)
        
        self.registry.register_plugin(plugin1)
        self.registry.register_plugin(plugin2)
        self.registry.register_plugin(plugin3)
        
        # Test filtering by type
        validation_plugins = self.registry.get_plugins_by_type(PluginType.VALIDATION)
        self.assertEqual(len(validation_plugins), 2)
        
        monitoring_plugins = self.registry.get_plugins_by_type(PluginType.MONITORING)
        self.assertEqual(len(monitoring_plugins), 1)
        
        custom_plugins = self.registry.get_plugins_by_type(PluginType.CUSTOM)
        self.assertEqual(len(custom_plugins), 0)
    
    def test_plugin_registry_statistics(self):
        """Test plugin registry statistics."""
        # Register some plugins
        plugin1 = MockPlugin("plugin1", PluginType.VALIDATION)
        plugin2 = MockPlugin("plugin2", PluginType.MONITORING)
        
        self.registry.register_plugin(plugin1)
        self.registry.register_plugin(plugin2)
        
        stats = self.registry.get_statistics()
        
        self.assertEqual(stats['total_plugins'], 2)
        self.assertEqual(stats['active_plugins'], 0)  # All inactive by default
        self.assertEqual(stats['error_plugins'], 0)
        self.assertIn('total_executions', stats)
        self.assertIn('total_execution_time_ms', stats)
        self.assertIn('average_execution_time_ms', stats)


class TestPluginIntegration(unittest.TestCase):
    """Integration tests for plugin system components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = PluginRegistry()
        self.lifecycle_manager = PluginLifecycleManager()
        self.hook_manager = HookManager()
        
        # Create test plugins
        self.plugin1 = MockPlugin("plugin1", PluginType.VALIDATION)
        self.plugin2 = MockPlugin("plugin2", PluginType.MONITORING)
    
    def test_plugin_lifecycle_integration(self):
        """Test plugin lifecycle integration with registry."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Register plugins
            self.registry.register_plugin(self.plugin1)
            self.registry.register_plugin(self.plugin2)
            
            # Create context
            context = PluginContext(
                plugin_id="plugin1",
                plugin_metadata=self.plugin1.metadata,
                framework_context=None
            )
            
            # Test initialization through lifecycle manager
            result = loop.run_until_complete(
                self.lifecycle_manager.initialize_plugin("plugin1", context)
            )
            self.assertTrue(result)
            
            # Test activation
            result = loop.run_until_complete(
                self.lifecycle_manager.activate_plugin("plugin1")
            )
            self.assertTrue(result)
            
            # Test execution
            result = loop.run_until_complete(
                self.lifecycle_manager.execute_plugin_hook("plugin1", HookType.BEFORE_SCRAPE)
            )
            self.assertTrue(result.success)
            
            # Test deactivation
            result = loop.run_until_complete(
                self.lifecycle_manager.deactivate_plugin("plugin1")
            )
            self.assertTrue(result)
            
            # Test cleanup
            result = loop.run_until_complete(
                self.lifecycle_manager.cleanup_plugin("plugin1")
            )
            self.assertTrue(result)
            
        finally:
            loop.close()
    
    def test_hook_system_integration(self):
        """Test hook system integration with plugins."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Register plugins
            self.registry.register_plugin(self.plugin1)
            self.registry.register_plugin(self.plugin2)
            
            # Register hooks
            self.hook_manager.register_hook("plugin1", HookType.BEFORE_SCRAPE, 
                                           lambda ctx, **kwargs: PluginResult(
                                               success=True,
                                               plugin_id="plugin1",
                                               hook_type=HookType.BEFORE_SCRAPE,
                                               data={"source": "plugin1"}
                                           ))
            
            self.hook_manager.register_hook("plugin2", HookType.BEFORE_SCRAPE,
                                           lambda ctx, **kwargs: PluginResult(
                                               success=True,
                                               plugin_id="plugin2",
                                               hook_type=HookType.BEFORE_SCRAPE,
                                               data={"source": "plugin2"}
                                           ))
            
            # Test hook execution
            results = loop.run_until_complete(
                self.hook_manager.execute_hooks(HookType.BEFORE_SCRAPE)
            )
            
            self.assertEqual(len(results), 2)
            self.assertTrue(all(r.success for r in results))
            
            # Check data sources
            sources = [r.data.get("source") for r in results]
            self.assertIn("plugin1", sources)
            self.assertIn("plugin2", sources)
            
        finally:
            loop.close()
    
    def test_plugin_error_handling(self):
        """Test plugin error handling."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Create plugin that raises an error
            class ErrorPlugin(BasePlugin):
                @property
                def metadata(self):
                    return PluginMetadata(
                        id="error_plugin",
                        name="Error Plugin",
                        version="1.0.0",
                        author="Test",
                        plugin_type=PluginType.CUSTOM
                    )
                
                async def _on_execute(self, context, hook_type, **kwargs):
                    raise ValueError("Test error")
            
            error_plugin = ErrorPlugin()
            
            # Register and initialize plugin
            self.registry.register_plugin(error_plugin)
            
            context = PluginContext(
                plugin_id="error_plugin",
                plugin_metadata=error_plugin.metadata,
                framework_context=None
            )
            
            # Test error handling
            result = loop.run_until_complete(
                error_plugin.execute(context, HookType.BEFORE_SCRAPE)
            )
            
            self.assertFalse(result.success)
            self.assertIn("Test error", result.errors[0])
            
        finally:
            loop.close()


class TestPluginPerformance(unittest.TestCase):
    """Performance tests for the plugin system."""
    
    def test_plugin_registry_performance(self):
        """Test plugin registry performance with many plugins."""
        registry = PluginRegistry()
        
        # Create many plugins
        plugins = []
        for i in range(100):
            plugin = MockPlugin(f"plugin_{i}")
            plugins.append(plugin)
        
        # Measure registration time
        import time
        start_time = time.time()
        
        for plugin in plugins:
            registry.register_plugin(plugin)
        
        registration_time = time.time() - start_time
        
        # Should complete quickly
        self.assertLess(registration_time, 1.0)  # Less than 1 second
        
        # Measure lookup time
        start_time = time.time()
        
        for i in range(100):
            plugin = registry.get_plugin(f"plugin_{i}")
            self.assertIsNotNone(plugin)
        
        lookup_time = time.time() - start_time
        
        # Should complete quickly
        self.assertLess(lookup_time, 0.1)  # Less than 100ms
        
        # Verify all plugins are registered
        self.assertEqual(len(registry.get_plugins()), 100)
    
    def test_hook_execution_performance(self):
        """Test hook execution performance."""
        hook_manager = HookManager()
        
        # Register many hooks
        for i in range(50):
            hook_manager.register_hook(
                f"plugin_{i}",
                HookType.BEFORE_SCRAPE,
                lambda ctx, **kwargs: PluginResult(success=True, data={"plugin": i})
            )
        
        # Measure execution time
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            start_time = time.time()
            
            results = loop.run_until_complete(
                hook_manager.execute_hooks(HookType.BEFORE_SCRAPE)
            )
            
            execution_time = time.time() - start_time
            
            # Should complete quickly
            self.assertLess(execution_time, 0.5)  # Less than 500ms
            
            # Verify all hooks executed
            self.assertEqual(len(results), 50)
            self.assertTrue(all(r.success for r in results))
            
        finally:
            loop.close()


if __name__ == '__main__':
    unittest.main()
