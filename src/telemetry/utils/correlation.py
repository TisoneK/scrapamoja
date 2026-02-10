"""
Correlation ID Generation Utilities

Utilities for generating and managing correlation IDs for
telemetry event tracking and operation linking.
"""

import uuid
import time
import threading
from typing import Optional, Dict, Any
from datetime import datetime
import hashlib
import base64

from ..exceptions import CorrelationIdError


class CorrelationIdGenerator:
    """
    Generates and manages correlation IDs for telemetry tracking.
    
    Provides thread-safe correlation ID generation with various
    strategies and context management.
    """
    
    def __init__(self, default_length: int = 16):
        """
        Initialize correlation ID generator.
        
        Args:
            default_length: Default length for generated IDs
        """
        self.default_length = default_length
        self._thread_local = threading.local()
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def generate_correlation_id(
        self,
        length: Optional[int] = None,
        prefix: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a new correlation ID.
        
        Args:
            length: Length of generated ID
            prefix: Optional prefix for ID
            context: Optional context for ID generation
            
        Returns:
            Generated correlation ID
            
        Raises:
            CorrelationIdError: If generation fails
        """
        try:
            length = length or self.default_length
            
            # Generate base UUID
            base_id = str(uuid.uuid4()).replace("-", "")
            
            # Take required length
            correlation_id = base_id[:length]
            
            # Add prefix if provided
            if prefix:
                correlation_id = f"{prefix}_{correlation_id}"
            
            # Store context if provided
            if context:
                self._store_context(correlation_id, context)
            
            return correlation_id
            
        except Exception as e:
            raise CorrelationIdError(
                f"Failed to generate correlation ID: {e}",
                operation="generate",
                correlation_id=None
            )
    
    def generate_time_based_correlation_id(
        self,
        prefix: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a time-based correlation ID.
        
        Args:
            prefix: Optional prefix for ID
            context: Optional context for ID generation
            
        Returns:
            Time-based correlation ID
        """
        try:
            # Get current timestamp
            timestamp = int(time.time() * 1000)  # milliseconds
            
            # Generate random component
            random_component = str(uuid.uuid4()).replace("-", "")[:8]
            
            # Combine components
            correlation_id = f"{timestamp}_{random_component}"
            
            # Add prefix if provided
            if prefix:
                correlation_id = f"{prefix}_{correlation_id}"
            
            # Store context if provided
            if context:
                self._store_context(correlation_id, context)
            
            return correlation_id
            
        except Exception as e:
            raise CorrelationIdError(
                f"Failed to generate time-based correlation ID: {e}",
                operation="generate_time_based",
                correlation_id=None
            )
    
    def generate_context_based_correlation_id(
        self,
        context: Dict[str, Any],
        prefix: Optional[str] = None
    ) -> str:
        """
        Generate a deterministic correlation ID based on context.
        
        Args:
            context: Context data for ID generation
            prefix: Optional prefix for ID
            
        Returns:
            Context-based correlation ID
        """
        try:
            # Create deterministic hash from context
            context_str = str(sorted(context.items()))
            hash_obj = hashlib.sha256(context_str.encode())
            hash_bytes = hash_obj.digest()
            
            # Convert to base64 and make URL-safe
            base64_str = base64.urlsafe_b64encode(hash_bytes).decode()
            correlation_id = base64_str[:16].rstrip("=")
            
            # Add prefix if provided
            if prefix:
                correlation_id = f"{prefix}_{correlation_id}"
            
            # Store context
            self._store_context(correlation_id, context)
            
            return correlation_id
            
        except Exception as e:
            raise CorrelationIdError(
                f"Failed to generate context-based correlation ID: {e}",
                operation="generate_context_based",
                correlation_id=None
            )
    
    def set_thread_correlation_id(self, correlation_id: str) -> None:
        """
        Set correlation ID for current thread.
        
        Args:
            correlation_id: Correlation ID to set
        """
        self._thread_local.correlation_id = correlation_id
    
    def get_thread_correlation_id(self) -> Optional[str]:
        """
        Get correlation ID for current thread.
        
        Returns:
            Thread correlation ID or None if not set
        """
        return getattr(self._thread_local, "correlation_id", None)
    
    def clear_thread_correlation_id(self) -> None:
        """Clear correlation ID for current thread."""
        if hasattr(self._thread_local, "correlation_id"):
            delattr(self._thread_local, "correlation_id")
    
    def start_session(
        self,
        session_id: str,
        correlation_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Start a correlation session.
        
        Args:
            session_id: Unique session identifier
            correlation_id: Primary correlation ID for session
            context: Optional session context
        """
        with self._lock:
            self._active_sessions[session_id] = {
                "correlation_id": correlation_id,
                "context": context or {},
                "start_time": datetime.utcnow(),
                "events": []
            }
    
    def end_session(self, session_id: str) -> Dict[str, Any]:
        """
        End a correlation session and get session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data and statistics
        """
        with self._lock:
            if session_id not in self._active_sessions:
                raise CorrelationIdError(
                    f"Session {session_id} not found",
                    operation="end_session",
                    correlation_id=None
                )
            
            session = self._active_sessions.pop(session_id)
            session["end_time"] = datetime.utcnow()
            session["duration_ms"] = (
                session["end_time"] - session["start_time"]
            ).total_seconds() * 1000
            
            return session
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None if not found
        """
        with self._lock:
            return self._active_sessions.get(session_id)
    
    def add_event_to_session(
        self,
        session_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> None:
        """
        Add an event to a session.
        
        Args:
            session_id: Session identifier
            event_type: Type of event
            event_data: Event data
        """
        with self._lock:
            if session_id in self._active_sessions:
                self._active_sessions[session_id]["events"].append({
                    "type": event_type,
                    "data": event_data,
                    "timestamp": datetime.utcnow()
                })
    
    def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active sessions.
        
        Returns:
            Active sessions dictionary
        """
        with self._lock:
            return self._active_sessions.copy()
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """
        Clean up expired sessions.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of sessions cleaned up
        """
        with self._lock:
            cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
            expired_sessions = []
            
            for session_id, session in self._active_sessions.items():
                if session["start_time"].timestamp() < cutoff_time:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self._active_sessions[session_id]
            
            return len(expired_sessions)
    
    def _store_context(self, correlation_id: str, context: Dict[str, Any]) -> None:
        """
        Store context for correlation ID.
        
        Args:
            correlation_id: Correlation ID
            context: Context data
        """
        # This could be extended to store in a database or cache
        # For now, we'll store in memory with the sessions
        session_id = f"ctx_{correlation_id}"
        self.start_session(session_id, correlation_id, context)
    
    def validate_correlation_id(self, correlation_id: str) -> bool:
        """
        Validate correlation ID format.
        
        Args:
            correlation_id: Correlation ID to validate
            
        Returns:
            True if valid format
        """
        if not correlation_id or not isinstance(correlation_id, str):
            return False
        
        # Basic validation - should be alphanumeric with optional underscores
        import re
        pattern = r"^[a-zA-Z0-9_-]+$"
        return bool(re.match(pattern, correlation_id))
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get correlation ID generator statistics.
        
        Returns:
            Statistics dictionary
        """
        with self._lock:
            return {
                "active_sessions": len(self._active_sessions),
                "default_length": self.default_length,
                "has_thread_correlation": self.get_thread_correlation_id() is not None
            }


# Global correlation ID generator instance
_default_generator = CorrelationIdGenerator()


def generate_correlation_id(
    length: Optional[int] = None,
    prefix: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a correlation ID using the default generator.
    
    Args:
        length: Length of generated ID
        prefix: Optional prefix for ID
        context: Optional context for ID generation
        
    Returns:
        Generated correlation ID
    """
    return _default_generator.generate_correlation_id(length, prefix, context)


def generate_time_based_correlation_id(
    prefix: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a time-based correlation ID using the default generator.
    
    Args:
        prefix: Optional prefix for ID
        context: Optional context for ID generation
        
    Returns:
        Time-based correlation ID
    """
    return _default_generator.generate_time_based_correlation_id(prefix, context)


def generate_context_based_correlation_id(
    context: Dict[str, Any],
    prefix: Optional[str] = None
) -> str:
    """
    Generate a context-based correlation ID using the default generator.
    
    Args:
        context: Context data for ID generation
        prefix: Optional prefix for ID
        
    Returns:
        Context-based correlation ID
    """
    return _default_generator.generate_context_based_correlation_id(context, prefix)


def set_thread_correlation_id(correlation_id: str) -> None:
    """
    Set correlation ID for current thread using default generator.
    
    Args:
        correlation_id: Correlation ID to set
    """
    _default_generator.set_thread_correlation_id(correlation_id)


def get_thread_correlation_id() -> Optional[str]:
    """
    Get correlation ID for current thread using default generator.
    
    Returns:
        Thread correlation ID or None if not set
    """
    return _default_generator.get_thread_correlation_id()


def clear_thread_correlation_id() -> None:
    """Clear correlation ID for current thread using default generator."""
    _default_generator.clear_thread_correlation_id()


def validate_correlation_id(correlation_id: str) -> bool:
    """
    Validate correlation ID format using default generator.
    
    Args:
        correlation_id: Correlation ID to validate
        
    Returns:
        True if valid format
    """
    return _default_generator.validate_correlation_id(correlation_id)
