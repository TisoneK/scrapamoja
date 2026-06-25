"""
Pagination flow template for the modular site scraper template.

This module provides a template for implementing pagination functionality
with common pagination patterns and data collection strategies.
"""

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import asyncio
import re

from .base_flow import BaseTemplateFlow
from src.sites.base.component_interface import ComponentResult


class PaginationFlow(BaseTemplateFlow):
    """Pagination flow template with common pagination functionality."""
    
    def __init__(
        self,
        component_id: str = "pagination_flow",
        name: str = "Pagination Flow",
        version: str = "1.0.0",
        description: str = "Handles pagination with configurable pagination patterns",
        page: Any = None,
        selector_engine: Any = None
    ):
        """
        Initialize pagination flow.
        
        Args:
            component_id: Unique identifier for the flow
            name: Human-readable name for the flow
            version: Flow version
            description: Flow description
            page: Playwright page object
            selector_engine: Selector engine instance
        """
        super().__init__(
            component_id=component_id,
            name=name,
            version=version,
            description=description,
            flow_type="PAGINATION",
            page=page,
            selector_engine=selector_engine
        )
        
        # Pagination-specific configuration
        self._next_button_selector: str = "next_button"
        self._prev_button_selector: str = "prev_button"
        self._page_numbers_selector: str = "page_numbers"
        self._current_page_selector: str = "current_page"
        self._total_pages_selector: str = "total_pages"
        self._items_per_page_selector: str = "items_per_page"
        self._pagination_container_selector: str = "pagination_container"
        self._max_pages: int = 100
        self._page_delay_ms: int = 1000
        self._pagination_type: str = "button"  # button, infinite_scroll, load_more
        
        # Pagination state
        self._current_page: int = 1
        self._total_pages: Optional[int] = None
        self._items_per_page: Optional[int] = None
        self._collected_data: List[Dict[str, Any]] = []
    
    async def _execute_flow_logic(self, **kwargs) -> Dict[str, Any]:
        """
        Execute pagination flow logic.
        
        Args:
            **kwargs: Pagination parameters including 'max_pages', 'data_extractor', etc.
            
        Returns:
            Pagination execution result
        """
        try:
            # Extract pagination parameters
            max_pages = kwargs.get('max_pages', self._max_pages)
            data_extractor = kwargs.get('data_extractor')
            pagination_type = kwargs.get('pagination_type', self._pagination_type)
            
            # Initialize pagination state
            await self._initialize_pagination_state()
            
            # Collect data across pages
            pagination_result = await self._collect_paginated_data(
                max_pages, data_extractor, pagination_type
            )
            
            # Extract pagination metadata
            pagination_metadata = await self._extract_pagination_metadata()
            
            return {
                'success': True,
                'current_page': self._current_page,
                'total_pages': self._total_pages,
                'items_collected': len(self._collected_data),
                'data': self._collected_data,
                'pagination_result': pagination_result,
                'metadata': pagination_metadata,
                'timestamp': datetime.utcnow().isoformat(),
                'url': self._flow_state.current_url if self._flow_state else None
            }
            
        except Exception as e:
            self._log_operation("_execute_flow_logic", f"Pagination failed: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e),
                'current_page': self._current_page,
                'items_collected': len(self._collected_data),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _initialize_pagination_state(self) -> None:
        """Initialize pagination state by detecting current page and total pages."""
        try:
            # Detect current page
            self._current_page = await self._detect_current_page()
            
            # Detect total pages
            self._total_pages = await self._detect_total_pages()
            
            # Detect items per page
            self._items_per_page = await self._detect_items_per_page()
            
            self._log_operation(
                "_initialize_pagination_state",
                f"Pagination state initialized: page {self._current_page}/{self._total_pages}"
            )
            
        except Exception as e:
            self._log_operation("_initialize_pagination_state", f"Failed to initialize pagination: {str(e)}", "error")
    
    async def _collect_paginated_data(
        self,
        max_pages: int,
        data_extractor: Optional[Callable],
        pagination_type: str
    ) -> Dict[str, Any]:
        """
        Collect data across multiple pages.
        
        Args:
            max_pages: Maximum number of pages to collect
            data_extractor: Function to extract data from each page
            pagination_type: Type of pagination
            
        Returns:
            Pagination collection result
        """
        try:
            pages_collected = 0
            total_items = 0
            
            while pages_collected < max_pages:
                # Extract data from current page
                page_data = await self._extract_page_data(data_extractor)
                if page_data:
                    self._collected_data.extend(page_data)
                    total_items += len(page_data)
                
                pages_collected += 1
                
                # Check if we should continue
                if not await self._should_continue_pagination(pages_collected, max_pages):
                    break
                
                # Navigate to next page
                if pagination_type == "button":
                    if not await self._navigate_to_next_page():
                        break
                elif pagination_type == "infinite_scroll":
                    if not await self._handle_infinite_scroll():
                        break
                elif pagination_type == "load_more":
                    if not await self._handle_load_more():
                        break
                
                # Wait between pages
                await asyncio.sleep(self._page_delay_ms / 1000.0)
            
            return {
                'pages_collected': pages_collected,
                'total_items': total_items,
                'pagination_type': pagination_type
            }
            
        except Exception as e:
            self._log_operation("_collect_paginated_data", f"Data collection failed: {str(e)}", "error")
            raise
    
    async def _extract_page_data(self, data_extractor: Optional[Callable]) -> List[Dict[str, Any]]:
        """
        Extract data from the current page.
        
        Args:
            data_extractor: Function to extract data
            
        Returns:
            List of extracted data items
        """
        try:
            if data_extractor:
                if asyncio.iscoroutinefunction(data_extractor):
                    return await data_extractor(self._page)
                else:
                    return data_extractor(self._page)
            else:
                # Default extraction using selector engine
                if self._selector_engine:
                    return await self._selector_engine.extract_all(self._page, "page_items")
                else:
                    return []
                    
        except Exception as e:
            self._log_operation("_extract_page_data", f"Data extraction failed: {str(e)}", "error")
            return []
    
    async def _should_continue_pagination(self, pages_collected: int, max_pages: int) -> bool:
        """
        Check if pagination should continue.
        
        Args:
            pages_collected: Number of pages already collected
            max_pages: Maximum pages to collect
            
        Returns:
            True if should continue, False otherwise
        """
        # Check max pages limit
        if pages_collected >= max_pages:
            return False
        
        # Check if we've reached the last page
        if self._total_pages and self._current_page >= self._total_pages:
            return False
        
        # Check if next button is available (for button pagination)
        if self._pagination_type == "button":
            next_button = await self.wait_for_element(self._next_button_selector, timeout_ms=2000)
            if not next_button:
                return False
            
            # Check if next button is disabled
            if await next_button.is_disabled():
                return False
        
        return True
    
    async def _navigate_to_next_page(self) -> bool:
        """Navigate to the next page using button pagination."""
        try:
            next_button = await self.wait_for_element(self._next_button_selector, timeout_ms=5000)
            if not next_button:
                return False
            
            # Check if button is disabled
            if await next_button.is_disabled():
                self._log_operation("_navigate_to_next_page", "Next button is disabled")
                return False
            
            # Click next button
            await self.click_element(self._next_button_selector)
            
            # Wait for page to load
            await self.wait_for_page_load()
            
            # Update current page
            self._current_page += 1
            
            self._log_operation("_navigate_to_next_page", f"Navigated to page {self._current_page}")
            return True
            
        except Exception as e:
            self._log_operation("_navigate_to_next_page", f"Failed to navigate to next page: {str(e)}", "error")
            return False
    
    async def _handle_infinite_scroll(self) -> bool:
        """Handle infinite scroll pagination."""
        try:
            # Get current scroll height
            last_height = await self._page.evaluate("document.body.scrollHeight")
            
            # Scroll to bottom
            await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # Wait for new content to load
            await asyncio.sleep(2)
            
            # Check if new content loaded
            new_height = await self._page.evaluate("document.body.scrollHeight")
            
            if new_height > last_height:
                self._log_operation("_handle_infinite_scroll", "New content loaded via infinite scroll")
                return True
            else:
                self._log_operation("_handle_infinite_scroll", "No new content loaded")
                return False
                
        except Exception as e:
            self._log_operation("_handle_infinite_scroll", f"Infinite scroll failed: {str(e)}", "error")
            return False
    
    async def _handle_load_more(self) -> bool:
        """Handle load more button pagination."""
        try:
            load_more_button = await self.wait_for_element("load_more_button", timeout_ms=5000)
            if not load_more_button:
                return False
            
            # Check if button is disabled
            if await load_more_button.is_disabled():
                self._log_operation("_handle_load_more", "Load more button is disabled")
                return False
            
            # Click load more button
            await self.click_element("load_more_button")
            
            # Wait for new content to load
            await asyncio.sleep(2)
            
            self._log_operation("_handle_load_more", "Loaded more content")
            return True
            
        except Exception as e:
            self._log_operation("_handle_load_more", f"Load more failed: {str(e)}", "error")
            return False
    
    async def _detect_current_page(self) -> int:
        """Detect the current page number."""
        try:
            # Try current page selector
            current_page_element = await self.wait_for_element(self._current_page_selector, timeout_ms=2000)
            if current_page_element:
                page_text = await current_page_element.text_content()
                page_number = self._extract_page_number(page_text)
                if page_number:
                    return page_number
            
            # Try to extract from URL
            current_url = self._flow_state.current_url if self._flow_state else ""
            page_match = re.search(r'[?&]page=(\d+)', current_url)
            if page_match:
                return int(page_match.group(1))
            
            # Try to extract from page numbers
            page_numbers_element = await self.wait_for_element(self._page_numbers_selector, timeout_ms=2000)
            if page_numbers_element:
                page_numbers_text = await page_numbers_element.text_content()
                # Look for current page indicator (often bold or active class)
                current_page_match = re.search(r'(\d+)', page_numbers_text)
                if current_page_match:
                    return int(current_page_match.group(1))
            
            return 1  # Default to page 1
            
        except Exception as e:
            self._log_operation("_detect_current_page", f"Failed to detect current page: {str(e)}", "error")
            return 1
    
    async def _detect_total_pages(self) -> Optional[int]:
        """Detect the total number of pages."""
        try:
            # Try total pages selector
            total_pages_element = await self.wait_for_element(self._total_pages_selector, timeout_ms=2000)
            if total_pages_element:
                pages_text = await total_pages_element.text_content()
                page_number = self._extract_page_number(pages_text)
                if page_number:
                    return page_number
            
            # Try to extract from page numbers
            page_numbers_element = await self.wait_for_element(self._page_numbers_selector, timeout_ms=2000)
            if page_numbers_element:
                page_numbers_text = await page_numbers_element.text_content()
                # Extract all page numbers
                page_numbers = re.findall(r'\d+', page_numbers_text)
                if page_numbers:
                    return max(int(p) for p in page_numbers)
            
            return None
            
        except Exception as e:
            self._log_operation("_detect_total_pages", f"Failed to detect total pages: {str(e)}", "error")
            return None
    
    async def _detect_items_per_page(self) -> Optional[int]:
        """Detect the number of items per page."""
        try:
            # Try items per page selector
            items_per_page_element = await self.wait_for_element(self._items_per_page_selector, timeout_ms=2000)
            if items_per_page_element:
                items_text = await items_per_page_element.text_content()
                items_number = self._extract_page_number(items_text)
                if items_number:
                    return items_number
            
            # Count items on current page
            if self._selector_engine:
                items = await self._selector_engine.extract_all(self._page, "page_items")
                return len(items)
            
            return None
            
        except Exception as e:
            self._log_operation("_detect_items_per_page", f"Failed to detect items per page: {str(e)}", "error")
            return None
    
    def _extract_page_number(self, text: str) -> Optional[int]:
        """Extract page number from text."""
        try:
            # Look for page number patterns
            patterns = [
                r'page\s*(\d+)',
                r'(\d+)\s*of\s*\d+',
                r'(\d+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return int(match.group(1))
            
            return None
            
        except Exception:
            return None
    
    async def _extract_pagination_metadata(self) -> Dict[str, Any]:
        """Extract metadata from pagination."""
        try:
            metadata = {
                'current_page': self._current_page,
                'total_pages': self._total_pages,
                'items_per_page': self._items_per_page,
                'pagination_type': self._pagination_type,
                'current_url': self._flow_state.current_url if self._flow_state else None
            }
            
            # Check for pagination controls
            next_button = await self.wait_for_element(self._next_button_selector, timeout_ms=1000)
            metadata['has_next_button'] = next_button is not None
            
            prev_button = await self.wait_for_element(self._prev_button_selector, timeout_ms=1000)
            metadata['has_prev_button'] = prev_button is not None
            
            # Check if next button is disabled
            if next_button:
                metadata['next_button_disabled'] = await next_button.is_disabled()
            
            return metadata
            
        except Exception as e:
            self._log_operation("_extract_pagination_metadata", f"Failed to extract metadata: {str(e)}", "error")
            return {}
    
    async def navigate_to_page(self, page_number: int) -> bool:
        """
        Navigate to a specific page number.
        
        Args:
            page_number: Page number to navigate to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Try clicking on page number
            page_numbers_element = await self.wait_for_element(self._page_numbers_selector, timeout_ms=5000)
            if page_numbers_element:
                # Look for the specific page number link
                page_links = await page_numbers_element.query_selector_all('a')
                for link in page_links:
                    link_text = await link.text_content()
                    if str(page_number) in link_text:
                        await link.click()
                        await self.wait_for_page_load()
                        self._current_page = page_number
                        return True
            
            # Try URL-based navigation
            current_url = self._flow_state.current_url if self._flow_state else ""
            if '?' in current_url:
                new_url = re.sub(r'[?&]page=\d+', f'page={page_number}', current_url)
            else:
                new_url = f"{current_url}?page={page_number}"
            
            await self.navigate_to_url(new_url)
            await self.wait_for_page_load()
            self._current_page = page_number
            
            return True
            
        except Exception as e:
            self._log_operation("navigate_to_page", f"Failed to navigate to page {page_number}: {str(e)}", "error")
            return False
    
    def configure_pagination(
        self,
        next_button_selector: Optional[str] = None,
        prev_button_selector: Optional[str] = None,
        page_numbers_selector: Optional[str] = None,
        current_page_selector: Optional[str] = None,
        total_pages_selector: Optional[str] = None,
        items_per_page_selector: Optional[str] = None,
        pagination_container_selector: Optional[str] = None,
        max_pages: Optional[int] = None,
        page_delay_ms: Optional[int] = None,
        pagination_type: Optional[str] = None
    ) -> None:
        """
        Configure pagination-specific parameters.
        
        Args:
            next_button_selector: Selector for next button
            prev_button_selector: Selector for previous button
            page_numbers_selector: Selector for page numbers
            current_page_selector: Selector for current page
            total_pages_selector: Selector for total pages
            items_per_page_selector: Selector for items per page
            pagination_container_selector: Selector for pagination container
            max_pages: Maximum pages to collect
            page_delay_ms: Delay between pages
            pagination_type: Type of pagination
        """
        if next_button_selector is not None:
            self._next_button_selector = next_button_selector
        if prev_button_selector is not None:
            self._prev_button_selector = prev_button_selector
        if page_numbers_selector is not None:
            self._page_numbers_selector = page_numbers_selector
        if current_page_selector is not None:
            self._current_page_selector = current_page_selector
        if total_pages_selector is not None:
            self._total_pages_selector = total_pages_selector
        if items_per_page_selector is not None:
            self._items_per_page_selector = items_per_page_selector
        if pagination_container_selector is not None:
            self._pagination_container_selector = pagination_container_selector
        if max_pages is not None:
            self._max_pages = max_pages
        if page_delay_ms is not None:
            self._page_delay_ms = page_delay_ms
        if pagination_type is not None:
            self._pagination_type = pagination_type
    
    def get_pagination_configuration(self) -> Dict[str, Any]:
        """Get current pagination configuration."""
        return {
            'next_button_selector': self._next_button_selector,
            'prev_button_selector': self._prev_button_selector,
            'page_numbers_selector': self._page_numbers_selector,
            'current_page_selector': self._current_page_selector,
            'total_pages_selector': self._total_pages_selector,
            'items_per_page_selector': self._items_per_page_selector,
            'pagination_container_selector': self._pagination_container_selector,
            'max_pages': self._max_pages,
            'page_delay_ms': self._page_delay_ms,
            'pagination_type': self._pagination_type,
            'current_page': self._current_page,
            'total_pages': self._total_pages,
            'items_per_page': self._items_per_page,
            **self.get_configuration()
        }
