"""
Browser manager for centralized session management.

This module provides the BrowserManager class for managing multiple browser
sessions with concurrent access, resource monitoring, and state persistence.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import asyncio
import json
from typing import Callable

from .session import BrowserSession, SessionStatus
from .config import BrowserConfiguration, BrowserType
from .monitoring import ResourceMetrics, get_resource_monitor
from .resilience import resilience_manager
from src.observability.logger import get_logger
from src.observability.events import (
    publish_browser_cleanup_started,
    publish_browser_cleanup_completed
)
from src.observability.metrics import get_browser_metrics_collector
from src.storage.adapter import get_storage_adapter
from src.utils.exceptions import BrowserManagerError


@dataclass
class SessionStatistics:
    """Statistics for browser session management."""
    total_sessions: int = 0
    active_sessions: int = 0
    failed_sessions: int = 0
    terminated_sessions: int = 0
    total_memory_mb: float = 0.0
    average_cpu_percent: float = 0.0
    oldest_session_age_minutes: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)


class BrowserManager:
    """Centralized browser session management with concurrent access."""
    
    def __init__(self):
        self._logger = get_logger("browser_manager")
        self._storage = get_storage_adapter()
        self._sessions: Dict[str, BrowserSession] = {}
        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._manager_lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval = 60  # 1 minute
        self._max_concurrent_sessions = 50
    
    async def initialize(self) -> None:
        """Initialize the browser manager."""
        self._logger.info("initializing_browser_manager")
        
        # Load existing sessions from storage
        await self._load_persisted_sessions()
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self._logger.info(
            "browser_manager_initialized",
            loaded_sessions=len(self._sessions)
        )
    
    async def create_session(
        self, 
        configuration: Optional[BrowserConfiguration] = None,
        session_id: Optional[str] = None
    ) -> BrowserSession:
        """Create a new browser session."""
        async with self._manager_lock:
            # Check concurrent session limit
            active_count = len([
                s for s in self._sessions.values() 
                if s.status == SessionStatus.ACTIVE
            ])
            
            if active_count >= self._max_concurrent_sessions:
                raise BrowserManagerError(
                    "session_limit_exceeded",
                    f"Maximum concurrent sessions ({self._max_concurrent_sessions}) exceeded"
                )
            
            # Create session
            session = BrowserSession(
                session_id=session_id,
                configuration=configuration or BrowserConfiguration()
            )
            
            # Add to manager
            self._sessions[session.session_id] = session
            self._session_locks[session.session_id] = asyncio.Lock()
            
            try:
                # Initialize session with resilience
                await resilience_manager.execute_with_resilience(
                    "session_initialization",
                    session.initialize,
                    retry_config="default",
                    circuit_breaker="default",
                    context={"session_id": session.session_id}
                )
                
                self._logger.info(
                    "browser_session_created",
                    session_id=session.session_id,
                    browser_type=session.configuration.browser_type.value
                )
                
                return session
                
            except Exception as e:
                # Cleanup failed session
                self._sessions.pop(session.session_id, None)
                self._session_locks.pop(session.session_id, None)
                
                self._logger.error(
                    "session_creation_failed",
                    session_id=session.session_id,
                    error=str(e)
                )
                
                raise BrowserManagerError(
                    "session_creation_failed",
                    f"Failed to create browser session: {str(e)}",
                    {"session_id": session.session_id, "error": str(e)}
                )
    
    async def get_session(self, session_id: str) -> Optional[BrowserSession]:
        """Get a browser session by ID."""
        return self._sessions.get(session_id)
    
    async def list_sessions(
        self, 
        status_filter: Optional[SessionStatus] = None
    ) -> List[BrowserSession]:
        """List all sessions, optionally filtered by status."""
        sessions = list(self._sessions.values())
        
        if status_filter:
            sessions = [s for s in sessions if s.status == status_filter]
        
        return sessions
    
    async def get_active_sessions(self) -> List[BrowserSession]:
        """Get all active sessions."""
        return await self.list_sessions(SessionStatus.ACTIVE)
    
    async def close_session(self, session_id: str) -> None:
        """Close a specific browser session."""
        session = self._sessions.get(session_id)
        if not session:
            raise BrowserManagerError(
                "session_not_found",
                f"Session not found: {session_id}"
            )
        
        session_lock = self._session_locks.get(session_id)
        if not session_lock:
            raise BrowserManagerError(
                "session_lock_not_found",
                f"Session lock not found: {session_id}"
            )
        
        async with session_lock:
            try:
                # Close session with resilience
                await resilience_manager.execute_with_resilience(
                    "session_termination",
                    session.close,
                    retry_config="default",
                    context={"session_id": session_id}
                )
                
                # Remove from manager
                self._sessions.pop(session_id, None)
                self._session_locks.pop(session_id, None)
                
                self._logger.info(
                    "browser_session_closed",
                    session_id=session_id
                )
                
            except Exception as e:
                self._logger.error(
                    "session_close_failed",
                    session_id=session_id,
                    error=str(e)
                )
                raise BrowserManagerError(
                    "session_close_failed",
                    f"Failed to close session: {str(e)}",
                    {"session_id": session_id, "error": str(e)}
                )
    
    async def close_all_sessions(self) -> None:
        """Close all browser sessions."""
        self._logger.info(
            "closing_all_sessions",
            session_count=len(self._sessions)
        )
        
        session_ids = list(self._sessions.keys())
        
        # Close sessions concurrently
        close_tasks = [
            self.close_session(session_id) 
            for session_id in session_ids
        ]
        
        results = await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # Log any errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self._logger.error(
                    "concurrent_session_close_error",
                    session_id=session_ids[i],
                    error=str(result)
                )
        
        self._logger.info("all_sessions_closed")
    
    async def get_statistics(self) -> SessionStatistics:
        """Get session management statistics."""
        sessions = list(self._sessions.values())
        
        stats = SessionStatistics(
            total_sessions=len(sessions),
            active_sessions=len([s for s in sessions if s.status == SessionStatus.ACTIVE]),
            failed_sessions=len([s for s in sessions if s.status == SessionStatus.FAILED]),
            terminated_sessions=len([s for s in sessions if s.status == SessionStatus.TERMINATED])
        )
        
        # Calculate resource metrics
        total_memory = 0.0
        total_cpu = 0.0
        active_metrics_count = 0
        
        for session in sessions:
            if session.resource_metrics:
                total_memory += session.resource_metrics.memory_usage_mb
                total_cpu += session.resource_metrics.cpu_percent
                active_metrics_count += 1
        
        if active_metrics_count > 0:
            stats.total_memory_mb = total_memory
            stats.average_cpu_percent = total_cpu / active_metrics_count
        
        # Calculate oldest session age
        if sessions:
            now = datetime.utcnow()
            oldest_age = min(
                (now - session.created_at).total_seconds() / 60
                for session in sessions
            )
            stats.oldest_session_age_minutes = oldest_age
        
        return stats
    
    async def cleanup_inactive_sessions(self) -> int:
        """Clean up inactive or failed sessions."""
        cleaned_count = 0
        now = datetime.utcnow()
        
        sessions_to_clean = []
        
        for session in self._sessions.values():
            # Clean up failed sessions
            if session.status == SessionStatus.FAILED:
                sessions_to_clean.append(session.session_id)
                continue
            
            # Clean up inactive sessions (older than 30 minutes)
            if (session.status == SessionStatus.ACTIVE and 
                (now - session.last_activity).total_seconds() > 1800):  # 30 minutes
                sessions_to_clean.append(session.session_id)
                continue
        
        # Publish cleanup started event
        if sessions_to_clean:
            await publish_browser_cleanup_started(len(sessions_to_clean))
        
        # Clean up sessions
        for session_id in sessions_to_clean:
            try:
                await self.close_session(session_id)
                cleaned_count += 1
            except Exception as e:
                self._logger.error(
                    "cleanup_session_error",
                    session_id=session_id,
                    error=str(e)
                )
        
        if cleaned_count > 0:
            # Publish cleanup completed event
            await publish_browser_cleanup_completed(cleaned_count)
            
            self._logger.info(
                "inactive_sessions_cleaned",
                cleaned_count=cleaned_count
            )
        
        return cleaned_count
    
    async def _load_persisted_sessions(self) -> None:
        """Load persisted sessions from storage."""
        try:
            session_files = await self._storage.list_files("browser_sessions/")
            
            for file_path in session_files:
                if not file_path.endswith('.json'):
                    continue
                
                try:
                    session_data = await self._storage.load(file_path)
                    session = BrowserSession.from_dict(session_data)
                    
                    # Only add non-terminated sessions
                    if session.status != SessionStatus.TERMINATED:
                        self._sessions[session.session_id] = session
                        self._session_locks[session.session_id] = asyncio.Lock()
                        
                        self._logger.info(
                            "persisted_session_loaded",
                            session_id=session.session_id,
                            status=session.status.value
                        )
                
                except Exception as e:
                    self._logger.error(
                        "persisted_session_load_error",
                        file_path=file_path,
                        error=str(e)
                    )
        
        except Exception as e:
            self._logger.warning(
                "persisted_sessions_load_error",
                error=str(e)
            )
    
    async def _cleanup_loop(self) -> None:
        """Main cleanup loop."""
        self._logger.info("cleanup_loop_started")
        
        try:
            while True:
                await asyncio.sleep(self._cleanup_interval)
                
                try:
                    await self.cleanup_inactive_sessions()
                except Exception as e:
                    self._logger.error(
                        "cleanup_loop_error",
                        error=str(e)
                    )
        
        except asyncio.CancelledError:
            self._logger.info("cleanup_loop_cancelled")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the browser manager."""
        self._logger.info("shutting_down_browser_manager")
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all sessions
        await self.close_all_sessions()
        
        # Cleanup resource monitoring
        await get_resource_monitor().cleanup_all()
        
        self._logger.info("browser_manager_shutdown_complete")


# Global browser manager instance
_browser_manager: Optional[BrowserManager] = None
_manager_lock = asyncio.Lock()


async def get_browser_manager() -> BrowserManager:
    """Get the global browser manager instance."""
    global _browser_manager
    
    if _browser_manager is None:
        async with _manager_lock:
            if _browser_manager is None:
                _browser_manager = BrowserManager()
                await _browser_manager.initialize()
    
    return _browser_manager
