"""
Correlation ID Tracking

Provides correlation ID generation and management for tracing resilience
operations across multiple components and operations.
"""

import uuid
from typing import Optional, Dict, Any
from contextvars import ContextVar
import threading


# Context variable for correlation ID
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationManager:
    """Manages correlation IDs for tracing operations across components."""
    
    def __init__(self):
        self._local_storage = threading.local()
    
    def generate_correlation_id(self) -> str:
        """Generate a new correlation ID."""
        return str(uuid.uuid4())
    
    def set_correlation_id(self, correlation_id: str) -> None:
        """Set the current correlation ID in context."""
        _correlation_id.set(correlation_id)
    
    def get_correlation_id(self) -> Optional[str]:
        """Get the current correlation ID from context."""
        return _correlation_id.get()
    
    def clear_correlation_id(self) -> None:
        """Clear the current correlation ID from context."""
        _correlation_id.set(None)
    
    def with_correlation_id(self, correlation_id: str):
        """Context manager to temporarily set correlation ID."""
        return CorrelationContext(correlation_id)
    
    def get_or_generate(self) -> str:
        """Get existing correlation ID or generate a new one."""
        correlation_id = self.get_correlation_id()
        if correlation_id is None:
            correlation_id = self.generate_correlation_id()
            self.set_correlation_id(correlation_id)
        return correlation_id


class CorrelationContext:
    """Context manager for correlation ID management."""
    
    def __init__(self, correlation_id: str):
        self.correlation_id = correlation_id
        self.previous_id = None
    
    def __enter__(self):
        self.previous_id = _correlation_id.get()
        _correlation_id.set(self.correlation_id)
        return self.correlation_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.previous_id is not None:
            _correlation_id.set(self.previous_id)
        else:
            _correlation_id.set(None)


# Global correlation manager instance
_correlation_manager = CorrelationManager()


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return _correlation_manager.generate_correlation_id()


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID."""
    return _correlation_manager.get_correlation_id()


def set_correlation_id(correlation_id: str) -> None:
    """Set the current correlation ID."""
    _correlation_manager.set_correlation_id(correlation_id)


def clear_correlation_id() -> None:
    """Clear the current correlation ID."""
    _correlation_manager.clear_correlation_id()


def get_or_generate_correlation_id() -> str:
    """Get existing correlation ID or generate a new one."""
    return _correlation_manager.get_or_generate()


def with_correlation_id(correlation_id: str):
    """Context manager to temporarily set correlation ID."""
    return _correlation_manager.with_correlation_id(correlation_id)


class CorrelationContextMixin:
    """Mixin class for adding correlation context to objects."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._correlation_id: Optional[str] = None
    
    def set_correlation_context(self, correlation_id: str) -> None:
        """Set correlation context for this object."""
        self._correlation_id = correlation_id
    
    def get_correlation_context(self) -> Optional[str]:
        """Get correlation context for this object."""
        return self._correlation_id or get_correlation_id()
    
    def with_correlation_context(self, correlation_id: str):
        """Context manager to temporarily set correlation context for this object."""
        return ObjectCorrelationContext(self, correlation_id)


class ObjectCorrelationContext:
    """Context manager for object-specific correlation context."""
    
    def __init__(self, obj: CorrelationContextMixin, correlation_id: str):
        self.obj = obj
        self.correlation_id = correlation_id
        self.previous_id = None
    
    def __enter__(self):
        self.previous_id = self.obj._correlation_id
        self.obj._correlation_id = self.correlation_id
        return self.correlation_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.obj._correlation_id = self.previous_id


def add_correlation_to_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Add correlation ID to a context dictionary."""
    correlation_id = get_correlation_id()
    if correlation_id:
        context["correlation_id"] = correlation_id
    return context


def extract_correlation_from_context(context: Dict[str, Any]) -> Optional[str]:
    """Extract correlation ID from a context dictionary."""
    return context.get("correlation_id")
