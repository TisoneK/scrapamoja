"""
Recipe SQLAlchemy model for storing recipe versions in the database.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import Integer, String, Float, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class FailureSeverity:
    """Enumeration for failure severity levels."""
    MINOR = "minor"
    MODERATE = "moderate"
    CRITICAL = "critical"
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if value is a valid severity level."""
        return value in (cls.MINOR, cls.MODERATE, cls.CRITICAL)


class Recipe(Base):
    """Recipe model representing a versioned recipe configuration."""
    __tablename__ = "recipes"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Required fields
    recipe_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    selectors: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    # Optional fields for versioning and stability
    parent_recipe_id: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True, 
        default=None
    )
    generation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    stability_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    
    # NEW: Stability tracking fields
    success_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    failure_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    consecutive_failures: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    generations_survived: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    last_successful_resolution: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    last_failure_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    failure_severity: Mapped[Optional[str]] = mapped_column(
        String(20), 
        nullable=True, 
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
    
    # Unique constraint on recipe_id + version combination
    __table_args__ = (
        UniqueConstraint('recipe_id', 'version', name='uq_recipe_version'),
    )
    
    def __repr__(self) -> str:
        return f"<Recipe(recipe_id={self.recipe_id!r}, version={self.version})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert recipe to dictionary representation."""
        return {
            "id": self.id,
            "recipe_id": self.recipe_id,
            "version": self.version,
            "parent_recipe_id": self.parent_recipe_id,
            "generation": self.generation,
            "stability_score": self.stability_score,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "consecutive_failures": self.consecutive_failures,
            "generations_survived": self.generations_survived,
            "last_successful_resolution": self.last_successful_resolution.isoformat() if self.last_successful_resolution else None,
            "last_failure_timestamp": self.last_failure_timestamp.isoformat() if self.last_failure_timestamp else None,
            "failure_severity": self.failure_severity,
            "selectors": self.selectors,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Recipe":
        """Create Recipe instance from dictionary."""
        return cls(
            recipe_id=data["recipe_id"],
            version=data.get("version", 1),
            selectors=data["selectors"],
            parent_recipe_id=data.get("parent_recipe_id"),
            generation=data.get("generation"),
            stability_score=data.get("stability_score"),
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            consecutive_failures=data.get("consecutive_failures", 0),
            generations_survived=data.get("generations_survived", 0),
            last_successful_resolution=data.get("last_successful_resolution"),
            last_failure_timestamp=data.get("last_failure_timestamp"),
            failure_severity=data.get("failure_severity"),
        )
