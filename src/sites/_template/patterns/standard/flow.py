"""
Standard pattern flow template.

This pattern combines basic navigation in flow.py with specialized
flows in the flows/ subfolder for complex operations.
Use this for sites with moderate complexity that need both
basic navigation and specialized extraction/filtering logic.
"""

from src.sites.base.flow import BaseFlow


class StandardFlow(BaseFlow):
    """Standard flow with basic navigation and coordination."""
    
    async def open_home(self):
        """Navigate to the home page."""
        await self.page.goto("https://example.com")
        await self.page.wait_for_load_state('networkidle')
    
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
    
    async def perform_basic_search(self, query: str):
        """Perform basic search - complex search logic moved to flows/search_flow.py"""
        # Navigate to search page first
        await self.open_home()
        
        # Find search input
        search_input = await self.selector_engine.find(
            self.page, "search_input"
        )
        
        if search_input:
            await search_input.clear()
            await search_input.type(query)
            await search_input.press('Enter')
            await self.page.wait_for_timeout(2000)
