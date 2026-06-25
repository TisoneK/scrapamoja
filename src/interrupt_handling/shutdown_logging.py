"""
Shutdown status logging for interrupt handling.
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Any, TextIO
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from .messaging import InterruptMessageHandler
from .resource_manager import ResourceManager


class ShutdownPhase(Enum):
    """Phases of the shutdown process."""
    INITIATED = "initiated"
    ACKNOWLEDGED = "acknowledged"
    CALLBACKS_EXECUTED = "callbacks_executed"
    RESOURCE_CLEANUP_STARTED = "resource_cleanup_started"
    RESOURCE_CLEANUP_COMPLETED = "resource_cleanup_completed"
    DATA_PRESERVATION_STARTED = "data_preservation_started"
    DATA_PRESERVATION_COMPLETED = "data_preservation_completed"
    FINALIZATION_STARTED = "finalization_started"
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"


class ShutdownStatus(Enum):
    """Overall shutdown status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ShutdownEvent:
    """An event during the shutdown process."""
    phase: ShutdownPhase
    timestamp: float = field(default_factory=time.time)
    duration: Optional[float] = None
    success: Optional[bool] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def age(self) -> float:
        """Get age of the event in seconds."""
        return time.time() - self.timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'phase': self.phase.value,
            'timestamp': self.timestamp,
            'duration': self.duration,
            'success': self.success,
            'message': self.message,
            'age': self.age,
            'metadata': self.metadata
        }


class ShutdownLogger:
    """Logs shutdown events and provides status reporting."""
    
    def __init__(self, log_file: Optional[Path] = None, message_handler: Optional[InterruptMessageHandler] = None):
        self.logger = logging.getLogger(__name__)
        self.message_handler = message_handler
        
        # Log file setup
        if log_file:
            self.log_file = Path(log_file)
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.log_file = None
        
        # Shutdown state
        self._events: List[ShutdownEvent] = []
        self._current_phase: Optional[ShutdownPhase] = None
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        self._lock = threading.RLock()
        
        # Statistics
        self._phase_counts = {phase.value: 0 for phase in ShutdownPhase}
        self._error_count = 0
        self._timeout_count = 0
    
    def start_shutdown(self, metadata: Optional[Dict[str, Any]] = None):
        """Start the shutdown process."""
        with self._lock:
            if self._current_phase is not None:
                self.logger.warning("Shutdown already in progress")
                return
            
            self._current_phase = ShutdownPhase.INITIATED
            self._start_time = time.time()
            
            event = ShutdownEvent(
                phase=ShutdownPhase.INITIATED,
                message="Shutdown process started",
                metadata=metadata or {}
            )
            
            self._add_event(event)
            self._log_to_file(event)
    
    def transition_to_phase(self, phase: ShutdownPhase, success: Optional[bool] = None,
                          message: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Transition to a new shutdown phase."""
        with self._lock:
            if self._current_phase is None:
                self.logger.warning("Shutdown not started, cannot transition phase")
                return
            
            # Calculate duration of previous phase
            previous_event = self._events[-1] if self._events else None
            if previous_event:
                previous_event.duration = time.time() - previous_event.timestamp
            
            # Create new event
            event = ShutdownEvent(
                phase=phase,
                success=success,
                message=message,
                metadata=metadata or {}
            )
            
            self._current_phase = phase
            self._add_event(event)
            self._log_to_file(event)
            
            # Update statistics
            if phase == ShutdownPhase.ERROR:
                self._error_count += 1
            elif phase == ShutdownPhase.TIMEOUT:
                self._timeout_count += 1
    
    def complete_shutdown(self, success: bool, message: Optional[str] = None):
        """Complete the shutdown process."""
        with self._lock:
            if self._current_phase is None:
                self.logger.warning("Shutdown not started, cannot complete")
                return
            
            self._end_time = time.time()
            
            # Calculate total duration
            total_duration = self._end_time - self._start_time if self._start_time else 0
            
            # Create completion event
            final_phase = ShutdownPhase.COMPLETED if success else ShutdownPhase.ERROR
            event = ShutdownEvent(
                phase=final_phase,
                duration=total_duration,
                success=success,
                message=message or ("Shutdown completed successfully" if success else "Shutdown failed"),
                metadata={
                    'total_duration': total_duration,
                    'final_status': final_phase.value
                }
            )
            
            self._current_phase = final_phase
            self._add_event(event)
            self._log_to_file(event)
    
    def log_phase_start(self, phase: ShutdownPhase, details: Optional[str] = None):
        """Log the start of a phase."""
        message = f"Started {phase.value}"
        if details:
            message += f": {details}"
        
        self.transition_to_phase(phase, success=True, message=message)
    
    def log_phase_completion(self, phase: ShutdownPhase, success: bool, 
                           details: Optional[str] = None, duration: Optional[float] = None):
        """Log the completion of a phase."""
        status = "completed successfully" if success else "failed"
        message = f"{phase.value} {status}"
        if details:
            message += f": {details}"
        
        self.transition_to_phase(phase, success=success, message=message, metadata={'duration': duration})
    
    def log_error(self, error: Exception, *, phase: Optional[ShutdownPhase] = None, 
                 details: Optional[str] = None):
        """Log an error during shutdown."""
        message = f"Error: {error}"
        if details:
            message += f" - {details}"
        
        if phase:
            self.transition_to_phase(ShutdownPhase.ERROR, success=False, message=message, 
                              metadata={'error_type': type(error).__name__, 'error_message': str(error)})
        else:
            # Log error without phase transition
            event = ShutdownEvent(
                phase=ShutdownPhase.ERROR,
                message=message,
                metadata={'error_type': type(error).__name__, 'error_message': str(error)}
            )
            self._add_event(event)
            self._log_to_file(event)
    
    def log_timeout(self, phase: Optional[ShutdownPhase] = None, timeout_duration: Optional[float] = None,
                  details: Optional[str] = None):
        """Log a timeout during shutdown."""
        message = "Timeout occurred"
        if details:
            message += f": {details}"
        
        if phase:
            self.transition_to_phase(ShutdownPhase.TIMEOUT, success=False, message=message,
                              metadata={'timeout_duration': timeout_duration})
        else:
            # Log timeout without phase transition
            event = ShutdownEvent(
                phase=ShutdownPhase.TIMEOUT,
                message=message,
                metadata={'timeout_duration': timeout_duration}
            )
            self._add_event(event)
            self._log_to_file(event)
    
    def log_resource_cleanup(self, resource_type: str, count: int, success_count: int, 
                           failed_count: int, duration: float):
        """Log resource cleanup results."""
        message = f"Resource cleanup: {resource_type} - {success_count}/{count} successful"
        if failed_count > 0:
            message += f", {failed_count} failed"
        
        self.transition_to_phase(
            ShutdownPhase.RESOURCE_CLEANUP_COMPLETED,
            success=failed_count == 0,
            message=message,
            metadata={
                'resource_type': resource_type,
                'total_count': count,
                'success_count': success_count,
                'failed_count': failed_count,
                'duration': duration
            }
        )
    
    def log_data_preservation(self, checkpoint_created: bool, checkpoint_path: Optional[str] = None,
                           *, duration: float):
        """Log data preservation results."""
        if checkpoint_created:
            message = f"Data preservation completed: checkpoint created"
            if checkpoint_path:
                message += f" at {checkpoint_path}"
        else:
            message = "Data preservation failed: checkpoint creation failed"
        
        self.transition_to_phase(
            ShutdownPhase.DATA_PRESERVATION_COMPLETED,
            success=checkpoint_created,
            message=message,
            metadata={
                'checkpoint_created': checkpoint_created,
                'checkpoint_path': checkpoint_path,
                'duration': duration
            }
        )
    
    def get_current_status(self) -> ShutdownStatus:
        """Get the current shutdown status."""
        with self._lock:
            if self._current_phase is None:
                return ShutdownStatus.NOT_STARTED
            elif self._current_phase in [ShutdownPhase.COMPLETED]:
                return ShutdownStatus.COMPLETED
            elif self._current_phase in [ShutdownPhase.ERROR, ShutdownPhase.TIMEOUT]:
                return ShutdownStatus.FAILED
            else:
                return ShutdownStatus.IN_PROGRESS
    
    def get_shutdown_summary(self) -> Dict[str, Any]:
        """Get a summary of the shutdown process."""
        with self._lock:
            if self._start_time is None:
                return {'status': 'No shutdown recorded'}
            
            current_time = time.time()
            total_duration = (self._end_time or current_time) - self._start_time
            
            # Count phases
            phase_counts = self._phase_counts.copy()
            for event in self._events:
                phase_counts[event.phase.value] += 1
            
            # Get recent events
            recent_events = [event for event in self._events if event.age < 300]  # Last 5 minutes
            
            return {
                'status': self.get_current_status().value,
                'current_phase': self._current_phase.value if self._current_phase else None,
                'start_time': self._start_time,
                'end_time': self._end_time,
                'total_duration': total_duration,
                'total_events': len(self._events),
                'phase_counts': phase_counts,
                'error_count': self._error_count,
                'timeout_count': self._timeout_count,
                'recent_events_count': len(recent_events),
                'recent_events': [event.to_dict() for event in recent_events[-10:]]  # Last 10 events
            }
    
    def get_phase_timeline(self) -> List[Dict[str, Any]]:
        """Get a timeline of all shutdown phases."""
        with self._lock:
            return [event.to_dict() for event in self._events]
    
    def get_events_by_phase(self, phase: ShutdownPhase) -> List[ShutdownEvent]:
        """Get all events for a specific phase."""
        with self._lock:
            return [event for event in self._events if event.phase == phase]
    
    def _add_event(self, event: ShutdownEvent):
        """Add an event to the log."""
        self._events.append(event)
        self._phase_counts[event.phase.value] += 1
        
        # Send message to message handler if available
        if self.message_handler:
            if event.phase == ShutdownPhase.ERROR:
                self.message_handler.send_custom_message(
                    event.message or "Shutdown error occurred",
                    MessageType.ERROR,
                    MessagePriority.HIGH
                )
            elif event.phase == ShutdownPhase.COMPLETED:
                self.message_handler.send_custom_message(
                    event.message or "Shutdown completed",
                    MessageType.COMPLETION,
                    MessagePriority.HIGH
                )
    
    def _log_to_file(self, event: ShutdownEvent):
        """Log an event to the log file."""
        if not self.log_file:
            return
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event.timestamp))
                log_entry = f"[{timestamp}] {event.phase.value}: {event.message or ''}\n"
                
                if event.metadata:
                    for key, value in event.metadata.items():
                        log_entry += f"  {key}: {value}\n"
                
                f.write(log_entry)
                f.flush()
                
        except Exception as e:
            self.logger.error(f"Error writing to shutdown log: {e}")
    
    def clear_log(self):
        """Clear the shutdown log."""
        with self._lock:
            self._events.clear()
            self._phase_counts = {phase.value: 0 for phase in ShutdownPhase}
            self._error_count = 0
            self._timeout_count = 0
            self._current_phase = None
            self._start_time = None
            self._end_time = None
        
        # Clear log file
        if self.log_file and self.log_file.exists():
            try:
                self.log_file.unlink()
                self.logger.info("Shutdown log cleared")
            except Exception as e:
                self.logger.error(f"Error clearing shutdown log: {e}")
    
    def export_log(self, export_path: Path) -> bool:
        """Export the shutdown log to a file."""
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write("# Shutdown Log Export\n")
                f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for event in self._events:
                    f.write(f"## {event.phase.value}\n")
                    f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event.timestamp))}\n")
                    if event.duration:
                        f.write(f"Duration: {event.duration:.2f}s\n")
                    if event.success is not None:
                        f.write(f"Success: {event.success}\n")
                    if event.message:
                        f.write(f"Message: {event.message}\n")
                    if event.metadata:
                        f.write("Metadata:\n")
                        for key, value in event.metadata.items():
                            f.write(f"  {key}: {value}\n")
                    f.write("\n")
            
            self.logger.info(f"Shutdown log exported to {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting shutdown log: {e}")
            return False


# Global shutdown logger instance
_shutdown_logger = None


def get_shutdown_logger(log_file: Optional[Path] = None,
                     message_handler: Optional[InterruptMessageHandler] = None) -> ShutdownLogger:
    """Get the global shutdown logger instance."""
    global _shutdown_logger
    if _shutdown_logger is None:
        _shutdown_logger = ShutdownLogger(log_file, message_handler)
    return _shutdown_logger
