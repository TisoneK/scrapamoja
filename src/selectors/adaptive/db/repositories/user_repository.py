"""
Repository for User Preference operations.

This implements the data access layer for user preferences and view mode management.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, select, func, desc
from sqlalchemy.orm import Session, sessionmaker
import os

from ..models.user_preferences import UserPreference, ViewUsageAnalytics, UserRole, ViewMode
from ..models.recipe import Base


class UserPreferenceRepository:
    """Repository for user preference data access."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the user preference repository.
        
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
    
    def create_user_preference(
        self,
        user_id: str,
        role: str = UserRole.OPERATIONS,
        default_view: Optional[str] = None,
        custom_settings: Optional[Dict[str, Any]] = None,
        api_key_hash: Optional[str] = None,
    ) -> UserPreference:
        """
        Create a new user preference.
        
        Args:
            user_id: Unique user identifier
            role: User role (operations, developer, admin)
            default_view: Default view mode preference
            custom_settings: Custom settings as key-value pairs
            api_key_hash: Hash of API key for role-based access
            
        Returns:
            Created user preference
        """
        session = self.get_session()
        try:
            # Set default view based on role if not provided
            if default_view is None:
                default_view = ViewMode.get_default_for_role(role)
            
            preference = UserPreference(
                user_id=user_id,
                role=role,
                default_view=default_view,
                custom_settings=custom_settings,
                api_key_hash=api_key_hash,
                last_view_mode=default_view,
            )
            
            session.add(preference)
            session.commit()
            session.refresh(preference)
            
            return preference
        finally:
            session.close()
    
    def get_by_user_id(self, user_id: str) -> Optional[UserPreference]:
        """
        Get user preference by user ID.
        
        Args:
            user_id: The user ID
            
        Returns:
            User preference if found, None otherwise
        """
        session = self.get_session()
        try:
            return (
                session.query(UserPreference)
                .filter(UserPreference.user_id == user_id)
                .first()
            )
        finally:
            session.close()
    
    def get_by_api_key_hash(self, api_key_hash: str) -> Optional[UserPreference]:
        """
        Get user preference by API key hash.
        
        Args:
            api_key_hash: Hash of the API key
            
        Returns:
            User preference if found, None otherwise
        """
        session = self.get_session()
        try:
            return (
                session.query(UserPreference)
                .filter(UserPreference.api_key_hash == api_key_hash)
                .first()
            )
        finally:
            session.close()
    
    def update_user_preference(
        self,
        user_id: str,
        role: Optional[str] = None,
        default_view: Optional[str] = None,
        custom_settings: Optional[Dict[str, Any]] = None,
    ) -> Optional[UserPreference]:
        """
        Update user preference.
        
        Args:
            user_id: The user ID
            role: New role (optional)
            default_view: New default view mode (optional)
            custom_settings: New custom settings (optional)
            
        Returns:
            Updated user preference if found, None otherwise
        """
        session = self.get_session()
        try:
            preference = (
                session.query(UserPreference)
                .filter(UserPreference.user_id == user_id)
                .first()
            )
            
            if preference is None:
                return None
            
            if role is not None:
                preference.role = role
            if default_view is not None:
                preference.default_view = default_view
            if custom_settings is not None:
                preference.custom_settings = custom_settings
            
            preference.updated_at = datetime.now(timezone.utc)
            
            session.commit()
            session.refresh(preference)
            
            return preference
        finally:
            session.close()
    
    def switch_view_mode(self, user_id: str, new_view_mode: str) -> Optional[UserPreference]:
        """
        Switch user's view mode and track the switch.
        
        Args:
            user_id: The user ID
            new_view_mode: The new view mode to switch to
            
        Returns:
            Updated user preference if found, None otherwise
        """
        session = self.get_session()
        try:
            preference = (
                session.query(UserPreference)
                .filter(UserPreference.user_id == user_id)
                .first()
            )
            
            if preference is None:
                return None
            
            # Track the switch
            preference.last_view_mode = new_view_mode
            preference.view_mode_switches += 1
            preference.updated_at = datetime.now(timezone.utc)
            
            session.commit()
            session.refresh(preference)
            
            return preference
        finally:
            session.close()
    
    def delete_user_preference(self, user_id: str) -> bool:
        """
        Delete user preference.
        
        Args:
            user_id: The user ID
            
        Returns:
            True if deleted, False if not found
        """
        session = self.get_session()
        try:
            preference = (
                session.query(UserPreference)
                .filter(UserPreference.user_id == user_id)
                .first()
            )
            
            if preference is None:
                return False
            
            session.delete(preference)
            session.commit()
            
            return True
        finally:
            session.close()
    
    def get_all_preferences(self, limit: int = 100) -> List[UserPreference]:
        """
        Get all user preferences.
        
        Args:
            limit: Maximum number of preferences to return
            
        Returns:
            List of user preferences
        """
        session = self.get_session()
        try:
            return (
                session.query(UserPreference)
                .limit(limit)
                .all()
            )
        finally:
            session.close()
    
    def get_preferences_by_role(self, role: str) -> List[UserPreference]:
        """
        Get user preferences by role.
        
        Args:
            role: The role to filter by
            
        Returns:
            List of user preferences for the role
        """
        session = self.get_session()
        try:
            return (
                session.query(UserPreference)
                .filter(UserPreference.role == role)
                .all()
            )
        finally:
            session.close()


class ViewUsageRepository:
    """Repository for view usage analytics data access."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the view usage repository.
        
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
    
    def create_usage_record(
        self,
        user_id: str,
        view_mode: str,
    ) -> ViewUsageAnalytics:
        """
        Create a new view usage record.
        
        Args:
            user_id: The user ID
            view_mode: The view mode being used
            
        Returns:
            Created usage record
        """
        session = self.get_session()
        try:
            record = ViewUsageAnalytics(
                user_id=user_id,
                view_mode=view_mode,
                session_start=datetime.now(timezone.utc),
            )
            
            session.add(record)
            session.commit()
            session.refresh(record)
            
            return record
        finally:
            session.close()
    
    def update_session(
        self,
        record_id: int,
        action_count: Optional[int] = None,
    ) -> Optional[ViewUsageAnalytics]:
        """
        Update a view usage session.
        
        Args:
            record_id: The record ID
            action_count: Updated action count
            
        Returns:
            Updated record if found, None otherwise
        """
        session = self.get_session()
        try:
            record = (
                session.query(ViewUsageAnalytics)
                .filter(ViewUsageAnalytics.id == record_id)
                .first()
            )
            
            if record is None:
                return None
            
            if action_count is not None:
                record.action_count = action_count
            
            session.commit()
            session.refresh(record)
            
            return record
        finally:
            session.close()
    
    def end_session(self, record_id: int) -> Optional[ViewUsageAnalytics]:
        """
        End a view usage session.
        
        Args:
            record_id: The record ID
            
        Returns:
            Updated record if found, None otherwise
        """
        session = self.get_session()
        try:
            record = (
                session.query(ViewUsageAnalytics)
                .filter(ViewUsageAnalytics.id == record_id)
                .first()
            )
            
            if record is None:
                return None
            
            record.session_end = datetime.now(timezone.utc)
            
            # Calculate duration
            if record.session_start and record.session_end:
                duration = (record.session_end - record.session_start).total_seconds()
                record.session_duration_seconds = int(duration)
            
            session.commit()
            session.refresh(record)
            
            return record
        finally:
            session.close()
    
    def get_by_user_id(
        self, 
        user_id: str, 
        limit: int = 100
    ) -> List[ViewUsageAnalytics]:
        """
        Get view usage records by user ID.
        
        Args:
            user_id: The user ID
            limit: Maximum number of records to return
            
        Returns:
            List of usage records for the user
        """
        session = self.get_session()
        try:
            return (
                session.query(ViewUsageAnalytics)
                .filter(ViewUsageAnalytics.user_id == user_id)
                .order_by(desc(ViewUsageAnalytics.session_start))
                .limit(limit)
                .all()
            )
        finally:
            session.close()
    
    def get_usage_statistics(
        self,
        user_id: Optional[str] = None,
        view_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get view usage statistics.
        
        Args:
            user_id: Optional user ID to filter by
            view_mode: Optional view mode to filter by
            
        Returns:
            Dictionary with usage statistics
        """
        session = self.get_session()
        try:
            query = session.query(ViewUsageAnalytics)
            
            if user_id:
                query = query.filter(ViewUsageAnalytics.user_id == user_id)
            if view_mode:
                query = query.filter(ViewUsageAnalytics.view_mode == view_mode)
            
            total_sessions = query.count()
            
            # Calculate total actions
            total_actions = sum(r.action_count for r in query.all())
            
            # Calculate average session duration
            records_with_duration = [
                r for r in query.all() 
                if r.session_duration_seconds is not None
            ]
            avg_duration = None
            if records_with_duration:
                durations = [r.session_duration_seconds for r in records_with_duration]
                avg_duration = sum(d for d in durations if d is not None) / len(durations)
            
            return {
                "total_sessions": total_sessions,
                "total_actions": total_actions,
                "average_session_duration_seconds": avg_duration,
                "user_id": user_id,
                "view_mode": view_mode,
            }
        finally:
            session.close()
