"""
Competition filtering flow.

Handles competition-based filtering operations including competition
selection, league filtering, and tournament-specific filtering.
"""

from src.sites.base.flow import BaseFlow


class CompetitionFilteringFlow(BaseFlow):
    """Competition filtering operations flow."""
    
    async def filter_by_competition(self, competition_id: str):
        """Filter content by a specific competition."""
        competition_filter = await self.selector_engine.find(
            self.page, f"competition_filter_{competition_id}"
        )
        
        if competition_filter:
            await competition_filter.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_competition_name(self, competition_name: str):
        """Filter content by competition name."""
        # Open competition search
        competition_search = await self.selector_engine.find(
            self.page, "competition_search"
        )
        
        if competition_search:
            await competition_search.click()
            await self.page.wait_for_timeout(1000)
        
        # Type competition name
        search_input = await self.selector_engine.find(
            self.page, "competition_search_input"
        )
        
        if search_input:
            await search_input.clear()
            await search_input.type(competition_name)
            await self.page.wait_for_timeout(1000)
        
        # Select from search results
        competition_result = await self.selector_engine.find(
            self.page, f"competition_result_{competition_name.lower()}"
        )
        
        if competition_result:
            await competition_result.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_multiple_competitions(self, competition_list: list):
        """Filter content by multiple competitions."""
        # Open multi-competition filter
        multi_comp_button = await self.selector_engine.find(
            self.page, "multi_competition_filter"
        )
        
        if multi_comp_button:
            await multi_comp_button.click()
            await self.page.wait_for_timeout(1000)
        
        # Select each competition
        for competition in competition_list:
            comp_checkbox = await self.selector_engine.find(
                self.page, f"competition_checkbox_{competition.lower()}"
            )
            
            if comp_checkbox:
                await comp_checkbox.check()
        
        # Apply filter
        apply_button = await self.selector_engine.find(
            self.page, "apply_competition_filter"
        )
        
        if apply_button:
            await apply_button.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_competition_type(self, comp_type: str):
        """Filter by competition type (league, cup, tournament)."""
        type_filter = await self.selector_engine.find(
            self.page, f"competition_type_{comp_type.lower()}"
        )
        
        if type_filter:
            await type_filter.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_competition_level(self, level: str):
        """Filter by competition level (international, national, regional)."""
        level_filter = await self.selector_engine.find(
            self.page, f"competition_level_{level.lower()}"
        )
        
        if level_filter:
            await level_filter.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_country(self, country_name: str):
        """Filter competitions by country."""
        country_filter = await self.selector_engine.find(
            self.page, f"country_filter_{country_name.lower()}"
        )
        
        if country_filter:
            await country_filter.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_popular_competitions(self):
        """Filter to show only popular competitions."""
        popular_filter = await self.selector_engine.find(
            self.page, "popular_competitions_filter"
        )
        
        if popular_filter:
            await popular_filter.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_live_competitions(self):
        """Filter to show only competitions with live events."""
        live_competitions_filter = await self.selector_engine.find(
            self.page, "live_competitions_filter"
        )
        
        if live_competitions_filter:
            await live_competitions_filter.click()
            await self.page.wait_for_timeout(2000)
    
    async def exclude_competition(self, competition_id: str):
        """Exclude a specific competition from results."""
        # Open exclude options
        exclude_button = await self.selector_engine.find(
            self.page, "exclude_competitions_button"
        )
        
        if exclude_button:
            await exclude_button.click()
            await self.page.wait_for_timeout(1000)
        
        # Select competition to exclude
        exclude_checkbox = await self.selector_engine.find(
            self.page, f"exclude_competition_{competition_id}"
        )
        
        if exclude_checkbox:
            await exclude_checkbox.check()
        
        # Apply exclusion
        apply_button = await self.selector_engine.find(
            self.page, "apply_exclude_competition_filter"
        )
        
        if apply_button:
            await apply_button.click()
            await self.page.wait_for_timeout(2000)
    
    async def clear_competition_filter(self):
        """Clear all competition filters."""
        clear_button = await self.selector_engine.find(
            self.page, "clear_competition_filter"
        )
        
        if clear_button:
            await clear_button.click()
            await self.page.wait_for_timeout(2000)
    
    async def get_active_competition_filters(self):
        """Get currently active competition filters."""
        active_filters = []
        
        # Find active competition filter elements
        active_elements = await self.page.query_selector_all(".competition-filter-active")
        
        for element in active_elements:
            competition_name = await element.inner_text()
            if competition_name:
                active_filters.append(competition_name.strip())
        
        return active_filters
    
    async def get_available_competitions(self):
        """Get list of available competitions for filtering."""
        available_competitions = []
        
        # Find all competition filter options
        competition_options = await self.page.query_selector_all(".competition-filter-option")
        
        for option in competition_options:
            competition_name = await option.inner_text()
            competition_id = await option.get_attribute('data-competition')
            
            if competition_name:
                available_competitions.append({
                    'name': competition_name.strip(),
                    'id': competition_id or competition_name.strip().lower()
                })
        
        return available_competitions
    
    async def get_competition_types(self):
        """Get available competition types."""
        types = []
        
        # Find all competition type options
        type_options = await self.page.query_selector_all(".competition-type-option")
        
        for option in type_options:
            type_name = await option.inner_text()
            type_value = await option.get_attribute('data-type')
            
            if type_name:
                types.append({
                    'name': type_name.strip(),
                    'value': type_value or type_name.strip().lower()
                })
        
        return types
    
    async def get_competition_countries(self):
        """Get available countries for competition filtering."""
        countries = []
        
        # Find all country filter options
        country_options = await self.page.query_selector_all(".country-filter-option")
        
        for option in country_options:
            country_name = await option.inner_text()
            country_code = await option.get_attribute('data-country')
            
            if country_name:
                countries.append({
                    'name': country_name.strip(),
                    'code': country_code or country_name.strip().lower()
                })
        
        return countries
