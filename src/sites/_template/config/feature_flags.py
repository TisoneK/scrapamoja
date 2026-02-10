"""
Feature flags configuration for the modular site scraper template.

This module provides feature flag management for enabling/disabling
features dynamically across different environments.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import os
import json


class FlagType(Enum):
    """Types of feature flags."""
    BOOLEAN = "boolean"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    JSON = "json"


@dataclass
class FeatureFlag:
    """Individual feature flag definition."""
    name: str
    flag_type: FlagType
    default_value: Any
    description: str = ""
    environments: List[str] = field(default_factory=lambda: ["dev", "staging", "prod"])
    rollout_percentage: float = 100.0
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate feature flag after creation."""
        if not self.name:
            raise ValueError("Feature flag name is required")
        
        if self.rollout_percentage < 0 or self.rollout_percentage > 100:
            raise ValueError("Rollout percentage must be between 0 and 100")


class FeatureFlags:
    """Feature flags manager for the modular scraper."""
    
    def __init__(self, environment: str = "dev"):
        """
        Initialize feature flags manager.
        
        Args:
            environment: Target environment
        """
        self.environment = environment
        self._flags: Dict[str, FeatureFlag] = {}
        self._runtime_values: Dict[str, Any] = {}
        
        # Initialize default flags
        self._initialize_default_flags()
        
        # Load environment-specific overrides
        self._load_environment_overrides()
    
    def _initialize_default_flags(self) -> None:
        """Initialize default feature flags."""
        default_flags = [
            # Core functionality flags
            FeatureFlag(
                name="enable_stealth_mode",
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description="Enable stealth mode for anti-detection",
                environments=["dev", "staging", "prod"],
                tags=["security", "stealth"]
            ),
            
            FeatureFlag(
                name="enable_circuit_breaker",
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description="Enable circuit breaker for resilience",
                environments=["dev", "staging", "prod"],
                tags=["resilience", "circuit_breaker"]
            ),
            
            FeatureFlag(
                name="enable_retry_with_backoff",
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description="Enable retry with exponential backoff",
                environments=["dev", "staging", "prod"],
                tags=["resilience", "retry"]
            ),
            
            # Performance flags
            FeatureFlag(
                name="enable_performance_monitoring",
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description="Enable performance monitoring and metrics",
                environments=["dev", "staging", "prod"],
                tags=["performance", "monitoring"]
            ),
            
            FeatureFlag(
                name="enable_structured_logging",
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description="Enable structured JSON logging",
                environments=["dev", "staging", "prod"],
                tags=["logging", "structured"]
            ),
            
            # Data collection flags
            FeatureFlag(
                name="enable_screenshots",
                flag_type=FlagType.BOOLEAN,
                default_value=False,
                description="Enable screenshot capture",
                environments=["dev"],
                tags=["data", "screenshots"]
            ),
            
            FeatureFlag(
                name="enable_html_capture",
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description="Enable HTML content capture",
                environments=["dev", "staging"],
                tags=["data", "html"]
            ),
            
            FeatureFlag(
                name="max_results",
                flag_type=FlagType.INTEGER,
                default_value=100,
                description="Maximum number of results to collect",
                environments=["dev", "staging", "prod"],
                tags=["data", "limits"]
            ),
            
            # Rate limiting flags
            FeatureFlag(
                name="requests_per_minute",
                flag_type=FlagType.INTEGER,
                default_value=60,
                description="Maximum requests per minute",
                environments=["dev", "staging", "prod"],
                tags=["rate_limiting", "performance"]
            ),
            
            FeatureFlag(
                name="delay_between_requests_ms",
                flag_type=FlagType.INTEGER,
                default_value=1000,
                description="Delay between requests in milliseconds",
                environments=["dev", "staging", "prod"],
                tags=["rate_limiting", "performance"]
            ),
            
            # Debug flags
            FeatureFlag(
                name="debug_mode",
                flag_type=FlagType.BOOLEAN,
                default_value=False,
                description="Enable debug mode with verbose logging",
                environments=["dev"],
                tags=["debug", "logging"]
            ),
            
            FeatureFlag(
                name="headless_mode",
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description="Run browser in headless mode",
                environments=["dev", "staging", "prod"],
                tags=["browser", "ui"]
            ),
            
            # Experimental flags
            FeatureFlag(
                name="enable_ai_processing",
                flag_type=FlagType.BOOLEAN,
                default_value=False,
                description="Enable AI-powered data processing",
                environments=["dev"],
                rollout_percentage=10.0,
                tags=["experimental", "ai"]
            ),
            
            FeatureFlag(
                name="enable_cache",
                flag_type=FlagType.BOOLEAN,
                default_value=True,
                description="Enable result caching",
                environments=["dev", "staging", "prod"],
                tags=["performance", "cache"]
            )
        ]
        
        for flag in default_flags:
            self._flags[flag.name] = flag
    
    def _load_environment_overrides(self) -> None:
        """Load environment-specific flag overrides."""
        # Environment-specific overrides
        env_overrides = {
            "dev": {
                "enable_screenshots": True,
                "debug_mode": True,
                "headless_mode": False,
                "max_results": 20,
                "requests_per_minute": 120,
                "delay_between_requests_ms": 500
            },
            "staging": {
                "enable_screenshots": False,
                "debug_mode": False,
                "headless_mode": True,
                "max_results": 200,
                "requests_per_minute": 60,
                "delay_between_requests_ms": 1000
            },
            "prod": {
                "enable_screenshots": False,
                "debug_mode": False,
                "headless_mode": True,
                "max_results": 1000,
                "requests_per_minute": 30,
                "delay_between_requests_ms": 2000
            }
        }
        
        if self.environment in env_overrides:
            for flag_name, value in env_overrides[self.environment].items():
                if flag_name in self._flags:
                    self._runtime_values[flag_name] = value
    
    def is_enabled(self, flag_name: str, user_id: Optional[str] = None) -> bool:
        """
        Check if a boolean feature flag is enabled.
        
        Args:
            flag_name: Name of the feature flag
            user_id: Optional user ID for percentage-based rollouts
            
        Returns:
            True if flag is enabled, False otherwise
        """
        flag = self._flags.get(flag_name)
        if not flag:
            return False
        
        if flag.flag_type != FlagType.BOOLEAN:
            raise ValueError(f"Flag {flag_name} is not a boolean flag")
        
        # Check if flag is available in current environment
        if self.environment not in flag.environments:
            return False
        
        # Get runtime value or default
        value = self._runtime_values.get(flag_name, flag.default_value)
        
        # Apply percentage-based rollout
        if flag.rollout_percentage < 100.0 and user_id:
            import random
            user_hash = hash(user_id) % 100
            if user_hash >= flag.rollout_percentage:
                return False
        
        return bool(value)
    
    def get_value(self, flag_name: str, default_value: Any = None) -> Any:
        """
        Get the value of a feature flag.
        
        Args:
            flag_name: Name of the feature flag
            default_value: Default value if flag doesn't exist
            
        Returns:
            Flag value or default
        """
        flag = self._flags.get(flag_name)
        if not flag:
            return default_value
        
        # Check if flag is available in current environment
        if self.environment not in flag.environments:
            return default_value
        
        return self._runtime_values.get(flag_name, flag.default_value)
    
    def set_value(self, flag_name: str, value: Any) -> bool:
        """
        Set the runtime value of a feature flag.
        
        Args:
            flag_name: Name of the feature flag
            value: New value
            
        Returns:
            True if successful, False otherwise
        """
        flag = self._flags.get(flag_name)
        if not flag:
            return False
        
        # Validate value type
        if flag.flag_type == FlagType.BOOLEAN:
            value = bool(value)
        elif flag.flag_type == FlagType.INTEGER:
            value = int(value)
        elif flag.flag_type == FlagType.FLOAT:
            value = float(value)
        elif flag.flag_type == FlagType.STRING:
            value = str(value)
        
        self._runtime_values[flag_name] = value
        return True
    
    def get_all_flags(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all feature flags with their current values.
        
        Returns:
            Dictionary of all flags
        """
        result = {}
        
        for flag_name, flag in self._flags.items():
            if self.environment in flag.environments:
                result[flag_name] = {
                    "name": flag.name,
                    "type": flag.flag_type.value,
                    "default_value": flag.default_value,
                    "current_value": self._runtime_values.get(flag_name, flag.default_value),
                    "description": flag.description,
                    "rollout_percentage": flag.rollout_percentage,
                    "tags": flag.tags
                }
        
        return result
    
    def get_flags_by_tag(self, tag: str) -> Dict[str, Dict[str, Any]]:
        """
        Get feature flags filtered by tag.
        
        Args:
            tag: Tag to filter by
            
        Returns:
            Dictionary of flags with the specified tag
        """
        all_flags = self.get_all_flags()
        return {
            name: flag_info 
            for name, flag_info in all_flags.items() 
            if tag in flag_info["tags"]
        }
    
    def export_config(self) -> Dict[str, Any]:
        """
        Export current feature flag configuration.
        
        Returns:
            Configuration dictionary
        """
        return {
            "environment": self.environment,
            "flags": self.get_all_flags(),
            "runtime_values": self._runtime_values
        }
    
    def import_config(self, config: Dict[str, Any]) -> bool:
        """
        Import feature flag configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if "runtime_values" in config:
                for flag_name, value in config["runtime_values"].items():
                    if flag_name in self._flags:
                        self._runtime_values[flag_name] = value
            
            return True
            
        except Exception:
            return False
    
    def save_to_file(self, file_path: str) -> bool:
        """
        Save feature flag configuration to file.
        
        Args:
            file_path: Path to save configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            config = self.export_config()
            
            # Ensure directory exists
            import os
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            return True
            
        except Exception:
            return False
    
    def load_from_file(self, file_path: str) -> bool:
        """
        Load feature flag configuration from file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'r') as f:
                config = json.load(f)
            
            return self.import_config(config)
            
        except Exception:
            return False
