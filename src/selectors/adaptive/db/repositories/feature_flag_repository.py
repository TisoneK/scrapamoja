"""
Repository for Feature Flag operations.

This implements the data access layer for sport-based feature flags.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, select, func, desc, and_
from sqlalchemy.orm import Session, sessionmaker
import os

from ..models.feature_flag import FeatureFlag
from ..models.recipe import Base


class FeatureFlagRepository:
    """Repository for feature flag data access."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the feature flag repository.
        
        Args:
            db_path: Optional path to SQLite database file.
                    If not provided, uses persistent storage.
        """
        if db_path is None:
            # Use persistent storage in data directory
            db_dir = os.path.join(os.getcwd(), "data")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "adaptive.db")
        
        self.db_path = db_path
        # Create engine with check_same_thread=False for SQLite
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False} if db_path != ":memory:" else {}
        )
        # Create tables with checkfirst to avoid index conflicts
        Base.metadata.create_all(self.engine, checkfirst=True)
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
    
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
        """
        session = self.get_session()
        try:
            feature_flag = FeatureFlag(
                sport=sport.lower().strip(),
                site=site.lower().strip() if site else None,
                enabled=enabled,
            )
            session.add(feature_flag)
            session.commit()
            session.refresh(feature_flag)
            return feature_flag
        finally:
            session.close()
    
    def get_feature_flag(
        self,
        sport: str,
        site: Optional[str] = None,
    ) -> Optional[FeatureFlag]:
        """
        Get feature flag by sport and site.
        
        Args:
            sport: Sport name
            site: Optional site name (if None, looks for global sport flag)
            
        Returns:
            Feature flag if found, None otherwise
        """
        session = self.get_session()
        try:
            stmt = select(FeatureFlag).where(
                FeatureFlag.sport == sport.lower().strip()
            )
            
            if site is None:
                stmt = stmt.where(FeatureFlag.site.is_(None))
            else:
                stmt = stmt.where(FeatureFlag.site == site.lower().strip())
            
            result = session.execute(stmt).scalar_one_or_none()
            return result
        finally:
            session.close()
    
    def get_all_feature_flags(self) -> List[FeatureFlag]:
        """
        Get all feature flags.
        
        Returns:
            List of all feature flags
        """
        session = self.get_session()
        try:
            stmt = select(FeatureFlag).order_by(
                FeatureFlag.sport, 
                FeatureFlag.site,
                FeatureFlag.created_at
            )
            result = session.execute(stmt).scalars().all()
            return list(result)
        finally:
            session.close()
    
    def get_feature_flags_by_sport(self, sport: str) -> List[FeatureFlag]:
        """
        Get all feature flags for a specific sport.
        
        Args:
            sport: Sport name
            
        Returns:
            List of feature flags for the sport (global + site-specific)
        """
        session = self.get_session()
        try:
            stmt = select(FeatureFlag).where(
                FeatureFlag.sport == sport.lower().strip()
            ).order_by(
                FeatureFlag.site.nulls_first(),
                FeatureFlag.created_at
            )
            result = session.execute(stmt).scalars().all()
            return list(result)
        finally:
            session.close()
    
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
        """
        session = self.get_session()
        try:
            # Find existing flag
            feature_flag = self.get_feature_flag(sport, site)
            if feature_flag is None:
                return None
            
            # Update fields
            if enabled is not None:
                feature_flag.enabled = enabled
                feature_flag.updated_at = datetime.utcnow()
            
            session.commit()
            session.refresh(feature_flag)
            return feature_flag
        finally:
            session.close()
    
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
        session = self.get_session()
        try:
            feature_flag = self.get_feature_flag(sport, site)
            if feature_flag is None:
                return False
            
            session.delete(feature_flag)
            session.commit()
            return True
        finally:
            session.close()
    
    def is_adaptive_enabled(
        self,
        sport: str,
        site: Optional[str] = None,
    ) -> bool:
        """
        Check if adaptive system is enabled for a sport/site.
        
        This method implements the core feature flag logic:
        1. Check site-specific flag first if site provided
        2. Fall back to global sport flag if site-specific not found
        3. Return False if no flag found (default disabled)
        
        Args:
            sport: Sport name
            site: Optional site name
            
        Returns:
            True if adaptive system enabled, False otherwise
        """
        # First check site-specific flag if site provided
        if site is not None:
            site_flag = self.get_feature_flag(sport, site)
            if site_flag is not None:
                return site_flag.enabled
        
        # Fall back to global sport flag
        global_flag = self.get_feature_flag(sport, None)
        if global_flag is not None:
            return global_flag.enabled
        
        # Default to disabled if no flag found
        return False
    
    def get_enabled_sports(self) -> List[str]:
        """
        Get list of sports with adaptive system enabled.
        
        Returns:
            List of sport names with enabled flags
        """
        session = self.get_session()
        try:
            stmt = select(FeatureFlag.sport).where(
                and_(
                    FeatureFlag.enabled == True,
                    FeatureFlag.site.is_(None)  # Only global flags
                )
            ).distinct()
            result = session.execute(stmt).scalars().all()
            return list(result)
        finally:
            session.close()
    
    def bulk_create_flags(self, flags_data: List[Dict[str, Any]]) -> List[FeatureFlag]:
        """
        Create multiple feature flags in bulk.
        
        Args:
            flags_data: List of dictionaries with flag data
            
        Returns:
            List of created feature flags
        """
        session = self.get_session()
        try:
            feature_flags = []
            for data in flags_data:
                flag = FeatureFlag(
                    sport=data["sport"].lower().strip(),
                    site=data.get("site", "").lower().strip() or None,
                    enabled=data.get("enabled", False),
                )
                feature_flags.append(flag)
                session.add(flag)
            
            session.commit()
            for flag in feature_flags:
                session.refresh(flag)
            return feature_flags
        finally:
            session.close()
