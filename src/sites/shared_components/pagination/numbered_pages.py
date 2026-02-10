"""
Shared numbered pages pagination component for reusable pagination across sites.

This module provides numbered pages pagination functionality that can be easily
integrated into any site scraper with traditional page number navigation.
"""

from typing import Dict, Any, Optional, List, Callable, Union, Tuple
from datetime import datetime, timedelta
import asyncio
import json
import re

from src.sites.base.component_interface import BaseComponent, ComponentContext, ComponentResult


class NumberedPagesPaginationComponent(BaseComponent):
    """Shared numbered pages pagination component for cross-site usage."""
    
    def __init__(
        self,
        component_id: str = "shared_numbered_pages",
        name: str = "Shared Numbered Pages Pagination Component",
        version: str = "1.0.0",
        description: str = "Reusable numbered pages pagination for multiple sites"
    ):
        """
        Initialize shared numbered pages pagination component.
        
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
        
        # Numbered pages configurations for different sites
        self._site_configs: Dict[str, Dict[str, Any]] = {}
        
        # Pagination state per site
        self._pagination_states: Dict[str, Dict[str, Any]] = {}
        
        # Callback handlers
        self._page_callbacks: Dict[str, List[Callable]] = {}
        self._complete_callbacks: Dict[str, List[Callable]] = {}
        self._error_callbacks: Dict[str, List[Callable]] = {}
        
        # Component metadata
        self._supported_sites = [
            'google', 'bing', 'yahoo', 'duckduckgo', 'stackoverflow',
            'github', 'reddit', 'amazon', 'ebay', 'craigslist'
        ]
        
        # Common pagination patterns
        self._page_link_patterns = [
            'a[href*="page="]', 'a[href*="/page/"]', 'a[href*="?p="]',
            'a[href*="&p="]', 'a[aria-label*="page"]', 'a[class*="page"]'
        ]
        
        self._next_button_patterns = [
            'a[href*="next"]', 'a[aria-label*="next"]', 'a[class*="next"]',
            'button[aria-label*="next"]', 'button[class*="next"]', '.next'
        ]
        
        self._prev_button_patterns = [
            'a[href*="prev"]', 'a[aria-label*="prev"]', 'a[class*="prev"]',
            'button[aria-label*="prev"]', 'button[class*="prev"]', '.prev'
        ]
    
    async def initialize(self, context: ComponentContext) -> bool:
        """
        Initialize shared numbered pages pagination component.
        
        Args:
            context: Component context
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load numbered pages configurations from context
            config = context.config_manager.get_config(context.environment) if context.config_manager else {}
            
            # Initialize default site configurations
            await self._initialize_default_configs()
            
            # Load custom site configurations
            custom_configs = config.get('numbered_pages_site_configs', {})
            for site, site_config in custom_configs.items():
                self.register_site(site, site_config)
            
            self._log_operation("initialize", f"Shared numbered pages component initialized with {len(self._site_configs)} site configurations")
            return True
            
        except Exception as e:
            self._log_operation("initialize", f"Shared numbered pages initialization failed: {str(e)}", "error")
            return False
    
    async def execute(self, **kwargs) -> ComponentResult:
        """
        Execute numbered pages pagination for a specific site.
        
        Args:
            **kwargs: Pagination parameters including 'site', 'page', 'max_pages', etc.
            
        Returns:
            Pagination result
        """
        try:
            start_time = datetime.utcnow()
            
            # Extract parameters
            site = kwargs.get('site')
            page = kwargs.get('page')
            start_page = kwargs.get('start_page', 1)
            max_pages = kwargs.get('max_pages', 10)
            page_delay = kwargs.get('page_delay', 2000)
            auto_detect = kwargs.get('auto_detect', True)
            collect_items = kwargs.get('collect_items', True)
            item_selector = kwargs.get('item_selector')
            
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
            
            # Perform numbered pages pagination
            pagination_result = await self._numbered_pages_pagination(
                site, page, start_page, max_pages, page_delay, auto_detect, collect_items, item_selector
            )
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return ComponentResult(
                success=pagination_result['success'],
                data={
                    'site': site,
                    'start_page': start_page,
                    'max_pages': max_pages,
                    'pages_visited': pagination_result['pages_visited'],
                    'items_collected': pagination_result['items_collected'],
                    'is_complete': pagination_result['is_complete'],
                    **pagination_result
                },
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self._log_operation("execute", f"Numbered pages pagination failed: {str(e)}", "error")
            return ComponentResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    def register_site(self, site: str, config: Dict[str, Any]) -> None:
        """
        Register numbered pages configuration for a site.
        
        Args:
            site: Site identifier
            config: Numbered pages configuration
        """
        self._site_configs[site] = {
            'page_url_pattern': config.get('page_url_pattern'),
            'page_param': config.get('page_param', 'page'),
            'next_button_selector': config.get('next_button_selector'),
            'prev_button_selector': config.get('prev_button_selector'),
            'page_links_selector': config.get('page_links_selector'),
            'current_page_selector': config.get('current_page_selector'),
            'item_selector': config.get('item_selector'),
            'max_pages': config.get('max_pages', 10),
            'page_delay': config.get('page_delay', 2000),
            'wait_for_selector': config.get('wait_for_selector'),
            'url_based': config.get('url_based', True),
            'button_based': config.get('button_based', False)
        }
        
        self._log_operation("register_site", f"Registered numbered pages configuration for site: {site}")
    
    async def _initialize_default_configs(self) -> None:
        """Initialize default numbered pages configurations for common sites."""
        default_configs = {
            'google': {
                'page_url_pattern': 'https://www.google.com/search?q={query}&start={offset}',
                'page_param': 'start',
                'next_button_selector': 'a#pnnext',
                'item_selector': 'div.g',
                'max_pages': 10,
                'url_based': True
            },
            'bing': {
                'page_url_pattern': 'https://www.bing.com/search?q={query}&first={offset}',
                'page_param': 'first',
                'next_button_selector': 'a.sb_pagN',
                'item_selector': 'li.b_algo',
                'max_pages': 10,
                'url_based': True
            },
            'stackoverflow': {
                'page_url_pattern': 'https://stackoverflow.com/questions/tagged/{tag}?page={page}',
                'page_param': 'page',
                'next_button_selector': 'a[rel="next"]',
                'item_selector': 'div.s-post-layout',
                'max_pages': 25,
                'url_based': True
            },
            'github': {
                'page_url_pattern': 'https://github.com/search?q={query}&p={page}',
                'page_param': 'p',
                'next_button_selector': 'a.next_page',
                'item_selector': 'div.repo-list-item',
                'max_pages': 100,
                'url_based': True
            },
            'reddit': {
                'page_url_pattern': 'https://www.reddit.com/r/{subreddit}/hot/?count={offset}',
                'page_param': 'count',
                'next_button_selector': 'button[aria-label="Next page"]',
                'item_selector': 'div[data-testid="post-container"]',
                'max_pages': 40,
                'url_based': True
            },
            'amazon': {
                'page_url_pattern': 'https://www.amazon.com/s?k={query}&page={page}',
                'page_param': 'page',
                'next_button_selector': 'a.s-pagination-next',
                'item_selector': 'div[data-component-type="s-search-result"]',
                'max_pages': 20,
                'url_based': True
            },
            'ebay': {
                'page_url_pattern': 'https://www.ebay.com/sch/i.html?_nkw={query}&_pgn={page}',
                'page_param': '_pgn',
                'next_button_selector': 'a.glyphicon-next',
                'item_selector': 'div.s-item',
                'max_pages': 50,
                'url_based': True
            }
        }
        
        for site, config in default_configs.items():
            if site not in self._site_configs:
                self._site_configs[site] = config
    
    def _initialize_pagination_state(self, site: str) -> None:
        """Initialize pagination state for a site."""
        if site not in self._pagination_states:
            self._pagination_states[site] = {
                'pages_visited': 0,
                'items_collected': 0,
                'current_page': 1,
                'is_complete': False,
                'start_time': datetime.utcnow(),
                'last_page_time': None,
                'error_count': 0,
                'page_urls': []
            }
    
    async def _numbered_pages_pagination(
        self, site: str, page, start_page: int, max_pages: int, 
        page_delay: int, auto_detect: bool, collect_items: bool, item_selector: str
    ) -> Dict[str, Any]:
        """Perform numbered pages pagination."""
        try:
            config = self._site_configs[site]
            state = self._pagination_states[site]
            
            # Auto-detect selectors if not provided
            if auto_detect:
                detected_selectors = await self._detect_pagination_selectors(page)
                config['next_button_selector'] = config.get('next_button_selector') or detected_selectors.get('next_button')
                config['item_selector'] = config.get('item_selector') or detected_selectors.get('item_selector')
                config['current_page_selector'] = config.get('current_page_selector') or detected_selectors.get('current_page')
            
            item_selector = item_selector or config.get('item_selector')
            
            self._log_operation("_numbered_pages_pagination", f"Starting numbered pages pagination for {site} from page {start_page}")
            
            # Visit pages
            pages_visited = 0
            total_items = 0
            
            for page_num in range(start_page, start_page + max_pages):
                # Navigate to page
                navigation_result = await self._navigate_to_page(site, page, page_num, config)
                if not navigation_result['success']:
                    state['error_count'] += 1
                    if state['error_count'] >= 3:
                        break
                    continue
                
                pages_visited += 1
                state['pages_visited'] = pages_visited
                state['current_page'] = page_num
                state['last_page_time'] = datetime.utcnow()
                state['page_urls'].append(page.url)
                
                # Wait for page to load
                if config.get('wait_for_selector'):
                    try:
                        await page.wait_for_selector(config['wait_for_selector'], timeout=10000)
                    except:
                        pass
                
                # Collect items from current page
                if collect_items and item_selector:
                    page_items = await self._collect_page_items(page, item_selector)
                    total_items += page_items
                    state['items_collected'] = total_items
                
                # Call page callbacks
                await self._call_page_callbacks(site, {
                    'page_number': page_num,
                    'page_url': page.url,
                    'items_on_page': page_items if collect_items else 0,
                    'total_items': total_items,
                    'pages_visited': pages_visited
                })
                
                # Check if pagination is complete
                if await self._is_pagination_complete(page, config):
                    state['is_complete'] = True
                    self._log_operation("_numbered_pages_pagination", f"Pagination complete for {site} after {pages_visited} pages")
                    break
                
                # Check if next page is available
                if not await self._has_next_page(page, config):
                    state['is_complete'] = True
                    break
                
                # Wait before next page
                await asyncio.sleep(page_delay / 1000.0)
            
            # Call completion callbacks
            if state['is_complete']:
                await self._call_complete_callbacks(site, state)
            
            return {
                'success': True,
                'pages_visited': pages_visited,
                'items_collected': total_items,
                'is_complete': state['is_complete'],
                'error_count': state['error_count'],
                'page_urls': state['page_urls'],
                'execution_time_seconds': (datetime.utcnow() - state['start_time']).total_seconds()
            }
            
        except Exception as e:
            self._log_operation("_numbered_pages_pagination", f"Numbered pages pagination failed for {site}: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e),
                'pages_visited': self._pagination_states.get(site, {}).get('pages_visited', 0),
                'items_collected': self._pagination_states.get(site, {}).get('items_collected', 0)
            }
    
    async def _detect_pagination_selectors(self, page) -> Dict[str, str]:
        """Auto-detect pagination selectors."""
        try:
            detected_selectors = {}
            
            # Detect next button
            for pattern in self._next_button_patterns:
                element = await page.query_selector(pattern)
                if element:
                    detected_selectors['next_button'] = pattern
                    break
            
            # Detect page links
            for pattern in self._page_link_patterns:
                elements = await page.query_selector_all(pattern)
                if len(elements) >= 2:  # Need at least 2 page links
                    detected_selectors['page_links'] = pattern
                    break
            
            # Detect current page indicator
            current_page_patterns = [
                '.current', '.active', '[aria-current="page"]', 
                '.selected', '.page-current', 'span.current'
            ]
            for pattern in current_page_patterns:
                element = await page.query_selector(pattern)
                if element:
                    detected_selectors['current_page'] = pattern
                    break
            
            # Detect item selector
            item_patterns = [
                'div[class*="item"]', 'div[class*="result"]', 'div[class*="post"]',
                'li[class*="item"]', 'li[class*="result"]', 'article'
            ]
            for pattern in item_patterns:
                elements = await page.query_selector_all(pattern)
                if len(elements) >= 3:
                    detected_selectors['item_selector'] = pattern
                    break
            
            self._log_operation("_detect_pagination_selectors", f"Detected selectors: {detected_selectors}")
            return detected_selectors
            
        except Exception as e:
            self._log_operation("_detect_pagination_selectors", f"Pagination selector detection failed: {str(e)}", "error")
            return {}
    
    async def _navigate_to_page(self, site: str, page, page_num: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Navigate to a specific page."""
        try:
            if config.get('url_based') and config.get('page_url_pattern'):
                # URL-based pagination
                url_pattern = config['page_url_pattern']
                page_param = config.get('page_param', 'page')
                
                # Replace placeholders in URL pattern
                if '{page}' in url_pattern:
                    page_url = url_pattern.format(page=page_num)
                elif '{offset}' in url_pattern:
                    offset = (page_num - 1) * 10  # Default offset calculation
                    page_url = url_pattern.format(offset=offset)
                else:
                    # Append page parameter to current URL
                    current_url = page.url
                    separator = '&' if '?' in current_url else '?'
                    page_url = f"{current_url}{separator}{page_param}={page_num}"
                
                await page.goto(page_url)
                
            elif config.get('button_based'):
                # Button-based pagination (for first page, already there)
                if page_num > 1:
                    # Click next button multiple times
                    for _ in range(page_num - 1):
                        next_button = await page.query_selector(config['next_button_selector'])
                        if next_button:
                            await next_button.click()
                            await asyncio.sleep(1)
                        else:
                            return {'success': False, 'error': 'Next button not found'}
            
            return {'success': True}
            
        except Exception as e:
            self._log_operation("_navigate_to_page", f"Failed to navigate to page {page_num}: {str(e)}", "error")
            return {'success': False, 'error': str(e)}
    
    async def _collect_page_items(self, page, item_selector: str) -> int:
        """Collect items from the current page."""
        try:
            if not item_selector:
                return 0
            
            elements = await page.query_selector_all(item_selector)
            return len(elements)
            
        except Exception as e:
            self._log_operation("_collect_page_items", f"Failed to collect page items: {str(e)}", "error")
            return 0
    
    async def _is_pagination_complete(self, page, config: Dict[str, Any]) -> bool:
        """Check if pagination is complete."""
        try:
            # Check for end indicators
            end_indicators = [
                '.no-results', '.no-more', '.end-of-results',
                '[data-end]', '.pagination-end'
            ]
            
            for indicator in end_indicators:
                element = await page.query_selector(indicator)
                if element and await element.is_visible():
                    return True
            
            # Check if next button is disabled
            next_selector = config.get('next_button_selector')
            if next_selector:
                next_button = await page.query_selector(next_selector)
                if next_button:
                    # Check for disabled attributes
                    is_disabled = await next_button.evaluate('el => el.disabled || el.getAttribute("aria-disabled") === "true"')
                    if is_disabled:
                        return True
            
            return False
            
        except Exception as e:
            self._log_operation("_is_pagination_complete", f"Failed to check pagination completion: {str(e)}", "error")
            return False
    
    async def _has_next_page(self, page, config: Dict[str, Any]) -> bool:
        """Check if there's a next page available."""
        try:
            next_selector = config.get('next_button_selector')
            if next_selector:
                next_button = await page.query_selector(next_selector)
                if next_button:
                    # Check if button is enabled and visible
                    is_visible = await next_button.is_visible()
                    is_disabled = await next_button.evaluate('el => el.disabled || el.getAttribute("aria-disabled") === "true"')
                    return is_visible and not is_disabled
            
            return False
            
        except Exception as e:
            self._log_operation("_has_next_page", f"Failed to check for next page: {str(e)}", "error")
            return False
    
    def add_page_callback(self, site: str, callback: Callable) -> None:
        """Add callback for when a new page is visited."""
        if site not in self._page_callbacks:
            self._page_callbacks[site] = []
        self._page_callbacks[site].append(callback)
    
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
    
    async def _call_page_callbacks(self, site: str, data: Dict[str, Any]) -> None:
        """Call page callbacks for site."""
        if site in self._page_callbacks:
            for callback in self._page_callbacks[site]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(site, data)
                    else:
                        callback(site, data)
                except Exception as e:
                    self._log_operation("_call_page_callbacks", f"Page callback failed for {site}: {str(e)}", "error")
    
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
        """Get numbered pages configuration for a site."""
        return self._site_configs.get(site)
    
    def get_pagination_state(self, site: str) -> Optional[Dict[str, Any]]:
        """Get pagination state for a site."""
        if site not in self._pagination_states:
            return None
        
        state = self._pagination_states[site].copy()
        if 'start_time' in state and isinstance(state['start_time'], datetime):
            state['start_time'] = state['start_time'].isoformat()
        if 'last_page_time' in state and isinstance(state['last_page_time'], datetime):
            state['last_page_time'] = state['last_page_time'].isoformat()
        
        return state
    
    def reset_pagination_state(self, site: str) -> None:
        """Reset pagination state for a site."""
        if site in self._pagination_states:
            del self._pagination_states[site]
    
    async def cleanup(self) -> None:
        """Clean up shared numbered pages pagination component."""
        try:
            # Clear all states and callbacks
            self._pagination_states.clear()
            self._page_callbacks.clear()
            self._complete_callbacks.clear()
            self._error_callbacks.clear()
            
            self._log_operation("cleanup", "Shared numbered pages component cleaned up")
            
        except Exception as e:
            self._log_operation("cleanup", f"Shared numbered pages cleanup failed: {str(e)}", "error")


# Factory function for easy component creation
def create_numbered_pages_component() -> NumberedPagesPaginationComponent:
    """Create a shared numbered pages pagination component."""
    return NumberedPagesPaginationComponent()


# Component metadata for discovery
COMPONENT_METADATA = {
    'id': 'shared_numbered_pages',
    'name': 'Shared Numbered Pages Pagination Component',
    'version': '1.0.0',
    'type': 'PAGINATION',
    'description': 'Reusable numbered pages pagination for multiple sites',
    'supported_sites': ['google', 'bing', 'yahoo', 'duckduckgo', 'stackoverflow', 'github', 'reddit', 'amazon', 'ebay', 'craigslist'],
    'features': [
        'multi_site_support',
        'auto_selector_detection',
        'url_based_pagination',
        'button_based_pagination',
        'callback_system',
        'error_handling',
        'page_tracking'
    ],
    'dependencies': [],
    'configuration_required': [],
    'optional_configuration': ['page_url_pattern', 'page_param', 'next_button_selector', 'item_selector', 'max_pages']
}
