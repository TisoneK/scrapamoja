"""
Configuration Management Integration Tests

Integration tests for browser configuration functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from src.browser.config import BrowserConfiguration, StealthConfiguration, ResourceLimits
from src.browser.models.proxy import ProxySettings
from src.browser.models.stealth import StealthSettings, StealthLevel
from src.browser.models.enums import ProxyType
from tests.fixtures.browser_configs import CHROMIUM_HEADLESS_CONFIG


class TestConfigurationManagement:
    """Integration tests for browser configuration management."""
    
    @pytest.mark.asyncio
    async def test_browser_configuration_creation(self):
        """Test BrowserConfiguration creation and validation."""
        config = BrowserConfiguration()
        
        assert config.browser_type.value == "chromium"
        assert config.headless is True
        assert isinstance(config.stealth, StealthConfiguration)
        assert isinstance(config.resource_limits, ResourceLimits)
        assert config.proxy is None
        assert config.launch_options == {}
        assert config.context_options == {}
    
    @pytest.mark.asyncio
    async def test_browser_configuration_serialization(self):
        """Test configuration serialization and deserialization."""
        # Create original configuration
        original_config = BrowserConfiguration()
        original_config.headless = False
        original_config.stealth.user_agent = "Mozilla/5.0 (Custom)"
        original_config.stealth.locale = "fr-FR"
        original_config.resource_limits.max_memory_mb = 2048
        original_config.proxy = {"server": "proxy.example.com", "port": 8080}
        
        # Serialize to dict
        config_dict = original_config.to_dict()
        
        # Verify serialization
        assert config_dict["browser_type"] == "chromium"
        assert config_dict["headless"] is False
        assert config_dict["stealth"]["user_agent"] == "Mozilla/5.0 (Custom)"
        assert config_dict["stealth"]["locale"] == "fr-FR"
        assert config_dict["resource_limits"]["max_memory_mb"] == 2048
        assert config_dict["proxy"]["server"] == "proxy.example.com"
        
        # Deserialize from dict
        restored_config = BrowserConfiguration.from_dict(config_dict)
        
        # Verify deserialization
        assert restored_config.browser_type.value == "chromium"
        assert restored_config.headless is False
        assert restored_config.stealth.user_agent == "Mozilla/5.0 (Custom)"
        assert restored_config.stealth.locale == "fr-FR"
        assert restored_config.resource_limits.max_memory_mb == 2048
        assert restored_config.proxy["server"] == "proxy.example.com"
    
    @pytest.mark.asyncio
    async def test_proxy_settings_creation(self):
        """Test ProxySettings creation and validation."""
        proxy = ProxySettings(
            proxy_type=ProxyType.HTTPS,
            server="proxy.example.com",
            port=8080,
            username="user123",
            password="pass456"
        )
        
        assert proxy.proxy_type == ProxyType.HTTPS
        assert proxy.server == "proxy.example.com"
        assert proxy.port == 8080
        assert proxy.username == "user123"
        assert proxy.password == "pass456"
        assert proxy.bypass_list == []
        assert proxy.dns_servers == []
    
    @pytest.mark.asyncio
    async def test_proxy_settings_validation(self):
        """Test ProxySettings validation."""
        # Valid proxy should not raise error
        proxy = ProxySettings(
            server="proxy.example.com",
            port=8080
        )
        assert proxy.server == "proxy.example.com"
        assert proxy.port == 8080
        
        # Invalid server should raise error
        with pytest.raises(ValueError, match="Proxy server cannot be empty"):
            ProxySettings(server="", port=8080)
        
        # Invalid port should raise error
        with pytest.raises(ValueError, match="Invalid proxy port"):
            ProxySettings(server="proxy.example.com", port=0)
        
        with pytest.raises(ValueError, match="Invalid proxy port"):
            ProxySettings(server="proxy.example.com", port=70000)
    
    @pytest.mark.asyncio
    async def test_stealth_settings_creation(self):
        """Test StealthSettings creation."""
        stealth = StealthSettings(
            stealth_level=StealthLevel.HIGH,
            fingerprint_randomization=True,
            user_agent_rotation=False
        )
        
        assert stealth.stealth_level == StealthLevel.HIGH
        assert stealth.fingerprint_randomization is True
        assert stealth.user_agent_rotation is False
        assert stealth.mouse_movement_simulation is True
        assert stealth.typing_simulation is True
    
    @pytest.mark.asyncio
    async def test_configuration_defaults(self):
        """Test configuration default values."""
        config = BrowserConfiguration()
        
        # Browser defaults
        assert config.browser_type.value == "chromium"
        assert config.headless is True
        
        # Stealth defaults
        assert config.stealth.locale == "en-US"
        assert config.stealth.timezone == "America/New_York"
        assert config.stealth.permissions == ["geolocation"]
        assert config.stealth.bypass_csp is True
        assert config.stealth.ignore_https_errors is False
        
        # Resource limits defaults
        assert config.resource_limits.max_memory_mb == 1024
        assert config.resource_limits.max_cpu_percent == 80.0
        assert config.resource_limits.max_tab_count == 10
        assert config.resource_limits.session_timeout_minutes == 30
        assert config.resource_limits.cleanup_threshold_memory == 0.8
        assert config.resource_limits.cleanup_threshold_cpu == 0.9
    
    @pytest.mark.asyncio
    async def test_configuration_integration_with_browser_session(self):
        """Test configuration integration with browser session."""
        from src.browser.session import BrowserSession
        
        # Create custom configuration
        config = BrowserConfiguration()
        config.headless = False
        config.stealth.user_agent = "Custom User Agent"
        config.stealth.locale = "es-ES"
        config.resource_limits.max_memory_mb = 512
        
        # Create session with custom configuration
        session = BrowserSession(configuration=config)
        
        assert session.configuration == config
        assert session.configuration.headless is False
        assert session.configuration.stealth.user_agent == "Custom User Agent"
        assert session.configuration.stealth.locale == "es-ES"
        assert session.configuration.resource_limits.max_memory_mb == 512
    
    @pytest.mark.asyncio
    async def test_proxy_configuration_integration(self):
        """Test proxy configuration integration."""
        proxy_settings = ProxySettings(
            proxy_type=ProxyType.SOCKS5,
            server="socks5.example.com",
            port=1080,
            username="proxy_user",
            password="proxy_pass"
        )
        
        config = BrowserConfiguration()
        config.proxy = {
            "type": proxy_settings.proxy_type.value,
            "server": proxy_settings.server,
            "port": proxy_settings.port,
            "username": proxy_settings.username,
            "password": proxy_settings.password
        }
        
        config_dict = config.to_dict()
        assert config_dict["proxy"]["type"] == "socks5"
        assert config_dict["proxy"]["server"] == "socks5.example.com"
        assert config_dict["proxy"]["port"] == 1080
        assert config_dict["proxy"]["username"] == "proxy_user"
        assert config_dict["proxy"]["password"] == "proxy_pass"
    
    @pytest.mark.asyncio
    async def test_stealth_configuration_integration(self):
        """Test stealth configuration integration."""
        stealth_settings = StealthSettings(
            stealth_level=StealthLevel.MAXIMUM,
            fingerprint_randomization=True,
            user_agent_rotation=True,
            viewport_randomization=True,
            mouse_movement_simulation=False
        )
        
        config = BrowserConfiguration()
        config.stealth.user_agent = "Stealth Browser"
        config.stealth.locale = "de-DE"
        config.stealth.timezone = "Europe/Berlin"
        config.stealth.geolocation = {"latitude": 52.5200, "longitude": 13.4050}
        config.stealth.permissions = ["geolocation", "camera", "microphone"]
        config.stealth.extra_http_headers = {"X-Custom-Header": "CustomValue"}
        
        config_dict = config.to_dict()
        stealth_dict = config_dict["stealth"]
        
        assert stealth_dict["user_agent"] == "Stealth Browser"
        assert stealth_dict["locale"] == "de-DE"
        assert stealth_dict["timezone"] == "Europe/Berlin"
        assert stealth_dict["geolocation"]["latitude"] == 52.5200
        assert stealth_dict["geolocation"]["longitude"] == 13.4050
        assert "camera" in stealth_dict["permissions"]
        assert "microphone" in stealth_dict["permissions"]
        assert stealth_dict["extra_http_headers"]["X-Custom-Header"] == "CustomValue"
    
    @pytest.mark.asyncio
    async def test_configuration_validation(self):
        """Test configuration validation."""
        # Test valid configuration
        config = BrowserConfiguration()
        config.resource_limits.max_memory_mb = 1024
        config.resource_limits.max_cpu_percent = 80.0
        
        # Should not raise any errors
        config_dict = config.to_dict()
        assert config_dict["resource_limits"]["max_memory_mb"] == 1024
        assert config_dict["resource_limits"]["max_cpu_percent"] == 80.0
        
        # Test configuration with various browser types
        for browser_type in ["chromium", "firefox", "webkit"]:
            config_dict = {"browser_type": browser_type}
            config = BrowserConfiguration.from_dict(config_dict)
            assert config.browser_type.value == browser_type
    
    @pytest.mark.asyncio
    async def test_configuration_error_handling(self):
        """Test configuration error handling."""
        # Test invalid browser type
        with pytest.raises(ValueError):
            config_dict = {"browser_type": "invalid_browser"}
            BrowserConfiguration.from_dict(config_dict)
        
        # Test invalid proxy configuration
        with pytest.raises(ValueError):
            ProxySettings(server="", port=8080)
        
        # Test invalid proxy port
        with pytest.raises(ValueError):
            ProxySettings(server="proxy.example.com", port=99999)
    
    @pytest.mark.asyncio
    async def test_configuration_compatibility(self):
        """Test configuration compatibility across different browser types."""
        configurations = []
        
        # Chromium configuration
        chromium_config = BrowserConfiguration()
        chromium_config.stealth.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        configurations.append(("chromium", chromium_config))
        
        # Firefox configuration  
        firefox_config = BrowserConfiguration()
        firefox_config.stealth.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0"
        configurations.append(("firefox", firefox_config))
        
        # WebKit configuration
        webkit_config = BrowserConfiguration()
        webkit_config.stealth.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
        configurations.append(("webkit", webkit_config))
        
        # Test all configurations are valid
        for browser_name, config in configurations:
            config_dict = config.to_dict()
            assert "browser_type" in config_dict
            assert "stealth" in config_dict
            assert "resource_limits" in config_dict
            
            # Test round-trip serialization
            restored_config = BrowserConfiguration.from_dict(config_dict)
            assert restored_config.browser_type.value == browser_name


if __name__ == "__main__":
    asyncio.run(test_configuration_management())
