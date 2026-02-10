"""
Match navigation flow.

Handles navigation to match pages, match details, and match-related
sections of sports websites. This is specifically designed for
sports sites with complex match navigation patterns.
"""

from src.sites.base.flow import BaseFlow


class MatchNavigationFlow(BaseFlow):
    """Match page navigation flow."""
    
    async def navigate_to_match(self, match_id: str):
        """Navigate to a specific match page."""
        match_url = f"https://example.com/match/{match_id}"
        await self.page.goto(match_url)
        await self.page.wait_for_load_state('networkidle')
        
        # Wait for match content to load
        await self.page.wait_for_selector(".match-content", timeout=10000)
    
    async def navigate_to_live_match(self, match_id: str):
        """Navigate to a live match page."""
        live_url = f"https://example.com/live/match/{match_id}"
        await self.page.goto(live_url)
        await self.page.wait_for_load_state('networkidle')
        
        # Wait for live data to load
        await self.page.wait_for_selector(".live-score", timeout=10000)
    
    async def navigate_to_match_highlights(self, match_id: str):
        """Navigate to match highlights page."""
        highlights_url = f"https://example.com/match/{match_id}/highlights"
        await self.page.goto(highlights_url)
        await self.page.wait_for_load_state('networkidle')
        
        # Wait for video player to load
        await self.page.wait_for_selector(".video-player", timeout=10000)
    
    async def navigate_to_match_statistics(self, match_id: str):
        """Navigate to match statistics page."""
        stats_url = f"https://example.com/match/{match_id}/statistics"
        await self.page.goto(stats_url)
        await self.page.wait_for_load_state('networkidle')
        
        # Wait for statistics tables to load
        await self.page.wait_for_selector(".stats-table", timeout=10000)
    
    async def navigate_to_match_lineups(self, match_id: str):
        """Navigate to match lineups page."""
        lineups_url = f"https://example.com/match/{match_id}/lineups"
        await self.page.goto(lineups_url)
        await self.page.wait_for_load_state('networkidle')
        
        # Wait for lineup data to load
        await self.page.wait_for_selector(".team-lineup", timeout=10000)
    
    async def navigate_to_related_matches(self, match_id: str):
        """Navigate to related matches page."""
        related_url = f"https://example.com/match/{match_id}/related"
        await self.page.goto(related_url)
        await self.page.wait_for_load_state('networkidle')
        
        # Wait for related matches to load
        await self.page.wait_for_selector(".related-matches", timeout=10000)
    
    async def get_match_navigation_links(self, match_id: str):
        """Get all available navigation links for a match."""
        await self.navigate_to_match(match_id)
        
        navigation_links = {}
        
        # Find all navigation tabs/links
        nav_elements = await self.page.query_selector_all(".match-nav a, .match-tabs a")
        
        for element in nav_elements:
            link_text = await element.inner_text()
            href = await element.get_attribute('href')
            
            if link_text and href:
                navigation_links[link_text.strip().lower()] = href
        
        return navigation_links
