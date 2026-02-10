"""
Search flow template for the modular site scraper template.

This module provides a template for implementing search functionality
with common search patterns and error handling.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

from .base_flow import BaseTemplateFlow
from src.sites.base.component_interface import ComponentResult


class SearchFlow(BaseTemplateFlow):
    """Search flow template with common search functionality."""
    
    def __init__(
        self,
        component_id: str = "search_flow",
        name: str = "Search Flow",
        version: str = "1.0.0",
        description: str = "Handles search functionality with configurable search patterns",
        page: Any = None,
        selector_engine: Any = None
    ):
        """
        Initialize search flow.
        
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
            flow_type="SEARCH",
            page=page,
            selector_engine=selector_engine
        )
        
        # Search-specific configuration
        self._search_input_selector: str = "search_input"
        self._search_button_selector: str = "search_button"
        self._search_results_selector: str = "search_results"
        self._no_results_selector: str = "no_results"
        self._loading_indicator_selector: str = "loading_indicator"
        self._max_results: int = 50
        self._search_delay_ms: int = 500
        self._clear_search_before: bool = True
        
        # Configure default success and error indicators
        self._success_indicators = [
            "search_results",
            "results",
            "items"
        ]
        
        self._error_indicators = [
            "no_results",
            "error",
            "not_found"
        ]
    
    async def _execute_flow_logic(self, **kwargs) -> Dict[str, Any]:
        """
        Execute search flow logic.
        
        Args:
            **kwargs: Search parameters including 'query', 'max_results', etc.
            
        Returns:
            Search execution result
        """
        try:
            # Extract search parameters
            query = kwargs.get('query', '')
            max_results = kwargs.get('max_results', self._max_results)
            search_url = kwargs.get('search_url')
            
            if not query:
                raise ValueError("Search query is required")
            
            # Navigate to search page if URL provided
            if search_url:
                await self.navigate_to_url(search_url)
                await self.wait_for_page_load()
            
            # Perform search
            search_result = await self._perform_search(query, max_results)
            
            # Wait for results to load
            await self._wait_for_search_results()
            
            # Extract search metadata
            search_metadata = await self._extract_search_metadata()
            
            return {
                'success': True,
                'query': query,
                'max_results': max_results,
                'search_result': search_result,
                'metadata': search_metadata,
                'timestamp': datetime.utcnow().isoformat(),
                'url': self._flow_state.current_url if self._flow_state else None
            }
            
        except Exception as e:
            self._log_operation("_execute_flow_logic", f"Search failed: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e),
                'query': kwargs.get('query', ''),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _perform_search(self, query: str, max_results: int) -> Dict[str, Any]:
        """
        Perform the actual search operation.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            Search operation result
        """
        try:
            # Clear search input if configured
            if self._clear_search_before:
                await self._clear_search_input()
            
            # Fill search input
            if not await self.fill_form(self._search_input_selector, query):
                raise Exception("Failed to fill search input")
            
            # Wait a moment to simulate human typing
            await asyncio.sleep(self._search_delay_ms / 1000.0)
            
            # Submit search (either by clicking button or pressing Enter)
            search_submitted = await self._submit_search()
            
            if not search_submitted:
                raise Exception("Failed to submit search")
            
            return {
                'query_submitted': True,
                'query': query,
                'max_results': max_results
            }
            
        except Exception as e:
            self._log_operation("_perform_search", f"Search operation failed: {str(e)}", "error")
            raise
    
    async def _clear_search_input(self) -> bool:
        """Clear the search input field."""
        try:
            search_input = await self.wait_for_element(self._search_input_selector)
            if search_input:
                await search_input.clear()
                self._log_operation("_clear_search_input", "Search input cleared")
                return True
            return False
            
        except Exception as e:
            self._log_operation("_clear_search_input", f"Failed to clear search input: {str(e)}", "error")
            return False
    
    async def _submit_search(self) -> bool:
        """Submit the search form."""
        try:
            # Try clicking search button first
            search_button = await self.wait_for_element(self._search_button_selector, timeout_ms=5000)
            if search_button:
                await self.click_element(self._search_button_selector)
                self._log_operation("_submit_search", "Search submitted via button click")
                return True
            
            # Fallback: press Enter in search input
            search_input = await self.wait_for_element(self._search_input_selector)
            if search_input:
                await search_input.press('Enter')
                self._log_operation("_submit_search", "Search submitted via Enter key")
                return True
            
            return False
            
        except Exception as e:
            self._log_operation("_submit_search", f"Failed to submit search: {str(e)}", "error")
            return False
    
    async def _wait_for_search_results(self, timeout_ms: int = 30000) -> bool:
        """
        Wait for search results to load.
        
        Args:
            timeout_ms: Timeout in milliseconds
            
        Returns:
            True if results loaded, False otherwise
        """
        try:
            # Wait for loading indicator to disappear (if present)
            if self._loading_indicator_selector:
                try:
                    loading_indicator = await self.wait_for_element(self._loading_indicator_selector, timeout_ms=2000)
                    if loading_indicator:
                        # Wait for loading indicator to become hidden
                        await self._page.wait_for_selector(
                            self._loading_indicator_selector,
                            state='hidden',
                            timeout=timeout_ms
                        )
                except:
                    # Loading indicator might not be present, continue
                    pass
            
            # Wait for search results or no results
            await self._page.wait_for_function(
                f"""() => {{
                    const results = document.querySelector('{self._search_results_selector}');
                    const noResults = document.querySelector('{self._no_results_selector}');
                    return results || noResults;
                }}""",
                timeout=timeout_ms
            )
            
            self._log_operation("_wait_for_search_results", "Search results loaded")
            return True
            
        except Exception as e:
            self._log_operation("_wait_for_search_results", f"Failed to wait for results: {str(e)}", "error")
            return False
    
    async def _extract_search_metadata(self) -> Dict[str, Any]:
        """Extract metadata from search results page."""
        try:
            metadata = {}
            
            # Check if results exist
            results_element = await self.wait_for_element(self._search_results_selector, timeout_ms=2000)
            metadata['has_results'] = results_element is not None
            
            # Check for no results message
            no_results_element = await self.wait_for_element(self._no_results_selector, timeout_ms=2000)
            metadata['has_no_results'] = no_results_element is not None
            
            # Extract result count if available
            try:
                count_element = await self.wait_for_element("result_count", timeout_ms=2000)
                if count_element:
                    count_text = await count_element.text_content()
                    # Try to extract number from text
                    import re
                    numbers = re.findall(r'\d+', count_text)
                    if numbers:
                        metadata['result_count'] = int(numbers[0])
            except:
                pass
            
            # Extract current URL
            metadata['current_url'] = self._flow_state.current_url if self._flow_state else None
            
            # Extract page title
            metadata['page_title'] = await self._page.title()
            
            return metadata
            
        except Exception as e:
            self._log_operation("_extract_search_metadata", f"Failed to extract metadata: {str(e)}", "error")
            return {}
    
    async def get_search_results(self, selector_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get search results using selector engine.
        
        Args:
            selector_name: Name of the selector for results (uses default if None)
            
        Returns:
            List of search results
        """
        try:
            selector = selector_name or self._search_results_selector
            
            if not self._selector_engine:
                self._log_operation("get_search_results", "Selector engine not available", "error")
                return []
            
            results = await self._selector_engine.extract_all(self._page, selector)
            
            self._log_operation("get_search_results", f"Extracted {len(results)} search results")
            return results
            
        except Exception as e:
            self._log_operation("get_search_results", f"Failed to get results: {str(e)}", "error")
            return []
    
    async def refine_search(self, additional_query: str) -> bool:
        """
        Refine the current search with additional terms.
        
        Args:
            additional_query: Additional search terms
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current search input value
            search_input = await self.wait_for_element(self._search_input_selector)
            if not search_input:
                return False
            
            current_value = await search_input.input_value()
            
            # Append additional query
            new_query = f"{current_value} {additional_query}".strip()
            
            # Clear and fill with new query
            await search_input.clear()
            await search_input.fill(new_query)
            
            # Submit search
            return await self._submit_search()
            
        except Exception as e:
            self._log_operation("refine_search", f"Failed to refine search: {str(e)}", "error")
            return False
    
    async def clear_search(self) -> bool:
        """Clear the current search and return to initial state."""
        try:
            # Clear search input
            await self._clear_search_input()
            
            # Optionally click a clear button if available
            clear_button = await self.wait_for_element("clear_button", timeout_ms=2000)
            if clear_button:
                await self.click_element("clear_button")
            
            self._log_operation("clear_search", "Search cleared")
            return True
            
        except Exception as e:
            self._log_operation("clear_search", f"Failed to clear search: {str(e)}", "error")
            return False
    
    def configure_search(
        self,
        search_input_selector: Optional[str] = None,
        search_button_selector: Optional[str] = None,
        search_results_selector: Optional[str] = None,
        no_results_selector: Optional[str] = None,
        loading_indicator_selector: Optional[str] = None,
        max_results: Optional[int] = None,
        search_delay_ms: Optional[int] = None,
        clear_search_before: Optional[bool] = None
    ) -> None:
        """
        Configure search-specific parameters.
        
        Args:
            search_input_selector: Selector for search input
            search_button_selector: Selector for search button
            search_results_selector: Selector for search results
            no_results_selector: Selector for no results message
            loading_indicator_selector: Selector for loading indicator
            max_results: Maximum number of results
            search_delay_ms: Delay before submitting search
            clear_search_before: Whether to clear search input before new search
        """
        if search_input_selector is not None:
            self._search_input_selector = search_input_selector
        if search_button_selector is not None:
            self._search_button_selector = search_button_selector
        if search_results_selector is not None:
            self._search_results_selector = search_results_selector
        if no_results_selector is not None:
            self._no_results_selector = no_results_selector
        if loading_indicator_selector is not None:
            self._loading_indicator_selector = loading_indicator_selector
        if max_results is not None:
            self._max_results = max_results
        if search_delay_ms is not None:
            self._search_delay_ms = search_delay_ms
        if clear_search_before is not None:
            self._clear_search_before = clear_search_before
    
    def get_search_configuration(self) -> Dict[str, Any]:
        """Get current search configuration."""
        return {
            'search_input_selector': self._search_input_selector,
            'search_button_selector': self._search_button_selector,
            'search_results_selector': self._search_results_selector,
            'no_results_selector': self._no_results_selector,
            'loading_indicator_selector': self._loading_indicator_selector,
            'max_results': self._max_results,
            'search_delay_ms': self._search_delay_ms,
            'clear_search_before': self._clear_search_before,
            **self.get_configuration()
        }
