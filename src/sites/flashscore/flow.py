"""
Flashscore navigation flow.

Handles navigation and interaction with Flashscore sports pages.
"""

from src.sites.base.flow import BaseFlow
from src.selectors.context_manager import SelectorContext, DOMState


class FlashscoreFlow(BaseFlow):
    """Navigation flow for Flashscore scraper."""
    
    async def open_home(self):
        """Navigate to Flashscore home page."""
        await self.page.goto("https://www.flashscore.com")
        await self.page.wait_for_load_state('networkidle')
        
        # Handle cookie consent if present
        await self._handle_cookie_consent()
    
    async def _handle_cookie_consent(self):
        """Handle cookie consent dialog if present."""
        try:
            # Try multiple cookie consent selectors
            cookie_selectors = [
                "cookie_consent",  # From our hierarchical selectors
                "cookie_accept",
                "#onetrust-accept-btn-handler",
                ".cookie-consent-accept"
            ]
            
            for selector_name in cookie_selectors:
                try:
                    accept_button = await self.selector_engine.find(self.page, selector_name)
                    if accept_button:
                        await accept_button.click()
                        await self.page.wait_for_timeout(1000)
                        break
                except Exception:
                    continue
                    
        except Exception:
            # Cookie dialog might not be present or different structure
            pass
    
    async def search_sport(self, sport_name: str):
        """Search for a specific sport."""
        search_input = await self.selector_engine.find(self.page, "search_input")
        if search_input:
            await search_input.clear()
            await search_input.type(sport_name)
            await search_input.press('Enter')
            await self.page.wait_for_timeout(2000)
    
    async def navigate_to_football(self):
        """Navigate to football section."""
        # Try multiple football link selectors
        football_selectors = [
            "football_link",  # From our hierarchical selectors
            ".sport-football",
            "[data-sport='football']"
        ]
        
        for selector_name in football_selectors:
            try:
                football_link = await self.selector_engine.find(self.page, selector_name)
                if football_link:
                    await football_link.click()
                    await self.page.wait_for_load_state('networkidle')
                    break
            except Exception:
                continue
    
    async def navigate_to_live_matches(self):
        """Navigate to live matches section."""
        # Try live filter selector from hierarchical selectors
        live_selectors = [
            "live_filter",  # From our hierarchical selectors
            "live_matches_link",
            ".filter-live"
        ]
        
        for selector_name in live_selectors:
            try:
                live_link = await self.selector_engine.find(self.page, selector_name)
                if live_link:
                    await live_link.click()
                    await self.page.wait_for_load_state('networkidle')
                    break
            except Exception:
                continue
    
    async def select_date(self, date_str: str):
        """Select a specific date for matches."""
        date_picker = await self.selector_engine.find(self.page, "date_picker")
        if date_picker:
            await date_picker.click()
            await self.page.wait_for_timeout(1000)
            
            # Try to find and click the specific date
            date_option = await self.selector_engine.find(self.page, "date_option", date_str)
            if date_option:
                await date_option.click()
                await self.page.wait_for_timeout(2000)
    
    async def click_match(self, match_identifier: str):
        """Click on a specific match."""
        match_element = await self.selector_engine.find(self.page, "match_item", match_identifier)
        if match_element:
            await match_element.click()
            await self.page.wait_for_load_state('networkidle')
    
    async def scroll_to_matches(self):
        """Scroll to the matches section."""
        matches_container = await self.selector_engine.find(self.page, "matches_container")
        if matches_container:
            await matches_container.scroll_into_view_if_needed()
            await self.page.wait_for_timeout(1000)
    
    async def filter_by_competition(self, competition_name: str):
        """Filter matches by competition."""
        filter_button = await self.selector_engine.find(self.page, "competition_filter")
        if filter_button:
            await filter_button.click()
            await self.page.wait_for_timeout(1000)
            
            competition_option = await self.selector_engine.find(self.page, "competition_option", competition_name)
            if competition_option:
                await competition_option.click()
                await self.page.wait_for_timeout(2000)
    
    async def navigate_to_live_games(self, sport_path: str):
        """Navigate to live games for a specific sport."""
        # First navigate to the sport
        await self.page.goto(f"https://www.flashscore.com/{sport_path}/")
        await self.page.wait_for_load_state('networkidle')
        
        # Then filter for live games
        await self.navigate_to_live_matches()
    
    async def navigate_to_finished_games(self, sport_path: str):
        """Navigate to finished games for a specific sport."""
        # First navigate to the sport
        await self.page.goto(f"https://www.flashscore.com/{sport_path}/")
        await self.page.wait_for_load_state('networkidle')
        
        # Try to find finished games filter
        finished_selectors = [
            "finished_filter",
            "filter-finished", 
            ".filter-finished"
        ]
        
        for selector_name in finished_selectors:
            try:
                finished_link = await self.selector_engine.find(self.page, selector_name)
                if finished_link:
                    await finished_link.click()
                    await self.page.wait_for_load_state('networkidle')
                    break
            except Exception:
                continue
    
    async def navigate_to_scheduled_games(self, sport_path: str):
        """Navigate to scheduled games for a specific sport."""
        # First navigate to the sport
        await self.page.goto(f"https://www.flashscore.com/{sport_path}/")
        await self.page.wait_for_load_state('networkidle')
        
        # Try to find scheduled games filter
        scheduled_selectors = [
            "scheduled_filter",
            "filter-scheduled",
            ".filter-scheduled"
        ]
        
        for selector_name in scheduled_selectors:
            try:
                scheduled_link = await self.selector_engine.find(self.page, selector_name)
                if scheduled_link:
                    await scheduled_link.click()
                    await self.page.wait_for_load_state('networkidle')
                    break
            except Exception:
                continue
