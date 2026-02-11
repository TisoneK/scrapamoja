"""
Flashscore navigation flow.

Handles navigation and interaction with Flashscore sports pages.
"""

from src.sites.base.flow import BaseFlow
from src.selectors.context_manager import SelectorContext, DOMState


class FlashscoreFlow(BaseFlow):
    """Navigation flow for Flashscore scraper."""
    
    def _get_timeout_ms(self, selector_name: str, default_timeout: float = 3.0) -> int:
        """
        Get timeout from selector definition and convert to milliseconds.
        
        Args:
            selector_name: Name of the selector to get timeout for
            default_timeout: Default timeout in seconds if selector not found
            
        Returns:
            Timeout in milliseconds
        """
        try:
            selector = self.selector_engine.get_selector(selector_name)
            timeout = selector.timeout if selector else default_timeout
            return int(timeout * 1000)  # Convert seconds to milliseconds
        except Exception:
            return int(default_timeout * 1000)

    async def open_home(self):
        """Navigate to Flashscore home page."""
        await self.page.goto("https://www.flashscore.com", wait_until="domcontentloaded")
        
        # Wait for main content to be present using selector system
        try:
            from src.selectors.context import DOMContext
            from datetime import datetime
            from src.observability.logger import get_logger
            
            logger = get_logger("flashscore.flow")
            
            dom_context = DOMContext(
                page=self.page,
                tab_context="flashscore_extraction",
                url=self.page.url,
                timestamp=datetime.utcnow()
            )
            
            # Try to resolve the main content selector
            main_content_result = await self.selector_engine.resolve("match_items", dom_context)
            if main_content_result and main_content_result.element_info:
                logger.info("Main content found using selector engine")
            else:
                # Wait for any match element as fallback
                await self.page.wait_for_selector('.event__match', timeout=5000)
        except Exception as e:
            logger.error(f"Selector engine error: {e}")
            # Final fallback: wait for any match element
            try:
                await self.page.wait_for_selector('.event__match', timeout=3000)
            except:
                pass  # Continue anyway
        
        # Handle cookie consent if present
        await self._handle_cookie_consent()
    
    async def _handle_cookie_consent(self):
        """Handle cookie consent dialog if present."""
        try:
            from src.selectors.context import DOMContext
            from datetime import datetime
            from src.observability.logger import get_logger
            
            logger = get_logger("flashscore.flow")
            
            # Create DOM context for the page
            dom_context = DOMContext(
                page=self.page,
                tab_context="flashscore_authentication",
                url=self.page.url,
                timestamp=datetime.utcnow()
            )
            
            # Use the selector engine to find cookie consent button
            try:
                cookie_result = await self.selector_engine.resolve("cookie_consent", dom_context)
                if cookie_result and cookie_result.element_info:
                    logger.info("Cookie consent dialog found using selector engine")
                    # Click accept button
                    await cookie_result.element_info.element.click()
                    # Wait using timeout from config
                    await self.page.wait_for_timeout(self._get_timeout_ms("cookie_consent", 5.0))
                else:
                    logger.info("No cookie consent dialog found")
            except Exception as e:
                logger.warning(f"Error using selector engine for cookie consent: {e}")
                # Fallback: try direct query if selector engine fails
                try:
                    accept_button = await self.page.query_selector("#onetrust-accept-btn-handler")
                    if accept_button:
                        await accept_button.click()
                        await self.page.wait_for_timeout(self._get_timeout_ms("cookie_consent", 5.0))
                except:
                    pass  # Cookie dialog might not be present
                    
        except Exception:
            # Cookie dialog might not be present or different structure
            pass
    
    async def search_sport(self, sport_name: str):
        """Search for a specific sport."""
        try:
            from src.selectors.context import DOMContext
            from datetime import datetime
            from src.observability.logger import get_logger
            
            logger = get_logger("flashscore.flow")
            
            dom_context = DOMContext(
                page=self.page,
                tab_context="flashscore_navigation",
                url=self.page.url,
                timestamp=datetime.utcnow()
            )
            
            # Use selector engine to find search input
            try:
                search_result = await self.selector_engine.resolve("search_input", dom_context)
                if search_result and search_result.element_info:
                    search_input = search_result.element_info.element
                    await search_input.clear()
                    await search_input.type(sport_name)
                    await search_input.press('Enter')
                    # Wait using timeout from config
                    await self.page.wait_for_timeout(self._get_timeout_ms("search_input"))
                else:
                    logger.warning("Search input not found")
            except Exception as e:
                logger.warning(f"Error searching for sport: {e}")
        except Exception as e:
            logger.warning(f"Error in search_sport: {e}")
    
    async def navigate_to_football(self):
        """Navigate to football section."""
        try:
            from src.selectors.context import DOMContext
            from datetime import datetime
            from src.observability.logger import get_logger
            
            logger = get_logger("flashscore.flow")
            
            dom_context = DOMContext(
                page=self.page,
                tab_context="flashscore_navigation",
                url=self.page.url,
                timestamp=datetime.utcnow()
            )
            
            # Try to find football link using selector engine
            football_result = await self.selector_engine.resolve("football_link", dom_context)
            if football_result and football_result.element_info:
                await football_result.element_info.element.click()
                await self.page.wait_for_timeout(self._get_timeout_ms("football_link", 2.0))
        except Exception as e:
            logger.warning(f"Error navigating to football: {e}")
    
    async def navigate_to_live_matches(self):
        """Navigate to live matches filter."""
        try:
            from src.selectors.context import DOMContext
            from datetime import datetime
            from src.observability.logger import get_logger
            
            logger = get_logger("flashscore.flow")
            
            dom_context = DOMContext(
                page=self.page,
                tab_context="flashscore_navigation",
                url=self.page.url,
                timestamp=datetime.utcnow()
            )
            
            # Try to find live games filter using selector engine
            live_result = await self.selector_engine.resolve("live_games_filter", dom_context)
            if live_result and live_result.element_info:
                await live_result.element_info.element.click()
                await self.page.wait_for_timeout(self._get_timeout_ms("live_games_filter", 2.0))
        except Exception as e:
            logger.warning(f"Error navigating to live matches: {e}")
    
    async def select_date(self, date_str: str):
        """Select a specific date for matches."""
        try:
            from src.selectors.context import DOMContext
            from datetime import datetime
            from src.observability.logger import get_logger
            
            logger = get_logger("flashscore.flow")
            
            dom_context = DOMContext(
                page=self.page,
                tab_context="flashscore_navigation",
                url=self.page.url,
                timestamp=datetime.utcnow()
            )
            
            # Use selector engine to find date picker
            try:
                date_result = await self.selector_engine.resolve("date_picker", dom_context)
                if date_result and date_result.element_info:
                    await date_result.element_info.element.click()
                    await self.page.wait_for_timeout(self._get_timeout_ms("date_picker", 1.0))
                    
                    # Try to find and click specific date
                    date_option_result = await self.selector_engine.resolve("date_option", dom_context)
                    if date_option_result and date_option_result.element_info:
                        await date_option_result.element_info.element.click()
                        await self.page.wait_for_timeout(self._get_timeout_ms("date_option", 2.0))
                else:
                    logger.warning("Date picker not found")
            except Exception as e:
                logger.warning(f"Error selecting date: {e}")
        except Exception as e:
            logger.warning(f"Error in select_date: {e}")
    
    async def click_match(self, match_identifier: str):
        """Click on a specific match."""
        match_element = await self.selector_engine.find(self.page, "match_item", match_identifier)
        if match_element:
            await match_element.click()
            await self.page.wait_for_timeout(2000)
    
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
        await self.page.goto(f"https://www.flashscore.com/{sport_path}/", wait_until="domcontentloaded")
        
        # Wait for the main content container to be present using selector system
        try:
            from src.selectors.context import DOMContext
            from datetime import datetime
            from src.observability.logger import get_logger
            
            logger = get_logger("flashscore.flow")
            
            dom_context = DOMContext(
                page=self.page,
                tab_context="flashscore_extraction",
                url=self.page.url,
                timestamp=datetime.utcnow()
            )
            
            # Try to resolve the main content selector
            main_content_result = await self.selector_engine.resolve("match_items", dom_context)
            if main_content_result and main_content_result.element_info:
                logger.info("Main content found using selector engine")
            else:
                # Wait for any match element as fallback
                await self.page.wait_for_selector('.event__match', timeout=5000)
        except Exception as e:
            logger.error(f"Selector engine error: {e}")
            # Final fallback: wait for any match element
            try:
                await self.page.wait_for_selector('.event__match', timeout=3000)
            except:
                pass  # Continue anyway
        
        # Then filter for live games
        await self.navigate_to_live_matches()
    
    async def navigate_to_finished_games(self, sport_path: str):
        """Navigate to finished games for a specific sport."""
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.flow")
        
        # First navigate to sport
        await self.page.goto(f"https://www.flashscore.com/{sport_path}/")
        await self.page.wait_for_load_state('domcontentloaded')
        
        # Wait for main content container to be present using selector system
        try:
            await self.page.wait_for_selector('.container__liveTableWrapper', timeout=10000)
        except:
            # Fallback: use selector engine to find match items
            try:
                await self.selector_engine.find(self.page, "match_items")
            except:
                await self.page.wait_for_timeout(2000)  # Final fallback
        
        # Try to find finished games filter
        finished_selectors = [
            "navigation.event_filter.finished_games_filter",
            "[data-analytics-element='SCN_TAB'][data-analytics-alias='finished']",
            ".filters__tab.selected"
        ]
        
        filter_clicked = False
        for selector_name in finished_selectors:
            try:
                logger.info(f"Trying to find finished filter with selector: {selector_name}")
                finished_link = await self.selector_engine.find(self.page, selector_name)
                if finished_link:
                    logger.info(f"Found finished filter, clicking...")
                    await finished_link.click()
                    # Wait for match items to reload
                    try:
                        await self.selector_engine.find(self.page, "match_items")
                    except:
                        await self.page.wait_for_timeout(2000)
                    filter_clicked = True
                    break
            except Exception as e:
                logger.warning(f"Failed with selector {selector_name}: {e}")
                continue
        
        if not filter_clicked:
            logger.warning("Could not find or click finished filter, proceeding with current page")
            # Try alternative approach - look for calendar and select previous date
            try:
                # Look for date picker or calendar to select finished games
                date_selectors = [
                    ".calendar__navigation",
                    ".calendar__day",
                    "[data-date]"
                ]
                for date_sel in date_selectors:
                    try:
                        date_elements = await self.page.query_selector_all(date_sel)
                        if date_elements:
                            # Click on a past date to get finished games
                            for date_elem in date_elements[:1]:  # Try first past date
                                await date_elem.click()
                                await self.page.wait_for_timeout(2000)
                                logger.info("Clicked on past date for finished games")
                                break
                            break
                    except:
                        continue
            except Exception as e:
                logger.warning(f"Alternative date selection failed: {e}")
    
    async def navigate_to_scheduled_games(self, sport_path: str):
        """Navigate to scheduled games for a specific sport."""
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.flow")
        
        # First navigate to the sport with better timeout handling
        try:
            await self.page.goto(f"https://www.flashscore.com/{sport_path}/", wait_until="domcontentloaded", timeout=30000)
            logger.info(f"Successfully navigated to {sport_path} page")
        except Exception as e:
            logger.error(f"Failed to navigate to {sport_path} page: {e}")
            # Try alternative approach - navigate to home first, then to sport
            try:
                await self.page.goto("https://www.flashscore.com", wait_until="domcontentloaded", timeout=20000)
                await self.page.wait_for_timeout(2000)
                await self.page.goto(f"https://www.flashscore.com/{sport_path}/", wait_until="domcontentloaded", timeout=30000)
                logger.info(f"Successfully navigated to {sport_path} page via home page")
            except Exception as e2:
                logger.error(f"Alternative navigation also failed: {e2}")
                raise e2
        
        # Wait for the main content container to be present using selector system
        try:
            await self.page.wait_for_selector('.container__liveTableWrapper', timeout=10000)
            logger.info("Main content container found")
        except:
            # Fallback: use selector engine to find match items
            try:
                await self.selector_engine.find(self.page, "match_items")
                logger.info("Match items found via selector engine")
            except:
                await self.page.wait_for_timeout(2000)  # Final fallback
                logger.warning("Using final timeout fallback")
        
        # Try to find scheduled games filter
        scheduled_selectors = [
            "navigation.event_filter.scheduled_games_filter",
            "scheduled_filter", 
            "filter-scheduled",
            ".filter-scheduled"
        ]
        
        for selector_name in scheduled_selectors:
            try:
                logger.info(f"Trying scheduled filter selector: {selector_name}")
                scheduled_link = await self.selector_engine.find(self.page, selector_name)
                if scheduled_link:
                    await scheduled_link.click()
                    logger.info(f"Successfully clicked scheduled filter using {selector_name}")
                    # Wait for match items to reload
                    try:
                        await self.selector_engine.find(self.page, "match_items")
                    except:
                        await self.page.wait_for_timeout(1000)
                    break
            except Exception as e:
                logger.debug(f"Failed with selector {selector_name}: {e}")
                continue
