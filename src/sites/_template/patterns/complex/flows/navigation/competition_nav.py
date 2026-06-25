"""
Competition navigation flow.

Handles navigation to competition pages, standings, fixtures,
and competition-related sections. Designed for sports sites
with complex competition structures and hierarchies.
"""

from src.sites.base.flow import BaseFlow


class CompetitionNavigationFlow(BaseFlow):
    """Competition navigation flow."""
    
    async def navigate_to_competition(self, competition_id: str):
        """Navigate to a specific competition page."""
        competition_url = f"https://example.com/competition/{competition_id}"
        await self.page.goto(competition_url)
        await self.page.wait_for_load_state('networkidle')
        
        # Wait for competition content to load
        await self.page.wait_for_selector(".competition-header", timeout=10000)
    
    async def navigate_to_competition_standings(self, competition_id: str):
        """Navigate to competition standings/table."""
        standings_url = f"https://example.com/competition/{competition_id}/standings"
        await self.page.goto(standings_url)
        await self.page.wait_for_load_state('networkidle')
        
        # Wait for standings table to load
        await self.page.wait_for_selector(".standings-table", timeout=10000)
    
    async def navigate_to_competition_fixtures(self, competition_id: str):
        """Navigate to competition fixtures."""
        fixtures_url = f"https://example.com/competition/{competition_id}/fixtures"
        await self.page.goto(fixtures_url)
        await self.page.wait_for_load_state('networkidle')
        
        # Wait for fixtures to load
        await self.page.wait_for_selector(".fixtures-list", timeout=10000)
    
    async def navigate_to_competition_results(self, competition_id: str):
        """Navigate to competition results."""
        results_url = f"https://example.com/competition/{competition_id}/results"
        await self.page.goto(results_url)
        await self.page.wait_for_load_state('networkidle')
        
        # Wait for results to load
        await self.page.wait_for_selector(".results-list", timeout=10000)
    
    async def navigate_to_competition_stats(self, competition_id: str):
        """Navigate to competition statistics."""
        stats_url = f"https://example.com/competition/{competition_id}/statistics"
        await self.page.goto(stats_url)
        await self.page.wait_for_load_state('networkidle')
        
        # Wait for statistics to load
        await self.page.wait_for_selector(".competition-stats", timeout=10000)
    
    async def navigate_to_competition_teams(self, competition_id: str):
        """Navigate to competition teams list."""
        teams_url = f"https://example.com/competition/{competition_id}/teams"
        await self.page.goto(teams_url)
        await self.page.wait_for_load_state('networkidle')
        
        # Wait for teams list to load
        await self.page.wait_for_selector(".teams-list", timeout=10000)
    
    async def filter_competition_by_season(self, season: str):
        """Filter competition data by season."""
        season_filter = await self.selector_engine.find(
            self.page, "season_filter"
        )
        
        if season_filter:
            await season_filter.select_option(season)
            await self.page.wait_for_timeout(2000)
    
    async def filter_competition_by_round(self, round_number: str):
        """Filter competition data by round."""
        round_filter = await self.selector_engine.find(
            self.page, "round_filter"
        )
        
        if round_filter:
            await round_filter.select_option(round_number)
            await self.page.wait_for_timeout(2000)
    
    async def navigate_to_competition_group(self, competition_id: str, group: str):
        """Navigate to a specific group within a competition."""
        group_url = f"https://example.com/competition/{competition_id}/group/{group}"
        await self.page.goto(group_url)
        await self.page.wait_for_load_state('networkidle')
        
        # Wait for group data to load
        await self.page.wait_for_selector(".group-standings", timeout=10000)
    
    async def get_competition_navigation_tabs(self, competition_id: str):
        """Get all available navigation tabs for a competition."""
        await self.navigate_to_competition(competition_id)
        
        navigation_tabs = {}
        
        # Find all navigation tabs
        tab_elements = await self.page.query_selector_all(".competition-nav a, .competition-tabs a")
        
        for element in tab_elements:
            tab_text = await element.inner_text()
            href = await element.get_attribute('href')
            
            if tab_text and href:
                navigation_tabs[tab_text.strip().lower()] = href
        
        return navigation_tabs
