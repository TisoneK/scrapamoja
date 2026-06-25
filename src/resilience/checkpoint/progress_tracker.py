"""
Progress Tracker for Checkpointing

Tracks and manages progress information for checkpointing operations,
including incremental progress calculation, milestone tracking, and progress
state management.
"""

import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from ..logging.resilience_logger import get_logger
from ..correlation import get_correlation_id
from ..events import publish_checkpoint_event


class ProgressState(Enum):
    """Progress tracking states."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressMilestone:
    """Represents a progress milestone."""
    id: str
    name: str
    description: str
    target_value: float
    current_value: float = 0.0
    completed: bool = False
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def progress_percentage(self) -> float:
        """Calculate progress percentage for this milestone."""
        if self.target_value == 0:
            return 100.0 if self.completed else 0.0
        return min(100.0, (self.current_value / self.target_value) * 100)
    
    def is_complete(self) -> bool:
        """Check if milestone is complete."""
        return self.completed or self.current_value >= self.target_value
    
    def mark_completed(self) -> None:
        """Mark milestone as completed."""
        self.completed = True
        self.completed_at = datetime.utcnow()
        self.current_value = self.target_value
    
    def update_progress(self, value: float) -> None:
        """Update milestone progress."""
        self.current_value = min(value, self.target_value)
        if self.is_complete():
            self.mark_completed()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "progress_percentage": self.progress_percentage(),
            "completed": self.completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ProgressSnapshot:
    """Snapshot of progress at a specific point in time."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    overall_progress: float = 0.0
    milestones: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    state: ProgressState = ProgressState.NOT_STARTED
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall_progress": self.overall_progress,
            "milestones": self.milestones,
            "metrics": self.metrics,
            "state": self.state.value,
            "custom_data": self.custom_data
        }


class ProgressTracker:
    """Tracks progress for checkpointing operations."""
    
    def __init__(self, job_id: str):
        """
        Initialize progress tracker.
        
        Args:
            job_id: Job identifier
        """
        self.job_id = job_id
        self.logger = get_logger("progress_tracker")
        
        self.milestones: Dict[str, ProgressMilestone] = {}
        self.snapshots: List[ProgressSnapshot] = []
        self.progress_callbacks: List[Callable] = []
        self.state = ProgressState.NOT_STARTED
        
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.pause_time: Optional[datetime] = None
        self.total_pause_duration: float = 0.0
        
        self.current_progress: float = 0.0
        self.target_progress: float = 100.0
        
        # Progress metrics
        self.metrics: Dict[str, Any] = defaultdict(float)
        self.custom_data: Dict[str, Any] = {}
        
        # Progress calculation configuration
        self.milestone_weights: Dict[str, float] = {}
        self.auto_snapshot_interval: int = 60  # seconds
        self.last_snapshot_time: Optional[datetime] = None
        
        # Auto-cleanup
        self.max_snapshots: int = 100
        self.snapshot_retention_hours: int = 24
    
    def add_milestone(
        self,
        milestone_id: str,
        name: str,
        description: str,
        target_value: float,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a progress milestone.
        
        Args:
            milestone_id: Unique milestone identifier
            name: Milestone name
            description: Milestone description
            target_value: Target value for completion
            weight: Weight in overall progress calculation
            metadata: Additional metadata
        """
        milestone = ProgressMilestone(
            id=milestone_id,
            name=name,
            description=description,
            target_value=target_value,
            metadata=metadata or {}
        )
        
        self.milestones[milestone_id] = milestone
        self.milestone_weights[milestone_id] = weight
        
        self.logger.info(
            f"Added milestone: {name} ({milestone_id}) for job {self.job_id}",
            event_type="milestone_added",
            correlation_id=get_correlation_id(),
            context={
                "job_id": self.job_id,
                "milestone_id": milestone_id,
                "name": name,
                "target_value": target_value,
                "weight": weight
            },
            component="progress_tracker"
        )
        
        # Recalculate overall progress
        self._recalculate_progress()
    
    def remove_milestone(self, milestone_id: str) -> bool:
        """
        Remove a progress milestone.
        
        Args:
            milestone_id: Milestone identifier to remove
            
        Returns:
            True if removed, False if not found
        """
        if milestone_id in self.milestones:
            del self.milestones[milestone_id]
            if milestone_id in self.milestone_weights:
                del self.milestone_weights[milestone_id]
            
            self._recalculate_progress()
            
            self.logger.info(
                f"Removed milestone: {milestone_id} for job {self.job_id}",
                event_type="milestone_removed",
                correlation_id=get_correlation_id(),
                context={
                    "job_id": self.job_id,
                    "milestone_id": milestone_id
                },
                component="progress_tracker"
            )
            
            return True
        
        return False
    
    def update_milestone(
        self,
        milestone_id: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update milestone progress.
        
        Args:
            milestone_id: Milestone identifier
            value: New progress value
            metadata: Additional metadata
            
        Returns:
            True if updated, False if not found
        """
        if milestone_id not in self.milestones:
            return False
        
        milestone = self.milestones[milestone_id]
        old_progress = milestone.progress_percentage()
        
        milestone.update_progress(value)
        
        if metadata:
            milestone.metadata.update(metadata)
        
        # Recalculate overall progress
        self._recalculate_progress()
        
        # Check if milestone was just completed
        if not milestone.completed and milestone.is_complete():
            self.logger.info(
                f"Milestone completed: {milestone.name} ({milestone_id}) for job {self.job_id}",
                event_type="milestone_completed",
                correlation_id=get_correlation_id(),
                context={
                    "job_id": self.job_id,
                    "milestone_id": milestone_id,
                    "milestone_name": milestone.name,
                    "progress": milestone.progress_percentage()
                },
                component="progress_tracker"
            )
            
            # Publish checkpoint event
            from ..events import publish_checkpoint_event
            publish_checkpoint_event(
                action="milestone_completed",
                checkpoint_id=f"progress_{self.job_id}",
                job_id=self.job_id,
                context={
                    "milestone_id": milestone_id,
                    "milestone_name": milestone.name,
                    "progress": milestone.progress_percentage()
                },
                component="progress_tracker"
            )
        
        # Notify callbacks
        self._notify_progress_callbacks(old_progress, milestone.progress_percentage())
        
        return True
    
    def set_target_progress(self, target: float) -> None:
        """
        Set the target progress value.
        
        Args:
            target: Target progress value (0-100)
        """
        self.target_progress = max(0.0, min(100.0, target))
        self._recalculate_progress()
    
    def get_progress(self) -> float:
        """Get current overall progress."""
        return self.current_progress
    
    def get_milestone_progress(self, milestone_id: str) -> Optional[float]:
        """Get progress for a specific milestone."""
        if milestone_id in self.milestones:
            return self.milestones[milestone_id].progress_percentage()
        return None
    
    def get_milestone_status(self, milestone_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status for a specific milestone."""
        if milestone_id not in self.milestones:
            return None
        
        milestone = self.milestones[milestone_id]
        return {
            "id": milestone.id,
            "name": milestone.name,
            "description": milestone.description,
            "target_value": milestone.target_value,
            "current_value": milestone.current_value,
            "progress_percentage": milestone.progress_percentage(),
            "completed": milestone.completed,
            "completed_at": milestone.completed_at.isoformat() if milestone.completed_at else None,
            "created_at": milestone.created_at.isoformat(),
            "metadata": milestone.metadata
        }
    
    def get_all_milestones(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all milestones."""
        return {
            milestone_id: self.get_milestone_status(milestone_id)
            for milestone_id in self.milestones
        }
    
    def get_completed_milestones(self) -> List[str]:
        """Get list of completed milestone IDs."""
        return [
            milestone_id for milestone_id, milestone in self.milestones.items()
            if milestone.is_complete()
        ]
    
    def get_pending_milestones(self) -> List[str]:
        """Get list of pending milestone IDs."""
        return [
            milestone_id for milestone_id, milestone in self.milestones.items()
            if not milestone.is_complete()
        ]
    
    def start_progress(self) -> None:
        """Start progress tracking."""
        if self.state == ProgressState.NOT_STARTED:
            self.state = ProgressState.IN_PROGRESS
            self.start_time = datetime.utcnow()
            
            self.logger.info(
                f"Progress tracking started for job {self.job_id}",
                event_type="progress_started",
                correlation_id=get_correlation_id(),
                context={"job_id": self.job_id},
                component="progress_tracker"
            )
            
            # Create initial snapshot
            self._create_snapshot()
    
    def pause_progress(self) -> None:
        """Pause progress tracking."""
        if self.state == ProgressState.IN_PROGRESS:
            self.state = ProgressState.PAUSED
            self.pause_time = datetime.utcnow()
            
            self.logger.info(
                f"Progress tracking paused for job {self.job_id}",
                event_type="progress_paused",
                correlation_id=get_correlation_id(),
                context={
                    "job_id": self.job_id,
                    "current_progress": self.current_progress
                },
                component="progress_tracker"
            )
    
    def resume_progress(self) -> None:
        """Resume progress tracking."""
        if self.state == ProgressState.PAUSED:
            if self.pause_time:
                pause_duration = (datetime.utcnow() - self.pause_time).total_seconds()
                self.total_pause_duration += pause_duration
                self.pause_time = None
            
            self.state = ProgressState.IN_PROGRESS
            
            self.logger.info(
                f"Progress tracking resumed for job {self.job_id}",
                event_type="progress_resumed",
                correlation_id=get_correlation_id(),
                context={
                    "job_id": self.job_id,
                    "current_progress": self.current_progress,
                    "total_pause_duration": self.total_pause_duration
                },
                component="progress_tracker"
            )
    
    def complete_progress(self) -> None:
        """Mark progress as completed."""
        if self.state in [ProgressState.IN_PROGRESS, ProgressState.PAUSED]:
            self.state = ProgressState.COMPLETED
            self.end_time = datetime.utcnow()
            self.current_progress = 100.0
            
            # Mark all remaining milestones as completed
            for milestone in self.milestones.values():
                if not milestone.completed:
                    milestone.mark_completed()
            
            # Create final snapshot
            self._create_snapshot()
            
            self.logger.info(
                f"Progress tracking completed for job {self.job_id}",
                event_type="progress_completed",
                correlation_id=get_correlation_id(),
                context={
                    "job_id": self.job_id,
                    "duration": self.get_duration(),
                    "total_pause_duration": self.total_pause_duration
                },
                component="progress_tracker"
            )
    
    def fail_progress(self, error: Optional[str] = None) -> None:
        """Mark progress as failed."""
        if self.state in [ProgressState.IN_PROGRESS, ProgressState.PAUSED]:
            self.state = ProgressState.FAILED
            self.end_time = datetime.utcnow()
            
            self.logger.error(
                f"Progress tracking failed for job {self.job_id}: {error or 'Unknown error'}",
                event_type="progress_failed",
                correlation_id=get_correlation_id(),
                context={
                    "job_id": self.job_id,
                    "current_progress": self.current_progress,
                    "error": error
                },
                component="progress_tracker"
            )
    
    def cancel_progress(self) -> None:
        """Cancel progress tracking."""
        if self.state in [ProgressState.IN_PROGRESS, ProgressState.PAUSED]:
            self.state = ProgressState.CANCELLED
            self.end_time = datetime.utcnow()
            
            self.logger.info(
                f"Progress tracking cancelled for job {self.job_id}",
                event_type="progress_cancelled",
                correlation_id=get_correlation_id(),
                context={
                    "job_id": self.job_id,
                    "current_progress": self.current_progress
                },
                component="progress_tracker"
            )
    
    def get_state(self) -> ProgressState:
        """Get current progress state."""
        return self.state
    
    def get_duration(self) -> float:
        """Get total duration of progress tracking."""
        if not self.start_time:
            return 0.0
        
        end_time = self.end_time or datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()
        
        # Subtract pause time
        if self.pause_time:
            pause_duration = (datetime.utcnow() - self.pause_time).total_seconds()
            duration -= pause_duration
        
        return max(0, duration)
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time since start (excluding pause time)."""
        if not self.start_time:
            return 0.0
        
        current_time = datetime.utcnow()
        elapsed = (current_time - self.start_time).total_seconds()
        
        # Subtract pause time
        if self.pause_time:
            pause_duration = (current_time - self.pause_time).total_seconds()
            elapsed -= pause_duration
        
        return max(0, elapsed)
    
    def add_progress_callback(self, callback: Callable[[float, float], None]) -> None:
        """
        Add a progress callback function.
        
        Args:
            callback: Function that receives (old_progress, new_progress)
        """
        self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable) -> bool:
        """
        Remove a progress callback function.
        
        Args:
            callback: Callback function to remove
            
        Returns:
            True if removed, False if not found
        """
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
            return True
        return False
    
    def update_metric(self, metric_name: str, value: float) -> None:
        """
        Update a progress metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
        """
        old_value = self.metrics.get(metric_name, 0.0)
        self.metrics[metric_name] = value
        
        self.logger.debug(
            f"Updated metric {metric_name}: {old_value} -> {value} for job {self.job_id}",
            event_type="metric_updated",
            correlation_id=get_correlation_id(),
            context={
                "job_id": self.job_id,
                "metric_name": metric_name,
                "old_value": old_value,
                "new_value": value
            },
            component="progress_tracker"
        )
    
    def get_metric(self, metric_name: str) -> float:
        """
        Get a progress metric value.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Metric value
        """
        return self.metrics.get(metric_name, 0.0)
    
    def set_custom_data(self, key: str, value: Any) -> None:
        """
        Set custom data.
        
        Args:
            key: Data key
            value: Data value
        """
        self.custom_data[key] = value
    
    def get_custom_data(self, key: str) -> Any:
        """
        Get custom data value.
        
        Args:
            key: Data key
            
        Returns:
            Data value
        """
        return self.custom_data.get(key)
    
    def _recalculate_progress(self) -> None:
        """Recalculate overall progress based on milestones."""
        if not self.milestones:
            self.current_progress = 0.0
            return
        
        total_weight = sum(self.milestone_weights.values())
        if total_weight == 0:
            self.current_progress = 0.0
            return
        
        weighted_progress = 0.0
        for milestone_id, milestone in self.milestones.items():
            weight = self.milestone_weights.get(milestone_id, 1.0)
            weighted_progress += (milestone.progress_percentage() / 100.0) * weight
        
        self.current_progress = (weighted_progress / total_weight) * 100
        
        # Clamp to target progress
        self.current_progress = min(self.current_progress, self.target_progress)
        
        # Notify callbacks
        self._notify_progress_callbacks(None, self.current_progress)
    
    def _notify_progress_callbacks(self, old_progress: Optional[float], new_progress: float) -> None:
        """Notify all progress callbacks."""
        for callback in self.progress_callbacks:
            try:
                callback(old_progress, new_progress)
            except Exception as e:
                self.logger.error(
                    f"Error in progress callback: {str(e)}",
                    event_type="progress_callback_error",
                    correlation_id=get_correlation_id(),
                    context={
                        "job_id": self.job_id,
                        "error": str(e)
                    },
                    component="progress_tracker"
                )
    
    def _create_snapshot(self) -> None:
        """Create a progress snapshot."""
        snapshot = ProgressSnapshot(
            overall_progress=self.current_progress,
            milestones={
                milestone_id: milestone.to_dict()
                for milestone_id, milestone in self.milestones.items()
            },
            metrics=dict(self.metrics),
            state=self.state,
            custom_data=self.custom_data.copy()
        )
        
        self.snapshots.append(snapshot)
        self.last_snapshot_time = datetime.utcnow()
        
        # Cleanup old snapshots
        self._cleanup_old_snapshots()
    
    def _cleanup_old_snapshots(self) -> None:
        """Clean up old snapshots based on retention policy."""
        if len(self.snapshots) <= self.max_snapshots:
            return
        
        # Calculate cutoff time
        cutoff_time = datetime.utcnow() - timedelta(hours=self.snapshot_retention_hours)
        
        # Remove old snapshots
        original_count = len(self.snapshots)
        self.snapshots = [
            snapshot for snapshot in self.snapshots
            if snapshot.timestamp >= cutoff_time
        ]
        
        removed_count = original_count - len(self.snapshots)
        
        if removed_count > 0:
            self.logger.info(
                f"Cleaned up {removed_count} old progress snapshots for job {self.job_id}",
                event_type="progress_snapshots_cleaned",
                correlation_id=get_correlation_id(),
                context={
                    "job_id": self.job_id,
                    "removed_count": removed_count,
                    "remaining_count": len(self.snapshots)
                },
                component="progress_tracker"
            )
    
    def get_progress_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get progress history from snapshots.
        
        Args:
            limit: Maximum number of snapshots to return
            
        Returns:
            List of progress snapshots
        """
        snapshots = self.snapshots.copy()
        snapshots.sort(key=lambda s: s.timestamp, reverse=True)
        
        if limit:
            snapshots = snapshots[:limit]
        
        return [snapshot.to_dict() for snapshot in snapshots]
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current progress status.
        
        Returns:
            Progress summary
        """
        completed_milestones = self.get_completed_milestones()
        pending_milestones = self.get_pending_milestones()
        
        return {
            "job_id": self.job_id,
            "state": self.state.value,
            "current_progress": self.current_progress,
            "target_progress": self.target_progress,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.get_duration(),
            "elapsed_time": self.get_elapsed_time(),
            "total_milestones": len(self.milestones),
            "completed_milestones": len(completed_milestones),
            "pending_milestones": len(pending_milestones),
            "completion_rate": (
                (len(completed_milestones) / len(self.milestones)) * 100
                if self.milestones else 0
            ),
            "total_pause_duration": self.total_pause_duration,
            "metrics": dict(self.metrics),
            "custom_data": self.custom_data
        }


# Global progress tracker instances
_progress_trackers: Dict[str, ProgressTracker] = {}


def get_progress_tracker(job_id: str) -> ProgressTracker:
    """Get or create a progress tracker for a job."""
    if job_id not in _progress_trackers:
        _progress_trackers[job_id] = ProgressTracker(job_id)
    return _progress_trackers[job_id]


def create_progress_tracker(job_id: str) -> ProgressTracker:
    """Create a new progress tracker for a job."""
    return ProgressTracker(job_id)
