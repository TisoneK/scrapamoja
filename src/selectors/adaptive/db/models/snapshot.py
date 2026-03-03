"""
Snapshot SQLAlchemy model for storing DOM snapshots in the database.
"""

import gzip
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Integer, String, DateTime, JSON, Index, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from .recipe import Base


class Snapshot(Base):
    """Snapshot model for storing DOM snapshots captured at failure time."""
    __tablename__ = "snapshots"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Link to failure event
    failure_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        nullable=True, 
        index=True
    )
    
    # Snapshot content (compressed HTML)
    html_content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    
    # Metadata fields
    viewport_size: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, 
        nullable=True
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500), 
        nullable=True
    )
    
    # Additional metadata
    url: Mapped[Optional[str]] = mapped_column(
        String(2048), 
        nullable=True
    )
    selector_context: Mapped[Optional[str]] = mapped_column(
        String(500), 
        nullable=True
    )
    
    # Compression info
    compression_algorithm: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="gzip"
    )
    original_size: Mapped[Optional[int]] = mapped_column(
        Integer, 
        nullable=True
    )
    compressed_size: Mapped[Optional[int]] = mapped_column(
        Integer, 
        nullable=True
    )
    
    # Correlation ID for tracing
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True, 
        index=True
    )
    
    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow
    )
    
    # Table indexes for common queries
    __table_args__ = (
        Index('ix_snapshots_failure_timestamp', 'failure_id', 'timestamp'),
        Index('ix_snapshots_correlation_timestamp', 'correlation_id', 'timestamp'),
    )
    
    def __repr__(self) -> str:
        return f"<Snapshot(id={self.id}, failure_id={self.failure_id}, timestamp={self.timestamp})>"
    
    @property
    def html_content_decompressed(self) -> str:
        """Decompress and return HTML content."""
        return decompress_html(self.html_content)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary representation."""
        return {
            "id": self.id,
            "failure_id": self.failure_id,
            "html_content": self.html_content_decompressed,  # Return decompressed
            "viewport_size": self.viewport_size,
            "user_agent": self.user_agent,
            "url": self.url,
            "selector_context": self.selector_context,
            "compression_algorithm": self.compression_algorithm,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def to_dict_metadata_only(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary with metadata only (no HTML content)."""
        return {
            "id": self.id,
            "failure_id": self.failure_id,
            "viewport_size": self.viewport_size,
            "user_agent": self.user_agent,
            "url": self.url,
            "selector_context": self.selector_context,
            "compression_algorithm": self.compression_algorithm,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Snapshot":
        """Create Snapshot instance from dictionary."""
        # Handle timestamp conversion
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        # Compress HTML content if provided as string
        html_content = data.get("html_content")
        if isinstance(html_content, str):
            html_content = compress_html(html_content)
        
        return cls(
            failure_id=data.get("failure_id"),
            html_content=html_content,
            viewport_size=data.get("viewport_size"),
            user_agent=data.get("user_agent"),
            url=data.get("url"),
            selector_context=data.get("selector_context"),
            compression_algorithm=data.get("compression_algorithm", "gzip"),
            original_size=data.get("original_size"),
            compressed_size=data.get("compressed_size"),
            correlation_id=data.get("correlation_id"),
            timestamp=timestamp or datetime.utcnow(),
            created_at=created_at or datetime.utcnow(),
        )


def compress_html(html: str) -> bytes:
    """
    Compress HTML content using gzip.
    
    Args:
        html: HTML string to compress
        
    Returns:
        Compressed bytes
    """
    return gzip.compress(html.encode('utf-8'), compresslevel=6)


def decompress_html(compressed: bytes) -> str:
    """
    Decompress HTML content.
    
    Args:
        compressed: Compressed HTML bytes
        
    Returns:
        Decompressed HTML string
    """
    return gzip.decompress(compressed).decode('utf-8')
