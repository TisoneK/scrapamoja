"""
Feature Flag Service for managing sport-based adaptive system enablement.

This implements Story 8.1 (Sport-Based Feature Flags) requirements:
- CRUD operations for feature flags
- Sport-specific adaptive system control
- Site-specific override capabilities
- Performance-optimized flag lookup with caching
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
from functools import lru_cache

from ..db.repositories.feature_flag_repository import FeatureFlagRepository
from ..db.models.feature_flag import FeatureFlag
from src.observability.logger import get_logger


class FeatureFlagService:
    """Service for managing sport-based feature flags."""
    
    def __init__(self, db_path: Optional[str] = None, cache_ttl: int = 60):
        """
        Initialize feature flag service.
        
        Args:
            db_path: Optional path to SQLite database file
            cache_ttl: Cache time-to-live in seconds for flag lookups
        """
        self._logger = get_logger("feature_flag_service")
        self._repository = FeatureFlagRepository(db_path)
        self._cache_ttl = cache_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, float] = {}
    
    def _get_cache_key(self, sport: str, site: Optional[str] = None) -> str:
        """Generate cache key for sport/site combination."""
        site_part = f"@{site}" if site else ""
        return f"{sport.lower()}{site_part}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        
        age = datetime.utcnow().timestamp() - self._cache_timestamps[cache_key]
        return age < self._cache_ttl
    
    def _update_cache(self, cache_key: str, enabled: bool) -> None:
        """Update cache with new flag value."""
        self._cache[cache_key] = {"enabled": enabled}
        self._cache_timestamps[cache_key] = datetime.utcnow().timestamp()
    
    def _get_from_cache(self, cache_key: str) -> Optional[bool]:
        """Get flag value from cache if valid."""
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]["enabled"]
        return None
    
    def create_feature_flag(
        self,
        sport: str,
        site: Optional[str] = None,
        enabled: bool = False,
    ) -> FeatureFlag:
        """
        Create a new feature flag.
        
        Args:
            sport: Sport name (e.g., "basketball", "tennis")
            site: Optional site name for site-specific flags
            enabled: Whether the adaptive system is enabled for this sport/site
            
        Returns:
            Created feature flag
            
        Raises:
            ValueError: If flag already exists for sport/site combination
        """
        # Check if flag already exists
        existing = self._repository.get_feature_flag(sport, site)
        if existing:
            site_desc = f" for site {site}" if site else ""
            raise ValueError(f"Feature flag already exists for sport {sport}{site_desc}")
        
        flag = self._repository.create_feature_flag(sport, site, enabled)
        
        # Invalidate cache for this sport/site
        cache_key = self._get_cache_key(sport, site)
        if cache_key in self._cache:
            del self._cache[cache_key]
            del self._cache_timestamps[cache_key]
        
        self._logger.info(
            f"Created feature flag: sport={sport}, site={site}, enabled={enabled}"
        )
        return flag
    
    def get_feature_flag(
        self,
        sport: str,
        site: Optional[str] = None,
    ) -> Optional[FeatureFlag]:
        """
        Get feature flag by sport and site.
        
        Args:
            sport: Sport name
            site: Optional site name
            
        Returns:
            Feature flag if found, None otherwise
        """
        return self._repository.get_feature_flag(sport, site)
    
    def get_all_feature_flags(self) -> List[FeatureFlag]:
        """
        Get all feature flags.
        
        Returns:
            List of all feature flags
        """
        return self._repository.get_all_feature_flags()
    
    def get_feature_flags_by_sport(self, sport: str) -> List[FeatureFlag]:
        """
        Get all feature flags for a specific sport.
        
        Args:
            sport: Sport name
            
        Returns:
            List of feature flags for the sport (global + site-specific)
        """
        return self._repository.get_feature_flags_by_sport(sport)
    
    def update_feature_flag(
        self,
        sport: str,
        site: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[FeatureFlag]:
        """
        Update feature flag.
        
        Args:
            sport: Sport name
            site: Optional site name
            enabled: New enabled state
            
        Returns:
            Updated feature flag if found, None otherwise
            
        Raises:
            ValueError: If no valid update parameters provided
        """
        if enabled is None:
            raise ValueError("At least one field must be provided for update")
        
        flag = self._repository.update_feature_flag(sport, site, enabled)
        
        if flag:
            # Update cache
            cache_key = self._get_cache_key(sport, site)
            self._update_cache(cache_key, flag.enabled)
            
            self._logger.info(
                f"Updated feature flag: sport={sport}, site={site}, enabled={enabled}"
            )
        
        return flag
    
    def delete_feature_flag(
        self,
        sport: str,
        site: Optional[str] = None,
    ) -> bool:
        """
        Delete feature flag.
        
        Args:
            sport: Sport name
            site: Optional site name
            
        Returns:
            True if deleted, False if not found
        """
        deleted = self._repository.delete_feature_flag(sport, site)
        
        if deleted:
            # Invalidate cache
            cache_key = self._get_cache_key(sport, site)
            if cache_key in self._cache:
                del self._cache[cache_key]
                del self._cache_timestamps[cache_key]
            
            self._logger.info(f"Deleted feature flag: sport={sport}, site={site}")
        
        return deleted
    
    def is_adaptive_enabled(
        self,
        sport: str,
        site: Optional[str] = None,
    ) -> bool:
        """
        Check if adaptive system is enabled for a sport/site.
        
        This method implements the core feature flag logic with caching:
        1. Check cache first for performance (< 1ms requirement)
        2. Check site-specific flag first if site provided
        3. Fall back to global sport flag if site-specific not found
        4. Return False if no flag found (default disabled)
        
        Args:
            sport: Sport name
            site: Optional site name
            
        Returns:
            True if adaptive system enabled, False otherwise
        """
        # Check cache first
        cache_key = self._get_cache_key(sport, site)
        cached_value = self._get_from_cache(cache_key)
        if cached_value is not None:
            return cached_value
        
        # Check from repository
        enabled = self._repository.is_adaptive_enabled(sport, site)
        
        # Update cache
        self._update_cache(cache_key, enabled)
        
        return enabled
    
    def get_enabled_sports(self) -> List[str]:
        """
        Get list of sports with adaptive system enabled.
        
        Returns:
            List of sport names with enabled flags
        """
        return self._repository.get_enabled_sports()
    
    def toggle_sport_flag(self, sport: str) -> Optional[FeatureFlag]:
        """
        Toggle adaptive system for a sport (global flag).
        
        Args:
            sport: Sport name
            
        Returns:
            Updated feature flag if found, None otherwise
        """
        current_flag = self.get_feature_flag(sport, None)
        if current_flag is None:
            # Create new flag with enabled=True
            return self.create_feature_flag(sport, None, enabled=True)
        
        # Toggle enabled state
        new_enabled = not current_flag.enabled
        return self.update_feature_flag(sport, None, enabled=new_enabled)
    
    def bulk_create_flags(self, flags_data: List[Dict[str, Any]]) -> List[FeatureFlag]:
        """
        Create multiple feature flags in bulk.
        
        Args:
            flags_data: List of dictionaries with flag data
            
        Returns:
            List of created feature flags
        """
        flags = self._repository.bulk_create_flags(flags_data)
        
        # Clear cache for all created flags
        for flag in flags:
            cache_key = self._get_cache_key(flag.sport, flag.site)
            if cache_key in self._cache:
                del self._cache[cache_key]
                del self._cache_timestamps[cache_key]
        
        self._logger.info(f"Created {len(flags)} feature flags in bulk")
        return flags
    
    def clear_cache(self) -> None:
        """Clear all cached flag values."""
        self._cache.clear()
        self._cache_timestamps.clear()
        self._logger.info("Cleared feature flag cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring.
        
        Returns:
            Dictionary with cache statistics
        """
        total_entries = len(self._cache)
        valid_entries = sum(
            1 for key in self._cache 
            if self._is_cache_valid(key)
        )
        
        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "invalid_entries": total_entries - valid_entries,
            "cache_ttl": self._cache_ttl,
        }


# Global service instance for dependency injection
_feature_flag_service: Optional[FeatureFlagService] = None


def get_feature_flag_service() -> FeatureFlagService:
    """
    Get the global feature flag service instance.
    
    Returns:
        FeatureFlagService instance
    """
    global _feature_flag_service
    if _feature_flag_service is None:
        _feature_flag_service = FeatureFlagService()
    return _feature_flag_service


def is_adaptive_enabled(sport: str, site: Optional[str] = None) -> bool:
    """
    Convenience function to check if adaptive system is enabled.
    
    This is the main entry point used by the selector engine.
    
    Args:
        sport: Sport name
        site: Optional site name
        
    Returns:
        True if adaptive system enabled, False otherwise
    """
    service = get_feature_flag_service()
    return service.is_adaptive_enabled(sport, site)
