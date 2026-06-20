"""
Primary tab extractor for Flashscore match detail pages.

Handles extraction from primary tabs: SUMMARY, H2H, ODDS, STATS.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from playwright.async_api import ElementHandle, Page

from src.sites.flashscore.scraper import FlashscoreScraper
from src.sites.flashscore.models import PageState, SummaryData, H2HData, OddsData, StatsData
from datetime import datetime


class PrimaryTabExtractor(ABC):
    """Base class for primary tab extraction from match detail pages."""
    
    def __init__(self, scraper: FlashscoreScraper):
        self.scraper = scraper
        self.logger = self._get_logger()
        self.page: Page = scraper.page  # type: ignore[assignment]
    
    def _get_logger(self):
        """Get logger instance."""
        from src.observability.logger import get_logger
        return get_logger(f"flashscore.primary_tab_extractor.{self.__class__.__name__.lower()}")
    
    # Mapping of tab names to Flashscore data-analytics-alias values
    # Primary tabs: Match, Odds, H2H, Standings
    # Secondary tabs (under Match): Summary, Player stats, Stats, Lineups, Match History
    TAB_ANALYTICS_ALIAS = {
        # Primary tabs
        'summary': 'match-summary',
        'odds': 'odds-comparison',
        'h2h': 'h2h',
        'stats': 'stats-detail',
        'standings': 'stats-detail',
        # Secondary tabs (under Match)
        'player-stats': 'player-statistics',
        'player-statistics': 'player-statistics',
        'match-stats': 'match-statistics',
        'match-statistics': 'match-statistics',
        'lineups': 'lineups',
        'match-history': 'match-history'
    }
    
    # Tab URL suffixes for navigation
    TAB_URL_SUFFIX = {
        'summary': '',
        'odds': 'odds',
        'h2h': 'h2h',
        'stats': 'standings',
        'standings': 'standings',
        # Secondary tabs URL suffixes
        'player-stats': 'summary/player-stats',
        'player-statistics': 'summary/player-stats',
        'match-stats': 'summary/stats',
        'match-statistics': 'summary/stats',
        'lineups': 'summary/lineups',
        'match-history': 'summary/point-by-point'
    }
    
    async def navigate_to_tab(self, tab_name: str) -> bool:
        """
        Navigate to a specific tab by clicking the button with matching text.
        
        This uses the most reliable approach: finding the button element by its
        visible text content, which matches FlashScore's actual DOM structure.
        """
        try:
            tab_name_lower = tab_name.lower()
            
            # Map tab names to FlashScore button display text
            tab_display_text = {
                'summary': 'Summary',
                'odds': 'Odds',
                'h2h': 'H2H',
                'stats': 'Stats',
                'player-stats': 'Player stats',
                'player-statistics': 'Player stats',
                'match-stats': 'Stats',
                'match-statistics': 'Stats',
                'lineups': 'Lineups',
                'match-history': 'Match History',
                'standings': 'Standings',
            }
            
            display_text = tab_display_text.get(tab_name_lower, tab_name)
            
            # Strategy 1: Find button element by text content (most reliable)
            try:
                tab_buttons = await self.page.query_selector_all('.wcl-tab_GS7ig, [class*="wcl-tab"]')
                for btn in tab_buttons:
                    text = (await btn.text_content()).strip()
                    if text == display_text:
                        await btn.click()
                        await self.page.wait_for_timeout(3000)
                        self.logger.info(f"Successfully navigated to {tab_name} tab via button click")
                        return True
            except Exception as e:
                self.logger.debug(f"Button text search failed: {e}")
            
            # Strategy 2: Find anchor link by data-analytics-alias
            analytics_alias = self.TAB_ANALYTICS_ALIAS.get(tab_name_lower, tab_name_lower)
            try:
                link = await self.page.query_selector(f'a[data-analytics-alias="{analytics_alias}"]')
                if link:
                    href = await link.get_attribute('href')
                    if href:
                        if not href.startswith('http'):
                            href = f"https://www.flashscore.com{href}"
                        await self.page.goto(href, wait_until='domcontentloaded')
                        await self.page.wait_for_timeout(3000)
                        self.logger.info(f"Successfully navigated to {tab_name} tab via URL")
                        return True
                    else:
                        await link.click()
                        await self.page.wait_for_timeout(3000)
                        self.logger.info(f"Successfully navigated to {tab_name} tab via link click")
                        return True
            except Exception as e:
                self.logger.debug(f"Analytics alias search failed: {e}")
            
            self.logger.warning(f"Could not find or navigate to {tab_name} tab")
            return False
            
        except Exception as e:
            self.logger.error(f"Error navigating to {tab_name} tab: {e}")
            return False
    
    async def _wait_for_tab_content_load(self, tab_name: str, timeout: int = 10000) -> bool:
        """Wait for tab content to load after navigation."""
        try:
            # Wait for tab content container
            content_selectors = [
                f'.tabContent__{self.TAB_ANALYTICS_ALIAS.get(tab_name, tab_name)}',
                '.tabContent',
                '[data-testid="tab-content"]',
                '.wcl-colXs-12'
            ]
            
            for selector in content_selectors:
                try:
                    await self.page.wait_for_selector(selector, state="visible", timeout=timeout)
                    return True
                except:
                    continue
            
            # Fallback: just wait for network to settle
            await self.page.wait_for_load_state("networkidle", timeout=5000)
            return True
            
        except Exception as e:
            self.logger.debug(f"Tab content wait completed with exception: {e}")
            return True  # Continue anyway
    
    async def _verify_tab_active(self, tab_name: str) -> bool:
        """Verify that the specified tab is currently active."""
        try:
            analytics_alias = self.TAB_ANALYTICS_ALIAS.get(tab_name, tab_name)
            
            # Flashscore uses data-selected="true" on button tabs
            # and data-analytics-alias for navigation links
            active_selectors = [
                # Primary: button with data-selected
                f'button[data-testid="wcl-tab"][data-selected="true"][data-analytics-alias="{analytics_alias}"]',
                # Secondary: navigation link with aria-selected
                f'a[data-analytics-alias="{analytics_alias}"][aria-selected="true"]',
                # Tertiary: check URL contains tab path
                f'a[data-analytics-alias="{analytics_alias}"].active'
            ]
            
            for selector in active_selectors:
                active_element = await self.page.query_selector(selector)
                if active_element:
                    return True
            
            # Fallback: check URL path contains tab indicator
            current_url = self.page.url
            if tab_name == 'summary' and '/odds/' not in current_url and '/h2h/' not in current_url and '/standings/' not in current_url:
                return True
            if tab_name == 'odds' and '/odds/' in current_url:
                return True
            if tab_name == 'h2h' and '/h2h/' in current_url:
                return True
            if tab_name in ('stats', 'standings') and '/standings/' in current_url:
                return True
            
            # Fallback: check if tab content is visible
            content_selectors = [
                f'.tabContent__{analytics_alias}',
                f'.{tab_name}__content',
                '[data-testid="tab-content"]'
            ]
            
            for selector in content_selectors:
                content_element = await self.page.query_selector(selector)
                if content_element:
                    # Check if element is visible
                    is_visible = await content_element.is_visible()
                    if is_visible:
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying tab active status for {tab_name}: {e}")
            return False
    
    async def wait_for_tab_content(self, tab_name: str, timeout: int = 5000) -> bool:
        """
        Wait for tab content to load.
        
        Args:
            tab_name: Name of the tab
            timeout: Maximum time to wait in milliseconds
            
        Returns:
            True if content loaded, False otherwise
        """
        try:
            analytics_alias = self.TAB_ANALYTICS_ALIAS.get(tab_name, tab_name)
            
            # Flashscore tab content selectors
            content_selectors = [
                f'.tabContent__{analytics_alias}',
                '.tabContent',
                '[data-testid="tab-content"]',
                '.wcl-colXs-12',
                '.duelParticipant__startTime'
            ]
            
            for selector in content_selectors:
                try:
                    await self.page.wait_for_selector(selector, state="visible", timeout=timeout)
                    return True
                except:
                    continue
            
            # Fallback: wait for network idle
            try:
                await self.page.wait_for_load_state("networkidle", timeout=3000)
            except:
                pass
            
            self.logger.warning(f"Tab content did not load for {tab_name}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error waiting for {tab_name} tab content: {e}")
            return False
    
    async def extract_tab_data(self, tab_name: str) -> Optional[Dict[str, Any]]:
        """
        Extract data from a specific tab with efficient switching.
        
        Args:
            tab_name: Name of tab to extract data from
            
        Returns:
            Extracted data dictionary or None if extraction fails
        """
        try:
            # Check if we're already on the correct tab to avoid unnecessary navigation
            current_tab = await self._get_current_active_tab()
            if current_tab == tab_name:
                self.logger.info(f"Already on {tab_name} tab, skipping navigation")
                return await self._extract_current_tab_data(tab_name)
            
            # Navigate to tab
            if not await self.navigate_to_tab(tab_name):
                return None
            
            # Wait for content to load
            if not await self.wait_for_tab_content(tab_name):
                return None
            
            # Extract data based on tab type
            return await self._extract_current_tab_data(tab_name)
                
        except Exception as e:
            self.logger.error(f"Error extracting data from {tab_name} tab: {e}")
            return None
    
    async def _get_current_active_tab(self) -> Optional[str]:
        """Get the currently active tab name."""
        try:
            # Flashscore uses data-selected="true" on button tabs
            active_selectors = [
                'button[data-testid="wcl-tab"][data-selected="true"]',
                'a[data-analytics-alias][aria-selected="true"]',
                '.tab__title.active',
                '.tab__title.selected'
            ]
            
            for selector in active_selectors:
                active_element = await self.page.query_selector(selector)
                if active_element:
                    # Try data-analytics-alias first (Flashscore specific)
                    analytics_alias = await active_element.get_attribute('data-analytics-alias')
                    if analytics_alias:
                        # Map back to tab name
                        for tab_name, alias in self.TAB_ANALYTICS_ALIAS.items():
                            if alias == analytics_alias:
                                return tab_name
                    
                    # Try data-tab-name
                    tab_name = await active_element.get_attribute('data-tab-name')
                    if tab_name:
                        return tab_name
                    
                    # Fallback: get text content
                    tab_text = await active_element.text_content()
                    if tab_text:
                        return tab_text.strip().lower()
            
            # Fallback: check URL
            current_url = self.page.url
            if '/odds/' in current_url:
                return 'odds'
            elif '/h2h/' in current_url:
                return 'h2h'
            elif '/standings/' in current_url:
                return 'stats'
            else:
                return 'summary'  # Default to summary
            
        except Exception as e:
            self.logger.error(f"Error getting current active tab: {e}")
            return None
    
    async def _extract_current_tab_data(self, tab_name: str) -> Optional[Dict[str, Any]]:
        """Extract data from the currently active tab without navigation."""
        try:
            # Extract data based on tab type (same logic as before but without navigation)
            if tab_name == 'summary':
                return await self._extract_summary_data()
            elif tab_name == 'h2h':
                return await self._extract_h2h_data()
            elif tab_name == 'odds':
                return await self._extract_odds_data()
            elif tab_name == 'stats':
                return await self._extract_stats_data()
            else:
                self.logger.warning(f"Unknown tab type: {tab_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error extracting current tab data for {tab_name}: {e}")
            return None
    
    @abstractmethod
    async def _extract_summary_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from SUMMARY tab."""
        pass
    
    @abstractmethod
    async def _extract_h2h_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from H2H tab."""
        pass
    
    @abstractmethod
    async def _extract_odds_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from ODDS tab."""
        pass
    
    @abstractmethod
    async def _extract_stats_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from STATS tab."""
        pass
    
    async def validate_tab_data(self, tab_name: str, data: Dict[str, Any]) -> bool:
        """
        Validate extracted tab data structure.
        
        Args:
            tab_name: Name of the tab
            data: Extracted data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        try:
            if not data or not isinstance(data, dict):
                return False
            
            # Basic validation for each tab type
            if tab_name == 'summary':
                required_fields = ['overview', 'teams']
                return all(field in data for field in required_fields)
            elif tab_name == 'h2h':
                required_fields = ['previous_matches']
                return all(field in data for field in required_fields)
            elif tab_name == 'odds':
                required_fields = ['betting_odds']
                return all(field in data for field in required_fields)
            elif tab_name == 'stats':
                required_fields = ['statistics']
                return all(field in data for field in required_fields)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating {tab_name} tab data: {e}")
            return False
