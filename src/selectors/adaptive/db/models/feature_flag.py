"""
Feature Flag SQLAlchemy model for enabling/disabling adaptive system per sport.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .recipe import Base


class FeatureFlag(Base):
    """Feature flag model representing adaptive system enablement per sport/site."""
    __tablename__ = "feature_flags"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Required fields
    sport: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Optional field for site-specific flags
    site: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True, 
        index=True,
        default=None
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Unique constraint on sport + site combination (site can be null for global sport flags)
    __table_args__ = (
        UniqueConstraint('sport', 'site', name='uq_feature_flag_sport_site'),
    )
    
    def __repr__(self) -> str:
        site_suffix = f"@{self.site}" if self.site else ""
        return f"<FeatureFlag(sport={self.sport!r}{site_suffix}, enabled={self.enabled})>"
    
    def to_dict(self) -> dict[str, object]:
        """Convert feature flag to dictionary representation."""
        return {
            "id": self.id,
            "sport": self.sport,
            "site": self.site,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "FeatureFlag":
        """Create FeatureFlag instance from dictionary."""
        return cls(
            sport=data["sport"],
            site=data.get("site"),
            enabled=data.get("enabled", False),
        )
