"""
Navigation configuration management

Centralized configuration management for all navigation components with validation,
defaults, and environment-specific settings.
"""

import os
import json
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict, field


@dataclass
class RouteDiscoveryConfig:
    """Configuration for route discovery component"""
    max_discovery_time: int = 30
    max_routes_per_page: int = 10
    enable_client_side_detection: bool = True
    enable_form_analysis: bool = True
    enable_link_extraction: bool = True
    enable_dynamic_content_detection: bool = True
    discovery_timeout: int = 15
    max_depth: int = 3
    follow_external_links: bool = False
    respect_robots_txt: bool = True


@dataclass
class PathPlanningConfig:
    """Configuration for path planning component"""
    max_planning_time: int = 10
    optimization_enabled: bool = True
    risk_tolerance: float = 0.5
    time_preference: float = 0.5
    stealth_preference: float = 0.5
    max_alternative_paths: int = 3
    enable_graph_optimization: bool = True
    enable_timing_optimization: bool = True
    enable_risk_assessment: bool = True


@dataclass
class RouteAdaptationConfig:
    """Configuration for route adaptation component"""
    max_adaptation_attempts: int = 3
    adaptation_timeout: int = 15
    enable_retry_with_delay: bool = True
    enable_alternative_paths: bool = True
    enable_stealth_enhancement: bool = True
    enable_obstacle_avoidance: bool = True
    enable_graceful_degradation: bool = True
    retry_delay_base: float = 1.0
    retry_delay_multiplier: float = 1.5
    max_retry_delay: float = 30.0


@dataclass
class ContextManagerConfig:
    """Configuration for context management component"""
    max_context_age_hours: int = 24
    max_history_items: int = 1000
    auto_save_enabled: bool = True
    cleanup_interval_hours: int = 6
    enable_session_persistence: bool = True
    enable_authentication_tracking: bool = True
    enable_performance_tracking: bool = True
    storage_compression: bool = False
    max_storage_size_mb: int = 100


@dataclass
class RouteOptimizerConfig:
    """Configuration for route optimization component"""
    learning_enabled: bool = True
    performance_window_size: int = 50
    min_samples_for_optimization: int = 5
    optimization_threshold: float = 0.1
    max_alternative_routes: int = 3
    optimization_interval_hours: int = 1
    enable_timing_learning: bool = True
    enable_success_pattern_learning: bool = True
    enable_risk_pattern_learning: bool = True
    enable_adaptive_optimization: bool = True


@dataclass
class NavigationServiceConfig:
    """Configuration for navigation service"""
    enable_statistics: bool = True
    enable_metrics: bool = True
    enable_health_checks: bool = True
    max_concurrent_sessions: int = 100
    session_timeout_hours: int = 2
    enable_load_balancing: bool = False
    enable_caching: bool = True
    cache_ttl_minutes: int = 30
    enable_rate_limiting: bool = False


@dataclass
class NavigationConfig:
    """Main navigation configuration containing all component configs"""
    route_discovery: RouteDiscoveryConfig = field(default_factory=RouteDiscoveryConfig)
    path_planning: PathPlanningConfig = field(default_factory=PathPlanningConfig)
    route_adaptation: RouteAdaptationConfig = field(default_factory=RouteAdaptationConfig)
    context_manager: ContextManagerConfig = field(default_factory=ContextManagerConfig)
    route_optimizer: RouteOptimizerConfig = field(default_factory=RouteOptimizerConfig)
    navigation_service: NavigationServiceConfig = field(default_factory=NavigationServiceConfig)
    
    # Global settings
    storage_path: str = "data/navigation"
    log_level: str = "INFO"
    enable_correlation_ids: bool = True
    enable_schema_validation: bool = True
    environment: str = "production"
    
    # Performance settings
    max_memory_usage_mb: int = 512
    max_cpu_usage_percent: float = 80.0
    enable_performance_monitoring: bool = True
    
    # Security settings
    enable_encryption: bool = True
    encryption_key_rotation_days: int = 30
    enable_audit_logging: bool = True


class NavigationConfigManager:
    """Manager for navigation configuration with validation and environment support"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager"""
        self.config_path = config_path or "config/navigation.json"
        self._config: Optional[NavigationConfig] = None
        self._environment = os.getenv("NAVIGATION_ENV", "production")
    
    def load_config(self) -> NavigationConfig:
        """Load configuration from file or create default"""
        try:
            config_file = Path(self.config_path)
            
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Load with environment overrides
                self._config = self._load_from_dict(config_data)
            else:
                # Create default configuration
                self._config = NavigationConfig()
                
                # Save default configuration
                self.save_config()
            
            # Apply environment-specific overrides
            self._apply_environment_overrides()
            
            # Validate configuration
            self._validate_config()
            
            return self._config
            
        except Exception as e:
            raise ValueError(f"Failed to load navigation configuration: {e}")
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        if not self._config:
            self._config = NavigationConfig()
        
        try:
            config_file = Path(self.config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            config_dict = asdict(self._config)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, default=str)
                
        except Exception as e:
            raise ValueError(f"Failed to save navigation configuration: {e}")
    
    def get_config(self) -> NavigationConfig:
        """Get current configuration"""
        if not self._config:
            self.load_config()
        return self._config
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values"""
        if not self._config:
            self.load_config()
        
        self._update_config_object(self._config, updates)
        self._validate_config()
    
    def get_component_config(self, component: str) -> Dict[str, Any]:
        """Get configuration for specific component"""
        if not self._config:
            self.load_config()
        
        component_map = {
            "route_discovery": self._config.route_discovery,
            "path_planning": self._config.path_planning,
            "route_adaptation": self._config.route_adaptation,
            "context_manager": self._config.context_manager,
            "route_optimizer": self._config.route_optimizer,
            "navigation_service": self._config.navigation_service
        }
        
        if component not in component_map:
            raise ValueError(f"Unknown component: {component}")
        
        return asdict(component_map[component])
    
    def _load_from_dict(self, config_data: Dict[str, Any]) -> NavigationConfig:
        """Load configuration from dictionary"""
        # Extract component configs
        route_discovery_data = config_data.get("route_discovery", {})
        path_planning_data = config_data.get("path_planning", {})
        route_adaptation_data = config_data.get("route_adaptation", {})
        context_manager_data = config_data.get("context_manager", {})
        route_optimizer_data = config_data.get("route_optimizer", {})
        navigation_service_data = config_data.get("navigation_service", {})
        
        # Create component configs
        route_discovery = RouteDiscoveryConfig(**route_discovery_data)
        path_planning = PathPlanningConfig(**path_planning_data)
        route_adaptation = RouteAdaptationConfig(**route_adaptation_data)
        context_manager = ContextManagerConfig(**context_manager_data)
        route_optimizer = RouteOptimizerConfig(**route_optimizer_data)
        navigation_service = NavigationServiceConfig(**navigation_service_data)
        
        # Create main config
        return NavigationConfig(
            route_discovery=route_discovery,
            path_planning=path_planning,
            route_adaptation=route_adaptation,
            context_manager=context_manager,
            route_optimizer=route_optimizer,
            navigation_service=navigation_service,
            storage_path=config_data.get("storage_path", "data/navigation"),
            log_level=config_data.get("log_level", "INFO"),
            enable_correlation_ids=config_data.get("enable_correlation_ids", True),
            enable_schema_validation=config_data.get("enable_schema_validation", True),
            environment=config_data.get("environment", "production"),
            max_memory_usage_mb=config_data.get("max_memory_usage_mb", 512),
            max_cpu_usage_percent=config_data.get("max_cpu_usage_percent", 80.0),
            enable_performance_monitoring=config_data.get("enable_performance_monitoring", True),
            enable_encryption=config_data.get("enable_encryption", True),
            encryption_key_rotation_days=config_data.get("encryption_key_rotation_days", 30),
            enable_audit_logging=config_data.get("enable_audit_logging", True)
        )
    
    def _apply_environment_overrides(self) -> None:
        """Apply environment-specific configuration overrides"""
        if not self._config:
            return
        
        # Environment-specific overrides
        env_overrides = {
            "development": {
                "log_level": "DEBUG",
                "enable_schema_validation": False,
                "enable_performance_monitoring": True,
                "route_discovery": {"max_discovery_time": 60},
                "path_planning": {"max_planning_time": 30},
                "route_adaptation": {"max_adaptation_attempts": 5}
            },
            "testing": {
                "log_level": "INFO",
                "enable_schema_validation": True,
                "enable_performance_monitoring": False,
                "route_discovery": {"max_discovery_time": 10},
                "path_planning": {"max_planning_time": 5},
                "context_manager": {"max_context_age_hours": 1}
            },
            "staging": {
                "log_level": "INFO",
                "enable_schema_validation": True,
                "enable_performance_monitoring": True,
                "enable_audit_logging": True
            },
            "production": {
                "log_level": "WARNING",
                "enable_schema_validation": True,
                "enable_performance_monitoring": True,
                "enable_audit_logging": True,
                "enable_encryption": True
            }
        }
        
        if self._environment in env_overrides:
            overrides = env_overrides[self._environment]
            self._update_config_object(self._config, overrides)
    
    def _update_config_object(self, config_obj: Any, updates: Dict[str, Any]) -> None:
        """Update configuration object with new values"""
        for key, value in updates.items():
            if hasattr(config_obj, key):
                attr = getattr(config_obj, key)
                
                if isinstance(attr, (RouteDiscoveryConfig, PathPlanningConfig, 
                                   RouteAdaptationConfig, ContextManagerConfig,
                                   RouteOptimizerConfig, NavigationServiceConfig)):
                    # Update nested config objects
                    if isinstance(value, dict):
                        self._update_config_object(attr, value)
                else:
                    # Update simple attributes
                    setattr(config_obj, key, value)
    
    def _validate_config(self) -> None:
        """Validate configuration values"""
        if not self._config:
            return
        
        # Validate global settings
        if self._config.max_memory_usage_mb <= 0:
            raise ValueError("max_memory_usage_mb must be positive")
        
        if not 0 <= self._config.max_cpu_usage_percent <= 100:
            raise ValueError("max_cpu_usage_percent must be between 0 and 100")
        
        if self._config.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid log level: {self._config.log_level}")
        
        # Validate component configs
        self._validate_route_discovery_config()
        self._validate_path_planning_config()
        self._validate_route_adaptation_config()
        self._validate_context_manager_config()
        self._validate_route_optimizer_config()
        self._validate_navigation_service_config()
    
    def _validate_route_discovery_config(self) -> None:
        """Validate route discovery configuration"""
        config = self._config.route_discovery
        
        if config.max_discovery_time <= 0:
            raise ValueError("route_discovery.max_discovery_time must be positive")
        
        if config.max_routes_per_page <= 0:
            raise ValueError("route_discovery.max_routes_per_page must be positive")
        
        if config.max_depth < 0:
            raise ValueError("route_discovery.max_depth must be non-negative")
    
    def _validate_path_planning_config(self) -> None:
        """Validate path planning configuration"""
        config = self._config.path_planning
        
        if config.max_planning_time <= 0:
            raise ValueError("path_planning.max_planning_time must be positive")
        
        if not 0 <= config.risk_tolerance <= 1:
            raise ValueError("path_planning.risk_tolerance must be between 0 and 1")
        
        if not 0 <= config.time_preference <= 1:
            raise ValueError("path_planning.time_preference must be between 0 and 1")
        
        if not 0 <= config.stealth_preference <= 1:
            raise ValueError("path_planning.stealth_preference must be between 0 and 1")
        
        if config.max_alternative_paths <= 0:
            raise ValueError("path_planning.max_alternative_paths must be positive")
    
    def _validate_route_adaptation_config(self) -> None:
        """Validate route adaptation configuration"""
        config = self._config.route_adaptation
        
        if config.max_adaptation_attempts <= 0:
            raise ValueError("route_adaptation.max_adaptation_attempts must be positive")
        
        if config.adaptation_timeout <= 0:
            raise ValueError("route_adaptation.adaptation_timeout must be positive")
        
        if config.retry_delay_base <= 0:
            raise ValueError("route_adaptation.retry_delay_base must be positive")
        
        if config.retry_delay_multiplier <= 0:
            raise ValueError("route_adaptation.retry_delay_multiplier must be positive")
        
        if config.max_retry_delay <= 0:
            raise ValueError("route_adaptation.max_retry_delay must be positive")
    
    def _validate_context_manager_config(self) -> None:
        """Validate context manager configuration"""
        config = self._config.context_manager
        
        if config.max_context_age_hours <= 0:
            raise ValueError("context_manager.max_context_age_hours must be positive")
        
        if config.max_history_items <= 0:
            raise ValueError("context_manager.max_history_items must be positive")
        
        if config.cleanup_interval_hours <= 0:
            raise ValueError("context_manager.cleanup_interval_hours must be positive")
        
        if config.max_storage_size_mb <= 0:
            raise ValueError("context_manager.max_storage_size_mb must be positive")
    
    def _validate_route_optimizer_config(self) -> None:
        """Validate route optimizer configuration"""
        config = self._config.route_optimizer
        
        if config.performance_window_size <= 0:
            raise ValueError("route_optimizer.performance_window_size must be positive")
        
        if config.min_samples_for_optimization <= 0:
            raise ValueError("route_optimizer.min_samples_for_optimization must be positive")
        
        if not 0 <= config.optimization_threshold <= 1:
            raise ValueError("route_optimizer.optimization_threshold must be between 0 and 1")
        
        if config.max_alternative_routes <= 0:
            raise ValueError("route_optimizer.max_alternative_routes must be positive")
        
        if config.optimization_interval_hours <= 0:
            raise ValueError("route_optimizer.optimization_interval_hours must be positive")
    
    def _validate_navigation_service_config(self) -> None:
        """Validate navigation service configuration"""
        config = self._config.navigation_service
        
        if config.max_concurrent_sessions <= 0:
            raise ValueError("navigation_service.max_concurrent_sessions must be positive")
        
        if config.session_timeout_hours <= 0:
            raise ValueError("navigation_service.session_timeout_hours must be positive")
        
        if config.cache_ttl_minutes <= 0:
            raise ValueError("navigation_service.cache_ttl_minutes must be positive")


# Global configuration manager instance
_config_manager: Optional[NavigationConfigManager] = None


def get_config_manager(config_path: Optional[str] = None) -> NavigationConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = NavigationConfigManager(config_path)
    
    return _config_manager


def get_navigation_config(config_path: Optional[str] = None) -> NavigationConfig:
    """Get navigation configuration"""
    return get_config_manager(config_path).get_config()


def load_navigation_config(config_path: Optional[str] = None) -> NavigationConfig:
    """Load navigation configuration"""
    return get_config_manager(config_path).load_config()
