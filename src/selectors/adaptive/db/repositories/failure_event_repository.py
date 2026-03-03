"""
Failure Event repository for database CRUD operations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session, sessionmaker

from ..models.recipe import Base
from ..models.failure_event import FailureEvent


class FailureEventRepository:
    """
    Repository for managing failure events in SQLite database.
    
    Provides CRUD operations for failure event tracking and querying.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the failure event repository.
        
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
        return self.SessionLocal()
    
    def create(
        self,
        selector_id: str,
        error_type: str,
        timestamp: Optional[datetime] = None,
        recipe_id: Optional[str] = None,
        sport: Optional[str] = None,
        site: Optional[str] = None,
        failure_reason: Optional[str] = None,
        strategy_used: Optional[str] = None,
        resolution_time: Optional[float] = None,
        severity: str = "minor",
        context_snapshot: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        # NEW: Context fields for Story 2.3
        previous_strategy_used: Optional[str] = None,
        confidence_score_at_failure: Optional[float] = None,
        tab_type: Optional[str] = None,
        page_state: Optional[Dict[str, Any]] = None,
    ) -> FailureEvent:
        """
        Create a new failure event.
        
        Args:
            selector_id: Name/ID of the failed selector
            error_type: Classification: empty_result, exception, timeout, validation
            timestamp: When failure occurred (defaults to now)
            recipe_id: Associated recipe (if known)
            sport: Sport context (from page context)
            site: Site identifier
            failure_reason: Detailed error message
            strategy: Strategy that was attempted
            resolution_time: Time taken before failure (ms)
            severity: Severity level: minor, moderate, critical
            context_snapshot: Additional context data
            correlation_id: For tracing related events
            
        Returns:
            Created FailureEvent instance
        """
        with self._get_session() as session:
            failure_event = FailureEvent(
                selector_id=selector_id,
                error_type=error_type,
                timestamp=timestamp or datetime.utcnow(),
                recipe_id=recipe_id,
                sport=sport,
                site=site,
                failure_reason=failure_reason,
                strategy_used=strategy_used,
                resolution_time=resolution_time,
                severity=severity,
                context_snapshot=context_snapshot,
                correlation_id=correlation_id,
                # NEW: Context fields for Story 2.3
                previous_strategy_used=previous_strategy_used,
                confidence_score_at_failure=confidence_score_at_failure,
                tab_type=tab_type,
                page_state=page_state,
                created_at=datetime.utcnow(),
            )
            session.add(failure_event)
            session.commit()
            session.refresh(failure_event)
            return failure_event
    
    def get_by_id(self, event_id: int) -> Optional[FailureEvent]:
        """
        Retrieve a failure event by ID.
        
        Args:
            event_id: Unique identifier for the failure event
            
        Returns:
            FailureEvent instance if found, None otherwise
        """
        with self._get_session() as session:
            return session.execute(
                select(FailureEvent).where(FailureEvent.id == event_id)
            ).scalar_one_or_none()
    
    def get_by_selector(
        self,
        selector_id: str,
        limit: Optional[int] = None,
    ) -> List[FailureEvent]:
        """
        Get failure events for a specific selector.
        
        Args:
            selector_id: Selector name/ID
            limit: Optional limit on number of results
            
        Returns:
            List of FailureEvent instances
        """
        with self._get_session() as session:
            query = (
                select(FailureEvent)
                .where(FailureEvent.selector_id == selector_id)
                .order_by(FailureEvent.timestamp.desc())
            )
            
            if limit is not None:
                query = query.limit(limit)
            
            return list(session.execute(query).scalars().all())
    
    def get_by_recipe(
        self,
        recipe_id: str,
        limit: Optional[int] = None,
    ) -> List[FailureEvent]:
        """
        Get failure events for a specific recipe.
        
        Args:
            recipe_id: Recipe identifier
            limit: Optional limit on number of results
            
        Returns:
            List of FailureEvent instances
        """
        with self._get_session() as session:
            query = (
                select(FailureEvent)
                .where(FailureEvent.recipe_id == recipe_id)
                .order_by(FailureEvent.timestamp.desc())
            )
            
            if limit is not None:
                query = query.limit(limit)
            
            return list(session.execute(query).scalars().all())
    
    def get_by_sport_site(
        self,
        sport: Optional[str] = None,
        site: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[FailureEvent]:
        """
        Get failure events filtered by sport and/or site.
        
        Args:
            sport: Optional sport filter
            site: Optional site filter
            limit: Optional limit on number of results
            
        Returns:
            List of FailureEvent instances
        """
        with self._get_session() as session:
            query = select(FailureEvent).order_by(FailureEvent.timestamp.desc())
            
            if sport is not None:
                query = query.where(FailureEvent.sport == sport)
            
            if site is not None:
                query = query.where(FailureEvent.site == site)
            
            if limit is not None:
                query = query.limit(limit)
            
            return list(session.execute(query).scalars().all())
    
    def get_by_date_range(
        self,
        start_time: datetime,
        end_time: datetime,
        selector_id: Optional[str] = None,
        sport: Optional[str] = None,
        site: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[FailureEvent]:
        """
        Get failure events within a date range.
        
        Args:
            start_time: Start of date range
            end_time: End of date range
            selector_id: Optional selector filter
            sport: Optional sport filter
            site: Optional site filter
            limit: Optional limit on number of results
            
        Returns:
            List of FailureEvent instances
        """
        with self._get_session() as session:
            query = (
                select(FailureEvent)
                .where(FailureEvent.timestamp >= start_time)
                .where(FailureEvent.timestamp <= end_time)
                .order_by(FailureEvent.timestamp.desc())
            )
            
            if selector_id is not None:
                query = query.where(FailureEvent.selector_id == selector_id)
            
            if sport is not None:
                query = query.where(FailureEvent.sport == sport)
            
            if site is not None:
                query = query.where(FailureEvent.site == site)
            
            if limit is not None:
                query = query.limit(limit)
            
            return list(session.execute(query).scalars().all())
    
    def count_by_selector(self, selector_id: str) -> int:
        """
        Count failure events for a selector.
        
        Args:
            selector_id: Selector name/ID
            
        Returns:
            Number of failure events
        """
        with self._get_session() as session:
            return session.execute(
                select(func.count(FailureEvent.id))
                .where(FailureEvent.selector_id == selector_id)
            ).scalar() or 0
    
    def count_by_error_type(self, error_type: str) -> int:
        """
        Count failure events by error type.
        
        Args:
            error_type: Error type to count
            
        Returns:
            Number of failure events
        """
        with self._get_session() as session:
            return session.execute(
                select(func.count(FailureEvent.id))
                .where(FailureEvent.error_type == error_type)
            ).scalar() or 0
    
    def get_recent_failures(
        self,
        limit: int = 10,
        sport: Optional[str] = None,
        site: Optional[str] = None,
    ) -> List[FailureEvent]:
        """
        Get recent failure events.
        
        Args:
            limit: Number of events to return
            sport: Optional sport filter
            site: Optional site filter
            
        Returns:
            List of recent FailureEvent instances
        """
        with self._get_session() as session:
            query = (
                select(FailureEvent)
                .order_by(FailureEvent.timestamp.desc())
                .limit(limit)
            )
            
            if sport is not None:
                query = query.where(FailureEvent.sport == sport)
            
            if site is not None:
                query = query.where(FailureEvent.site == site)
            
            return list(session.execute(query).scalars().all())
    
    def delete_by_id(self, event_id: int) -> bool:
        """
        Delete a failure event by ID.
        
        Args:
            event_id: Unique identifier for the failure event
            
        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            event = session.execute(
                select(FailureEvent).where(FailureEvent.id == event_id)
            ).scalar_one_or_none()
            
            if event:
                session.delete(event)
                session.commit()
                return True
            return False
    
    def delete_old_events(self, before: datetime) -> int:
        """
        Delete failure events older than specified date.
        
        Args:
            before: Delete events before this datetime
            
        Returns:
            Number of events deleted
        """
        with self._get_session() as session:
            result = session.execute(
                select(FailureEvent).where(FailureEvent.timestamp < before)
            )
            events = result.scalars().all()
            count = len(events)
            
            for event in events:
                session.delete(event)
            
            session.commit()
            return count
    
    # =====================================================
    # Filtering and Aggregation Methods (Story 2.3)
    # =====================================================
    
    def find_with_filters(
        self,
        sport: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        selector_type: Optional[str] = None,
        error_type: Optional[str] = None,
        tab_type: Optional[str] = None,
        site: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[FailureEvent]:
        """
        Query failures with filters.
        
        Args:
            sport: Filter by sport name
            date_from: Filter failures from this date
            date_to: Filter failures until this date
            selector_type: Filter by selector type (uses selector_id pattern)
            error_type: Filter by error type
            tab_type: Filter by tab type
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of FailureEvent instances matching filters
        """
        with self._get_session() as session:
            query = select(FailureEvent).order_by(FailureEvent.timestamp.desc())
            
            if sport is not None:
                query = query.where(FailureEvent.sport == sport)
            
            if date_from is not None:
                query = query.where(FailureEvent.timestamp >= date_from)
            
            if date_to is not None:
                query = query.where(FailureEvent.timestamp <= date_to)
            
            if selector_type is not None:
                query = query.where(FailureEvent.selector_id.like(f"{selector_type}%"))
            
            if error_type is not None:
                query = query.where(FailureEvent.error_type == error_type)
            
            if tab_type is not None:
                query = query.where(FailureEvent.tab_type == tab_type)
            
            if site is not None:
                query = query.where(FailureEvent.site == site)
            
            query = query.limit(limit).offset(offset)
            
            return list(session.execute(query).scalars().all())
    
    def aggregate_by_sport(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """
        Aggregate failures by sport.
        
        Args:
            date_from: Optional date range start
            date_to: Optional date range end
            
        Returns:
            Dictionary mapping sport to failure count
        """
        with self._get_session() as session:
            query = select(
                FailureEvent.sport,
                func.count(FailureEvent.id).label('count')
            )
            
            if date_from is not None:
                query = query.where(FailureEvent.timestamp >= date_from)
            
            if date_to is not None:
                query = query.where(FailureEvent.timestamp <= date_to)
            
            query = query.group_by(FailureEvent.sport)
            
            results = session.execute(query).all()
            result_dict: Dict[str, int] = {}
            for row in results:
                sport_key = str(row[0]) if row[0] else "unknown"
                result_dict[sport_key] = int(row[1])
            return result_dict
    
    def aggregate_by_error_type(
        self,
        sport: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Aggregate failures by error type.
        
        Args:
            sport: Optional sport filter
            
        Returns:
            Dictionary mapping error_type to failure count
        """
        with self._get_session() as session:
            query = select(
                FailureEvent.error_type,
                func.count(FailureEvent.id).label('count')
            )
            
            if sport is not None:
                query = query.where(FailureEvent.sport == sport)
            
            query = query.group_by(FailureEvent.error_type)
            
            results = session.execute(query).all()
            result_dict: Dict[str, int] = {}
            for row in results:
                result_dict[str(row[0])] = int(row[1])
            return result_dict
    
    def aggregate_by_site(
        self,
        sport: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Aggregate failures by site.
        
        Args:
            sport: Optional sport filter
            
        Returns:
            Dictionary mapping site to failure count
        """
        with self._get_session() as session:
            query = select(
                FailureEvent.site,
                func.count(FailureEvent.id).label('count')
            )
            
            if sport is not None:
                query = query.where(FailureEvent.sport == sport)
            
            query = query.group_by(FailureEvent.site)
            
            results = session.execute(query).all()
            result_dict: Dict[str, int] = {}
            for row in results:
                site_key = str(row[0]) if row[0] else "unknown"
                result_dict[site_key] = int(row[1])
            return result_dict
    
    def get_failure_trend(
        self,
        date_from: datetime,
        date_to: datetime,
        group_by: str = "day",
    ) -> List[Dict[str, Any]]:
        """
        Get failure trend over time.
        
        Args:
            date_from: Start of date range
            date_to: End of date range
            group_by: Grouping granularity - 'day', 'week', or 'month'
            
        Returns:
            List of dictionaries with date and count
        """
        with self._get_session() as session:
            # SQLite doesn't support all date functions, so we use a simple approach
            if group_by == "day":
                date_format = "%Y-%m-%d"
            elif group_by == "week":
                date_format = "%Y-W%W"
            else:  # month
                date_format = "%Y-%m"
            
            query = select(
                func.strftime(date_format, FailureEvent.timestamp).label('date'),
                func.count(FailureEvent.id).label('count')
            ).where(
                FailureEvent.timestamp >= date_from
            ).where(
                FailureEvent.timestamp <= date_to
            ).group_by(
                func.strftime(date_format, FailureEvent.timestamp)
            ).order_by(
                func.strftime(date_format, FailureEvent.timestamp)
            )
            
            results = session.execute(query).all()
            return [{"date": row.date, "count": row.count} for row in results]
    
    def close(self):
        """Close the database connection."""
        self.engine.dispose()
