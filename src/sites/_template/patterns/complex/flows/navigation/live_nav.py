"""
Live navigation flow.

Handles navigation to live matches, live scores, and real-time
data sections. Designed for sports sites with complex live
match tracking and real-time updates.
"""

from src.sites.base.flow import BaseFlow


class LiveNavigationFlow(BaseFlow):
    """Live matches navigation flow."""
    
    async def navigate_to_live_home(self):
        """Navigate to the live matches home page."""
        await self.page.goto("https://example.com/live")
        await self.page.wait_for_load_state('networkidle')
        
        # Wait for live matches to load
        await self.page.wait_for_selector(".live-matches-container", timeout=10000)
    
    async def navigate_to_live_sport(self, sport_name: str):
        """Navigate to live matches for a specific sport."""
        sport_url = f"https://example.com/live/{sport_name.lower()}"
        await self.page.goto(sport_url)
        await self.page.wait_for_load_state('networkidle')
        
        # Wait for sport-specific live matches
        await self.page.wait_for_selector(f".live-{sport_name.lower()}", timeout=10000)
    
    async def navigate_to_live_competition(self, competition_id: str):
        """Navigate to live matches for a specific competition."""
        competition_url = f"https://example.com/live/competition/{competition_id}"
        await self.page.goto(competition_url)
        await self.page.wait_for_load_state('networkidle')
        
        # Wait for competition live matches
        await self.page.wait_for_selector(".live-competition-matches", timeout=10000)
    
    async def filter_live_matches_by_time(self, time_filter: str):
        """Filter live matches by time (today, tomorrow, etc.)."""
        time_filter_element = await self.selector_engine.find(
            self.page, f"live_time_filter_{time_filter}"
        )
        
        if time_filter_element:
            await time_filter_element.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_live_matches_by_status(self, status_filter: str):
        """Filter live matches by status (live, upcoming, finished)."""
        status_filter_element = await self.selector_engine.find(
            self.page, f"live_status_filter_{status_filter}"
        )
        
        if status_filter_element:
            await status_filter_element.click()
            await self.page.wait_for_timeout(2000)
    
    async def navigate_to_live_match_details(self, match_id: str):
        """Navigate to detailed view of a live match."""
        # First go to live home
        await self.navigate_to_live_home()
        
        # Find and click the specific match
        match_element = await self.selector_engine.find(
            self.page, f"live_match_{match_id}"
        )
        
        if match_element:
            await match_element.click()
            await self.page.wait_for_load_state('networkidle')
            
            # Wait for match details to load
            await self.page.wait_for_selector(".live-match-details", timeout=10000)
    
    async def get_live_navigation_options(self):
        """Get all available live navigation options."""
        navigation_options = {}
        
        # Find sport filters
        sport_filters = await self.page.query_selector_all(".live-sport-filter")
        for filter_element in sport_filters:
            sport_name = await filter_element.inner_text()
            navigation_options[sport_name.strip().lower()] = {
                'type': 'sport',
                'element': filter_element
            }
        
        # Find time filters
        time_filters = await self.page.query_selector_all(".live-time-filter")
        for filter_element in time_filters:
            time_name = await filter_element.inner_text()
            navigation_options[time_name.strip().lower()] = {
                'type': 'time',
                'element': filter_element
            }
        
        return navigation_options
    
    async def refresh_live_data(self):
        """Refresh live data on current page."""
        refresh_button = await self.selector_engine.find(
            self.page, "live_refresh_button"
        )
        
        if refresh_button:
            await refresh_button.click()
            await self.page.wait_for_timeout(3000)
        else:
            # Alternative: reload the page
            await self.page.reload()
            await self.page.wait_for_load_state('networkidle')
