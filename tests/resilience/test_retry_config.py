"""
Configuration Reload Tests

Tests for retry configuration hot-reload functionality.
"""

import pytest
import pytest_asyncio
from pathlib import Path

from src.resilience.config.retry_config import (
    RetryConfigManager,
    RetryPolicyConfig,
    GlobalDefaultsConfig,
    RetryConfiguration,
    ConfigChange
)


@pytest.fixture
async def config_manager():
    """Create a config manager instance for testing."""
    manager = RetryConfigManager()
    await manager.load_config()
    return manager


@pytest.mark.asyncio
class TestRetryConfigLoading:
    """Tests for retry configuration loading."""
    
    async def test_load_valid_config(self, config_manager):
        """Test loading a valid configuration file."""
        # This test will use the actual config file
        config = await config_manager.load_config()
        
        assert config is not None
        assert config.version == "1.0.0"
        assert len(config.policies) > 0
        assert "browser_state_timeout" in config.policies
        assert "navigation_retry_with_delay" in config.policies
    
    async def test_load_invalid_yaml(self, config_manager, tmp_path):
        """Test loading an invalid YAML configuration."""
        # Create an invalid YAML file
        invalid_yaml = tmp_path / "invalid_retry_config.yaml"
        invalid_yaml.write_text("""
version: "1.0.0"
policies:
  invalid_policy:
    max_attempts: -1
    backoff_type: "invalid_backoff"
    base_delay: -1.0
""")
        
        # Try to load it
        with pytest.raises(Exception) as exc_info:
            await config_manager.load_config()
        
        assert "invalid" in str(exc_info.value).lower()
    
    async def test_load_missing_file(self, config_manager, tmp_path):
        """Test loading a missing configuration file."""
        missing_file = tmp_path / "missing_retry_config.yaml"
        
        with pytest.raises(Exception) as exc_info:
            await config_manager.load_config()
        
        assert "not found" in str(exc_info.value).lower()
    
    async def test_policy_validation(self, config_manager):
        """Test policy validation."""
        config = await config_manager.load_config()
        
        # Test valid policy
        valid_policy = config.policies["browser_state_timeout"]
        assert valid_policy.max_attempts == 3
        assert valid_policy.backoff_type == "exponential"
        assert valid_policy.base_delay == 1.0
        assert valid_policy.max_delay == 10.0
    
    async def test_global_defaults_application(self, config_manager):
        """Test that global defaults are applied to policies."""
        config = await config_manager.load_config()
        
        # Check that policies have global defaults applied
        for policy_id, policy in config.policies.items():
            if config.global_defaults:
                if config.global_defaults.jitter_type:
                    assert policy.jitter_type == config.global_defaults.jitter_type
                if config.global_defaults.jitter_amount is not None:
                    assert policy.jitter_amount == config.global_defaults.jitter_amount


@pytest.mark.asyncio
class TestConfigReloading:
    """Tests for configuration hot-reload functionality."""
    
    async def test_reload_config(self, config_manager, tmp_path):
        """Test reloading configuration."""
        # Create a modified config file
        config_file = tmp_path / "test_retry_config.yaml"
        config_file.write_text("""
version: "1.0.0"
policies:
  browser_state_timeout:
    name: "Browser State Timeout Retry (Modified)"
    description: "Retry state operations that timeout (modified)"
    max_attempts: 5
    backoff_type: "exponential"
    base_delay: 2.0
    max_delay: 20.0
    enabled: true
""")
        
        # Reload configuration
        await config_manager.reload_config()
        
        # Verify new policy is loaded
        config = await config_manager.load_config()
        policy = config.policies["browser_state_timeout"]
        
        assert policy.max_attempts == 5
        assert policy.base_delay == 2.0
        assert policy.max_delay == 20.0
    
    async def test_config_change_callback(self, config_manager):
        """Test configuration change callback."""
        callback_called = []
        
        async def test_callback(change: ConfigChange):
            callback_called.append(change)
        
        # Register callback
        await config_manager.register_change_callback(test_callback)
        
        # Trigger a config change
        await config_manager.reload_config()
        
        # Verify callback was called
        assert len(callback_called) > 0
        assert callback_called[-1].change_type == "reloaded"
    
    async def test_hot_reload_within_time_limit(self, config_manager, tmp_path):
        """Test that hot-reload completes within 5 seconds."""
        import time
        
        # Create a config file
        config_file = tmp_path / "test_retry_config.yaml"
        config_file.write_text("""
version: "1.0.0"
policies:
  browser_state_timeout:
    name: "Browser State Timeout Retry"
    max_attempts: 3
    backoff_type: "exponential"
    base_delay: 1.0
    max_delay: 10.0
    enabled: true
""")
        
        # Load initial config
        await config_manager.load_config()
        initial_policy = config.policies["browser_state_timeout"]
        
        # Modify file
        time.sleep(0.1)  # Small delay
        config_file.write_text("""
version: "1.0.0"
policies:
  browser_state_timeout:
    name: "Browser State Timeout Retry (Modified)"
    max_attempts: 5
    backoff_type: "exponential"
    base_delay: 2.0
    max_delay: 20.0
    enabled: true
""")
        
        # Measure reload time
        start_time = time.time()
        await config_manager.reload_config()
        reload_time = time.time() - start_time
        
        # Verify reload completed within 5 seconds
        assert reload_time < 5.0


@pytest.mark.asyncio
class TestSubsystemMappings:
    """Tests for subsystem mappings."""
    
    async def test_browser_mappings(self, config_manager):
        """Test browser subsystem mappings."""
        config = await config_manager.load_config()
        
        assert config.subsystem_mappings is not None
        assert "browser" in config.subsystem_mappings
        
        browser_mappings = config.subsystem_mappings.browser
        assert browser_mappings is not None
        assert "state_operations" in browser_mappings
        assert "timeout" in browser_mappings.state_operations
        assert browser_mappings.state_operations["timeout"] == "browser_state_timeout"
    
    async def test_navigation_mappings(self, config_manager):
        """Test navigation subsystem mappings."""
        config = await config_manager.load_config()
        
        assert config.subsystem_mappings is not None
        assert "navigation" in config.subsystem_mappings
        
        navigation_mappings = config.subsystem_mappings.navigation
        assert navigation_mappings is not None
        assert "route_adaptation" in navigation_mappings
        assert navigation_mappings.route_adaptation["retry_with_delay"] == "navigation_retry_with_delay"
    
    async def test_telemetry_mappings(self, config_manager):
        """Test telemetry subsystem mappings."""
        config = await config_manager.load_config()
        
        assert config.subsystem_mappings is not None
        assert "telemetry" in config.subsystem_mappings
        
        telemetry_mappings = config.subsystem_mappings.telemetry
        assert telemetry_mappings is not None
        assert "error_handling" in telemetry_mappings
        assert telemetry_mappings.error_handling["default"] == "telemetry_error_handling"


@pytest.mark.asyncio
class TestConfigManagerIntegration:
    """Tests for integration between config manager and retry manager."""
    
    async def test_config_manager_initializes_retry_manager(self, config_manager):
        """Test that config manager initializes retry manager."""
        from src.resilience.retry.retry_manager import get_retry_manager
        
        # Get retry manager
        retry_manager = get_retry_manager()
        
        # Verify it's initialized
        health = await retry_manager.health_check()
        assert health["status"] == "healthy"
        assert health["initialized"] is True
        assert health["policies_count"] > 0
    
    async def test_config_policies_available_in_retry_manager(self, config_manager):
        """Test that config policies are available in retry manager."""
        from src.resilience.retry.retry_manager import get_retry_manager
        
        # Get retry manager
        retry_manager = get_retry_manager()
        
        # Verify policies are loaded
        assert len(retry_manager.policies) > 0
        
        # Check for specific policies
        assert "browser_state_timeout" in retry_manager.policies
        assert "navigation_retry_with_delay" in retry_manager.policies
        assert "telemetry_error_handling" in retry_manager.policies
