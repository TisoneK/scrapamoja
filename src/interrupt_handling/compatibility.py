"""
Backward compatibility layer for interrupt handling system.
"""

import logging
import warnings
from typing import Dict, Any, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum

from .config import InterruptConfig
from .handler import InterruptHandler
from .resource_manager import ResourceManager
from .messaging import InterruptMessageHandler


class CompatibilityMode(Enum):
    """Compatibility modes for the interrupt handling system."""
    LEGACY = "legacy"           # Old behavior without interrupt handling
    TRANSITIONAL = "transitional"   # Gradual adoption with warnings
    MODERN = "modern"           # Full interrupt handling enabled
    DISABLED = "disabled"         # Interrupt handling completely disabled


@dataclass
class CompatibilityConfig:
    """Configuration for backward compatibility."""
    mode: CompatibilityMode = CompatibilityMode.MODERN
    enable_warnings: bool = True
    warning_threshold: int = 3  # Number of warnings before suggesting upgrade
    legacy_api_fallback: bool = True
    migration_assistance: bool = True
    
    # Deprecated API settings
    deprecated_api_warnings: bool = True
    deprecated_parameter_warnings: bool = True
    graceful_degradation: bool = True


class LegacyAPIWrapper:
    """Wrapper for legacy API compatibility."""
    
    def __init__(self, modern_handler, logger):
        self.modern_handler = modern_handler
        self.logger = logger
        self._call_count = 0
        self._warning_issued = False
    
    def __getattr__(self, name: str):
        """Handle attribute access for legacy API calls."""
        if hasattr(self.modern_handler, name):
            # Check if this is a deprecated API
            if self._is_deprecated_api(name):
                if not self._warning_issued:
                    self._issue_deprecation_warning(name)
                    self._warning_issued = True
            
            return getattr(self.modern_handler, name)
        
        raise AttributeError(f"'{type(self.modern_handler).__name__}' object has no attribute '{name}'")
    
    def _is_deprecated_api(self, api_name: str) -> bool:
        """Check if an API is deprecated."""
        deprecated_apis = {
            # Old resource management methods
            'register_resource',
            'cleanup_resource',
            'force_cleanup',
            
            # Old signal handling methods
            'set_signal_handler',
            'ignore_signals',
            
            # Old configuration methods
            'set_interrupt_enabled',
            'set_cleanup_timeout',
            
            # Old callback methods
            'add_interrupt_callback',
            'remove_interrupt_callback'
        }
        
        return api_name in deprecated_apis
    
    def _issue_deprecation_warning(self, api_name: str):
        """Issue a deprecation warning."""
        self.logger.warning(
            f"DEPRECATED: {api_name} is deprecated and will be removed in a future version. "
            f"Please migrate to the new interrupt handling API. "
            f"See documentation for migration guidance."
        )
    
    def __call__(self, *args, **kwargs):
        """Handle direct calls to the wrapper."""
        self._call_count += 1
        
        # Issue warning on first use if not already issued
        if not self._warning_issued and self._is_deprecated_api(''):
            self._issue_migration_suggestion()
            self._warning_issued = True
        
        # Forward call to modern handler
        return self.modern_handler(*args, **kwargs)
    
    def _issue_migration_suggestion(self):
        """Issue migration suggestion for legacy API usage."""
        self.logger.warning(
            f"You are using the legacy interrupt handling API. "
            f"Consider upgrading to the modern API for better reliability and features. "
            f"Call upgrade_assistance() for migration help."
        )


class BackwardCompatibilityManager:
    """Manages backward compatibility for the interrupt handling system."""
    
    def __init__(self, config: InterruptConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize compatibility configuration
        self.compat_config = CompatibilityConfig()
        
        # Load compatibility settings from config
        self._load_from_config()
        
        # Initialize modern components
        self._modern_handler = None
        self._legacy_wrapper = None
        
        # Statistics
        self.stats = {
            'legacy_api_calls': 0,
            'modern_api_calls': 0,
            'warnings_issued': 0,
            'migrations_suggested': 0
        }
    
    def _load_from_config(self):
        """Load compatibility settings from configuration."""
        if hasattr(self.config, 'compatibility_mode'):
            mode_map = {
                'legacy': CompatibilityMode.LEGACY,
                'transitional': CompatibilityMode.TRANSITIONAL,
                'modern': CompatibilityMode.MODERN,
                'disabled': CompatibilityMode.DISABLED
            }
            
            mode_str = getattr(self.config, 'compatibility_mode', 'modern')
            self.compat_config.mode = mode_map.get(mode_str, CompatibilityMode.MODERN)
        
        if hasattr(self.config, 'compatibility_warnings'):
            self.compat_config.enable_warnings = bool(
                getattr(self.config, 'compatibility_warnings', True)
            )
        
        if hasattr(self.config, 'warning_threshold'):
            self.compat_config.warning_threshold = int(
                getattr(self.config, 'warning_threshold', 3)
            )
    
    def initialize_modern_handler(self, 
                               interrupt_handler: InterruptHandler,
                               resource_manager: ResourceManager,
                               message_handler: InterruptMessageHandler) -> 'LegacyAPIWrapper':
        """Initialize the modern interrupt handler and create legacy wrapper."""
        from .integration import InterruptAwareScraper
        
        # Create modern handler
        self._modern_handler = InterruptAwareScraper(self.config)
        
        # Create legacy wrapper
        self._legacy_wrapper = LegacyAPIWrapper(self._modern_handler, self.logger)
        
        # Update statistics
        self.stats['modern_api_calls'] += 1
        
        self.logger.info(f"Initialized modern interrupt handler in {self.compat_config.mode.value} mode")
        
        return self._legacy_wrapper
    
    def get_handler(self) -> Union['InterruptAwareScraper', 'LegacyAPIWrapper']:
        """Get the appropriate handler based on compatibility mode."""
        if self.compat_config.mode == CompatibilityMode.LEGACY:
            if not self._legacy_wrapper:
                self.logger.warning("Legacy mode enabled - consider upgrading to modern API")
            return self._legacy_wrapper
        
        elif self.compat_config.mode == CompatibilityMode.TRANSITIONAL:
            if not self._legacy_wrapper:
                self.logger.info("Transitional mode - migrating to modern API")
            return self._legacy_wrapper
        
        elif self.compat_config.mode == CompatibilityMode.MODERN:
            if not self._modern_handler:
                self.logger.info("Modern mode enabled")
            return self._modern_handler
        
        elif self.compat_config.mode == CompatibilityMode.DISABLED:
            self.logger.warning("Interrupt handling disabled - no protection against interruptions")
            return self._create_disabled_handler()
        
        else:
            # Default to modern
            return self._modern_handler
    
    def _create_disabled_handler(self):
        """Create a disabled handler that does nothing."""
        class DisabledHandler:
            def __init__(self):
                self.logger.warning("Interrupt handling is disabled")
            
            def check_interrupt_status(self):
                return False
            
            def enter_critical_operation(self, operation_name: str):
                pass
            
            def exit_critical_operation(self, operation_name: str):
                pass
            
            def scrape_with_interrupt_handling(self, func, *args, **kwargs):
                # Just execute the function without interrupt handling
                if hasattr(func, '__call__'):
                    return func(*args, **kwargs)
                else:
                    import asyncio
                    return asyncio.run(func(*args, **kwargs))
        
        return DisabledHandler()
    
    def should_issue_warning(self, api_name: str) -> bool:
        """Check if a warning should be issued for API usage."""
        if not self.compat_config.enable_warnings:
            return False
        
        # Check warning threshold
        if self.stats['warnings_issued'] >= self.compat_config.warning_threshold:
            return False
        
        # Check if this API has been warned about before
        return self._is_new_api_usage(api_name)
    
    def _is_new_api_usage(self, api_name: str) -> bool:
        """Check if the API usage is following modern patterns."""
        # This would implement logic to detect modern vs legacy usage
        # For now, assume legacy APIs trigger warnings
        modern_apis = {
            'check_interrupt_status',
            'enter_critical_operation',
            'exit_critical_operation',
            'scrape_with_interrupt_handling',
            'register_interrupt_callback',
            'get_interrupt_statistics'
        }
        
        return api_name not in modern_apis
    
    def issue_api_warning(self, api_name: str, suggestion: str = ""):
        """Issue a warning about API usage."""
        if self.should_issue_warning(api_name):
            self.stats['warnings_issued'] += 1
            
            warning_msg = f"API Usage Warning: {api_name}"
            if suggestion:
                warning_msg += f" - {suggestion}"
            
            self.logger.warning(warning_msg)
            
            # Suggest migration if enabled
            if self.compat_config.migration_assistance:
                self._suggest_migration()
    
    def _suggest_migration(self):
        """Suggest migration to modern API."""
        self.stats['migrations_suggested'] += 1
        
        migration_msg = (
            "Consider migrating to the modern interrupt handling API for better reliability. "
            "Call upgrade_assistance() for detailed migration guidance."
        )
        
        self.logger.warning(migration_msg)
    
    def upgrade_assistance(self) -> Dict[str, Any]:
        """Provide assistance for upgrading to modern API."""
        current_mode = self.compat_config.mode.value
        
        assistance = {
            'current_mode': current_mode,
            'recommended_mode': 'modern',
            'upgrade_steps': [],
            'code_examples': {},
            'benefits': {
                'better_reliability': 'Modern API provides more reliable interrupt handling',
                'enhanced_features': 'Access to new features like graceful shutdown coordination',
                'improved_performance': 'Optimized resource cleanup and data preservation',
                'better_error_handling': 'Comprehensive error reporting and recovery',
                'future_proof': 'Modern API is maintained and updated with new features'
            },
            'migration_risks': {
                'minimal_risk': 'Transitional mode provides gradual migration with fallback',
                'testing_required': 'Test thoroughly after migration',
                'backup_required': 'Keep backup of current configuration'
            }
        }
        
        # Add upgrade steps based on current mode
        if current_mode == 'legacy':
            assistance['upgrade_steps'] = [
                "1. Enable transitional mode: set compatibility_mode='transitional'",
                "2. Test with modern features enabled",
                "3. Update code to use modern API calls",
                "4. Switch to modern mode: set compatibility_mode='modern'"
            ]
        
        elif current_mode == 'transitional':
            assistance['upgrade_steps'] = [
                "1. Remove legacy API calls",
                "2. Add modern error handling",
                "3. Enable all modern features",
                "4. Switch to modern mode"
            ]
        
        # Add code examples
        assistance['code_examples'] = {
            'legacy_config': {
                'description': 'Legacy configuration',
                'code': 'config = InterruptConfig()\nconfig.compatibility_mode = "legacy"'
            },
            'modern_config': {
                'description': 'Modern configuration',
                'code': 'config = InterruptConfig()\nconfig.compatibility_mode = "modern"'
            },
            'legacy_usage': {
                'description': 'Legacy API usage',
                'code': '# Old way\nresult = some_legacy_function()'
            },
            'modern_usage': {
                'description': 'Modern API usage',
                'code': '''# New way
handler = get_interrupt_handler()
result = await handler.scrape_with_interrupt_handling(my_function)'''
            }
        }
        
        return assistance
    
    def get_compatibility_statistics(self) -> Dict[str, Any]:
        """Get statistics about compatibility usage."""
        return {
            **self.stats,
            'compatibility_mode': self.compat_config.mode.value,
            'warnings_enabled': self.compat_config.enable_warnings,
            'warning_threshold': self.compat_config.warning_threshold,
            'legacy_api_ratio': (
                self.stats['legacy_api_calls'] / 
                max(1, self.stats['modern_api_calls'] + self.stats['legacy_api_calls'])
                if (self.stats['modern_api_calls'] + self.stats['legacy_api_calls']) > 0 else 0
            ),
            'upgrade_recommended': (
                self.compat_config.mode != CompatibilityMode.MODERN and
                self.stats['warnings_issued'] >= self.compat_config.warning_threshold
            )
        }
    
    def create_compatibility_decorator(self):
        """Create a decorator for compatibility checking."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Check function name for compatibility
                func_name = func.__name__
                
                if self.should_issue_warning(func_name):
                    self.issue_api_warning(
                        func_name,
                        "Consider using modern interrupt handling API"
                    )
                
                # Execute function
                return func(*args, **kwargs)
            
            return wrapper
        
        return decorator


class CompatibilityValidator:
    """Validates compatibility configurations and API usage."""
    
    def __init__(self, config: InterruptConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def validate_config(self) -> List[str]:
        """Validate compatibility configuration."""
        errors = []
        
        # Check if compatibility mode is valid
        valid_modes = ['legacy', 'transitional', 'modern', 'disabled']
        if hasattr(self.config, 'compatibility_mode'):
            mode = getattr(self.config, 'compatibility_mode', 'modern')
            if mode not in valid_modes:
                errors.append(f"Invalid compatibility mode: {mode}")
        
        # Check warning threshold
        if hasattr(self.config, 'warning_threshold'):
            threshold = getattr(self.config, 'warning_threshold', 3)
            if not isinstance(threshold, int) or threshold < 1:
                errors.append(f"Invalid warning threshold: {threshold}")
        
        return errors
    
    def validate_api_usage(self, api_calls: List[str]) -> Dict[str, Any]:
        """Validate a list of API calls for compatibility."""
        validation_result = {
            'valid_calls': [],
            'deprecated_calls': [],
            'modern_calls': [],
            'warnings': [],
            'suggestions': []
        }
        
        for api_call in api_calls:
            if self._is_modern_api(api_call):
                validation_result['modern_calls'].append(api_call)
            else:
                validation_result['deprecated_calls'].append(api_call)
                validation_result['warnings'].append(
                    f"Deprecated API used: {api_call}"
                )
                validation_result['suggestions'].append(
                    f"Replace {api_call} with modern equivalent"
                )
        
        return validation_result
    
    def _is_modern_api(self, api_name: str) -> bool:
        """Check if an API is considered modern."""
        modern_apis = {
            'check_interrupt_status',
            'enter_critical_operation',
            'exit_critical_operation',
            'scrape_with_interrupt_handling',
            'register_interrupt_callback',
            'get_interrupt_statistics',
            'create_checkpoint',
            'cleanup_resources',
            'graceful_shutdown'
        }
        
        return api_name in modern_apis


# Convenience functions for easy migration
def create_compatible_handler(config: InterruptConfig) -> Union['InterruptAwareScraper', 'LegacyAPIWrapper']:
    """Create a handler that maintains backward compatibility."""
    manager = BackwardCompatibilityManager(config)
    
    # Initialize with placeholder components (would be injected in real usage)
    from .handler import InterruptHandler
    from .resource_manager import ResourceManager
    from .messaging import InterruptMessageHandler
    
    return manager.initialize_modern_handler(
        InterruptHandler(config),
        ResourceManager(config),
        InterruptMessageHandler(config)
    )


def migrate_to_modern_api(legacy_handler, config: InterruptConfig) -> InterruptAwareScraper:
    """Migrate from legacy handler to modern API."""
    logger = logging.getLogger(__name__)
    
    logger.info("Starting migration to modern interrupt handling API")
    
    # Create modern handler
    modern_handler = InterruptAwareScraper(config)
    
    # Copy state from legacy handler if possible
    if hasattr(legacy_handler, '_scraping_active'):
        modern_handler._scraping_active = legacy_handler._scraping_active
    
    if hasattr(legacy_handler, '_interrupted'):
        modern_handler._interrupted = legacy_handler._interrupted
    
    logger.info("Migration to modern API completed")
    return modern_handler


def check_api_compatibility(api_name: str, config: InterruptConfig) -> bool:
    """Check if an API call is compatible with current configuration."""
    manager = BackwardCompatibilityManager(config)
    
    if manager.compat_config.mode == CompatibilityMode.LEGACY:
        # All APIs allowed in legacy mode
        return True
    
    elif manager.compat_config.mode == CompatibilityMode.TRANSITIONAL:
        # Most APIs allowed, but warnings for deprecated ones
        return not manager._legacy_wrapper._is_deprecated_api(api_name)
    
    elif manager.compat_config.mode == CompatibilityMode.MODERN:
        # Only modern APIs allowed
        return manager._legacy_wrapper._is_new_api_usage(api_name)
    
    else:  # DISABLED
        return False
