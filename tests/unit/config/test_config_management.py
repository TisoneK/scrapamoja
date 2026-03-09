"""
Configuration testing framework for the scraper framework.

This module provides comprehensive testing utilities for configuration management.
"""

import pytest
import asyncio
import json
import tempfile
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.sites.base.config_schemas import (
    ConfigSchema, ConfigField, ConfigType, ValidationRule,
    create_base_config_schema, get_schema, validate_config_by_schema
)
from src.sites.base.environment_detector import (
    EnvironmentDetector, Environment, detect_environment, get_environment
)
from src.sites.base.config_loader import (
    ConfigLoader, ConfigLoadResult, load_config, get_config_value
)
from src.sites.base.config_validator import (
    ConfigValidator, ValidationResult, validate_config, add_validation_rule
)
from src.sites.base.feature_flags import (
    FeatureFlagManager, FeatureFlag, FlagType, is_enabled, get_flag_value
)
from src.sites.base.config_hot_reload import (
    ConfigHotReloadManager, ReloadEvent, start_watching, stop_watching
)
from src.sites.base.config_merger import (
    ConfigMerger, MergeResult, MergeStrategy, merge_configs
)
from src.sites.base.config_cache import (
    ConfigCache, CacheStrategy, get as cache_get, set as cache_set
)
from src.sites.base.config_io import (
    ConfigIO, ExportOptions, ImportOptions, export_config, import_config
)
from src.sites.base.config_migration import (
    ConfigMigration, MigrationStep, migrate_config, get_migration_plan
)


class ConfigTestBase:
    """Base test class for configuration testing."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing."""
        return {
            'site_id': 'test_site',
            'site_name': 'Test Site',
            'base_url': 'https://example.com',
            'enabled': True,
            'timeout': 30000,
            'retry_count': 3,
            'environment': 'testing'
        }
    
    def create_temp_config_file(self, temp_dir: Path, config: Dict[str, Any], 
                               format: str = 'json') -> Path:
        """Create a temporary configuration file."""
        if format == 'json':
            file_path = temp_dir / 'config.json'
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=2)
        elif format == 'yaml':
            file_path = temp_dir / 'config.yaml'
            import yaml
            with open(file_path, 'w') as f:
                yaml.dump(config, f)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        return file_path


class TestConfigSchemas(ConfigTestBase):
    """Test configuration schemas."""
    
    def test_create_base_config_schema(self):
        """Test base configuration schema creation."""
        schema = create_base_config_schema()
        
        assert schema.name == "base_config"
        assert schema.version == "1.0.0"
        assert len(schema.fields) > 0
        
        # Check required fields
        site_id_field = schema.get_field('site_id')
        assert site_id_field is not None
        assert site_id_field.required is True
        assert site_id_field.type == ConfigType.STRING
    
    def test_validate_base_config(self, sample_config):
        """Test base configuration validation."""
        schema = create_base_config_schema()
        result = schema.validate_config(sample_config)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
    
    def test_validate_invalid_config(self):
        """Test invalid configuration validation."""
        schema = create_base_config_schema()
        invalid_config = {
            'site_id': '',  # Empty required field
            'timeout': -1000  # Invalid value
        }
        
        result = schema.validate_config(invalid_config)
        
        assert result['valid'] is False
        assert len(result['errors']) > 0
    
    def test_schema_registry(self):
        """Test schema registry functionality."""
        # Test getting schema
        base_schema = get_schema('base')
        assert base_schema is not None
        assert base_schema.name == 'base_config'
        
        # Test validating with registry
        result = validate_config_by_schema(
            {'site_id': 'test', 'site_name': 'Test', 'base_url': 'https://test.com'},
            'base'
        )
        assert result['valid'] is True


class TestEnvironmentDetector(ConfigTestBase):
    """Test environment detection."""
    
    def test_environment_detector_initialization(self):
        """Test environment detector initialization."""
        detector = EnvironmentDetector()
        assert detector is not None
        assert len(detector._detection_methods) > 0
    
    def test_detect_environment(self):
        """Test environment detection."""
        environment = detect_environment()
        assert environment in [env.value for env in Environment]
    
    @patch.dict('os.environ', {'SCRAPER_ENV': 'production'})
    def test_environment_override(self):
        """Test environment override via environment variable."""
        environment = detect_environment()
        assert environment == 'production'
    
    def test_environment_checkers(self):
        """Test environment checker functions."""
        from src.sites.base.environment_detector import is_production, is_development, is_testing
        
        # These should return boolean values
        assert isinstance(is_production(), bool)
        assert isinstance(is_development(), bool)
        assert isinstance(is_testing(), bool)


class TestConfigLoader(ConfigTestBase):
    """Test configuration loading."""
    
    def test_config_loader_initialization(self):
        """Test configuration loader initialization."""
        loader = ConfigLoader()
        assert loader is not None
        assert loader._default_config == {}
    
    def test_load_from_dict(self, sample_config):
        """Test loading configuration from dictionary."""
        loader = ConfigLoader()
        result = loader.load_config_from_dict(sample_config)
        
        assert result.success is True
        assert result.config['site_id'] == sample_config['site_id']
    
    def test_load_from_file(self, temp_dir, sample_config):
        """Test loading configuration from file."""
        config_file = self.create_temp_config_file(temp_dir, sample_config)
        loader = ConfigLoader()
        
        result = loader.load_config(config_path=config_file)
        
        assert result.success is True
        assert result.config['site_id'] == sample_config['site_id']
    
    def test_config_value_get_set(self, sample_config):
        """Test getting and setting configuration values."""
        loader = ConfigLoader()
        loader.load_config_from_dict(sample_config)
        
        # Test getting value
        value = loader.get_config_value('site_id')
        assert value == sample_config['site_id']
        
        # Test setting value
        success = loader.set_config_value('site_id', 'new_site')
        assert success is True
        
        new_value = loader.get_config_value('site_id')
        assert new_value == 'new_site'


class TestConfigValidator(ConfigTestBase):
    """Test configuration validation."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = ConfigValidator()
        assert validator is not None
        assert len(validator._custom_rules) == 0
    
    def test_add_validation_rule(self, sample_config):
        """Test adding custom validation rule."""
        validator = ConfigValidator()
        
        # Add custom rule
        def custom_validator(value):
            return len(str(value)) > 3
        
        rule = validator.create_custom_rule(
            'site_id_length',
            custom_validator,
            'Site ID must be longer than 3 characters'
        )
        
        validator.add_custom_rule('site_id', rule)
        
        # Test validation
        result = validator.validate_config(sample_config)
        assert result.success is True
    
    def test_required_field_rule(self):
        """Test required field validation rule."""
        validator = ConfigValidator()
        validator.add_required_field_rule('required_field')
        
        # Test with missing field
        result = validator.validate_config({})
        assert result.success is False
        assert len(result.errors) > 0
    
    def test_type_validation_rule(self):
        """Test type validation rule."""
        validator = ConfigValidator()
        validator.add_type_rule('numeric_field', int)
        
        # Test with correct type
        result = validator.validate_config({'numeric_field': 42})
        assert result.success is True
        
        # Test with incorrect type
        result = validator.validate_config({'numeric_field': 'not_a_number'})
        assert result.success is False


class TestFeatureFlags(ConfigTestBase):
    """Test feature flag management."""
    
    def test_feature_flag_manager_initialization(self):
        """Test feature flag manager initialization."""
        manager = FeatureFlagManager()
        assert manager is not None
        assert len(manager._flags) > 0  # Should have built-in flags
    
    def test_add_feature_flag(self):
        """Test adding a feature flag."""
        manager = FeatureFlagManager()
        
        flag = FeatureFlag(
            name='test_flag',
            flag_type=FlagType.BOOLEAN,
            default_value=False,
            description='Test flag for testing'
        )
        
        manager.add_flag(flag)
        
        retrieved_flag = manager.get_flag('test_flag')
        assert retrieved_flag is not None
        assert retrieved_flag.name == 'test_flag'
    
    def test_evaluate_boolean_flag(self):
        """Test evaluating boolean feature flag."""
        manager = FeatureFlagManager()
        
        # Test built-in flag
        result = manager.evaluate_flag('debug_mode')
        assert result.enabled is not None
        assert isinstance(result.enabled, bool)
    
    def test_flag_environment_overrides(self):
        """Test feature flag environment overrides."""
        manager = FeatureFlagManager()
        
        # Add flag with environment override
        flag = FeatureFlag(
            name='env_test_flag',
            flag_type=FlagType.BOOLEAN,
            default_value=False,
            environment_overrides={
                'development': True
            }
        )
        
        manager.add_flag(flag)
        
        # Test in development environment
        result = manager.evaluate_flag('env_test_flag', environment='development')
        assert result.enabled is True
        
        # Test in production environment
        result = manager.evaluate_flag('env_test_flag', environment='production')
        assert result.enabled is False
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        # Test is_enabled
        result = is_enabled('debug_mode')
        assert isinstance(result, bool)
        
        # Test get_value
        value = get_flag_value('debug_mode')
        assert isinstance(value, bool)


class TestConfigHotReload(ConfigTestBase):
    """Test configuration hot reloading."""
    
    def test_hot_reload_manager_initialization(self):
        """Test hot reload manager initialization."""
        manager = ConfigHotReloadManager()
        assert manager is not None
        assert manager._is_running is False
    
    def test_start_stop_watching(self, temp_dir):
        """Test starting and stopping file watching."""
        manager = ConfigHotReloadManager()
        
        # Start watching
        success = manager.start_watching([str(temp_dir)])
        assert success is True
        assert manager.is_watching() is True
        
        # Stop watching
        success = manager.stop_watching()
        assert success is True
        assert manager.is_watching() is False
    
    def test_add_remove_watch_path(self, temp_dir):
        """Test adding and removing watch paths."""
        manager = ConfigHotReloadManager()
        
        # Add watch path
        success = manager.add_watch_path(str(temp_dir))
        assert success is True
        
        # Remove watch path
        success = manager.remove_watch_path(str(temp_dir))
        assert success is True
    
    def test_performance_stats(self):
        """Test performance statistics."""
        manager = ConfigHotReloadManager()
        
        stats = manager.get_performance_stats()
        assert 'total_reloads' in stats
        assert 'is_watching' in stats
        assert 'watched_paths' in stats


class TestConfigMerger(ConfigTestBase):
    """Test configuration merging."""
    
    def test_merger_initialization(self):
        """Test configuration merger initialization."""
        merger = ConfigMerger()
        assert merger is not None
        assert merger._default_strategy == MergeStrategy.SMART_MERGE
    
    def test_replace_merge(self, sample_config):
        """Test replace merge strategy."""
        merger = ConfigMerger()
        
        base_config = {'key1': 'value1', 'key2': 'value2'}
        override_config = {'key3': 'value3'}
        
        result = merger.merge_configs(
            base_config,
            [override_config],
            strategy=MergeStrategy.REPLACE
        )
        
        assert result.success is True
        assert result.merged_config == override_config
    
    def test_deep_merge(self):
        """Test deep merge strategy."""
        merger = ConfigMerger()
        
        base_config = {
            'level1': {
                'level2': {
                    'key1': 'value1',
                    'key2': 'value2'
                }
            }
        }
        
        override_config = {
            'level1': {
                'level2': {
                    'key2': 'new_value2',
                    'key3': 'value3'
                }
            }
        }
        
        result = merger.merge_configs(
            base_config,
            [override_config],
            strategy=MergeStrategy.MERGE
        )
        
        assert result.success is True
        assert result.merged_config['level1']['level2']['key1'] == 'value1'
        assert result.merged_config['level1']['level2']['key2'] == 'new_value2'
        assert result.merged_config['level1']['level2']['key3'] == 'value3'
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        base_config = {'key1': 'value1'}
        override_config = {'key2': 'value2'}
        
        result = merge_configs(base_config, [override_config])
        assert result.success is True


class TestConfigCache(ConfigTestBase):
    """Test configuration caching."""
    
    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = ConfigCache()
        assert cache is not None
        assert cache.max_size > 0
        assert cache.max_memory_bytes > 0
    
    def test_cache_set_get(self):
        """Test cache set and get operations."""
        cache = ConfigCache()
        
        # Set value
        success = cache.set('test_key', 'test_value')
        assert success is True
        
        # Get value
        value = cache.get('test_key')
        assert value == 'test_value'
        
        # Get non-existent value
        value = cache.get('non_existent_key', 'default')
        assert value == 'default'
    
    def test_cache_delete_clear(self):
        """Test cache delete and clear operations."""
        cache = ConfigCache()
        
        # Set multiple values
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        
        # Delete specific key
        success = cache.delete('key2')
        assert success is True
        assert cache.get('key2') is None
        assert cache.get('key1') == 'value1'
        
        # Clear all
        cache.clear()
        assert cache.get('key1') is None
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = ConfigCache()
        
        # Perform operations
        cache.set('key1', 'value1')
        cache.get('key1')  # Hit
        cache.get('key2')  # Miss
        
        stats = cache.get_stats()
        assert stats.hits >= 1
        assert stats.misses >= 1
        assert stats.total_requests >= 2
        assert stats.entry_count >= 1
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        # Test global cache functions
        success = cache_set('global_key', 'global_value')
        assert success is True
        
        value = cache_get('global_key')
        assert value == 'global_value'
        
        from src.sites.base.config_cache import exists, clear
        assert exists('global_key') is True
        
        clear()
        assert exists('global_key') is False


class TestConfigIO(ConfigTestBase):
    """Test configuration I/O operations."""
    
    def test_io_initialization(self):
        """Test I/O manager initialization."""
        io = ConfigIO()
        assert io is not None
        assert io._backup_dir.exists()
    
    def test_export_json(self, temp_dir, sample_config):
        """Test JSON export."""
        io = ConfigIO()
        output_path = temp_dir / 'export.json'
        
        options = ExportOptions(format=ConfigFormat.JSON, pretty_print=True)
        result = io.export_config(sample_config, output_path, options)
        
        assert result.success is True
        assert output_path.exists()
    
    def test_import_json(self, temp_dir, sample_config):
        """Test JSON import."""
        io = ConfigIO()
        
        # First export
        config_file = self.create_temp_config_file(temp_dir, sample_config, 'json')
        
        # Then import
        options = ImportOptions(format=ConfigFormat.JSON, validate=True)
        result = io.import_config(config_file, options)
        
        assert result.success is True
        assert 'configs' in result.imported_configs
    
    def test_convenience_functions(self, temp_dir, sample_config):
        """Test convenience functions."""
        # Test export
        output_path = temp_dir / 'convenience.json'
        result = export_config(sample_config, output_path)
        assert result.success is True
        
        # Test import
        import_options = ImportOptions()
        import_result = import_config(output_path, import_options)
        assert import_result.success is True


class TestConfigMigration(ConfigTestBase):
    """Test configuration migration."""
    
    def test_migration_initialization(self):
        """Test migration manager initialization."""
        migration = ConfigMigration()
        assert migration is not None
        assert len(migration._migrations) > 0  # Should have built-in migrations
    
    def test_register_migration(self):
        """Test migration registration."""
        migration = ConfigMigration()
        
        def up_migration(config):
            config['new_field'] = 'new_value'
            return config
        
        def down_migration(config):
            config.pop('new_field', None)
            return config
        
        step = MigrationStep(
            version='2.0.0',
            description='Test migration',
            up_migration=up_migration,
            down_migration=down_migration
        )
        
        migration.register_migration(step)
        
        retrieved_step = migration.get_migration('2.0.0')
        assert retrieved_step is not None
        assert retrieved_step.version == '2.0.0'
    
    def test_migration_plan(self):
        """Test migration plan creation."""
        migration = ConfigMigration()
        
        plan = migration.get_migration_plan('1.0.0', '1.2.0')
        
        assert plan.from_version == '1.0.0'
        assert plan.to_version == '1.2.0'
        assert len(plan.steps) > 0
        assert plan.estimated_time_ms > 0
    
    def test_migrate_config(self):
        """Test configuration migration."""
        migration = ConfigMigration()
        
        config = {'site_id': 'test', 'timeout': 30}  # timeout in seconds (old format)
        
        result = migration.migrate_config(config, '1.0.0', '1.1.0')
        
        assert result.success is True
        assert len(result.applied_steps) > 0
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        config = {'site_id': 'test'}
        
        # Test migration
        result = migrate_config(config, '1.0.0', '1.1.0')
        assert result.success is True
        
        # Test plan
        plan = get_migration_plan('1.0.0', '1.1.0')
        assert plan.from_version == '1.0.0'
        assert plan.to_version == '1.1.0'


class TestConfigIntegration(ConfigTestBase):
    """Integration tests for configuration management."""
    
    def test_end_to_end_config_workflow(self, temp_dir, sample_config):
        """Test end-to-end configuration workflow."""
        # 1. Create initial configuration
        initial_config = sample_config.copy()
        
        # 2. Validate configuration
        schema = create_base_config_schema()
        validation_result = schema.validate_config(initial_config)
        assert validation_result['valid'] is True
        
        # 3. Export configuration
        io = ConfigIO()
        export_path = temp_dir / 'integration_config.json'
        export_options = ExportOptions(format=ConfigFormat.JSON)
        export_result = io.export_config(initial_config, export_path, export_options)
        assert export_result.success is True
        
        # 4. Import configuration
        import_options = ImportOptions(format=ConfigFormat.JSON, validate=True)
        import_result = io.import_config(export_path, import_options)
        assert import_result.success is True
        
        # 5. Load configuration
        loader = ConfigLoader()
        load_result = loader.load_config(config_path=export_path)
        assert load_result.success is True
        
        # 6. Cache configuration
        cache = ConfigCache()
        cache.set('integration_config', load_result.config)
        cached_config = cache.get('integration_config')
        assert cached_config is not None
        assert cached_config['site_id'] == initial_config['site_id']
        
        # 7. Test feature flags
        flag_result = is_enabled('debug_mode')
        assert isinstance(flag_result, bool)
        
        # 8. Test environment detection
        environment = get_environment()
        assert environment is not None
        
        # 9. Test configuration merging
        override_config = {'timeout': 60000, 'debug': True}
        merge_result = merge_configs(load_result.config, [override_config])
        assert merge_result.success is True
        assert merge_result.merged_config['timeout'] == 60000
        assert merge_result.merged_config['debug'] is True
        
        # 10. Test migration
        migration = ConfigMigration()
        migration_plan = migration.get_migration_plan('1.0.0', '1.1.0')
        assert migration_plan.from_version == '1.0.0'
        assert migration_plan.to_version == '1.1.0'
    
    def test_configuration_performance(self, sample_config):
        """Test configuration performance."""
        import time
        
        # Test schema validation performance
        schema = create_base_config_schema()
        start_time = time.time()
        
        for _ in range(100):
            schema.validate_config(sample_config)
        
        validation_time = time.time() - start_time
        assert validation_time < 1.0  # Should complete in under 1 second
        
        # Test cache performance
        cache = ConfigCache()
        start_time = time.time()
        
        for i in range(100):
            cache.set(f'key_{i}', f'value_{i}')
            cache.get(f'key_{i}')
        
        cache_time = time.time() - start_time
        assert cache_time < 1.0  # Should complete in under 1 second
    
    def test_configuration_error_handling(self, temp_dir):
        """Test configuration error handling."""
        # Test invalid configuration
        invalid_config = {'site_id': '', 'timeout': 'invalid'}
        
        schema = create_base_config_schema()
        result = schema.validate_config(invalid_config)
        assert result['valid'] is False
        assert len(result['errors']) > 0
        
        # Test missing file
        loader = ConfigLoader()
        result = loader.load_config(config_path='non_existent.json')
        assert result.success is False
        assert len(result.errors) > 0
        
        # Test invalid import
        io = ConfigIO()
        invalid_path = temp_dir / 'invalid.json'
        with open(invalid_path, 'w') as f:
            f.write('invalid json content')
        
        import_options = ImportOptions(format=ConfigFormat.JSON)
        result = io.import_config(invalid_path, import_options)
        assert result.success is False
        assert len(result.errors) > 0


# Pytest configuration
def pytest_configure(config):
    """Configure pytest for configuration tests."""
    config.addinivalue_line(
        "markers", "config: marks tests as configuration tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection for configuration tests."""
    for item in items:
        if "config" in item.nodeid:
            item.add_marker(pytest.mark.config)
