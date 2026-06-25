"""
Snapshot model for storing DOM snapshots of selector failures.

Provides compression/decompression utilities and the SQLAlchemy model
for persisting HTML snapshots captured at the point of failure.
"""

import gzip
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Integer, String, Float, DateTime, JSON, LargeBinary, Text
from sqlalchemy.orm import Mapped, mapped_column

from .recipe import Base


def compress_html(html_content: str) -> bytes:
    """Compress HTML content using gzip.

    Args:
        html_content: Raw HTML string to compress.

    Returns:
        Gzip-compressed bytes.
    """
    return gzip.compress(html_content.encode("utf-8"))


def decompress_html(compressed: bytes) -> str:
    """Decompress gzip-compressed HTML content.

    Args:
        compressed: Gzip-compressed bytes.

    Returns:
        Decompressed HTML string.

    Raises:
        Exception: If decompression fails.
    """
    return gzip.decompress(compressed).decode("utf-8")


class Snapshot(Base):
    """SQLAlchemy model for DOM snapshots captured during selector failures."""

    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    failure_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    html_compressed: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    original_size: Mapped[int] = mapped_column(Integer, nullable=False)
    compressed_size: Mapped[int] = mapped_column(Integer, nullable=False)
    compression_algorithm: Mapped[str] = mapped_column(String(20), default="gzip")
    viewport_size: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    selector_context: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, index=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary with decompressed HTML content."""
        return {
            "id": self.id,
            "failure_id": self.failure_id,
            "html_content": decompress_html(self.html_compressed),
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "compression_algorithm": self.compression_algorithm,
            "viewport_size": self.viewport_size,
            "user_agent": self.user_agent,
            "url": self.url,
            "selector_context": self.selector_context,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
