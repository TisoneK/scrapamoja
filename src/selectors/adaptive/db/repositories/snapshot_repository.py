"""
Snapshot repository for database CRUD operations.
"""

import gzip
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import Session, sessionmaker

from ..models.snapshot import Base, Snapshot, compress_html, decompress_html


class SnapshotRepository:
    """
    Repository for managing DOM snapshots in SQLite database.
    
    Provides CRUD operations for snapshot capture, storage, and retrieval.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the snapshot repository.
        
        Args:
            db_path: Optional path to SQLite database file.
                    If not provided, uses ':memory:' for testing.
        """
        if db_path is None:
            db_path = ":memory:"
        
        self.db_path = db_path
        # Create engine with check_same_thread=False for SQLite
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False} if db_path != ":memory:" else {}
        )
        # Create tables
        Base.metadata.create_all(self.engine)
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def _get_session(self) -> Session:
        """Get a new database session."""
        return Session(bind=self.engine)
    
    def create_snapshot(
        self,
        html_content: str,
        failure_id: Optional[int] = None,
        viewport_size: Optional[Dict[str, Any]] = None,
        user_agent: Optional[str] = None,
        url: Optional[str] = None,
        selector_context: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Snapshot:
        """
        Create a new snapshot with compressed HTML content.
        
        Args:
            html_content: HTML content to store
            failure_id: Optional link to failure event
            viewport_size: Optional viewport dimensions
            user_agent: Optional browser user agent
            url: Optional page URL
            selector_context: Optional selector that failed
            correlation_id: Optional correlation ID
            
        Returns:
            Created Snapshot instance
        """
        # Compress HTML content
        compressed = compress_html(html_content)
        original_size = len(html_content.encode('utf-8'))
        compressed_size = len(compressed)
        
        with self._get_session() as session:
            snapshot = Snapshot(
                failure_id=failure_id,
                html_content=compressed,
                viewport_size=viewport_size,
                user_agent=user_agent,
                url=url,
                selector_context=selector_context,
                compression_algorithm="gzip",
                original_size=original_size,
                compressed_size=compressed_size,
                correlation_id=correlation_id,
                timestamp=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            session.add(snapshot)
            session.commit()
            session.refresh(snapshot)
            return snapshot
    
    def get_by_id(self, snapshot_id: int) -> Optional[Snapshot]:
        """
        Retrieve a snapshot by ID.
        
        Args:
            snapshot_id: Unique identifier for the snapshot
            
        Returns:
            Snapshot instance if found, None otherwise
        """
        with self._get_session() as session:
            return session.execute(
                select(Snapshot).where(Snapshot.id == snapshot_id)
            ).scalar_one_or_none()
    
    def get_by_failure_id(self, failure_id: int) -> Optional[Snapshot]:
        """
        Retrieve a snapshot by failure ID.
        
        Args:
            failure_id: Failure event ID
            
        Returns:
            Snapshot instance if found, None otherwise
        """
        with self._get_session() as session:
            return session.execute(
                select(Snapshot)
                .where(Snapshot.failure_id == failure_id)
                .order_by(Snapshot.timestamp.desc())
            ).scalars().first()
    
    def get_by_correlation_id(self, correlation_id: str) -> List[Snapshot]:
        """
        Retrieve snapshots by correlation ID.
        
        Args:
            correlation_id: Correlation ID for tracing
            
        Returns:
            List of Snapshot instances
        """
        with self._get_session() as session:
            return list(
                session.execute(
                    select(Snapshot)
                    .where(Snapshot.correlation_id == correlation_id)
                    .order_by(Snapshot.timestamp.desc())
                ).scalars().all()
            )
    
    def get_recent_snapshots(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Snapshot]:
        """
        Get recent snapshots ordered by timestamp.
        
        Args:
            limit: Maximum number of snapshots to return
            offset: Number of snapshots to skip
            
        Returns:
            List of Snapshot instances ordered by timestamp (newest first)
        """
        with self._get_session() as session:
            return list(
                session.execute(
                    select(Snapshot)
                    .order_by(Snapshot.timestamp.desc())
                    .limit(limit)
                    .offset(offset)
                ).scalars().all()
            )
    
    def get_snapshots_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: Optional[int] = None,
    ) -> List[Snapshot]:
        """
        Get snapshots within a date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            limit: Optional maximum number of snapshots
            
        Returns:
            List of Snapshot instances within the date range
        """
        with self._get_session() as session:
            query = (
                select(Snapshot)
                .where(Snapshot.timestamp >= start_date)
                .where(Snapshot.timestamp <= end_date)
                .order_by(Snapshot.timestamp.desc())
            )
            
            if limit:
                query = query.limit(limit)
            
            return list(session.execute(query).scalars().all())
    
    def get_snapshots_by_selector_context(
        self,
        selector_context: str,
        limit: int = 50,
    ) -> List[Snapshot]:
        """
        Get snapshots by selector context.
        
        Args:
            selector_context: Selector that was being used
            limit: Maximum number of snapshots
            
        Returns:
            List of Snapshot instances
        """
        with self._get_session() as session:
            return list(
                session.execute(
                    select(Snapshot)
                    .where(Snapshot.selector_context == selector_context)
                    .order_by(Snapshot.timestamp.desc())
                    .limit(limit)
                ).scalars().all()
            )
    
    def update_snapshot_failure_link(
        self,
        snapshot_id: int,
        failure_id: int,
    ) -> Optional[Snapshot]:
        """
        Update the failure ID link for a snapshot.
        
        Args:
            snapshot_id: Snapshot ID to update
            failure_id: Failure event ID to link
            
        Returns:
            Updated Snapshot if found, None otherwise
        """
        with self._get_session() as session:
            snapshot = session.execute(
                select(Snapshot).where(Snapshot.id == snapshot_id)
            ).scalar_one_or_none()
            
            if snapshot:
                snapshot.failure_id = failure_id
                session.commit()
                session.refresh(snapshot)
            
            return snapshot
    
    def delete_snapshot(self, snapshot_id: int) -> bool:
        """
        Delete a snapshot by ID.
        
        Args:
            snapshot_id: ID of snapshot to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            snapshot = session.execute(
                select(Snapshot).where(Snapshot.id == snapshot_id)
            ).scalar_one_or_none()
            
            if snapshot:
                session.delete(snapshot)
                session.commit()
                return True
            return False
    
    def delete_old_snapshots(
        self,
        days_old: int,
    ) -> int:
        """
        Delete snapshots older than specified days.
        
        Args:
            days_old: Number of days to keep
            
        Returns:
            Number of snapshots deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        with self._get_session() as session:
            # Get snapshots to delete
            old_snapshots = session.execute(
                select(Snapshot.id)
                .where(Snapshot.timestamp < cutoff_date)
            ).scalars().all()
            
            count = len(old_snapshots)
            
            if count > 0:
                session.execute(
                    delete(Snapshot)
                    .where(Snapshot.timestamp < cutoff_date)
                )
                session.commit()
            
            return count
    
    def delete_excess_snapshots(
        self,
        keep_count: int,
    ) -> int:
        """
        Delete excess snapshots, keeping the most recent ones.
        
        Args:
            keep_count: Number of snapshots to keep
            
        Returns:
            Number of snapshots deleted
        """
        with self._get_session() as session:
            # Get total count
            total = session.execute(
                select(Snapshot)
            ).scalars().all()
            
            if len(total) <= keep_count:
                return 0
            
            # Get IDs to keep (most recent)
            to_keep = session.execute(
                select(Snapshot.id)
                .order_by(Snapshot.timestamp.desc())
                .limit(keep_count)
            ).scalars().all()
            
            keep_ids = set(to_keep)
            
            # Get IDs to delete
            to_delete = session.execute(
                select(Snapshot.id)
                .where(Snapshot.id.not_in(keep_ids))
            ).scalars().all()
            
            # Delete snapshots not in keep_ids
            if to_delete:
                session.execute(
                    delete(Snapshot)
                    .where(Snapshot.id.not_in(keep_ids))
                )
                session.commit()
            
            return len(to_delete)
    
    def get_snapshot_count(self) -> int:
        """
        Get total number of snapshots.
        
        Returns:
            Total count of snapshots
        """
        with self._get_session() as session:
            snapshots = session.execute(select(Snapshot)).scalars().all()
            return len(snapshots)
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage stats
        """
        with self._get_session() as session:
            snapshots = session.execute(select(Snapshot)).scalars().all()
            
            total_original = sum(s.original_size or 0 for s in snapshots)
            total_compressed = sum(s.compressed_size or 0 for s in snapshots)
            
            return {
                "total_snapshots": len(snapshots),
                "total_original_size_bytes": total_original,
                "total_compressed_size_bytes": total_compressed,
                "compression_ratio": (
                    (1 - total_compressed / total_original) * 100 
                    if total_original > 0 else 0
                ),
            }
    
    def close(self):
        """Close the database connection."""
        self.engine.dispose()
