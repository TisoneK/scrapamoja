"""
Feature Flags

Manages feature flags for gradual rollout and A/B testing of new features.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from ..logging.resilience_logger import get_logger


logger = get_logger("feature_flags")


@dataclass
class FeatureFlags:
    """Feature flags for retry consolidation."""
    
    # Retry consolidation flags
    use_centralized_retry: bool = field(
        default_factory=lambda: os.getenv("USE_CENTRALIZED_RETRY", "false").lower() == "true",
        metadata={"description": "Use centralized retry module instead of local implementations"}
    )
    
    # Subsystem-specific flags
    browser_use_centralized: bool = field(
        default_factory=lambda: os.getenv("BROWSER_USE_CENTRALIZED_RETRY", "false").lower() == "true",
        metadata={"description": "Browser subsystem uses centralized retry"}
    )
    navigation_use_centralized: bool = field(
        default_factory=lambda: os.getenv("NAVIGATION_USE_CENTRALIZED_RETRY", "false").lower() == "true",
        metadata={"description": "Navigation subsystem uses centralized retry"}
    )
    telemetry_use_centralized: bool = field(
        default_factory=lambda: os.getenv("TELEMETRY_USE_CENTRALIZED_RETRY", "false").lower() == "true",
        metadata={"description": "Telemetry subsystem uses centralized retry"}
    )
    
    # Configuration flags
    enable_hot_reload: bool = field(
        default_factory=lambda: os.getenv("ENABLE_HOT_RELOAD", "true").lower() == "true",
        metadata={"description": "Enable hot-reload of retry configuration"}
    )
    
    # Testing flags
    enable_retry_tests: bool = field(
        default_factory=lambda: os.getenv("ENABLE_RETRY_TESTS", "true").lower() == "true",
        metadata={"description": "Enable retry-related tests"}
    )
    
    # Migration flags
    enable_migration_mode: bool = field(
        default_factory=lambda: os.getenv("ENABLE_MIGRATION_MODE", "false").lower() == "true",
        metadata={"description": "Enable migration mode for gradual rollout"}
    )
    
    # Monitoring flags
    enable_retry_metrics: bool = field(
        default_factory=lambda: os.getenv("ENABLE_RETRY_METRICS", "true").lower() == "true",
        metadata={"description": "Enable retry metrics collection and reporting"}
    )
    
    def __post_init__(self):
        """Initialize feature flags from environment variables."""
        logger.info(
            "Feature flags initialized",
            use_centralized_retry=self.use_centralized_retry,
            browser_use_centralized=self.browser_use_centralized,
            navigation_use_centralized=self.navigation_use_centralized,
            telemetry_use_centralized=self.telemetry_use_centralized,
            enable_hot_reload=self.enable_hot_reload,
            enable_retry_tests=self.enable_retry_tests,
            enable_migration_mode=self.enable_migration_mode,
            enable_retry_metrics=self.enable_retry_metrics,
            component="feature_flags"
        )
    
    def is_enabled(self, flag_name: str) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            flag_name: Name of feature flag
            
        Returns:
            True if enabled, False otherwise
        """
        return getattr(self, flag_name, False)
    
    def get_all_flags(self) -> Dict[str, Any]:
        """
        Get all feature flags and their values.
        
        Returns:
            Dictionary of all feature flags
        """
        return {
            "use_centralized_retry": self.use_centralized_retry,
            "browser_use_centralized": self.browser_use_centralized,
            "navigation_use_centralized": self.navigation_use_centralized,
            "telemetry_use_centralized": self.telemetry_use_centralized,
            "enable_hot_reload": self.enable_hot_reload,
            "enable_retry_tests": self.enable_retry_tests,
            "enable_migration_mode": self.enable_migration_mode,
            "enable_retry_metrics": self.enable_retry_metrics
        }


# Global feature flags instance
_feature_flags: Optional[FeatureFlags] = None


def get_feature_flags() -> FeatureFlags:
    """
    Get or create global feature flags instance.
    
    Returns:
        Feature flags instance
    """
    global _feature_flags
    
    if _feature_flags is None:
        _feature_flags = FeatureFlags()
    
    return _feature_flags


def is_feature_enabled(flag_name: str) -> bool:
    """
    Check if a feature flag is enabled.
    
    Args:
        flag_name: Name of the feature flag
        
    Returns:
        True if enabled, False otherwise
    """
    flags = get_feature_flags()
    return flags.is_enabled(flag_name)
