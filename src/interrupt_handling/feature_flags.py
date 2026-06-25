"""
Feature flags for interrupt handling system.
"""

import logging
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from .config import InterruptConfig


class FlagType(Enum):
    """Types of feature flags."""
    BOOLEAN = "boolean"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"


@dataclass
class FeatureFlag:
    """Represents a single feature flag."""
    name: str
    flag_type: FlagType
    default_value: Any
    description: str
    env_var: Optional[str] = None
    category: str = "general"
    requires_restart: bool = False


@dataclass
class FeatureFlagConfig:
    """Configuration for all feature flags."""
    flags: Dict[str, FeatureFlag] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default feature flags."""
        if not self.flags:
            self._create_default_flags()
    
    def _create_default_flags(self):
        """Create default feature flags."""
        self.flags = {
            # Core interrupt handling
            'interrupt_handling_enabled': FeatureFlag(
                name='interrupt_handling_enabled',
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description='Enable interrupt handling system',
                env_var='SCRAPAMOJA_INTERRUPT_ENABLED',
                category='core'
            ),
            
            # Signal handling
            'handle_sigint': FeatureFlag(
                name='handle_sigint',
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description='Handle SIGINT signals',
                env_var='SCRAPAMOJA_HANDLE_SIGINT',
                category='signals'
            ),
            
            'handle_sigterm': FeatureFlag(
                name='handle_sigterm',
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description='Handle SIGTERM signals',
                env_var='SCRAPAMOJA_HANDLE_SIGTERM',
                category='signals'
            ),
            
            'handle_sigbreak': FeatureFlag(
                name='handle_sigbreak',
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description='Handle SIGBREAK signals (Windows)',
                env_var='SCRAPAMOJA_HANDLE_SIGBREAK',
                category='signals'
            ),
            
            # Resource cleanup
            'resource_cleanup_enabled': FeatureFlag(
                name='resource_cleanup_enabled',
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description='Enable automatic resource cleanup',
                env_var='SCRAPAMOJA_RESOURCE_CLEANUP_ENABLED',
                category='cleanup'
            ),
            
            'parallel_cleanup_enabled': FeatureFlag(
                name='parallel_cleanup_enabled',
                flag_type=FlagType.BOOLEAN,
                default_value=False,
                description='Enable parallel cleanup execution',
                env_var='SCRAPAMOJA_PARALLEL_CLEANUP',
                category='cleanup'
            ),
            
            # Data preservation
            'checkpoints_enabled': FeatureFlag(
                name='checkpoints_enabled',
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description='Enable checkpoint creation',
                env_var='SCRAPAMOJA_CHECKPOINTS_ENABLED',
                category='data'
            ),
            
            'auto_checkpoint_interval': FeatureFlag(
                name='auto_checkpoint_interval',
                flag_type=FlagType.FLOAT,
                default_value=60.0,
                description='Auto-checkpoint interval in seconds',
                env_var='SCRAPAMOJA_CHECKPOINT_INTERVAL',
                category='data'
            ),
            
            # User feedback
            'user_feedback_enabled': FeatureFlag(
                name='user_feedback_enabled',
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description='Enable user feedback messages',
                env_var='SCRAPAMOJA_USER_FEEDBACK_ENABLED',
                category='feedback'
            ),
            
            'progress_bars_enabled': FeatureFlag(
                name='progress_bars_enabled',
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description='Enable progress bars',
                env_var='SCRAPAMOJA_PROGRESS_BARS',
                category='feedback'
            ),
            
            'colored_output_enabled': FeatureFlag(
                name='colored_output_enabled',
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description='Enable colored terminal output',
                env_var='SCRAPAMOJA_COLORED_OUTPUT',
                category='feedback'
            ),
            
            'icons_enabled': FeatureFlag(
                name='icons_enabled',
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description='Enable icons in output',
                env_var='SCRAPAMOJA_ICONS_ENABLED',
                category='feedback'
            ),
            
            # Logging
            'shutdown_logging_enabled': FeatureFlag(
                name='shutdown_logging_enabled',
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description='Enable shutdown logging',
                env_var='SCRAPAMOJA_SHUTDOWN_LOGGING',
                category='logging'
            ),
            
            'debug_logging_enabled': FeatureFlag(
                name='debug_logging_enabled',
                flag_type=FlagType.BOOLEAN,
                default_value=False,
                description='Enable debug logging',
                env_var='SCRAPAMOJA_DEBUG_LOGGING',
                category='logging'
            ),
            
            # Graceful shutdown
            'graceful_shutdown_enabled': FeatureFlag(
                name='graceful_shutdown_enabled',
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description='Enable graceful shutdown coordination',
                env_var='SCRAPAMOJA_GRACEFUL_SHUTDOWN',
                category='shutdown'
            ),
            
            'force_termination_enabled': FeatureFlag(
                name='force_termination_enabled',
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description='Enable force termination on timeout',
                env_var='SCRAPAMOJA_FORCE_TERMINATION',
                category='shutdown'
            ),
            
            # Experimental features
            'experimental_features_enabled': FeatureFlag(
                name='experimental_features_enabled',
                flag_type=FlagType.BOOLEAN,
                default_value=False,
                description='Enable experimental interrupt handling features',
                env_var='SCRAPAMOJA_EXPERIMENTAL',
                category='experimental'
            ),
            
            # Performance
            'performance_monitoring_enabled': FeatureFlag(
                name='performance_monitoring_enabled',
                flag_type=FlagType.BOOLEAN,
                default_value=False,
                description='Enable performance monitoring',
                env_var='SCRAPAMOJA_PERFORMANCE_MONITORING',
                category='performance'
            ),
            
            # Testing
            'testing_mode_enabled': FeatureFlag(
                name='testing_mode_enabled',
                flag_type=FlagType.BOOLEAN,
                default_value=False,
                description='Enable testing mode',
                env_var='SCRAPAMOJA_TESTING_MODE',
                category='testing'
            )
        }
    
    def get_flag(self, name: str) -> Optional[FeatureFlag]:
        """Get a feature flag by name."""
        return self.flags.get(name)
    
    def set_flag(self, name: str, value: Any):
        """Set a feature flag value."""
        if name in self.flags:
            flag = self.flags[name]
            flag.default_value = value
            self.logger.debug(f"Updated feature flag {name}: {value}")
        else:
            self.logger.warning(f"Unknown feature flag: {name}")
    
    def get_flag_value(self, name: str) -> Any:
        """Get the current value of a feature flag."""
        flag = self.get_flag(name)
        if flag:
            # Check environment variable first
            if flag.env_var and flag.env_var in os.environ:
                env_value = os.environ[flag.env_var]
                return self._parse_env_value(env_value, flag.flag_type)
            
            # Return default value
            return flag.default_value
        
        return None
    
    def _parse_env_value(self, env_value: str, flag_type: FlagType) -> Any:
        """Parse environment variable value based on flag type."""
        try:
            if flag_type == FlagType.BOOLEAN:
                return env_value.lower() in ('true', '1', 'yes', 'on')
            elif flag_type == FlagType.INTEGER:
                return int(env_value)
            elif flag_type == FlagType.FLOAT:
                return float(env_value)
            elif flag_type == FlagType.STRING:
                return env_value
            else:
                return env_value
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid environment value for {flag_type}: {env_value}")
            return None
    
    def is_enabled(self, name: str) -> bool:
        """Check if a boolean feature flag is enabled."""
        value = self.get_flag_value(name)
        return bool(value) if value is not None else False
    
    def load_from_environment(self):
        """Load all feature flags from environment variables."""
        for flag_name, flag in self.flags.items():
            if flag.env_var and flag.env_var in os.environ:
                env_value = os.environ[flag.env_var]
                parsed_value = self._parse_env_value(env_value, flag.flag_type)
                if parsed_value is not None:
                    flag.default_value = parsed_value
                    self.logger.debug(f"Loaded flag {flag_name} from environment: {parsed_value}")
    
    def get_flags_by_category(self, category: str) -> List[FeatureFlag]:
        """Get all flags in a specific category."""
        return [flag for flag in self.flags.values() if flag.category == category]
    
    def validate_flags(self) -> List[str]:
        """Validate all feature flags."""
        errors = []
        
        for flag_name, flag in self.flags.items():
            # Check flag name
            if not flag.name or not isinstance(flag.name, str):
                errors.append(f"Invalid flag name for {flag_name}")
            
            # Check environment variable name
            if flag.env_var and not isinstance(flag.env_var, str):
                errors.append(f"Invalid environment variable for {flag_name}")
            
            # Check description
            if not flag.description or not isinstance(flag.description, str):
                errors.append(f"Invalid description for {flag_name}")
            
            # Check category
            if not flag.category or not isinstance(flag.category, str):
                errors.append(f"Invalid category for {flag_name}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert all flags to dictionary."""
        return {
            flag_name: {
                'value': flag.default_value,
                'type': flag.flag_type.value,
                'description': flag.description,
                'environment_variable': flag.env_var,
                'category': flag.category,
                'requires_restart': flag.requires_restart
            }
            for flag_name, flag in self.flags.items()
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of feature flag configuration."""
        categories = {}
        for flag in self.flags.values():
            if flag.category not in categories:
                categories[flag.category] = {
                    'total': 0,
                    'enabled': 0,
                    'disabled': 0
                }
            
            categories[flag.category]['total'] += 1
            
            if bool(flag.default_value):
                categories[flag.category]['enabled'] += 1
            else:
                categories[flag.category]['disabled'] += 1
        
        return {
            'total_flags': len(self.flags),
            'categories': categories,
            'enabled_count': sum(cat['enabled'] for cat in categories.values()),
            'disabled_count': sum(cat['disabled'] for cat in categories.values())
        }


class FeatureFlagManager:
    """Manages feature flags for interrupt handling system."""
    
    def __init__(self, config: InterruptConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize feature flag configuration
        self.flag_config = FeatureFlagConfig()
        
        # Load from environment
        self.flag_config.load_from_environment()
        
        # Validate configuration
        self._validate_and_fix()
    
    def _validate_and_fix(self):
        """Validate and fix feature flag configuration."""
        errors = self.flag_config.validate_flags()
        
        if errors:
            self.logger.warning(f"Feature flag configuration errors: {errors}")
            # Apply automatic fixes where possible
            self._apply_fixes(errors)
    
    def _apply_fixes(self, errors: List[str]):
        """Apply automatic fixes for feature flag errors."""
        for error in errors:
            if "Invalid flag name" in error:
                # This would require more specific intervention
                continue
            elif "Invalid environment variable" in error:
                # Fix environment variable names
                self._fix_environment_variables()
            elif "Invalid description" in error:
                # Fix descriptions
                self._fix_descriptions()
    
    def _fix_environment_variables(self):
        """Fix invalid environment variable names."""
        # This would implement automatic fixes for common issues
        pass
    
    def _fix_descriptions(self):
        """Fix invalid descriptions."""
        # This would implement automatic fixes for missing descriptions
        pass
    
    def is_enabled(self, flag_name: str) -> bool:
        """Check if a feature flag is enabled."""
        return self.flag_config.is_enabled(flag_name)
    
    def get_flag_value(self, flag_name: str) -> Any:
        """Get the value of a feature flag."""
        return self.flag_config.get_flag_value(flag_name)
    
    def set_flag(self, flag_name: str, value: Any):
        """Set a feature flag value."""
        self.flag_config.set_flag(flag_name, value)
    
    def get_all_flags(self) -> Dict[str, Any]:
        """Get all feature flag values."""
        return {name: flag.default_value for name, flag in self.flag_config.flags.items()}
    
    def get_flags_by_category(self, category: str) -> Dict[str, Any]:
        """Get all flags in a category."""
        category_flags = self.flag_config.get_flags_by_category(category)
        return {flag.name: flag.default_value for flag in category_flags}
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get summary of feature flag configuration."""
        return self.flag_config.get_summary()
    
    def apply_to_config(self, config: InterruptConfig) -> InterruptConfig:
        """Apply feature flags to configuration object."""
        # Core features
        if self.is_enabled('interrupt_handling_enabled'):
            config.enable_interrupt_handling = True
        
        # Signal handling
        config.handle_sigint = self.is_enabled('handle_sigint')
        config.handle_sigterm = self.is_enabled('handle_sigterm')
        config.handle_sigbreak = self.is_enabled('handle_sigbreak')
        
        # Resource cleanup
        config.enable_resource_cleanup = self.is_enabled('resource_cleanup_enabled')
        config.enable_parallel_cleanup = self.is_enabled('parallel_cleanup_enabled')
        
        # Data preservation
        config.enable_checkpoints = self.is_enabled('checkpoints_enabled')
        
        checkpoint_interval = self.get_flag_value('auto_checkpoint_interval')
        if checkpoint_interval is not None:
            config.checkpoint_interval = float(checkpoint_interval)
        
        # User feedback
        config.enable_user_feedback = self.is_enabled('user_feedback_enabled')
        config.enable_progress_bars = self.is_enabled('progress_bars_enabled')
        config.enable_colors = self.is_enabled('colored_output_enabled')
        config.enable_icons = self.is_enabled('icons_enabled')
        
        # Logging
        config.enable_shutdown_logging = self.is_enabled('shutdown_logging_enabled')
        
        debug_enabled = self.is_enabled('debug_logging_enabled')
        config.log_level = 'DEBUG' if debug_enabled else 'INFO'
        
        # Graceful shutdown
        config.enable_graceful_shutdown = self.is_enabled('graceful_shutdown_enabled')
        config.shutdown_coordinator_enabled = config.enable_graceful_shutdown
        
        # Apply experimental features with warnings
        if self.is_enabled('experimental_features_enabled'):
            self.logger.warning("Experimental features are enabled - use with caution")
        
        return config
    
    def get_feature_documentation(self) -> str:
        """Generate documentation for all feature flags."""
        doc_lines = [
            "# Interrupt Handling Feature Flags",
            "",
            "Feature flags can be set using environment variables or programmatically.",
            "",
            "## Categories",
            ""
        ]
        
        # Group flags by category
        categories = {}
        for flag in self.flag_config.flags.values():
            if flag.category not in categories:
                categories[flag.category] = []
            categories[flag.category].append(flag)
        
        # Generate documentation for each category
        for category, flags in sorted(categories.items()):
            doc_lines.extend([
                f"### {category.title()}",
                ""
            ])
            
            for flag in sorted(flags, key=lambda f: f.name):
                env_var = f" (env: {flag.env_var})" if flag.env_var else ""
                doc_lines.extend([
                    f"**{flag.name}**{env_var}",
                    f"- {flag.description}",
                    f"- Type: {flag.flag_type.value}",
                    f"- Default: {flag.default_value}",
                    f"- Requires restart: {flag.requires_restart}",
                    ""
                ])
        
        return "\n".join(doc_lines)
