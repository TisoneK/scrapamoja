"""
Flashscore navigation flow.

Handles navigation and interaction with Flashscore sports pages.
"""

import asyncio
from src.observability.logger import get_logger
from src.sites.base.flow import BaseFlow
from src.selectors.context_manager import SelectorContext, DOMState
from src.sites.flashscore.models import NavigationState, PageState

# Module logger
logger = get_logger(__name__)


class FlashscoreFlow(BaseFlow):
    """Navigation flow for Flashscore scraper."""
    
    def __init__(self, page, selector_engine):
        """Initialize Flashscore flow with page and selector engine."""
        super().__init__(page, selector_engine)
        # Initialize snapshot system for debugging
        from src.core.snapshot.manager import SnapshotManager
        from src.core.snapshot.config import get_settings
        self.snapshot_settings = get_settings()
        self.snapshot_manager = SnapshotManager(self.snapshot_settings.base_path)
    
    async def _capture_debug_snapshot(self, operation: str, metadata: dict = None):
        """Capture debug snapshot during flow operations."""
        logger.debug("Capturing debug snapshot", operation=operation, enable_metrics=self.snapshot_settings.enable_metrics)
        try:
            if self.snapshot_settings.enable_metrics:
                from src.core.snapshot.models import SnapshotContext, SnapshotConfig, SnapshotMode
                from datetime import datetime
                import inspect
                
                # Filter metadata to remove non-serializable objects
                filtered_metadata = {}
                if metadata:
                    for key, value in metadata.items():
                        # Skip asyncio objects, functions, and other non-serializable types
                        value_type = type(value)
                        value_type_str = str(value_type)
                        
                        # Check for asyncio-related types
                        if (not inspect.iscoroutine(value) and 
                            not inspect.iscoroutinefunction(value) and
                            not inspect.isfunction(value) and
                            not inspect.ismethod(value) and
                            not inspect.isgenerator(value) and
                            not inspect.isgeneratorfunction(value) and
                            'asyncio' not in value_type_str and
                            'Future' not in value_type_str and
                            'Task' not in value_type_str and
                            'coroutine' not in value_type_str.lower() and
                            value_type.__module__ != 'asyncio' if hasattr(value_type, '__module__') else True):
                            filtered_metadata[key] = value
                
                context = SnapshotContext(
                    site="flashscore",
                    module="flow",
                    component="navigation",
                    session_id=f"flow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    function=operation,
                    additional_metadata=filtered_metadata
                )
                
                config = SnapshotConfig(
                    mode=SnapshotMode.FULL_PAGE,  # Use FULL_PAGE mode since no specific selector is provided
                    capture_html=True,
                    capture_screenshot=self.snapshot_settings.default_capture_screenshot,
                    capture_console=self.snapshot_settings.default_capture_console
                )
                
                snapshot_result = await self.snapshot_manager.capture_snapshot(
                    page=self.page,
                    context=context,
                    config=config
                )
                
                # Extract the bundle path from the SnapshotBundle result
                bundle_path = "unknown"
                if snapshot_result:
                    if hasattr(snapshot_result, 'bundle_path'):
                        bundle_path = snapshot_result.bundle_path
                        logger.debug("Successfully captured flow snapshot", bundle_path=bundle_path)
                    else:
                        logger.debug("Snapshot created but bundle_path not found in result", result_type=str(type(snapshot_result)))
                else:
                    logger.warning("Failed to capture snapshot - result is None")
                
                logger.info("Captured debug snapshot", operation=operation, bundle_path=bundle_path)

        except Exception as e:
            logger.error("Failed to capture debug snapshot", operation=operation, error=str(e), exception_type=type(e).__name__)
            import traceback
            logger.debug("Full traceback", traceback=traceback.format_exc())
    
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
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.flow")
        
        logger.info("Starting navigation to Flashscore home page...")
        
        try:
            await self.page.goto("https://www.flashscore.com", wait_until="domcontentloaded")
            logger.info("Successfully navigated to Flashscore home page")
        except Exception as e:
            logger.error(f"Failed to navigate to home page: {e}")
            raise
        
        # Handle cookie consent FIRST before trying to interact with page content
        logger.info("Proceeding to handle cookie consent...")
        await self._handle_cookie_consent()
        
        # Wait for main content using primary selectors (direct Playwright, no selector engine)
        try:
            # Get primary selectors from match_items config
            primary_selectors = self._get_match_items_primary_selectors()
            match_element = primary_selectors.get("match_element", ".event__match")
            
            logger.info(f"Waiting for main content with primary selector: {match_element}")
            await self.page.wait_for_selector(match_element, timeout=5000, state="attached")
            logger.info("Main content found using primary selector")
        except Exception as e:
            logger.warning(f"Primary selector failed: {e}, trying fallback...")
            # Fallback: wait for any match element
            try:
                await self.page.wait_for_selector('.event__match', timeout=3000)
                logger.info("Found match elements with fallback selector")
            except:
                logger.warning("No match elements found, continuing anyway")
        
        logger.info("Home page navigation completed")
    
    async def _handle_cookie_consent(self):
        """Handle cookie consent dialog if present using proper Playwright element waiting."""
        from src.observability.logger import get_logger
        from src.selectors.context import DOMContext
        from datetime import datetime
        
        logger = get_logger("flashscore.flow")
        
        logger.info("cookie_consent_handling_initiated")
        
        try:
            # Get primary selectors from config (loaded from YAML)
            primary_selectors = self._get_cookie_consent_primary_selectors()
            banner_selector = primary_selectors.get("banner_container", "#onetrust-banner-sdk")
            accept_selector = primary_selectors.get("accept_button", "#onetrust-accept-btn-handler")
            banner_timeout = primary_selectors.get("banner_timeout", 15000)
            
            # Wait for the OneTrust dialog to appear (it's loaded via external script)
            # Using Playwright's built-in wait for element visibility
            try:
                await self.page.wait_for_selector(banner_selector, state="visible", timeout=banner_timeout)
                logger.info("cookie_consent_banner_visible", banner_selector=banner_selector)
            except Exception as e:
                logger.info("cookie_consent_no_dialog", reason=str(e))
                return True  # No dialog appeared, proceed
            
            # Now try to click the accept button directly
            accept_button = await self.page.query_selector(accept_selector)
            if accept_button:
                # Ensure button is visible and clickable
                try:
                    await accept_button.wait_for_element_state("visible", timeout=5000)
                    await accept_button.click()
                    logger.info("cookie_consent_accepted", method="direct_playwright", accept_selector=accept_selector)
                    await self.page.wait_for_timeout(1000)
                    return True
                except Exception as click_error:
                    logger.warning("cookie_consent_click_failed", error=str(click_error))
            
            # Fallback Method: Use selector engine (comprehensive approach)
            try:
                dom_context = DOMContext(
                    page=self.page,
                    tab_context="flashscore_authentication",
                    url=self.page.url,
                    timestamp=datetime.utcnow()
                )
                
                logger.info("cookie_consent_handling_started", method="selector_engine")
                cookie_result = await self.selector_engine.resolve("cookie_consent", dom_context)
                if cookie_result and cookie_result.element_info:
                    logger.info("cookie_consent_dialog_found", method="selector_engine", selector_used=cookie_result.strategy_used)
                    await cookie_result.element_info.element.click()
                    logger.info("cookie_consent_accepted", method="selector_engine")
                    await self.page.wait_for_timeout(1000)
                    return True
                else:
                    logger.info("cookie_consent_dialog_not_found", method="selector_engine")
            except Exception as e:
                logger.warning("cookie_consent_handling_failed", method="selector_engine", error=str(e))
            
            # Second Fallback: Try authentication.cookie_consent selector
            try:
                logger.info("cookie_consent_handling_started", method="authentication_selector")
                auth_cookie_result = await self.selector_engine.resolve("authentication.cookie_consent", dom_context)
                if auth_cookie_result and auth_cookie_result.element_info:
                    logger.info("cookie_consent_dialog_found", method="authentication_selector", selector_used=auth_cookie_result.strategy_used)
                    await auth_cookie_result.element_info.element.click()
                    logger.info("cookie_consent_accepted", method="authentication_selector")
                    await self.page.wait_for_timeout(1000)
                    return True
                else:
                    logger.info("cookie_consent_dialog_not_found", method="authentication_selector")
            except Exception as e:
                logger.warning("cookie_consent_handling_failed", method="authentication_selector", error=str(e))
            
            # Last Resort: JavaScript dismissal for stubborn dialogs
            try:
                cookie_dialog = await self.page.query_selector(".ot-sdk-container")
                if cookie_dialog:
                    logger.warning("cookie_consent_dialog_still_visible", method="javascript_dismissal")
                    await self.page.evaluate("() => { if (window.OnetrustActiveGroups) { window.OneTrust.UpdateConsent(); } }")
                    await self.page.wait_for_timeout(1000)
                    logger.info("cookie_consent_javascript_dismissal_attempted")
            except Exception as e:
                logger.debug("cookie_consent_javascript_dismissal_failed", error=str(e))
            
            logger.info("cookie_consent_handling_completed", result="no_dialog_found")
            return False
                    
        except Exception as e:
            logger.error("cookie_consent_handling_unexpected_error", error=str(e))
            return False
    
    def _get_cookie_consent_primary_selectors(self) -> dict:
        """Get primary selectors from cookie consent config."""
        try:
            # Try to get from authentication.cookie_consent selector metadata
            selector = self.selector_engine.get_selector("authentication.cookie_consent")
            if selector and hasattr(selector, 'metadata') and selector.metadata:
                primary = selector.metadata.get('primary_selectors', {})
                if primary:
                    return primary
            
            # Fallback: Try cookie_consent selector
            selector = self.selector_engine.get_selector("cookie_consent")
            if selector and hasattr(selector, 'metadata') and selector.metadata:
                primary = selector.metadata.get('primary_selectors', {})
                if primary:
                    return primary
        except Exception:
            pass
        
        # Default values if config not found
        return {
            "banner_container": "#onetrust-banner-sdk",
            "accept_button": "#onetrust-accept-btn-handler",
            "banner_visible_state": "visible",
            "banner_timeout": 15000
        }
    
    def _get_match_items_primary_selectors(self) -> dict:
        """Get primary selectors from match_items config."""
        try:
            selector = self.selector_engine.get_selector("match_items")
            if selector and hasattr(selector, 'metadata') and selector.metadata:
                primary = selector.metadata.get('primary_selectors', {})
                if primary:
                    return primary
        except Exception:
            pass
        
        # Default values if config not found
        return {
            "match_element": ".event__match",
            "match_container": ".container__liveTableWrapper"
        }
    
    def _get_basketball_link_primary_selectors(self) -> dict:
        """Get primary selectors from basketball_link config."""
        try:
            selector = self.selector_engine.get_selector("navigation.sport_selection.basketball_link")
            if selector and hasattr(selector, 'metadata') and selector.metadata:
                primary = selector.metadata.get('primary_selectors', {})
                if primary:
                    return primary
        except Exception:
            pass
        
        # Default values if config not found
        return {
            "basketball_link": "a.menuTop__item[data-sport-id='3']",
            "basketball_menu_item": ".menuTop__item[href*='basketball']"
        }
    
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
    
    async def navigate_to_basketball(self) -> NavigationState:
        """Navigate to basketball section using workflow-based navigation."""
        from src.observability.logger import get_logger
        from src.selectors.context import DOMContext
        from datetime import datetime
        import re
        
        logger = get_logger("flashscore.flow")
        
        logger.info("Starting basketball workflow navigation...")
        
        try:
            # Step 1: Navigate to home page (handles cookie consent internally)
            await self.open_home()
            
            # Step 2: Navigate to basketball section through proper menu navigation
            # Wait for the menu to be ready and basketball link to be visible
            try:
                # Wait for the top menu to be present
                await self.page.wait_for_selector(".menuTop__item", state="visible", timeout=10000)
                logger.info("Navigation menu is visible")
            except Exception as menu_error:
                logger.warning("Navigation menu not found", error=str(menu_error))
            
            # Try to find basketball link using primary selectors (direct Playwright)
            basketball_clicked = False
            try:
                # Get primary selectors from basketball_link config
                primary_selectors = self._get_basketball_link_primary_selectors()
                basketball_selector = primary_selectors.get("basketball_link", "a.menuTop__item[data-sport-id='3']")
                
                logger.info(f"Looking for basketball link with primary selector: {basketball_selector}")
                basketball_link = await self.page.wait_for_selector(basketball_selector, timeout=5000, state="visible")
                if basketball_link:
                    await basketball_link.click()
                    await self.page.wait_for_timeout(2000)
                    logger.info("Successfully clicked basketball link", method="direct_playwright")
                    basketball_clicked = True
            except Exception as e:
                logger.warning(f"Primary basketball selector failed: {e}")
            
            if not basketball_clicked:
                # Fallback: direct navigation
                logger.warning("Basketball link not found, using direct navigation")
                await self.page.goto("https://www.flashscore.com/basketball/", wait_until="domcontentloaded")
            
            # Step 3: Verify basketball page loaded via URL pattern
            current_url = self.page.url
            url_verified = bool(re.search(r'/basketball/', current_url))
            
            # Step 4: Verify presence of match listing container
            elements_present = False
            try:
                match_container = await self.page.wait_for_selector('.container__liveTableWrapper', timeout=5000)
                elements_present = match_container is not None
                logger.info("Match listing container found")
            except:
                # Try alternative selector
                try:
                    match_elements = await self.page.query_selector_all('.event__match')
                    elements_present = len(match_elements) > 0
                    logger.info(f"Found {len(match_elements)} match elements")
                except:
                    logger.warning("No match elements found")
            
            # Step 5: Filter for scheduled matches
            await self._filter_scheduled_matches()
            
            navigation_state = NavigationState(
                url=current_url,
                verified=url_verified and elements_present,
                elements_present=elements_present,
                timestamp=datetime.utcnow()
            )
            
            if navigation_state.verified:
                logger.info("Basketball navigation completed successfully")
            else:
                logger.warning("Basketball navigation completed with verification issues")
            
            return navigation_state
            
        except Exception as e:
            logger.error(f"Error in navigate_to_basketball: {e}")
            # Return failed state
            return NavigationState(
                url=self.page.url,
                verified=False,
                elements_present=False,
                timestamp=datetime.utcnow()
            )
    
    async def _filter_scheduled_matches(self):
        """Filter for scheduled matches."""
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.flow")
        
        try:
            # Look for scheduled matches filter
            scheduled_selectors = [
                "navigation.event_filter.scheduled_games_filter",
                "[data-analytics-element='SCN_TAB'][data-analytics-alias='scheduled']",
                ".filters__tab:not(.selected)"
            ]
            
            for selector in scheduled_selectors:
                try:
                    scheduled_link = await self.page.query_selector(selector)
                    if scheduled_link:
                        await scheduled_link.click()
                        await self.page.wait_for_timeout(2000)
                        logger.info("Successfully filtered for scheduled matches")
                        return
                except:
                    continue
            
            logger.info("No scheduled filter found, using current page state")
            
        except Exception as e:
            logger.warning(f"Error filtering scheduled matches: {e}")

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
    
    async def navigate_to_match(self, match_id: str, max_retries: int = 3) -> PageState:
        """Navigate to a specific match detail page with state verification and rate limiting."""
        from src.observability.logger import get_logger
        from datetime import datetime
        import re
        import asyncio
        
        logger = get_logger("flashscore.flow")
        
        # Rate limiting: 1 request per second
        current_time = datetime.utcnow()
        
        # Check if we need to wait for rate limiting
        if hasattr(self, '_last_match_navigation_time'):
            time_since_last = (current_time - self._last_match_navigation_time).total_seconds()
            if time_since_last < 1.0:  # Less than 1 second since last navigation
                wait_time = 1.0 - time_since_last
                logger.info(f"Rate limiting: waiting {wait_time:.2f}s before next match navigation")
                await asyncio.sleep(wait_time)
        
        logger.info(f"Navigating to match detail page for match ID: {match_id}")
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    backoff_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} after {backoff_time}s backoff")
                    await asyncio.sleep(backoff_time)
                
                # Step 1: Find match element using correct selectors based on extraction logic
                # Match extraction uses ?mid= parameter or aria-describedby, so we need to find elements accordingly
                match_selectors = [
                    f".eventRowLink[href*='mid={match_id}']",  # Primary: URL contains mid= parameter
                    f".eventRowLink[aria-describedby*='{match_id}']",  # Fallback: aria-describedby contains match ID
                    f".event__match .eventRowLink[href*='mid={match_id}']",  # More specific version
                    f"[href*='mid={match_id}']",  # Generic fallback
                    f"[aria-describedby*='{match_id}']"  # Generic fallback
                ]
                
                match_element = None
                for selector in match_selectors:
                    match_element = await self.page.query_selector(selector)
                    if match_element:
                        logger.info(f"Found match using selector: {selector}")
                        break
                
                if not match_element:
                    # Additional fallback: try data-event-id (in case the site structure changed)
                    fallback_selectors = [
                        f".event__match[data-event-id='{match_id}']",
                        f"[data-event-id='{match_id}']",
                        f".eventRowLink[href*='{match_id}']"
                    ]
                    
                    for selector in fallback_selectors:
                        match_element = await self.page.query_selector(selector)
                        if match_element:
                            logger.info(f"Found match using fallback selector: {selector}")
                            break
                    
                    if not match_element:
                        raise Exception(f"Match element not found for ID: {match_id}")
                
                # Step 2: Click on match element
                await match_element.click()
                await self.page.wait_for_timeout(2000)
                
                # Step 3: Wait for match detail page to load
                await self.page.wait_for_load_state('domcontentloaded')
                
                # Step 4: Verify match detail page URL pattern
                current_url = self.page.url
                url_verified = bool(re.search(r'/match/', current_url)) or bool(re.search(match_id, current_url))
                
                # Step 5: Confirm presence of match detail DOM markers
                tabs_available = []
                verified = False
                
                try:
                    # Multiple verification strategies for different page layouts
                    # Note: _verify_tabs_container and _verify_match_detail_content are async
                    verification_strategies = [
                        # Strategy 1: Check for tabs container (async)
                        self._verify_tabs_container,
                        # Strategy 2: Check for match detail content (async)
                        self._verify_match_detail_content,
                        # Strategy 3: Check for URL-based verification only (sync)
                        lambda: self._verify_url_only(current_url, match_id)
                    ]
                    
                    for strategy_func in verification_strategies:
                        try:
                            # Handle async functions properly
                            import asyncio
                            if asyncio.iscoroutinefunction(strategy_func):
                                result = await strategy_func()
                            else:
                                result = strategy_func()
                            if result:
                                tabs_available = result if isinstance(result, list) else ['summary']
                                verified = True
                                logger.info(f"Verification successful using strategy, found tabs: {tabs_available}")
                                break
                        except Exception as e:
                            logger.debug(f"Verification strategy failed: {e}")
                            continue
                            
                except Exception as e:
                    logger.warning(f"Error verifying match detail page structure: {e}")
                
                # Update rate limiting timestamp
                self._last_match_navigation_time = datetime.utcnow()
                
                page_state = PageState(
                    match_id=match_id,
                    url=current_url,
                    tabs_available=tabs_available,
                    verified=verified and url_verified,
                    timestamp=datetime.utcnow()
                )
                
                if page_state.verified:
                    logger.info(f"Successfully navigated to match detail page: {match_id}")
                    return page_state
                else:
                    logger.warning(f"Match detail navigation completed with verification issues: {match_id}")
                    if attempt < max_retries - 1:
                        continue  # Try again
                    return page_state
                    
            except Exception as e:
                logger.error(f"Error navigating to match {match_id} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    continue  # Try again
                else:
                    # Return failed state after all retries exhausted
                    logger.error(f"All {max_retries} attempts failed for match {match_id}")
                    return PageState(
                        match_id=match_id,
                        url=self.page.url,
                        tabs_available=[],
                        verified=False,
                        timestamp=datetime.utcnow()
                    )

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
        
        # Skip scheduled filter click - page already shows scheduled matches by default
        # The scheduled filter selector was failing, but scheduled matches are found without it
        logger.info("Skipping scheduled filter click - page shows scheduled matches by default")
    
    async def _verify_tabs_container(self) -> Optional[list]:
        """Verify tabs container exists and extract available tabs."""
        try:
            tab_container = await self.page.query_selector('.tabs__detail')
            if tab_container:
                tab_selectors = {
                    'summary': '.tab__title[data-tab-name="summary"]',
                    'h2h': '.tab__title[data-tab-name="h2h"]', 
                    'odds': '.tab__title[data-tab-name="odds"]',
                    'stats': '.tab__title[data-tab-name="stats"]'
                }
                
                tabs_available = []
                for tab_name, selector in tab_selectors.items():
                    tab_element = await self.page.query_selector(selector)
                    if tab_element:
                        tabs_available.append(tab_name)
                
                return tabs_available if tabs_available else None
            return None
        except Exception:
            return None
    
    async def _verify_match_detail_content(self) -> Optional[bool]:
        """Verify match detail content exists."""
        try:
            # Multiple possible content containers
            content_selectors = [
                '.matchDetail',
                '.match-detail',
                '.event__match--detail',
                '[class*="matchDetail"]',
                '[class*="match-detail"]',
                '.detailContainer',
                '[class*="detail"]'
            ]
            
            for selector in content_selectors:
                content = await self.page.query_selector(selector)
                if content:
                    return True
            return False
        except Exception:
            return False
    
    def _verify_url_only(self, current_url: str, match_id: str) -> Optional[bool]:
        """Verify URL contains match indicators."""
        try:
            # Multiple URL patterns for match detail pages
            match_patterns = [
                f'/match/',
                f'/game/',
                f'/event/',
                match_id,
                'flashscore.com/match',
                'flashscore.com/game'
            ]
            
            return any(pattern in current_url for pattern in match_patterns)
        except Exception:
            return False
