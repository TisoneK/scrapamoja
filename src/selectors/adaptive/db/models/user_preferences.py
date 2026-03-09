"""
User Preference model for storing user view mode preferences.

This implements Story 7.2 (Technical and Non-Technical Views) requirements.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from sqlalchemy import Integer, String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .recipe import Base


class UserRole:
    """Enumeration for user roles."""
    OPERATIONS = "operations"
    DEVELOPER = "developer"
    ADMIN = "admin"

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if value is a valid role."""
        return value in (cls.OPERATIONS, cls.DEVELOPER, cls.ADMIN)


class ViewMode:
    """Enumeration for view modes."""
    TECHNICAL = "technical"
    NON_TECHNICAL = "non_technical"

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if value is a valid view mode."""
        return value in (cls.TECHNICAL, cls.NON_TECHNICAL)

    @classmethod
    def get_default_for_role(cls, role: str) -> str:
        """Get the default view mode for a given role."""
        if role == UserRole.OPERATIONS:
            return cls.NON_TECHNICAL
        return cls.TECHNICAL


class UserPreference(Base):
    """
    User preference model for storing view mode and role preferences.
    
    This table stores:
    - User role (operations, developer, admin)
    - Default view mode preference
    - Custom settings per user
    - API key association for role-based access
    """
    
    __tablename__ = "user_preferences"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # User identification
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    api_key_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Role and view preferences
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.OPERATIONS)
    default_view: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default=ViewMode.NON_TECHNICAL
    )
    
    # Custom settings (JSON for flexibility)
    custom_settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # View mode usage tracking
    last_view_mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    view_mode_switches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role": self.role,
            "default_view": self.default_view,
            "custom_settings": self.custom_settings or {},
            "last_view_mode": self.last_view_mode,
            "view_mode_switches": self.view_mode_switches,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<UserPreference(user_id={self.user_id!r}, role={self.role}, default_view={self.default_view})>"


class ViewUsageAnalytics(Base):
    """
    View usage analytics for tracking user view mode patterns.
    
    This table stores:
    - View mode usage per user
    - Session duration
    - Action counts
    """
    
    __tablename__ = "view_usage_analytics"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # User identification
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # View mode data
    view_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Usage metrics
    action_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    session_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Session tracking
    session_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc)
    )
    session_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc)
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        session_duration = None
        if self.session_start:
            end = self.session_end or datetime.now(timezone.utc)
            session_duration = int((end - self.session_start).total_seconds())
        
        return {
            "id": self.id,
            "user_id": self.user_id,
            "view_mode": self.view_mode,
            "action_count": self.action_count,
            "session_duration_seconds": session_duration,
            "session_start": self.session_start.isoformat() if self.session_start else None,
            "session_end": self.session_end.isoformat() if self.session_end else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ViewUsageAnalytics(user_id={self.user_id!r}, view_mode={self.view_mode})>"
