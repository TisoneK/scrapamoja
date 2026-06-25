"""
Sport filtering flow.

Handles sport-based filtering operations including sport selection,
multi-sport filtering, and sport-specific content filtering.
"""

from src.sites.base.flow import BaseFlow


class SportFilteringFlow(BaseFlow):
    """Sport filtering operations flow."""
    
    async def filter_by_sport(self, sport_name: str):
        """Filter content by a specific sport."""
        sport_filter = await self.selector_engine.find(
            self.page, f"sport_filter_{sport_name.lower()}"
        )
        
        if sport_filter:
            await sport_filter.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_multiple_sports(self, sport_list: list):
        """Filter content by multiple sports."""
        # Open multi-sport filter
        multi_sport_button = await self.selector_engine.find(
            self.page, "multi_sport_filter"
        )
        
        if multi_sport_button:
            await multi_sport_button.click()
            await self.page.wait_for_timeout(1000)
        
        # Select each sport
        for sport in sport_list:
            sport_checkbox = await self.selector_engine.find(
                self.page, f"sport_checkbox_{sport.lower()}"
            )
            
            if sport_checkbox:
                await sport_checkbox.check()
        
        # Apply filter
        apply_button = await self.selector_engine.find(
            self.page, "apply_sport_filter"
        )
        
        if apply_button:
            await apply_button.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_sport_category(self, category: str):
        """Filter by sport category (team sports, individual sports, etc.)."""
        category_filter = await self.selector_engine.find(
            self.page, f"sport_category_{category.lower()}"
        )
        
        if category_filter:
            await category_filter.click()
            await self.page.wait_for_timeout(2000)
    
    async def exclude_sport(self, sport_name: str):
        """Exclude a specific sport from results."""
        # Open exclude options
        exclude_button = await self.selector_engine.find(
            self.page, "exclude_sports_button"
        )
        
        if exclude_button:
            await exclude_button.click()
            await self.page.wait_for_timeout(1000)
        
        # Select sport to exclude
        exclude_checkbox = await self.selector_engine.find(
            self.page, f"exclude_sport_{sport_name.lower()}"
        )
        
        if exclude_checkbox:
            await exclude_checkbox.check()
        
        # Apply exclusion
        apply_button = await self.selector_engine.find(
            self.page, "apply_exclude_filter"
        )
        
        if apply_button:
            await apply_button.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_popular_sports(self):
        """Filter to show only popular sports."""
        popular_sports_filter = await self.selector_engine.find(
            self.page, "popular_sports_filter"
        )
        
        if popular_sports_filter:
            await popular_sports_filter.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_live_sports(self):
        """Filter to show only sports with live events."""
        live_sports_filter = await self.selector_engine.find(
            self.page, "live_sports_filter"
        )
        
        if live_sports_filter:
            await live_sports_filter.click()
            await self.page.wait_for_timeout(2000)
    
    async def clear_sport_filter(self):
        """Clear all sport filters."""
        clear_button = await self.selector_engine.find(
            self.page, "clear_sport_filter"
        )
        
        if clear_button:
            await clear_button.click()
            await self.page.wait_for_timeout(2000)
    
    async def get_active_sport_filters(self):
        """Get currently active sport filters."""
        active_filters = []
        
        # Find active sport filter elements
        active_elements = await self.page.query_selector_all(".sport-filter-active")
        
        for element in active_elements:
            sport_name = await element.inner_text()
            if sport_name:
                active_filters.append(sport_name.strip())
        
        return active_filters
    
    async def get_available_sports(self):
        """Get list of available sports for filtering."""
        available_sports = []
        
        # Find all sport filter options
        sport_options = await self.page.query_selector_all(".sport-filter-option")
        
        for option in sport_options:
            sport_name = await option.inner_text()
            sport_value = await option.get_attribute('data-sport')
            
            if sport_name:
                available_sports.append({
                    'name': sport_name.strip(),
                    'value': sport_value or sport_name.strip().lower()
                })
        
        return available_sports
    
    async def get_sport_categories(self):
        """Get available sport categories."""
        categories = []
        
        # Find all sport category options
        category_options = await self.page.query_selector_all(".sport-category-option")
        
        for option in category_options:
            category_name = await option.inner_text()
            category_value = await option.get_attribute('data-category')
            
            if category_name:
                categories.append({
                    'name': category_name.strip(),
                    'value': category_value or category_name.strip().lower()
                })
        
        return categories
    
    async def search_sport(self, sport_name: str):
        """Search for a specific sport in the sport filter."""
        search_input = await self.selector_engine.find(
            self.page, "sport_search_input"
        )
        
        if search_input:
            await search_input.clear()
            await search_input.type(sport_name)
            await self.page.wait_for_timeout(1000)
            
            # Wait for search results
            await self.page.wait_for_selector(".sport_search_results", timeout=5000)
    
    async def select_sport_from_search(self, sport_name: str):
        """Select a sport from search results."""
        sport_result = await self.selector_engine.find(
            self.page, f"sport_search_result_{sport_name.lower()}"
        )
        
        if sport_result:
            await sport_result.click()
            await self.page.wait_for_timeout(2000)
