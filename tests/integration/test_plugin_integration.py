"""
Integration tests for the plugin system.

This module provides comprehensive integration tests for the complete plugin
system, testing the interaction between different components.
"""

import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List

from src.sites.base.plugin_interface import (
    IPlugin, BasePlugin, PluginMetadata, PluginType, PluginStatus,
    HookType, PluginContext, PluginResult, PluginRegistry,
    register_plugin, get_plugin_registry
)
from src.sites.base.plugin_discovery import PluginDiscovery, DiscoverySource
from src.sites.base.plugin_lifecycle import PluginLifecycleManager
from src.sites.base.plugin_hooks import HookManager, HookExecutionMode
from src.sites.base.plugin_permissions import PluginManager, PermissionType, PermissionLevel
from src.sites.base.plugin_sandbox import PluginSandbox, SandboxConfig, SandboxType, SecurityLevel
from src.sites.base.plugin_config import PluginConfigManager, ConfigScope, ConfigFormat
from src.sites.base.plugin_compatibility import PluginCompatibilityChecker, CompatibilityStatus
from src.sites.base.plugin_error_handling import PluginErrorHandler, ErrorSeverity
from src.sites.base.plugin_telemetry import PluginTelemetry, TelemetryLevel


class TestValidationPlugin(BasePlugin):
    """Test validation plugin for integration testing."""
    
    def __init__(self):
        super().__init__()
        self.validation_results = []
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="test_validation_plugin",
            name="Test Validation Plugin",
            version="1.0.0",
            description="Test validation plugin",
            author="Test Team",
            plugin_type=PluginType.VALIDATION,
            permissions=["data_access"],
            hooks=[HookType.AFTER_EXTRACT]
        )
    
    async def _on_execute(self, context: PluginContext, hook_type: HookType, **kwargs) -> PluginResult:
        extracted_data = kwargs.get('extracted_data', {})
        
        # Simple validation
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        if not extracted_data:
            validation_result['valid'] = False
            validation_result['errors'].append("No data to validate")
        
        if 'title' in extracted_data and not extracted_data['title']:
            validation_result['valid'] = False
            validation_result['errors'].append("Title is empty")
        
        self.validation_results.append(validation_result)
        
        return PluginResult(
            success=validation_result['valid'],
            plugin_id=self.metadata.id,
            hook_type=hook_type,
            data=validation_result
        )


class TestMonitoringPlugin(BasePlugin):
    """Test monitoring plugin for integration testing."""
    
    def __init__(self):
        super().__init__()
        self.monitoring_data = []
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="test_monitoring_plugin",
            name="Test Monitoring Plugin",
            version="1.0.0",
            description="Test monitoring plugin",
            author="Test Team",
            plugin_type=PluginType.MONITORING,
            permissions=["system_access"],
            hooks=[HookType.BEFORE_SCRAPE, HookType.AFTER_SCRAPE]
        )
    
    async def _on_execute(self, context: PluginContext, hook_type: HookType, **kwargs) -> PluginResult:
        monitoring_data = {
            'hook_type': hook_type.value,
            'timestamp': datetime.utcnow().isoformat(),
            'plugin_id': self.metadata.id
        }
        
        if hook_type == HookType.AFTER_SCRAPE:
            monitoring_data['execution_time_ms'] = kwargs.get('execution_time_ms', 0)
            monitoring_data['items_extracted'] = len(kwargs.get('scrape_results', {}))
        
        self.monitoring_data.append(monitoring_data)
        
        return PluginResult(
            success=True,
            plugin_id=self.metadata.id,
            hook_type=hook_type,
            data=monitoring_data
        )


class TestPluginSystemIntegration(unittest.TestCase):
    """Integration tests for the complete plugin system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = PluginRegistry()
        self.discovery = PluginDiscovery()
        self.lifecycle_manager = PluginLifecycleManager()
        self.hook_manager = HookManager()
        self.permission_manager = PluginManager()
        self.sandbox = PluginSandbox(SandboxConfig(
            sandbox_type=SandboxType.MEMORY,
            security_level=SecurityLevel.STANDARD
        ))
        self.config_manager = PluginConfigManager()
        self.compatibility_checker = PluginCompatibilityChecker()
        self.error_handler = PluginErrorHandler()
        self.telemetry = PluginTelemetry(TelemetryLevel.STANDARD)
        
        # Test plugins
        self.validation_plugin = TestValidationPlugin()
        self.monitoring_plugin = TestMonitoringPlugin()
    
    def test_complete_plugin_lifecycle(self):
        """Test complete plugin lifecycle from discovery to execution."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Step 1: Register plugins
            self.registry.register_plugin(self.validation_plugin)
            self.registry.register_plugin(self.monitoring_plugin)
            
            # Verify registration
            self.assertEqual(len(self.registry.get_plugins()), 2)
            
            # Step 2: Check compatibility
            validation_compatibility = self.compatibility_checker.check_plugin_compatibility("test_validation_plugin")
            monitoring_compatibility = self.compatibility_checker.check_plugin_compatibility("test_monitoring_plugin")
            
            self.assertEqual(validation_compatibility.status, CompatibilityStatus.COMPATIBLE)
            self.assertEqual(monitoring_compatibility.status, CompatibilityStatus.COMPATIBLE)
            
            # Step 3: Initialize plugins
            validation_context = PluginContext(
                plugin_id="test_validation_plugin",
                plugin_metadata=self.validation_plugin.metadata,
                framework_context=None,
                configuration={}
            )
            
            monitoring_context = PluginContext(
                plugin_id="test_monitoring_plugin",
                plugin_metadata=self.monitoring_plugin.metadata,
                framework_context=None,
                configuration={}
            )
            
            validation_init = loop.run_until_complete(
                self.lifecycle_manager.initialize_plugin("test_validation_plugin", validation_context)
            )
            monitoring_init = loop.run_until_complete(
                self.lifecycle_manager.initialize_plugin("test_monitoring_plugin", monitoring_context)
            )
            
            self.assertTrue(validation_init)
            self.assertTrue(monitoring_init)
            
            # Step 4: Activate plugins
            validation_active = loop.run_until_complete(
                self.lifecycle_manager.activate_plugin("test_validation_plugin")
            )
            monitoring_active = loop.run_until_complete(
                self.lifecycle_manager.activate_plugin("test_monitoring_plugin")
            )
            
            self.assertTrue(validation_active)
            self.assertTrue(monitoring_active)
            
            # Step 5: Execute hooks
            before_scrape_results = loop.run_until_complete(
                self.hook_manager.execute_hooks(HookType.BEFORE_SCRAPE)
            )
            
            # Only monitoring plugin should respond to BEFORE_SCRAPE
            self.assertEqual(len(before_scrape_results), 1)
            self.assertEqual(before_scrape_results[0].plugin_id, "test_monitoring_plugin")
            
            # Step 6: Execute extraction hooks
            test_data = {
                'title': 'Test Article',
                'content': 'Test content',
                'url': 'https://example.com'
            }
            
            after_extract_results = loop.run_until_complete(
                self.hook_manager.execute_hooks(HookType.AFTER_EXTRACT, extracted_data=test_data)
            )
            
            # Only validation plugin should respond to AFTER_EXTRACT
            self.assertEqual(len(after_extract_results), 1)
            self.assertEqual(after_extract_results[0].plugin_id, "test_validation_plugin")
            self.assertTrue(after_extract_results[0].success)
            
            # Step 7: Cleanup plugins
            validation_cleanup = loop.run_until_complete(
                self.lifecycle_manager.cleanup_plugin("test_validation_plugin")
            )
            monitoring_cleanup = loop.run_until_complete(
                self.lifecycle_manager.cleanup_plugin("test_monitoring_plugin")
            )
            
            self.assertTrue(validation_cleanup)
            self.assertTrue(monitoring_cleanup)
            
        finally:
            loop.close()
    
    def test_plugin_configuration_integration(self):
        """Test plugin configuration management integration."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Register plugin
            self.registry.register_plugin(self.validation_plugin)
            
            # Create configuration source
            from src.sites.base.plugin_config import ConfigSource
            config_source = ConfigSource(
                source_id="test_config",
                source_type=ConfigFormat.JSON,
                source_data={
                    "plugin": {
                        "test_validation_plugin": {
                            "enabled": True,
                            "strict_mode": True,
                            "custom_rules": {
                                "title": {
                                    "pattern": "^.+$",
                                    "required": True,
                                    "message": "Title cannot be empty"
                                }
                            }
                        }
                    }
                }
            )
            
            # Add configuration source
            self.config_manager.add_config_source(config_source)
            
            # Load configuration
            config_loaded = loop.run_until_complete(
                self.config_manager.load_plugin_config("test_validation_plugin")
            )
            
            self.assertTrue(config_loaded)
            
            # Get configuration
            config = self.config_manager.get_plugin_config("test_validation_plugin")
            
            self.assertIsNotNone(config)
            self.assertTrue(config.get("enabled", False))
            self.assertTrue(config.get("strict_mode", False))
            self.assertIn("custom_rules", config)
            
            # Initialize plugin with configuration
            context = PluginContext(
                plugin_id="test_validation_plugin",
                plugin_metadata=self.validation_plugin.metadata,
                framework_context=None,
                configuration=config
            )
            
            init_result = loop.run_until_complete(
                self.validation_plugin.initialize(context)
            )
            
            self.assertTrue(init_result)
            
            # Test validation with strict mode
            test_data = {'title': '', 'content': 'Test'}
            result = loop.run_until_complete(
                self.validation_plugin.execute(context, HookType.AFTER_EXTRACT, extracted_data=test_data)
            )
            
            self.assertFalse(result.success)
            self.assertIn("Title is empty", result.data.get('errors', []))
            
        finally:
            loop.close()
    
    def test_plugin_permission_integration(self):
        """Test plugin permission system integration."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Register plugin
            self.registry.register_plugin(self.validation_plugin)
            
            # Check permissions
            has_data_access = self.permission_manager.has_permission("test_validation_plugin", "data_access")
            has_system_access = self.permission_manager.has_permission("test_validation_plugin", "system_access")
            
            self.assertTrue(has_data_access)
            self.assertFalse(has_system_access)
            
            # Request additional permission
            request_id = self.permission_manager.request_permission(
                "test_validation_plugin",
                "system_access",
                "Need system access for advanced validation"
            )
            
            self.assertIsNotNone(request_id)
            
            # Approve permission
            approval_result = loop.run_until_complete(
                self.permission_manager.approve_permission(request_id, True, "Testing approval")
            )
            
            self.assertTrue(approval_result)
            
            # Check permission again
            has_system_access = self.permission_manager.has_permission("test_validation_plugin", "system_access")
            self.assertTrue(has_system_access)
            
            # Get permission status
            status = self.permission_manager.get_permission_status("test_validation_plugin", "system_access")
            self.assertTrue(status.get("granted", False))
            
        finally:
            loop.close()
    
    def test_plugin_error_handling_integration(self):
        """Test plugin error handling integration."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Create plugin that raises errors
            class ErrorPlugin(BasePlugin):
                @property
                def metadata(self):
                    return PluginMetadata(
                        id="error_plugin",
                        name="Error Plugin",
                        version="1.0.0",
                        author="Test",
                        plugin_type=PluginType.CUSTOM,
                        hooks=[HookType.BEFORE_SCRAPE]
                    )
                
                async def _on_execute(self, context, hook_type, **kwargs):
                    raise ValueError("Test error for error handling")
            
            error_plugin = ErrorPlugin()
            self.registry.register_plugin(error_plugin)
            
            # Initialize plugin
            context = PluginContext(
                plugin_id="error_plugin",
                plugin_metadata=error_plugin.metadata,
                framework_context=None
            )
            
            init_result = loop.run_until_complete(error_plugin.initialize(context))
            self.assertTrue(init_result)
            
            # Execute plugin (should handle error)
            result = loop.run_until_complete(
                self.lifecycle_manager.execute_plugin_hook("error_plugin", HookType.BEFORE_SCRAPE)
            )
            
            self.assertFalse(result.success)
            self.assertIn("Test error for error handling", result.errors[0])
            
            # Check error was recorded
            errors = self.error_handler.get_plugin_errors("error_plugin")
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0].error_type, "ValueError")
            self.assertEqual(errors[0].severity, ErrorSeverity.MEDIUM)
            
            # Generate error report
            report = self.error_handler.generate_error_report("error_plugin")
            self.assertEqual(report.plugin_id, "error_plugin")
            self.assertEqual(report.error_count, 1)
            
        finally:
            loop.close()
    
    def test_plugin_telemetry_integration(self):
        """Test plugin telemetry integration."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Register plugins
            self.registry.register_plugin(self.validation_plugin)
            self.registry.register_plugin(self.monitoring_plugin)
            
            # Initialize plugins
            validation_context = PluginContext(
                plugin_id="test_validation_plugin",
                plugin_metadata=self.validation_plugin.metadata,
                framework_context=None
            )
            
            monitoring_context = PluginContext(
                plugin_id="test_monitoring_plugin",
                plugin_metadata=self.monitoring_plugin.metadata,
                framework_context=None
            )
            
            loop.run_until_complete(
                self.validation_plugin.initialize(validation_context)
            )
            loop.run_until_complete(
                self.monitoring_plugin.initialize(monitoring_context)
            )
            
            # Record some metrics
            from src.sites.base.plugin_telemetry import record_metric, record_execution
            
            record_metric("test_validation_plugin", "test_counter", 1)
            record_metric("test_monitoring_plugin", "test_gauge", 42.5)
            
            record_execution("test_validation_plugin", 100.0, True)
            record_execution("test_monitoring_plugin", 50.0, True)
            
            # Get metrics
            validation_metrics = self.telemetry.get_metrics("test_validation_plugin")
            monitoring_metrics = self.telemetry.get_metrics("test_monitoring_plugin")
            
            self.assertGreater(len(validation_metrics), 0)
            self.assertGreater(len(monitoring_metrics), 0)
            
            # Get performance metrics
            validation_perf = self.telemetry.get_performance_metrics("test_validation_plugin")
            monitoring_perf = self.telemetry.get_performance_metrics("test_monitoring_plugin")
            
            self.assertIsNotNone(validation_perf)
            self.assertIsNotNone(monitoring_perf)
            self.assertEqual(validation_perf.execution_count, 1)
            self.assertEqual(monitoring_perf.execution_count, 1)
            
            # Generate telemetry report
            report = self.telemetry.generate_report("test_validation_plugin")
            self.assertEqual(report.plugin_id, "test_validation_plugin")
            self.assertIsNotNone(report.performance_metrics)
            self.assertIsNotNone(report.health_metrics)
            
        finally:
            loop.close()
    
    def test_plugin_sandbox_integration(self):
        """Test plugin sandbox integration."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Register plugin
            self.registry.register_plugin(self.validation_plugin)
            
            # Create sandbox context
            context = PluginContext(
                plugin_id="test_validation_plugin",
                plugin_metadata=self.validation_plugin.metadata,
                framework_context=None
            )
            
            # Execute plugin in sandbox
            result = loop.run_until_complete(
                self.sandbox.execute_plugin(self.validation_plugin, context, HookType.AFTER_EXTRACT, 
                                           extracted_data={'title': 'Test'})
            )
            
            self.assertTrue(result.success)
            self.assertEqual(result.plugin_id, "test_validation_plugin")
            self.assertGreater(result.execution_time_ms, 0)
            
            # Check sandbox statistics
            stats = self.sandbox.get_statistics()
            self.assertGreater(stats['total_executions'], 0)
            self.assertGreater(stats['successful_executions'], 0)
            
        finally:
            loop.close()
    
    def test_plugin_discovery_integration(self):
        """Test plugin discovery integration."""
        # Create temporary plugin file
        import tempfile
        import os
        
        plugin_code = '''
from src.sites.base.plugin_interface import BasePlugin, PluginMetadata, PluginType, HookType, PluginResult, PluginContext

class DiscoveredPlugin(BasePlugin):
    @property
    def metadata(self):
        return PluginMetadata(
            id="discovered_plugin",
            name="Discovered Plugin",
            version="1.0.0",
            author="Test",
            plugin_type=PluginType.CUSTOM,
            hooks=[HookType.BEFORE_SCRAPE]
        )
    
    async def _on_execute(self, context, hook_type, **kwargs):
        return PluginResult(success=True, plugin_id="discovered_plugin", hook_type=hook_type)
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(plugin_code)
            plugin_file = f.name
        
        try:
            # Add discovery path
            temp_dir = os.path.dirname(plugin_file)
            self.discovery.add_discovery_path(temp_dir)
            
            # Discover plugins
            result = self.discovery.discover_plugins([DiscoverySource.FILE_SYSTEM])
            
            self.assertTrue(result.success)
            self.assertGreater(len(result.discovered_plugins), 0)
            
            # Get discovered plugin info
            discovered_plugins = self.discovery.get_discovered_plugins()
            self.assertIn("discovered_plugin", discovered_plugins)
            
            # Register discovered plugin
            plugin_info = discovered_plugins["discovered_plugin"]
            plugin = plugin_info.plugin_class()
            self.registry.register_plugin(plugin)
            
            # Verify registration
            registered_plugin = self.registry.get_plugin("discovered_plugin")
            self.assertIsNotNone(registered_plugin)
            
        finally:
            # Clean up
            os.unlink(plugin_file)
    
    def test_plugin_system_end_to_end(self):
        """Test complete plugin system end-to-end workflow."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Step 1: Discover and register plugins
            self.registry.register_plugin(self.validation_plugin)
            self.registry.register_plugin(self.monitoring_plugin)
            
            # Step 2: Configure permissions
            self.permission_manager.request_permission("test_validation_plugin", "data_access", "Testing")
            self.permission_manager.approve_permission(
                self.permission_manager.get_plugin_requests("test_validation_plugin")[0].request_id,
                True,
                "Auto-approved for testing"
            )
            
            # Step 3: Configure plugins
            from src.sites.base.plugin_config import ConfigSource, ConfigFormat
            config_source = ConfigSource(
                source_id="test_config",
                source_type=ConfigFormat.JSON,
                source_data={
                    "plugin": {
                        "test_validation_plugin": {"enabled": True},
                        "test_monitoring_plugin": {"enabled": True}
                    }
                }
            )
            self.config_manager.add_config_source(config_source)
            
            loop.run_until_complete(
                self.config_manager.load_plugin_config("test_validation_plugin")
            )
            loop.run_until_complete(
                self.config_manager.load_plugin_config("test_monitoring_plugin")
            )
            
            # Step 4: Initialize and activate plugins
            validation_context = PluginContext(
                plugin_id="test_validation_plugin",
                plugin_metadata=self.validation_plugin.metadata,
                framework_context=None,
                configuration=self.config_manager.get_plugin_config("test_validation_plugin")
            )
            
            monitoring_context = PluginContext(
                plugin_id="test_monitoring_plugin",
                plugin_metadata=self.monitoring_plugin.metadata,
                framework_context=None,
                configuration=self.config_manager.get_plugin_config("test_monitoring_plugin")
            )
            
            self.lifecycle_manager.initialize_plugin("test_validation_plugin", validation_context)
            self.lifecycle_manager.initialize_plugin("test_monitoring_plugin", monitoring_context)
            
            self.lifecycle_manager.activate_plugin("test_validation_plugin")
            self.lifecycle_manager.activate_plugin("test_monitoring_plugin")
            
            # Step 5: Execute scraping workflow
            # Before scrape
            before_results = loop.run_until_complete(
                self.hook_manager.execute_hooks(HookType.BEFORE_SCRAPE)
            )
            
            # Simulate scraping
            test_data = {'title': 'Test Article', 'content': 'Test content'}
            
            # After extract
            after_results = loop.run_until_complete(
                self.hook_manager.execute_hooks(HookType.AFTER_EXTRACT, extracted_data=test_data)
            )
            
            # Step 6: Verify results
            self.assertEqual(len(before_results), 1)  # Only monitoring plugin
            self.assertEqual(len(after_results), 1)  # Only validation plugin
            
            self.assertTrue(before_results[0].success)
            self.assertTrue(after_results[0].success)
            
            # Step 7: Check telemetry
            validation_metrics = self.telemetry.get_performance_metrics("test_validation_plugin")
            monitoring_metrics = self.telemetry.get_performance_metrics("test_monitoring_plugin")
            
            self.assertIsNotNone(validation_metrics)
            self.assertIsNotNone(monitoring_metrics)
            
            # Step 8: Cleanup
            self.lifecycle_manager.cleanup_plugin("test_validation_plugin")
            self.lifecycle_manager.cleanup_plugin("test_monitoring_plugin")
            
            # Step 9: Generate final reports
            compatibility_report = self.compatibility_checker.check_all_plugins_compatibility()
            error_report = self.error_handler.generate_error_report()
            telemetry_report = self.telemetry.generate_report()
            
            self.assertEqual(len(compatibility_report), 2)  # Both plugins
            self.assertEqual(error_report.error_count, 0)  # No errors
            self.assertIsNotNone(telemetry_report.performance_metrics)
            
        finally:
            loop.close()


class TestPluginSystemPerformance(unittest.TestCase):
    """Performance tests for the complete plugin system."""
    
    def test_system_performance_with_many_plugins(self):
        """Test system performance with many plugins."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            registry = PluginRegistry()
            hook_manager = HookManager()
            
            # Create many plugins
            plugins = []
            for i in range(50):
                plugin = TestValidationPlugin()
                plugin._plugin_id = f"plugin_{i}"
                plugins.append(plugin)
                registry.register_plugin(plugin)
                
                # Register hooks
                hook_manager.register_hook(
                    f"plugin_{i}",
                    HookType.AFTER_EXTRACT,
                    lambda ctx, **kwargs: PluginResult(
                        success=True,
                        plugin_id=f"plugin_{i}",
                        hook_type=HookType.AFTER_EXTRACT,
                        data={"plugin_id": f"plugin_{i}"}
                    )
                )
            
            # Measure execution time
            import time
            start_time = time.time()
            
            results = loop.run_until_complete(
                hook_manager.execute_hooks(HookType.AFTER_EXTRACT, extracted_data={'title': 'Test'})
            )
            
            execution_time = time.time() - start_time
            
            # Should complete reasonably quickly
            self.assertLess(execution_time, 2.0)  # Less than 2 seconds
            
            # Verify all plugins executed
            self.assertEqual(len(results), 50)
            self.assertTrue(all(r.success for r in results))
            
        finally:
            loop.close()


if __name__ == '__main__':
    unittest.main()
