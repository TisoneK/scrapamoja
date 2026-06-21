"""
Context Data Collector

Specialized collector for context data with environment tracking,
session management, and execution context analysis.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
import json

from ..models import ContextData, ViewportSize
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryCollectionError
from ..configuration.logging import get_logger


@dataclass
class ContextStats:
    """Statistics for context data."""
    total_contexts: int = 0
    unique_browsers: int = 0
    unique_tabs: int = 0
    unique_pages: int = 0
    average_viewport_width: float = 0.0
    average_viewport_height: float = 0.0
    most_common_user_agent: str = ""
    most_common_page_domain: str = ""
    session_duration_stats: Dict[str, float] = None
    last_context: Optional[datetime] = None
    
    def __post_init__(self):
        if self.session_duration_stats is None:
            self.session_duration_stats = {}


@dataclass
class SessionInfo:
    """Information about a browser session."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_operations: int = 0
    pages_visited: int = 0
    selectors_used: List[str] = None
    user_agent: str = ""
    viewport_changes: int = 0
    
    def __post_init__(self):
        if self.selectors_used is None:
            self.selectors_used = []


class ContextCollector:
    """
    Specialized collector for context data with environment tracking.
    
    Provides comprehensive context collection, session management,
    and execution context analysis for selector operations.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize context collector.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("context_collector")
        
        # Context configuration
        self.max_samples = config.get("max_context_samples", 10000)
        self.session_timeout = timedelta(minutes=config.get("session_timeout_minutes", 30))
        
        # Context storage
        self._context_samples: List[Dict[str, Any]] = []
        self._active_sessions: Dict[str, SessionInfo] = {}
        self._context_stats: ContextStats = ContextStats()
        self._stats_lock = asyncio.Lock()
        
        # Context tracking
        self._session_contexts: Dict[str, Dict[str, Any]] = {}
        self._page_contexts: Dict[str, Dict[str, Any]] = {}
        
        # Collection state
        self._enabled = True
        self._collection_count = 0
        self._error_count = 0
    
    async def collect_context_data(
        self,
        selector_name: str,
        operation_type: str,
        browser_session_id: str,
        tab_context_id: str,
        page_url: Optional[str] = None,
        page_title: Optional[str] = None,
        user_agent: Optional[str] = None,
        viewport_size: Optional[ViewportSize] = None,
        timestamp_context: Optional[Dict[str, Any]] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> ContextData:
        """
        Collect context data for an operation.
        
        Args:
            selector_name: Name of selector
            operation_type: Type of operation
            browser_session_id: Browser session identifier
            tab_context_id: Tab context identifier
            page_url: Current page URL
            page_title: Current page title
            user_agent: Browser user agent
            viewport_size: Viewport size information
            timestamp_context: Timestamp context information
            additional_context: Additional context data
            
        Returns:
            ContextData instance
            
        Raises:
            TelemetryCollectionError: If collection fails
        """
        try:
            if not self._enabled:
                raise TelemetryCollectionError(
                    "Context collector is disabled",
                    error_code="TEL-701"
                )
            
            # Create context data
            context_data = ContextData(
                browser_session_id=browser_session_id,
                tab_context_id=tab_context_id,
                page_url=page_url,
                page_title=page_title,
                user_agent=user_agent,
                viewport_size=viewport_size,
                timestamp_context=timestamp_context
            )
            
            # Store context sample
            await self._store_context_sample(
                selector_name,
                operation_type,
                context_data,
                additional_context
            )
            
            # Update session tracking
            await self._update_session_tracking(
                browser_session_id,
                tab_context_id,
                page_url,
                user_agent,
                selector_name
            )
            
            # Update statistics
            await self._update_statistics(context_data)
            
            self._collection_count += 1
            
            self.logger.debug(
                "Context data collected",
                selector_name=selector_name,
                browser_session_id=browser_session_id,
                tab_context_id=tab_context_id,
                page_url=page_url
            )
            
            return context_data
            
        except Exception as e:
            self._error_count += 1
            self.logger.error(
                "Failed to collect context data",
                selector_name=selector_name,
                browser_session_id=browser_session_id,
                error=str(e)
            )
            raise TelemetryCollectionError(
                f"Failed to collect context data: {e}",
                error_code="TEL-702"
            )
    
    async def start_session(
        self,
        browser_session_id: str,
        user_agent: Optional[str] = None,
        initial_viewport: Optional[ViewportSize] = None,
        session_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Start tracking a new browser session.
        
        Args:
            browser_session_id: Browser session identifier
            user_agent: Browser user agent
            initial_viewport: Initial viewport size
            session_context: Additional session context
        """
        try:
            async with self._stats_lock:
                if browser_session_id in self._active_sessions:
                    self.logger.warning(
                        "Session already exists",
                        browser_session_id=browser_session_id
                    )
                    return
                
                session_info = SessionInfo(
                    session_id=browser_session_id,
                    start_time=datetime.utcnow(),
                    user_agent=user_agent or "",
                    viewport_size=initial_viewport
                )
                
                self._active_sessions[browser_session_id] = session_info
                self._session_contexts[browser_session_id] = session_context or {}
            
            self.logger.info(
                "Session started",
                browser_session_id=browser_session_id,
                user_agent=user_agent
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to start session",
                browser_session_id=browser_session_id,
                error=str(e)
            )
    
    async def end_session(
        self,
        browser_session_id: str,
        end_context: Optional[Dict[str, Any]] = None
    ) -> Optional[SessionInfo]:
        """
        End tracking for a browser session.
        
        Args:
            browser_session_id: Browser session identifier
            end_context: Additional end context
            
        Returns:
            Session information if found
        """
        try:
            async with self._stats_lock:
                if browser_session_id not in self._active_sessions:
                    self.logger.warning(
                        "Session not found",
                        browser_session_id=browser_session_id
                    )
                    return None
                
                session_info = self._active_sessions.pop(browser_session_id)
                session_info.end_time = datetime.utcnow()
                
                # Update session context
                if end_context:
                    self._session_contexts[browser_session_id].update(end_context)
            
            self.logger.info(
                "Session ended",
                browser_session_id=browser_session_id,
                duration_ms=(
                    (session_info.end_time - session_info.start_time).total_seconds() * 1000
                    if session_info.end_time else 0
                ),
                total_operations=session_info.total_operations
            )
            
            return session_info
            
        except Exception as e:
            self.logger.error(
                "Failed to end session",
                browser_session_id=browser_session_id,
                error=str(e)
            )
            return None
    
    async def get_session_analysis(
        self,
        browser_session_id: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Analyze session data and patterns.
        
        Args:
            browser_session_id: Optional specific session to analyze
            time_window: Optional time window for analysis
            
        Returns:
            Session analysis results
        """
        try:
            # Get relevant samples
            samples = await self._get_filtered_samples(None, time_window)
            
            if not samples:
                return {}
            
            # Filter by session if specified
            if browser_session_id:
                samples = [
                    sample for sample in samples
                    if sample["context_data"].get("browser_session_id") == browser_session_id
                ]
            
            if not samples:
                return {}
            
            # Analyze session patterns
            session_analysis = {
                "total_sessions": len(set(
                    sample["context_data"].get("browser_session_id")
                    for sample in samples
                    if sample["context_data"].get("browser_session_id")
                )),
                "session_duration_stats": {},
                "pages_per_session": {},
                "selectors_per_session": {},
                "viewport_changes": {},
                "user_agent_distribution": {}
            }
            
            # Group by session
            session_groups = defaultdict(list)
            for sample in samples:
                session_id = sample["context_data"].get("browser_session_id")
                if session_id:
                    session_groups[session_id].append(sample)
            
            # Analyze each session
            session_durations = []
            pages_per_session = []
            selectors_per_session = []
            viewport_changes = []
            user_agents = []
            
            for session_id, session_samples in session_groups.items():
                # Calculate session duration
                timestamps = [sample["timestamp"] for sample in session_samples]
                if len(timestamps) > 1:
                    duration = (max(timestamps) - min(timestamps)).total_seconds()
                    session_durations.append(duration)
                
                # Count unique pages
                pages = set(
                    sample["context_data"].get("page_url")
                    for sample in session_samples
                    if sample["context_data"].get("page_url")
                )
                pages_per_session.append(len(pages))
                
                # Count unique selectors
                selectors = set(sample["selector_name"] for sample in session_samples)
                selectors_per_session.append(len(selectors))
                
                # Count viewport changes
                viewports = [
                    sample["context_data"].get("viewport_size")
                    for sample in session_samples
                    if sample["context_data"].get("viewport_size")
                ]
                if len(viewports) > 1:
                    viewport_changes.append(len(set(viewports)) - 1)
                else:
                    viewport_changes.append(0)
                
                # Collect user agents
                user_agent = session_samples[0]["context_data"].get("user_agent")
                if user_agent:
                    user_agents.append(user_agent)
            
            # Calculate statistics
            if session_durations:
                session_analysis["session_duration_stats"] = {
                    "average_seconds": sum(session_durations) / len(session_durations),
                    "min_seconds": min(session_durations),
                    "max_seconds": max(session_durations),
                    "total_sessions": len(session_durations)
                }
            
            if pages_per_session:
                session_analysis["pages_per_session"] = {
                    "average": sum(pages_per_session) / len(pages_per_session),
                    "min": min(pages_per_session),
                    "max": max(pages_per_session)
                }
            
            if selectors_per_session:
                session_analysis["selectors_per_session"] = {
                    "average": sum(selectors_per_session) / len(selectors_per_session),
                    "min": min(selectors_per_session),
                    "max": max(selectors_per_session)
                }
            
            if viewport_changes:
                session_analysis["viewport_changes"] = {
                    "average_changes": sum(viewport_changes) / len(viewport_changes),
                    "sessions_with_changes": sum(1 for changes in viewport_changes if changes > 0),
                    "max_changes": max(viewport_changes)
                }
            
            # User agent distribution
            if user_agents:
                from collections import Counter
                user_agent_counts = Counter(user_agents)
                session_analysis["user_agent_distribution"] = dict(user_agent_counts)
                session_analysis["most_common_user_agent"] = user_agent_counts.most_common(1)[0][0]
            
            return session_analysis
            
        except Exception as e:
            self.logger.error(
                "Failed to get session analysis",
                browser_session_id=browser_session_id,
                error=str(e)
            )
            return {}
    
    async def get_page_analysis(
        self,
        page_url: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Analyze page context and patterns.
        
        Args:
            page_url: Optional specific page to analyze
            time_window: Optional time window for analysis
            
        Returns:
            Page analysis results
        """
        try:
            # Get relevant samples
            samples = await self._get_filtered_samples(None, time_window)
            
            if not samples:
                return {}
            
            # Filter by page if specified
            if page_url:
                samples = [
                    sample for sample in samples
                    if sample["context_data"].get("page_url") == page_url
                ]
            
            if not samples:
                return {}
            
            # Analyze page patterns
            page_analysis = {
                "total_pages": len(set(
                    sample["context_data"].get("page_url")
                    for sample in samples
                    if sample["context_data"].get("page_url")
                )),
                "page_statistics": {},
                "domain_distribution": {},
                "viewport_distribution": {},
                "selector_usage_by_page": {}
            }
            
            # Extract page information
            page_urls = [
                sample["context_data"].get("page_url")
                for sample in samples
                if sample["context_data"].get("page_url")
            ]
            
            page_titles = [
                sample["context_data"].get("page_title")
                for sample in samples
                if sample["context_data"].get("page_title")
            ]
            
            viewports = [
                sample["context_data"].get("viewport_size")
                for sample in samples
                if sample["context_data"].get("viewport_size")
            ]
            
            # Group by page
            page_groups = defaultdict(list)
            for sample in samples:
                page_url = sample["context_data"].get("page_url")
                if page_url:
                    page_groups[page_url].append(sample)
            
            # Analyze each page
            operation_counts = []
            selector_counts = []
            
            for page_url, page_samples in page_groups.items():
                operation_counts.append(len(page_samples))
                selectors = set(sample["selector_name"] for sample in page_samples)
                selector_counts.append(len(selectors))
            
            # Calculate statistics
            if operation_counts:
                page_analysis["page_statistics"] = {
                    "average_operations_per_page": sum(operation_counts) / len(operation_counts),
                    "min_operations": min(operation_counts),
                    "max_operations": max(operation_counts),
                    "total_pages_analyzed": len(page_groups)
                }
            
            if selector_counts:
                page_analysis["page_statistics"]["average_selectors_per_page"] = (
                    sum(selector_counts) / len(selector_counts)
                )
            
            # Domain distribution
            domains = []
            for page_url in page_urls:
                try:
                    domain = page_url.split("//")[1].split("/")[0] if "//" in page_url else page_url.split("/")[0]
                    domains.append(domain)
                except:
                    continue
            
            if domains:
                from collections import Counter
                domain_counts = Counter(domains)
                page_analysis["domain_distribution"] = dict(domain_counts)
                page_analysis["most_common_domain"] = domain_counts.most_common(1)[0][0]
            
            # Viewport distribution
            if viewports:
                viewport_sizes = [(vp.width, vp.height) for vp in viewports if vp.width and vp.height]
                if viewport_sizes:
                    from collections import Counter
                    viewport_counts = Counter(viewport_sizes)
                    page_analysis["viewport_distribution"] = {
                        f"{w}x{h}": count for (w, h), count in viewport_counts.items()
                    }
                    
                    # Calculate average viewport
                    avg_width = sum(vp[0] for vp in viewport_sizes) / len(viewport_sizes)
                    avg_height = sum(vp[1] for vp in viewport_sizes) / len(viewport_sizes)
                    page_analysis["average_viewport"] = {
                        "width": avg_width,
                        "height": avg_height
                    }
            
            return page_analysis
            
        except Exception as e:
            self.logger.error(
                "Failed to get page analysis",
                page_url=page_url,
                error=str(e)
            )
            return {}
    
    async def get_context_statistics(
        self,
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive context statistics.
        
        Args:
            selector_name: Optional selector filter
            time_window: Optional time window for statistics
            
        Returns:
            Context statistics
        """
        try:
            # Get relevant samples
            samples = await self._get_filtered_samples(selector_name, time_window)
            
            if not samples:
                return {}
            
            # Extract context information
            browser_sessions = [
                sample["context_data"].get("browser_session_id")
                for sample in samples
                if sample["context_data"].get("browser_session_id")
            ]
            
            tab_contexts = [
                sample["context_data"].get("tab_context_id")
                for sample in samples
                if sample["context_data"].get("tab_context_id")
            ]
            
            page_urls = [
                sample["context_data"].get("page_url")
                for sample in samples
                if sample["context_data"].get("page_url")
            ]
            
            viewports = [
                sample["context_data"].get("viewport_size")
                for sample in samples
                if sample["context_data"].get("viewport_size")
            ]
            
            user_agents = [
                sample["context_data"].get("user_agent")
                for sample in samples
                if sample["context_data"].get("user_agent")
            ]
            
            # Calculate statistics
            stats = {
                "total_contexts": len(samples),
                "unique_browser_sessions": len(set(browser_sessions)),
                "unique_tab_contexts": len(set(tab_contexts)),
                "unique_pages": len(set(page_urls)),
                "unique_user_agents": len(set(user_agents))
            }
            
            # Viewport statistics
            if viewports:
                widths = [vp.width for vp in viewports if vp.width]
                heights = [vp.height for vp in viewports if vp.height]
                
                if widths:
                    stats["viewport_statistics"] = {
                        "average_width": sum(widths) / len(widths),
                        "min_width": min(widths),
                        "max_width": max(widths)
                    }
                
                if heights:
                    if "viewport_statistics" not in stats:
                        stats["viewport_statistics"] = {}
                    stats["viewport_statistics"].update({
                        "average_height": sum(heights) / len(heights),
                        "min_height": min(heights),
                        "max_height": max(heights)
                    })
            
            # User agent distribution
            if user_agents:
                from collections import Counter
                user_agent_counts = Counter(user_agents)
                stats["user_agent_distribution"] = dict(user_agent_counts)
                stats["most_common_user_agent"] = user_agent_counts.most_common(1)[0][0]
            
            # Page domain distribution
            if page_urls:
                domains = []
                for page_url in page_urls:
                    try:
                        domain = page_url.split("//")[1].split("/")[0] if "//" in page_url else page_url.split("/")[0]
                        domains.append(domain)
                    except:
                        continue
                
                if domains:
                    from collections import Counter
                    domain_counts = Counter(domains)
                    stats["domain_distribution"] = dict(domain_counts)
                    stats["most_common_domain"] = domain_counts.most_common(1)[0][0]
            
            return stats
            
        except Exception as e:
            self.logger.error(
                "Failed to get context statistics",
                selector_name=selector_name,
                error=str(e)
            )
            return {}
    
    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Get list of active sessions.
        
        Returns:
            List of active session information
        """
        try:
            async with self._stats_lock:
                active_sessions = []
                
                for session_id, session_info in self._active_sessions.items():
                    session_dict = {
                        "session_id": session_id,
                        "start_time": session_info.start_time,
                        "total_operations": session_info.total_operations,
                        "pages_visited": session_info.pages_visited,
                        "selectors_used": len(session_info.selectors_used),
                        "user_agent": session_info.user_agent,
                        "duration_minutes": (
                            (datetime.utcnow() - session_info.start_time).total_seconds() / 60
                        )
                    }
                    active_sessions.append(session_dict)
                
                return active_sessions
                
        except Exception as e:
            self.logger.error(
                "Failed to get active sessions",
                error=str(e)
            )
            return []
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            current_time = datetime.utcnow()
            expired_sessions = []
            
            async with self._stats_lock:
                for session_id, session_info in self._active_sessions.items():
                    session_age = current_time - session_info.start_time
                    if session_age > self.session_timeout:
                        expired_sessions.append(session_id)
                
                # Remove expired sessions
                for session_id in expired_sessions:
                    session_info = self._active_sessions.pop(session_id)
                    session_info.end_time = current_time
                    
                    # Move to completed sessions tracking if needed
                    # This could be extended to store completed sessions
                
            if expired_sessions:
                self.logger.info(
                    "Expired sessions cleaned up",
                    count=len(expired_sessions),
                    session_ids=expired_sessions
                )
            
            return len(expired_sessions)
            
        except Exception as e:
            self.logger.error(
                "Failed to cleanup expired sessions",
                error=str(e)
            )
            return 0
    
    async def get_collection_statistics(self) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Collection statistics
        """
        async with self._stats_lock:
            return {
                "total_collections": self._collection_count,
                "error_count": self._error_count,
                "error_rate": self._error_count / max(1, self._collection_count),
                "samples_stored": len(self._context_samples),
                "active_sessions": len(self._active_sessions),
                "unique_browsers": len(set(
                    sample["context_data"].get("browser_session_id")
                    for sample in self._context_samples
                    if sample["context_data"].get("browser_session_id")
                )),
                "unique_pages": len(set(
                    sample["context_data"].get("page_url")
                    for sample in self._context_samples
                    if sample["context_data"].get("page_url")
                )),
                "enabled": self._enabled,
                "max_samples": self.max_samples
            }
    
    async def enable_collection(self) -> None:
        """Enable context collection."""
        self._enabled = True
        self.logger.info("Context collection enabled")
    
    async def disable_collection(self) -> None:
        """Disable context collection."""
        self._enabled = False
        self.logger.info("Context collection disabled")
    
    async def clear_samples(self, selector_name: Optional[str] = None) -> int:
        """
        Clear context samples.
        
        Args:
            selector_name: Optional selector filter
            
        Returns:
            Number of samples cleared
        """
        async with self._stats_lock:
            if selector_name:
                original_count = len(self._context_samples)
                self._context_samples = [
                    sample for sample in self._context_samples
                    if sample["selector_name"] != selector_name
                ]
                cleared_count = original_count - len(self._context_samples)
            else:
                cleared_count = len(self._context_samples)
                self._context_samples.clear()
                self._context_stats = ContextStats()
            
            self.logger.info(
                "Context samples cleared",
                selector_name=selector_name or "all",
                cleared_count=cleared_count
            )
            
            return cleared_count
    
    # Private methods
    
    async def _store_context_sample(
        self,
        selector_name: str,
        operation_type: str,
        context_data: ContextData,
        additional_context: Optional[Dict[str, Any]]
    ) -> None:
        """Store context sample."""
        sample = {
            "selector_name": selector_name,
            "operation_type": operation_type,
            "context_data": context_data.to_dict(),
            "additional_context": additional_context or {},
            "timestamp": datetime.utcnow()
        }
        
        async with self._stats_lock:
            self._context_samples.append(sample)
            
            # Limit sample size
            if len(self._context_samples) > self.max_samples:
                self._context_samples = self._context_samples[-self.max_samples:]
    
    async def _update_session_tracking(
        self,
        browser_session_id: str,
        tab_context_id: str,
        page_url: Optional[str],
        user_agent: Optional[str],
        selector_name: str
    ) -> None:
        """Update session tracking information."""
        async with self._stats_lock:
            # Update or create session info
            if browser_session_id not in self._active_sessions:
                self._active_sessions[browser_session_id] = SessionInfo(
                    session_id=browser_session_id,
                    start_time=datetime.utcnow(),
                    user_agent=user_agent or ""
                )
            
            session_info = self._active_sessions[browser_session_id]
            session_info.total_operations += 1
            
            # Track selectors used
            if selector_name not in session_info.selectors_used:
                session_info.selectors_used.append(selector_name)
            
            # Track pages visited
            if page_url and page_url not in self._session_contexts.get(browser_session_id, {}).get("visited_pages", set()):
                if "visited_pages" not in self._session_contexts[browser_session_id]:
                    self._session_contexts[browser_session_id]["visited_pages"] = set()
                self._session_contexts[browser_session_id]["visited_pages"].add(page_url)
                session_info.pages_visited += 1
    
    async def _update_statistics(self, context_data: ContextData) -> None:
        """Update context statistics."""
        async with self._stats_lock:
            self._context_stats.total_contexts += 1
            self._context_stats.last_context = datetime.utcnow()
            
            # Update viewport statistics
            if context_data.viewport_size:
                # This would need more sophisticated tracking for averages
                pass
    
    async def _get_filtered_samples(
        self,
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> List[Dict[str, Any]]:
        """Get filtered context samples."""
        samples = self._context_samples.copy()
        
        if selector_name:
            samples = [
                sample for sample in samples
                if sample["selector_name"] == selector_name
            ]
        
        if time_window:
            cutoff_time = datetime.utcnow() - time_window
            samples = [
                sample for sample in samples
                if sample["timestamp"] >= cutoff_time
            ]
        
        return samples
