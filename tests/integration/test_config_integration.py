"""
Configuration integration tests for the scraper framework.

This module provides comprehensive integration tests for configuration management,
testing the interaction between different configuration components.
"""

import pytest
import asyncio
import json
import tempfile
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.sites.base.config_schemas import create_base_config_schema, get_schema
from src.sites.base.environment_detector import detect_environment, Environment
from src.sites.base.config_loader import ConfigLoader, load_config
from src.sites.base.config_validator import ConfigValidator, validate_config
from src.sites.base.feature_flags import FeatureFlagManager, is_enabled, get_value
from src.sites.base.config_hot_reload import ConfigHotReloadManager
from src.sites.base.config_merger import ConfigMerger, merge_configs
from src.sites.base.config_cache import ConfigCache
from src.sites.base.config_io import ConfigIO, ExportOptions, ImportOptions
from src.sites.base.config_migration import ConfigMigration


class ConfigIntegrationTestBase:
    """Base test class for configuration integration tests."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing."""
        return {
            'site_id': 'integration_test',
            'site_name': 'Integration Test Site',
            'base_url': 'https://integration.test.com',
            'enabled': True,
            'timeout': 30000,
            'retry_count': 3,
            'environment': 'testing',
            'browser': {
                'headless': True,
                'browser_type': 'chromium',
                'viewport_width': 1920,
                'viewport_height': 1080
            },
            'rate_limiting': {
                'enabled': True,
                'max_requests_per_minute': 60,
                'strategy': 'token_bucket'
            },
            'feature_flags': {
                'debug_mode': False,
                'headless_mode': True,
                'rate_limiting_enabled': True
            }
        }
    
    def create_config_file(self, temp_dir: Path, config: Dict[str, Any], 
                          filename: str = 'config.json') -> Path:
        """Create a configuration file."""
        config_path = temp_dir / filename
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return config_path


class TestConfigSystemIntegration(ConfigIntegrationTestBase):
    """Test complete configuration system integration."""
    
    @pytest.mark.asyncio
    async def test_full_configuration_lifecycle(self, temp_dir, sample_config):
        """Test complete configuration lifecycle from creation to usage."""
        
        # 1. Create configuration file
        config_file = self.create_config_file(temp_dir, sample_config)
        
        # 2. Load and validate configuration
        loader = ConfigLoader()
        load_result = loader.load_config(config_path=config_file, schema_name='base')
        assert load_result.success is True
        
        # 3. Cache configuration
        cache = ConfigCache()
        cache_key = f"config_{sample_config['site_id']}"
        cache_success = cache.set(cache_key, load_result.config)
        assert cache_success is True
        
        cached_config = cache.get(cache_key)
        assert cached_config is not None
        assert cached_config['site_id'] == sample_config['site_id']
        
        # 4. Test feature flags
        flag_enabled = is_enabled('debug_mode')
        assert isinstance(flag_enabled, bool)
        
        flag_value = get_value('rate_limiting_enabled')
        assert isinstance(flag_value, bool)
        
        # 5. Test environment detection
        environment = detect_environment()
        assert environment in [env.value for env in Environment]
        
        # 6. Test configuration merging
        override_config = {
            'timeout': 60000,
            'debug': True,
            'browser': {
                'headless': False
            }
        }
        
        merge_result = merge_configs(load_result.config, [override_config])
        assert merge_result.success is True
        assert merge_result.merged_config['timeout'] == 60000
        assert merge_result.merged_config['debug'] is True
        assert merge_result.merged_config['browser']['headless'] is False
        
        # 7. Test configuration export
        io = ConfigIO()
        export_path = temp_dir / 'exported_config.json'
        export_options = ExportOptions(format=ConfigFormat.JSON, pretty_print=True)
        export_result = io.export_config(merge_result.merged_config, export_path, export_options)
        assert export_result.success is True
        assert export_path.exists()
        
        # 8. Test configuration import
        import_options = ImportOptions(format=ConfigFormat.JSON, validate=True)
        import_result = io.import_config(export_path, import_options)
        assert import_result.success is True
        
        # 9. Test configuration migration
        migration = ConfigMigration()
        migration_plan = migration.get_migration_plan('1.0.0', '1.2.0')
        assert migration_plan.from_version == '1.0.0'
        assert migration_plan.to_version == '1.2.0'
        assert len(migration_plan.steps) > 0
        
        # 10. Verify end-to-end data integrity
        final_config = import_result.imported_configs.get('configs', {})
        assert final_config['site_id'] == sample_config['site_id']
        assert final_config['timeout'] == 60000  # From override
        assert final_config['debug'] is True  # From override
    
    def test_environment_specific_configuration(self, temp_dir):
        """Test environment-specific configuration handling."""
        
        # Create environment-specific configurations
        dev_config = {
            'site_id': 'dev_site',
            'debug': True,
            'headless': False,
            'timeout': 60000,
            'environment': 'development'
        }
        
        prod_config = {
            'site_id': 'prod_site',
            'debug': False,
            'headless': True,
            'timeout': 30000,
            'environment': 'production'
        }
        
        # Create config files
        dev_file = self.create_config_file(temp_dir, dev_config, 'config.development.json')
        prod_file = self.create_config_file(temp_dir, prod_config, 'config.production.json')
        
        # Test development environment loading
        loader = ConfigLoader()
        dev_result = loader.load_config(config_path=dev_file, environment='development')
        assert dev_result.success is True
        assert dev_result.config['environment'] == 'development'
        assert dev_result.config['debug'] is True
        
        # Test production environment loading
        prod_result = loader.load_config(config_path=prod_file, environment='production')
        assert prod_result.success is True
        assert prod_result.config['environment'] == 'production'
        assert prod_result.config['debug'] is False
        
        # Test environment merging
        base_config = {'site_id': 'base_site', 'timeout': 30000}
        env_overrides = {
            'development': {'debug': True, 'timeout': 60000},
            'production': {'debug': False, 'timeout': 10000}
        }
        
        merger = ConfigMerger()
        dev_merged = merger.merge_environment_configs(base_config, env_overrides, 'development')
        prod_merged = merger.merge_environment_configs(base_config, env_overrides, 'production')
        
        assert dev_merged['debug'] is True
        assert dev_merged['timeout'] == 60000
        assert prod_merged['debug'] is False
        assert prod_merged['timeout'] == 10000
    
    @pytest.mark.asyncio
    async def test_hot_reload_integration(self, temp_dir, sample_config):
        """Test hot reloading integration with other components."""
        
        # Create initial configuration
        config_file = self.create_config_file(temp_dir, sample_config)
        
        # Initialize components
        loader = ConfigLoader()
        cache = ConfigCache()
        hot_reload = ConfigHotReloadManager()
        
        # Load initial configuration
        initial_result = loader.load_config(config_path=config_file)
        assert initial_result.success is True
        
        # Cache configuration
        cache.set('hot_reload_test', initial_result.config)
        
        # Set up hot reload
        reload_called = False
        reload_config = None
        
        def reload_callback(result):
            nonlocal reload_called, reload_config
            reload_called = True
            reload_config = result
        
        hot_reload.add_reload_callback(reload_callback)
        
        # Start watching
        watch_success = hot_reload.start_watching([str(temp_dir)])
        assert watch_success is True
        
        # Modify configuration file
        modified_config = sample_config.copy()
        modified_config['timeout'] = 45000
        modified_config['debug'] = True
        
        with open(config_file, 'w') as f:
            json.dump(modified_config, f, indent=2)
        
        # Wait for hot reload (in real scenario, this would be async)
        await asyncio.sleep(0.1)
        
        # Manually trigger reload for testing
        manual_result = hot_reload.reload_config(config_path=str(config_file))
        assert manual_result.success is True
        
        # Verify updated configuration
        assert manual_result.merged_config['timeout'] == 45000
        assert manual_result.merged_config['debug'] is True
        
        # Stop watching
        stop_success = hot_reload.stop_watching()
        assert stop_success is False  # Already stopped in manual reload
    
    def test_feature_flag_integration(self, temp_dir, sample_config):
        """Test feature flag integration with configuration system."""
        
        # Create configuration with feature flags
        config_with_flags = sample_config.copy()
        config_with_flags['feature_flags'] = {
            'debug_mode': True,
            'headless_mode': False,
            'rate_limiting_enabled': True,
            'stealth_mode': False
        }
        
        config_file = self.create_config_file(temp_dir, config_with_flags)
        
        # Load configuration
        loader = ConfigLoader()
        load_result = loader.load_config(config_path=config_file)
        assert load_result.success is True
        
        # Test feature flag evaluation
        debug_enabled = is_enabled('debug_mode')
        assert isinstance(debug_enabled, bool)
        
        headless_enabled = is_enabled('headless_mode')
        assert isinstance(headless_enabled, bool)
        
        # Test feature flag manager integration
        flag_manager = FeatureFlagManager()
        
        # Add custom flag
        from src.sites.base.feature_flags import FeatureFlag, FlagType
        custom_flag = FeatureFlag(
            name='integration_test_flag',
            flag_type=FlagType.BOOLEAN,
            default_value=True,
            description='Integration test flag'
        )
        
        flag_manager.add_flag(custom_flag)
        
        # Evaluate custom flag
        custom_result = flag_manager.evaluate_flag('integration_test_flag')
        assert custom_result.enabled is True
        
        # Test environment-specific flag
        env_flag = FeatureFlag(
            name='env_specific_flag',
            flag_type=FlagType.BOOLEAN,
            default_value=False,
            environment_overrides={
                'testing': True
            }
        )
        
        flag_manager.add_flag(env_flag)
        
        env_result = flag_manager.evaluate_flag('env_specific_flag', environment='testing')
        assert env_result.enabled is True
    
    def test_configuration_validation_integration(self, temp_dir):
        """Test configuration validation integration."""
        
        # Create valid configuration
        valid_config = {
            'site_id': 'valid_site',
            'site_name': 'Valid Site',
            'base_url': 'https://valid.example.com',
            'enabled': True,
            'timeout': 30000,
            'retry_count': 3
        }
        
        # Create invalid configuration
        invalid_config = {
            'site_id': '',  # Empty required field
            'site_name': 'Invalid Site',
            'base_url': 'invalid_url',  # Invalid URL
            'enabled': True,
            'timeout': -1000,  # Invalid value
            'retry_count': 3
        }
        
        valid_file = self.create_config_file(temp_dir, valid_config, 'valid_config.json')
        invalid_file = self.create_config_file(temp_dir, invalid_config, 'invalid_config.json')
        
        # Test validator integration
        validator = ConfigValidator()
        
        # Add custom validation rule
        validator.add_required_field_rule('custom_required_field')
        
        # Test valid configuration
        valid_result = validator.validate_config(valid_config, schema_name='base')
        assert valid_result['valid'] is True
        assert len(valid_result['errors']) == 0
        
        # Test invalid configuration
        invalid_result = validator.validate_config(invalid_config, schema_name='base')
        assert invalid_result['valid'] is False
        assert len(invalid_result['errors']) > 0
        
        # Test loader integration with validation
        loader = ConfigLoader()
        
        # Load valid config with validation
        valid_load_result = loader.load_config(
            config_path=valid_file,
            schema_name='base'
        )
        assert valid_load_result.success is True
        
        # Load invalid config with validation
        invalid_load_result = loader.load_config(
            config_path=invalid_file,
            schema_name='base'
        )
        assert invalid_load_result.success is False
        assert len(invalid_load_result.errors) > 0
    
    def test_configuration_caching_integration(self, temp_dir, sample_config):
        """Test configuration caching integration."""
        
        # Create configuration file
        config_file = self.create_config_file(temp_dir, sample_config)
        
        # Initialize components
        loader = ConfigLoader()
        cache = ConfigCache()
        
        # Load configuration
        load_result = loader.load_config(config_path=config_file)
        assert load_result.success is True
        
        # Test caching with different strategies
        strategies = [CacheStrategy.LRU, CacheStrategy.LFU, CacheStrategy.TTL]
        
        for strategy in strategies:
            # Create cache with specific strategy
            strategy_cache = ConfigCache(strategy=strategy)
            
            # Cache configuration
            cache_key = f"config_{strategy.value}_{sample_config['site_id']}"
            cache_success = strategy_cache.set(cache_key, load_result.config)
            assert cache_success is True
            
            # Retrieve from cache
            cached_config = strategy_cache.get(cache_key)
            assert cached_config is not None
            assert cached_config['site_id'] == sample_config['site_id']
            
            # Test cache statistics
            stats = strategy_cache.get_stats()
            assert stats.hits >= 1
            assert stats.entry_count >= 1
        
        # Test TTL cache
        ttl_cache = ConfigCache(strategy=CacheStrategy.TTL)
        ttl_success = ttl_cache.set('ttl_test', sample_config, ttl=timedelta(milliseconds=100))
        assert ttl_success is True
        
        # Should be available immediately
        immediate_result = ttl_cache.get('ttl_test')
        assert immediate_result is not None
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired
        expired_result = ttl_cache.get('ttl_test')
        assert expired_result is None
    
    def test_configuration_io_integration(self, temp_dir, sample_config):
        """Test configuration I/O integration."""
        
        # Initialize I/O manager
        io = ConfigIO()
        
        # Test different export formats
        formats = [ConfigFormat.JSON, ConfigFormat.YAML]
        
        for format_type in formats:
            # Export configuration
            export_path = temp_dir / f'config.{format_type.value}'
            export_options = ExportOptions(format=format_type, pretty_print=True)
            export_result = io.export_config(sample_config, export_path, export_options)
            assert export_result.success is True
            assert export_path.exists()
            
            # Import configuration
            import_options = ImportOptions(format=format_type, validate=True)
            import_result = io.import_config(export_path, import_options)
            assert import_result.success is True
            
            # Verify data integrity
            imported_config = import_result.imported_configs.get('configs', {})
            assert imported_config['site_id'] == sample_config['site_id']
            assert imported_config['site_name'] == sample_config['site_name']
        
        # Test export/import roundtrip
        original_path = temp_dir / 'original.json'
        roundtrip_path = temp_dir / 'roundtrip.json'
        
        # Export original
        original_options = ExportOptions(format=ConfigFormat.JSON, include_sensitive=True)
        original_result = io.export_config(sample_config, original_path, original_options)
        assert original_result.success is True
        
        # Import and re-export
        import_options = ImportOptions(format=ConfigFormat.JSON)
        import_result = io.import_config(original_path, import_options)
        assert import_result.success is True
        
        roundtrip_options = ExportOptions(format=ConfigFormat.JSON)
        roundtrip_result = io.export_config(
            import_result.imported_configs.get('configs', {}),
            roundtrip_path,
            roundtrip_options
        )
        assert roundtrip_result.success is True
        
        # Verify roundtrip integrity
        with open(original_path, 'r') as f1, open(roundtrip_path, 'r') as f2:
            original_data = json.load(f1)
            roundtrip_data = json.load(f2)
            
            # Compare core fields
            assert original_data['configs']['site_id'] == roundtrip_data['configs']['site_id']
            assert original_data['configs']['site_name'] == roundtrip_data['configs']['site_name']
    
    def test_configuration_migration_integration(self, temp_dir):
        """Test configuration migration integration."""
        
        # Create old format configuration
        old_config = {
            'site_id': 'migration_test',
            'site_name': 'Migration Test Site',
            'base_url': 'https://migration.test.com',
            'timeout': 30,  # Old format: seconds
            'retry_count': 3,
            'version': '1.0.0'
        }
        
        old_file = self.create_config_file(temp_dir, old_config, 'old_config.json')
        
        # Initialize migration manager
        migration = ConfigMigration()
        
        # Test migration plan
        plan = migration.get_migration_plan('1.0.0', '1.2.0')
        assert plan.from_version == '1.0.0'
        assert plan.to_version == '1.2.0'
        assert len(plan.steps) > 0
        assert plan.rollback_possible is True
        
        # Perform migration
        migration_result = migration.migrate_config(old_config, '1.0.0', '1.2.0')
        assert migration_result.success is True
        assert len(migration_result.applied_steps) > 0
        
        # Verify migration results
        migrated_config = migration_result.merged_configs
        assert 'environment' in migrated_config  # Added in 1.1.0
        assert 'feature_flags' in migrated_config  # Added in 1.2.0
        assert 'rate_limiting' in migrated_config  # Added in 1.2.0
        
        # Test rollback
        rollback_result = migration.rollback_migration(migrated_config, '1.2.0', '1.0.0')
        assert rollback_result.success is True
        assert len(rollback_result.applied_steps) > 0
        
        # Test migration with I/O
        io = ConfigIO()
        
        # Export old configuration
        export_path = temp_dir / 'migration_export.json'
        export_options = ExportOptions(format=ConfigFormat.JSON)
        export_result = io.export_config(old_config, export_path, export_options)
        assert export_result.success is True
        
        # Import and migrate
        import_options = ImportOptions(format=ConfigFormat.JSON)
        import_result = io.import_config(export_path, import_options)
        assert import_result.success is True
        
        imported_config = import_result.imported_configs.get('configs', {})
        migrated_imported = migration.migrate_config(imported_config, '1.0.0', '1.2.0')
        assert migrated_imported.success is True
    
    def test_error_handling_integration(self, temp_dir):
        """Test error handling across configuration components."""
        
        # Test invalid configuration file
        invalid_file = temp_dir / 'invalid.json'
        with open(invalid_file, 'w') as f:
            f.write('invalid json content {')
        
        # Test loader error handling
        loader = ConfigLoader()
        load_result = loader.load_config(config_path=invalid_file)
        assert load_result.success is False
        assert len(load_result.errors) > 0
        
        # Test validator error handling
        validator = ConfigValidator()
        invalid_config = {'site_id': '', 'timeout': 'invalid'}
        validation_result = validator.validate_config(invalid_config)
        assert validation_result['valid'] is False
        assert len(validation_result['errors']) > 0
        
        # Test I/O error handling
        io = ConfigIO()
        io_result = io.import_config('non_existent_file.json')
        assert io_result.success is False
        assert len(io_result.errors) > 0
        
        # Test migration error handling
        migration = ConfigMigration()
        migration_result = migration.migrate_config({'invalid': 'config'}, 'invalid_version', '1.0.0')
        assert migration_result.success is False
        assert len(migration_result.errors) > 0
        
        # Test cache error handling
        cache = ConfigCache()
        # Cache should handle invalid data gracefully
        try:
            cache.set('test_key', object())  # Non-serializable object
        except Exception:
            pass  # Expected to handle gracefully
        
        # Test hot reload error handling
        hot_reload = ConfigHotReloadManager()
        # Should handle non-existent directory gracefully
        watch_result = hot_reload.start_watching(['/non/existent/path'])
        assert isinstance(watch_result, bool)
    
    def test_performance_integration(self, sample_config):
        """Test performance across configuration components."""
        
        import time
        
        # Test configuration loading performance
        loader = ConfigLoader()
        start_time = time.time()
        
        for _ in range(100):
            # Simulate loading from dict
            result = loader.load_config_from_dict(sample_config)
            assert result.success is True
        
        load_time = time.time() - start_time
        assert load_time < 1.0  # Should complete in under 1 second
        
        # Test validation performance
        validator = ConfigValidator()
        start_time = time.time()
        
        for _ in range(100):
            result = validator.validate_config(sample_config, schema_name='base')
            assert result['valid'] is True
        
        validation_time = time.time() - start_time
        assert validation_time < 1.0  # Should complete in under 1 second
        
        # Test caching performance
        cache = ConfigCache()
        start_time = time.time()
        
        for i in range(100):
            cache.set(f'perf_test_{i}', sample_config)
            cache.get(f'perf_test_{i}')
        
        cache_time = time.time() - start_time
        assert cache_time < 1.0  # Should complete in under 1 second
        
        # Test feature flag performance
        flag_manager = FeatureFlagManager()
        start_time = time.time()
        
        for _ in range(100):
            result = flag_manager.evaluate_flag('debug_mode')
            assert result is not None
        
        flag_time = time.time() - start_time
        assert flag_time < 1.0  # Should complete in under 1 second
        
        # Test merging performance
        merger = ConfigMerger()
        start_time = time.time()
        
        override_config = {'timeout': 60000, 'debug': True}
        for _ in range(100):
            result = merger.merge_configs(sample_config, [override_config])
            assert result.success is True
        
        merge_time = time.time() - start_time
        assert merge_time < 1.0  # Should complete in under 1 second


# Pytest configuration
def pytest_configure(config):
    """Configure pytest for configuration integration tests."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection for configuration integration tests."""
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
