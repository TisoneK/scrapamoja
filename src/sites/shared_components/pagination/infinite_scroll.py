"""
Shared infinite scroll pagination component for reusable pagination across sites.

This module provides infinite scroll pagination functionality that can be easily
integrated into any site scraper with infinite scroll loading patterns.
"""

from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
import asyncio
import json
import re

from src.sites.base.component_interface import BaseComponent, ComponentContext, ComponentResult


class InfiniteScrollPaginationComponent(BaseComponent):
    """Shared infinite scroll pagination component for cross-site usage."""
    
    def __init__(
        self,
        component_id: str = "shared_infinite_scroll",
        name: str = "Shared Infinite Scroll Pagination Component",
        version: str = "1.0.0",
        description: str = "Reusable infinite scroll pagination for multiple sites"
    ):
        """
        Initialize shared infinite scroll pagination component.
        
        Args:
            component_id: Unique identifier for the component
            name: Human-readable name for the component
            version: Component version
            description: Component description
        """
        super().__init__(
            component_id=component_id,
            name=name,
            version=version,
            description=description,
            component_type="PAGINATION"
        )
        
        # Infinite scroll configurations for different sites
        self._site_configs: Dict[str, Dict[str, Any]] = {}
        
        # Pagination state per site
        self._pagination_states: Dict[str, Dict[str, Any]] = {}
        
        # Callback handlers
        self._load_callbacks: Dict[str, List[Callable]] = {}
        self._complete_callbacks: Dict[str, List[Callable]] = {}
        self._error_callbacks: Dict[str, List[Callable]] = {}
        
        # Component metadata
        self._supported_sites = [
            'twitter', 'facebook', 'instagram', 'reddit', 'linkedin',
            'youtube', 'tiktok', 'pinterest', 'tumblr', 'medium'
        ]
        
        # Common infinite scroll patterns
        self._scroll_triggers = [
            'window.scrollY + window.innerHeight >= document.body.offsetHeight - 1000',
            'document.documentElement.scrollTop + window.innerHeight >= document.documentElement.scrollHeight - 1000',
            'window.pageYOffset + window.innerHeight >= document.body.scrollHeight - 1000'
        ]
        
        self._loading_indicators = [
            '.loading', '.spinner', '.loader', '.loading-indicator',
            '[data-loading]', '.infinite-scroll-loader', '.more-loading'
        ]
        
        self._end_indicators = [
            '.no-more', '.end-of-results', '.no-more-results',
            '[data-end]', '.infinite-scroll-end', '.end-of-content'
        ]
    
    async def initialize(self, context: ComponentContext) -> bool:
        """
        Initialize shared infinite scroll pagination component.
        
        Args:
            context: Component context
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load infinite scroll configurations from context
            config = context.config_manager.get_config(context.environment) if context.config_manager else {}
            
            # Initialize default site configurations
            await self._initialize_default_configs()
            
            # Load custom site configurations
            custom_configs = config.get('infinite_scroll_site_configs', {})
            for site, site_config in custom_configs.items():
                self.register_site(site, site_config)
            
            self._log_operation("initialize", f"Shared infinite scroll component initialized with {len(self._site_configs)} site configurations")
            return True
            
        except Exception as e:
            self._log_operation("initialize", f"Shared infinite scroll initialization failed: {str(e)}", "error")
            return False
    
    async def execute(self, **kwargs) -> ComponentResult:
        """
        Execute infinite scroll pagination for a specific site.
        
        Args:
            **kwargs: Pagination parameters including 'site', 'page', 'max_scrolls', etc.
            
        Returns:
            Pagination result
        """
        try:
            start_time = datetime.utcnow()
            
            # Extract parameters
            site = kwargs.get('site')
            page = kwargs.get('page')
            max_scrolls = kwargs.get('max_scrolls', 10)
            scroll_delay = kwargs.get('scroll_delay', 2000)
            item_selector = kwargs.get('item_selector')
            auto_detect = kwargs.get('auto_detect', True)
            wait_for_new_content = kwargs.get('wait_for_new_content', True)
            
            if not site:
                return ComponentResult(
                    success=False,
                    data={'error': 'Site parameter is required'},
                    errors=['Site parameter is required']
                )
            
            if not page:
                return ComponentResult(
                    success=False,
                    data={'error': 'Page parameter is required'},
                    errors=['Page parameter is required']
                )
            
            # Initialize pagination state
            self._initialize_pagination_state(site)
            
            # Perform infinite scroll pagination
            scroll_result = await self._infinite_scroll(
                site, page, max_scrolls, scroll_delay, item_selector, auto_detect, wait_for_new_content
            )
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return ComponentResult(
                success=scroll_result['success'],
                data={
                    'site': site,
                    'max_scrolls': max_scrolls,
                    'scrolls_performed': scroll_result['scrolls_performed'],
                    'items_collected': scroll_result['items_collected'],
                    'is_complete': scroll_result['is_complete'],
                    **scroll_result
                },
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self._log_operation("execute", f"Infinite scroll pagination failed: {str(e)}", "error")
            return ComponentResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    def register_site(self, site: str, config: Dict[str, Any]) -> None:
        """
        Register infinite scroll configuration for a site.
        
        Args:
            site: Site identifier
            config: Infinite scroll configuration
        """
        self._site_configs[site] = {
            'scroll_container': config.get('scroll_container', 'body'),
            'item_selector': config.get('item_selector'),
            'loading_selector': config.get('loading_selector'),
            'end_selector': config.get('end_selector'),
            'scroll_step': config.get('scroll_step', 'window.innerHeight'),
            'scroll_delay': config.get('scroll_delay', 2000),
            'max_scrolls': config.get('max_scrolls', 10),
            'wait_for_new_content': config.get('wait_for_new_content', True),
            'content_check_delay': config.get('content_check_delay', 1000),
            'scroll_to_bottom': config.get('scroll_to_bottom', True),
            'smooth_scroll': config.get('smooth_scroll', False),
            'custom_scroll_function': config.get('custom_scroll_function')
        }
        
        self._log_operation("register_site", f"Registered infinite scroll configuration for site: {site}")
    
    async def _initialize_default_configs(self) -> None:
        """Initialize default infinite scroll configurations for common sites."""
        default_configs = {
            'twitter': {
                'scroll_container': 'div[data-testid="primaryColumn"]',
                'item_selector': 'div[data-testid="tweet"]',
                'loading_selector': '[data-testid="loading"]',
                'scroll_delay': 2000,
                'max_scrolls': 20
            },
            'facebook': {
                'scroll_container': 'div[role="feed"]',
                'item_selector': 'div[role="article"]',
                'loading_selector': '.scaffold__layout',
                'scroll_delay': 3000,
                'max_scrolls': 15
            },
            'reddit': {
                'scroll_container': '#shorts-feed-container, div[data-testid="post-container"]',
                'item_selector': 'div[data-testid="post-container"], div[data-click-id="post"]',
                'loading_selector': '.loading',
                'scroll_delay': 2500,
                'max_scrolls': 25
            },
            'linkedin': {
                'scroll_container': '.scaffold-finite-scroll__content',
                'item_selector': '.feed-shared-update-v2',
                'loading_selector': '.artdeco-spinner',
                'scroll_delay': 2000,
                'max_scrolls': 15
            },
            'youtube': {
                'scroll_container': 'div#contents',
                'item_selector': 'ytd-video-renderer, ytd-grid-video-renderer',
                'loading_selector': '.skeleton',
                'scroll_delay': 1500,
                'max_scrolls': 30
            },
            'instagram': {
                'scroll_container': 'div[role="main"]',
                'item_selector': 'article',
                'loading_selector': '.skeleton',
                'scroll_delay': 2000,
                'max_scrolls': 20
            }
        }
        
        for site, config in default_configs.items():
            if site not in self._site_configs:
                self._site_configs[site] = config
    
    def _initialize_pagination_state(self, site: str) -> None:
        """Initialize pagination state for a site."""
        if site not in self._pagination_states:
            self._pagination_states[site] = {
                'scrolls_performed': 0,
                'items_collected': 0,
                'last_item_count': 0,
                'is_complete': False,
                'start_time': datetime.utcnow(),
                'last_scroll_time': None,
                'error_count': 0
            }
    
    async def _infinite_scroll(
        self, site: str, page, max_scrolls: int, scroll_delay: int, 
        item_selector: str, auto_detect: bool, wait_for_new_content: bool
    ) -> Dict[str, Any]:
        """Perform infinite scroll pagination."""
        try:
            config = self._site_configs[site]
            state = self._pagination_states[site]
            
            # Auto-detect selectors if not provided
            if auto_detect and not item_selector:
                detected_selectors = await self._detect_selectors(page)
                item_selector = item_selector or detected_selectors.get('item_selector')
                config['loading_selector'] = config.get('loading_selector') or detected_selectors.get('loading_selector')
                config['end_selector'] = config.get('end_selector') or detected_selectors.get('end_selector')
            
            # Get initial item count
            initial_items = await self._get_item_count(page, item_selector)
            state['last_item_count'] = initial_items
            state['items_collected'] = initial_items
            
            self._log_operation("_infinite_scroll", f"Starting infinite scroll for {site} with {initial_items} initial items")
            
            # Perform scrolling
            scrolls_performed = 0
            for scroll_num in range(max_scrolls):
                # Check if pagination is complete
                if await self._is_pagination_complete(page, config):
                    state['is_complete'] = True
                    self._log_operation("_infinite_scroll", f"Pagination complete for {site} after {scrolls_performed} scrolls")
                    break
                
                # Perform scroll
                scroll_result = await self._perform_scroll(page, config, scroll_num)
                if not scroll_result['success']:
                    state['error_count'] += 1
                    if state['error_count'] >= 3:
                        break
                    continue
                
                scrolls_performed += 1
                state['scrolls_performed'] = scrolls_performed
                state['last_scroll_time'] = datetime.utcnow()
                
                # Wait for new content to load
                if wait_for_new_content:
                    await self._wait_for_new_content(page, config, item_selector)
                
                # Check for new items
                current_items = await self._get_item_count(page, item_selector)
                new_items = current_items - state['last_item_count']
                
                if new_items > 0:
                    state['items_collected'] = current_items
                    state['last_item_count'] = current_items
                    
                    # Call load callbacks
                    await self._call_load_callbacks(site, {
                        'scroll_number': scroll_num + 1,
                        'new_items': new_items,
                        'total_items': current_items,
                        'scrolls_performed': scrolls_performed
                    })
                
                # Check if we've reached the end
                if new_items == 0 and await self._is_at_bottom(page, config):
                    state['is_complete'] = True
                    break
                
                # Wait before next scroll
                await asyncio.sleep(scroll_delay / 1000.0)
            
            # Call completion callbacks
            if state['is_complete']:
                await self._call_complete_callbacks(site, state)
            
            return {
                'success': True,
                'scrolls_performed': scrolls_performed,
                'items_collected': state['items_collected'],
                'is_complete': state['is_complete'],
                'error_count': state['error_count'],
                'execution_time_seconds': (datetime.utcnow() - state['start_time']).total_seconds()
            }
            
        except Exception as e:
            self._log_operation("_infinite_scroll", f"Infinite scroll failed for {site}: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e),
                'scrolls_performed': self._pagination_states.get(site, {}).get('scrolls_performed', 0),
                'items_collected': self._pagination_states.get(site, {}).get('items_collected', 0)
            }
    
    async def _detect_selectors(self, page) -> Dict[str, str]:
        """Auto-detect selectors for infinite scroll."""
        try:
            detected_selectors = {}
            
            # Detect item selectors (common patterns)
            item_patterns = [
                'div[class*="item"]', 'div[class*="post"]', 'div[class*="tweet"]',
                'div[class*="card"]', 'div[class*="article"]', 'div[class*="result"]',
                'li[class*="item"]', 'li[class*="post"]', 'article', '[data-testid*="post"]'
            ]
            
            for pattern in item_patterns:
                elements = await page.query_selector_all(pattern)
                if len(elements) >= 3:  # Need at least 3 items to be confident
                    detected_selectors['item_selector'] = pattern
                    break
            
            # Detect loading indicators
            for indicator in self._loading_indicators:
                element = await page.query_selector(indicator)
                if element:
                    detected_selectors['loading_selector'] = indicator
                    break
            
            # Detect end indicators
            for indicator in self._end_indicators:
                element = await page.query_selector(indicator)
                if element:
                    detected_selectors['end_selector'] = indicator
                    break
            
            self._log_operation("_detect_selectors", f"Detected selectors: {detected_selectors}")
            return detected_selectors
            
        except Exception as e:
            self._log_operation("_detect_selectors", f"Selector detection failed: {str(e)}", "error")
            return {}
    
    async def _perform_scroll(self, page, config: Dict[str, Any], scroll_num: int) -> Dict[str, Any]:
        """Perform a single scroll operation."""
        try:
            scroll_container = config.get('scroll_container', 'body')
            scroll_step = config.get('scroll_step', 'window.innerHeight')
            smooth_scroll = config.get('smooth_scroll', False)
            custom_function = config.get('custom_scroll_function')
            
            if custom_function:
                # Use custom scroll function
                await page.evaluate(custom_function)
            else:
                # Use default scroll behavior
                if smooth_scroll:
                    await page.evaluate(f'''
                        const container = document.querySelector("{scroll_container}") || document.body;
                        const scrollHeight = container.scrollHeight;
                        const currentScroll = container.scrollTop || window.pageYOffset;
                        const targetScroll = Math.min(currentScroll + {scroll_step}, scrollHeight);
                        
                        container.scrollTo({{
                            top: targetScroll,
                            behavior: 'smooth'
                        }});
                    ''')
                else:
                    await page.evaluate(f'''
                        const container = document.querySelector("{scroll_container}") || document.body;
                        const scrollHeight = container.scrollHeight;
                        const currentScroll = container.scrollTop || window.pageYOffset;
                        const targetScroll = Math.min(currentScroll + {scroll_step}, scrollHeight);
                        
                        if (container === document.body) {{
                            window.scrollTo(0, targetScroll);
                        }} else {{
                            container.scrollTop = targetScroll;
                        }}
                    ''')
            
            # Small delay to allow scroll to complete
            await asyncio.sleep(0.5)
            
            return {'success': True}
            
        except Exception as e:
            self._log_operation("_perform_scroll", f"Scroll operation failed: {str(e)}", "error")
            return {'success': False, 'error': str(e)}
    
    async def _wait_for_new_content(self, page, config: Dict[str, Any], item_selector: str) -> None:
        """Wait for new content to load after scrolling."""
        try:
            wait_delay = config.get('content_check_delay', 1000)
            loading_selector = config.get('loading_selector')
            
            # Wait for loading indicator to disappear if present
            if loading_selector:
                try:
                    await page.wait_for_selector(loading_selector, state='hidden', timeout=5000)
                except:
                    pass  # Loading indicator might not be present
            
            # Additional wait for content to stabilize
            await asyncio.sleep(wait_delay / 1000.0)
            
        except Exception as e:
            self._log_operation("_wait_for_new_content", f"Wait for new content failed: {str(e)}", "error")
    
    async def _get_item_count(self, page, item_selector: str) -> int:
        """Get the current count of items."""
        try:
            if not item_selector:
                return 0
            
            elements = await page.query_selector_all(item_selector)
            return len(elements)
            
        except Exception as e:
            self._log_operation("_get_item_count", f"Failed to get item count: {str(e)}", "error")
            return 0
    
    async def _is_pagination_complete(self, page, config: Dict[str, Any]) -> bool:
        """Check if pagination is complete."""
        try:
            end_selector = config.get('end_selector')
            if end_selector:
                element = await page.query_selector(end_selector)
                if element:
                    return await element.is_visible()
            
            return False
            
        except Exception as e:
            self._log_operation("_is_pagination_complete", f"Failed to check pagination completion: {str(e)}", "error")
            return False
    
    async def _is_at_bottom(self, page, config: Dict[str, Any]) -> bool:
        """Check if we've scrolled to the bottom."""
        try:
            scroll_container = config.get('scroll_container', 'body')
            
            at_bottom = await page.evaluate(f'''
                const container = document.querySelector("{scroll_container}") || document.body;
                const scrollTop = container.scrollTop || window.pageYOffset;
                const scrollHeight = container.scrollHeight;
                const clientHeight = container.clientHeight || window.innerHeight;
                
                return scrollTop + clientHeight >= scrollHeight - 100;
            ''')
            
            return at_bottom
            
        except Exception as e:
            self._log_operation("_is_at_bottom", f"Failed to check if at bottom: {str(e)}", "error")
            return False
    
    def add_load_callback(self, site: str, callback: Callable) -> None:
        """Add callback for when new content is loaded."""
        if site not in self._load_callbacks:
            self._load_callbacks[site] = []
        self._load_callbacks[site].append(callback)
    
    def add_complete_callback(self, site: str, callback: Callable) -> None:
        """Add callback for when pagination is complete."""
        if site not in self._complete_callbacks:
            self._complete_callbacks[site] = []
        self._complete_callbacks[site].append(callback)
    
    def add_error_callback(self, site: str, callback: Callable) -> None:
        """Add callback for pagination errors."""
        if site not in self._error_callbacks:
            self._error_callbacks[site] = []
        self._error_callbacks[site].append(callback)
    
    async def _call_load_callbacks(self, site: str, data: Dict[str, Any]) -> None:
        """Call load callbacks for site."""
        if site in self._load_callbacks:
            for callback in self._load_callbacks[site]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(site, data)
                    else:
                        callback(site, data)
                except Exception as e:
                    self._log_operation("_call_load_callbacks", f"Load callback failed for {site}: {str(e)}", "error")
    
    async def _call_complete_callbacks(self, site: str, data: Dict[str, Any]) -> None:
        """Call completion callbacks for site."""
        if site in self._complete_callbacks:
            for callback in self._complete_callbacks[site]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(site, data)
                    else:
                        callback(site, data)
                except Exception as e:
                    self._log_operation("_call_complete_callbacks", f"Complete callback failed for {site}: {str(e)}", "error")
    
    def get_supported_sites(self) -> List[str]:
        """Get list of supported sites."""
        return list(self._supported_sites)
    
    def get_site_config(self, site: str) -> Optional[Dict[str, Any]]:
        """Get infinite scroll configuration for a site."""
        return self._site_configs.get(site)
    
    def get_pagination_state(self, site: str) -> Optional[Dict[str, Any]]:
        """Get pagination state for a site."""
        if site not in self._pagination_states:
            return None
        
        state = self._pagination_states[site].copy()
        if 'start_time' in state and isinstance(state['start_time'], datetime):
            state['start_time'] = state['start_time'].isoformat()
        if 'last_scroll_time' in state and isinstance(state['last_scroll_time'], datetime):
            state['last_scroll_time'] = state['last_scroll_time'].isoformat()
        
        return state
    
    def reset_pagination_state(self, site: str) -> None:
        """Reset pagination state for a site."""
        if site in self._pagination_states:
            del self._pagination_states[site]
    
    async def cleanup(self) -> None:
        """Clean up shared infinite scroll pagination component."""
        try:
            # Clear all states and callbacks
            self._pagination_states.clear()
            self._load_callbacks.clear()
            self._complete_callbacks.clear()
            self._error_callbacks.clear()
            
            self._log_operation("cleanup", "Shared infinite scroll component cleaned up")
            
        except Exception as e:
            self._log_operation("cleanup", f"Shared infinite scroll cleanup failed: {str(e)}", "error")


# Factory function for easy component creation
def create_infinite_scroll_component() -> InfiniteScrollPaginationComponent:
    """Create a shared infinite scroll pagination component."""
    return InfiniteScrollPaginationComponent()


# Component metadata for discovery
COMPONENT_METADATA = {
    'id': 'shared_infinite_scroll',
    'name': 'Shared Infinite Scroll Pagination Component',
    'version': '1.0.0',
    'type': 'PAGINATION',
    'description': 'Reusable infinite scroll pagination for multiple sites',
    'supported_sites': ['twitter', 'facebook', 'instagram', 'reddit', 'linkedin', 'youtube', 'tiktok', 'pinterest', 'tumblr', 'medium'],
    'features': [
        'multi_site_support',
        'auto_selector_detection',
        'loading_detection',
        'end_detection',
        'callback_system',
        'custom_scroll_functions',
        'error_handling'
    ],
    'dependencies': [],
    'configuration_required': [],
    'optional_configuration': ['scroll_container', 'item_selector', 'loading_selector', 'end_selector', 'scroll_delay', 'max_scrolls']
}
