"""
Navigation module logging configuration

Provides structured logging with correlation IDs for navigation operations
following Constitution Principle V - Production Resilience.
"""

import structlog
import uuid
from typing import Dict, Any, Optional
from contextvars import ContextVar

# Context variable for correlation ID
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


def get_correlation_id() -> str:
    """Get or generate correlation ID for current navigation operation"""
    current_id = correlation_id.get()
    if current_id is None:
        current_id = f"nav_{uuid.uuid4().hex[:12]}"  # Navigation-prefixed ID
        correlation_id.set(current_id)
    return current_id


def set_correlation_id(cid: str) -> None:
    """Set correlation ID for current navigation operation"""
    if not cid.startswith('nav_'):
        cid = f"nav_{cid}"
    correlation_id.set(cid)


def generate_correlation_id() -> str:
    """Generate a new correlation ID"""
    return f"nav_{uuid.uuid4().hex[:12]}"


def get_context_correlation_id(context_id: str) -> str:
    """Generate context-specific correlation ID"""
    return f"nav_ctx_{context_id[:8]}_{uuid.uuid4().hex[:8]}"


class NavigationLogger:
    """Structured logger for navigation operations with correlation tracking"""
    
    def __init__(self, component: str):
        self.component = component
        self.logger = structlog.get_logger(component=component)
    
    def _log_with_context(self, level: str, message: str, **kwargs) -> None:
        """Log message with correlation ID and component context"""
        log_data = {
            'correlation_id': get_correlation_id(),
            'component': self.component,
            **kwargs
        }
        
        getattr(self.logger, level)(message, **log_data)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with navigation context"""
        self._log_with_context('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with navigation context"""
        self._log_with_context('warning', message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message with navigation context"""
        self._log_with_context('error', message, **kwargs)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with navigation context"""
        self._log_with_context('debug', message, **kwargs)
    
    def route_discovery_start(self, page_url: str, max_depth: int) -> None:
        """Log route discovery operation start"""
        self.info(
            "route_discovery_started",
            page_url=page_url,
            max_depth=max_depth
        )
    
    def route_discovery_complete(self, routes_found: int, duration_seconds: float) -> None:
        """Log route discovery operation completion"""
        self.info(
            "route_discovery_completed",
            routes_found=routes_found,
            duration_seconds=duration_seconds
        )
    
    def path_planning_start(self, source: str, destination: str) -> None:
        """Log path planning operation start"""
        self.info(
            "path_planning_started",
            source=source,
            destination=destination
        )
    
    def path_planning_complete(self, path_length: int, risk_score: float, duration_ms: float) -> None:
        """Log path planning operation completion"""
        self.info(
            "path_planning_completed",
            path_length=path_length,
            risk_score=risk_score,
            duration_ms=duration_ms
        )
    
    def navigation_execution_start(self, plan_id: str) -> None:
        """Log navigation execution start"""
        self.info(
            "navigation_execution_started",
            plan_id=plan_id
        )
    
    def navigation_execution_complete(self, success: bool, steps_completed: int) -> None:
        """Log navigation execution completion"""
        self.info(
            "navigation_execution_completed",
            success=success,
            steps_completed=steps_completed
        )
    
    def adaptation_triggered(self, obstacle_type: str, original_plan_id: str) -> None:
        """Log route adaptation trigger"""
        self.warning(
            "route_adaptation_triggered",
            obstacle_type=obstacle_type,
            original_plan_id=original_plan_id
        )
    
    def context_created(self, context_id: str, session_id: str) -> None:
        """Log navigation context creation"""
        self.info(
            "navigation_context_created",
            context_id=context_id,
            session_id=session_id
        )
    
    def context_updated(self, context_id: str, event_type: str) -> None:
        """Log navigation context update"""
        self.debug(
            "navigation_context_updated",
            context_id=context_id,
            event_type=event_type
        )


def configure_navigation_logging() -> None:
    """Configure structured logging for navigation module"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_navigation_logger(component: str) -> NavigationLogger:
    """Get navigation logger for specific component"""
    return NavigationLogger(component)
