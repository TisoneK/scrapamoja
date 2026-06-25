"""
Browser Configuration Management

This module implements browser configuration validation and defaults,
following the BrowserConfiguration entity specification.
"""

import asyncio
import json
import time
from typing import Optional, Dict, Any, List, Union, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import structlog

from .models.session import BrowserConfiguration
from .models.proxy import ProxySettings
from .models.stealth import StealthSettings, StealthLevel
from .models.viewport import ViewportSettings
from .exceptions import ConfigurationError
from ..config.settings import get_config


class ConfigurationStatus(Enum):
    """Configuration validation status."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    status: ConfigurationStatus
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    def add_error(self, error: str) -> None:
        """Add an error to the validation result."""
        self.errors.append(error)
        self.status = ConfigurationStatus.ERROR
        self.is_valid = False
        
    def add_warning(self, warning: str) -> None:
        """Add a warning to the validation result."""
        self.warnings.append(warning)
        if self.status == ConfigurationStatus.VALID:
            self.status = ConfigurationStatus.WARNING
            
    def add_suggestion(self, suggestion: str) -> None:
        """Add a suggestion to the validation result."""
        self.suggestions.append(suggestion)


class BrowserConfigurationManager:
    """Manages browser configuration with validation and defaults."""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir or "data/configs")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.app_config = get_config()
        
        # Logging
        self.logger = structlog.get_logger("browser.configuration")
        
        # Default configurations
        self.default_configurations = self._load_default_configurations()
        
        # Configuration cache
        self._config_cache: Dict[str, BrowserConfiguration] = {}
        
    def _load_default_configurations(self) -> Dict[str, BrowserConfiguration]:
        """Load default browser configurations."""
        return {
            "chromium_headless": BrowserConfiguration(
                config_id="chromium_headless",
                browser_type="chromium",
                headless=True,
                viewport_width=1920,
                viewport_height=1080,
                device_scale_factor=1.0,
                is_mobile=False,
                has_touch=False,
                stealth_settings=StealthSettings.get_stealth_presets()["standard"]
            ),
            "chromium_gui": BrowserConfiguration(
                config_id="chromium_gui",
                browser_type="chromium",
                headless=False,
                viewport_width=1920,
                viewport_height=1080,
                device_scale_factor=1.0,
                is_mobile=False,
                has_touch=False,
                stealth_settings=StealthSettings.get_stealth_presets()["standard"]
            ),
            "firefox_headless": BrowserConfiguration(
                config_id="firefox_headless",
                browser_type="firefox",
                headless=True,
                viewport_width=1920,
                viewport_height=1080,
                device_scale_factor=1.0,
                is_mobile=False,
                has_touch=False,
                stealth_settings=StealthSettings.get_stealth_presets()["standard"]
            ),
            "firefox_gui": BrowserConfiguration(
                config_id="firefox_gui",
                browser_type="firefox",
                headless=False,
                viewport_width=1920,
                viewport_height=1080,
                device_scale_factor=1.0,
                is_mobile=False,
                has_touch=False,
                stealth_settings=StealthSettings.get_stealth_presets()["standard"]
            ),
            "mobile_chrome": BrowserConfiguration(
                config_id="mobile_chrome",
                browser_type="chromium",
                headless=True,
                viewport_width=375,
                viewport_height=667,
                device_scale_factor=2.0,
                is_mobile=True,
                has_touch=True,
                stealth_settings=StealthSettings.get_stealth_presets()["high"]
            ),
            "tablet_safari": BrowserConfiguration(
                config_id="tablet_safari",
                browser_type="webkit",
                headless=True,
                viewport_width=768,
                viewport_height=1024,
                device_scale_factor=2.0,
                is_mobile=True,
                has_touch=True,
                stealth_settings=StealthSettings.get_stealth_presets()["high"]
            ),
            "stealth_chromium": BrowserConfiguration(
                config_id="stealth_chromium",
                browser_type="chromium",
                headless=True,
                viewport_width=1366,
                viewport_height=768,
                device_scale_factor=1.0,
                is_mobile=False,
                has_touch=False,
                stealth_settings=StealthSettings.get_stealth_presets()["maximum"]
            ),
            "residential_proxy": BrowserConfiguration(
                config_id="residential_proxy",
                browser_type="chromium",
                headless=True,
                viewport_width=1920,
                viewport_height=1080,
                device_scale_factor=1.0,
                is_mobile=False,
                has_touch=False,
                proxy_settings=ProxySettings.create_residential_proxy(
                    "residential.example.com",
                    8080,
                    "user123",
                    "pass123"
                ),
                stealth_settings=StealthSettings.get_stealth_presets()["high"]
            )
        }
        
    def get_configuration(self, config_id: str) -> Optional[BrowserConfiguration]:
        """Get configuration by ID."""
        # Check cache first
        if config_id in self._config_cache:
            return self._config_cache[config_id]
            
        # Check default configurations
        if config_id in self.default_configurations:
            config = self.default_configurations[config_id]
            self._config_cache[config_id] = config
            return config
            
        # Try to load from file
        config = self._load_configuration_from_file(config_id)
        if config:
            self._config_cache[config_id] = config
            return config
            
        return None
        
    def create_configuration(
        self,
        config_id: str,
        browser_type: str,
        **kwargs
    ) -> BrowserConfiguration:
        """Create a new browser configuration."""
        # Validate browser type
        valid_browsers = ["chromium", "firefox", "webkit"]
        if browser_type not in valid_browsers:
            raise ConfigurationError(
                "configuration",
                "browser_type",
                f"Invalid browser type: {browser_type}. Valid types: {valid_browsers}",
                config_field="browser_type",
                config_value=browser_type
            )
            
        # Create configuration with defaults
        config = BrowserConfiguration(
            config_id=config_id,
            browser_type=browser_type,
            **kwargs
        )
        
        # Validate the configuration
        validation_result = self.validate_configuration(config)
        if not validation_result.is_valid:
            raise ConfigurationError(
                "configuration",
                "validation_failed",
                f"Configuration validation failed: {'; '.join(validation_result.errors)}",
                config_id=config_id
            )
            
        # Cache the configuration
        self._config_cache[config_id] = config
        
        # Save to file
        self._save_configuration_to_file(config)
        
        self.logger.info(
            "Browser configuration created",
            config_id=config_id,
            browser_type=browser_type,
            headless=config.headless
        )
        
        return config
        
    def update_configuration(
        self,
        config_id: str,
        **updates
    ) -> BrowserConfiguration:
        """Update an existing browser configuration."""
        config = self.get_configuration(config_id)
        if not config:
            raise ConfigurationError(
                "configuration",
                "not_found",
                f"Configuration not found: {config_id}",
                config_id=config_id
            )
            
        # Update configuration
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                self.logger.warning(
                    "Unknown configuration field",
                    field=key,
                    config_id=config_id
                )
                
        # Validate the updated configuration
        validation_result = self.validate_configuration(config)
        if not validation_result.is_valid:
            raise ConfigurationError(
                "configuration",
                "validation_failed",
                f"Configuration validation failed: {'; '.join(validation_result.errors)}",
                config_id=config_id
            )
            
        # Update cache
        self._config_cache[config_id] = config
        
        # Save to file
        self._save_configuration_to_file(config)
        
        self.logger.info(
            "Browser configuration updated",
            config_id=config_id,
            updates=updates
        )
        
        return config
        
    def delete_configuration(self, config_id: str) -> bool:
        """Delete a browser configuration."""
        # Remove from cache
        if config_id in self._config_cache:
            del self._config_cache[config_id]
            
        # Remove from defaults (if it exists there)
        if config_id in self.default_configurations:
            self.logger.warning(
                "Cannot delete default configuration",
                config_id=config_id
            )
            return False
            
        # Delete file
        config_file = self.config_dir / f"{config_id}.json"
        if config_file.exists():
            config_file.unlink()
            
            self.logger.info(
                "Browser configuration deleted",
                config_id=config_id
            )
            
            return True
            
        return False
        
    def list_configurations(self) -> List[str]:
        """List all available configuration IDs."""
        configs = set(self.default_configurations.keys())
        
        # Add file-based configurations
        for config_file in self.config_dir.glob("*.json"):
            config_id = config_file.stem
            configs.add(config_id)
            
        return sorted(list(configs))
        
    def validate_configuration(self, config: BrowserConfiguration) -> ValidationResult:
        """Validate a browser configuration."""
        result = ValidationResult(status=ConfigurationStatus.VALID, is_valid=True)
        
        try:
            # Validate required fields
            if not config.config_id:
                result.add_error("Configuration ID is required")
                
            if not config.browser_type:
                result.add_error("Browser type is required")
                
            # Validate browser type
            valid_browsers = ["chromium", "firefox", "webkit"]
            if config.browser_type not in valid_browsers:
                result.add_error(f"Invalid browser type: {config.browser_type}")
                
            # Validate viewport dimensions
            if config.viewport_width <= 0:
                result.add_error("Viewport width must be positive")
                
            if config.viewport_height <= 0:
                result.add_error("Viewport height must be positive")
                
            if config.device_scale_factor <= 0:
                result.add_error("Device scale factor must be positive")
                
            # Validate stealth settings
            if config.stealth_settings:
                stealth_validation = self._validate_stealth_settings(config.stealth_settings)
                if not stealth_validation.is_valid:
                    result.errors.extend(stealth_validation.errors)
                    result.warnings.extend(stealth_validation.warnings)
                    if result.status == ConfigurationStatus.VALID:
                        result.status = ConfigurationStatus.WARNING
                        
            # Validate proxy settings
            if config.proxy_settings:
                proxy_validation = self._validate_proxy_settings(config.proxy_settings)
                if not proxy_validation.is_valid:
                    result.errors.extend(proxy_validation.errors)
                    result.warnings.extend(proxy_validation.warnings)
                    if result.status == ConfigurationStatus.VALID:
                        result.status = ConfigurationStatus.WARNING
                        
            # Check for common issues
            self._check_common_issues(config, result)
            
        except Exception as e:
            result.add_error(f"Validation error: {str(e)}")
            result.status = ConfigurationStatus.ERROR
            
        return result
        
    def _validate_stealth_settings(self, stealth: StealthSettings) -> ValidationResult:
        """Validate stealth settings."""
        result = ValidationResult(status=ConfigurationStatus.VALID, is_valid=True)
        
        # Validate timing settings
        if stealth.min_delay_ms < 0:
            result.add_error("Minimum delay must be non-negative")
            
        if stealth.max_delay_ms < 0:
            result.add_error("Maximum delay must be non-negative")
            
        if stealth.min_delay_ms >= stealth.max_delay_ms:
            result.add_warning("Minimum delay is greater than or equal to maximum delay")
            
        if stealth.delay_variation_factor < 0 or stealth.delay_variation_factor > 1:
            result.add_warning("Delay variation factor should be between 0 and 1")
            
        # Validate stealth level compatibility
        if stealth.residential_ip_required and not stealth.proxy_rotation:
            result.add_warning("Residential IP required but proxy rotation is disabled")
            
        return result
        
    def _validate_proxy_settings(self, proxy: ProxySettings) -> ValidationResult:
        """Validate proxy settings."""
        result = ValidationResult(status=ConfigurationStatus.VALID, is_valid=True)
        
        # Validate port range
        if proxy.port < 1 or proxy.port > 65535:
            result.add_error(f"Invalid proxy port: {proxy.port}. Must be 1-65535")
            
        # Validate server
        if not proxy.server:
            result.add_error("Proxy server is required")
            
        # Check for common misconfigurations
        if proxy.server in ["localhost", "127.0.0.1"] and proxy.has_credentials():
            result.add_warning("Using localhost with proxy credentials may not be intended")
            
        return result
        
    def _check_common_issues(self, config: BrowserConfiguration, result: ValidationResult) -> None:
        """Check for common configuration issues."""
        # Check for headless browser with mobile viewport
        if config.headless and config.is_mobile:
            result.add_suggestion("Consider using GUI browser for mobile viewport testing")
            
        # Check for stealth settings with headless browser
        if config.stealth_settings.stealth_level == StealthLevel.MAXIMUM and config.headless:
            result.add_warning("Maximum stealth with headless browser may have limited effectiveness")
            
        # Check for proxy settings without rotation
        if config.proxy_settings and not config.proxy_rotation:
            result.add_suggestion("Consider enabling proxy rotation for better anonymity")
            
        # Check for very small viewports
        if config.viewport_width < 800 or config.viewport_height < 600:
            result.add_warning("Small viewport may cause issues with some websites")
            
    def _load_configuration_from_file(self, config_id: str) -> Optional[BrowserConfiguration]:
        """Load configuration from file."""
        try:
            config_file = self.config_dir / f"{config_id}.json"
            
            if not config_file.exists():
                return None
                
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            return BrowserConfiguration.from_dict(data)
            
        except Exception as e:
            self.logger.error(
                "Failed to load configuration from file",
                config_id=config_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
            
    def _save_configuration_to_file(self, config: BrowserConfiguration) -> None:
        """Save configuration to file."""
        try:
            config_file = self.config_dir / f"{config.config_id}.json"
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(
                "Failed to save configuration to file",
                config_id=config.config_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise ConfigurationError(
                "configuration",
                "save_failed",
                f"Failed to save configuration {config.config_id}: {str(e)}"
            )
            
    def get_configuration_summary(self, config_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of configuration details."""
        config = self.get_configuration(config_id)
        if not config:
            return None
            
        return {
            "config_id": config.config_id,
            "browser_type": config.browser_type,
            "headless": config.headless,
            "viewport": {
                "width": config.viewport_width,
                "height": config.height,
                "device_scale_factor": config.device_scale_factor,
                "is_mobile": config.is_mobile,
                "has_touch": config.has_touch
            },
            "has_proxy": config.proxy_settings is not None,
            "has_stealth": config.stealth_settings is not None,
            "stealth_level": config.stealth_settings.stealth_level.value if config.stealth_settings else None,
            "permissions": config.permissions,
            "ignore_https_errors": config.ignore_https_errors,
            "locale": config.locale,
            "timezone": config.timezone
        }
        
    def clone_configuration(self, source_config_id: str, new_config_id: str) -> BrowserConfiguration:
        """Clone an existing configuration."""
        source_config = self.get_configuration(source_config_id)
        if not source_config:
            raise ConfigurationError(
                "configuration",
                "not_found",
                f"Source configuration not found: {source_config_id}",
                config_id=source_config_id
            )
            
        # Create clone with new ID
        clone_data = source_config.to_dict()
        clone_data["config_id"] = new_config_id
        
        # Remove fields that should be unique
        clone_data.pop("created_at", None)
        clone_data.pop("updated_at", None)
        
        clone_config = BrowserConfiguration.from_dict(clone_data)
        
        # Validate and save
        validation_result = self.validate_configuration(clone_config)
        if not validation_result.is_valid:
            raise ConfigurationError(
                "configuration",
                "clone_validation_failed",
                f"Cloned configuration validation failed: {'; '.join(validation_result.errors)}",
                config_id=new_config_id
            )
            
        self._config_cache[new_config_id] = clone_config
        self._save_configuration_to_file(clone_config)
        
        self.logger.info(
            "Browser configuration cloned",
            source_config_id=source_config_id,
            new_config_id=new_config_id
        )
        
        return clone_config
        
    def export_configuration(self, config_id: str, file_path: str) -> bool:
        """Export configuration to file."""
        config = self.get_configuration(config_id)
        if not config:
            return False
            
        try:
            export_path = Path(file_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
                
            self.logger.info(
                "Configuration exported",
                config_id=config_id,
                file_path=file_path
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to export configuration",
                config_id=config_id,
                file_path=file_path,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
            
    def import_configuration(self, file_path: str, config_id: Optional[str] = None) -> BrowserConfiguration:
        """Import configuration from file."""
        try:
            import_path = Path(file_path)
            
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if config_id:
                data["config_id"] = config_id
            elif "config_id" not in data:
                raise ConfigurationError(
                    "configuration",
                    "import_failed",
                    "Configuration ID must be specified in file or as parameter"
                )
                
            config = BrowserConfiguration.from_dict(data)
            
            # Validate imported configuration
            validation_result = self.validate_configuration(config)
            if not validation_result.is_valid:
                raise ConfigurationError(
                    "configuration",
                    "import_validation_failed",
                    f"Imported configuration validation failed: {'; '.join(validation_result.errors)}",
                    config_id=config.config_id
                )
                
            # Save to cache and file
            self._config_cache[config.config_id] = config
            self._save_configuration_to_file(config)
            
            self.logger.info(
                "Configuration imported",
                config_id=config.config_id,
                file_path=file_path
            )
            
            return config
            
        except Exception as e:
            self.logger.error(
                "Failed to import configuration",
                file_path=file_path,
                error=str(e),
                error_type=type(e).__name__
            )
            raise ConfigurationError(
                "configuration",
                "import_failed",
                f"Failed to import configuration: {str(e)}"
            )
            
    def get_default_configuration(self) -> BrowserConfiguration:
        """Get the default browser configuration."""
        default_type = self.app_config.browser.default_browser_type
        default_id = f"{default_type}_default"
        
        return self.get_configuration(default_id) or self.default_configurations[default_id]


# Global configuration manager instance
configuration_manager = BrowserConfigurationManager()


def get_configuration_manager() -> BrowserConfigurationManager:
    """Get the global configuration manager instance."""
    return configuration_manager
