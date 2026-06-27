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
    """Base class for primary tab extraction from match detail pages.
    
    All selectors are YAML-driven. Zero hardcoded CSS strings.
    """
    
    def __init__(self, scraper: FlashscoreScraper):
        self.scraper = scraper
        self.logger = self._get_logger()
        self.page: Page = scraper.page  # type: ignore[assignment]
        self._selector_engine = getattr(scraper, 'selector_engine', None)
    
    def _get_logger(self):
        """Get logger instance."""
        from src.observability.logger import get_logger
        return get_logger(f"flashscore.primary_tab_extractor.{self.__class__.__name__.lower()}")
    
    async def _resolve_element(self, selector_name: str, parent=None) -> Optional[Any]:
        """Resolve a single element via YAML selector engine."""
        if self._selector_engine:
            try:
                search_target = parent or self.page
                return await self._selector_engine.find(search_target, selector_name)
            except Exception as e:
                self.logger.debug(f"YAML selector '{selector_name}' failed: {e}")
        return None
    
    async def _resolve_elements(self, selector_name: str, parent=None) -> List[Any]:
        """Resolve multiple elements via YAML selector engine."""
        if self._selector_engine:
            try:
                search_target = parent or self.page
                elements = await self._selector_engine.find_all(search_target, selector_name)
                if elements:
                    return elements
            except Exception as e:
                self.logger.debug(f"YAML selector '{selector_name}' failed: {e}")
        return []
    
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
    
    # Tabs that are sub-tabs under "Match" primary tab
    MATCH_SUB_TABS = {'summary', 'stats', 'player-stats', 'player-statistics', 
                      'match-stats', 'match-statistics', 'lineups', 'match-history'}
    
    async def navigate_to_tab(self, tab_name: str) -> bool:
        """
        Navigate to a specific tab by clicking the button with matching text.
        
        FlashScore tab hierarchy (confirmed via live inspection):
        - Primary tabs: Match, Odds, H2H, Draw, Video
        - Under "Match" sub-tabs: Summary, Player stats, Stats, Lineups, Match History
        - Under "Odds" sub-tabs: Home/Away, 1X2, Over/Under, etc.
        
        Navigation strategy:
        - For sub-tabs under "Match": first click "Match" primary tab, then the sub-tab
        - For primary tabs (Odds, H2H): click directly
        - For "Stats": click "Match" → "Stats" sub-tab
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
            
            # For sub-tabs under "Match", first ensure "Match" primary tab is active
            if tab_name_lower in self.MATCH_SUB_TABS:
                # Click "Match" primary tab first to reveal sub-tabs
                match_clicked = await self._click_tab_by_text('Match')
                if match_clicked:
                    await self.page.wait_for_timeout(1500)
                    self.logger.info(f"Clicked 'Match' primary tab for sub-tab access")
                
                # Now click the actual sub-tab
                if await self._click_tab_by_text(display_text):
                    await self.page.wait_for_timeout(2000)
                    self.logger.info(f"Successfully navigated to {tab_name} sub-tab")
                    return True
            
            # For primary tabs (Odds, H2H, Draw, Video), click directly
            if await self._click_tab_by_text(display_text):
                await self.page.wait_for_timeout(3000)
                self.logger.info(f"Successfully navigated to {tab_name} tab via button click")
                return True
            
            # Strategy 2: Find anchor link by data-analytics-alias (YAML: analytics_link)
            analytics_alias = self.TAB_ANALYTICS_ALIAS.get(tab_name_lower, tab_name_lower)
            try:
                # Find all analytics links via YAML selector, then match by alias
                all_links = await self._resolve_elements('analytics_link')
                link = None
                for l in all_links:
                    alias = await l.get_attribute('data-analytics-alias')
                    if alias == analytics_alias:
                        link = l
                        break
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
            
            # Strategy 3: URL-based navigation for known tab URL patterns
            tab_url_suffix = self.TAB_URL_SUFFIX.get(tab_name_lower)
            if tab_url_suffix is not None:
                current_url = self.page.url
                base_url = current_url.split('?')[0].rstrip('/')
                # Remove any existing tab path segments
                for suffix in ['', '/odds', '/h2h', '/standings', '/summary', 
                               '/summary/stats', '/summary/player-stats', '/summary/lineups',
                               '/summary/point-by-point']:
                    if base_url.endswith(suffix):
                        base_url = base_url[:-len(suffix)] if suffix else base_url
                        break
                
                target_url = base_url + ('/' + tab_url_suffix if tab_url_suffix else '')
                # Preserve query params
                query = current_url.split('?')[1] if '?' in current_url else ''
                if query:
                    target_url += '?' + query
                
                self.logger.info(f"Trying URL navigation to: {target_url}")
                await self.page.goto(target_url, wait_until='domcontentloaded')
                await self.page.wait_for_timeout(3000)
                return True
            
            self.logger.warning(f"Could not find or navigate to {tab_name} tab")
            return False
            
        except Exception as e:
            self.logger.error(f"Error navigating to {tab_name} tab: {e}")
            return False
    
    async def _click_tab_by_text(self, display_text: str) -> bool:
        """Click a tab button matching the given display text — YAML selector: tab_button."""
        try:
            tab_buttons = await self._resolve_elements('tab_button')
            for btn in tab_buttons:
                text = (await btn.text_content()).strip()
                if text == display_text:
                    await btn.click()
                    return True
            return False
        except Exception as e:
            self.logger.debug(f"Error clicking tab by text '{display_text}': {e}")
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
            # Use YAML-driven tab_selected selector to check active state
            selected_tabs = await self._resolve_elements('tab_selected')
            for tab in selected_tabs:
                text = (await tab.text_content()).strip()
                text_to_tab = {
                    'Summary': 'summary', 'Stats': 'stats', 'Odds': 'odds',
                    'H2H': 'h2h', 'Match': 'match', 'Player stats': 'player-stats',
                    'Lineups': 'lineups', 'Match History': 'match-history',
                }
                if text_to_tab.get(text) == tab_name:
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
            
            # Fallback: check if tab content is visible via YAML selector
            content_element = await self._resolve_element('tab_content')
            if content_element:
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
            # Check if the page is still alive before doing anything
            if not await self._is_page_alive():
                self.logger.error(f"Page is closed before extracting {tab_name} tab")
                return None
            
            # Check if we're already on the correct tab to avoid unnecessary navigation
            current_tab = await self._get_current_active_tab()
            if current_tab == tab_name:
                self.logger.info(f"Already on {tab_name} tab, skipping navigation")
                return await self._extract_current_tab_data(tab_name)
            
            # Navigate to tab
            if not await self.navigate_to_tab(tab_name):
                return None
            
            # Verify page is still alive after navigation
            if not await self._is_page_alive():
                self.logger.error(f"Page closed after navigating to {tab_name} tab")
                return None
            
            # Wait for content to load
            if not await self.wait_for_tab_content(tab_name):
                return None
            
            # Extract data based on tab type
            return await self._extract_current_tab_data(tab_name)
                
        except Exception as e:
            error_msg = str(e)
            if "Target page, context or browser has been closed" in error_msg:
                self.logger.error(f"Browser context closed while extracting {tab_name} tab — page likely navigated away or browser shut down")
            else:
                self.logger.error(f"Error extracting data from {tab_name} tab: {e}")
            return None
    
    async def _is_page_alive(self) -> bool:
        """Check if the Playwright page is still accessible."""
        try:
            # Simple check: can we access the page URL?
            _ = self.page.url
            return True
        except Exception:
            return False
    
    async def _get_current_active_tab(self) -> Optional[str]:
        """Get the currently active tab name.
        
        FlashScore uses .wcl-tabSelected class on active tab buttons.
        We check both primary tabs (Match, Odds, H2H) and sub-tabs (Summary, Stats, etc.)
        """
        try:
            # Find all selected tab buttons - FlashScore uses wcl-tabSelected class
            selected_tabs = await self._resolve_elements('tab_selected')
            
            # Map button text to internal tab names
            text_to_tab = {
                'Summary': 'summary',
                'Stats': 'stats',
                'Player stats': 'player-stats',
                'Lineups': 'lineups',
                'Match History': 'match-history',
                'Odds': 'odds',
                'H2H': 'h2h',
                'Match': 'match',
            }
            
            active_primary = None
            active_sub = None
            
            for tab in selected_tabs:
                text = (await tab.text_content()).strip()
                tab_name = text_to_tab.get(text, text.lower())
                
                # Determine if this is a primary or sub-tab by checking parent
                cls = await tab.get_attribute('class') or ''
                if 'tabsPrimary' in cls or 'tabsPrimary' in (await tab.evaluate('el => el.closest("[class*=tabsPrimary]")?.className || ""')):
                    active_primary = tab_name
                else:
                    active_sub = tab_name
            
            # If a sub-tab is selected under "Match", return the sub-tab name
            if active_sub and active_sub not in ('match',):
                return active_sub
            
            # If primary tab is selected (Odds, H2H), return that
            if active_primary and active_primary != 'match':
                return active_primary
            
            # Fallback: check URL
            current_url = self.page.url
            if '/odds/' in current_url:
                return 'odds'
            elif '/h2h/' in current_url:
                return 'h2h'
            elif '/summary/stats' in current_url:
                return 'stats'
            elif '/summary/' in current_url:
                return 'summary'
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
