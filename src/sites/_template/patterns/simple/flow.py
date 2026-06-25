"""
Simple pattern flow template.

This is the most basic flow pattern for simple sites.
Contains all navigation and basic interaction logic in a single file.
Use this for sites with minimal complexity and straightforward navigation.
"""

from src.sites.base.flow import BaseFlow


class SimpleFlow(BaseFlow):
    """Simple flow for basic site navigation."""
    
    async def open_home(self):
        """Navigate to the home page."""
        await self.page.goto("https://example.com")
        await self.page.wait_for_load_state('networkidle')
    
    async def perform_search(self, query: str):
        """Perform a search query."""
        # Find search input using selector engine
        search_input = await self.selector_engine.find(
            self.page, "search_input"
        )
        
        if search_input:
            # Type search query
            await search_input.clear()
            await search_input.type(query)
            
            # Submit search
            await search_input.press('Enter')
            
            # Wait for results to load
            await self.page.wait_for_timeout(2000)
    
    async def navigate_to_page(self, page_url: str):
        """Navigate to a specific page."""
        await self.page.goto(page_url)
        await self.page.wait_for_load_state('networkidle')
    
    async def click_element(self, selector_name: str):
        """Click an element by selector name."""
        element = await self.selector_engine.find(self.page, selector_name)
        if element:
            await element.click()
            await self.page.wait_for_timeout(1000)
