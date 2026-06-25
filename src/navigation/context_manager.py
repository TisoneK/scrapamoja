"""
Navigation context management

Maintain and manage navigation context including page state, user session information, 
and navigation history to inform intelligent routing decisions.
Conforms to Constitution Principle III - Deep Modularity.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from .interfaces import IContextManager
from .models import NavigationContext, PageState, AuthenticationState, NavigationOutcome
from .exceptions import ContextManagementError
from .logging_config import get_navigation_logger, set_correlation_id, generate_correlation_id
from .schema_validation import navigation_validator


class ContextManager(IContextManager):
    """Navigation context management implementation"""
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize context manager with storage and configuration"""
        self.logger = get_navigation_logger("context_manager")
        self.config = config or {}
        
        # Storage configuration
        self.storage_path = Path(storage_path or "data/navigation/contexts")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory context cache
        self._contexts: Dict[str, NavigationContext] = {}
        self._session_contexts: Dict[str, str] = {}  # session_id -> context_id mapping
        
        # Configuration
        self.max_context_age_hours = self.config.get("max_context_age_hours", 24)
        self.max_history_items = self.config.get("max_history_items", 1000)
        self.cleanup_interval_hours = self.config.get("cleanup_interval_hours", 6)
        self.auto_save_enabled = self.config.get("auto_save_enabled", True)
        
        # Cleanup tracking
        self._last_cleanup = datetime.utcnow()
        
        self.logger.info(
            "Context manager initialized",
            storage_path=str(self.storage_path),
            max_context_age_hours=self.max_context_age_hours,
            auto_save_enabled=self.auto_save_enabled
        )
    
    async def create_context(
        self,
        session_id: str,
        initial_page: str
    ) -> NavigationContext:
        """Create new navigation context"""
        try:
            # Generate correlation ID for this operation
            correlation_id = generate_correlation_id()
            set_correlation_id(correlation_id)
            
            self.logger.info(
                "Creating navigation context",
                session_id=session_id,
                initial_page=initial_page
            )
            
            # Check if session already has an active context
            if session_id in self._session_contexts:
                existing_context_id = self._session_contexts[session_id]
                if existing_context_id in self._contexts:
                    self.logger.warning(
                        "Session already has active context",
                        session_id=session_id,
                        existing_context_id=existing_context_id
                    )
                    return self._contexts[existing_context_id]
            
            # Create initial page state
            page_state = PageState(
                url=initial_page,
                title=self._extract_page_title(initial_page),
                page_type=self._detect_page_type(initial_page),
                load_time=0.0,
                dom_elements_count=0,
                has_dynamic_content=self._detect_dynamic_content(initial_page),
                requires_authentication=self._detect_authentication_required(initial_page)
            )
            
            # Create navigation context
            context_id = f"ctx_{session_id}_{correlation_id}"
            context = NavigationContext(
                context_id=context_id,
                session_id=session_id,
                current_page=page_state,
                correlation_id=correlation_id
            )
            
            # Validate context
            context_data = context.to_dict()
            if not navigation_validator.validate_context(context_data):
                raise ContextManagementError(
                    "Created context failed validation",
                    "CONTEXT_VALIDATION_FAILED",
                    {"context_id": context_id}
                )
            
            # Store context
            self._contexts[context_id] = context
            self._session_contexts[session_id] = context_id
            
            # Auto-save if enabled
            if self.auto_save_enabled:
                await self._save_context_to_storage(context)
            
            self.logger.info(
                "Navigation context created successfully",
                context_id=context_id,
                session_id=session_id
            )
            
            return context
            
        except Exception as e:
            self.logger.error(
                f"Failed to create navigation context: {str(e)}",
                session_id=session_id,
                initial_page=initial_page,
                correlation_id=correlation_id
            )
            raise ContextManagementError(
                f"Failed to create context for session {session_id}: {str(e)}",
                "CONTEXT_CREATION_FAILED",
                {
                    "session_id": session_id,
                    "initial_page": initial_page,
                    "correlation_id": correlation_id
                }
            )
    
    async def update_context(
        self,
        context_id: str,
        navigation_event: NavigationEvent
    ) -> NavigationContext:
        """Update context with navigation event"""
        try:
            set_correlation_id(navigation_event.correlation_id)
            
            if context_id not in self._contexts:
                raise ContextManagementError(
                    f"Context {context_id} not found",
                    "CONTEXT_NOT_FOUND",
                    {"context_id": context_id}
                )
            
            context = self._contexts[context_id]
            
            self.logger.debug(
                "Updating navigation context",
                context_id=context_id,
                event_id=navigation_event.event_id,
                outcome=navigation_event.outcome.value
            )
            
            # Add navigation event to history
            context.add_navigation_event(navigation_event.event_id)
            
            # Update performance metrics
            if navigation_event.performance_metrics:
                if navigation_event.is_successful():
                    context.record_navigation_success(
                        navigation_event.performance_metrics.duration_seconds
                    )
                else:
                    context.record_navigation_failure(
                        navigation_event.performance_metrics.duration_seconds
                    )
            
            # Update page state if navigation was successful
            if navigation_event.is_successful() and navigation_event.page_url_after:
                new_page_state = PageState(
                    url=navigation_event.page_url_after,
                    title=self._extract_page_title(navigation_event.page_url_after),
                    page_type=self._detect_page_type(navigation_event.page_url_after),
                    load_time=navigation_event.performance_metrics.duration_seconds if navigation_event.performance_metrics else 0.0,
                    dom_elements_count=navigation_event.performance_metrics.dom_changes_count if navigation_event.performance_metrics else 0,
                    has_dynamic_content=self._detect_dynamic_content(navigation_event.page_url_after),
                    requires_authentication=self._detect_authentication_required(navigation_event.page_url_after)
                )
                
                context.update_page(new_page_state)
            
            # Update stealth scores if available
            if navigation_event.stealth_score_after is not None:
                context.update_session_data("last_stealth_score", navigation_event.stealth_score_after)
            
            # Auto-save if enabled
            if self.auto_save_enabled:
                await self._save_context_to_storage(context)
            
            self.logger.debug(
                "Navigation context updated successfully",
                context_id=context_id,
                pages_visited=context.pages_visited,
                success_rate=context.get_success_rate()
            )
            
            return context
            
        except Exception as e:
            self.logger.error(
                f"Failed to update navigation context: {str(e)}",
                context_id=context_id,
                event_id=navigation_event.event_id
            )
            raise ContextManagementError(
                f"Failed to update context {context_id}: {str(e)}",
                "CONTEXT_UPDATE_FAILED",
                {
                    "context_id": context_id,
                    "event_id": navigation_event.event_id
                }
            )
    
    async def get_context_history(
        self,
        context_id: str,
        limit: int = 100
    ) -> List[NavigationEvent]:
        """Get navigation history for context"""
        try:
            if context_id not in self._contexts:
                raise ContextManagementError(
                    f"Context {context_id} not found",
                    "CONTEXT_NOT_FOUND",
                    {"context_id": context_id}
                )
            
            context = self._contexts[context_id]
            
            # Get navigation events from storage
            history_events = []
            for event_id in context.navigation_history[-limit:]:
                event = await self._load_navigation_event(event_id)
                if event:
                    history_events.append(event)
            
            self.logger.debug(
                "Retrieved context history",
                context_id=context_id,
                events_count=len(history_events),
                limit=limit
            )
            
            return history_events
            
        except Exception as e:
            self.logger.error(
                f"Failed to get context history: {str(e)}",
                context_id=context_id,
                limit=limit
            )
            raise ContextManagementError(
                f"Failed to get history for context {context_id}: {str(e)}",
                "HISTORY_RETRIEVAL_FAILED",
                {
                    "context_id": context_id,
                    "limit": limit
                }
            )
    
    async def cleanup_context(
        self,
        context_id: str
    ) -> bool:
        """Clean up context resources"""
        try:
            if context_id not in self._contexts:
                self.logger.warning(
                    "Context not found for cleanup",
                    context_id=context_id
                )
                return False
            
            context = self._contexts[context_id]
            
            self.logger.info(
                "Cleaning up navigation context",
                context_id=context_id,
                session_id=context.session_id
            )
            
            # Save final state
            if self.auto_save_enabled:
                await self._save_context_to_storage(context)
            
            # Remove from memory
            del self._contexts[context_id]
            
            # Remove session mapping
            if context.session_id in self._session_contexts:
                if self._session_contexts[context.session_id] == context_id:
                    del self._session_contexts[context.session_id]
            
            # Clean up storage files
            await self._cleanup_context_storage(context_id)
            
            self.logger.info(
                "Navigation context cleaned up successfully",
                context_id=context_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to cleanup context: {str(e)}",
                context_id=context_id
            )
            raise ContextManagementError(
                f"Failed to cleanup context {context_id}: {str(e)}",
                "CONTEXT_CLEANUP_FAILED",
                {"context_id": context_id}
            )
    
    async def get_context(
        self,
        context_id: str
    ) -> Optional[NavigationContext]:
        """Get context by ID"""
        return self._contexts.get(context_id)
    
    async def get_context_by_session(
        self,
        session_id: str
    ) -> Optional[NavigationContext]:
        """Get context by session ID"""
        context_id = self._session_contexts.get(session_id)
        if context_id:
            return self._contexts.get(context_id)
        return None
    
    async def list_active_contexts(self) -> List[str]:
        """List all active context IDs"""
        return list(self._contexts.keys())
    
    async def list_active_sessions(self) -> List[str]:
        """List all active session IDs"""
        return list(self._session_contexts.keys())
    
    async def update_authentication_state(
        self,
        context_id: str,
        auth_state: AuthenticationState
    ) -> NavigationContext:
        """Update authentication state for context"""
        try:
            if context_id not in self._contexts:
                raise ContextManagementError(
                    f"Context {context_id} not found",
                    "CONTEXT_NOT_FOUND",
                    {"context_id": context_id}
                )
            
            context = self._contexts[context_id]
            context.update_authentication(auth_state)
            
            # Auto-save if enabled
            if self.auto_save_enabled:
                await self._save_context_to_storage(context)
            
            self.logger.info(
                "Authentication state updated",
                context_id=context_id,
                is_authenticated=auth_state.is_authenticated,
                auth_method=auth_state.auth_method
            )
            
            return context
            
        except Exception as e:
            self.logger.error(
                f"Failed to update authentication state: {str(e)}",
                context_id=context_id
            )
            raise ContextManagementError(
                f"Failed to update auth state for context {context_id}: {str(e)}",
                "AUTH_UPDATE_FAILED",
                {"context_id": context_id}
            )
    
    async def cleanup_expired_contexts(self) -> int:
        """Clean up expired contexts"""
        try:
            current_time = datetime.utcnow()
            expired_contexts = []
            
            for context_id, context in self._contexts.items():
                age = current_time - context.created_at
                if age > timedelta(hours=self.max_context_age_hours):
                    expired_contexts.append(context_id)
            
            cleaned_count = 0
            for context_id in expired_contexts:
                if await self.cleanup_context(context_id):
                    cleaned_count += 1
            
            self._last_cleanup = current_time
            
            self.logger.info(
                "Expired contexts cleanup completed",
                expired_count=len(expired_contexts),
                cleaned_count=cleaned_count
            )
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(
                f"Failed to cleanup expired contexts: {str(e)}"
            )
            return 0
    
    async def get_context_statistics(self) -> Dict[str, Any]:
        """Get context management statistics"""
        try:
            total_contexts = len(self._contexts)
            total_sessions = len(self._session_contexts)
            
            # Calculate statistics
            authenticated_contexts = sum(
                1 for context in self._contexts.values()
                if context.is_authenticated()
            )
            
            average_success_rate = 0.0
            if total_contexts > 0:
                success_rates = [
                    context.get_success_rate()
                    for context in self._contexts.values()
                ]
                average_success_rate = sum(success_rates) / len(success_rates)
            
            total_pages_visited = sum(
                context.pages_visited
                for context in self._contexts.values()
            )
            
            total_navigation_time = sum(
                context.total_navigation_time
                for context in self._contexts.values()
            )
            
            return {
                "total_contexts": total_contexts,
                "total_sessions": total_sessions,
                "authenticated_contexts": authenticated_contexts,
                "average_success_rate": average_success_rate,
                "total_pages_visited": total_pages_visited,
                "total_navigation_time": total_navigation_time,
                "last_cleanup": self._last_cleanup.isoformat(),
                "storage_path": str(self.storage_path)
            }
            
        except Exception as e:
            self.logger.error(
                f"Failed to get context statistics: {str(e)}"
            )
            return {}
    
    # Private helper methods
    
    def _extract_page_title(self, url: str) -> str:
        """Extract page title from URL"""
        # Simple title extraction - in real implementation, this would use page content
        if url:
            # Extract last path component as title
            parts = url.rstrip('/').split('/')
            return parts[-1] if parts else url
        return ""
    
    def _detect_page_type(self, url: str) -> str:
        """Detect page type from URL"""
        url_lower = url.lower()
        
        if any(pattern in url_lower for pattern in ['/login', '/signin', '/auth']):
            return "authentication"
        elif any(pattern in url_lower for pattern in ['/admin', '/dashboard']):
            return "admin"
        elif any(pattern in url_lower for pattern in ['/search', '/query']):
            return "search"
        elif any(pattern in url_lower for pattern in ['/cart', '/checkout', '/payment']):
            return "ecommerce"
        elif any(pattern in url_lower for pattern in ['.js', '/api/', '/ajax']):
            return "dynamic"
        else:
            return "standard"
    
    def _detect_dynamic_content(self, url: str) -> bool:
        """Detect if page has dynamic content"""
        url_lower = url.lower()
        
        # Heuristics for dynamic content detection
        dynamic_indicators = [
            '.js', 'react', 'angular', 'vue', 'spa', 'ajax',
            'api/', 'dynamic', 'async'
        ]
        
        return any(indicator in url_lower for indicator in dynamic_indicators)
    
    def _detect_authentication_required(self, url: str) -> bool:
        """Detect if page requires authentication"""
        url_lower = url.lower()
        
        auth_indicators = [
            '/login', '/signin', '/auth', '/secure', '/admin',
            '/dashboard', '/profile', '/account'
        ]
        
        return any(indicator in url_lower for indicator in auth_indicators)
    
    async def _save_context_to_storage(self, context: NavigationContext) -> None:
        """Save context to storage"""
        try:
            # Save context data
            context_file = self.storage_path / f"{context.context_id}.json"
            context_data = context.to_dict()
            
            with open(context_file, 'w', encoding='utf-8') as f:
                json.dump(context_data, f, indent=2, default=str)
            
            # Save navigation events
            events_dir = self.storage_path / "events"
            events_dir.mkdir(exist_ok=True)
            
            for event_id in context.navigation_history[-100:]:  # Save last 100 events
                event_file = events_dir / f"{event_id}.json"
                if not event_file.exists():
                    # Create placeholder event file
                    event_data = {
                        "event_id": event_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "context_id": context.context_id
                    }
                    
                    with open(event_file, 'w', encoding='utf-8') as f:
                        json.dump(event_data, f, indent=2, default=str)
            
        except Exception as e:
            self.logger.warning(
                f"Failed to save context to storage: {str(e)}",
                context_id=context.context_id
            )
    
    async def _load_context_from_storage(self, context_id: str) -> Optional[NavigationContext]:
        """Load context from storage"""
        try:
            context_file = self.storage_path / f"{context_id}.json"
            
            if not context_file.exists():
                return None
            
            with open(context_file, 'r', encoding='utf-8') as f:
                context_data = json.load(f)
            
            # Validate loaded data
            if not navigation_validator.validate_context(context_data):
                self.logger.warning(
                    "Loaded context failed validation",
                    context_id=context_id
                )
                return None
            
            context = NavigationContext.from_dict(context_data)
            return context
            
        except Exception as e:
            self.logger.warning(
                f"Failed to load context from storage: {str(e)}",
                context_id=context_id
            )
            return None
    
    async def _load_navigation_event(self, event_id: str) -> Optional[NavigationEvent]:
        """Load navigation event from storage"""
        try:
            events_dir = self.storage_path / "events"
            event_file = events_dir / f"{event_id}.json"
            
            if not event_file.exists():
                return None
            
            with open(event_file, 'r', encoding='utf-8') as f:
                event_data = json.load(f)
            
            # Create basic event from stored data
            event = NavigationEvent(
                event_id=event_data.get("event_id", event_id),
                route_id=event_data.get("route_id", "unknown"),
                context_before=event_data.get("context_before", "unknown"),
                context_after=event_data.get("context_after", "unknown"),
                outcome=NavigationOutcome.SUCCESS  # Default to success
            )
            
            return event
            
        except Exception as e:
            self.logger.warning(
                f"Failed to load navigation event: {str(e)}",
                event_id=event_id
            )
            return None
    
    async def _cleanup_context_storage(self, context_id: str) -> None:
        """Clean up context storage files"""
        try:
            # Remove context file
            context_file = self.storage_path / f"{context_id}.json"
            if context_file.exists():
                context_file.unlink()
            
            # Remove event files
            events_dir = self.storage_path / "events"
            if events_dir.exists():
                for event_file in events_dir.glob(f"{context_id}_*.json"):
                    event_file.unlink()
            
        except Exception as e:
            self.logger.warning(
                f"Failed to cleanup context storage: {str(e)}",
                context_id=context_id
            )
