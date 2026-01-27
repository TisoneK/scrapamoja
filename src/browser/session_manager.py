"""
Browser Session Implementation

This module implements the BrowserSession class for browser lifecycle management,
following the IBrowserSession interface.
"""

import asyncio
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
import structlog

try:
    from playwright.async_api import Browser, BrowserContext, Page
except ImportError:
    Browser = BrowserContext = Page = None

from .interfaces import IBrowserSession
from .models.session import BrowserSession, BrowserConfiguration, SessionStatus
from .models.context import TabContext
from .models.state import BrowserState
from .models.metrics import ResourceMetrics
from .models.enums import ContextStatus
from .state_manager import StateManager
from .snapshot import DOMSnapshotManager
from .exceptions import BrowserError, SessionCreationError, NavigationError
from .lifecycle import ModuleState, lifecycle_manager
from .resilience import resilience_manager
from ..config.settings import get_config


class BrowserSessionManager(IBrowserSession):
    """Manages individual browser sessions with full lifecycle support."""
    
    def __init__(
        self,
        session: BrowserSession,
        playwright_browser: Optional[Browser] = None,
        state_manager: Optional[StateManager] = None,
        snapshot_manager: Optional[DOMSnapshotManager] = None
    ):
        self.session = session
        self._playwright_browser = playwright_browser
        self._playwright_context: Optional[BrowserContext] = None
        self._active_context_id: Optional[str] = None
        
        # Managers
        self.state_manager = state_manager or StateManager()
        self.snapshot_manager = snapshot_manager or DOMSnapshotManager()
        
        # Configuration
        self.config = get_config()
        
        # Lifecycle state
        self.lifecycle_state = lifecycle_manager.register_module(f"session_{session.session_id}")
        
        # Logging
        self.logger = structlog.get_logger("browser.session_manager")
        
    async def initialize(self) -> bool:
        """Initialize the browser session."""
        try:
            await self.lifecycle_state.initialize()
            self.session.update_status(SessionStatus.INITIALIZING)
            
            # Create Playwright context if browser provided
            if self._playwright_browser and BrowserContext:
                context_options = self._build_context_options()
                self._playwright_context = await self._playwright_browser.new_context(**context_options)
                
                # Setup event listeners
                await self._setup_event_listeners()
                
            self.session.update_status(SessionStatus.ACTIVE)
            await self.lifecycle_state.activate()
            
            self.logger.info(
                "Browser session initialized",
                session_id=self.session.session_id,
                browser_type=self.session.browser_type
            )
            
            return True
            
        except Exception as e:
            await self.lifecycle_state.handle_error(e)
            self.session.update_status(SessionStatus.FAILED)
            
            self.logger.error(
                "Failed to initialize browser session",
                session_id=self.session.session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            raise SessionCreationError(
                "SESSION_INIT_FAILED",
                f"Failed to initialize session {self.session.session_id}: {str(e)}",
                session_id=self.session.session_id
            )
            
    async def create_context(self, url: Optional[str] = None) -> TabContext:
        """Create a new browser context/tab."""
        try:
            if not self.session.can_create_context():
                raise BrowserError(
                    "SESSION_NOT_ACTIVE",
                    f"Session {self.session.session_id} cannot create contexts",
                    session_id=self.session.session_id
                )
                
            # Generate context ID
            context_id = f"{self.session.session_id}_ctx_{int(time.time())}"
            
            # Create TabContext
            tab_context = TabContext(
                context_id=context_id,
                session_id=self.session.session_id,
                url=url
            )
            
            # Create Playwright page if context available
            if self._playwright_context and Page:
                page = await self._playwright_context.new_page()
                tab_context._playwright_page = page
                tab_context._playwright_context = self._playwright_context
                
                # Navigate to URL if provided
                if url:
                    await page.goto(url)
                    tab_context.update_status(ContextStatus.ACTIVE)
                    
            # Add to session
            self.session.add_context(context_id)
            
            # Set as active context
            self._active_context_id = context_id
            tab_context.set_active(True)
            
            self.logger.info(
                "Browser context created",
                session_id=self.session.session_id,
                context_id=context_id,
                url=url
            )
            
            return tab_context
            
        except Exception as e:
            self.logger.error(
                "Failed to create browser context",
                session_id=self.session.session_id,
                url=url,
                error=str(e),
                error_type=type(e).__name__
            )
            
            raise BrowserError(
                "CONTEXT_CREATION_FAILED",
                f"Failed to create context: {str(e)}",
                session_id=self.session.session_id
            )
            
    async def get_context(self, context_id: str) -> Optional[TabContext]:
        """Retrieve a specific context by ID."""
        # This would need to be implemented with context storage
        # For now, return None
        return None
        
    async def list_contexts(self) -> List[TabContext]:
        """List all contexts in this session."""
        # This would need to be implemented with context storage
        # For now, return empty list
        return []
        
    async def switch_to_context(self, context_id: str) -> bool:
        """Switch to a specific context."""
        try:
            if context_id not in self.session.contexts:
                self.logger.warning(
                    "Context not found in session",
                    session_id=self.session.session_id,
                    context_id=context_id,
                    available_contexts=self.session.contexts
                )
                return False
                
            # Deactivate current context
            if self._active_context_id:
                # Would deactivate current context here
                pass
                
            # Activate new context
            self._active_context_id = context_id
            self.session.update_activity()
            
            self.logger.info(
                "Switched to context",
                session_id=self.session.session_id,
                context_id=context_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to switch context",
                session_id=self.session.session_id,
                context_id=context_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
            
    async def close_context(self, context_id: str) -> bool:
        """Close a specific context."""
        try:
            if context_id not in self.session.contexts:
                self.logger.warning(
                    "Context not found for closure",
                    session_id=self.session.session_id,
                    context_id=context_id
                )
                return False
                
            # Clean up context resources
            # This would need to be implemented with actual context cleanup
            
            # Remove from session
            self.session.remove_context(context_id)
            
            # Update active context if needed
            if self._active_context_id == context_id:
                self._active_context_id = None
                
            self.logger.info(
                "Context closed",
                session_id=self.session.session_id,
                context_id=context_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to close context",
                session_id=self.session.session_id,
                context_id=context_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
            
    async def save_state(self, state_id: Optional[str] = None) -> BrowserState:
        """Save the current browser state."""
        try:
            return await resilience_manager.execute_with_resilience(
                "save_state",
                self.state_manager.save_state,
                self.session,
                state_id,
                retry_config="default"
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to save state",
                session_id=self.session.session_id,
                state_id=state_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise BrowserError(
                "STATE_SAVE_FAILED",
                f"Failed to save state: {str(e)}",
                session_id=self.session.session_id
            )
            
    async def restore_state(self, state: BrowserState) -> bool:
        """Restore browser state from saved data."""
        try:
            # This would implement state restoration logic
            # For now, just log the attempt
            self.logger.info(
                "State restoration attempted",
                session_id=self.session.session_id,
                state_id=state.state_id,
                cookies=len(state.cookies),
                storage_items=len(state.local_storage) + len(state.session_storage)
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to restore state",
                session_id=self.session.session_id,
                state_id=state.state_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
            
    async def get_resource_metrics(self) -> ResourceMetrics:
        """Get current resource usage metrics."""
        try:
            # This would implement actual resource monitoring
            # For now, return current metrics from session
            return self.session.resource_metrics
            
        except Exception as e:
            self.logger.error(
                "Failed to get resource metrics",
                session_id=self.session.session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            # Return empty metrics on error
            return ResourceMetrics(session_id=self.session.session_id)
            
    async def take_screenshot(self, context_id: Optional[str] = None) -> bytes:
        """Take screenshot of session or specific context."""
        try:
            if context_id and self._active_context_id == context_id:
                # Take screenshot of specific context
                # This would need to be implemented with actual screenshot logic
                pass
            else:
                # Take screenshot of active context
                pass
                
            # Return empty bytes for now
            return b""
            
        except Exception as e:
            self.logger.error(
                "Failed to take screenshot",
                session_id=self.session.session_id,
                context_id=context_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return b""
            
    async def get_dom_snapshot(self, context_id: Optional[str] = None) -> Dict[str, Any]:
        """Get DOM snapshot for debugging."""
        try:
            # This would implement DOM snapshot logic
            # For now, return empty dict
            return {}
            
        except Exception as e:
            self.logger.error(
                "Failed to get DOM snapshot",
                session_id=self.session.session_id,
                context_id=context_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return {}
            
    async def shutdown(self) -> bool:
        """Shutdown the browser session."""
        try:
            self.session.update_status(SessionStatus.CLOSING)
            
            # Close all contexts
            for context_id in self.session.contexts.copy():
                await self.close_context(context_id)
                
            # Close Playwright context
            if self._playwright_context:
                await self._playwright_context.close()
                self._playwright_context = None
                
            # Update status
            self.session.update_status(SessionStatus.TERMINATED)
            await self.lifecycle_state.shutdown()
            
            self.logger.info(
                "Browser session shutdown",
                session_id=self.session.session_id
            )
            
            return True
            
        except Exception as e:
            self.session.update_status(SessionStatus.CLEANUP_ERROR)
            self.logger.error(
                "Failed to shutdown session",
                session_id=self.session.session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
            
    def _build_context_options(self) -> Dict[str, Any]:
        """Build Playwright context options from configuration."""
        config = self.session.configuration
        
        options = {
            "viewport": {
                "width": config.viewport_width,
                "height": config.viewport_height
            },
            "locale": config.locale,
            "timezone_id": config.timezone,
            "ignore_https_errors": config.ignore_https_errors
        }
        
        # Add user agent if specified
        if config.user_agent:
            options["user_agent"] = config.user_agent
            
        # Add proxy if configured
        if config.proxy_server:
            options["proxy"] = {
                "server": config.proxy_server
            }
            if config.proxy_username and config.proxy_password:
                options["proxy"]["username"] = config.proxy_username
                options["proxy"]["password"] = config.proxy_password
                
        return options
        
    async def _setup_event_listeners(self) -> None:
        """Setup event listeners for the browser context."""
        if not self._playwright_context:
            return
            
        # Setup page event listeners
        self._playwright_context.on("page", self._on_page_created)
        
    async def _on_page_created(self, page: Page) -> None:
        """Handle new page creation."""
        self.logger.debug(
            "New page created",
            session_id=self.session.session_id,
            page_url=page.url
        )
