"""
Triage performance tracking models.

This module defines the database models for tracking triage workflow performance,
enabling monitoring of page load times, action response times, and overall
triage efficiency.

Story: 7.3 - Fast Triage Workflow
"""

from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, select, func
from sqlalchemy.orm import Session, sessionmaker

from ..models.recipe import Base


class TriageMetrics(Base):
    """
    Model for tracking triage action performance metrics.
    
    Stores timing information for each triage action to enable
    performance monitoring and optimization.
    """
    __tablename__ = "triage_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    failure_id = Column(Integer, nullable=False, index=True)
    user_id = Column(String(255), nullable=True, index=True)
    action_type = Column(String(50), nullable=False)  # approve, reject, escalate, load, preview
    load_time_ms = Column(Float, nullable=True)  # Time to load failure data
    action_time_ms = Column(Float, nullable=True)  # Time to perform action
    total_time_ms = Column(Float, nullable=True)  # Total workflow time
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    meta_data = Column(JSON, nullable=True)  # Additional context


class BulkOperation(Base):
    """
    Model for tracking bulk triage operations.
    
    Stores information about bulk approve/reject/escalate actions
    for performance analysis.
    """
    __tablename__ = "bulk_operations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    operation_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(String(255), nullable=True, index=True)
    action = Column(String(50), nullable=False)  # approve, reject, escalate
    failure_count = Column(Integer, nullable=False)
    total_time_ms = Column(Float, nullable=True)
    success_count = Column(Integer, default=0)
    failure_count_op = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    meta_data = Column(JSON, nullable=True)


class PerformanceCache(Base):
    """
    Model for caching frequently accessed failure summaries.
    
    Provides a caching layer for quick failure list loads.
    """
    __tablename__ = "performance_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(255), unique=True, nullable=False, index=True)
    data = Column(JSON, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


@dataclass
class TriagePerformanceRecord:
    """In-memory record for tracking performance."""
    failure_id: int
    user_id: Optional[str]
    action_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def elapsed_ms(self) -> Optional[float]:
        """Calculate elapsed time in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None


class TriageMetricsRepository:
    """
    Repository for managing triage performance metrics.
    
    Provides methods for recording and querying performance data.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the metrics repository.
        
        Args:
            db_path: Optional path to SQLite database file.
        """
        if db_path is None:
            db_path = ":memory:"
        
        self.db_path = db_path
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False} if db_path != ":memory:" else {}
        )
        # Create all tables explicitly
        Base.metadata.create_all(self.engine, checkfirst=True)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def _get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    def record_action(
        self,
        failure_id: int,
        action_type: str,
        load_time_ms: Optional[float] = None,
        action_time_ms: Optional[float] = None,
        total_time_ms: Optional[float] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TriageMetrics:
        """
        Record a triage action performance metric.
        
        Args:
            failure_id: The failure ID
            action_type: Type of action (approve, reject, etc.)
            load_time_ms: Time to load failure data
            action_time_ms: Time to perform action
            total_time_ms: Total workflow time
            user_id: User performing action
            metadata: Additional context
            
        Returns:
            Created TriageMetrics instance
        """
        with self._get_session() as session:
            metric = TriageMetrics(
                failure_id=failure_id,
                user_id=user_id,
                action_type=action_type,
                load_time_ms=load_time_ms,
                action_time_ms=action_time_ms,
                total_time_ms=total_time_ms,
                metadata=metadata,
            )
            session.add(metric)
            session.commit()
            session.refresh(metric)
            return metric
    
    def get_average_times(
        self,
        action_type: Optional[str] = None,
        hours: int = 24,
    ) -> Dict[str, float]:
        """
        Get average performance times.
        
        Args:
            action_type: Filter by action type
            hours: Time window in hours
            
        Returns:
            Dictionary with average times
        """
        with self._get_session() as session:
            from sqlalchemy import and_
            from datetime import timedelta
            
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            query = select(
                TriageMetrics.action_type,
                func.avg(TriageMetrics.total_time_ms).label('avg_total'),
                func.avg(TriageMetrics.load_time_ms).label('avg_load'),
                func.avg(TriageMetrics.action_time_ms).label('avg_action'),
                func.count(TriageMetrics.id).label('count'),
            ).where(TriageMetrics.timestamp >= cutoff)
            
            if action_type:
                query = query.where(TriageMetrics.action_type == action_type)
            
            query = query.group_by(TriageMetrics.action_type)
            
            result = session.execute(query)
            rows = result.fetchall()
            
            times = {}
            for row in rows:
                times[row[0]] = {
                    "avg_total_ms": row[1] or 0,
                    "avg_load_ms": row[2] or 0,
                    "avg_action_ms": row[3] or 0,
                    "count": row[4],
                }
            
            return times
    
    def record_bulk_operation(
        self,
        operation_id: str,
        action: str,
        failure_count: int,
        total_time_ms: Optional[float] = None,
        user_id: Optional[str] = None,
        success_count: int = 0,
        failure_count_op: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BulkOperation:
        """
        Record a bulk triage operation.
        
        Args:
            operation_id: Unique operation ID
            action: Type of bulk action
            failure_count: Number of failures processed
            total_time_ms: Total operation time
            user_id: User performing operation
            success_count: Number of successful actions
            failure_count_op: Number of failed actions
            metadata: Additional context
            
        Returns:
            Created BulkOperation instance
        """
        with self._get_session() as session:
            operation = BulkOperation(
                operation_id=operation_id,
                user_id=user_id,
                action=action,
                failure_count=failure_count,
                total_time_ms=total_time_ms,
                success_count=success_count,
                failure_count_op=failure_count_op,
                metadata=metadata,
            )
            session.add(operation)
            session.commit()
            session.refresh(operation)
            return operation


# Singleton instance
_metrics_repository: Optional[TriageMetricsRepository] = None


def get_triage_metrics_repository() -> TriageMetricsRepository:
    """Get the singleton metrics repository instance."""
    global _metrics_repository
    if _metrics_repository is None:
        _metrics_repository = TriageMetricsRepository()
    return _metrics_repository
