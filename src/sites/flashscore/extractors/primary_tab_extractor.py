"""
Primary tab extractor for Flashscore match detail pages.

Handles extraction from primary tabs: SUMMARY, H2H, ODDS, STATS.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from playwright.async_api import ElementHandle, Page

from src.sites.flashscore.scraper import FlashscoreScraper
from src.sites.flashscore.models import PageState, SummaryData, H2HData, OddsData, StatsData
from src.sites.flashscore.extractors.selector_mixin import SelectorEngineMixin
from datetime import datetime


class PrimaryTabExtractor(SelectorEngineMixin, ABC):
    """Base class for primary tab extraction from match detail pages.
    
    Navigation and interactive operations use Playwright direct CSS queries
    (the YAML selector engine has an internal retry loop that swallows
    CancelledError, making asyncio.wait_for timeouts ineffective).
    Non-interactive reads may still fall back to the YAML selector engine
    with 8-second timeout protection.
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
    
    # YAML selector engine methods are provided by SelectorEngineMixin
    # (_resolve_element, _resolve_elements, _resolve_text)
    
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
    
    async def tab_available(self, tab_name: str) -> bool:
        """Check if a tab is present on the current page without clicking it.
        
        Not all matches have all tabs — lower-league matches may lack
        "Stats", "Player stats", and "Lineups" sub-tabs. This method
        checks whether the tab button exists before attempting navigation.
        
        For sub-tabs under "Match", first clicks the Match primary tab
        to reveal them, then checks.
        
        Args:
            tab_name: Tab identifier (e.g. 'match-stats', 'h2h', 'odds')
            
        Returns:
            True if the tab button is present on the page
        """
        tab_name_lower = tab_name.lower()
        tab_display_text = {
            'summary': 'Summary',
            'odds': 'Odds',
            'h2h': 'H2H',
            'stats': 'Standings',
            'standings': 'Standings',
            'player-stats': 'Player stats',
            'player-statistics': 'Player stats',
            'match-stats': 'Stats',
            'match-statistics': 'Stats',
            'lineups': 'Lineups',
            'match-history': 'Match History',
        }
        display_text = tab_display_text.get(tab_name_lower, tab_name)
        
        # For sub-tabs, first click "Match" primary tab to reveal them
        if tab_name_lower in self.MATCH_SUB_TABS:
            # Check if Match primary tab is already active
            match_active = await self.page.evaluate("""
                () => {
                    const buttons = document.querySelectorAll('button[data-testid="wcl-tab"]');
                    for (const btn of buttons) {
                        if (btn.textContent.trim() === 'Match') {
                            return btn.getAttribute('aria-selected') === 'true' 
                                || btn.classList.contains('wcl-tabActive')
                                || btn.getAttribute('data-active') === 'true';
                        }
                    }
                    return false;
                }
            """)
            if not match_active:
                # Click Match tab to reveal sub-tabs
                await self._click_tab_by_text('Match')
                await self.page.wait_for_timeout(1000)
        
        try:
            found = await self.page.evaluate(f"""
                () => {{
                    const buttons = document.querySelectorAll(
                        'button[data-testid="wcl-tab"], [role="tab"], a[role="tab"]'
                    );
                    for (const btn of buttons) {{
                        if (btn.textContent.trim() === '{display_text.replace("'", "\\'")}') {{
                            return true;
                        }}
                    }}
                    return false;
                }}
            """)
            if not found:
                self.logger.info(f"Tab '{display_text}' not available on this page")
            return found
        except Exception as e:
            self.logger.debug(f"Error checking tab availability: {e}")
            return False
    
    async def navigate_to_tab(self, tab_name: str) -> bool:
        """
        Navigate to a specific tab by clicking the button with matching text.
        
        FlashScore tab hierarchy (confirmed via live inspection):
        - Primary tabs: Match, Odds, H2H, Draw, Video
        - Under "Match" sub-tabs: Summary, Player stats, Stats, Lineups, Match History
        - Under "Odds" sub-tabs: Home/Away, 1X2, Over/Under, etc.
        
        Navigation strategy (in order):
        1. Playwright direct query — bypasses the selector engine entirely
        2. YAML selector engine (fallback for complex selectors)
        3. URL-based navigation as last resort (preserves page context)
        """
        try:
            tab_name_lower = tab_name.lower()
            
            # Map tab names to FlashScore button display text
            # Note: FlashScore uses "Standings" as a primary tab (not "Stats")
            tab_display_text = {
                'summary': 'Summary',
                'odds': 'Odds',
                'h2h': 'H2H',
                'stats': 'Standings',
                'standings': 'Standings',
                'player-stats': 'Player stats',
                'player-statistics': 'Player stats',
                'match-stats': 'Stats',
                'match-statistics': 'Stats',
                'lineups': 'Lineups',
                'match-history': 'Match History',
            }
            
            display_text = tab_display_text.get(tab_name_lower, tab_name)
            
            # For sub-tabs under "Match", first ensure "Match" primary tab is active
            if tab_name_lower in self.MATCH_SUB_TABS:
                # Click "Match" primary tab first to reveal sub-tabs
                if await self._click_tab_by_text('Match'):
                    await self.page.wait_for_timeout(1500)
                    self.logger.info(f"Clicked 'Match' primary tab for sub-tab access")
                
                # Now click the actual sub-tab
                if await self._click_tab_by_text(display_text):
                    await self.page.wait_for_timeout(2000)
                    self.logger.info(f"Successfully navigated to {tab_name} sub-tab")
                    return True
            
            # For primary tabs (Odds, H2H, Standings), click directly
            if await self._click_tab_by_text(display_text):
                await self.page.wait_for_timeout(3000)
                self.logger.info(f"Successfully navigated to {tab_name} tab via button click")
                return True
            
            # Strategy 2: URL-based navigation (last resort)
            # Instead of page.goto() which can close the context, we click the
            # navigation link directly using Playwright.
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
                
                # Try to find and click a link matching the target URL
                # This is safer than page.goto() because it keeps the page context
                try:
                    # Look for anchor elements that link to this tab
                    # FlashScore uses <a> tags with href attributes for tab navigation
                    link_selectors = [
                        f'a[href*="/{tab_url_suffix}/"]' if tab_url_suffix else 'a[href*="?mid="]',
                        f'a[href*="/{tab_url_suffix}"]' if tab_url_suffix else None,
                    ]
                    for sel in link_selectors:
                        if sel is None:
                            continue
                        try:
                            link = await self.page.query_selector(sel)
                            if link:
                                await link.click()
                                await self.page.wait_for_timeout(3000)
                                self.logger.info(f"Navigated to {tab_name} tab via link click (Playwright)")
                                return True
                        except Exception:
                            continue
                except Exception as e:
                    self.logger.debug(f"Link-click navigation failed: {e}")
                
                # Final fallback: page.goto() with error recovery
                # This can close the browser context, but we have no other option
                try:
                    self.logger.info(f"Trying URL navigation to: {target_url}")
                    await self.page.goto(target_url, wait_until='domcontentloaded', timeout=15000)
                    await self.page.wait_for_timeout(2000)
                    # Verify page is still alive
                    _ = self.page.url
                    self.logger.info(f"Successfully navigated to {tab_name} tab via URL")
                    return True
                except Exception as goto_err:
                    self.logger.error(f"URL navigation failed for {tab_name} tab: {goto_err}")
                    # Page context may be destroyed — try to recover
                    return False
            
            self.logger.warning(f"Could not find or navigate to {tab_name} tab")
            return False
            
        except Exception as e:
            self.logger.error(f"Error navigating to {tab_name} tab: {e}")
            return False
    
    async def _click_tab_by_text(self, display_text: str) -> bool:
        """Click a tab button matching the given display text.
        
        Strategy 1: Playwright direct CSS query — tries multiple selectors.
        Strategy 2: JavaScript text-based button search.
        
        NOTE: YAML selector engine is intentionally NOT used here because its
        internal retry loop catches CancelledError, making asyncio.wait_for
        timeouts ineffective. The engine will loop forever if the quality
        gate keeps failing.
        """
        # Strategy 1: Playwright direct — try all known FlashScore tab selectors
        tab_selectors = [
            'button[data-testid="wcl-tab"]',                  # Modern FlashScore tabs
            'a[data-analytics-element="SCN_TAB"]',            # Primary tab links
            'button[class*="tab"]',                            # Generic tab buttons
            '[role="tab"]',                                    # ARIA tabs
            'a[class*="tab"]',                                 # Tab links
            '.tabsPrimary a',                                  # Primary tab links (old)
            '.tabsSecondary a',                                # Sub-tab links (old)
            'button[class*="wcl-tab"]',                        # wcl-tab class pattern
        ]
        
        for selector in tab_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                for el in elements:
                    try:
                        text = (await el.text_content()).strip()
                        if text == display_text or display_text in text:
                            await el.click()
                            self.logger.info(f"Clicked '{display_text}' tab via selector: {selector}")
                            return True
                    except Exception:
                        continue
            except Exception:
                continue
        
        # Strategy 2: JavaScript text search — find and click any button with matching text
        try:
            # Escape single quotes in display_text for JS
            safe_text = display_text.replace("'", "\\'")
            matching = await self.page.evaluate(f"""
                () => {{
                    const buttons = document.querySelectorAll('button, a[role="tab"], [role="tab"], a[href*="/match/"]');
                    for (const btn of buttons) {{
                        if (btn.textContent.trim() === '{safe_text}') {{
                            btn.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
            """)
            if matching:
                self.logger.info(f"Clicked '{display_text}' tab via JavaScript text search")
                return True
        except Exception as e:
            self.logger.debug(f"JavaScript text search failed: {e}")
        
        self.logger.warning(f"Could not find tab button for '{display_text}'")
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
                except Exception:
                    continue
            
            # Fallback: just wait for network to settle
            await self.page.wait_for_load_state("networkidle", timeout=5000)
            return True
            
        except Exception as e:
            self.logger.debug(f"Tab content wait completed with exception: {e}")
            return True  # Continue anyway
    
    async def _verify_tab_active(self, tab_name: str) -> bool:
        """Verify that the specified tab is currently active.
        
        Playwright direct first, URL-based fallback.
        YAML selector engine NOT used (infinite retry loop risk).
        """
        try:
            text_to_tab = {
                'Summary': 'summary', 'Stats': 'stats', 'Odds': 'odds',
                'H2H': 'h2h', 'Match': 'match', 'Player stats': 'player-stats',
                'Lineups': 'lineups', 'Match History': 'match-history',
                'Standings': 'stats',  # FlashScore uses "Standings" primary tab for stats
            }
            
            # Strategy 1: Playwright direct — check active tab buttons
            # Live site uses data-selected="true" and class wcl-tabSelected_*
            # aria-selected is NOT set by FlashScore (confirmed via live inspection)
            active_selectors = [
                'button[data-testid="wcl-tab"][data-selected="true"]',
                'button[data-testid="wcl-tab"][class*="tabSelected"]',
                'button[data-testid="wcl-tab"][class*="Selected"]',
                'button[data-testid="wcl-tab"][class*="selected"]',
            ]
            for sel in active_selectors:
                try:
                    active_btns = await self.page.query_selector_all(sel)
                    for btn in active_btns:
                        text = (await btn.text_content()).strip()
                        if text_to_tab.get(text) == tab_name:
                            return True
                except Exception:
                    continue
            
            # Strategy 2: URL-based fallback
            current_url = self.page.url
            url_checks = {
                'summary': '/odds/' not in current_url and '/h2h/' not in current_url and '/standings/' not in current_url,
                'odds': '/odds/' in current_url,
                'h2h': '/h2h/' in current_url,
                'stats': '/summary/stats' in current_url or '/standings/' in current_url,
                'standings': '/standings/' in current_url,
            }
            if url_checks.get(tab_name, False):
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
                except Exception:
                    continue
            
            # Fallback: wait for network idle
            try:
                await self.page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
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
        
        Playwright direct queries first (fast, no infinite loops),
        then URL-based fallback. YAML selector engine is NOT used here
        because tab_selected enters an infinite retry loop.
        """
        try:
            text_to_tab = {
                'Summary': 'summary',
                'Stats': 'stats',
                'Player stats': 'player-stats',
                'Lineups': 'lineups',
                'Match History': 'match-history',
                'Odds': 'odds',
                'H2H': 'h2h',
                'Match': 'match',
                'Standings': 'standings',
                'Overall': 'overall',
                'Form': 'form',
            }
            
            # Strategy 1: Playwright direct — find active tab buttons
            # Live site uses data-selected="true" and class wcl-tabSelected_*
            # aria-selected is NOT set by FlashScore (confirmed via live inspection)
            active_selectors = [
                'button[data-testid="wcl-tab"][data-selected="true"]',
                'button[data-testid="wcl-tab"][class*="tabSelected"]',
                'button[data-testid="wcl-tab"][class*="Selected"]',
                'button[data-testid="wcl-tab"][class*="selected"]',
                'a[data-analytics-element="SCN_TAB"] button[class*="tabSelected"]',
                'a[data-analytics-element="SCN_TAB"] button[class*="Selected"]',
            ]
            for sel in active_selectors:
                try:
                    active_btns = await self.page.query_selector_all(sel)
                    for btn in active_btns:
                        text = (await btn.text_content()).strip()
                        tab_name = text_to_tab.get(text)
                        if tab_name:
                            self.logger.debug(f"Active tab detected via Playwright: {tab_name}")
                            return tab_name
                except Exception:
                    continue
            
            # Strategy 2: Check all tab buttons and find one with active class indicator
            try:
                all_btns = await self.page.query_selector_all('button[data-testid="wcl-tab"]')
                for btn in all_btns:
                    cls = await btn.get_attribute('class') or ''
                    if 'selected' in cls.lower() or 'active' in cls.lower():
                        text = (await btn.text_content()).strip()
                        tab_name = text_to_tab.get(text)
                        if tab_name:
                            self.logger.debug(f"Active tab detected via class scan: {tab_name}")
                            return tab_name
            except Exception:
                pass
            
            # Strategy 3: URL-based fallback (fast, reliable)
            current_url = self.page.url
            if '/odds/' in current_url:
                return 'odds'
            elif '/h2h/' in current_url:
                return 'h2h'
            elif '/summary/stats' in current_url or '/summary/point-by-point' in current_url:
                return 'stats'
            elif '/summary/lineups' in current_url:
                return 'lineups'
            elif '/summary/player-stats' in current_url:
                return 'player-stats'
            elif '/standings/' in current_url:
                return 'standings'
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
            elif tab_name in ('stats', 'match-stats', 'match-statistics'):
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
                required_fields = ['overview']
                return all(field in data for field in required_fields)
            elif tab_name == 'h2h':
                required_fields = ['previous_matches']
                return all(field in data for field in required_fields)
            elif tab_name == 'odds':
                required_fields = ['betting_odds']
                return all(field in data for field in required_fields)
            elif tab_name in ('stats', 'match-stats', 'match-statistics'):
                required_fields = ['detailed_statistics']
                return all(field in data for field in required_fields)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating {tab_name} tab data: {e}")
            return False
