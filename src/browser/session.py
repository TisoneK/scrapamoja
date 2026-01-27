"""
Browser session management and lifecycle control.

This module provides the BrowserSession class for managing individual browser
instances with their configuration, state, and resource monitoring.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import asyncio
import json
import uuid
from playwright.async_api import Browser, BrowserContext, Page
from playwright.async_api import Error as PlaywrightError

from .config import BrowserConfiguration
from .models.enums import SessionStatus
from .monitoring import ResourceMetrics, get_resource_monitor
from src.observability.logger import get_logger
from src.observability.events import (
    publish_browser_session_created,
    publish_browser_session_initialized,
    publish_browser_session_closed,
    publish_browser_session_failed,
    publish_browser_context_created,
    publish_browser_page_created,
    publish_browser_tab_switched
)
from src.observability.metrics import get_browser_metrics_collector
from src.storage.adapter import get_storage_adapter
from src.utils.exceptions import BrowserSessionError
from .snapshot import snapshot_manager
from .models.context import TabContext
from .models.enums import ContextStatus


@dataclass
class BrowserSession:
    """Represents a browser instance with its configuration and state."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    configuration: BrowserConfiguration = field(default_factory=BrowserConfiguration)
    status: SessionStatus = SessionStatus.INITIALIZING
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    # Runtime state
    browser: Optional[Browser] = None
    contexts: List[BrowserContext] = field(default_factory=list)
    pages: List[Page] = field(default_factory=list)
    process_id: Optional[int] = None
    resource_metrics: Optional[ResourceMetrics] = None
    
    # Tab context management
    tab_contexts: Dict[str, TabContext] = field(default_factory=dict)
    active_tab_id: Optional[str] = None
    
    def __post_init__(self):
        """Initialize session after creation."""
        self._logger = get_logger(f"browser_session.{self.session_id[:8]}")
        self._storage = get_storage_adapter()
        self._correlation_id = self.session_id[:8]  # Use session ID prefix as correlation ID
        self._metrics_collector = get_browser_metrics_collector()
        
        # Start metrics tracking
        self._metrics_collector.start_session_tracking(
            self.session_id,
            self.configuration.browser_type.value
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "configuration": self.configuration.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "process_id": self.process_id,
            "resource_metrics": self.resource_metrics.to_dict() if self.resource_metrics else None,
            "context_count": len(self.contexts),
            "page_count": len(self.pages)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BrowserSession":
        """Create session from dictionary."""
        session = cls(
            session_id=data["session_id"],
            configuration=BrowserConfiguration.from_dict(data["configuration"]),
            status=SessionStatus(data["status"])
        )
        
        if "created_at" in data:
            session.created_at = datetime.fromisoformat(data["created_at"])
        
        if "last_activity" in data:
            session.last_activity = datetime.fromisoformat(data["last_activity"])
        
        session.process_id = data.get("process_id")
        
        if "resource_metrics" in data and data["resource_metrics"]:
            session.resource_metrics = ResourceMetrics.from_dict(data["resource_metrics"])
        
        return session
    
    async def initialize(self) -> None:
        """Initialize the browser session."""
        if self.status != SessionStatus.INITIALIZING:
            raise BrowserSessionError(
                "invalid_session_state",
                f"Cannot initialize session in state: {self.status.value}"
            )
        
        try:
            # Publish session created event
            await publish_browser_session_created(
                self.session_id,
                self.configuration.browser_type.value,
                self._correlation_id
            )
            
            self._logger.info(
                "initializing_browser_session",
                session_id=self.session_id,
                browser_type=self.configuration.browser_type.value,
                correlation_id=self._correlation_id
            )
            
            # Prepare launch arguments
            launch_args = {
                "headless": self.configuration.headless,
                **self.configuration.launch_options
            }
            
            # Add stealth configuration
            if self.configuration.stealth.user_agent:
                launch_args["user_agent"] = self.configuration.stealth.user_agent
            
            # Initialize browser
            from playwright.async_api import async_playwright
            
            playwright = await async_playwright().start()
            
            if self.configuration.browser_type.value == "chromium":
                self.browser = await playwright.chromium.launch(**launch_args)
            elif self.configuration.browser_type.value == "firefox":
                self.browser = await playwright.firefox.launch(**launch_args)
            elif self.configuration.browser_type.value == "webkit":
                self.browser = await playwright.webkit.launch(**launch_args)
            else:
                raise BrowserSessionError(
                    "unsupported_browser_type",
                    f"Browser type not supported: {self.configuration.browser_type.value}"
                )
            
            # Get process ID for monitoring
            if hasattr(self.browser, '_impl_obj') and hasattr(self.browser._impl_obj, '_process'):
                self.process_id = self.browser._impl_obj._process.pid
            
            # Start resource monitoring
            if self.process_id:
                await get_resource_monitor().start_monitoring(
                    self.session_id, 
                    self.process_id
                )
            
            # Update status
            self.status = SessionStatus.ACTIVE
            self.last_activity = datetime.utcnow()
            
            # Publish session initialized event
            await publish_browser_session_initialized(
                self.session_id,
                self.process_id,
                self._correlation_id
            )
            
            self._logger.info(
                "browser_session_initialized",
                session_id=self.session_id,
                process_id=self.process_id,
                browser_type=self.configuration.browser_type.value,
                correlation_id=self._correlation_id
            )
            
            # Persist session state
            await self.persist_state()
            
        except PlaywrightError as e:
            self.status = SessionStatus.FAILED
            
            # Capture snapshot for failure analysis
            await self._capture_failure_snapshot("initialization_failed", str(e))
            
            # Publish session failed event
            await publish_browser_session_failed(
                self.session_id,
                str(e),
                self._correlation_id
            )
            
            self._logger.error(
                "browser_initialization_failed",
                session_id=self.session_id,
                error=str(e),
                correlation_id=self._correlation_id
            )
            raise BrowserSessionError(
                "browser_initialization_failed",
                f"Failed to initialize browser: {str(e)}",
                {"session_id": self.session_id, "error": str(e)}
            )
        except Exception as e:
            self.status = SessionStatus.FAILED
            self._logger.error(
                "session_initialization_error",
                session_id=self.session_id,
                error=str(e)
            )
            raise BrowserSessionError(
                "session_initialization_error",
                f"Session initialization failed: {str(e)}",
                {"session_id": self.session_id, "error": str(e)}
            )
    
    async def create_context(self, **context_options) -> BrowserContext:
        """Create a new browser context."""
        if self.status != SessionStatus.ACTIVE:
            raise BrowserSessionError(
                "invalid_session_state",
                f"Cannot create context in state: {self.status.value}"
            )
        
        if not self.browser:
            raise BrowserSessionError(
                "browser_not_initialized",
                "Browser instance not available"
            )
        
        try:
            # Merge configuration context options with provided options
            final_options = {
                **self.configuration.context_options,
                **context_options
            }
            
            # Add stealth settings
            if self.configuration.stealth.viewport:
                final_options["viewport"] = self.configuration.stealth.viewport
            
            if self.configuration.stealth.locale:
                final_options["locale"] = self.configuration.stealth.locale
            
            if self.configuration.stealth.timezone:
                final_options["timezone_id"] = self.configuration.stealth.timezone
            
            if self.configuration.stealth.geolocation:
                final_options["geolocation"] = self.configuration.stealth.geolocation
                final_options["permissions"] = self.configuration.stealth.permissions
            
            if self.configuration.stealth.extra_http_headers:
                final_options["extra_http_headers"] = self.configuration.stealth.extra_http_headers
            
            final_options["bypass_csp"] = self.configuration.stealth.bypass_csp
            final_options["ignore_https_errors"] = self.configuration.stealth.ignore_https_errors
            
            context = await self.browser.new_context(**final_options)
            self.contexts.append(context)
            
            # Record metrics
            self._metrics_collector.record_context_created(self.session_id)
            
            self.last_activity = datetime.utcnow()
            
            # Publish context created event
            await publish_browser_context_created(
                self.session_id,
                str(id(context)),
                self._correlation_id
            )
            
            self._logger.info(
                "browser_context_created",
                session_id=self.session_id,
                context_count=len(self.contexts),
                correlation_id=self._correlation_id
            )
            
            return context
            
        except PlaywrightError as e:
            self._logger.error(
                "context_creation_failed",
                session_id=self.session_id,
                error=str(e)
            )
            raise BrowserSessionError(
                "context_creation_failed",
                f"Failed to create browser context: {str(e)}",
                {"session_id": self.session_id, "error": str(e)}
            )
    
    async def create_page(self, context: Optional[BrowserContext] = None) -> Page:
        """Create a new page in the specified context."""
        if not context and self.contexts:
            context = self.contexts[0]
        elif not context:
            context = await self.create_context()
        
        try:
            page = await context.new_page()
            self.pages.append(page)
            
            # Record metrics
            self._metrics_collector.record_page_created(self.session_id)
            
            self.last_activity = datetime.utcnow()
            
            # Publish page created event
            await publish_browser_page_created(
                self.session_id,
                str(id(page)),
                page.url,
                self._correlation_id
            )
            
            self._logger.info(
                "browser_page_created",
                session_id=self.session_id,
                page_count=len(self.pages),
                correlation_id=self._correlation_id
            )
            
            return page
            
        except PlaywrightError as e:
            self._logger.error(
                "page_creation_failed",
                session_id=self.session_id,
                error=str(e)
            )
            raise BrowserSessionError(
                "page_creation_failed",
                f"Failed to create browser page: {str(e)}",
                {"session_id": self.session_id, "error": str(e)}
            )
    
    async def update_metrics(self) -> None:
        """Update resource metrics for the session."""
        if self.process_id:
            self.resource_metrics = await get_resource_monitor().get_current_metrics(
                self.session_id, 
                self.process_id
            )
    
    async def persist_state(self) -> None:
        """Persist session state to storage."""
        try:
            await self._storage.store(
                f"browser_sessions/{self.session_id}.json",
                self.to_dict()
            )
            
            self._logger.debug(
                "session_state_persisted",
                session_id=self.session_id
            )
            
        except Exception as e:
            self._logger.error(
                "session_persistence_failed",
                session_id=self.session_id,
                error=str(e)
            )
    
    async def _capture_failure_snapshot(self, failure_type: str, error: str) -> None:
        """Capture DOM snapshot for failure analysis."""
        try:
            # Try to capture snapshot from any available page
            for page in self.pages:
                try:
                    await snapshot_manager.capture_snapshot(
                        page,
                        f"{self.session_id}_{failure_type}",
                        include_screenshot=True,
                        custom_selectors=["body", "html", "head"]
                    )
                    self._logger.info(
                        "failure_snapshot_captured",
                        session_id=self.session_id,
                        failure_type=failure_type,
                        page_id=str(id(page))
                    )
                    break  # Only need one snapshot
                except Exception as snapshot_error:
                    self._logger.warning(
                        "snapshot_capture_failed",
                        session_id=self.session_id,
                        failure_type=failure_type,
                        snapshot_error=str(snapshot_error)
                    )
                    continue
        except Exception as e:
            self._logger.warning(
                "failure_snapshot_error",
                session_id=self.session_id,
                failure_type=failure_type,
                error=str(e)
            )
    
    async def close(self) -> None:
        """Close the browser session and cleanup resources."""
        if self.status in [SessionStatus.CLOSING, SessionStatus.TERMINATED]:
            return
        
        self.status = SessionStatus.CLOSING
        
        try:
            self._logger.info(
                "closing_browser_session",
                session_id=self.session_id
            )
            
            # Close all pages
            for page in self.pages:
                try:
                    await page.close()
                except Exception as e:
                    self._logger.warning(
                        "page_close_error",
                        session_id=self.session_id,
                        error=str(e)
                    )
            
            self.pages.clear()
            
            # Close all contexts
            for context in self.contexts:
                try:
                    await context.close()
                except Exception as e:
                    self._logger.warning(
                        "context_close_error",
                        session_id=self.session_id,
                        error=str(e)
                    )
            
            self.contexts.clear()
            
            # Close browser
            if self.browser:
                try:
                    await self.browser.close()
                except Exception as e:
                    self._logger.warning(
                        "browser_close_error",
                        session_id=self.session_id,
                        error=str(e)
                    )
            
            # Stop resource monitoring
            if self.process_id:
                await get_resource_monitor().stop_monitoring(self.session_id)
            
            self.status = SessionStatus.TERMINATED
            
            # Finalize metrics
            final_metrics = self._metrics_collector.finalize_session_metrics(self.session_id)
            if final_metrics:
                self._logger.info(
                    "session_metrics_finalized",
                    session_id=self.session_id,
                    duration_seconds=final_metrics.session_duration_seconds,
                    total_pages=final_metrics.total_pages_created,
                    peak_memory_mb=final_metrics.peak_memory_mb
                )
            
            # Publish session closed event
            await publish_browser_session_closed(
                self.session_id,
                self._correlation_id
            )
            
            self._logger.info(
                "browser_session_closed",
                session_id=self.session_id,
                correlation_id=self._correlation_id
            )
            
            # Remove persisted state
            try:
                await self._storage.delete(f"browser_sessions/{self.session_id}.json")
            except Exception as e:
                self._logger.warning(
                    "session_state_cleanup_failed",
                    session_id=self.session_id,
                    error=str(e)
                )
            
        except Exception as e:
            self.status = SessionStatus.CLEANUP_ERROR
            self._logger.error(
                "session_cleanup_error",
                session_id=self.session_id,
                error=str(e)
            )
            raise BrowserSessionError(
                "session_cleanup_error",
                f"Session cleanup failed: {str(e)}",
                {"session_id": self.session_id, "error": str(e)}
            )
    
    # Tab Context Management Methods
    
    async def create_tab_context(self, url: Optional[str] = None, title: Optional[str] = None) -> TabContext:
        """Create a new tab context."""
        if self.status != SessionStatus.ACTIVE:
            raise BrowserSessionError(
                "invalid_session_state",
                f"Cannot create tab context in state: {self.status.value}"
            )
        
        # Generate unique context ID
        context_id = f"tab_{len(self.tab_contexts) + 1}_{int(datetime.utcnow().timestamp())}"
        
        # Create tab context
        tab_context = TabContext(
            context_id=context_id,
            session_id=self.session_id,
            url=url,
            title=title
        )
        
        # Add to session
        self.tab_contexts[context_id] = tab_context
        
        # Set as active if no active tab
        if not self.active_tab_id:
            await self.switch_to_tab(context_id)
        
        self._logger.info(
            "tab_context_created",
            session_id=self.session_id,
            context_id=context_id,
            url=url,
            title=title,
            correlation_id=self._correlation_id
        )
        
        return tab_context
    
    async def get_tab_context(self, context_id: str) -> Optional[TabContext]:
        """Get a specific tab context by ID."""
        return self.tab_contexts.get(context_id)
    
    async def list_tab_contexts(self) -> List[TabContext]:
        """List all tab contexts."""
        return list(self.tab_contexts.values())
    
    async def get_active_tab_context(self) -> Optional[TabContext]:
        """Get the currently active tab context."""
        if self.active_tab_id:
            return self.tab_contexts.get(self.active_tab_id)
        return None
    
    async def switch_to_tab(self, context_id: str) -> bool:
        """Switch to a specific tab context."""
        if context_id not in self.tab_contexts:
            self._logger.warning(
                "tab_context_not_found",
                session_id=self.session_id,
                context_id=context_id,
                correlation_id=self._correlation_id
            )
            return False
        
        # Deactivate current active tab
        if self.active_tab_id and self.active_tab_id in self.tab_contexts:
            self.tab_contexts[self.active_tab_id].set_active(False)
        
        # Activate new tab
        self.tab_contexts[context_id].set_active(True)
        self.active_tab_id = context_id
        
        # Publish tab switched event
        await publish_browser_tab_switched(
            self.session_id,
            context_id,
            self._correlation_id
        )
        
        self._logger.info(
            "tab_switched",
            session_id=self.session_id,
            from_context_id=self.active_tab_id,
            to_context_id=context_id,
            correlation_id=self._correlation_id
        )
        
        return True
    
    async def close_tab_context(self, context_id: str) -> bool:
        """Close a specific tab context."""
        if context_id not in self.tab_contexts:
            self._logger.warning(
                "tab_context_not_found",
                session_id=self.session_id,
                context_id=context_id,
                correlation_id=self._correlation_id
            )
            return False
        
        tab_context = self.tab_contexts[context_id]
        
        # Update status
        tab_context.update_status(ContextStatus.CLOSING)
        
        # If this was the active tab, switch to another
        if self.active_tab_id == context_id:
            remaining_tabs = [tid for tid in self.tab_contexts.keys() if tid != context_id]
            if remaining_tabs:
                await self.switch_to_tab(remaining_tabs[0])
            else:
                self.active_tab_id = None
        
        # Remove from session
        del self.tab_contexts[context_id]
        
        self._logger.info(
            "tab_context_closed",
            session_id=self.session_id,
            context_id=context_id,
            correlation_id=self._correlation_id
        )
        
        return True
    
    async def close_all_tab_contexts(self) -> int:
        """Close all tab contexts."""
        context_ids = list(self.tab_contexts.keys())
        closed_count = 0
        
        for context_id in context_ids:
            if await self.close_tab_context(context_id):
                closed_count += 1
        
        self._logger.info(
            "all_tab_contexts_closed",
            session_id=self.session_id,
            closed_count=closed_count,
            correlation_id=self._correlation_id
        )
        
        return closed_count
    
    async def get_tab_statistics(self) -> Dict[str, Any]:
        """Get statistics about tab contexts."""
        contexts = list(self.tab_contexts.values())
        
        return {
            "total_tabs": len(contexts),
            "active_tab_id": self.active_tab_id,
            "tabs_by_status": {
                status.value: len([c for c in contexts if c.status == status])
                for status in ContextStatus
            },
            "average_navigations": sum(c.get_navigation_count() for c in contexts) / len(contexts) if contexts else 0,
            "oldest_tab_age_seconds": min(c.get_context_age_seconds() for c in contexts) if contexts else 0,
            "total_navigations": sum(c.get_navigation_count() for c in contexts)
        }
    
    async def save_state(self, state_id: Optional[str] = None) -> str:
        """Save browser state to storage."""
        from .state import StateManager
        
        try:
            # Create state manager if not exists
            if not hasattr(self, '_state_manager'):
                self._state_manager = StateManager()
            
            # Save state
            saved_state_id = await self._state_manager.save_state(self, state_id)
            
            self._logger.info(
                "Browser state saved",
                session_id=self.session_id,
                state_id=saved_state_id,
                correlation_id=self._correlation_id
            )
            
            return saved_state_id
            
        except Exception as e:
            self._logger.error(
                "Failed to save browser state",
                session_id=self.session_id,
                error=str(e),
                error_type=type(e).__name__,
                correlation_id=self._correlation_id
            )
            raise
    
    async def restore_state(self, state_id: str) -> bool:
        """Restore browser state from storage."""
        from .state import StateManager
        from .models.state import BrowserState
        
        try:
            # Create state manager if not exists
            if not hasattr(self, '_state_manager'):
                self._state_manager = StateManager()
            
            # Load state
            browser_state = await self._state_manager.load_state(state_id)
            if not browser_state:
                self._logger.warning(
                    "Failed to load browser state",
                    session_id=self.session_id,
                    state_id=state_id,
                    correlation_id=self._correlation_id
                )
                return False
            
            # Restore state
            success = await self._apply_state_to_session(browser_state)
            
            if success:
                self._logger.info(
                    "Browser state restored",
                    session_id=self.session_id,
                    state_id=state_id,
                    correlation_id=self._correlation_id
                )
            else:
                self._logger.error(
                    "Failed to apply browser state",
                    session_id=self.session_id,
                    state_id=state_id,
                    correlation_id=self._correlation_id
                )
            
            return success
            
        except Exception as e:
            self._logger.error(
                "Failed to restore browser state",
                session_id=self.session_id,
                state_id=state_id,
                error=str(e),
                error_type=type(e).__name__,
                correlation_id=self._correlation_id
            )
            return False
    
    async def list_saved_states(self) -> List[str]:
        """List saved states for this session."""
        from .state import StateManager
        
        try:
            # Create state manager if not exists
            if not hasattr(self, '_state_manager'):
                self._state_manager = StateManager()
            
            # List states
            states = await self._state_manager.list_states(self.session_id)
            
            self._logger.info(
                "Listed saved states",
                session_id=self.session_id,
                state_count=len(states),
                correlation_id=self._correlation_id
            )
            
            return states
            
        except Exception as e:
            self._logger.error(
                "Failed to list saved states",
                session_id=self.session_id,
                error=str(e),
                error_type=type(e).__name__,
                correlation_id=self._correlation_id
            )
            return []
    
    async def delete_saved_state(self, state_id: str) -> bool:
        """Delete a saved state."""
        from .state import StateManager
        
        try:
            # Create state manager if not exists
            if not hasattr(self, '_state_manager'):
                self._state_manager = StateManager()
            
            # Delete state
            success = await self._state_manager.delete_state(state_id)
            
            if success:
                self._logger.info(
                    "Saved state deleted",
                    session_id=self.session_id,
                    state_id=state_id,
                    correlation_id=self._correlation_id
                )
            else:
                self._logger.warning(
                    "Failed to delete saved state",
                    session_id=self.session_id,
                    state_id=state_id,
                    correlation_id=self._correlation_id
                )
            
            return success
            
        except Exception as e:
            self._logger.error(
                "Failed to delete saved state",
                session_id=self.session_id,
                state_id=state_id,
                error=str(e),
                error_type=type(e).__name__,
                correlation_id=self._correlation_id
            )
            return False
    
    async def _apply_state_to_session(self, browser_state: "BrowserState") -> bool:
        """Apply browser state to the current session."""
        try:
            # Apply cookies to all contexts
            for tab_context in self.tab_contexts.values():
                if tab_context._playwright_context:
                    # Convert cookies to Playwright format
                    playwright_cookies = []
                    for cookie in browser_state.cookies:
                        playwright_cookie = {
                            "name": cookie.name,
                            "value": cookie.value,
                            "domain": cookie.domain,
                            "path": cookie.path,
                            "secure": cookie.secure,
                            "httpOnly": cookie.http_only,
                            "sameSite": cookie.same_site
                        }
                        if cookie.expires:
                            playwright_cookie["expires"] = cookie.expires
                        playwright_cookies.append(playwright_cookie)
                    
                    # Add cookies to context
                    await tab_context._playwright_context.add_cookies(playwright_cookies)
            
            # Apply storage to active tab
            active_tab = await self.get_active_tab_context()
            if active_tab and active_tab._playwright_page:
                # Apply local storage
                if browser_state.local_storage:
                    await active_tab._playwright_page.evaluate("""
                        (data) => {
                            for (const [key, value] of Object.entries(data)) {
                                localStorage.setItem(key, value);
                            }
                        }
                    """, browser_state.local_storage)
                
                # Apply session storage
                if browser_state.session_storage:
                    await active_tab._playwright_page.evaluate("""
                        (data) => {
                            for (const [key, value] of Object.entries(data)) {
                                sessionStorage.setItem(key, value);
                            }
                        }
                    """, browser_state.session_storage)
            
            # Store authentication tokens for later use
            if browser_state.authentication_tokens:
                if not hasattr(self, '_auth_tokens'):
                    self._auth_tokens = {}
                self._auth_tokens.update(browser_state.authentication_tokens)
            
            self._logger.info(
                "Browser state applied successfully",
                session_id=self.session_id,
                cookie_count=len(browser_state.cookies),
                local_storage_items=len(browser_state.local_storage),
                session_storage_items=len(browser_state.session_storage),
                auth_tokens_count=len(browser_state.authentication_tokens)
            )
            
            return True
            
        except Exception as e:
            self._logger.error(
                "Failed to apply browser state",
                session_id=self.session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
