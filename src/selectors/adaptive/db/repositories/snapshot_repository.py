"""
Repository for DOM Snapshot persistence.

Provides CRUD operations for Snapshot records with compression,
age-based cleanup, and storage statistics.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy import create_engine, select, func, desc, and_
from sqlalchemy.orm import sessionmaker, Session

from ..models.snapshot import Snapshot, compress_html, decompress_html
from ..models.recipe import Base


class SnapshotRepository:
    """Repository for snapshot data access with compression support."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize snapshot repository.

        Args:
            db_path: Path to SQLite database. Defaults to persistent storage.
        """
        if db_path is None:
            db_dir = os.path.join(os.getcwd(), "data")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "adaptive.db")

        self.db_path = db_path
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False} if db_path != ":memory:" else {}
        )
        Base.metadata.create_all(self.engine, checkfirst=True)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

    def close(self) -> None:
        """Dispose of the database engine."""
        self.engine.dispose()

    def create_snapshot(
        self,
        html_content: str,
        failure_id: Optional[int] = None,
        viewport_size: Optional[Dict[str, int]] = None,
        user_agent: Optional[str] = None,
        url: Optional[str] = None,
        selector_context: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Snapshot:
        """Create a new compressed snapshot.

        Args:
            html_content: Raw HTML to compress and store.
            failure_id: Associated failure event ID.
            viewport_size: Browser viewport dimensions.
            user_agent: Browser user agent string.
            url: Page URL where snapshot was captured.
            selector_context: CSS selector context for the failure.
            correlation_id: Correlation ID for tracing.

        Returns:
            Created Snapshot with populated id and timestamps.
        """
        compressed = compress_html(html_content)
        session = self.get_session()
        try:
            snapshot = Snapshot(
                failure_id=failure_id,
                html_compressed=compressed,
                original_size=len(html_content.encode("utf-8")),
                compressed_size=len(compressed),
                compression_algorithm="gzip",
                viewport_size=viewport_size,
                user_agent=user_agent,
                url=url,
                selector_context=selector_context,
                correlation_id=correlation_id,
            )
            session.add(snapshot)
            session.commit()
            session.refresh(snapshot)
            return snapshot
        finally:
            session.close()

    def get_by_id(self, snapshot_id: int) -> Optional[Snapshot]:
        """Get snapshot by ID."""
        session = self.get_session()
        try:
            return session.execute(
                select(Snapshot).where(Snapshot.id == snapshot_id)
            ).scalar_one_or_none()
        finally:
            session.close()

    def get_by_failure_id(self, failure_id: int) -> Optional[Snapshot]:
        """Get most recent snapshot by failure ID."""
        session = self.get_session()
        try:
            return session.execute(
                select(Snapshot)
                .where(Snapshot.failure_id == failure_id)
                .order_by(desc(Snapshot.created_at))
                .limit(1)
            ).scalar_one_or_none()
        finally:
            session.close()

    def get_recent_snapshots(self, limit: int = 10) -> List[Snapshot]:
        """Get most recent snapshots."""
        session = self.get_session()
        try:
            return list(
                session.execute(
                    select(Snapshot).order_by(desc(Snapshot.created_at)).limit(limit)
                ).scalars().all()
            )
        finally:
            session.close()

    def get_snapshots_by_selector_context(self, selector_context: str) -> List[Snapshot]:
        """Get snapshots filtered by selector context."""
        session = self.get_session()
        try:
            return list(
                session.execute(
                    select(Snapshot)
                    .where(Snapshot.selector_context == selector_context)
                    .order_by(desc(Snapshot.created_at))
                ).scalars().all()
            )
        finally:
            session.close()

    def delete_snapshot(self, snapshot_id: int) -> bool:
        """Delete snapshot by ID. Returns True if deleted."""
        session = self.get_session()
        try:
            snapshot = session.execute(
                select(Snapshot).where(Snapshot.id == snapshot_id)
            ).scalar_one_or_none()
            if snapshot is None:
                return False
            session.delete(snapshot)
            session.commit()
            return True
        finally:
            session.close()

    def delete_old_snapshots(self, days_old: int = 30) -> int:
        """Delete snapshots older than specified days. Returns count deleted."""
        session = self.get_session()
        try:
            cutoff = datetime.utcnow() - timedelta(days=days_old)
            old_snapshots = session.execute(
                select(Snapshot).where(Snapshot.created_at < cutoff)
            ).scalars().all()
            count = len(old_snapshots)
            for s in old_snapshots:
                session.delete(s)
            session.commit()
            return count
        finally:
            session.close()

    def delete_excess_snapshots(self, keep_count: int = 1000) -> int:
        """Delete oldest snapshots keeping only the most recent keep_count.

        Returns count deleted.
        """
        session = self.get_session()
        try:
            total = session.execute(
                select(func.count()).select_from(Snapshot)
            ).scalar()
            if total <= keep_count:
                return 0

            # Find the ID threshold — keep the newest `keep_count` snapshots
            threshold_id = session.execute(
                select(Snapshot.id)
                .order_by(desc(Snapshot.created_at))
                .offset(keep_count)
                .limit(1)
            ).scalar_one_or_none()

            if threshold_id is None:
                return 0

            result = session.execute(
                select(Snapshot).where(Snapshot.id <= threshold_id)
            ).scalars().all()

            # Actually, let's find the cutoff more carefully
            all_ids = list(
                session.execute(
                    select(Snapshot.id).order_by(desc(Snapshot.created_at))
                ).scalars().all()
            )

            ids_to_delete = all_ids[keep_count:]
            count = 0
            for sid in ids_to_delete:
                snap = session.get(Snapshot, sid)
                if snap:
                    session.delete(snap)
                    count += 1
            session.commit()
            return count
        finally:
            session.close()

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics for snapshots."""
        session = self.get_session()
        try:
            total = session.execute(
                select(func.count()).select_from(Snapshot)
            ).scalar() or 0

            total_original = session.execute(
                select(func.sum(Snapshot.original_size))
            ).scalar() or 0

            total_compressed = session.execute(
                select(func.sum(Snapshot.compressed_size))
            ).scalar() or 0

            ratio = 0.0
            if total_original > 0:
                ratio = 1.0 - (total_compressed / total_original)

            return {
                "total_snapshots": total,
                "total_original_size_bytes": total_original,
                "total_compressed_size_bytes": total_compressed,
                "compression_ratio": ratio,
            }
        finally:
            session.close()
