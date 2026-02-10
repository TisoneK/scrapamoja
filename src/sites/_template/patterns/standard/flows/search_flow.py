"""
Search flow for standard pattern.

Handles complex search operations including advanced filtering,
result pagination, and search result extraction.
"""

from src.sites.base.flow import BaseFlow


class SearchFlow(BaseFlow):
    """Complex search operations flow."""
    
    async def perform_advanced_search(self, query: str, filters: dict = None):
        """Perform advanced search with filters."""
        await self.page.goto("https://example.com/search")
        await self.page.wait_for_load_state('networkidle')
        
        # Enter search query
        search_input = await self.selector_engine.find(
            self.page, "advanced_search_input"
        )
        
        if search_input:
            await search_input.clear()
            await search_input.type(query)
        
        # Apply filters if provided
        if filters:
            await self._apply_search_filters(filters)
        
        # Submit search
        search_button = await self.selector_engine.find(
            self.page, "search_button"
        )
        if search_button:
            await search_button.click()
            await self.page.wait_for_timeout(2000)
    
    async def _apply_search_filters(self, filters: dict):
        """Apply search filters."""
        for filter_name, filter_value in filters.items():
            filter_element = await self.selector_engine.find(
                self.page, f"filter_{filter_name}"
            )
            if filter_element:
                await filter_element.select_option(filter_value)
    
    async def get_search_results(self):
        """Extract search results."""
        results = []
        result_elements = await self.selector_engine.find_all(
            self.page, "search_result_item"
        )
        
        for element in result_elements:
            result = await self._extract_result_data(element)
            results.append(result)
        
        return results
    
    async def _extract_result_data(self, element):
        """Extract data from a single search result."""
        title = await element.query_selector("result_title")
        description = await element.query_selector("result_description")
        url = await element.query_selector("result_url")
        
        return {
            'title': await title.inner_text() if title else None,
            'description': await description.inner_text() if description else None,
            'url': await url.get_attribute('href') if url else None
        }
