"""
Scrape command implementation.

Handles data extraction from Flashscore.
"""

import asyncio
from typing import List, Optional
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
            
            # Navigate to site
            await scraper.navigate()
            
            # Set context based on sport and status
            await scraper._set_context(
                primary_context=f"{args.sport}_{args.status}",
                dom_state="loaded"
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
        
        # Extract match data
        matches = []
        match_elements = await scraper.page.query_selector_all('[data-testid="wcl-match"]')
        
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
        
        # Extract match data
        matches = []
        match_elements = await scraper.page.query_selector_all('[data-testid="wcl-match"]')
        
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
        # Navigate to scheduled games
        await scraper.flow.navigate_to_scheduled_games(sport_config['path_segment'])
        
        # Extract match data
        matches = []
        match_elements = await scraper.page.query_selector_all('[data-testid="wcl-match"]')
        
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
    
    async def _extract_match_data(self, element, status: str) -> dict:
        """Extract data from a match element."""
        # Basic match data extraction
        try:
            home_team = await element.query_selector('.participant__home .participant__participantName')
            away_team = await element.query_selector('.participant__away .participant__participantName')
            score = await element.query_selector('.detailScore__wrapper')
            
            return {
                'home_team': await home_team.text_content() if home_team else None,
                'away_team': await away_team.text_content() if away_team else None,
                'score': await score.text_content() if score else None,
                'status': status,
                'url': await element.get_attribute('href')
            }
        except Exception as e:
            return {'error': str(e), 'status': status}
    
    async def _write_to_file(self, content: str, file_path: str):
        """Write content to file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
