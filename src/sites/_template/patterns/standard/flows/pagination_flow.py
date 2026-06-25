"""
Pagination flow for standard pattern.

Handles pagination operations including next/previous navigation,
page number jumping, and infinite scroll handling.
"""

from src.sites.base.flow import BaseFlow


class PaginationFlow(BaseFlow):
    """Pagination operations flow."""
    
    async def go_to_next_page(self):
        """Navigate to next page."""
        next_button = await self.selector_engine.find(
            self.page, "next_page_button"
        )
        
        if next_button and await next_button.is_enabled():
            await next_button.click()
            await self.page.wait_for_load_state('networkidle')
            return True
        return False
    
    async def go_to_previous_page(self):
        """Navigate to previous page."""
        prev_button = await self.selector_engine.find(
            self.page, "prev_page_button"
        )
        
        if prev_button and await prev_button.is_enabled():
            await prev_button.click()
            await self.page.wait_for_load_state('networkidle')
            return True
        return False
    
    async def go_to_page_number(self, page_number: int):
        """Navigate to specific page number."""
        page_input = await self.selector_engine.find(
            self.page, "page_number_input"
        )
        
        if page_input:
            await page_input.clear()
            await page_input.type(str(page_number))
            await page_input.press('Enter')
            await self.page.wait_for_load_state('networkidle')
            return True
        return False
    
    async def get_current_page(self):
        """Get current page number."""
        current_page_element = await self.selector_engine.find(
            self.page, "current_page_indicator"
        )
        
        if current_page_element:
            page_text = await current_page_element.inner_text()
            try:
                return int(page_text)
            except ValueError:
                pass
        
        return None
    
    async def get_total_pages(self):
        """Get total number of pages."""
        total_pages_element = await self.selector_engine.find(
            self.page, "total_pages_indicator"
        )
        
        if total_pages_element:
            pages_text = await total_pages_element.inner_text()
            try:
                return int(pages_text)
            except ValueError:
                pass
        
        return None
    
    async def handle_infinite_scroll(self, max_scrolls: int = 10):
        """Handle infinite scroll pagination."""
        items_count = 0
        scrolls = 0
        
        while scrolls < max_scrolls:
            # Get current items count
            current_items = await self.selector_engine.find_all(
                self.page, "scrollable_item"
            )
            
            if len(current_items) <= items_count:
                # No new items loaded, stop scrolling
                break
            
            items_count = len(current_items)
            
            # Scroll to bottom
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.page.wait_for_timeout(2000)
            
            scrolls += 1
        
        return items_count
