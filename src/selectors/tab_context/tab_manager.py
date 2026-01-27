"""
Tab Context Detection and Management for Selector Engine.

Provides comprehensive tab context detection, management, and isolation
for SPA applications with complex tab states as required by User Story 3.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict

from src.models.selector_models import (
    TabContext, TabState, TabType, TabVisibility
)
from src.observability.logger import get_logger
from src.utils.exceptions import TabContextError


@dataclass
class TabDetectionResult:
    """Result of tab context detection."""
    success: bool
    active_tab: Optional[str] = None
    available_tabs: List[str] = field(default_factory=list)
    tab_contexts: Dict[str, TabContext] = field(default_factory=dict)
    detection_time: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None


@dataclass
class TabSwitchingEvent:
    """Event representing a tab switching action."""
    from_tab: Optional[str]
    to_tab: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: Optional[str] = None
    switching_time: Optional[float] = None


class TabContextManager:
    """
    Manages tab context detection, tracking, and isolation for SPA applications.
    
    Provides comprehensive tab state management with:
    - Active tab detection
    - Tab context isolation
    - State persistence and recovery
    - Tab switching event handling
    - Performance monitoring
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self._logger = get_logger("tab_context_manager")
        self._storage_path = Path(storage_path or "data/tab_contexts")
        self._storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for tab contexts
        self._tab_contexts: Dict[str, TabContext] = {}
        self._active_tab: Optional[str] = None
        self._last_detection: Optional[datetime] = None
        
        # Tab switching history
        self._switching_history: List[TabSwitchingEvent] = []
        self._max_history_size = 100
        
        # Performance metrics
        self._detection_count = 0
        self._switching_count = 0
        self._error_count = 0
        
        self._logger.info(
            "TabContextManager initialized",
            storage_path=str(self._storage_path)
        )
    
    async def detect_active_tab_context(self, page) -> Optional[TabContext]:
        """
        Detect the currently active tab context.
        
        Args:
            page: Playwright page object
            
        Returns:
            Active tab context or None if detection fails
            
        Raises:
            TabContextError: If tab detection fails
        """
        try:
            start_time = datetime.utcnow()
            
            # Execute JavaScript to detect tab state
            tab_state_script = """
            () => {
                // Common tab detection patterns for SPA applications
                const activeTabSelectors = [
                    '.tab.active',
                    '.tab.active[data-tab]',
                    '.nav-tabs .active',
                    '.tabs .active',
                    '[role="tab"][aria-selected="true"]',
                    '.tab-pane.active',
                    '.tab-content .active'
                ];
                
                const tabContainerSelectors = [
                    '.tabs',
                    '.nav-tabs',
                    '.tab-container',
                    '[role="tablist"]',
                    '.tab-navigation'
                ];
                
                let activeTab = null;
                let availableTabs = [];
                let tabStates = {};
                
                // Find active tab
                for (const selector of activeTabSelectors) {
                    const activeElement = document.querySelector(selector);
                    if (activeElement) {
                        activeTab = activeElement.getAttribute('data-tab') || 
                                   activeElement.getAttribute('id') ||
                                   activeElement.textContent?.trim() ||
                                   'unknown';
                        break;
                    }
                }
                
                // Find all available tabs
                for (const containerSelector of tabContainerSelectors) {
                    const container = document.querySelector(containerSelector);
                    if (container) {
                        const tabs = container.querySelectorAll('[data-tab], .tab, [role="tab"]');
                        tabs.forEach(tab => {
                            const tabId = tab.getAttribute('data-tab') || 
                                        tab.getAttribute('id') ||
                                        tab.textContent?.trim() ||
                                        'unknown';
                            
                            if (!availableTabs.includes(tabId)) {
                                availableTabs.push(tabId);
                                
                                // Determine tab state
                                const isActive = tab.classList.contains('active') ||
                                              tab.getAttribute('aria-selected') === 'true';
                                const isVisible = tab.offsetParent !== null;
                                const isLoaded = tab.getAttribute('data-loaded') === 'true' ||
                                              isVisible; // Assume loaded if visible
                                
                                tabStates[tabId] = {
                                    visible: isVisible,
                                    loaded: isLoaded,
                                    active: isActive
                                };
                            }
                        });
                        break;
                    }
                }
                
                // Fallback: try to detect from URL hash or query parameters
                if (!activeTab && availableTabs.length === 0) {
                    const hash = window.location.hash.slice(1);
                    const params = new URLSearchParams(window.location.search);
                    const tabParam = params.get('tab') || params.get('view');
                    
                    if (hash) {
                        activeTab = hash;
                        availableTabs = [hash];
                        tabStates[hash] = { visible: true, loaded: true, active: true };
                    } else if (tabParam) {
                        activeTab = tabParam;
                        availableTabs = [tabParam];
                        tabStates[tabParam] = { visible: true, loaded: true, active: true };
                    }
                }
                
                return {
                    active_tab: activeTab,
                    available_tabs: availableTabs,
                    tab_states: tabStates
                };
            }
            """
            
            # Execute detection script
            result = await page.evaluate(tab_state_script)
            
            if not result or not result.get('available_tabs'):
                self._logger.warning(
                    "no_tabs_detected",
                    page_url=page.url
                )
                return None
            
            # Process detection results
            detection_result = self._process_detection_result(result)
            
            if not detection_result.success:
                raise TabContextError(
                    "tab_detection_failed",
                    f"Tab context detection failed: {detection_result.error_message}"
                )
            
            # Update internal state
            self._active_tab = detection_result.active_tab
            self._tab_contexts.update(detection_result.tab_contexts)
            self._last_detection = datetime.utcnow()
            self._detection_count += 1
            
            # Log detection
            detection_time = (datetime.utcnow() - start_time).total_seconds()
            self._logger.info(
                "tab_context_detected",
                active_tab=detection_result.active_tab,
                total_tabs=len(detection_result.available_tabs),
                detection_time=detection_time,
                available_tabs=detection_result.available_tabs
            )
            
            # Return active tab context
            return detection_result.tab_contexts.get(detection_result.active_tab)
            
        except Exception as e:
            self._error_count += 1
            error_msg = f"Tab context detection failed: {str(e)}"
            self._logger.error(
                "tab_context_detection_error",
                error=str(e),
                page_url=getattr(page, 'url', 'unknown')
            )
            
            if isinstance(e, TabContextError):
                raise
            
            raise TabContextError(
                "tab_detection_failed",
                error_msg
            )
    
    def get_tab_context_by_id(self, page, tab_id: str) -> Optional[TabContext]:
        """
        Get specific tab context by ID.
        
        Args:
            page: Playwright page object
            tab_id: ID of the tab to retrieve
            
        Returns:
            Tab context or None if not found
            
        Raises:
            TabContextError: If tab ID is invalid or detection fails
        """
        if not tab_id or not tab_id.strip():
            raise TabContextError(
                "invalid_tab_id",
                "Tab ID cannot be empty"
            )
        
        # Check cache first
        if tab_id in self._tab_contexts:
            return self._tab_contexts[tab_id]
        
        # Detect all tab contexts if not cached
        try:
            # Use sync detection for cached contexts
            if hasattr(page, 'evaluate'):
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If we're in an async context, create a new task
                        task = asyncio.create_task(self.detect_active_tab_context(page))
                        active_context = asyncio.run_coroutine_threadsafe(task, loop).result(timeout=5.0)
                    else:
                        # If no loop running, run the coroutine directly
                        active_context = asyncio.run(self.detect_active_tab_context(page))
                except Exception:
                    # Fallback to sync detection
                    active_context = self._detect_sync(page)
            else:
                raise TabContextError(
                    "page_not_supported",
                    "Page object does not support tab detection"
                )
            
            return self._tab_contexts.get(tab_id)
            
        except Exception as e:
            self._logger.error(
                "tab_context_retrieval_failed",
                tab_id=tab_id,
                error=str(e)
            )
            
            if isinstance(e, TabContextError):
                raise
            
            raise TabContextError(
                "tab_context_retrieval_failed",
                f"Failed to retrieve tab context '{tab_id}': {str(e)}"
            )
    
    def list_all_available_tabs(self, page) -> List[TabContext]:
        """
        List all available tab contexts.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of all available tab contexts
            
        Raises:
            TabContextError: If tab detection fails
        """
        try:
            # Ensure tab contexts are detected
            if not self._tab_contexts:
                if hasattr(page, 'evaluate'):
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            task = asyncio.create_task(self.detect_active_tab_context(page))
                            asyncio.run_coroutine_threadsafe(task, loop).result(timeout=5.0)
                        else:
                            asyncio.run(self.detect_active_tab_context(page))
                    except Exception:
                        self._detect_sync(page)
                else:
                    raise TabContextError(
                        "page_not_supported",
                        "Page object does not support tab detection"
                    )
            
            return list(self._tab_contexts.values())
            
        except Exception as e:
            self._logger.error(
                "tab_listing_failed",
                error=str(e)
            )
            
            if isinstance(e, TabContextError):
                raise
            
            raise TabContextError(
                "tab_listing_failed",
                f"Failed to list available tabs: {str(e)}"
            )
    
    def validate_tab_context_exists(self, page, tab_id: str) -> bool:
        """
        Validate that a tab context exists.
        
        Args:
            page: Playwright page object
            tab_id: ID of the tab to validate
            
        Returns:
            True if tab exists, False otherwise
        """
        try:
            tab_context = self.get_tab_context_by_id(page, tab_id)
            return tab_context is not None
        except TabContextError:
            return False
    
    def detect_tab_switching(self, page, previous_context: Optional[TabContext]) -> bool:
        """
        Detect if tab switching has occurred.
        
        Args:
            page: Playwright page object
            previous_context: Previous active tab context
            
        Returns:
            True if tab switching detected, False otherwise
        """
        try:
            current_context = self.get_tab_context_by_id(page, self._active_tab or "")
            
            if not current_context or not previous_context:
                return False
            
            # Check if active tab changed
            if current_context.tab_id != previous_context.tab_id:
                return True
            
            # Check if tab state changed significantly
            if (current_context.state != previous_context.state or
                current_context.visibility != previous_context.visibility):
                return True
            
            return False
            
        except Exception as e:
            self._logger.error(
                "tab_switching_detection_failed",
                error=str(e)
            )
            return False
    
    def create_tab_context(self, tab_id: str, **kwargs) -> TabContext:
        """
        Create a new tab context.
        
        Args:
            tab_id: ID of the tab
            **kwargs: Additional tab context properties
            
        Returns:
            Created tab context
        """
        context = TabContext(
            tab_id=tab_id,
            tab_type=kwargs.get('tab_type', TabType.CONTENT),
            state=kwargs.get('state', TabState.LOADING),
            visibility=kwargs.get('visibility', TabVisibility.HIDDEN),
            is_active=kwargs.get('is_active', False),
            dom_scope=kwargs.get('dom_scope', f"div#{tab_id}-content"),
            metadata=kwargs.get('metadata', {})
        )
        
        self._tab_contexts[tab_id] = context
        return context
    
    def update_tab_context_state(self, context: TabContext, **updates) -> TabContext:
        """
        Update tab context state.
        
        Args:
            context: Tab context to update
            **updates: Properties to update
            
        Returns:
            Updated tab context
        """
        for key, value in updates.items():
            if hasattr(context, key):
                setattr(context, key, value)
        
        # Update cache
        self._tab_contexts[context.tab_id] = context
        
        return context
    
    def isolate_tab_dom_scope(self, page, tab_id: str) -> Optional[str]:
        """
        Isolate DOM scope for a specific tab.
        
        Args:
            page: Playwright page object
            tab_id: ID of the tab
            
        Returns:
            DOM scope selector or None if not found
        """
        try:
            # Get tab context
            tab_context = self.get_tab_context_by_id(page, tab_id)
            if not tab_context:
                return None
            
            # Use existing DOM scope if available
            if tab_context.dom_scope:
                return tab_context.dom_scope
            
            # Try to detect DOM scope automatically
            scope_detection_script = f"""
            () => {{
                const tabId = '{tab_id}';
                
                // Look for tab content container
                const contentSelectors = [
                    `[data-tab-content="${{tabId}}"]`,
                    `#${{tabId}}-content`,
                    `.tab-content[data-tab="${{tabId}}"]`,
                    `.tab-pane[data-tab="${{tabId}}"]`,
                    `[role="tabpanel"][aria-labelledby="${{tabId}}"]`
                ];
                
                for (const selector of contentSelectors) {{
                    const element = document.querySelector(selector);
                    if (element) {{
                        return selector;
                    }}
                }}
                
                return null;
            }}
            """
            
            if hasattr(page, 'evaluate'):
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        task = asyncio.create_task(page.evaluate(scope_detection_script))
                        scope = asyncio.run_coroutine_threadsafe(task, loop).result(timeout=5.0)
                    else:
                        scope = asyncio.run(page.evaluate(scope_detection_script))
                except Exception:
                    scope = None
            else:
                scope = None
            
            if scope:
                # Update tab context with detected scope
                tab_context.dom_scope = scope
                self._tab_contexts[tab_id] = tab_context
            
            return scope
            
        except Exception as e:
            self._logger.error(
                "dom_scope_isolation_failed",
                tab_id=tab_id,
                error=str(e)
            )
            return None
    
    def persist_tab_state(self, context: TabContext) -> bool:
        """
        Persist tab state to storage.
        
        Args:
            context: Tab context to persist
            
        Returns:
            True if persistence successful, False otherwise
        """
        try:
            file_path = self._storage_path / f"tab_{context.tab_id}.json"
            
            # Convert to serializable format
            state_data = {
                "tab_id": context.tab_id,
                "tab_type": context.tab_type.value,
                "state": context.state.value,
                "visibility": context.visibility.value,
                "is_active": context.is_active,
                "dom_scope": context.dom_scope,
                "metadata": context.metadata,
                "persisted_at": datetime.utcnow().isoformat()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            
            self._logger.debug(
                "tab_state_persisted",
                tab_id=context.tab_id,
                file_path=str(file_path)
            )
            
            return True
            
        except Exception as e:
            self._logger.error(
                "tab_state_persistence_failed",
                tab_id=context.tab_id,
                error=str(e)
            )
            return False
    
    def retrieve_tab_state(self, tab_id: str) -> Optional[TabContext]:
        """
        Retrieve persisted tab state from storage.
        
        Args:
            tab_id: ID of the tab to retrieve
            
        Returns:
            Retrieved tab context or None if not found
        """
        try:
            file_path = self._storage_path / f"tab_{tab_id}.json"
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            # Convert back to TabContext
            context = TabContext(
                tab_id=state_data["tab_id"],
                tab_type=TabType(state_data["tab_type"]),
                state=TabState(state_data["state"]),
                visibility=TabVisibility(state_data["visibility"]),
                is_active=state_data["is_active"],
                dom_scope=state_data["dom_scope"],
                metadata=state_data["metadata"]
            )
            
            self._logger.debug(
                "tab_state_retrieved",
                tab_id=tab_id,
                file_path=str(file_path)
            )
            
            return context
            
        except Exception as e:
            self._logger.error(
                "tab_state_retrieval_failed",
                tab_id=tab_id,
                error=str(e)
            )
            return None
    
    def _process_detection_result(self, result: Dict[str, Any]) -> TabDetectionResult:
        """Process tab detection result into structured format."""
        detection_result = TabDetectionResult(success=True)
        
        try:
            detection_result.active_tab = result.get('active_tab')
            detection_result.available_tabs = result.get('available_tabs', [])
            
            # Process tab states
            tab_states = result.get('tab_states', {})
            for tab_id, state_data in tab_states.items():
                # Determine tab properties
                is_active = tab_id == detection_result.active_tab
                visibility = TabVisibility.VISIBLE if state_data.get('visible') else TabVisibility.HIDDEN
                state = TabState.LOADED if state_data.get('loaded') else TabState.LOADING
                
                # Create tab context
                context = TabContext(
                    tab_id=tab_id,
                    tab_type=TabType.CONTENT,  # Default to content type
                    state=state,
                    visibility=visibility,
                    is_active=is_active,
                    dom_scope=f"div#{tab_id}-content",  # Default scope
                    metadata={
                        "detected_at": datetime.utcnow().isoformat(),
                        "raw_state": state_data
                    }
                )
                
                detection_result.tab_contexts[tab_id] = context
            
            return detection_result
            
        except Exception as e:
            detection_result.success = False
            detection_result.error_message = str(e)
            return detection_result
    
    def _detect_sync(self, page) -> Optional[TabContext]:
        """Synchronous fallback for tab detection."""
        try:
            # Simple synchronous detection using page URL or other available methods
            # This is a fallback when async detection is not available
            self._logger.warning(
                "using_sync_tab_detection",
                page_url=getattr(page, 'url', 'unknown')
            )
            
            # Create a default tab context based on URL
            url = getattr(page, 'url', '')
            if 'tab=' in url:
                from urllib.parse import parse_qs, urlparse
                parsed = urlparse(url)
                query_params = parse_qs(parsed.query)
                tab_param = query_params.get('tab', ['default'])[0]
                
                context = self.create_tab_context(
                    tab_param,
                    is_active=True,
                    state=TabState.LOADED,
                    visibility=TabVisibility.VISIBLE
                )
                
                self._active_tab = tab_param
                return context
            
            return None
            
        except Exception as e:
            self._logger.error(
                "sync_tab_detection_failed",
                error=str(e)
            )
            return None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for tab context management."""
        return {
            "detection_count": self._detection_count,
            "switching_count": self._switching_count,
            "error_count": self._error_count,
            "cached_tabs": len(self._tab_contexts),
            "active_tab": self._active_tab,
            "last_detection": self._last_detection.isoformat() if self._last_detection else None,
            "switching_history_size": len(self._switching_history)
        }


# Global tab context manager instance
tab_context_manager = TabContextManager()


def get_tab_context_manager() -> TabContextManager:
    """Get global tab context manager instance."""
    return tab_context_manager
