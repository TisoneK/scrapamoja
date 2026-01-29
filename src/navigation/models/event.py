"""
NavigationEvent entity

Recorded navigation action with context, outcome, and performance metrics.
Conforms to Constitution Principle III - Deep Modularity.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import json

from .context import NavigationOutcome


@dataclass
class EventPerformanceMetrics:
    """Performance metrics for navigation events"""
    
    duration_seconds: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    network_requests_count: int = 0
    dom_changes_count: int = 0
    javascript_errors_count: int = 0
    console_warnings_count: int = 0
    page_load_time: float = 0.0
    render_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            'duration_seconds': self.duration_seconds,
            'cpu_usage_percent': self.cpu_usage_percent,
            'memory_usage_mb': self.memory_usage_mb,
            'network_requests_count': self.network_requests_count,
            'dom_changes_count': self.dom_changes_count,
            'javascript_errors_count': self.javascript_errors_count,
            'console_warnings_count': self.console_warnings_count,
            'page_load_time': self.page_load_time,
            'render_time': self.render_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventPerformanceMetrics':
        """Create metrics from dictionary"""
        return cls(
            duration_seconds=data.get('duration_seconds', 0.0),
            cpu_usage_percent=data.get('cpu_usage_percent', 0.0),
            memory_usage_mb=data.get('memory_usage_mb', 0.0),
            network_requests_count=data.get('network_requests_count', 0),
            dom_changes_count=data.get('dom_changes_count', 0),
            javascript_errors_count=data.get('javascript_errors_count', 0),
            console_warnings_count=data.get('console_warnings_count', 0),
            page_load_time=data.get('page_load_time', 0.0),
            render_time=data.get('render_time', 0.0)
        )


@dataclass
class NavigationEvent:
    """Recorded navigation action with context and outcome"""
    
    # Core identification
    event_id: str
    
    # Timing
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Navigation details
    route_id: str
    context_before: str
    context_after: str
    
    # Outcome
    outcome: NavigationOutcome = NavigationOutcome.SUCCESS
    
    # Performance metrics
    performance_metrics: EventPerformanceMetrics = field(default_factory=EventPerformanceMetrics)
    
    # Error information
    error_details: Optional[str] = None
    error_code: Optional[str] = None
    error_stack_trace: Optional[str] = None
    
    # Additional context
    user_agent: str = ""
    page_url_before: str = ""
    page_url_after: str = ""
    session_id: str = ""
    correlation_id: str = ""
    
    # Detection and security
    detection_triggers: List[str] = field(default_factory=list)
    stealth_score_before: float = 0.0
    stealth_score_after: float = 0.0
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate event after dataclass creation"""
        self._validate_event()
    
    def _validate_event(self) -> None:
        """Validate event data according to business rules"""
        if not self.event_id:
            raise ValueError("Event ID cannot be empty")
        
        if not self.route_id:
            raise ValueError("Route ID cannot be empty")
        
        if not self.context_before:
            raise ValueError("Context before cannot be empty")
        
        if not self.context_after:
            raise ValueError("Context after cannot be empty")
        
        if not 0.0 <= self.stealth_score_before <= 1.0:
            raise ValueError("Stealth score before must be between 0.0 and 1.0")
        
        if not 0.0 <= self.stealth_score_after <= 1.0:
            raise ValueError("Stealth score after must be between 0.0 and 1.0")
    
    def is_successful(self) -> bool:
        """Check if navigation event was successful"""
        return self.outcome == NavigationOutcome.SUCCESS
    
    def is_failure(self) -> bool:
        """Check if navigation event failed"""
        return self.outcome in [
            NavigationOutcome.FAILURE,
            NavigationOutcome.TIMEOUT,
            NavigationOutcome.DETECTED
        ]
    
    def has_detection_triggers(self) -> bool:
        """Check if event has detection triggers"""
        return len(self.detection_triggers) > 0
    
    def get_stealth_score_change(self) -> float:
        """Get change in stealth score"""
        return self.stealth_score_after - self.stealth_score_before
    
    def has_stealth_degradation(self) -> bool:
        """Check if stealth score degraded"""
        return self.stealth_score_after < self.stealth_score_before
    
    def add_detection_trigger(self, trigger: str) -> None:
        """Add a detection trigger to the event"""
        if trigger not in self.detection_triggers:
            self.detection_triggers.append(trigger)
    
    def set_error(
        self, 
        error_details: str, 
        error_code: Optional[str] = None,
        error_stack_trace: Optional[str] = None
    ) -> None:
        """Set error information for the event"""
        self.error_details = error_details
        self.error_code = error_code
        self.error_stack_trace = error_stack_trace
    
    def update_performance_metrics(
        self,
        duration_seconds: Optional[float] = None,
        cpu_usage_percent: Optional[float] = None,
        memory_usage_mb: Optional[float] = None,
        network_requests_count: Optional[int] = None,
        dom_changes_count: Optional[int] = None,
        javascript_errors_count: Optional[int] = None,
        console_warnings_count: Optional[int] = None,
        page_load_time: Optional[float] = None,
        render_time: Optional[float] = None
    ) -> None:
        """Update performance metrics"""
        if duration_seconds is not None:
            self.performance_metrics.duration_seconds = duration_seconds
        if cpu_usage_percent is not None:
            self.performance_metrics.cpu_usage_percent = cpu_usage_percent
        if memory_usage_mb is not None:
            self.performance_metrics.memory_usage_mb = memory_usage_mb
        if network_requests_count is not None:
            self.performance_metrics.network_requests_count = network_requests_count
        if dom_changes_count is not None:
            self.performance_metrics.dom_changes_count = dom_changes_count
        if javascript_errors_count is not None:
            self.performance_metrics.javascript_errors_count = javascript_errors_count
        if console_warnings_count is not None:
            self.performance_metrics.console_warnings_count = console_warnings_count
        if page_load_time is not None:
            self.performance_metrics.page_load_time = page_load_time
        if render_time is not None:
            self.performance_metrics.render_time = render_time
    
    def get_event_summary(self) -> Dict[str, Any]:
        """Get summary of the navigation event"""
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'route_id': self.route_id,
            'outcome': self.outcome.value,
            'duration_seconds': self.performance_metrics.duration_seconds,
            'is_successful': self.is_successful(),
            'has_detection_triggers': self.has_detection_triggers(),
            'detection_triggers_count': len(self.detection_triggers),
            'stealth_score_change': self.get_stealth_score_change(),
            'has_stealth_degradation': self.has_stealth_degradation(),
            'error_occurred': self.error_details is not None,
            'correlation_id': self.correlation_id
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary"""
        return {
            'duration_seconds': self.performance_metrics.duration_seconds,
            'cpu_usage_percent': self.performance_metrics.cpu_usage_percent,
            'memory_usage_mb': self.performance_metrics.memory_usage_mb,
            'network_requests_count': self.performance_metrics.network_requests_count,
            'dom_changes_count': self.performance_metrics.dom_changes_count,
            'javascript_errors_count': self.performance_metrics.javascript_errors_count,
            'console_warnings_count': self.performance_metrics.console_warnings_count,
            'page_load_time': self.performance_metrics.page_load_time,
            'render_time': self.performance_metrics.render_time
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation"""
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'route_id': self.route_id,
            'context_before': self.context_before,
            'context_after': self.context_after,
            'outcome': self.outcome.value,
            'performance_metrics': self.performance_metrics.to_dict(),
            'error_details': self.error_details,
            'error_code': self.error_code,
            'error_stack_trace': self.error_stack_trace,
            'user_agent': self.user_agent,
            'page_url_before': self.page_url_before,
            'page_url_after': self.page_url_after,
            'session_id': self.session_id,
            'correlation_id': self.correlation_id,
            'detection_triggers': self.detection_triggers,
            'stealth_score_before': self.stealth_score_before,
            'stealth_score_after': self.stealth_score_after,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NavigationEvent':
        """Create event from dictionary representation"""
        event = cls(
            event_id=data['event_id'],
            route_id=data['route_id'],
            context_before=data['context_before'],
            context_after=data['context_after'],
            outcome=NavigationOutcome(data.get('outcome', 'success')),
            performance_metrics=EventPerformanceMetrics.from_dict(data.get('performance_metrics', {})),
            error_details=data.get('error_details'),
            error_code=data.get('error_code'),
            error_stack_trace=data.get('error_stack_trace'),
            user_agent=data.get('user_agent', ''),
            page_url_before=data.get('page_url_before', ''),
            page_url_after=data.get('page_url_after', ''),
            session_id=data.get('session_id', ''),
            correlation_id=data.get('correlation_id', ''),
            detection_triggers=data.get('detection_triggers', []),
            stealth_score_before=data.get('stealth_score_before', 0.0),
            stealth_score_after=data.get('stealth_score_after', 0.0),
            metadata=data.get('metadata', {})
        )
        
        # Set timestamp
        if 'timestamp' in data:
            event.timestamp = datetime.fromisoformat(data['timestamp'])
        
        return event
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'NavigationEvent':
        """Create event from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
