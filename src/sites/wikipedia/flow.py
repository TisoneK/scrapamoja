"""
Wikipedia navigation flow.

Handles navigation and interaction with Wikipedia pages.
"""

from src.sites.base.flow import BaseFlow


class WikipediaFlow(BaseFlow):
    """Navigation flow for Wikipedia scraper."""
    
    async def open_home(self):
        """Navigate to Wikipedia home page."""
        await self.page.goto("https://en.wikipedia.org")
        await self.page.wait_for_load_state('networkidle')
    
    async def perform_search(self, query: str):
        """Perform a search query on Wikipedia."""
        # Find search input
        search_input = await self.selector_engine.find(self.page, "search_input")
        if search_input:
            await search_input.clear()
            await search_input.type(query)
            await search_input.press('Enter')
            
            # Wait for search results to load
            await self.page.wait_for_timeout(2000)
    
    async def open_article(self, article_title: str):
        """Open a specific Wikipedia article."""
        article_url = f"https://en.wikipedia.org/wiki/{article_title}"
        await self.page.goto(article_url)
        await self.page.wait_for_load_state('networkidle')
    
    async def click_first_search_result(self):
        """Click on the first search result."""
        first_result = await self.selector_engine.find(self.page, "first_search_result")
        if first_result:
            await first_result.click()
            await self.page.wait_for_load_state('networkidle')
    
    async def scroll_to_content(self):
        """Scroll to the main content area."""
        content_area = await self.selector_engine.find(self.page, "content_area")
        if content_area:
            await content_area.scroll_into_view_if_needed()
            await self.page.wait_for_timeout(1000)
