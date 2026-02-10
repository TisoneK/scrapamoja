"""
Scrape command implementation.

Handles data extraction from Flashscore.
"""

import asyncio
from typing import List, Optional
import json
import re
from pathlib import Path
import argparse

from ...scraper import FlashscoreScraper
from ...selector_config import sports, match_status_detection
from ..utils.output import OutputFormatter
from src.browser import BrowserManager, BrowserConfiguration, BrowserType
from src.selectors import get_selector_engine
from tests.fixtures.browser_configs import CHROMIUM_HEADLESS_CONFIG


class ScrapeCommand:
    """Command for scraping Flashscore data."""
    
    help_text = "Scrape data from Flashscore"
    
    def add_arguments(self, parser: argparse.ArgumentParser):
        """Add command-specific arguments."""
        parser.add_argument(
            'sport',
            choices=list(sports.keys()),
            help='Sport to scrape'
        )
        
        parser.add_argument(
            'status',
            choices=['live', 'finished', 'scheduled'],
            help='Match status to scrape'
        )
        
        parser.add_argument(
            '--output', '-o',
            choices=['json', 'csv', 'xml'],
            default='json',
            help='Output format (default: json)'
        )
        
        parser.add_argument(
            '--file', '-f',
            type=str,
            help='Output file path (default: stdout)'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of matches to scrape'
        )
        
        parser.add_argument(
            '--headless',
            action='store_true',
            default=True,
            help='Run browser in headless mode'
        )
        
        parser.add_argument(
            '--no-headless',
            action='store_true',
            help='Run browser in headed mode'
        )
    
    async def execute(self, args: argparse.Namespace) -> int:
        """Execute scrape command."""
        try:
            # Determine headless mode
            headless = args.headless and not args.no_headless
            
            # Initialize browser manager and session
            browser_manager = BrowserManager()
            config = CHROMIUM_HEADLESS_CONFIG
            config.headless = headless
            
            # Create browser session
            session = await browser_manager.create_session(config)
            page = await session.create_page()
            
            # Initialize selector engine
            selector_engine = get_selector_engine()
            
            # Initialize scraper
            scraper = FlashscoreScraper(page, selector_engine)
            
            # Get sport config for navigation
            sport_config = sports[args.sport]
            
            # Import logger
            from src.observability.logger import get_logger
            logger = get_logger("flashscore.scrape")
            
            # Navigate directly to sport page with aggressive timeout handling
            try:
                await scraper.page.goto(f"https://www.flashscore.com/{sport_config['path_segment']}/", timeout=5000)
            except Exception as e:
                logger.warning(f"Initial navigation timeout, trying without wait: {e}")
                # Try again without any wait state
                await scraper.page.goto(f"https://www.flashscore.com/{sport_config['path_segment']}/", wait_until="commit")
            
            # Smart wait for real content (not skeleton)
            logger.info("Waiting for real content to load...")
            
            # Wait for initial page load
            await scraper.page.wait_for_load_state('domcontentloaded')
            
            # Wait for real match content (not skeleton)
            max_attempts = 10
            for attempt in range(max_attempts):
                try:
                    # Check if we have real match elements with actual team names
                    match_elements = await scraper.page.query_selector_all('.event__match')
                    if match_elements:
                        # Check if any match has real team names (not skeleton placeholders)
                        for match in match_elements[:3]:  # Check first 3 matches
                            try:
                                home_element = await match.query_selector('.event__participant--home, .participant__home')
                                away_element = await match.query_selector('.event__participant--away, .participant__away')
                                
                                if home_element and away_element:
                                    home_text = await home_element.text_content()
                                    away_text = await away_element.text_content()
                                    
                                    # Real team names are usually longer than skeleton placeholders
                                    if len(home_text.strip()) > 2 and len(away_text.strip()) > 2:
                                        logger.info(f"Real content detected on attempt {attempt + 1}")
                                        break
                            except:
                                continue
                        
                        # If we get here, we didn't find real content yet
                        if attempt < max_attempts - 1:
                            logger.info(f"Skeleton content detected, waiting... (attempt {attempt + 1}/{max_attempts})")
                            await scraper.page.wait_for_timeout(1000)
                        else:
                            logger.warning("Real content not detected after maximum attempts, proceeding anyway")
                    else:
                        # No match elements found yet
                        if attempt < max_attempts - 1:
                            await scraper.page.wait_for_timeout(1000)
                        else:
                            logger.warning("No match elements found after maximum attempts")
                except Exception as e:
                    logger.error(f"Error checking for real content: {e}")
                    if attempt < max_attempts - 1:
                        await scraper.page.wait_for_timeout(1000)
                    else:
                        break
            
            # Set context for match list extraction
            await scraper._set_context(
                primary_context="extraction",
                secondary_context="match_list"
            )
            
            # Scrape data
            data = await self._scrape_data(scraper, args)
            
            # Format and output results
            formatter = OutputFormatter()
            output = formatter.format(data, args.output)
            
            if args.file:
                await self._write_to_file(output, args.file)
            else:
                print(output)
            
            # Cleanup
            await browser_manager.close_session(session.session_id)
            
            return 0
            
        except Exception as e:
            print(f"Scraping failed: {e}", file=__import__('sys').stderr)
            return 1
    
    async def _scrape_data(self, scraper: FlashscoreScraper, args: argparse.Namespace) -> dict:
        """Scrape data based on arguments."""
        sport_config = sports[args.sport]
        
        if args.status == 'live':
            return await self._scrape_live_matches(scraper, sport_config, args.limit)
        elif args.status == 'finished':
            return await self._scrape_finished_matches(scraper, sport_config, args.limit)
        elif args.status == 'scheduled':
            return await self._scrape_scheduled_matches(scraper, sport_config, args.limit)
        else:
            raise ValueError(f"Unknown status: {args.status}")
    
    async def _scrape_live_matches(self, scraper: FlashscoreScraper, sport_config: dict, limit: Optional[int]) -> dict:
        """Scrape live matches."""
        # Navigate to live games
        await scraper.flow.navigate_to_live_games(sport_config['path_segment'])
        
        # Extract match data using proper selector system
        matches = []
        
        # Use the selector engine to find match items
        try:
            from src.selectors.context import DOMContext
            from datetime import datetime
            from src.observability.logger import get_logger
            
            logger = get_logger("flashscore.scrape")
            
            # Create DOM context for the page
            dom_context = DOMContext(
                page=scraper.page,
                tab_context="flashscore_extraction",
                url=scraper.page.url,
                timestamp=datetime.utcnow()
            )
            
            # Use the selector engine to resolve match_items
            match_result = await scraper.selector_engine.resolve("match_items", dom_context)
            if match_result and match_result.element_info:
                # If we found one, get all similar elements using the CSS selector from the result
                if match_result.element_info.css_selector:
                    match_elements = await scraper.page.query_selector_all(match_result.element_info.css_selector)
                else:
                    # Fallback to standard selector
                    match_elements = await scraper.page.query_selector_all('.event__match')
                logger.info(f"Found {len(match_elements)} live match elements using selector engine")
            else:
                match_elements = []
                logger.warning("No live match elements found")
        except Exception as e:
            logger.error(f"Error using selector engine: {e}")
            # Fallback to direct query if selector engine fails
            match_elements = await scraper.page.query_selector_all('.event__match')
            logger.info(f"Found {len(match_elements)} live match elements with fallback selector .event__match")
        
        for i, element in enumerate(match_elements):
            if limit and i >= limit:
                break
                
            match_data = await self._extract_match_data(element, 'live')
            matches.append(match_data)
        
        return {
            'sport': sport_config['name'],
            'status': 'live',
            'matches': matches,
            'total': len(matches)
        }
    
    async def _scrape_finished_matches(self, scraper: FlashscoreScraper, sport_config: dict, limit: Optional[int]) -> dict:
        """Scrape finished matches."""
        # Navigate to finished games
        await scraper.flow.navigate_to_finished_games(sport_config['path_segment'])
        
        # Extract match data using proper selector system
        matches = []
        
        # Use the selector engine to find match items
        try:
            from src.selectors.context import DOMContext
            from datetime import datetime
            from src.observability.logger import get_logger
            
            logger = get_logger("flashscore.scrape")
            
            # Create DOM context for the page
            dom_context = DOMContext(
                page=scraper.page,
                tab_context="flashscore_extraction",
                url=scraper.page.url,
                timestamp=datetime.utcnow()
            )
            
            # Use the selector engine to resolve match_items
            match_result = await scraper.selector_engine.resolve("match_items", dom_context)
            if match_result and match_result.element_info:
                # If we found one, get all similar elements using the CSS selector from the result
                if match_result.element_info.css_selector:
                    match_elements = await scraper.page.query_selector_all(match_result.element_info.css_selector)
                else:
                    # Fallback to standard selector
                    match_elements = await scraper.page.query_selector_all('.event__match')
                logger.info(f"Found {len(match_elements)} finished match elements using selector engine")
            else:
                match_elements = []
                logger.warning("No finished match elements found")
        except Exception as e:
            logger.error(f"Error using selector engine: {e}")
            # Fallback to direct query if selector engine fails
            match_elements = await scraper.page.query_selector_all('.event__match')
            logger.info(f"Found {len(match_elements)} finished match elements with fallback selector .event__match")
        
        for i, element in enumerate(match_elements):
            if limit and i >= limit:
                break
                
            match_data = await self._extract_match_data(element, 'finished')
            matches.append(match_data)
        
        return {
            'sport': sport_config['name'],
            'status': 'finished',
            'matches': matches,
            'total': len(matches)
        }
    
    async def _scrape_scheduled_matches(self, scraper: FlashscoreScraper, sport_config: dict, limit: Optional[int]) -> dict:
        """Scrape scheduled matches."""
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.scrape")
        
        # Navigate to scheduled games
        await scraper.flow.navigate_to_scheduled_games(sport_config['path_segment'])
        
        # Debug: Check current URL and page title
        current_url = scraper.page.url
        page_title = await scraper.page.title()
        logger.info(f"Navigating to scheduled games for {sport_config['path_segment']}")
        logger.info(f"Current URL: {current_url}")
        logger.info(f"Page title: {page_title}")
        
        # Extract match data using proper selector system
        matches = []
        
        # Use the selector engine to find match items
        try:
            from src.selectors.context import DOMContext
            from datetime import datetime
            from src.observability.logger import get_logger, CorrelationContext
            
            logger = get_logger("flashscore.scrape")
            
            # Generate unique correlation ID for this operation
            correlation_id = f"scrape_scheduled_{datetime.utcnow().timestamp()}"
            CorrelationContext.set_correlation_id(correlation_id)
            
            # Create DOM context for the page
            dom_context = DOMContext(
                page=scraper.page,
                tab_context="flashscore_extraction",
                url=scraper.page.url,
                timestamp=datetime.utcnow()
            )
            
            # Use the selector engine to resolve match_items
            match_result = await scraper.selector_engine.resolve("match_items", dom_context)
            if match_result and match_result.element_info:
                # If we found one, get all similar elements using the CSS selector from the result
                if match_result.element_info.css_selector:
                    match_elements = await scraper.page.query_selector_all(match_result.element_info.css_selector)
                else:
                    # Fallback to standard selector
                    match_elements = await scraper.page.query_selector_all('.event__match')
                logger.info(f"Found {len(match_elements)} match elements using selector engine")
            else:
                match_elements = []
                logger.warning("No match elements found")
        except Exception as e:
            logger.error(f"Error using selector engine: {e}")
            # Fallback to direct query if selector engine fails
            match_elements = await scraper.page.query_selector_all('.event__match')
            logger.info(f"Found {len(match_elements)} match elements with fallback selector .event__match")
        
        for i, element in enumerate(match_elements):
            if limit and i >= limit:
                break
                
            match_data = await self._extract_match_data(element, 'scheduled')
            matches.append(match_data)
        
        return {
            'sport': sport_config['name'],
            'status': 'scheduled',
            'matches': matches,
            'total': len(matches)
        }
    
    async def _extract_match_id(self, element) -> str:
        """Extract match ID using two methods: URL parameter (primary) and aria-describedby (fallback)."""
        
        # Method 1: Extract from URL parameter ?mid=CSXgyReU (primary)
        try:
            link_element = await element.query_selector('.eventRowLink')
            if link_element:
                href = await link_element.get_attribute('href')
                if href:
                    import re
                    mid_match = re.search(r'[?&]mid=([^&]+)', href)
                    if mid_match:
                        return mid_match.group(1)
        except:
            pass
        
        # Method 2: Extract from aria-describedby="g_3_CSXgyReU" (fallback)
        try:
            link_element = await element.query_selector('.eventRowLink')
            if link_element:
                aria_describedby = await link_element.get_attribute('aria-describedby')
                if aria_describedby:
                    # Remove "g_3_" prefix to get match ID
                    if aria_describedby.startswith('g_'):
                        parts = aria_describedby.split('_')
                        if len(parts) >= 3:
                            return '_'.join(parts[2:])  # Join everything after "g_3_"
        except:
            pass
        
        return None

    async def _extract_match_data(self, element, status: str) -> dict:
        """Extract data from a match element using proper selector system."""
        # Basic match data extraction using selector engine
        try:
            # For match list extraction, we need to find elements within the match item
            # Use element as context for finding team names and scores
            
            # Extract match ID using dedicated method
            match_id = await self._extract_match_id(element)
            
            # Extract match URL
            match_url = None
            try:
                link_element = await element.query_selector('.eventRowLink')
                if link_element:
                    match_url = await link_element.get_attribute('href')
                    if match_url and not match_url.startswith('http'):
                        match_url = f"https://www.flashscore.com{match_url}"
            except:
                pass
            
            # Try to find home team within the match element
            try:
                home_team_element = await element.query_selector('.event__participant--home, .participant__home')
                home_team = await home_team_element.text_content() if home_team_element else None
            except:
                home_team = None
            
            # Try to find away team within the match element  
            try:
                away_team_element = await element.query_selector('.event__participant--away, .participant__away')
                away_team = await away_team_element.text_content() if away_team_element else None
            except:
                away_team = None
            
            # Try to find score within the match element
            try:
                score_element = await element.query_selector('.detailScore__wrapper, .event__result')
                score = await score_element.text_content() if score_element else None
            except:
                score = None
            
            # Try to extract time/date info
            try:
                time_element = await element.query_selector('.event__time, .time')
                match_time = await time_element.text_content() if time_element else None
            except:
                match_time = None
            
            # Try to extract tournament info
            try:
                tournament_element = await element.query_selector('.event__tournament, .tournament')
                tournament = await tournament_element.text_content() if tournament_element else None
            except:
                tournament = None
            
            return {
                'match_id': match_id,
                'home_team': home_team,
                'away_team': away_team,
                'score': score,
                'status': status,
                'url': match_url,
                'time': match_time,
                'tournament': tournament
            }
        except Exception as e:
            return {'error': str(e), 'status': status}
    
    async def _write_to_file(self, content: str, file_path: str):
        """Write content to file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
