"""
DOM context and element info structures for Selector Engine.

Provides context management for tab-aware selector resolution and element
information extraction from Playwright pages.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from playwright.async_api import Page, ElementHandle

from src.models.selector_models import ElementInfo, TabContext
from src.utils.exceptions import ContextValidationError
from ..core.snapshot.handlers import SelectorSnapshot
from ..core.snapshot.manager import SnapshotManager


@dataclass
class DOMContext:
    """Context information for DOM resolution."""
    page: Page
    tab_context: str
    url: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate DOM context."""
        if not self.tab_context.strip():
            raise ContextValidationError(
                self.tab_context, "Tab context cannot be empty"
            )
        if not self.url.strip():
            raise ContextValidationError(
                self.tab_context, "URL cannot be empty"
            )
        
        # Initialize selector snapshot handler
        from src.core.snapshot.config import get_settings
        snapshot_settings = get_settings()
        self.snapshot_manager = SnapshotManager(snapshot_settings.base_path)
        self.selector_snapshot = SelectorSnapshot(self.snapshot_manager)
    
    async def get_page_content(self) -> str:
        """Get current page HTML content."""
        try:
            return await self.page.content()
        except Exception as e:
            raise ContextValidationError(
                self.tab_context, f"Failed to get page content: {e}"
            )
    
    async def get_viewport_size(self) -> Tuple[int, int]:
        """Get current viewport size."""
        try:
            viewport = self.page.viewport_size
            return viewport.get("width", 0), viewport.get("height", 0)
        except Exception as e:
            raise ContextValidationError(
                self.tab_context, f"Failed to get viewport size: {e}"
            )
    
    async def get_user_agent(self) -> str:
        """Get current user agent."""
        try:
            user_agent = await self.page.evaluate("navigator.userAgent")
            return user_agent or "Unknown"
        except Exception as e:
            raise ContextValidationError(
                self.tab_context, f"Failed to get user agent: {e}"
            )
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to context."""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self.metadata.get(key, default)
    
    async def capture_screenshot(self) -> bytes:
        """Capture screenshot of current page using core snapshot system."""
        try:
            # Use selector snapshot handler for consistent capture
            context_data = {
                "site": "unknown",
                "module": "selector_context",
                "component": "screenshot_capture",
                "function": "capture_screenshot",
                "tab_context": self.tab_context,
                "url": self.url
            }
            
            # Trigger snapshot through selector handler
            snapshot_id = await self.selector_snapshot._capture_selector_snapshot(
                trigger_source="screenshot_requested",
                context_data=context_data
            )
            
            # Still return direct screenshot for backward compatibility
            return await self.page.screenshot(type='png')
            
        except Exception as e:
            raise ContextValidationError(
                self.tab_context, f"Failed to capture screenshot: {e}"
            )


class ElementInfoExtractor:
    """Extracts detailed information from DOM elements."""
    
    @staticmethod
    async def extract_element_info(element: ElementHandle) -> ElementInfo:
        """Extract comprehensive element information."""
        try:
            # Basic element properties
            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
            text_content = await element.evaluate("el => el.textContent || ''")
            
            # Attributes
            attributes = await element.evaluate("""
                el => {
                    const attrs = {};
                    for (const attr of el.attributes) {
                        attrs[attr.name] = attr.value;
                    }
                    return attrs;
                }
            """)
            
            # CSS classes
            class_list = await element.evaluate("el => Array.from(el.classList)")
            
            # DOM path
            dom_path = await ElementInfoExtractor._get_dom_path(element)
            
            # Visibility and interactability
            visibility = await ElementInfoExtractor._is_visible(element)
            interactable = await ElementInfoExtractor._is_interactable(element)
            
            return ElementInfo(
                tag_name=tag_name,
                text_content=text_content.strip(),
                attributes=attributes,
                css_classes=class_list,
                dom_path=dom_path,
                visibility=visibility,
                interactable=interactable
            )
            
        except Exception as e:
            raise ContextValidationError(
                "unknown", f"Failed to extract element info: {e}"
            )
    
    @staticmethod
    async def _get_dom_path(element: ElementHandle) -> str:
        """Generate DOM path for element."""
        return await element.evaluate("""
            el => {
                const path = [];
                let current = el;
                
                while (current && current !== document.body) {
                    let selector = current.tagName.toLowerCase();
                    
                    // Add ID if present
                    if (current.id) {
                        selector += '#' + current.id;
                    } else if (current.className) {
                        // Add first class if no ID
                        const classes = current.className.split(' ').filter(c => c);
                        if (classes.length > 0) {
                            selector += '.' + classes[0];
                        }
                    }
                    
                    // Add nth-child if needed for uniqueness
                    const siblings = Array.from(current.parentNode.children || []);
                    const sameTagSiblings = siblings.filter(s => s.tagName === current.tagName);
                    if (sameTagSiblings.length > 1) {
                        const index = sameTagSiblings.indexOf(current) + 1;
                        selector += `:nth-child(${index})`;
                    }
                    
                    path.unshift(selector);
                    current = current.parentNode;
                }
                
                return 'body' + (path.length > 0 ? ' > ' + path.join(' > ') : '');
            }
        """)
    
    @staticmethod
    async def _is_visible(element: ElementHandle) -> bool:
        """Check if element is visible."""
        return await element.evaluate("""
            el => {
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && 
                       style.visibility !== 'hidden' && 
                       style.opacity !== '0';
            }
        """)
    
    @staticmethod
    async def _is_interactable(element: ElementHandle) -> bool:
        """Check if element is interactable."""
        return await element.evaluate("""
            el => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                
                // Check if element is visible and not disabled
                if (style.display === 'none' || 
                    style.visibility === 'hidden' || 
                    style.opacity === '0' ||
                    rect.width === 0 || 
                    rect.height === 0) {
                    return false;
                }
                
                // Check if element is disabled
                if (el.disabled || el.getAttribute('aria-disabled') === 'true') {
                    return false;
                }
                
                // Check common interactable elements
                const interactableTags = ['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'];
                const interactableRoles = ['button', 'link', 'menuitem', 'option'];
                
                return interactableTags.includes(el.tagName) ||
                       interactableRoles.includes(el.getAttribute('role')) ||
                       el.onclick !== null ||
                       el.style.cursor === 'pointer';
            }
        """)


class TabContextManager:
    """Manages tab contexts for selector scoping."""
    
    def __init__(self):
        self._contexts: Dict[str, TabContext] = {}
        self._active_context: Optional[str] = None
    
    def register_context(self, context: TabContext) -> None:
        """Register a tab context."""
        self._contexts[context.name] = context
    
    def get_context(self, name: str) -> Optional[TabContext]:
        """Get tab context by name."""
        return self._contexts.get(name)
    
    def set_active_context(self, name: str) -> bool:
        """Set active tab context."""
        if name in self._contexts:
            self._active_context = name
            return True
        return False
    
    def get_active_context(self) -> Optional[TabContext]:
        """Get currently active context."""
        if self._active_context:
            return self._contexts.get(self._active_context)
        return None
    
    def list_contexts(self) -> List[str]:
        """List all registered context names."""
        return list(self._contexts.keys())
    
    def is_context_available(self, name: str) -> bool:
        """Check if context is available."""
        context = self._contexts.get(name)
        return context.is_available if context else False
    
    async def activate_tab(self, page: Page, tab_name: str) -> bool:
        """Activate a tab by clicking its selector."""
        context = self.get_context(tab_name)
        if not context or not context.is_available:
            return False
        
        try:
            # Click tab activation selector
            await page.click(context.activation_selector)
            
            # Wait for tab content to load
            await page.wait_for_selector(context.container_selector, timeout=context.load_timeout * 1000)
            
            # Set as active context
            self.set_active_context(tab_name)
            return True
            
        except Exception as e:
            raise ContextValidationError(
                tab_name, f"Failed to activate tab: {e}"
            )
    
    async def validate_context(self, page: Page, context_name: str) -> bool:
        """Validate that context is properly activated."""
        context = self.get_context(context_name)
        if not context:
            return False
        
        try:
            # Check if container element exists
            container = await page.query_selector(context.container_selector)
            if not container:
                return False
            
            # Check if tab is marked as active (if applicable)
            if context.activation_selector:
                active_tab = await page.query_selector(f"{context.activation_selector}.active")
                return active_tab is not None
            
            return True
            
        except Exception:
            return False


class DOMContextFactory:
    """Factory for creating DOM contexts with validation."""
    
    def __init__(self, tab_manager: Optional[TabContextManager] = None):
        self.tab_manager = tab_manager or TabContextManager()
    
    def create_context(self, page: Page, tab_context: str, 
                      metadata: Optional[Dict[str, Any]] = None) -> DOMContext:
        """Create a new DOM context."""
        try:
            # Get page information
            url = page.url
            timestamp = datetime.utcnow()
            
            # Validate tab context
            if not self.tab_manager.get_context(tab_context):
                raise ContextValidationError(
                    tab_context, "Tab context not registered"
                )
            
            # Create context
            context = DOMContext(
                page=page,
                tab_context=tab_context,
                url=url,
                timestamp=timestamp,
                metadata=metadata or {}
            )
            
            return context
            
        except Exception as e:
            raise ContextValidationError(
                tab_context, f"Failed to create DOM context: {e}"
            )
    
    async def create_validated_context(self, page: Page, tab_context: str,
                                     metadata: Optional[Dict[str, Any]] = None) -> DOMContext:
        """Create and validate a DOM context."""
        # Create context
        context = self.create_context(page, tab_context, metadata)
        
        # Validate tab is properly activated
        if not await self.tab_manager.validate_context(page, tab_context):
            raise ContextValidationError(
                tab_context, "Tab context validation failed"
            )
        
        return context


# Global instances
default_tab_manager = TabContextManager()
context_factory = DOMContextFactory(default_tab_manager)


def get_tab_manager() -> TabContextManager:
    """Get default tab context manager."""
    return default_tab_manager


def get_context_factory() -> DOMContextFactory:
    """Get default DOM context factory."""
    return context_factory


# Utility functions
async def extract_element_info(element: ElementHandle) -> ElementInfo:
    """Extract element information using default extractor."""
    return await ElementInfoExtractor.extract_element_info(element)


async def create_dom_context(page: Page, tab_context: str,
                           metadata: Optional[Dict[str, Any]] = None) -> DOMContext:
    """Create DOM context using default factory."""
    return await context_factory.create_validated_context(page, tab_context, metadata)


def register_tab_context(name: str, container_selector: str,
                       activation_selector: str, is_available: bool = True,
                       load_timeout: float = 10.0) -> None:
    """Register a tab context with default manager."""
    context = TabContext(
        name=name,
        container_selector=container_selector,
        activation_selector=activation_selector,
        is_available=is_available,
        load_timeout=load_timeout
    )
    default_tab_manager.register_context(context)


# Predefined common tab contexts
def register_common_contexts():
    """Register common tab contexts for web scraping."""
    register_tab_context(
        name="summary",
        container_selector=".summary-content, .match-summary",
        activation_selector="[data-tab='summary'], .tab.summary",
        is_available=True
    )
    
    register_tab_context(
        name="odds",
        container_selector=".odds-content, .betting-odds",
        activation_selector="[data-tab='odds'], .tab.odds",
        is_available=True
    )
    
    register_tab_context(
        name="h2h",
        container_selector=".h2h-content, .head-to-head",
        activation_selector="[data-tab='h2h'], .tab.h2h",
        is_available=True
    )
    
    register_tab_context(
        name="lineups",
        container_selector=".lineups-content, .team-lineups",
        activation_selector="[data-tab='lineups'], .tab.lineups",
        is_available=False  # Often not available
    )
    
    register_tab_context(
        name="standings",
        container_selector=".standings-content, .league-table",
        activation_selector="[data-tab='standings'], .tab.standings",
        is_available=False  # Often not available
    )
